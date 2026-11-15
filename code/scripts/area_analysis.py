"""Leaf area, perimeter and roundness: Low (mh) vs High (sh) humidity.
Reads leaf_area_perimeter_v1.csv (from leaf_area.py) and the specimens CSV; writes a per-leaf CSV,
the numbers behind the figures, and three figures (PNG 300 dpi + SVG) in the same style as poster_figures.py.
Days 1-16 data (files end in _v3). Growth = slope of ln(value) against day, as % per day, for leaves with 3+ photos
in the window (Days 1-10 and Days 11-16 separately: the Low tank was more humid from Day 11).
Roundness = 4 pi area / perimeter^2 (1 = perfect circle; ragged, curled or notched edges lower it).
Perimeter and roundness skip the 4 hand-traced outlines (Day 5, Low): a traced outline zig-zags between
clicks, which adds length but hardly changes area, so area keeps them.
p-values: exact permutation tests on one value per leaf (every possible split of the leaves).
Usage: python area_analysis.py <morpho folder> <figure folder>
"""
import csv
import itertools
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root, out = sys.argv[1], sys.argv[2]
res = os.path.join(root, "3_results")
LOW, HIGH, INK, QUIET, GRID = "#1f6fd1", "#8a8a8a", "#222222", "#666666", "#e4e4e4"
COL = {"mh": LOW, "sh": HIGH}
NAME = {"mh": "Low humidity (50% RH)", "sh": "High humidity (80–85% RH)"}
plt.rcParams.update({"font.family": "Arial", "font.size": 11, "axes.edgecolor": QUIET, "axes.labelcolor": INK,
                     "xtick.color": QUIET, "ytick.color": QUIET, "svg.fonttype": "none"})
LABEL_BOX = dict(facecolor="white", edgecolor="none", pad=1.5)
numbers = []


def sd(v):
    return float(np.std(v, ddof=1)) if len(v) > 1 else float("nan")


def exact_p(values, groups):
    v, g = np.asarray(values, float), np.asarray(groups)
    n, k = len(v), int((g == "mh").sum())
    obs = v[g == "mh"].mean() - v[g == "sh"].mean()
    hits = total = 0
    for idx in itertools.combinations(range(n), k):
        m = np.zeros(n, bool)
        m[list(idx)] = True
        hits += abs(v[m].mean() - v[~m].mean()) >= abs(obs) - 1e-12
        total += 1
    return hits / total


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


def strip(ax, x0, vals, color, fmt):
    vals = np.sort(np.asarray(vals, float))
    off = np.zeros(len(vals))
    span = (vals.max() - vals.min()) or 1
    for i in range(1, len(vals)):
        if vals[i] - vals[i - 1] < span * 0.06:
            off[i] = -off[i - 1] if off[i - 1] else 0.07
    ax.scatter(x0 + off - 0.08, vals, s=46, color=color, alpha=0.75, edgecolor="white", linewidth=0.8, zorder=3)
    m, s = vals.mean(), sd(vals)
    ax.errorbar(x0 + 0.2, m, yerr=s, fmt="o", color=INK, markersize=7, capsize=6, linewidth=1.6, zorder=4)
    ax.text(x0 + 0.32, m, fmt(m, s), va="center", fontsize=9.5, color=INK, bbox=LABEL_BOX, zorder=5)
    return m, s


# ---------- data ----------
V_OUT = "v3"
LAST = 16
rows = list(csv.DictReader(open(os.path.join(res, "leaf_area_perimeter_v3.csv"), encoding="utf-8")))
spec = {r["ID"]: r for r in csv.DictReader(open(os.path.join(res, "mh-sh_L01-L11_D01-D16_specimens_v5.csv"), encoding="utf-8"))}
for r in rows:
    for k in ("area_mm2", "perimeter_mm", "roundness", "landmark_gap_pct_radius"):
        r[k] = float(r[k])
    r["day"] = int(r["day"])
    r["cs_mm"] = float(spec[r["ID"]]["centroid_size_mm"])
    r["t"] = int(spec[r["ID"]]["days_since_first_photo"])

gaps = np.array([r["landmark_gap_pct_radius"] for r in rows])
r_cs = np.corrcoef(np.sqrt([r["area_mm2"] for r in rows]), [r["cs_mm"] for r in rows])[0, 1]
print(f"check: landmarks 2-13 lie within {gaps.max():.2f}% of radius of the rebuilt outlines (median {np.median(gaps):.2f}%)")
print(f"check: sqrt(area) vs centroid size r = {r_cs:.3f}")
for c in ("mh", "sh"):
    a = [r["area_mm2"] for r in rows if r["condition"] == c]
    p = [r["perimeter_mm"] for r in rows if r["condition"] == c]
    print(f"  {c}: {len(a)} photos, area {np.mean(a):.0f} mm2 (range {min(a):.0f}-{max(a):.0f}), perimeter {np.mean(p):.0f} mm")

