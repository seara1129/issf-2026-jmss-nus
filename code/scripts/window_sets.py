"""Two matching sets of results, Days 1-10 and Days 11-16 (the Low tank became more humid from Day 11), plus a
before/after comparison of the leaves photographed in both windows.

Per window, Low (mh) vs High (sh), one value per leaf, exact permutation test on every split of the leaves, and a 95%
confidence interval for the difference (the same test inverted):
  humidity      tank mean of hourly sensor readings (descriptive, no test)
  greenness     leaf mean GCC; set 1 uses Days 2-10 (Day 1 was before the treatment could act)
  size growth   slope of ln(centroid size) per day, % per day (leaves with 3+ photos in the window)
  area growth   slope of ln(leaf area) per day, % per day (3+ photos)
  leaf area     leaf mean area in mm2 (descriptive: which leaves were tagged, not a treatment effect)
  roundness     leaf mean 4*pi*area/perimeter^2, hand-traced outlines left out (their zig-zag adds length)
  shape         Procrustes distance between the tanks' mean shapes (leaf averages)
Before/after: change per leaf (Days 11-16 minus Days 1-10) for leaves with 3+ photos in both windows; Low's change vs High's change
(exact test), so a change that happened in both tanks (leaf age, weather) is not credited to the Low tank's humidity.
Usage: python window_sets.py <morpho folder> <out results csv> <out before-after csv> <figure folder>
Writes fig17_days1-10_v1, fig18_days11-16_v1, fig19_low_tank_before_after_v1 (.png/.svg).
"""
import csv
import itertools
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import auto_landmarks as A
from growth_allometry import procrustes

root, out_csv, ba_csv, figdir = sys.argv[1:5]
res = os.path.join(root, "3_results")
LOW, HIGH, INK, QUIET, GRID = "#1f6fd1", "#8a8a8a", "#222222", "#666666", "#e4e4e4"
COL = {"mh": LOW, "sh": HIGH}
plt.rcParams.update({"font.family": "Arial", "font.size": 11, "axes.edgecolor": QUIET, "axes.labelcolor": INK,
                     "xtick.color": QUIET, "ytick.color": QUIET, "svg.fonttype": "none"})
WINDOWS = {"Days 1-10": (1, 10), "Days 11-16": (11, 16)}


# ---------- tests ----------
def splits(n, k):
    W = []
    for idx in itertools.combinations(range(n), k):
        w = np.full(n, -1.0 / (n - k))
        w[list(idx)] = 1.0 / k
        W.append(w)
    return np.array(W)


def exact(v, low):
    """Exact permutation p and 95% CI (test inversion) for mean(low) - mean(rest)."""
    v = np.asarray(v, float)
    W = splits(len(v), int(low.sum()))
    obs = v[low].mean() - v[~low].mean()
    p = float(np.mean(np.abs(W @ v) >= abs(obs) - 1e-12))
    s = np.std(v, ddof=1)
    deltas = np.linspace(obs - 6 * s, obs + 6 * s, 4001)
    V = v[:, None] - np.outer(low.astype(float), deltas)
    keep = np.mean(np.abs(W @ V) >= np.abs(obs - deltas) - 1e-12, axis=0) > 0.05
    return obs, p, deltas[keep].min(), deltas[keep].max()


def slope_pct(days, vals):
    return 100 * np.polyfit(days, np.log(vals), 1)[0]


# ---------- data ----------
spec = list(csv.DictReader(open(os.path.join(res, "mh-sh_L01-L11_D01-D16_specimens_v5.csv"), encoding="utf-8")))
colour = list(csv.DictReader(open(os.path.join(res, "leaf_colour_v3.csv"), encoding="utf-8")))
area = list(csv.DictReader(open(os.path.join(res, "leaf_area_perimeter_v3.csv"), encoding="utf-8")))
hourly = list(csv.DictReader(open(os.path.join(res, "tank_conditions", "tank_conditions_hourly_v1.csv"), encoding="utf-8")))


