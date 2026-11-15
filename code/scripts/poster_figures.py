"""Poster figures (PNG at 300 dpi + SVG): tank humidity, growth and greenness (mean +/- SD),
and leaf shape (PCA, mean shapes, size of the Low-High shape difference). Days 1-16 data; files end in _v3.
Reads only; writes figures and the numbers behind them to the output folder.
Usage: python poster_figures.py <morpho folder> <out folder>
"""
import csv
import itertools
import os
import sys
from decimal import ROUND_HALF_UP, Decimal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auto_landmarks as A
from growth_allometry import procrustes

root, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

LOW, HIGH, INK, QUIET, GRID = "#1f6fd1", "#8a8a8a", "#222222", "#666666", "#e4e4e4"
COL = {"mh": LOW, "sh": HIGH}
NAME = {"mh": "Low humidity (50% RH)", "sh": "High humidity (80–85% RH)"}
plt.rcParams.update({"font.family": "Arial", "font.size": 11, "axes.edgecolor": QUIET, "axes.labelcolor": INK,
                     "xtick.color": QUIET, "ytick.color": QUIET, "svg.fonttype": "none"})
stats = []   # rows written to figure_numbers_v3.csv
V_OUT = "v3"
LAST = 16


def frame(ax, title, subtitle):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", color=INK, pad=30)
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


LABEL_BOX = dict(facecolor="white", edgecolor="none", pad=1.5)


# ---------- data ----------
spec = list(csv.DictReader(open(os.path.join(root, "3_results", "mh-sh_L01-L11_D01-D16_specimens_v5.csv"), encoding="utf-8")))
colour = list(csv.DictReader(open(os.path.join(root, "3_results", "leaf_colour_v3.csv"), encoding="utf-8")))
growth_win = list(csv.DictReader(open(os.path.join(root, "3_results", "growth_by_window_v5.csv"), encoding="utf-8")))
shape_p = {(r["days"], r["test"]): r for r in csv.DictReader(open(os.path.join(root, "3_results", "shape_tests_v5.csv"), encoding="utf-8"))}
tank = list(csv.DictReader(open(os.path.join(root, "3_results", "tank_conditions", "tank_conditions_daily_v1.csv"), encoding="utf-8")))
me = {r["photo"]: r for r in csv.DictReader(open(os.path.join(root, "3_results", "measurement_error", "measurement_error_v1.csv"), encoding="utf-8"))}

# ---------- 1. tank humidity ----------
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.axhspan(80, 85, color=HIGH, alpha=0.15, linewidth=0)
ax.axhline(50, color=QUIET, linestyle="--", linewidth=1)
ax.text(11.2, 82.5, "High target 80–85%", va="center", fontsize=9.5, color=QUIET)
ax.text(11.2, 47.5, "Low target 50%", va="top", fontsize=9.5, color=QUIET)
for key, label in (("Low", "mh"), ("High", "sh")):
    rows = [r for r in tank if r["tank"].startswith(key)]
    d = np.array([int(r["day"]) for r in rows])
    m = np.array([float(r["rh_mean"]) for r in rows])
    s = np.array([float(r["rh_sd"]) for r in rows])
    ax.fill_between(d, m - s, np.minimum(m + s, 100), color=COL[label], alpha=0.15, linewidth=0)
    ax.plot(d, m, "-o", color=COL[label], markersize=4.5, linewidth=2)
    ax.text(d[-1] + 0.3, m[-1], NAME[label].split(" (")[0], va="center", fontsize=10.5, fontweight="bold", color=COL[label])
    for di, mi, si in zip(d, m, s):
        stats.append(["tank_humidity", label, int(di), "", round(mi, 1), round(si, 1)])
ax.axvline(10.5, color=QUIET, linestyle=":", linewidth=1)
ax.text(10.3, 101.5, "Days 1–10", ha="right", fontsize=9.5, color=QUIET)
ax.text(10.7, 101.5, "Days 11–17: Low tank more humid", ha="left", fontsize=9.5, color=QUIET)
ax.set_xlim(0.5, 17.5)
ax.set_ylim(20, 104)
ax.set_xticks(range(1, 18))
ax.set_xlabel("Experiment day (Day 1 = 21 Sep 2026)")
ax.set_ylabel("Relative humidity (%)")
frame(ax, "The tanks held 54% vs 90% humidity on Days 1–10; the gap narrowed afterwards",
      "Daily mean ± SD of hourly sensor readings (DHT1 taken as the High tank)")