# ---------- per leaf ----------
leaves = {}
for r in rows:
    leaves.setdefault((r["condition"], r["leaf"]), []).append(r)
WINDOWS = {"d1_10": (1, 10), "d11_16": (11, 16), "d1_16": (1, 16)}
per_leaf = []
for (c, l), v in sorted(leaves.items()):
    v.sort(key=lambda r: r["day"])
    d = np.array([r["day"] for r in v])
    va = [r for r in v if r["outline_source"] != "hand-traced"]
    rec = {"leaf": f"{c}_{l}", "condition": c, "n_photos": len(v), "first_day": d.min(), "last_day": d.max(),
           "mean_area_mm2": np.mean([r["area_mm2"] for r in v]), "mean_perimeter_mm": np.mean([r["perimeter_mm"] for r in va])}
    for wk, (a, b) in WINDOWS.items():
        w_all = [r for r in v if a <= r["day"] <= b]
        w_auto = [r for r in va if a <= r["day"] <= b]
        if len(w_all) >= 3:
            rec[f"area_growth_{wk}"] = 100 * np.polyfit([r["day"] for r in w_all], np.log([r["area_mm2"] for r in w_all]), 1)[0]
        if len(w_auto) >= 3:
            rec[f"perimeter_growth_{wk}"] = 100 * np.polyfit([r["day"] for r in w_auto], np.log([r["perimeter_mm"] for r in w_auto]), 1)[0]
    if len(va) >= 3:
        rec["roundness_change_per_day"] = np.polyfit([r["day"] for r in va], [r["roundness"] for r in va], 1)[0]
    for key, ok in (("roundness_day1", lambda x: x == 1), ("roundness_days2_10", lambda x: 2 <= x <= 10),
                    ("roundness_days11_16", lambda x: x >= 11)):
        vals = [r["roundness"] for r in va if ok(r["day"])]
        rec[key] = np.mean(vals) if vals else None
    per_leaf.append(rec)
cols = ["leaf", "condition", "n_photos", "first_day", "last_day", "mean_area_mm2", "mean_perimeter_mm"] + \
       [f"{m}_growth_{wk}" for m in ("area", "perimeter") for wk in WINDOWS] + \
       ["roundness_day1", "roundness_days2_10", "roundness_days11_16", "roundness_change_per_day"]
with open(os.path.join(res, f"area_perimeter_per_leaf_{V_OUT}.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(cols)
    for rec in per_leaf:
        w.writerow(["" if rec.get(k) is None else (round(rec[k], 4) if isinstance(rec[k], float) else rec[k]) for k in cols])

tests = {}
for key in cols[7:]:
    sel = [rec for rec in per_leaf if rec.get(key) is not None]
    v = np.array([rec[key] for rec in sel])
    g = np.array([rec["condition"] for rec in sel])
    if min((g == "mh").sum(), (g == "sh").sum()) < 2:
        continue
    p = exact_p(v, g)
    tests[key] = (v, g, p)
    msg = "  ".join(f"{c}: {v[g == c].mean():+.4g} ± {sd(v[g == c]):.3g} (n={int((g == c).sum())})" for c in ("mh", "sh"))
    print(f"{key:30} {msg}  exact p = {p:.3f}")
    for c in ("mh", "sh"):
        numbers.append(["per_leaf", key, c, int((g == c).sum()), round(v[g == c].mean(), 4), round(sd(v[g == c]), 4), round(p, 4)])

# ---------- fig 9: area over time ----------
rel = {}
for (c, l), v in leaves.items():
    if len(v) < 2:
        continue
    a0 = v[0]["area_mm2"]
    for r in v:
        rel.setdefault((c, r["t"]), []).append(100 * r["area_mm2"] / a0)
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.axhline(100, color=QUIET, linestyle="--", linewidth=1)
ends = {}
for c, dx in (("mh", -0.08), ("sh", 0.08)):
    ts = [t for t in range(LAST) if len(rel.get((c, t), [])) >= 3]
    m = np.array([np.mean(rel[(c, t)]) for t in ts])
    s = np.array([sd(rel[(c, t)]) for t in ts])
    ax.errorbar(np.array(ts) + dx, m, yerr=s, fmt="-o", color=COL[c], markersize=6, capsize=4, linewidth=2, label=NAME[c])
    ends[c] = ts[-1]
    for t, mi, si in zip(ts, m, s):
        numbers.append(["area_over_time", "area_pct_of_first", c, len(rel[(c, t)]), round(mi, 2), round(si, 2), t])
    for t in ts:
        ax.text(t, -0.20 if c == "mh" else -0.26, str(len(rel[(c, t)])), transform=ax.get_xaxis_transform(),
                ha="center", fontsize=9, color=COL[c])
ax.text(-0.6, -0.20, "Low leaves", transform=ax.get_xaxis_transform(), ha="right", fontsize=9, color=LOW)
ax.text(-0.6, -0.26, "High leaves", transform=ax.get_xaxis_transform(), ha="right", fontsize=9, color=HIGH)
ax.set_xlim(-0.5, max(ends.values()) + 0.5)
ax.set_xlabel("Days since the leaf's first photo")
ax.set_ylabel("Leaf area (% of first photo)")
ax.legend(frameon=False, loc="upper left")
t_cmp = min(ends.values())
lo, hi = np.mean(rel[("mh", t_cmp)]) - 100, np.mean(rel[("sh", t_cmp)]) - 100
frame(ax, f"After {t_cmp} days, leaf area had grown {hi:.0f}% in High humidity and {lo:.0f}% in Low humidity",
      "Leaf area (from the outline) relative to each leaf's first photo, mean ± SD; days with 3+ leaves (counts below)")
save(fig, "fig9_area_over_time_" + V_OUT)

# ---------- fig 10: area growth per leaf, Days 1-10 and Days 11-16 ----------
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.8), sharey=True)
for ax, key, lab in ((axes[0], "area_growth_d1_10", "Days 1–10"), (axes[1], "area_growth_d11_16", "Days 11–16")):
    v, g, p = tests[key]
    ax.axhline(0, color=QUIET, linestyle="--", linewidth=1)
    for i, c in enumerate(("mh", "sh")):
        strip(ax, i, v[g == c], COL[c], lambda m, s_: f"{m:+.1f} ± {s_:.1f}")
    ax.set_xticks([0, 1], ["Low humidity", "High humidity"])
    ax.set_xlim(-0.5, 1.85)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(f"{lab}: p = {p:.3f}", fontsize=12, color=INK)
