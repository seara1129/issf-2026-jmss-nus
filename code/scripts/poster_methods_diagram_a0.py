"""Methods diagram for the A0 poster: a schematic nasturtium leaf on 5 mm grid paper showing how the 13 landmarks are
placed (hub = landmark 1; the line from the leaf's centre through the hub sets 12 o'clock = landmark 2; the others every
30 degrees, marked on the drawing), with the method steps around it. Schematic only: the leaf is drawn, not a photo.
Boxes size themselves to their wrapped text; the gap above box 2 is left empty for a set-up diagram.
Two arrangements:
  default  tall: boxes 1-2 left, 3-4 right of the photo, 5 under it; body text 28 pt on a 16 in wide figure, which
           matches the poster caption when placed at column width (v4).
  --wide   landscape like v3 (boxes 3-5 in a right column) at the v3 poster size (16 x 9.1 in); the body text is the
           largest size that still fits, searched in 0.5 pt steps.
--fair-tests adds the fair-tests band underneath. --editable also writes the leaf drawing on its own
(a0_methods_leaf_<v>.png) and the box layout (a0_methods_layout_<v>.json) for make_methods_pptx.js.
Usage: python poster_methods_diagram_a0.py <morpho folder> <version> [--wide] [--fair-tests] [--editable]
Writes 3_results/poster_figures/a0/a0_methods_diagram_<v>.svg and .png (300 dpi).
"""
import json
import os
import sys
from functools import lru_cache

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Polygon, Rectangle
from matplotlib.textpath import TextPath
from matplotlib.transforms import Bbox

root, ver = sys.argv[1:3]
opts = sys.argv[3:]
wide, fair_tests, editable = "--wide" in opts, "--fair-tests" in opts, "--editable" in opts
out = os.path.join(root, "3_results", "poster_figures", "a0")
GREEN, DARK, LEAF, VEIN, ORANGE, INK, GRIDC, PAPER = ("#3d6b2c", "#25451a", "#6f9e45", "#dfeec4", "#d9822b", "#222222",
                                                      "#d9d9d2", "#fbfbf6")
TINT = "#eef5e6"
plt.rcParams.update({"font.family": "Arial", "svg.fonttype": "none"})
REG, BOLD = FontProperties(family="Arial"), FontProperties(family="Arial", weight="bold")
W, LX, VGAP = 160, 1.5, 3.0                      # 1 unit = 0.1 in = 7.2 pt
SETUP = 20.0 if wide else 26.0                   # minimum empty gap above box 2 for the set-up diagram
TITLE = 30 if wide else 40                       # pt
H_WIDE = 91.0                                    # v3 as placed on the poster (fair-tests band cropped off)
TITLE_TEXT = "From leaf photo to 13 landmarks"

steps = {1: ("Two climates, 26 days", ["Low humidity (Melbourne-like): 52–54% RH",
                                         "High humidity (Singapore-like): 90–96% RH",
                                         "9 seedlings per tank; same light and water"]),
         2: ("Tagged leaves, daily photos", ["5 tagged leaves per tank at the start",
                                               "Shrivelled leaves replaced; more tagged from Day 21",
                                               "23 leaves in total (11 Low, 12 High)",
                                               "Photographed every day on 5 mm grid paper (263 photos)"]),
         3: ("Hub and edge", ["We click the hub, where the stalk joins",
                              "The program finds the edge (traced by hand if needed)"]),
         4: ("13 landmarks", ["1 = the hub", "The line from the leaf centre through the hub sets 12 o'clock (2)"]),
         5: ("What we measure", ["Shape: Procrustes analysis removes size, position and rotation",
                                 "Size: centroid size (mm)",
                                 "Roundness: 4π × area ÷ perimeter²",
                                 "Greenness: G ÷ (R + G + B), white-balanced to the paper"]),
         6: ("Fair tests", ["One value per leaf per period, never one per photo",
                            "Exact permutation tests with 95% confidence intervals",
                            "Plan written on 18 Oct, before testing Days 17–26",
                            "Measurement error 0.012 (day-to-day change 0.030; two leaves 0.06)"])}


