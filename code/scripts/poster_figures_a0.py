"""Poster versions of the main figures for the A0 poster: no built-in titles (the poster's headline says it), drawn at
print size (about 28 cm wide) with 20-26 pt text, thicker lines and bigger dots. Same data and numbers as the analysis
files; nothing is recomputed except the average leaf outlines (same method as plan_D17_D26.py).
Colours are the poster's greens (dark = Low humidity, sage = High humidity); backgrounds are transparent.
The shape figure (fig23) is on the poster: all its text is one size and black, matching the poster's caption text at
the width it is placed.
Usage: python poster_figures_a0.py <morpho folder> <version> [name ...] [--editable]
(names, e.g. fig23, limit which figures are saved; --editable also writes each saved figure's picture without text and
its text list for make_figure_pptx.js, see editable_text.py)
Writes 3_results/poster_figures/a0/a0_*_<v>.svg and .png (300 dpi).
"""
import csv
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import auto_landmarks as A
from editable_text import save_editable
from growth_allometry import procrustes

root, ver = sys.argv[1:3]
only = [a for a in sys.argv[3:] if not a.startswith("--")]
editable = "--editable" in sys.argv[3:]
res = os.path.join(root, "3_results")
out = os.path.join(res, "poster_figures", "a0")
os.makedirs(out, exist_ok=True)
LOW, HIGH, INK, QUIET, GRID, ACC = "#406327", "#7f9c65", "#222222", "#555555", "#e2e2e2", "#c0502a"
SHADE = {"A": "#edf1e5", "B": "#f4f0e3", "C": "#d9eac2"}             # C shows on the poster's #e4e9d9
plt.rcParams.update({"font.family": "Arial", "font.size": 22, "axes.labelsize": 24, "xtick.labelsize": 22,
                     "ytick.labelsize": 22, "legend.fontsize": 21, "axes.edgecolor": QUIET, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.linewidth": 1.4, "xtick.major.width": 1.4,
                     "ytick.major.width": 1.4, "xtick.major.size": 7, "ytick.major.size": 7, "svg.fonttype": "none"})
load = lambda name: list(csv.DictReader(open(os.path.join(res, name), encoding="utf-8")))


def save(fig, name):
    if only and not any(o in name for o in only):
        plt.close(fig)
        return
    for ext in ("svg", "png"):
        p = os.path.join(out, f"{name}_{ver}.{ext}")
        if os.path.exists(p):
            raise SystemExit(f"{p} already exists - not overwriting")
        fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.15, transparent=True)
    print("wrote", name)
    if editable:
        save_editable(fig, out, f"{name}_{ver}")
    plt.close(fig)


def clean(ax):
    ax.spines[["top", "right"]].set_visible(False)


def ptxt(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}" if p < 0.1 else f"p = {p:.2f}"


per_leaf = load("plan_D17-D26_per_leaf_v2.csv")
results = load("plan_D17-D26_results_v2.csv")
DIFF = "low_minus_high (shape: distance)"


def result(measure, period):
    return next(r for r in results if r["measure"] == measure and r["period"].startswith(period + " "))


def by_period_plot(measure, ylab, ylim, name, zero=False, fmt="{:+.3f}"):
    fig, ax = plt.subplots(figsize=(11, 6.6))
    labels = {"A": "Days 2–10\n54% vs 90% RH", "B": "Days 11–16\n68% vs 96% RH", "C": "Days 17–26\n52% vs 94% RH"}
    for i, per in enumerate("ABC"):
        ax.axvspan(i - 0.46, i + 0.46, color=SHADE[per], zorder=0, lw=0)
        for t, col, dx in (("mh", LOW, -0.2), ("sh", HIGH, 0.2)):
            v = np.array([float(r["value"]) for r in per_leaf if r["measure"] == measure and r["period"] == per and r["tank"] == t])
            jit = np.linspace(-0.09, 0.09, len(v)) if len(v) > 1 else np.zeros(1)
            ax.scatter(i + dx + jit, v, s=150, color=col, edgecolor="white", linewidth=1.2, zorder=3)
            ax.plot([i + dx - 0.15, i + dx + 0.15], [v.mean()] * 2, color=col, lw=5, zorder=4, solid_capstyle="butt")
        r = result(measure, per)
        txt = fmt.format(float(r[DIFF])).replace("-", "−") + "\n" + ptxt(float(r["exact_p"]))
        ax.text(i, ylim[1] - 0.02 * (ylim[1] - ylim[0]), txt, ha="center", va="top", fontsize=21, color=INK,
                fontweight="bold" if per == "C" else "normal", linespacing=1.15)
    if zero:
        ax.axhline(0, color=QUIET, lw=1.2, zorder=1)
    ax.set_xticks(range(3))
    ax.set_xticklabels([labels[p] for p in "ABC"])
    ax.set_xlim(-0.5, 2.5)
    ax.set_ylim(*ylim)
    ax.set_ylabel(ylab)
    clean(ax)
    ax.scatter([], [], s=150, color=LOW, label="Low humidity (Melbourne-like)")
    ax.scatter([], [], s=150, color=HIGH, label="High humidity (Singapore-like)")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, handletextpad=0.3, columnspacing=1.2)
    ax.text(0, 1.03, "Numbers at the top: Low − High difference", transform=ax.transAxes, ha="left", va="bottom",
            fontsize=19, color=QUIET)
    save(fig, name)