def per_leaf(rows, value, lo, hi, min_n=1, exclude=None):
    acc = {}
    for r in rows:
        d = int(r["day"])
        if lo <= d <= hi and not (exclude and exclude(r)):
            acc.setdefault((r["condition"], r["leaf"]), []).append((d, value(r)))
    return {k: v for k, v in acc.items() if len(v) >= min_n}


def window_values(lo, hi):
    """measure -> {(cond, leaf): value} for one window."""
    g_lo = max(lo, 2)
    out = {
        "greenness": {k: np.mean([x for _, x in v]) for k, v in per_leaf(colour, lambda r: float(r["gcc"]), g_lo, hi).items()},
        "size growth (% per day)": {k: slope_pct(*zip(*v)) for k, v in
                                    per_leaf(spec, lambda r: float(r["centroid_size_mm"]), lo, hi, 3).items()},
        "area growth (% per day)": {k: slope_pct(*zip(*v)) for k, v in per_leaf(area, lambda r: float(r["area_mm2"]), lo, hi, 3).items()},
        "leaf area (mm2)": {k: np.mean([x for _, x in v]) for k, v in per_leaf(area, lambda r: float(r["area_mm2"]), lo, hi).items()},
        "roundness": {k: np.mean([x for _, x in v]) for k, v in
                      per_leaf(area, lambda r: float(r["roundness"]), lo, hi, 1, lambda r: r["outline_source"] == "hand-traced").items()},
    }
    return out


# shape: one Procrustes fit of all 160 photos, leaf averages per window
R = A.read_tps(os.path.join(root, "2_landmarks", "mh-sh_L01-L11_D01-D16_combined_v5.tps"))
ids = np.array([r["fields"]["ID"] for r in R])
V = procrustes(np.array([[complex(*p) for p in r["pts"]] for r in R]))
Z = V[:, :13] + 1j * V[:, 13:]
cons = Z.mean(0)
ROT = np.exp(1j * (np.pi / 2 - np.angle(cons[1] - cons[0])))      # landmark 2 straight above the hub
pday = np.array([int(i[-2:]) for i in ids])
pleaf = np.array([i[:6] for i in ids])


def shape_window(lo, hi):
    s = (pday >= lo) & (pday <= hi)
    leaves = sorted(set(pleaf[s]))
    LM = np.array([Z[s & (pleaf == l)].mean(0) for l in leaves])
    low = np.array([l.startswith("mh") for l in leaves])
    W = splits(len(leaves), int(low.sum()))
    X = np.concatenate([LM.real, LM.imag], axis=1)
    d = np.linalg.norm(W @ X, axis=1)
    obs = np.linalg.norm(X[low].mean(0) - X[~low].mean(0))
    return LM[low].mean(0), LM[~low].mean(0), obs, float(np.mean(d >= obs - 1e-12)), int(low.sum()), int((~low).sum())


