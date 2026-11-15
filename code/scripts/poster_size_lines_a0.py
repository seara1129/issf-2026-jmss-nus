"""Poster (A0) version of the leaf-size half of fig26: each tagged leaf's size (centroid size, mm) over the 26 days, one
line per leaf, Low humidity tank left and High humidity tank right on the same y scale, periods shaded. Same numbers as
mh-sh_L01-L14_D01-D26_specimens_v6.csv (nothing recomputed). No leaf names: they crowd the early days and the poster
never refers to single leaves. Lines are brighter greens than the other figures (darker = Low humidity, lighter = High
humidity), as asked, so they stand out on the poster's #e4e9d9. All text is one size (FS) and black, matching the
poster's caption text at the width the figure is placed. Transparent background.
Usage: python poster_size_lines_a0.py <morpho folder> <version> [--editable]
Writes 3_results/poster_figures/a0/a0_size_per_leaf_<v>.svg and .png (300 dpi); --editable also writes the picture
without text and its text list for make_figure_pptx.js (see editable_text.py).
"""
import csv
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from editable_text import save_editable

root, ver = sys.argv[1:3]
editable = "--editable" in sys.argv[3:]
res = os.path.join(root, "3_results")
out = os.path.join(res, "poster_figures", "a0")
LOW, HIGH, INK, QUIET = "#3f8f2a", "#6cbf3f", "#000000", "#555555"     # line colours; black text
SHADE = {"A": "#edf1e5", "B": "#f4f0e3", "C": "#d9eac2"}
PERIODS = {"A": (1, 10, "1–10"), "B": (11, 16, "11–16"), "C": (17, 26, "17–26")}   # days; "Day" is the axis title
FS = 30                                                                  # pt, all text
plt.rcParams.update({"font.family": "Arial", "font.size": FS, "axes.labelsize": FS, "xtick.labelsize": FS,
                     "ytick.labelsize": FS, "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "axes.edgecolor": QUIET, "axes.linewidth": 1.4, "xtick.major.width": 1.4,
                     "ytick.major.width": 1.4, "xtick.major.size": 7, "ytick.major.size": 7, "svg.fonttype": "none"})
spec = list(csv.DictReader(open(os.path.join(res, "mh-sh_L01-L14_D01-D26_specimens_v6.csv"), encoding="utf-8")))
series = {}
for r in spec:
    series.setdefault((r["condition"], r["leaf"]), []).append((int(r["day"]), float(r["centroid_size_mm"])))
YLIM = (28, 80)

fig, axes = plt.subplots(1, 2, figsize=(12.3, 7.4), sharey=True, gridspec_kw=dict(wspace=0.08))
for ax, (t, col, name) in zip(axes, (("mh", LOW, "Low humidity\n(Melbourne-like)"),
                                     ("sh", HIGH, "High humidity\n(Singapore-like)"))):
    for per, (lo, hi, lab) in PERIODS.items():
        ax.axvspan(lo - 0.5, hi + 0.5, color=SHADE[per], zorder=0, lw=0)
        ax.text((lo + hi) / 2, YLIM[1] - 0.8, lab, ha="center", va="top", fontsize=FS)
    for (c, leaf), v in sorted(series.items()):
        if c != t:
            continue
        v.sort()
        ax.plot([d for d, _ in v], [s for _, s in v], color=col, lw=2.6, marker="o", ms=6, zorder=2)
    ax.set_title(name, loc="left", fontsize=FS, fontweight="bold", linespacing=1.15)
    ax.set_xlim(0.3, 26.7)
    ax.set_ylim(*YLIM)
    ax.set_yticks(range(30, 80, 10))                                     # no "80": it would touch the panel title
    ax.set_xticks([1, 5, 10, 15, 20, 25])
    ax.set_xlabel("Day")
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("Leaf size\n(centroid size, mm)", linespacing=1.15)
for ext in ("svg", "png"):
    p = os.path.join(out, f"a0_size_per_leaf_{ver}.{ext}")
    if os.path.exists(p):
        raise SystemExit(f"{p} already exists - not overwriting")
    fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.15, transparent=True)
print("wrote a0_size_per_leaf", {t: sum(k[0] == t for k in series) for t in ("mh", "sh")}, "leaves")
if editable:
    save_editable(fig, out, f"a0_size_per_leaf_{ver}")