# 1. greenness per leaf by period (fig21)
by_period_plot("greenness (GCC)", "Greenness (GCC, leaf average)", (0.42, 0.62), "a0_fig21_greenness_by_period")
# 2. size growth per leaf by period (new, same style)
by_period_plot("size growth (% per day)", "Size growth (% per day)", (-2.0, 4.0), "a0_growth_by_period", zero=True, fmt="{:+.2f}%")

# 3. shape: average outlines + the difference against the yardsticks (fig23)
R = [r for r in A.read_tps(os.path.join(root, "2_landmarks", "mh-sh_L01-L14_D01-D26_combined_v6.tps")) if int(r["fields"]["ID"][-2:]) >= 2]
ids = np.array([r["fields"]["ID"] for r in R])
V = procrustes(np.array([[complex(*p) for p in r["pts"]] for r in R]))
leaf = np.array([i[:6] for i in ids])
leaves = sorted(l for l in set(leaf) if (leaf == l).sum() >= 3)
LM = np.array([V[leaf == l].mean(0) for l in leaves])
low = np.array([l.startswith("mh") for l in leaves])
Z = LM[:, :13] + 1j * LM[:, 13:]
zl, zh = Z[low].mean(0), Z[~low].mean(0)
rot = np.exp(1j * (np.pi / 2 - np.angle(((zl + zh) / 2)[1] - ((zl + zh) / 2)[0])))
m2 = next(r for r in results if r["role"] == "M2 main")
d, c0, c1 = float(m2[DIFF]), float(m2["ci95_low"]), float(m2["ci95_high"])
FS4, BLACK = 27, "#000000"                       # all text in this figure: caption size where it is placed, black
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.7, 6.4), gridspec_kw=dict(width_ratios=[1, 1.75], wspace=0.1))
for z, col, lab in ((zh, HIGH, f"High humidity\n({(~low).sum()} leaves)"), (zl, LOW, f"Low humidity\n({low.sum()} leaves)")):
    z = (z - z[0]) * rot
    ring = np.append(z[1:], z[1])
    a1.plot(ring.real, ring.imag, color=col, lw=4, label=lab)
    a1.scatter(z[1:].real, z[1:].imag, color=col, s=60, zorder=3)
a1.scatter([0], [0], color=BLACK, s=120, marker="+", linewidths=3, zorder=4)
a1.set_aspect("equal")
a1.axis("off")
a1.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=1, handlelength=1.4, fontsize=FS4,
          labelcolor=BLACK)
for x, lab, col, y in ((0.0115, "measurement\nerror", QUIET, 0.70), (0.030, "one day's change\nin a leaf", ACC, 0.97),
                       (0.063, "two different\nleaves", QUIET, 0.97)):
    a2.axvline(x, ymin=0.34, ymax=y - 0.22, color=col, ls="--", lw=2)   # stops short of its label and the numbers below
    a2.text(x, y, lab, transform=a2.get_xaxis_transform(), ha="center", va="top", fontsize=FS4,
            color=BLACK if col == QUIET else col, linespacing=1.15)    # grey labels black; the limit label keeps its colour
a2.plot([c0, c1], [0.44, 0.44], color=INK, lw=6, solid_capstyle="round", transform=a2.get_xaxis_transform())
a2.scatter([d], [0.44], s=260, color=INK, zorder=3, transform=a2.get_xaxis_transform())
a2.text(d, 0.30, f"tank difference {d:.3f}\n95% range {c0:.3f}–{c1:.3f}", transform=a2.get_xaxis_transform(), ha="center",
        va="top", fontsize=FS4, color=BLACK, linespacing=1.15)