save(fig, "fig1_tank_humidity_" + V_OUT)

# ---------- 2. growth over time (mean +/- SD of size relative to first photo) ----------
by_leaf = {}
for r in spec:
    by_leaf.setdefault((r["condition"], r["leaf"]), []).append((int(r["days_since_first_photo"]), float(r["centroid_size_mm"])))
rel = {}   # (cond, t) -> list of % of first photo
for (c, l), v in by_leaf.items():
    if len(v) < 2:
        continue
    v.sort()
    for t, mm in v:
        rel.setdefault((c, t), []).append(100 * mm / v[0][1])
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.axhline(100, color=QUIET, linestyle="--", linewidth=1)
ends = {}
for c, dx in (("mh", -0.08), ("sh", 0.08)):
    ts = [t for t in range(0, LAST) if len(rel.get((c, t), [])) >= 3]
    m = np.array([np.mean(rel[(c, t)]) for t in ts])
    s = np.array([sd(rel[(c, t)]) for t in ts])
    ax.errorbar(np.array(ts) + dx, m, yerr=s, fmt="-o", color=COL[c], markersize=6, capsize=4, linewidth=2, label=NAME[c])
    ends[c] = (ts[-1], m[-1])
    for t, mi, si in zip(ts, m, s):
        stats.append(["growth_over_time", c, t, len(rel[(c, t)]), round(mi, 2), round(si, 2)])
    for t in ts:
        ax.text(t, -0.20 if c == "mh" else -0.26, str(len(rel[(c, t)])), transform=ax.get_xaxis_transform(),
                ha="center", fontsize=9, color=COL[c])
ax.text(-0.6, -0.20, "Low leaves", transform=ax.get_xaxis_transform(), ha="right", fontsize=9, color=LOW)
ax.text(-0.6, -0.26, "High leaves", transform=ax.get_xaxis_transform(), ha="right", fontsize=9, color=HIGH)
ax.set_xlim(-0.5, max(ends["mh"][0], ends["sh"][0]) + 0.5)
ax.set_xlabel("Days since the leaf's first photo")
ax.set_ylabel("Leaf size (% of first photo)")
ax.legend(frameon=False, loc="upper left")
t_cmp = min(ends["mh"][0], ends["sh"][0])
lo, hi = np.mean(rel[("mh", t_cmp)]) - 100, np.mean(rel[("sh", t_cmp)]) - 100
early = 5
e_lo, e_hi = np.mean(rel[("mh", early)]) - 100, np.mean(rel[("sh", early)]) - 100
title2 = (f"High-humidity leaves grew faster at first ({e_hi:.0f}% vs {e_lo:.0f}% after {early} days); "
          f"after {t_cmp} days both were about {(hi + lo) / 2:.0f}% larger" if abs(hi - lo) < 3 and e_hi > e_lo else
          f"After {t_cmp} days, High-humidity leaves were {hi:.0f}% larger and Low-humidity leaves {lo:.0f}% larger")
frame(ax, title2,
      "Centroid size relative to each leaf's first photo, mean ± SD; days with 3+ leaves (counts below; leaves drop out when replaced)")
save(fig, "fig2_growth_over_time_" + V_OUT)

# ---------- 3. growth rate per leaf, Days 1-10 and Days 11-16 ----------
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.8), sharey=True)
pg = {}
for ax, win, lab in ((axes[0], "1-10", "Days 1–10"), (axes[1], "11-16", "Days 11–16")):
    rows_w = [r for r in growth_win if r["days"] == win]
    gv = np.array([float(r["growth_pct_per_day"]) for r in rows_w])
    gc = np.array([r["condition"] for r in rows_w])
    _, pg[lab] = perm_diff(gv, gc)
    ax.axhline(0, color=QUIET, linestyle="--", linewidth=1)
    for i, c in enumerate(("mh", "sh")):
        m, sdv = strip(ax, i, gv[gc == c], COL[c])
        ax.text(i + 0.32, m, f"{m:+.1f} ± {sdv:.1f}", va="center", fontsize=10, color=INK, bbox=LABEL_BOX, zorder=5)
        stats.append(["growth_rate_per_leaf", c, lab, int((gc == c).sum()), round(m, 2), round(sdv, 2)])
    ax.set_xticks([0, 1], ["Low humidity", "High humidity"])
    ax.set_xlim(-0.5, 1.85)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(f"{lab}: p = {pg[lab]:.3f}", fontsize=12, color=INK)
