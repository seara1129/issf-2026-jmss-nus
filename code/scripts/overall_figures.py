"""Whole-experiment versions (Days 1-16) of the per-leaf growth and greenness figures (fig3 and fig5 show the
day windows). Same style as poster_figures.py; titles are computed from the test results.
Usage: python overall_figures.py <morpho folder> <out folder>
Reads 3_results/growth_by_window_v5.csv and 3_results/leaf_colour_v3.csv; writes fig13/fig14 *_v3.png/.svg
and overall_figure_numbers_v3.csv.
"""
import csv
import itertools
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

root, out = sys.argv[1], sys.argv[2]
LOW, HIGH, INK, QUIET, GRID = "#1f6fd1", "#8a8a8a", "#222222", "#666666", "#e4e4e4"
COL = {"mh": LOW, "sh": HIGH}
plt.rcParams.update({"font.family": "Arial", "font.size": 11, "axes.edgecolor": QUIET, "axes.labelcolor": INK,
                     "xtick.color": QUIET, "ytick.color": QUIET, "svg.fonttype": "none"})
V_OUT = "v3"
LABEL_BOX = dict(facecolor="white", edgecolor="none", pad=1.5)
stats = []


def frame(ax, title, subtitle):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK, pad=30)
    ax.text(0, 1.03, subtitle, transform=ax.transAxes, fontsize=10, color=QUIET, va="bottom")


def save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(out, f"{name}.{ext}"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", name)


def sd(v):
    return float(np.std(v, ddof=1)) if len(v) > 1 else float("nan")


def perm_diff(values, groups):
    """Exact permutation p for the difference in means between mh and sh: every possible split of the leaves."""
    v, g = np.asarray(values, dtype=float), np.asarray(groups)
    n, k = len(v), int((g == "mh").sum())
    obs = v[g == "mh"].mean() - v[g == "sh"].mean()
    hits = total = 0
    for idx in itertools.combinations(range(n), k):
        m = np.zeros(n, bool)
        m[list(idx)] = True
        hits += abs(v[m].mean() - v[~m].mean()) >= abs(obs) - 1e-12
        total += 1
    return obs, hits / total


def strip(ax, x0, vals, color):
    """Dots for single leaves (spread sideways when values are close) and a mean +/- SD bar beside them."""
    vals = np.sort(np.asarray(vals))
    off = np.zeros(len(vals))
    span = (vals.max() - vals.min()) or 1
    for i in range(1, len(vals)):
        if vals[i] - vals[i - 1] < span * 0.06:
            off[i] = -off[i - 1] if off[i - 1] else 0.07
    ax.scatter(x0 + off - 0.08, vals, s=46, color=color, alpha=0.75, edgecolor="white", linewidth=0.8, zorder=3)
    m, s = vals.mean(), sd(vals)
    ax.errorbar(x0 + 0.2, m, yerr=s, fmt="o", color=INK, markersize=7, capsize=6, linewidth=1.6, zorder=4)
    return m, s


res = os.path.join(root, "3_results")
growth = [r for r in csv.DictReader(open(os.path.join(res, "growth_by_window_v5.csv"), encoding="utf-8")) if r["days"] == "1-16"]
colour = list(csv.DictReader(open(os.path.join(res, "leaf_colour_v3.csv"), encoding="utf-8")))

# ---------- 13. growth rate per leaf, Days 1-16 ----------
gv = np.array([float(r["growth_pct_per_day"]) for r in growth])
gc = np.array([r["condition"] for r in growth])
_, pg = perm_diff(gv, gc)
fig, ax = plt.subplots(figsize=(6.4, 4.8))
ax.axhline(0, color=QUIET, linestyle="--", linewidth=1)
means = {}
for i, c in enumerate(("mh", "sh")):
    m, s = strip(ax, i, gv[gc == c], COL[c])
    means[c] = m
    ax.text(i + 0.32, m, f"{m:+.1f} ± {s:.1f}", va="center", fontsize=10, color=INK, bbox=LABEL_BOX, zorder=5)
    stats.append(["growth_rate_per_leaf", c, "Days 1–16", int((gc == c).sum()), round(m, 2), round(s, 2), round(pg, 4)])
ax.set_xticks([0, 1], [f"Low humidity\n({(gc == 'mh').sum()} leaves)", f"High humidity\n({(gc == 'sh').sum()} leaves)"])
ax.set_xlim(-0.5, 1.85)
ax.set_ylabel("Growth (% size change per day)")
faster = "High" if means["sh"] > means["mh"] else "Low"
title = (f"Days 1–16: {faster}-humidity leaves grew a little faster (p = {pg:.2f}, not significant)" if pg >= 0.05
         else f"Days 1–16: {faster}-humidity leaves grew faster (p = {pg:.3f})")
frame(ax, title, "Dots = leaves with 3+ photos; black = mean ± SD; exact permutation test. Day windows: Figure 3")
save(fig, "fig13_growth_rate_days1-16_" + V_OUT)

# ---------- 14. greenness per leaf, Days 1-16 ----------
acc = {}
for r in colour:
    acc.setdefault((r["condition"], r["leaf"]), []).append(float(r["gcc"]))
keys = sorted(acc)
v = np.array([np.mean(acc[k]) for k in keys])
g = np.array([k[0] for k in keys])
_, pc = perm_diff(v, g)
fig, ax = plt.subplots(figsize=(6.4, 4.8))
for i, c in enumerate(("mh", "sh")):
    m, s = strip(ax, i, v[g == c], COL[c])
    ax.text(i + 0.32, m, f"{m:.3f}\n± {s:.3f}", va="center", fontsize=10, color=INK, bbox=LABEL_BOX, zorder=5)
    stats.append(["greenness_per_leaf", c, "Days 1–16", int((g == c).sum()), round(m, 4), round(s, 4), round(pc, 4)])
ax.set_xticks([0, 1], [f"Low humidity\n({(g == 'mh').sum()} leaves)", f"High humidity\n({(g == 'sh').sum()} leaves)"])
ax.set_xlim(-0.5, 1.85)
ax.set_ylabel("Greenness (leaf average, all its photos)")
lower = "Low" if v[g == "mh"].mean() < v[g == "sh"].mean() else "High"
title = (f"Days 1–16: {lower}-humidity leaves were less green (p = {pc:.3f})" if pc < 0.05
         else f"Days 1–16: {lower}-humidity leaves were a little less green (p = {pc:.2f}, not significant)")
frame(ax, title, "Dots = one average per leaf over all its photos, Day 1 included; black = mean ± SD; exact test. Windows: Figure 5")
save(fig, "fig14_greenness_days1-16_" + V_OUT)

with open(os.path.join(out, f"overall_figure_numbers_{V_OUT}.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["figure", "group", "days", "n_leaves", "mean", "sd", "exact_p"])
    w.writerows(stats)
for s in stats:
    print(s)