a2.set_xlim(0, 0.072)
a2.set_ylim(0, 1)
a2.set_yticks([])
a2.set_xticks([0, 0.02, 0.04, 0.06])
a2.tick_params(labelsize=FS4, labelcolor=BLACK)
a2.spines[["top", "right", "left"]].set_visible(False)
a2.set_xlabel("Shape difference\n(Procrustes distance)", fontsize=FS4, color=BLACK, linespacing=1.15)
save(fig, "a0_fig23_shape")

# 4. tank humidity, Days 1-26 (fig20)
hourly = load(os.path.join("tank_conditions", "tank_conditions_hourly_v2.csv"))
fig, ax = plt.subplots(figsize=(12, 5.2))
for per, (lo, hi) in {"A": (1, 10), "B": (11, 16), "C": (17, 26)}.items():
    ax.axvspan(lo - 0.5, hi + 0.5, color=SHADE[per], lw=0, zorder=0)
    ax.text((lo + hi) / 2, 103, f"Days {lo}–{hi}", ha="center", va="bottom", fontsize=21, color=INK)
for t, col, lab in (("Low", LOW, "Low humidity tank"), ("High", HIGH, "High humidity tank")):
    H = [r for r in hourly if r["tank"].startswith(t) and 1 <= int(r["day"]) <= 26]
    ax.scatter([int(r["day"]) + int(r["hour"][11:13]) / 24 - 0.5 for r in H], [float(r["rh_pct"]) for r in H], s=10, color=col,
               alpha=0.25, lw=0)
    x = np.arange(1, 27)
    dm = [np.mean([float(r["rh_pct"]) for r in H if int(r["day"]) == d]) if any(int(r["day"]) == d for r in H) else np.nan for d in x]
    ax.plot(x, dm, color=col, lw=4, label=lab)
ax.set_xlim(0.5, 26.5)
ax.set_ylim(0, 112)
ax.set_yticks([0, 25, 50, 75, 100])
ax.set_xlabel("Day")
ax.set_ylabel("Humidity (% RH)")
clean(ax)
ax.legend(frameon=False, loc="lower left", ncol=2)
save(fig, "a0_fig20_tank_humidity")

# 5. leaf lifespans (fig28)
spec = load("mh-sh_L01-L14_D01-D26_specimens_v6.csv")
life = {}
for r in spec:
    life.setdefault((r["condition"], r["leaf"]), []).append(int(r["day"]))
fig, axes = plt.subplots(1, 2, figsize=(12, 6.4), sharex=True, gridspec_kw=dict(wspace=0.16))
for ax, (t, col, lab) in zip(axes, (("mh", LOW, "Low humidity"), ("sh", HIGH, "High humidity"))):
    for per, (lo, hi) in {"A": (1, 10), "B": (11, 16), "C": (17, 26)}.items():
        ax.axvspan(lo - 0.5, hi + 0.5, color=SHADE[per], lw=0, zorder=0)
    keys = sorted((k for k in life if k[0] == t), key=lambda k: (min(life[k]), k[1]))
    for i, k in enumerate(keys):
        dd = sorted(life[k])
        ax.plot([dd[0], dd[-1]], [i, i], color=col, lw=4, alpha=0.6, solid_capstyle="round")
        ax.scatter(dd, [i] * len(dd), color=col, s=26, zorder=3)
        if dd[-1] < 26:
            ax.scatter([dd[-1] + 0.5], [i], marker="|", color=INK, s=220, linewidths=3, zorder=4)
        ax.text(0.1, i, k[1], ha="right", va="center", fontsize=19, color=col)
    early = sum(1 for k in keys if min(life[k]) == 1 and max(life[k]) <= 10)
    ax.set_title(f"{lab}: {early} of 5 starting\nleaves lost by Day 10", loc="left", fontsize=22, color=INK)
    ax.set_ylim(len(keys) - 0.4, -0.7)
    ax.set_yticks([])
    ax.set_xlim(-1.8, 26.9)
    ax.set_xticks([1, 5, 10, 15, 20, 25])
    ax.set_xlabel("Day")
    ax.spines[["top", "right", "left"]].set_visible(False)
save(fig, "a0_fig28_leaf_lifespans")