axes[0].set_ylabel("Growth (% size change per day)")
fig.suptitle("Leaves grew faster in High humidity on Days 1–10 and in Low humidity on Days 11–16 (neither significant)"
             if max(pg.values()) >= 0.05 else "Growth per leaf, Days 1–10 and Days 11–16", x=0.06, ha="left",
             fontsize=13, fontweight="bold", color=INK)
fig.text(0.06, 0.885, "Dots = leaves with 3+ photos in that window; black = mean ± SD; exact permutation test. "
         "The Low tank was more humid from Day 11", fontsize=10, color=QUIET)
fig.subplots_adjust(top=0.78)
save(fig, "fig3_growth_rate_per_leaf_" + V_OUT)
print("growth exact p:", {k: round(v, 3) for k, v in pg.items()})

# ---------- 4. greenness over time ----------
fig, ax = plt.subplots(figsize=(8, 4.6))
for c, dx in (("mh", -0.1), ("sh", 0.1)):
    days = sorted({int(r["day"]) for r in colour if r["condition"] == c})
    vals = [[float(r["gcc"]) for r in colour if r["condition"] == c and int(r["day"]) == d] for d in days]
    m = np.array([np.mean(v) for v in vals])
    s = np.array([sd(v) for v in vals])
    ax.errorbar(np.array(days) + dx, m, yerr=np.nan_to_num(s), fmt="-o", color=COL[c], markersize=6, capsize=4,
                linewidth=2, label=NAME[c])
    for d, v, mi, si in zip(days, vals, m, s):
        stats.append(["greenness_over_time", c, d, len(v), round(mi, 4), round(si, 4)])
ax.text(5, 0.383, "Day 5: glare on 4 Low photos", fontsize=9, color=QUIET, ha="center", va="center")
ax.axvline(10.5, color=QUIET, linestyle=":", linewidth=1)
ax.text(10.7, 0.383, "Low tank more humid from Day 11", fontsize=9, color=QUIET, va="center")
ax.set_xticks(range(1, LAST + 1))
ax.set_xlabel("Experiment day")
ax.set_ylabel("Greenness (green share of colour)")
ax.legend(frameon=False, loc="upper right", ncol=2)
ax.set_ylim(0.37, 0.66)
fig4 = (fig, ax)   # titled and saved after the per-leaf tests below

# ---------- 5. greenness per leaf: Day 1 vs Days 2-10 ----------
def leaf_means(day_ok):
    acc = {}
    for r in colour:
        if day_ok(int(r["day"])):
            acc.setdefault((r["condition"], r["leaf"]), []).append(float(r["gcc"]))
    keys = sorted(acc)
    return np.array([np.mean(acc[k]) for k in keys]), np.array([k[0] for k in keys])

fig, ax = plt.subplots(figsize=(9.4, 4.8))
ps = {}
for j, (label, ok) in enumerate((("Day 1", lambda d: d == 1), ("Days 2–10", lambda d: 2 <= d <= 10), ("Days 11–16", lambda d: d >= 11))):
    v, g = leaf_means(ok)
    _, ps[label] = perm_diff(v, g)
    for i, c in enumerate(("mh", "sh")):
        m, s = strip(ax, j * 2.4 + i, v[g == c], COL[c])
        ax.text(j * 2.4 + i + 0.32, m, f"{m:.3f}\n± {s:.3f}", va="center", fontsize=9, color=INK)
        stats.append(["greenness_per_leaf", c, label, int((g == c).sum()), round(m, 4), round(s, 4)])
    ax.text(j * 2.4 + 0.5, 0.385, f"{label}\np = {ps[label]:.3f}", ha="center", va="bottom", fontsize=10.5, color=INK)