rows, results, shapes = [], {}, {}
MDE = {"Days 1-10": 0.032, "Days 11-16": 0.037}                    # from power_ci_v1.csv (random direction)
for wname, (lo, hi) in WINDOWS.items():
    for tank, key in (("Low (mh)", "mh"), ("High (sh)", "sh")):
        h = [r for r in hourly if lo <= int(r["day"]) <= hi and r["tank"].startswith(tank.split()[0])]
        rh = np.array([float(r["rh_pct"]) for r in h])
        vpd = np.array([float(r["vpd_kPa"]) for r in h])
        rows.append([wname, "humidity (% RH, hourly)", key, len(h), round(rh.mean(), 1), round(rh.std(ddof=1), 1), "", "", "", "", ""])
        rows.append([wname, "VPD (kPa, hourly)", key, len(h), round(vpd.mean(), 2), round(vpd.std(ddof=1), 2), "", "", "", "", ""])
    vals = window_values(lo, hi)
    results[wname] = vals
    for m, d in vals.items():
        keys = sorted(d)
        v = np.array([d[k] for k in keys])
        low = np.array([k[0] == "mh" for k in keys])
        diff, p, c0, c1 = exact(v, low)
        dg = 4 if m in ("greenness", "roundness") else 2
        for c, sel in (("mh", low), ("sh", ~low)):
            rows.append([wname + (" (greenness: Days 2-10)" if m == "greenness" and lo == 1 else ""), m, c, int(sel.sum()),
                         round(v[sel].mean(), dg), round(np.std(v[sel], ddof=1), dg),
                         round(diff, dg), round(c0, dg), round(c1, dg), round(p, 4), "" if m != "leaf area (mm2)" else "descriptive"])
    lm, hm, dist, p, nl, nh = shape_window(lo, hi)
    shapes[wname] = (lm, hm, dist, p)
    rows.append([wname, "shape: Procrustes distance between mean shapes", "mh vs sh", f"{nl} vs {nh}", round(dist, 4), "",
                 round(dist, 4), "", "", round(p, 4), f"smallest detectable (80% power) {MDE[wname]}"])

with open(out_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["window", "measure", "tank", "n (leaves, or hours for humidity)", "mean", "sd",
                "difference_low_minus_high", "ci95_low", "ci95_high", "exact_p", "note"])
    w.writerows(rows)

# ---------- before / after, leaves in both windows ----------
ba_rows, ba = [], {}
eligible = set(results["Days 1-10"]["size growth (% per day)"]) & set(results["Days 11-16"]["size growth (% per day)"])  # 3+ photos in both
for m in ("greenness", "size growth (% per day)", "roundness"):
    a, b = results["Days 1-10"][m], results["Days 11-16"][m]
    both = sorted(set(a) & set(b) & eligible)
    ch = np.array([b[k] - a[k] for k in both])
    low = np.array([k[0] == "mh" for k in both])
    diff, p, c0, c1 = exact(ch, low)
    signs = np.array(list(itertools.product([-1, 1], repeat=int(low.sum()))))
    lc = ch[low]
    p_paired = float(np.mean(np.abs((signs * lc).mean(1)) >= abs(lc.mean()) - 1e-12))
    ba[m] = (both, a, b, diff, p, p_paired)
    for k, c in zip(both, ch):
        ba_rows.append([m, k[0], k[1], round(a[k], 4), round(b[k], 4), round(c, 4)])
    ba_rows.append([m, "Low change minus High change", f"{low.sum()} vs {(~low).sum()} leaves", "", "", round(diff, 4),
                    f"95% CI {c0:.4f} to {c1:.4f}", f"exact p = {p:.4f}", f"Low change alone (sign-flip test): p = {p_paired:.4f}"])
with open(ba_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["measure", "tank", "leaf", "days_1_10", "days_11_16", "change", "ci", "p", "note"])
    w.writerows(ba_rows)

# ---------- figures 17 and 18: one per window, same axes ----------
YL = {"greenness": (0.40, 0.62), "size growth (% per day)": (-4.5, 4.8), "area growth (% per day)": (-9, 9), "roundness": (0.83, 1.0)}
UNIT = {"greenness": "Greenness (GCC, leaf average)", "size growth (% per day)": "Size growth (% per day)",
        "area growth (% per day)": "Area growth (% per day)", "roundness": "Roundness (1 = circle)"}


def strip(ax, x0, vals, col):
    vals = np.sort(np.asarray(vals))
    off = np.zeros(len(vals))
    span = (vals.max() - vals.min()) or 1
    for i in range(1, len(vals)):
        if vals[i] - vals[i - 1] < span * 0.06:
            off[i] = -off[i - 1] if off[i - 1] else 0.07
    ax.scatter(x0 + off - 0.08, vals, s=40, color=col, alpha=0.8, edgecolor="white", linewidth=0.8, zorder=3)
    ax.errorbar(x0 + 0.22, vals.mean(), yerr=np.std(vals, ddof=1) if len(vals) > 1 else 0, fmt="o", color=INK,
                markersize=6, capsize=5, linewidth=1.4, zorder=4)