@lru_cache(maxsize=None)
def text_w(s, size, prop=REG):
    """Ink width of s in diagram units."""
    return TextPath((0, 0), s, size=size, prop=prop).get_extents().width / 7.2


def wrap(s, avail, size):
    rows = [""]
    for word in s.split(" "):                                    # split on plain spaces only: "5 mm" stays together
        t = (rows[-1] + " " + word).strip()
        if rows[-1] and text_w(t, size) > avail:
            rows.append(word)
        else:
            rows[-1] = t
    return rows


def metrics(body):
    """Text sizes (pt) and box spacing (units) for body text of `body` pt; the spacing scales with the text."""
    s = body / 28
    return dict(body=body, label=round(0.86 * body, 1), step=body * 1.25 / 7.2, gap=s, bul=2.6 * s, pad=2.4 * s,
                rpad=1.8 * s, head=5.0 * s, first=11.2 * s, bottom=3.8 * s, rad=2.6 * s, tx=7.4 * s)


def layout(w, lines, m):
    """Wrap each bullet to a box w units wide; return the wrapped bullets and the box height."""
    avail, wrapped = w - m["pad"] - m["bul"] - m["rpad"], []
    for ln in lines:
        n = len(wrap(ln, avail, m["body"]))
        lo, hi = 0.0, avail                  # narrowest width that still needs only n rows: no one-word last rows
        while hi - lo > 0.2:
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if len(wrap(ln, mid, m["body"])) > n else (lo, mid)
        wrapped.append(wrap(ln, hi, m["body"]))
    n = sum(len(r) for r in wrapped)
    return wrapped, m["first"] + (n - 1) * m["step"] + (len(wrapped) - 1) * m["gap"] + m["bottom"]


def arrange(body):
    """Column widths, wrapped text and box heights at this text size, and the column height they need."""
    m = metrics(body)
    tw = max(text_w(steps[k][0], body, BOLD) for k in (1, 2)) + m["tx"] + 2.0
    if wide:
        lw = rw = max(52.0, tw)
        widths = {1: lw, 2: lw, 3: rw, 4: rw, 5: rw}
    else:
        lw, rw = max(60.0, tw), 46.0
        widths = {1: lw, 2: lw, 3: rw, 4: rw, 5: W - 1.5 - (LX + lw + 2.0)}
    widths[6] = W - 3
    prep = {k: layout(widths[k], steps[k][1], m) for k in steps}
    hgt = {k: prep[k][1] for k in prep}
    return m, lw, rw, widths, prep, hgt, max(hgt[3] + hgt[4] + hgt[5] + 2 * VGAP, hgt[1] + hgt[2] + SETUP)


# ---------- sizes first (the figure height depends on the wrapped text) ----------
top_room = 10.5 * TITLE / 40                     # title strip above the columns
body = 24.0 if wide else 28.0
while True:
    m, LW, RW, widths, prep, hgt, need = arrange(body)
    y_base = 1.5 + (hgt[6] + VGAP if fair_tests else 0)
    H = H_WIDE + y_base - 1.5 if wide else y_base + need + top_room
    if not wide or y_base + need + top_room <= H or body <= 12:
        break
    body -= 0.5
col_h = H - top_room - y_base
RX = W - 1.5 - RW
ls = m["label"] / 24                             # scale for offsets inside the drawing

fig = plt.figure(figsize=(W / 10, H / 10))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")

# ---------- photo on 5 mm grid paper ----------
if wide:
    fx0, fx1 = LX + LW + 2.5, RX - 2.5
    F = fx1 - fx0
    FH = min(col_h - 2, F + 6)
    fy0 = y_base + (col_h - FH) / 2
