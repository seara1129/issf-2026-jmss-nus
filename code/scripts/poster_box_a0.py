"""Box-plot version of the greenness-by-period figure for the A0 poster: one value per leaf (its average greenness in the
period), box = middle half of the leaves, line = median, whiskers = 1.5 x IQR, every leaf shown as a dot on top (only
5-7 leaves per box). Difference, 95% CI and exact p from plan_D17-D26_results_v2.csv (difference of MEANS, as tested).
Colours are the poster's greens (dark = Low humidity, sage = High humidity); the background is transparent. All text
is one size (FS), black, matching the poster's caption text at the width the figure is placed.
Usage: python poster_box_a0.py <morpho folder> <version> [--editable]
Writes 3_results/poster_figures/a0/a0_fig21_greenness_box_<v>.svg and .png (300 dpi); --editable also writes the
picture without text and its text list for make_figure_pptx.js (see editable_text.py).
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
LOW, HIGH, INK, QUIET = "#406327", "#7f9c65", "#000000", "#555555"     # the poster's dark green and sage; black text
SHADE = {"A": "#edf1e5", "B": "#f4f0e3", "C": "#d9eac2"}                # periods; C shows on the poster's #e4e9d9
FS = 30                                                                  # pt, all text
plt.rcParams.update({"font.family": "Arial", "font.size": FS, "axes.labelsize": FS, "xtick.labelsize": FS,
                     "ytick.labelsize": FS, "legend.fontsize": FS, "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.edgecolor": QUIET, "axes.linewidth": 1.4,
                     "xtick.major.width": 1.4, "ytick.major.width": 1.4, "xtick.major.size": 7, "ytick.major.size": 7,
                     "svg.fonttype": "none"})
per_leaf = list(csv.DictReader(open(os.path.join(res, "plan_D17-D26_per_leaf_v2.csv"), encoding="utf-8")))
results = list(csv.DictReader(open(os.path.join(res, "plan_D17-D26_results_v2.csv"), encoding="utf-8")))
M = "greenness (GCC)"
minus = lambda s: s.replace("-", "−")


def ptxt(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}" if p < 0.1 else f"p = {p:.2f}"


fig, ax = plt.subplots(figsize=(12.0, 9.2))
labels = {"A": "Days 2–10\nfirst week\n54 vs 90% RH", "B": "Days 11–16\nLow tank damper\n68 vs 96% RH",
          "C": "Days 17–26\nplanned test\n52 vs 94% RH"}
for i, per in enumerate("ABC"):
    ax.axvspan(i - 0.46, i + 0.46, color=SHADE[per], zorder=0, lw=0)
    for t, col, dx in (("mh", LOW, -0.2), ("sh", HIGH, 0.2)):
        v = np.array([float(r["value"]) for r in per_leaf if r["measure"] == M and r["period"] == per and r["tank"] == t])
        bp = ax.boxplot(v, positions=[i + dx], widths=0.3, patch_artist=True, showfliers=False, zorder=2,
                        medianprops=dict(color=col, lw=4), whiskerprops=dict(color=col, lw=2.2),
                        capprops=dict(color=col, lw=2.2), boxprops=dict(facecolor="none", edgecolor=col, lw=2.6))
        jit = np.linspace(-0.08, 0.08, len(v)) if len(v) > 1 else np.zeros(1)
        ax.scatter(i + dx + jit, v, s=130, color=col, edgecolor="white", linewidth=1.1, zorder=3)
    r = next(x for x in results if x["measure"] == M and x["period"].startswith(per + " "))
    d, c0, c1, p = float(r["low_minus_high (shape: distance)"]), float(r["ci95_low"]), float(r["ci95_high"]), float(r["exact_p"])
    txt = minus(f"{d:+.3f}\n{c0:+.2f} to {c1:+.2f}") + "\n" + ptxt(p)       # CI to 2 decimals so it fits its band
    ax.text(i, 0.668, txt, ha="center", va="top", fontsize=FS, fontweight="bold" if per == "C" else "normal",
            linespacing=1.15)
# the y-axis title sits in this note instead of beside the axis, so the three periods get the full width at this size
ax.text(-0.09, 1.02, "Greenness (GCC, leaf average). Numbers at the\ntop: Low − High difference, 95% CI and p",
        transform=ax.transAxes, ha="left", va="bottom", fontsize=FS, linespacing=1.15)
ax.set_xticks(range(3))
ax.set_xticklabels([labels[p] for p in "ABC"])
ax.set_xlim(-0.5, 2.5)
ax.set_ylim(0.42, 0.67)
ax.spines[["top", "right"]].set_visible(False)
ax.scatter([], [], s=130, color=LOW, label="Low humidity (Melbourne-like)")
ax.scatter([], [], s=130, color=HIGH, label="High humidity (Singapore-like)")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.215), ncol=1, handletextpad=0.3,
          borderpad=0, labelspacing=0.3)                                    # right under the period labels
for ext in ("svg", "png"):
    path = os.path.join(out, f"a0_fig21_greenness_box_{ver}.{ext}")
    if os.path.exists(path):
        raise SystemExit(f"{path} already exists - not overwriting")
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.15, transparent=True)   # sits on the poster's colour
print("wrote a0_fig21_greenness_box")
if editable:
    save_editable(fig, out, f"a0_fig21_greenness_box_{ver}")