def p_text(p):
    return f"p = {p:.3f}" if p >= 0.001 else "p < 0.001"


for wname, fname in (("Days 1-10", "fig17_days1-10_v1"), ("Days 11-16", "fig18_days11-16_v1")):
    lo, hi = WINDOWS[wname]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9.2))
    ax = axes[0, 0]
    hum = {r[2]: (r[4], r[5]) for r in rows if r[0] == wname and r[1] == "humidity (% RH, hourly)"}
    for i, c in enumerate(("mh", "sh")):
        ax.bar(i, hum[c][0], yerr=hum[c][1], color=COL[c], width=0.55, capsize=6, error_kw={"ecolor": INK, "linewidth": 1.3})
        ax.text(i, hum[c][0] + hum[c][1] + 2, f"{hum[c][0]:.0f}%", ha="center", fontsize=12, fontweight="bold", color=INK)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Relative humidity (%), mean ± SD of hourly readings")
    ax.set_title("Tank humidity", loc="left", fontsize=12, fontweight="bold", color=INK)
    for k, m in enumerate(("greenness", "size growth (% per day)", "area growth (% per day)", "roundness")):
        ax = axes.flat[k + 1]
        d = results[wname][m]
        keys = sorted(d)
        v = np.array([d[x] for x in keys])
        low = np.array([x[0] == "mh" for x in keys])
        _, p, _, _ = exact(v, low)
        for i, c in enumerate(("mh", "sh")):
            sel = low if c == "mh" else ~low
            strip(ax, i, v[sel], COL[c])
            mu = v[sel].mean()
            ax.text(i + 0.36, mu, (f"{mu:.3f}" if m in ("greenness", "roundness") else f"{mu:+.1f}") + f"\n({sel.sum()} leaves)",
                    va="center", fontsize=9, color=INK)
        if "growth" in m:
            ax.axhline(0, color=QUIET, linestyle="--", linewidth=1)
        ax.set_ylim(*YL[m])
        ax.set_ylabel(UNIT[m])
        lab = {"greenness": "Leaf colour" + (" (Days 2–10)" if lo == 1 else ""), "size growth (% per day)": "Leaf size growth",
               "area growth (% per day)": "Leaf area growth", "roundness": "Roundness"}[m]
        ax.set_title(f"{lab}: {p_text(p)}", loc="left", fontsize=12, fontweight="bold", color=LOW if p < 0.05 else INK)
    ax = axes[1, 2]
    lm, hm, dist, p = shapes[wname]
    ringH = np.append((hm * ROT)[1:], (hm * ROT)[1])
    mag = (hm + 5 * (lm - hm)) * ROT
    ringL = np.append(mag[1:], mag[1])
    ax.plot(ringH.real, ringH.imag, color=HIGH, linewidth=4, alpha=0.7, label="High humidity")
    ax.plot(ringL.real, ringL.imag, color=LOW, linewidth=2, label="Low humidity (difference × 5)")
    ax.scatter([(hm * ROT)[0].real], [(hm * ROT)[0].imag], marker="x", color=HIGH, s=60)
    ax.scatter([mag[0].real], [mag[0].imag], marker="x", color=LOW, s=60)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.2), fontsize=9.5)
    ax.set_title(f"Mean shape: distance {dist:.3f}, {p_text(p)}\n(detectable: about {MDE[wname]})", loc="left",
                 fontsize=12, fontweight="bold", color=INK)
    for a in axes.flat[1:5]:
        a.set_xticks([0, 1], ["Low", "High"])
        a.set_xlim(-0.5, 1.95)
    for a in axes.flat[:5]:
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", color=GRID, linewidth=0.8)
        a.set_axisbelow(True)
    if lo == 1:
        a.set_xticks([0, 1], ["Low", "High"])
    axes[0, 0].set_xticks([0, 1], ["Low tank", "High tank"])
    sub = (f"Low tank {hum['mh'][0]:.0f}% vs High {hum['sh'][0]:.0f}% humidity" if lo == 1 else
           f"Low tank rose to {hum['mh'][0]:.0f}% humidity; High {hum['sh'][0]:.0f}%")
    fig.suptitle(f"Set {1 if lo == 1 else 2}: {wname.replace('-', '–')} ({sub})", x=0.01, ha="left", fontsize=15,
                 fontweight="bold", color=INK)
    fig.text(0.01, 0.935, "One value per leaf; black = mean ± SD; exact permutation tests between leaves (blue title = p < 0.05). "
             "Same axes in both sets so they can be compared.", fontsize=10, color=QUIET)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(figdir, f"{fname}.{ext}"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", fname)

# ---------- figure 19: leaves in both windows, before vs after ----------
fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
for ax, m in zip(axes, ("greenness", "size growth (% per day)", "roundness")):
    both, a, b, diff, p, p_paired = ba[m]
    span = max(max(a[k], b[k]) for k in both) - min(min(a[k], b[k]) for k in both)
    for cond in ("mh", "sh"):
        x0 = 0 if cond == "mh" else 2.6
        labs = []
        for k in both:
            if k[0] == cond:
                ax.plot([x0, x0 + 1], [a[k], b[k]], "-o", color=COL[cond], linewidth=1.8, markersize=5, alpha=0.85)
                labs.append([b[k], k[1]])
        labs.sort()
        for i in range(1, len(labs)):                       # keep end labels at least 4% of the range apart
            labs[i][0] = max(labs[i][0], labs[i - 1][0] + 0.045 * span)
        for y, t in labs:
            ax.text(x0 + 1.08, y, t, va="center", fontsize=8.5, color=QUIET)
    ax.set_xticks([0, 1, 2.6, 3.6], ["Days\n1–10", "Days\n11–16", "Days\n1–10", "Days\n11–16"])
    ax.text(0.5, 1.0, "Low tank", transform=ax.get_xaxis_transform(), ha="center", va="bottom", color=LOW, fontweight="bold")
    ax.text(3.1, 1.0, "High tank", transform=ax.get_xaxis_transform(), ha="center", va="bottom", color=HIGH, fontweight="bold")
    if "growth" in m:
        ax.axhline(0, color=QUIET, linestyle="--", linewidth=1)
    ax.set_xlim(-0.4, 4.3)
    ax.set_ylabel(UNIT[m])
    ax.set_title(f"{UNIT[m].split(' (')[0]}: Low changed {'more' if diff > 0 else 'less'} than High by {diff:+.3g}\n"
                 f"{p_text(p)} (Low change vs High change)", loc="left", fontsize=11.5, fontweight="bold",
                 color=LOW if p < 0.05 else INK, pad=22)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
fig.suptitle("The same leaves before and after the Low tank became more humid (Day 11)", x=0.01, ha="left", fontsize=15,
             fontweight="bold", color=INK)
fig.text(0.01, 0.9, "Lines = leaves photographed in both windows (greenness: Days 2–10 vs 11–16). Comparing the Low tank's change with the "
         "High tank's change removes anything that changed in both tanks (leaf age, weather).", fontsize=10, color=QUIET)
fig.tight_layout(rect=(0, 0, 1, 0.88))
for ext in ("png", "svg"):
    fig.savefig(os.path.join(figdir, f"fig19_low_tank_before_after_v1.{ext}"), dpi=300, bbox_inches="tight", facecolor="white")
print("wrote fig19_low_tank_before_after_v1")
for r in rows:
    print(r)
for r in ba_rows:
    print(r)
