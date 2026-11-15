"""Figure 16: leaf size over time with one line per leaf (no averaging), Low and High humidity side by side, by
experiment day, so the spread behind fig2's error bars is visible leaf by leaf. Size = centroid size as % of the
leaf's first photo. Title computed from the data.
Usage: python growth_lines_figure.py <morpho folder> <out folder>
"""
import csv
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

root, out = sys.argv[1:3]
LOW, HIGH, INK, QUIET, GRID = "#1f6fd1", "#8a8a8a", "#222222", "#666666", "#e4e4e4"
plt.rcParams.update({"font.family": "Arial", "font.size": 11, "axes.edgecolor": QUIET, "axes.labelcolor": INK,
                     "xtick.color": QUIET, "ytick.color": QUIET, "svg.fonttype": "none"})
spec = list(csv.DictReader(open(os.path.join(root, "3_results", "mh-sh_L01-L11_D01-D16_specimens_v5.csv"), encoding="utf-8")))
by = {}
for r in spec:
    by.setdefault((r["condition"], r["leaf"]), []).append((int(r["day"]), float(r["centroid_size_mm"])))
series = {k: (np.array([d for d, _ in sorted(v)]), 100 * np.array([m for _, m in sorted(v)]) / sorted(v)[0][1]) for k, v in by.items()}

fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
ends = {}
for ax, cond, col, name in ((axes[0], "mh", LOW, "Low humidity (50% RH)"), (axes[1], "sh", HIGH, "High humidity (80–85% RH)")):
    leaves = sorted(l for c, l in series if c == cond)
    ends[cond] = []
    labels = []
    for lf in leaves:
        d, p = series[(cond, lf)]
        ax.plot(d, p, "-o", color=col, markersize=3.5, linewidth=1.6, alpha=0.85)
        ends[cond].append(p[-1])
        labels.append([d[-1], p[-1], f"{lf} {p[-1] - 100:+.0f}%"])
    labels.sort(key=lambda t: (t[0], t[1]))                  # nudge labels at the same end day apart
    for i in range(1, len(labels)):
        a, b = labels[i - 1], labels[i]
        if a[0] == b[0] and b[1] - a[1] < 2.2:
            b[1] = a[1] + 2.2
    for x, y, t in labels:
        ax.text(x + 0.25, y, t, va="center", fontsize=9, color=INK, zorder=5,
                bbox=dict(facecolor="white", edgecolor="none", pad=1, alpha=0.9))
    ax.axhline(100, color=QUIET, linestyle="--", linewidth=1)
    ax.axvline(10.5, color=QUIET, linestyle=":", linewidth=1)
    ax.text(10.7, 89.5, "Low tank more humid\nfrom Day 11", fontsize=9, color=QUIET, va="bottom")
    ax.set_title(name, loc="left", fontsize=12, color=INK)
    ax.set_xticks(range(1, 17))
    ax.set_xlim(0.5, 18.6)
    ax.set_xlabel("Experiment day")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
axes[0].set_ylabel("Leaf size (% of the leaf's first photo)")
axes[0].set_ylim(88, 134)
lo, hi = ends["mh"], ends["sh"]
fig.suptitle(f"Each leaf grew differently: Low leaves ended {min(lo) - 100:+.0f}% to {max(lo) - 100:+.0f}%, "
             f"High leaves {min(hi) - 100:+.0f}% to {max(hi) - 100:+.0f}%", x=0.01, ha="left", fontsize=14, fontweight="bold", color=INK)
fig.text(0.01, 0.905, "One line per leaf, all 18 leaves, no averaging; labels = change from the leaf's first photo to its last. "
         "Leaves that stop early were replaced.", fontsize=10, color=QUIET)
fig.tight_layout(rect=(0, 0, 1, 0.9))
for ext in ("png", "svg"):
    fig.savefig(os.path.join(out, f"fig16_growth_per_leaf_lines_v1.{ext}"), dpi=300, bbox_inches="tight", facecolor="white")
print("wrote fig16_growth_per_leaf_lines_v1")