ax.set_xticks([0, 1, 2.4, 3.4, 4.8, 5.8], ["Low", "High"] * 3)
ax.set_xlim(-0.5, 6.5)
ax.set_ylim(0.38, 0.64)
ax.set_ylabel("Greenness (leaf average)")
p2, p3 = ps["Days 2–10"], ps["Days 11–16"]
title5 = ("Equal on Day 1, less green in Low humidity on Days 2–10" + (" and 11–16" if p3 < 0.05 else "; no clear gap on Days 11–16")
          if p2 < 0.05 else "Greenness per leaf: Day 1, Days 2–10 and Days 11–16")
frame(ax, title5, "Dots = one average per leaf; black = mean ± SD; exact permutation test between leaves")
save(fig, "fig5_greenness_per_leaf_" + V_OUT)
print("greenness exact p:", {k: round(float(v), 4) for k, v in ps.items()})
fig, ax = fig4
title4 = ("Low-humidity leaves were less green on Days 2–10" + ("" if p3 < 0.05 else "; the gap closed on Days 11–16")
          if p2 < 0.05 else "Leaf greenness by day")
frame(ax, title4, "Greenness = G / (R + G + B), white-balanced to the grid paper; daily mean ± SD across leaves")
save(fig, "fig4_greenness_over_time_" + V_OUT)

# ---------- shape: Procrustes, PCA, mean shapes ----------
R = A.read_tps(os.path.join(root, "2_landmarks", "mh-sh_L01-L11_D01-D16_combined_v5.tps"))
ids = [r["fields"]["ID"] for r in R]
cond = np.array([i[:2] for i in ids])
leaf = np.array([i[:6] for i in ids])
day = np.array([int(i[-2:]) for i in ids])
V = procrustes(np.array([[complex(*p) for p in r["pts"]] for r in R]))
Z = V[:, :13] + 1j * V[:, 13:]
dist = lambda a, b: float(np.sqrt((np.abs(a - b) ** 2).sum()))

# 6. PCA of all photos
C = V - V.mean(0)
_, sv, Wt = np.linalg.svd(C, full_matrices=False)
var = sv ** 2 / (sv ** 2).sum()
S = C @ Wt[:2].T
fig, ax = plt.subplots(figsize=(6.6, 5.6))
for l in sorted(set(leaf)):
    s = leaf == l
    c = l[:2]
    cx, cy = S[s, 0].mean(), S[s, 1].mean()
    for x, y in S[s]:
        ax.plot([cx, x], [cy, y], color=COL[c], alpha=0.35, linewidth=0.8, zorder=1)
    ax.scatter(S[s, 0], S[s, 1], s=16, color=COL[c], alpha=0.55, linewidth=0, zorder=2)
    ax.scatter(cx, cy, s=70, color=COL[c], edgecolor="white", linewidth=1.2, zorder=3)
for c in ("mh", "sh"):
    ax.scatter([], [], s=70, color=COL[c], label=NAME[c])
ax.axhline(0, color=GRID, linewidth=0.8, zorder=0)
ax.axvline(0, color=GRID, linewidth=0.8, zorder=0)
ax.set_xlabel(f"PC1 ({100 * var[0]:.0f}% of shape variation)")
ax.set_ylabel(f"PC2 ({100 * var[1]:.0f}%)")
ax.legend(frameon=False, loc="best", fontsize=10)
frame(ax, "Shape differs mostly between leaves; Low and High leaves overlap",
      f"PCA of Procrustes shapes, {len(R)} photos (Days 1–16); big dot = leaf average, small dots = its daily photos")
save(fig, "fig6_shape_pca_" + V_OUT)

