"""Shared by the poster figure scripts: save a figure as a picture without its text, plus a list of that text (string,
position, size, colour, weight, rotation), so make_figure_pptx.js can rebuild the figure in PowerPoint with every label,
tick number, title and legend entry as an editable text box in the same place. Legend symbols (dots and line samples)
are left out of the picture too and listed as shapes, so they can be moved together with their legend text.
"""
import json
import os

import matplotlib.colors as mcolors
import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.lines import Line2D


def _legends(fig):
    return [ax.get_legend() for ax in fig.axes if ax.get_legend()] + list(fig.legends)


def _texts(fig):
    """Every piece of text the figure draws: titles, axis labels, tick labels, legend entries and free text."""
    found = list(fig.texts)
    for ax in fig.axes:
        found += [ax.title, ax._left_title, ax._right_title] + list(ax.texts)
        if not ax.axison:                                        # axis("off"): its labels and numbers are not drawn
            continue
        found += [ax.xaxis.label, ax.yaxis.label]
        for axis in (ax.xaxis, ax.yaxis):
            ticks = axis._update_ticks()                         # only the ticks inside the axis limits
            found += [t.label1 for t in ticks] + [t.label2 for t in ticks]
    for lg in _legends(fig):
        found += list(lg.get_texts())
    return [t for t in found if t.get_visible() and t.get_text().strip()]


def _bold(t):
    w = t.get_fontweight()
    return w >= 600 if isinstance(w, (int, float)) else w in ("semibold", "demibold", "bold", "heavy", "extra bold", "black")


def _legend_symbols(fig, to_in):
    """Legend dots (scatter handles) and line samples (line handles), as shapes in inches from the top-left."""
    shapes, artists = [], []
    for lg in _legends(fig):
        for h in lg.legend_handles:
            if isinstance(h, PathCollection):
                d_in = np.sqrt(h.get_sizes()[0]) / 72                   # marker size is an area in points^2
                for x, y in h.get_offset_transform().transform(h.get_offsets()):
                    cx, cy = to_in(x, y)
                    shapes.append(dict(kind="dot", cx=cx, cy=cy, d=d_in, fill=mcolors.to_hex(h.get_facecolor()[0]),
                                       edge=mcolors.to_hex(h.get_edgecolor()[0]), edge_pt=float(h.get_linewidths()[0])))
            elif isinstance(h, Line2D):
                (x1, y1), (x2, y2) = h.get_transform().transform(h.get_xydata())[[0, -1]]
                shapes.append(dict(kind="line", x1=to_in(x1, y1)[0], y1=to_in(x1, y1)[1], x2=to_in(x2, y2)[0],
                                   y2=to_in(x2, y2)[1], color=mcolors.to_hex(h.get_color()), width_pt=h.get_linewidth()))
            else:
                continue
            artists.append(h)
    return shapes, artists


def save_editable(fig, out, name, pad=0.15):
    """Write <name>_notext.png (300 dpi, transparent) and <name>_text.json, in the same frame as
    savefig(bbox_inches="tight", pad_inches=pad). Call after the normal save; the text is hidden while saving."""
    paths = [os.path.join(out, f"{name}_notext.png"), os.path.join(out, f"{name}_text.json")]
    for p in paths:
        if os.path.exists(p):
            raise SystemExit(f"{p} already exists - not overwriting")
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bb = fig.get_tightbbox(r).padded(pad)                        # inches
    to_in = lambda x, y: (x / fig.dpi - bb.x0, bb.y1 - y / fig.dpi)
    items, texts = [], _texts(fig)
    for t in texts:
        e = t.get_window_extent(r)
        items.append(dict(text=t.get_text(), x=e.x0 / fig.dpi - bb.x0, y=bb.y1 - e.y1 / fig.dpi, w=e.width / fig.dpi,
                          h=e.height / fig.dpi, ha=t.get_horizontalalignment(), rotation=round(t.get_rotation()) % 360,
                          size=t.get_fontsize(), color=mcolors.to_hex(t.get_color()), bold=_bold(t),
                          italic=t.get_fontstyle() == "italic", linespacing=t.get_linespacing()))
    shapes, symbols = _legend_symbols(fig, to_in)
    for a in texts + symbols:
        a.set_visible(False)
    fig.savefig(paths[0], dpi=300, bbox_inches=bb, transparent=True)
    for a in texts + symbols:
        a.set_visible(True)
    json.dump(dict(width_in=bb.width, height_in=bb.height, image=os.path.basename(paths[0]), texts=items, shapes=shapes),
              open(paths[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", os.path.basename(paths[0]), "and", os.path.basename(paths[1]),
          f"({len(items)} text boxes, {len(shapes)} legend symbols)")