# 6. day by day: heat and the daily colour gap (fig27, two panels)
colour = load("leaf_colour_v4.csv")
daily = load(os.path.join("tank_conditions", "tank_conditions_daily_v2.csv"))
days = np.arange(1, 27)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 8.2), sharex=True, gridspec_kw=dict(hspace=0.18, height_ratios=[1, 1.1]))
for a in (a1, a2):
    for per, (lo, hi) in {"A": (1, 10), "B": (11, 16), "C": (17, 26)}.items():
        a.axvspan(lo - 0.5, hi + 0.5, color=SHADE[per], lw=0, zorder=0)
    clean(a)
for t, col, lab in (("Low", LOW, "Low humidity tank"), ("High", HIGH, "High humidity tank")):
    tm = {int(r["day"]): float(r["temp_max"]) for r in daily if r["tank"].startswith(t) and int(r["day"]) <= 26}
    a1.plot(days, [tm.get(d, np.nan) for d in days], color=col, lw=4, marker="o", ms=8, label=lab)
a1.axhline(40, color=ACC, ls="--", lw=2)
a1.text(1, 41, "40 °C", color=ACC, fontsize=20, ha="left", va="bottom")
a1.set_ylim(12, 52)
a1.set_ylabel("Daily max (°C)")
a1.legend(frameon=False, loc="lower left", ncol=2, bbox_to_anchor=(0, 1.0))
by = {}
for r in colour:
    if int(r["day"]) >= 2:
        by.setdefault((r["condition"], int(r["day"])), []).append(float(r["gcc"]))
diff = [np.mean(by[("mh", d)]) - np.mean(by[("sh", d)]) if ("mh", d) in by and ("sh", d) in by else np.nan for d in days]
a2.bar(days, diff, width=0.72, color=[LOW if (x == x and x < 0) else HIGH for x in diff])
a2.axhline(0, color=QUIET, lw=1.2)
for per, (lo, hi) in {"A": (2, 10), "B": (11, 16), "C": (17, 26)}.items():
    v = [x for dd, x in zip(days, diff) if lo <= dd <= hi and x == x]
    a2.plot([lo - 0.4, hi + 0.4], [np.mean(v)] * 2, color=INK, lw=3)
    a2.text((lo + hi) / 2, 0.072, f"mean {np.mean(v):+.3f}".replace("-", "−"), ha="center", fontsize=20, color=INK)
a2.set_ylim(-0.1, 0.09)
a2.set_ylabel("Greenness,\nLow − High")
a2.set_xlabel("Day")
a2.set_xlim(0.5, 26.5)
save(fig, "a0_fig27_heat_and_colour_by_day")

# 7. classifier check (fig29)
cl = load("classifier_check_v1.csv")
acc = lambda prefix, unit: next(r for r in cl if r["evaluation"].startswith(prefix) and r["unit"] == unit)
rnd, lp, ll, base = acc("wrong way", "photos"), acc("right way", "photos"), acc("right way", "leaves"), acc("baseline", "photos")
fig, ax = plt.subplots(figsize=(10, 6))
ax.axhspan(float(base["ci95_low"]), float(base["ci95_high"]), color="#ececec", lw=0, zorder=0)
ax.text(2.42, float(base["ci95_high"]) + 0.015, "range of pure guessing", ha="right", va="bottom", fontsize=19, color=QUIET)
bars = [("Photos split\nat random", float(rnd["accuracy"]), ACC), ("Whole leaves\nheld out (photos)", float(lp["accuracy"]), INK),
        ("Whole leaves\nheld out (leaves)", float(ll["accuracy"]), INK)]
for i, (lab, v, c) in enumerate(bars):
    ax.bar(i, v, color=c, width=0.58, zorder=2)
    ax.text(i, 0.05, f"{v:.0%}", ha="center", va="bottom", fontsize=26, color="white", fontweight="bold", zorder=3)
ax.errorbar(2, float(ll["accuracy"]), yerr=[[float(ll["accuracy"]) - float(ll["ci95_low"])], [float(ll["ci95_high"]) - float(ll["accuracy"])]],
            color=QUIET, capsize=8, lw=2.5, zorder=4)
ax.set_xticks(range(3))
ax.set_xticklabels([b[0] for b in bars])
ax.set_ylim(0, 1)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.set_ylabel("Tank guessed right")
clean(ax)
save(fig, "a0_fig29_classifier")