else:
    fx0, fx1 = LX + LW + 2.0, RX - 2.0
    F = fx1 - fx0
    fy0 = y_base + hgt[5] + VGAP
    FH = y_base + col_h - fy0
g = 4.5 * F / 54                                                 # one 5 mm square
ax.add_patch(Rectangle((fx0, fy0), F, FH, facecolor=PAPER, edgecolor="#9a9a92", lw=1.6, zorder=1))
for x in np.arange(fx0, fx1 + 0.01, g):
    ax.plot([x, x], [fy0, fy0 + FH], color=GRIDC, lw=0.9, zorder=1)
for y in np.arange(fy0, fy0 + FH + 0.01, g):
    ax.plot([fx0, fx1], [y, y], color=GRIDC, lw=0.9, zorder=1)
sb = (fx0 + 1.6, fy0 + 2.4 * ls)
ax.plot([sb[0], sb[0] + g], [sb[1], sb[1]], color=INK, lw=3, zorder=6, solid_capstyle="butt")
ax.text(sb[0] + g + 1.0, sb[1], "5 mm", fontsize=m["label"], color=INK, va="center_baseline", zorder=6)

# ---------- leaf ----------
lm = 6.4 * ls                                                    # room for the landmark numbers outside the edge
R = min(F / 2 - lm, (FH - lm - 2) / 2.24)
below, above = R + lm + 0.5, 1.24 * R + 0.5                      # reach below (number 8) and above (stalk) the centre
cx, cy = fx0 + F / 2, fy0 + below + (FH - below - above) / 2
th = np.linspace(0, 2 * np.pi, 2000, endpoint=False)
r = R * (1 + 0.035 * np.sin(5 * th + 0.3) + 0.022 * np.sin(8 * th + 1.0))
ox, oy = cx + r * np.cos(th), cy + r * np.sin(th)
gx, gy = ox.mean(), oy.mean()                                    # outline centre (schematic centroid)
hx, hy = gx, gy + 0.2 * R                                        # hub, off-centre as in real leaves
sa, sp = np.array([-1, 1]) / np.sqrt(2), np.array([-1, -1]) / np.sqrt(2)   # stalk leaves between landmarks 12 and 13
stalk = np.array([[hx, hy], [hx - 0.62 * R, hy + 0.58 * R], [hx - 1.02 * R, hy + 1.04 * R]])
ax.plot(stalk[:, 0], stalk[:, 1], color="#b9cf8a", lw=6, solid_capstyle="round", zorder=2)
tc = np.array([hx, hy]) + 1.3 * R * sa                           # coloured tag on the stalk
ax.add_patch(Polygon([tc + i * 0.07 * R * sa + j * 0.13 * R * sp for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))],
                     closed=True, facecolor="#e2574c", edgecolor="#9b2f26", lw=1, zorder=3))
ax.add_patch(Polygon(np.c_[ox, oy], closed=True, facecolor=LEAF, edgecolor=DARK, lw=2.2, zorder=3))
ang = np.degrees(np.arctan2(oy - hy, ox - hx))


def edge_point(deg):
    """Outline point in direction deg (math angle, y up) as seen from the hub."""
    i = np.argmin(np.abs(((ang - deg) + 180) % 360 - 180))
    return ox[i], oy[i]


for k in range(12):                                              # veins between the landmark rays
    ex, ey = edge_point(90 - 30 * k - 15)
    ax.plot([hx, ex], [hy, ey], color=VEIN, lw=1.5, zorder=4, alpha=0.85)
pts = [edge_point(90 - 30 * k) for k in range(12)]               # landmarks 2-13, clockwise from 12 o'clock
for x, y in pts:
    ax.plot([hx, x], [hy, y], color="white", lw=1.3, zorder=4, alpha=0.9)
