"""Figure 15: what the results can and can't say. Shape: the measured Low-High difference next to the smallest
difference the study could detect (80% power) and the reference distances. Greenness and growth: Low - High
difference per leaf with its 95% confidence interval (exact permutation test inverted), per day window.
Usage: python can_cant_figure.py <morpho folder> <out folder>
Reads 3_results/power_ci_v1.csv and 3_results/poster_figures/figure_numbers_v3.csv.
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
pc = list(csv.DictReader(open(os.path.join(root, "3_results", "power_ci_v1.csv"), encoding="utf-8")))
fn = {r["group"]: float(r["mean_or_value"]) for r in csv.DictReader(open(os.path.join(out, "figure_numbers_v3.csv"), encoding="utf-8"))
      if r["figure"] == "shape_distances"}
shape = {r["shape_effect_direction"]: r for r in pc if r["measure"].startswith("shape") and r["days"] == "Days 1-16"}
mde_rand = float(shape["random direction"]["smallest_detectable_80pct_power"])
mde_pc1 = float(shape["along PC1 (hardest)"]["smallest_detectable_80pct_power"])
obs = float(shape["random direction"]["difference_low_minus_high"])

fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1.35, 1, 1]})

# ---- shape ----
ax = axes[0]
bars = [("Measuring the same photo again", fn["Measuring the same photo again"], HIGH, None),
        ("Low vs High (measured)", obs, LOW, None),
        ("Smallest we could detect (80% power)", mde_rand, "white", mde_pc1),
        ("Same leaf, one day apart", fn["Same leaf, one day apart"], HIGH, None),
        ("Two leaves in the same tank", fn["Two different leaves in the same tank"], HIGH, None)]
for i, (lab, v, col, hi) in enumerate(bars):
    y = len(bars) - 1 - i
    ax.barh(y, v, color=col, edgecolor=INK if col == "white" else col, linewidth=1.4, hatch="//" if col == "white" else None, height=0.62)
    if hi:
        ax.plot([v, hi], [y, y], color=INK, linewidth=1.4)
        ax.plot([hi, hi], [y - 0.15, y + 0.15], color=INK, linewidth=1.4)
        ax.text(hi + 0.0015, y, f"{v:.3f}–{hi:.3f}", va="center", fontsize=10, color=INK)
    else:
        ax.text(v + 0.0015, y, f"{v:.3f}", va="center", fontsize=10, color=INK)
ax.set_yticks(range(len(bars)), [b[0] for b in bars][::-1])
ax.set_xlabel("Procrustes distance (0 = identical shapes)")
ax.set_xlim(0, 0.072)
ax.set_title("Shape: an effect of about 0.03 or more\nwould very likely have been found", loc="left", fontsize=12, fontweight="bold", color=INK)


def ci_panel(ax, measure, windows, unit, title):
    rows = {r["days"]: r for r in pc if r["measure"] == measure}
    for j, w in enumerate(windows):
        r = rows[w]
        d, lo, hi, p = (float(r[k]) for k in ("difference_low_minus_high", "ci95_low", "ci95_high", "exact_p"))
        y = len(windows) - 1 - j
        col = LOW if p < 0.05 else HIGH
        ax.plot([lo, hi], [y, y], color=col, linewidth=3, solid_capstyle="round")
        ax.plot(d, y, "o", color=col, markersize=9, markeredgecolor="white")
        val = f"{d:+.3f}" if unit == "" else f"{d:+.1f}"
        ax.text(d, y + 0.24, f"{val}   p = {p:.3f}", ha="center", fontsize=10, color=INK,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5), zorder=5)
    ax.axvline(0, color=QUIET, linestyle="--", linewidth=1)
    ax.set_yticks(range(len(windows)), [w.replace("-", "–") for w in windows][::-1])
    ax.set_ylim(-0.7, len(windows) - 0.4)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color=INK)


ci_panel(axes[1], "greenness (leaf average)", ["Days 2-10", "Days 11-16", "Days 1-16"], "",
         "Greenness: lower in dry air on Days 2–10\n(interval clear of zero)")
axes[1].set_xlabel("Low − High greenness, 95% CI")
ci_panel(axes[2], "growth (% size change per day)", ["Days 1-10", "Days 11-16", "Days 1-16"], "%",
         "Growth: too few leaves to tell\n(intervals include zero and large effects)")
axes[2].set_xlabel("Low − High growth (% per day), 95% CI")
for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
fig.suptitle("What our results can and can't say", x=0.01, ha="left", fontsize=15, fontweight="bold", color=INK)
fig.text(0.01, 0.915,"One value per leaf (9 per tank); 95% confidence intervals from the exact permutation tests; "
         "detectable shape effect from 500 simulated experiments per size (range: random direction to the hardest one, PC1)",
         fontsize=10, color=QUIET)
fig.tight_layout(rect=(0, 0, 1, 0.9))
for ext in ("png", "svg"):
    fig.savefig(os.path.join(out, f"fig15_can_and_cant_say_v1.{ext}"), dpi=300, bbox_inches="tight", facecolor="white")
print("wrote fig15_can_and_cant_say_v1")
