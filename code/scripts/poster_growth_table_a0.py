"""Poster table (A0): leaf size growth per day in each tank and period, with the exact-test p-value, and the median total
growth of the leaves followed 12 days or more. Same numbers as growth_summary_D01-D26_v1.csv and plan_D17-D26_results_v2.csv.
Usage: python poster_growth_table_a0.py <morpho folder> <version>
Writes 3_results/poster_figures/a0/a0_growth_table_<v>.svg and .png (300 dpi).
"""
import csv
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

root, ver = sys.argv[1:3]
res = os.path.join(root, "3_results")
out = os.path.join(res, "poster_figures", "a0")
LOW, HIGH, INK, QUIET, RULE = "#1f6fd1", "#8a8a8a", "#222222", "#555555", "#cfcfcf"
plt.rcParams.update({"font.family": "Arial", "svg.fonttype": "none"})
summ = list(csv.DictReader(open(os.path.join(res, "growth_summary_D01-D26_v1.csv"), encoding="utf-8")))
plan = list(csv.DictReader(open(os.path.join(res, "plan_D17-D26_results_v2.csv"), encoding="utf-8")))
rate = {(r["period_or_leaf"][0], r["tank"]): float(r["growth_pct_per_day"]) for r in summ if r["table"] == "period"}
pval = {r["period"][0]: float(r["exact_p"]) for r in plan if r["measure"] == "size growth (% per day)"}
totals = {t: np.median([float(r["total_growth_pct"]) for r in summ if r["table"].startswith("leaf") and r["tank"] == t])
          for t in ("Low", "High")}
rows = [("Days 2–10", "A"), ("Days 11–16", "B"), ("Days 17–26", "C")]
fmt = lambda v: f"{v:+.2f}%".replace("-", "−")

fig, ax = plt.subplots(figsize=(8.6, 4.4))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")
X = [2, 40, 66, 92]                                        # column anchors: period | Low | High | p
ax.text(X[0], 90, "Size growth\nper day", fontsize=22, fontweight="bold", color=INK, va="center", linespacing=1.1)
ax.text(X[1], 90, "Low\nhumidity", fontsize=22, fontweight="bold", color=LOW, ha="center", va="center", linespacing=1.1)
ax.text(X[2], 90, "High\nhumidity", fontsize=22, fontweight="bold", color="#6b6b6b", ha="center", va="center", linespacing=1.1)
ax.text(X[3], 90, "p", fontsize=22, fontweight="bold", fontstyle="italic", color=INK, ha="center", va="center")
ax.plot([0, 100], [78, 78], color=INK, lw=2)
for i, (lab, k) in enumerate(rows):
    y = 66 - i * 17
    ax.text(X[0], y, lab, fontsize=24, color=INK, va="center")
    ax.text(X[1], y, fmt(rate[(k, "Low")]), fontsize=24, color=LOW, ha="center", va="center")
    ax.text(X[2], y, fmt(rate[(k, "High")]), fontsize=24, color=INK, ha="center", va="center")
    ax.text(X[3], y, f"{pval[k]:.2f}", fontsize=24, color=INK, ha="center", va="center")
    ax.plot([0, 100], [y - 8.5, y - 8.5], color=RULE, lw=1.2)
tl, th = f"{totals['Low']:+.0f}%", f"{totals['High']:+.0f}%"
ax.text(X[0], 6, f"Median total growth: {tl} in both tanks" if tl == th else f"Median total growth: {tl} (Low), {th} (High)",
        fontsize=20, color=QUIET, va="center")
for ext in ("svg", "png"):
    p = os.path.join(out, f"a0_growth_table_{ver}.{ext}")
    if os.path.exists(p):
        raise SystemExit(f"{p} already exists - not overwriting")
    fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.12)
print("wrote a0_growth_table", {k: round(v, 2) for k, v in rate.items()}, pval, totals)