ax.plot([gx, pts[0][0]], [gy, pts[0][1]], color=ORANGE, lw=2.4, ls=(0, (5, 3)), zorder=5)
ax.plot([gx], [gy], marker="+", ms=16, mew=3, color=ORANGE, zorder=6)
ax.text(gx, gy - 3.2 * ls, "leaf centre", fontsize=m["label"] - 2, color=DARK, fontweight="bold", ha="center",
        va="center", zorder=7, path_effects=[pe.withStroke(linewidth=5, foreground=LEAF)])
# 30 degree mark between 12 o'clock (2) and the next landmark (3)
ra = 0.38 * R
ax.add_patch(Arc((hx, hy), 2 * ra, 2 * ra, theta1=60, theta2=90, color="white", lw=2.6, zorder=6))
ax.text(hx + 1.0, hy + ra + 2.3 * ls, "30°", fontsize=m["label"], fontweight="bold", color="white", ha="left",
        va="center", zorder=7, path_effects=[pe.withStroke(linewidth=3, foreground=DARK)])
for k, (x, y) in enumerate(pts):
    ax.add_patch(Circle((x, y), 1.2, facecolor=ORANGE if k == 0 else "white", edgecolor=DARK, lw=1.8, zorder=7))
    u = np.array([x - hx, y - hy]) / np.hypot(x - hx, y - hy)
    off = 1.7 + abs(u[0]) * text_w(str(k + 2), m["label"], BOLD) / 2 + abs(u[1]) * 0.36 * m["label"] / 7.2   # clear of dot
    ax.text(x + off * u[0], y + off * u[1], str(k + 2), fontsize=m["label"], fontweight="bold", color=INK,
            ha="center", va="center", zorder=7)
ax.add_patch(Circle((hx, hy), 1.4, facecolor=INK, edgecolor="white", lw=1.5, zorder=8))
ax.text(hx - 3.4 * ls, hy + 0.5, "1", fontsize=m["label"], fontweight="bold", color="white", ha="center", va="center",
        zorder=8, bbox=dict(boxstyle="circle,pad=0.15", facecolor=INK, edgecolor="none"))

if editable:                                                     # the drawing alone, for the editable PowerPoint
    leaf_png = os.path.join(out, f"a0_methods_leaf_{ver}.png")
    if os.path.exists(leaf_png):
        raise SystemExit(f"{leaf_png} already exists - not overwriting")
    fig.savefig(leaf_png, dpi=300, bbox_inches=Bbox([[fx0 / 10 - 0.02, fy0 / 10 - 0.02],
                                                     [fx1 / 10 + 0.02, (fy0 + FH) / 10 + 0.02]]))

# ---------- step boxes ----------
drawn, links = [], []


def box(x0, top, w, num, fill="white"):
    """Draw step num as a box hanging from y = top; returns (x0, y0, w, h)."""
    title, (wrapped, h) = steps[num][0], prep[num]
    y0 = top - h
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=1.6", facecolor=fill,
                                edgecolor=GREEN, lw=2.4, zorder=5))
    ax.add_patch(Circle((x0 + 1.4 * m["rad"], top - m["head"]), m["rad"], facecolor=GREEN, edgecolor="none", zorder=6))
    ax.text(x0 + 1.4 * m["rad"], top - m["head"], str(num), fontsize=m["label"], fontweight="bold", color="white",
            ha="center", va="center", zorder=7)
    ax.text(x0 + m["tx"], top - m["head"], title, fontsize=m["body"], fontweight="bold", color=DARK,
            va="center_baseline", zorder=7)
    y = top - m["first"]
    for rows in wrapped:
        ax.text(x0 + m["pad"], y, "•", fontsize=m["body"], color=INK, va="center_baseline", zorder=7)
        for piece in rows:
            ax.text(x0 + m["pad"] + m["bul"], y, piece, fontsize=m["body"], color=INK, va="center_baseline", zorder=7)
            y -= m["step"]
        y -= m["gap"]
    drawn.append(dict(num=num, title=title, bullets=steps[num][1], rows=wrapped, x=x0, top=top, w=w, h=h, fill=fill))
    return x0, y0, w, h


