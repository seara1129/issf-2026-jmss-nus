"""Two descriptive figures for the Days 1-26 story (no new tests; exploratory, labelled as such).
fig27: day by day - each tank's daily maximum temperature, each tank's mean leaf greenness, and Low minus High greenness
       (both tanks are photographed on the same day, so the daily difference cancels lighting that changes from day to day).
fig28: how long each tagged leaf was followed (one dot per photo; the line ends at its last photo).
Usage: python story_figures.py <morpho folder> <version>
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
figdir = os.path.join(res, "poster_figures")
for n in ("fig27_colour_and_heat_by_day", "fig28_leaf_lifespans"):
    if os.path.exists(os.path.join(figdir, f"{n}_{ver}.png")):
        raise SystemExit(f"{n}_{ver} already exists - not overwriting")
LOW, HIGH, INK, QUIET, GRID = "#1f6fd1", "#8a8a8a", "#222222", "#666666", "#e4e4e4"
SHADE = {"A": "#f3f6fb", "B": "#fbf6ee", "C": "#eef6f0"}
PER = {"A": (1, 10), "B": (11, 16), "C": (17, 26)}
plt.rcParams.update({"font.family": "Arial", "font.size": 11, "axes.edgecolor": QUIET, "axes.labelcolor": INK,
                     "xtick.color": QUIET, "ytick.color": QUIET, "svg.fonttype": "none"})
load = lambda name: list(csv.DictReader(open(os.path.join(res, name), encoding="utf-8")))
colour = load("leaf_colour_v4.csv")
spec = load("mh-sh_L01-L14_D01-D26_specimens_v6.csv")
daily = load(os.path.join("tank_conditions", "tank_conditions_daily_v2.csv"))


def shade(ax, labels=False, top=None):
    for p, (lo, hi) in PER.items():
        ax.axvspan(lo - 0.5, hi + 0.5, color=SHADE[p], zorder=0)
        if labels:
            ax.text((lo + hi) / 2, top, f"{p}  Days {lo}–{hi}", ha="center", va="bottom", fontsize=9.5, color=INK)


def save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(figdir, f"{name}_{ver}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------- fig27 ----------
days = np.arange(1, 27)
fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(10, 9), sharex=True, gridspec_kw=dict(hspace=0.28, height_ratios=[1, 1.2, 1]))
for t, col, lab in (("Low", LOW, "Low tank"), ("High", HIGH, "High tank")):
    tm = {int(r["day"]): float(r["temp_max"]) for r in daily if r["tank"].startswith(t) and int(r["day"]) <= 26}
    a1.plot(days, [tm.get(d, np.nan) for d in days], color=col, lw=2, marker="o", ms=3.5, label=lab)
shade(a1, True, 51)
a1.axhline(40, color="#c0502a", ls="--", lw=1)
a1.text(26.4, 40.6, "40 °C", color="#c0502a", fontsize=9, ha="right", va="bottom")
a1.set_ylim(10, 56)
a1.set_ylabel("Daily max\ntemperature (°C)")
a1.legend(frameon=False, loc="lower left", fontsize=9.5, ncol=2)
by = {}
for r in colour:
    if int(r["day"]) >= 2:
        by.setdefault((r["condition"], int(r["day"])), []).append(float(r["gcc"]))
for t, col, lab in (("mh", LOW, "Low tank"), ("sh", HIGH, "High tank")):
    m = [np.mean(by[(t, d)]) if (t, d) in by else np.nan for d in days]
    a2.plot(days, m, color=col, lw=2, marker="o", ms=3.5, label=lab)
shade(a2)
a2.set_ylabel("Mean leaf greenness\n(GCC, all leaves that day)")
diff = [np.mean(by[("mh", d)]) - np.mean(by[("sh", d)]) if ("mh", d) in by and ("sh", d) in by else np.nan for d in days]
a3.bar(days, diff, color=[LOW if (x == x and x < 0) else HIGH for x in diff], width=0.7)
a3.axhline(0, color=QUIET, lw=0.8)
for p, (lo, hi) in PER.items():
    v = [x for d, x in zip(days, diff) if max(lo, 2) <= d <= hi and x == x]
    a3.plot([max(lo, 2) - 0.4, hi + 0.4], [np.mean(v)] * 2, color=INK, lw=1.6)
    a3.text((max(lo, 2) + hi) / 2, 0.075, f"mean {np.mean(v):+.3f}", ha="center", fontsize=9, color=INK)
shade(a3)
a3.set_ylim(-0.11, 0.09)
a3.set_ylabel("Low − High\ngreenness")
a3.set_xlabel("Day (Day 1 = baseline, no colour comparison)")
for a in (a1, a2, a3):
    a.spines[["top", "right"]].set_visible(False)
    a.set_xlim(0.5, 26.5)
fig.suptitle("Day by day: tank heat and leaf colour (descriptive, not a planned test)", x=0.02, ha="left", fontsize=12.5, color=INK, y=0.95)
save(fig, "fig27_colour_and_heat_by_day")

# ---------- fig28 ----------
life = {}
for r in spec:
    life.setdefault((r["condition"], r["leaf"]), []).append(int(r["day"]))
fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharex=True, gridspec_kw=dict(wspace=0.12))
for ax, (t, col, name) in zip(axes, (("mh", LOW, "Low tank"), ("sh", HIGH, "High tank"))):
    shade(ax)
    keys = sorted((k for k in life if k[0] == t), key=lambda k: (min(life[k]), k[1]))
    for i, k in enumerate(keys):
        d = sorted(life[k])
        ax.plot([d[0], d[-1]], [i, i], color=col, lw=2.2, alpha=0.6)
        ax.scatter(d, [i] * len(d), color=col, s=12, zorder=3)
        if d[-1] < 26:
            ax.scatter([d[-1] + 0.45], [i], marker="|", color=INK, s=60, zorder=4)
        ax.text(0.2, i, k[1], ha="right", va="center", fontsize=9, color=col)
    ax.set_ylim(len(keys) - 0.4, -0.8)
    ax.set_yticks([])
    ax.set_xlim(-1.2, 26.8)
    ax.set_xlabel("Day")
    ax.spines[["top", "right", "left"]].set_visible(False)
    early = sum(1 for k in keys if min(life[k]) == 1 and max(life[k]) <= 10)
    first = sum(1 for k in keys if min(life[k]) == 1)
    ax.set_title(f"{name}: {early} of {first} Day-1 leaves ended by Day 10", loc="left", fontsize=11, color=INK)
fig.suptitle("How long each tagged leaf was followed (dot = photo; | = last photo before Day 26)",
             x=0.02, ha="left", fontsize=12, color=INK, y=1.0)
save(fig, "fig28_leaf_lifespans")
print("written")