# 7. mean shapes (average of leaf averages, as in MorphoJ's averaged dataset)
leaves = sorted(set(leaf))
LM = {l: Z[leaf == l].mean(0) for l in leaves}
G = {c: np.mean([LM[l] for l in leaves if l[:2] == c], axis=0) for c in ("mh", "sh")}
grand = (G["mh"] + G["sh"]) / 2
rot = np.exp(1j * (np.pi / 2 - np.angle(grand[1] - grand[0])))   # hub -> landmark 2 points up
fig, axes = plt.subplots(1, 2, figsize=(9, 4.8))
for ax, mag, sub in ((axes[0], 1, "Actual average shapes"), (axes[1], 5, "Difference magnified 5×")):
    for c, ls in (("sh", "-"), ("mh", "-")):
        z = (grand + mag * (G[c] - grand)) * rot
        ring = np.append(z[1:], z[1])
        ax.plot(ring.real, ring.imag, ls, color=COL[c], linewidth=2.2 if c == "mh" else 3.2, alpha=0.95 if c == "mh" else 0.6,
                label=NAME[c])
        ax.scatter(z.real, z.imag, s=18, color=COL[c], zorder=3)
        ax.scatter(z[0].real, z[0].imag, s=60, marker="x", color=COL[c], zorder=4)
    if mag == 1:
        z = grand * rot
        for k in range(13):
            ax.text(z[k].real * (1.12 if k else 1) + (0.012 if k == 0 else 0), z[k].imag * (1.12 if k else 1) - (0.03 if k == 0 else 0),
                    str(k + 1), fontsize=8.5, color=QUIET, ha="center", va="center")
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(sub, fontsize=11, color=INK)
axes[0].legend(frameon=False, loc="lower center", bbox_to_anchor=(1.1, -0.12), ncol=2, fontsize=10)
d_groups = dist(G["mh"], G["sh"])
p_shape = float(shape_p[("Days 1-16", "mean shape Low vs High (leaf averages)")]["p"])
fig.suptitle(f"Average leaf shape barely differed (Procrustes distance {d_groups:.3f}, p = {p_shape:.2f}; Days 1–16)", x=0.05, ha="left",
             fontsize=14, fontweight="bold", color=INK)
fig.text(0.05, 0.89, "Landmark 1 (×) = vein hub; 2–13 = clock points on the edge; each tank's shape = average of its leaf averages",
         fontsize=10, color=QUIET)
save(fig, "fig7_mean_shapes_" + V_OUT)

# 8. how big the Low-High difference is next to other differences
d2d = []
for l in leaves:
    ix = np.where(leaf == l)[0]
    ix = ix[np.argsort(day[ix])]
    d2d += [dist(Z[i], Z[j]) for i, j in zip(ix[:-1], ix[1:]) if day[j] - day[i] == 1]
between = [dist(LM[a], LM[b]) for c in ("mh", "sh") for ia, a in enumerate(leaves) for b in leaves[ia + 1:]
           if a[:2] == c and b[:2] == c]
me_mean = float(Decimal(me["ALL"]["shape_distance_between_repeats_mean"]).quantize(Decimal("0.001"), ROUND_HALF_UP))
bars = [("Measuring the same photo again", me_mean, HIGH),
        ("Low vs High humidity (average shapes)", d_groups, LOW),
        ("Same leaf, one day apart", float(np.mean(d2d)), HIGH),
        ("Two different leaves in the same tank", float(np.median(between)), HIGH)]
fig, ax = plt.subplots(figsize=(8, 3.6))
for k, (lab, v, colr) in enumerate(bars):
    ax.barh(k, v, color=colr, height=0.6)
    ax.text(v + 0.001, k, f"{v:.3f}", va="center", fontsize=10.5, color=INK)
    stats.append(["shape_distances", lab, "", "", round(v, 4), ""])
ax.set_yticks(range(len(bars)), [b[0] for b in bars])
ax.invert_yaxis()
ax.set_xlabel("Procrustes distance (0 = identical shapes)")
ax.grid(axis="x", color=GRID, linewidth=0.8)
ax.grid(axis="y", visible=False)
ax.set_axisbelow(True)
ax.spines[["top", "right"]].set_visible(False)
ax.set_xlim(0, max(b[1] for b in bars) * 1.15)
ax.set_title("The humidity difference in shape is smaller than natural day-to-day change", loc="left",
             fontsize=14, fontweight="bold", color=INK, pad=30)
ax.text(0, 1.04, "Shape differences measured in this study (mean for photos, median for leaf pairs)", transform=ax.transAxes,
        fontsize=10, color=QUIET, va="bottom")
save(fig, "fig8_shape_distances_" + V_OUT)
print(f"shape: mh-sh {d_groups:.4f}, day-to-day {np.mean(d2d):.4f} (n={len(d2d)}), between leaves median {np.median(between):.4f}, "
      f"PC1 {var[0]:.3f} PC2 {var[1]:.3f} PC3 {var[2]:.3f}")

with open(os.path.join(out, f"figure_numbers_{V_OUT}.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["figure", "group", "x", "n", "mean_or_value", "sd"])
    w.writerows(stats)
print(f"wrote figure_numbers_{V_OUT}.csv")