def link(p_from, p_to, col=GREEN):
    ax.plot([p_from[0], p_to[0]], [p_from[1], p_to[1]], color=col, lw=1.8, zorder=4)
    ax.add_patch(Circle(p_to, 0.7, facecolor=col, edgecolor="none", zorder=9))
    links.append([float(v) for v in (*p_from, *p_to)])


def side_link(b, target, y_from=None):
    """Link from the side of box b that faces the photo, level with the target (or y_from) where the box allows."""
    x = b[0] + b[2] if b[0] < fx0 else b[0]
    y = min(max(target[1] if y_from is None else y_from, b[1] + 3), b[1] + b[3] - 3)
    link((x, y), target)


top = y_base + col_h
b1 = box(LX, top, LW, 1)
b2 = box(LX, y_base + hgt[2], LW, 2)                             # bottom of the column: set-up diagram goes above it
b3 = box(RX, top, RW, 3)
if wide:                                                         # right column spread over the full height
    rgap = (col_h - hgt[3] - hgt[4] - hgt[5]) / 2
    b4 = box(RX, b3[1] - rgap, RW, 4)
    b5 = box(RX, y_base + hgt[5], RW, 5)
    side_link(b1, (fx0 + 1.5, fy0 + FH - 1.5))
    side_link(b2, sb)
    side_link(b3, edge_point(45))
    side_link(b4, (hx + 1.5, hy + 0.2), y_from=hy - (RX - hx) * np.tan(np.radians(15)))   # between landmarks 5 and 6
    side_link(b5, (gx + 0.5 * R, gy - 0.5 * R))
else:
    b4 = box(RX, b3[1] - VGAP, RW, 4)
    b5 = box(fx0, y_base + hgt[5], widths[5], 5)
    link((b1[0] + b1[2], top - 12), (fx0 + 1.5, top - 12))     # above the stalk, clear of the landmark numbers
    link((b2[0] + b2[2], sb[1]), sb)
    e40 = edge_point(40)
    link((b3[0], b3[1] + 5), (e40[0] + 0.3, e40[1] + 0.3))
    link((b4[0], b4[1] + b4[3] - 6), (hx + 1.5, hy + 0.2))
    link((gx + 0.5 * R, b5[1] + b5[3]), (gx + 0.5 * R, gy - 0.5 * R))
if fair_tests:
    box(LX, 1.5 + hgt[6], W - 3, 6, fill=TINT)

title_y = H - top_room * 0.44
ax.text(W / 2, title_y, TITLE_TEXT, fontsize=TITLE, fontweight="bold", color=DARK, ha="center", va="center")

for ext in ("svg", "png"):
    p = os.path.join(out, f"a0_methods_diagram_{ver}.{ext}")
    if os.path.exists(p):
        raise SystemExit(f"{p} already exists - not overwriting")
    fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.1)
if editable:
    p = os.path.join(out, f"a0_methods_layout_{ver}.json")
    if os.path.exists(p):
        raise SystemExit(f"{p} already exists - not overwriting")
    json.dump(dict(W=W, H=H, title=TITLE_TEXT, title_pt=TITLE, title_y=title_y, metrics=m, boxes=drawn, links=links,
                   leaf=dict(file=os.path.basename(leaf_png), x=fx0 - 0.2, top=fy0 + FH + 0.2, w=F + 0.4, h=FH + 0.4),
                   colours=dict(green=GREEN, dark=DARK, ink=INK)),
              open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote a0_methods_diagram_{ver}: {W} x {H:.1f} units, body {m['body']} pt, frame {F:.1f} x {FH:.1f}, "
      f"leaf R {R:.1f}, set-up gap {b1[1] - (b2[1] + b2[3]):.1f}")