axes[0].set_ylabel("Area growth (% change per day)")
p1, p2_ = tests["area_growth_d1_10"][2], tests["area_growth_d11_16"][2]
def faster(key):
    v, g, _ = tests[key]
    return "High" if v[g == "sh"].mean() > v[g == "mh"].mean() else "Low"
sig = "neither significant" if max(p1, p2_) >= 0.05 else "both significant"
fig.suptitle(f"Leaf area grew faster in {faster('area_growth_d1_10')} humidity on Days 1–10 and in "
             f"{faster('area_growth_d11_16')} humidity on Days 11–16 ({sig})", x=0.06, ha="left", fontsize=13, fontweight="bold", color=INK)
fig.text(0.06, 0.885, "Dots = leaves with 3+ photos in that window; black = mean ± SD; exact permutation test. "
         "The Low tank was more humid from Day 11", fontsize=10, color=QUIET)
fig.subplots_adjust(top=0.78)
save(fig, "fig10_area_growth_" + V_OUT)

# ---------- fig 11: roundness per leaf ----------
fig, ax = plt.subplots(figsize=(9.4, 4.8))
RKEYS = (("roundness_day1", "Day 1"), ("roundness_days2_10", "Days 2–10"), ("roundness_days11_16", "Days 11–16"))
for j, (key, label) in enumerate(RKEYS):
    v, g, p = tests[key]
    for i, c in enumerate(("mh", "sh")):
        strip(ax, j * 2.4 + i, v[g == c], COL[c], lambda m, s: f"{m:.3f}\n± {s:.3f}")
    ax.text(j * 2.4 + 0.5, 0.02, f"{label}\np = {p:.3f}", transform=ax.get_xaxis_transform(), ha="center", va="bottom",
            fontsize=10.5, color=INK)
ax.set_xticks([0, 1, 2.4, 3.4, 4.8, 5.8], ["Low", "High"] * 3)
ax.set_xlim(-0.5, 6.5)
lo_y = min(min(tests[k][0]) for k, _ in RKEYS)
hi_y = max(max(tests[k][0]) for k, _ in RKEYS)
ax.set_ylim(lo_y - 0.35 * (hi_y - lo_y), hi_y + 0.1 * (hi_y - lo_y))
ax.set_ylabel("Roundness, 4π × area / perimeter²")
p2 = min(tests[k][2] for k, _ in RKEYS[1:])
frame(ax, "Leaf roundness: Low vs High humidity" + (" (no clear difference)" if p2 >= 0.05 else ""),
      "1 = perfect circle; ragged, curled or notched edges lower it. Dots = one average per leaf; black = mean ± SD")
save(fig, "fig11_roundness_per_leaf_" + V_OUT)

with open(os.path.join(out, f"area_figure_numbers_{V_OUT}.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["table", "measure", "condition", "n", "mean", "sd", "p_or_day"])
    w.writerows(numbers)
print(f"wrote area_perimeter_per_leaf_{V_OUT}.csv and area_figure_numbers_{V_OUT}.csv")
