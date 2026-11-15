"""Days 17-26 analysis exactly as fixed in 4_docs/analysis_plan_humidity_D17-D26_v1.docx (written 18 Oct 2026,
before any Days 17-26 tank comparison).

Main      M1 colour: leaf-mean greenness (GCC), Days 17-26, Low < High; confirmed if that direction and exact p < 0.05.
          M2 shape: Procrustes distance between the tanks' average shapes (leaf means, Days 2-26); confirmed "same within
             the limit" if the upper end of the 95% bootstrap range (leaves resampled within tank, 2000x) is below 0.030.
Secondary S1 growth (slope of ln centroid size, % per day), Days 17-26.
          S2 Low - High greenness in periods A (Days 2-10), B (11-16), C (17-26) against the humidity gap; picture only.
          S3 roundness Days 11-16 -> 17-26, leaves with 3+ computer-drawn outlines in both periods; picture only, no p.
Exploratory: every measure in every period (forest plot).
Rules: one value per leaf per period; a leaf counts if it has 3+ photos in the period (roundness: 3+ computer-drawn
outlines); Day 1 left out; exact permutation test over every split of the leaves, two-sided; 95% CI by inverting the
same test; smallest detectable difference at 80% power by simulation (same method as power_and_ci.py).
Usage: python plan_D17_D26.py <morpho folder> <version, e.g. v1>
Writes 3_results/plan_D17-D26_results_<v>.csv, plan_D17-D26_per_leaf_<v>.csv, poster_figures/fig20-fig26_*_<v>.png/.svg
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

root, ver = sys.argv[1:3]
res = os.path.join(root, "3_results")
figdir = os.path.join(res, "poster_figures")
OUT_RES = os.path.join(res, f"plan_D17-D26_results_{ver}.csv")
OUT_LEAF = os.path.join(res, f"plan_D17-D26_per_leaf_{ver}.csv")
for p in (OUT_RES, OUT_LEAF):
    if os.path.exists(p):
        raise SystemExit(f"{p} already exists - not overwriting")
RNG = np.random.default_rng(2026)
N_SIM, N_PERM, POWER, N_BOOT, LIMIT, ME = 500, 999, 0.8, 2000, 0.030, 0.0115
PERIODS = {"A": (2, 10), "B": (11, 16), "C": (17, 26)}
PLABEL = {"A": "A  Days 2–10", "B": "B  Days 11–16", "C": "C  Days 17–26"}
HUM_DAYS = {"A": (1, 10), "B": (11, 16), "C": (17, 26)}            # as in the plan's period table
PLAN_GAP = {"A": 36.7, "B": 28.1, "C": 41.3}
LOW, HIGH, INK, QUIET, GRID = "#1f6fd1", "#8a8a8a", "#222222", "#666666", "#e4e4e4"
SHADE = {"A": "#f3f6fb", "B": "#fbf6ee", "C": "#eef6f0"}
plt.rcParams.update({"font.family": "Arial", "font.size": 11, "axes.edgecolor": QUIET, "axes.labelcolor": INK,
                     "xtick.color": QUIET, "ytick.color": QUIET, "svg.fonttype": "none"})

# ---------- data ----------
load = lambda name: list(csv.DictReader(open(os.path.join(res, name), encoding="utf-8")))
spec = load("mh-sh_L01-L14_D01-D26_specimens_v6.csv")
colour = load("leaf_colour_v4.csv")
area = load("leaf_area_perimeter_v4.csv")
hourly = load(os.path.join("tank_conditions", "tank_conditions_hourly_v2.csv"))


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
    keep = []
    for chunk in np.array_split(deltas, 20):
        V = v[:, None] - np.outer(low.astype(float), chunk)
        keep.append(np.mean(np.abs(W @ V) >= np.abs(obs - chunk) - 1e-12, axis=0) > 0.05)
    keep = np.concatenate(keep)
    return obs, p, deltas[keep].min(), deltas[keep].max()


def perm_matrix(n, k):
    M = np.zeros((N_PERM, n))
    for i in range(N_PERM):
        pm = RNG.permutation(n)
        M[i, pm[:k]] = 1.0 / k
        M[i, pm[k:]] = -1.0 / (n - k)
    return M


def mc_p(X, low, M):
    d_obs = np.linalg.norm(X[low].mean(0) - X[~low].mean(0))
    return (np.sum(np.linalg.norm(M @ X, axis=1) >= d_obs - 1e-12) + 1) / (len(M) + 1)


def power_curve(X, low_real, grid, direction):
    X = np.asarray(X, float)
    X = X[:, None] if X.ndim == 1 else X
    base = X.copy()
    for g in (low_real, ~low_real):                                  # remove the observed difference
        base[g] -= X[g].mean(0) - X.mean(0)
    n, k = len(X), int(low_real.sum())
    M = perm_matrix(n, k)
    out = []
    for d in grid:
        hits = 0
        for _ in range(N_SIM):
            low = np.zeros(n, bool)
            low[RNG.choice(n, k, replace=False)] = True
            Y = base.copy()
            Y[low] += d * direction()
            hits += mc_p(Y, low, M) < 0.05
        out.append(hits / N_SIM)
    return np.array(out)


def mde(grid, power):
    i = np.argmax(power >= POWER)
    if power[i] < POWER:
        return float("nan")
    if i == 0:
        return float(grid[0])
    g0, g1, p0, p1 = grid[i - 1], grid[i], power[i - 1], power[i]
    return float(g0 + (POWER - p0) * (g1 - g0) / (p1 - p0))


def scalar_mde(v, low):
    sd = np.sqrt(((v[low] - v[low].mean()) ** 2).sum() + ((v[~low] - v[~low].mean()) ** 2).sum()) / np.sqrt(len(v) - 2)
    grid = np.linspace(0.25, 3.0, 12) * sd
    return mde(grid, power_curve(v, low, grid, lambda: np.array([1.0])))


def slope_pct(days, vals):
    return 100 * np.polyfit(days, np.log(vals), 1)[0]


# ---------- per-leaf values ----------
def per_leaf(rows, value, lo, hi, keep=lambda r: True):
    acc = {}
    for r in rows:
        if lo <= int(r["day"]) <= hi and keep(r):
            acc.setdefault((r["condition"], r["leaf"]), []).append((int(r["day"]), value(r)))
    return {k: v for k, v in acc.items() if len(v) >= 3}


untraced = lambda r: r["outline_source"] != "hand-traced"
MEASURES = {
    "greenness (GCC)": lambda lo, hi: {k: np.mean([x for _, x in v]) for k, v in
                                       per_leaf(colour, lambda r: float(r["gcc"]), lo, hi).items()},
    "size growth (% per day)": lambda lo, hi: {k: slope_pct(*zip(*v)) for k, v in
                                               per_leaf(spec, lambda r: float(r["centroid_size_mm"]), lo, hi).items()},
    "area growth (% per day)": lambda lo, hi: {k: slope_pct(*zip(*v)) for k, v in
                                               per_leaf(area, lambda r: float(r["area_mm2"]), lo, hi).items()},
    "roundness (computer outlines)": lambda lo, hi: {k: np.mean([x for _, x in v]) for k, v in
                                                     per_leaf(area, lambda r: float(r["roundness"]), lo, hi, untraced).items()},
}
ROLE = {("greenness (GCC)", "C"): "M1 main", ("size growth (% per day)", "C"): "S1 secondary"}
results, leafvals, rows = {}, [], []
for m, fn in MEASURES.items():
    for per, (lo, hi) in PERIODS.items():
        d = fn(lo, hi)
        keys = sorted(d)
        v = np.array([d[k] for k in keys])
        low = np.array([k[0] == "mh" for k in keys])
        diff, p, c0, c1 = exact(v, low)
        m80 = scalar_mde(v, low)
        role = ROLE.get((m, per), "S2 secondary (picture)" if m.startswith("greenness") else "exploratory")
        results[(m, per)] = dict(keys=keys, v=v, low=low, diff=diff, p=p, ci=(c0, c1), mde=m80, role=role)
        for k, x in zip(keys, v):
            leafvals.append([m, per, k[0], k[1], round(float(x), 5)])
        rows.append([role, m, PLABEL[per], int(low.sum()), int((~low).sum()), round(v[low].mean(), 5),
                     round(v[~low].mean(), 5), round(diff, 5), round(c0, 5), round(c1, 5), round(p, 4), round(m80, 5), ""])
        print(f"{role:24} {m:30} {per}: Low {v[low].mean():.4f} (n={low.sum()}) High {v[~low].mean():.4f} (n={(~low).sum()}) "
              f"diff {diff:+.4f} CI {c0:+.4f} to {c1:+.4f} p={p:.4f} MDE80 {m80:.4f}", flush=True)

# ---------- shape: one Procrustes fit of every photo on Days 2-26 ----------
R = [r for r in A.read_tps(os.path.join(root, "2_landmarks", "mh-sh_L01-L14_D01-D26_combined_v6.tps"))
     if int(r["fields"]["ID"][-2:]) >= 2]
ids = np.array([r["fields"]["ID"] for r in R])
V = procrustes(np.array([[complex(*p) for p in r["pts"]] for r in R]))
pday = np.array([int(i[-2:]) for i in ids])
pleaf = np.array([i[:6] for i in ids])
Zall = V[:, :13] + 1j * V[:, 13:]
MU = Zall.mean(0)


def leaf_means(lo, hi, min_n=3):
    s = (pday >= lo) & (pday <= hi)
    leaves = sorted(l for l in set(pleaf[s]) if (s & (pleaf == l)).sum() >= min_n)
    X = np.array([V[s & (pleaf == l)].mean(0) for l in leaves])
    return leaves, X, np.array([l.startswith("mh") for l in leaves])


def random_dir():
    z = RNG.normal(size=13) + 1j * RNG.normal(size=13)
    z = z - z.mean()
    z = z - (np.vdot(MU, z) / np.vdot(MU, MU)) * MU
    z = z / np.linalg.norm(z)
    return np.concatenate([z.real, z.imag])


def shape_test(lo, hi, with_mde=False, min_n=3):
    leaves, X, low = leaf_means(lo, hi, min_n)
    obs = float(np.linalg.norm(X[low].mean(0) - X[~low].mean(0)))
    W = splits(len(leaves), int(low.sum()))
    p = float(np.mean(np.linalg.norm(W @ X, axis=1) >= obs - 1e-12))
    iL, iH = np.where(low)[0], np.where(~low)[0]
    boot = np.array([np.linalg.norm(X[RNG.choice(iL, len(iL))].mean(0) - X[RNG.choice(iH, len(iH))].mean(0))
                     for _ in range(N_BOOT)])
    lo95, hi95 = np.percentile(boot, [2.5, 97.5])
    m80 = mde(np.round(np.arange(0.005, 0.0651, 0.005), 3),
              power_curve(X, low, np.round(np.arange(0.005, 0.0651, 0.005), 3), random_dir)) if with_mde else float("nan")
    return dict(leaves=leaves, X=X, low=low, d=obs, p=p, ci=(lo95, hi95), mde=m80)


shape = {"Days 2-26": shape_test(2, 26, True)}
for per, (lo, hi) in PERIODS.items():
    shape[per] = shape_test(lo, hi)
sens = shape_test(2, 10, min_n=1)                                  # leaf-inclusion check for the period A result
for name, s in shape.items():
    role = "M2 main" if name == "Days 2-26" else "exploratory"
    lab = "Days 2-26" if name == "Days 2-26" else PLABEL[name]
    verdict = ""
    if role == "M2 main":
        verdict = (f"CONFIRMED: upper end {s['ci'][1]:.4f} < limit {LIMIT}" if s["ci"][1] < LIMIT
                   else f"NOT CONFIRMED: upper end {s['ci'][1]:.4f} >= limit {LIMIT}; a difference that large cannot be ruled out")
    rows.append([role, "shape: Procrustes distance between tank averages", lab, int(s["low"].sum()), int((~s["low"]).sum()),
                 "", "", round(s["d"], 5), round(s["ci"][0], 5), round(s["ci"][1], 5), round(s["p"], 4),
                 "" if np.isnan(s["mde"]) else round(s["mde"], 5), verdict])
    print(f"{role:24} shape {lab}: {s['low'].sum()} vs {(~s['low']).sum()} leaves, distance {s['d']:.4f}, "
          f"bootstrap 95% {s['ci'][0]:.4f}-{s['ci'][1]:.4f}, exact p={s['p']:.4f}, MDE80 {s['mde']:.4f}  {verdict}", flush=True)

rows.append(["exploratory (inclusion check)", "shape: Procrustes distance between tank averages", "A  Days 2–10, every leaf",
             int(sens['low'].sum()), int((~sens['low']).sum()), '', '', round(sens['d'], 5), round(sens['ci'][0], 5),
             round(sens['ci'][1], 5), round(sens['p'], 4), '',
             'same period counting every leaf (also those with 1-2 photos): the period A shape result depends on which leaves are counted'])
print(f"inclusion check: shape A with every leaf: {sens['low'].sum()} vs {(~sens['low']).sum()}, d {sens['d']:.4f}, p {sens['p']:.4f}")

# ---------- verdict for M1 ----------
m1 = results[("greenness (GCC)", "C")]
ok = m1["diff"] < 0 and m1["p"] < 0.05
for r in rows:
    if r[0] == "M1 main":
        r[-1] = (f"CONFIRMED: Low less green, p = {m1['p']:.4f}" if ok else
                 f"NOT CONFIRMED: difference {m1['diff']:+.4f}, p = {m1['p']:.4f}")

# ---------- S2: colour gap against humidity gap ----------
gap = {}
for per, (lo, hi) in HUM_DAYS.items():
    hs = {r["hour"]: float(r["rh_pct"]) for r in hourly if r["tank"].startswith("High") and lo <= int(r["day"]) <= hi}
    ls = {r["hour"]: float(r["rh_pct"]) for r in hourly if r["tank"].startswith("Low") and lo <= int(r["day"]) <= hi}
    both = sorted(set(hs) & set(ls))
    gap[per] = float(np.mean([hs[h] - ls[h] for h in both]))
    assert abs(round(gap[per], 1) - PLAN_GAP[per]) < 0.051, (per, gap[per])
g = {per: results[("greenness (GCC)", per)]["diff"] for per in PERIODS}
order_ok = g["C"] < g["A"] < g["B"]
rows.append(["S2 secondary (picture)", "colour gap ordering C < A < B (most negative = biggest gap)", "A, B, C", "", "", "", "",
             "", "", "", "", "", f"{'as predicted' if order_ok else 'not as predicted'}: A {g['A']:+.4f}, B {g['B']:+.4f}, "
                                 f"C {g['C']:+.4f}; humidity gaps A {gap['A']:.1f}, B {gap['B']:.1f}, C {gap['C']:.1f} points"])

# ---------- S3: roundness B -> C, leaves with 3+ computer outlines in both ----------
rB = MEASURES["roundness (computer outlines)"](11, 16)
rC = MEASURES["roundness (computer outlines)"](17, 26)
s3 = sorted(set(rB) & set(rC))
for t, name in (("mh", "Low"), ("sh", "High")):
    ch = [rC[k] - rB[k] for k in s3 if k[0] == t]
    rows.append(["S3 secondary (picture)", f"roundness change Days 11-16 -> 17-26, {name} tank", "B to C",
                 len(ch) if t == "mh" else "", len(ch) if t == "sh" else "", "", "", round(float(np.mean(ch)), 5), "", "", "", "",
                 "picture only, no p-value (plan): " + ", ".join(f"{k[1]} {rC[k] - rB[k]:+.4f}" for k in s3 if k[0] == t)])

with open(OUT_RES, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["role", "measure", "period", "n_low_leaves", "n_high_leaves", "low_mean", "high_mean",
                "low_minus_high (shape: distance)", "ci95_low", "ci95_high", "exact_p", "smallest_detectable_80pct", "verdict / note"])
    w.writerows(rows)
with open(OUT_LEAF, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["measure", "period", "tank", "leaf", "value"])
    w.writerows(leafvals)
print("wrote", OUT_RES, OUT_LEAF)


# ---------- figures ----------
def save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(figdir, f"{name}_{ver}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def p_text(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def strip(ax, x, vals, col, w=0.11):
    jit = np.linspace(-w, w, len(vals)) if len(vals) > 1 else np.zeros(1)
    ax.scatter(x + jit, vals, s=34, color=col, alpha=0.85, edgecolor="white", linewidth=0.6, zorder=3)
    ax.plot([x - 0.17, x + 0.17], [np.mean(vals)] * 2, color=col, lw=2.6, zorder=4)


# fig20: tank humidity, Days 1-26
fig, ax = plt.subplots(figsize=(10, 3.6))
for per, (lo, hi) in HUM_DAYS.items():
    ax.axvspan(lo - 0.5, hi + 0.5, color=SHADE[per], zorder=0)
    ax.text((lo + hi) / 2, 104, f"{per}  Days {lo}–{hi}", ha="center", va="bottom", color=INK, fontsize=10)
for tank, col, lab in (("Low", LOW, "Low tank (Melbourne-like)"), ("High", HIGH, "High tank (Singapore-like)")):
    H = [r for r in hourly if r["tank"].startswith(tank) and 1 <= int(r["day"]) <= 26]
    t = np.array([int(r["day"]) + int(r["hour"][11:13]) / 24 - 0.5 for r in H])
    rh = np.array([float(r["rh_pct"]) for r in H])
    ax.scatter(t, rh, s=4, color=col, alpha=0.25, linewidth=0)
    days = sorted({int(r["day"]) for r in H})
    dm = {d: np.mean([float(r["rh_pct"]) for r in H if int(r["day"]) == d]) for d in days}
    x = np.arange(1, 27)
    y = np.array([dm.get(d, np.nan) for d in x])
    ax.plot(x, y, color=col, lw=2.2, label=lab)
ax.annotate("Low-tank sensor\nnot logging", xy=(23.5, 50), xytext=(23.5, 22), ha="center", fontsize=9, color=QUIET,
            arrowprops=dict(arrowstyle="-", color=QUIET, lw=0.8))
ax.set_xlim(0.5, 26.5)
ax.set_ylim(0, 112)
ax.set_xlabel("Day")
ax.set_ylabel("Humidity (% RH)")
ax.set_yticks([0, 25, 50, 75, 100])
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, loc="lower left", fontsize=9.5)
ax.set_title("What the leaves experienced: daily mean humidity (dots: hourly)", loc="left", fontsize=12, color=INK)
save(fig, "fig20_tank_humidity_days1-26")

# fig21: greenness per leaf in A, B, C
fig, ax = plt.subplots(figsize=(9, 4.8))
tag = {"A": "result found here", "B": "Low tank damper", "C": "planned test"}
for i, per in enumerate(PERIODS):
    r = results[("greenness (GCC)", per)]
    ax.axvspan(i - 0.45, i + 0.45, color=SHADE[per], zorder=0)
    strip(ax, i - 0.2, r["v"][r["low"]], LOW)
    strip(ax, i + 0.2, r["v"][~r["low"]], HIGH)
    ax.text(i, 0.632, f"Low − High {r['diff']:+.3f}\n95% CI {r['ci'][0]:+.3f} to {r['ci'][1]:+.3f}\n{p_text(r['p'])}",
            ha="center", va="bottom", fontsize=9.5, color=INK, fontweight="bold" if per == "C" else "normal")
ax.set_xticks(range(3))
ax.set_xticklabels([f"{PLABEL[p]}\n{tag[p]}\n{r0:.0f}% vs {r1:.0f}% humidity" for p, (r0, r1) in
                    zip(PERIODS, ((53.6, 90.2), (68.2, 96.3), (52.4, 94.2)))], fontsize=9.5)
ax.set_ylim(0.40, 0.70)
ax.set_xlim(-0.5, 2.5)
ax.set_ylabel("Greenness (GCC, leaf average)")
ax.spines[["top", "right"]].set_visible(False)
ax.scatter([], [], color=LOW, label="Low tank leaves")
ax.scatter([], [], color=HIGH, label="High tank leaves")
ax.legend(frameon=False, loc="lower left", fontsize=9.5, ncol=2)
ax.set_title("Greenness per leaf (one dot = one leaf; bar = tank mean)", loc="left", fontsize=12, color=INK)
save(fig, "fig21_greenness_by_period")

# fig22: every measure in every period (forest plot)
panels = list(MEASURES) + ["shape"]
fig, axes = plt.subplots(len(panels), 1, figsize=(8, 11), gridspec_kw=dict(hspace=0.8, top=0.94))
for ax, m in zip(axes, panels):
    if m == "shape":
        names = ["A", "B", "C", "Days 2-26"]
        for j, n in enumerate(names):
            s = shape[n]
            main = n == "Days 2-26"
            ax.plot(s["ci"], [j, j], color=INK if main else QUIET, lw=2.4 if main else 1.4)
            ax.scatter([s["d"]], [j], color=INK if main else QUIET, s=40 if main else 24, zorder=3)
        ax.axvline(LIMIT, color="#c0502a", ls="--", lw=1.2)
        ax.text(LIMIT, -0.75, " limit 0.030 (one day's change)", color="#c0502a", fontsize=8.5, ha="left", va="center")
        ax.axvline(ME, color=QUIET, ls=":", lw=1)
        ax.text(ME, -0.75, "measurement error ", color=QUIET, fontsize=8.5, ha="right", va="center")
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(["A", "B", "C", "Days 2–26 (M2)"])
        ax.set_xlim(0, max(0.07, max(s["ci"][1] for s in shape.values()) * 1.1))
        ax.set_title("Shape: distance between tank averages, bootstrap 95% range", loc="left", fontsize=10.5, color=INK, pad=16)
        ax.set_ylim(len(names) - 0.5, -1.0)
    else:
        for j, per in enumerate(PERIODS):
            r = results[(m, per)]
            main = r["role"].startswith(("M1", "S1"))
            col = INK if main else QUIET
            ax.plot(r["ci"], [j, j], color=col, lw=2.4 if main else 1.4)
            ax.scatter([r["diff"]], [j], color=col, s=40 if main else 24, zorder=3)
        ax.axvline(0, color=QUIET, lw=0.8)
        ax.set_yticks(range(3))
        ax.set_yticklabels([f"{p}{' (M1)' if m.startswith('greenness') and p == 'C' else ''}"
                            f"{' (S1)' if m.startswith('size') and p == 'C' else ''}" for p in PERIODS])
        ax.set_title(f"{m}: Low − High, 95% CI", loc="left", fontsize=10.5, color=INK)
    if m != "shape":
        ax.invert_yaxis()
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, lw=0.6)
fig.suptitle("Every measure, every period (A Days 2–10, B 11–16, C 17–26); dark = planned main/secondary test",
             x=0.02, ha="left", fontsize=11.5, color=INK, y=0.985)
save(fig, "fig22_effect_sizes_all_periods")

# fig23: shape - average outlines and the distance against the limit
s = shape["Days 2-26"]
mz = lambda X: X[:, :13] + 1j * X[:, 13:]
zl, zh = mz(s["X"][s["low"]]).mean(0), mz(s["X"][~s["low"]]).mean(0)
rot = np.exp(1j * (np.pi / 2 - np.angle(((zl + zh) / 2)[1] - ((zl + zh) / 2)[0])))
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.6), gridspec_kw=dict(width_ratios=[1.1, 1]))
for z, col, lab in ((zh, HIGH, f"High tank ({(~s['low']).sum()} leaves)"), (zl, LOW, f"Low tank ({s['low'].sum()} leaves)")):
    z = (z - z[0]) * rot
    ring = np.append(z[1:], z[1])
    a1.plot(ring.real, ring.imag, color=col, lw=2.2, label=lab)
    a1.scatter(z[1:].real, z[1:].imag, color=col, s=16, zorder=3)
    a1.scatter([0], [0], color=col, s=30, marker="x")
a1.set_aspect("equal")
a1.axis("off")
a1.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=9.5)
a1.set_title("Average leaf outline, Days 2–26 (x = hub)", loc="left", fontsize=11, color=INK)
a2.axvspan(0, LIMIT, color="#eef6f0")
a2.plot(s["ci"], [0, 0], color=INK, lw=3)
a2.scatter([s["d"]], [0], color=INK, s=60, zorder=3)
for x, lab, col in ((ME, "measurement\nerror", QUIET), (LIMIT, "limit: one day's\nchange in a leaf", "#c0502a"),
                    (0.063, "typical difference\nbetween two leaves", QUIET)):
    a2.axvline(x, color=col, ls="--", lw=1.1)
    a2.text(x, 0.55, lab, color=col, fontsize=8.5, ha="center", va="bottom",
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5))
a2.text(s["d"], -0.25, f"tank difference {s['d']:.3f}\n95% range {s['ci'][0]:.3f}–{s['ci'][1]:.3f}", ha="center", va="top",
        fontsize=9.5, color=INK, bbox=dict(facecolor="white", edgecolor="none", pad=1.5))
a2.set_ylim(-1, 1.2)
a2.set_xlim(0, 0.075)
a2.set_yticks([])
a2.spines[["top", "right", "left"]].set_visible(False)
a2.set_xlabel("Procrustes distance")
a2.set_title("Shape difference between tanks vs the limit", loc="left", fontsize=11, color=INK)
save(fig, "fig23_shape_within_limit")

# fig24: colour gap against humidity gap
fig, ax = plt.subplots(figsize=(5.6, 4.4))
for per in PERIODS:
    r = results[("greenness (GCC)", per)]
    ax.errorbar(gap[per], r["diff"], yerr=[[r["diff"] - r["ci"][0]], [r["ci"][1] - r["diff"]]], fmt="o", color=INK,
                ecolor=QUIET, capsize=4, ms=7)
    ax.text(gap[per] + 0.6, r["diff"], f" {per}", va="center", fontsize=11, color=INK, fontweight="bold")
ax.axhline(0, color=QUIET, lw=0.8)
ax.set_xlabel("Humidity gap, High − Low (% points)")
ax.set_ylabel("Greenness, Low − High (95% CI)")
ax.spines[["top", "right"]].set_visible(False)
ax.set_xlim(24, 45)
ax.set_title("Does the colour gap follow the humidity gap?", loc="left", fontsize=11.5, color=INK)
save(fig, "fig24_colour_gap_vs_humidity_gap")

# fig25: roundness B -> C, one line per leaf
fig, ax = plt.subplots(figsize=(4.8, 4.6))
lab_y, last = {}, -9.0
for k in sorted(s3, key=lambda k: rC[k]):                          # keep end labels at least 0.004 apart
    last = max(rC[k], last + 0.004)
    lab_y[k] = last
for k in s3:
    col = LOW if k[0] == "mh" else HIGH
    ax.plot([0, 1], [rB[k], rC[k]], color=col, lw=1.8, marker="o")
    ax.text(1.04, lab_y[k], k[1], va="center", fontsize=8.5, color=col)
ax.set_xticks([0, 1])
ax.set_xticklabels(["Days 11–16\n(Low tank damper)", "Days 17–26\n(Low tank dry again)"])
ax.set_xlim(-0.2, 1.25)
ax.set_ylabel("Roundness (1 = circle)")
ax.spines[["top", "right"]].set_visible(False)
ax.plot([], [], color=LOW, label="Low tank")
ax.plot([], [], color=HIGH, label="High tank")
ax.legend(frameon=False, fontsize=9, loc="best")
ax.set_title(f"Roundness, {sum(k[0] == 'mh' for k in s3)} vs {sum(k[0] == 'sh' for k in s3)} leaves\n(picture only: too few leaves to test)",
             loc="left", fontsize=10.5, color=INK)
save(fig, "fig25_roundness_B_to_C")

# fig26: each leaf over 26 days (backup)
fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True, gridspec_kw=dict(hspace=0.25, wspace=0.18))
series = {"greenness": {}, "size": {}}
for r in colour:
    series["greenness"].setdefault((r["condition"], r["leaf"]), []).append((int(r["day"]), float(r["gcc"])))
for r in spec:
    series["size"].setdefault((r["condition"], r["leaf"]), []).append((int(r["day"]), float(r["centroid_size_mm"])))
for row, (meas, ylab) in enumerate((("greenness", "Greenness (GCC)"), ("size", "Leaf size (centroid size, mm)"))):
    for c, (t, col, name) in enumerate((("mh", LOW, "Low tank"), ("sh", HIGH, "High tank"))):
        ax = axes[row, c]
        for per, (lo, hi) in HUM_DAYS.items():
            ax.axvspan(lo - 0.5, hi + 0.5, color=SHADE[per], zorder=0)
        for k, v in sorted(series[meas].items()):
            if k[0] != t:
                continue
            v.sort()
            ax.plot([d for d, _ in v], [x for _, x in v], color=col, lw=1.2, alpha=0.8, marker="o", ms=2.5)
            ax.text(v[-1][0] + 0.25, v[-1][1], k[1], fontsize=7, color=col, va="center")
        ax.spines[["top", "right"]].set_visible(False)
        if row == 0:
            ax.set_title(name, loc="left", fontsize=11.5, color=INK)
        if c == 0:
            ax.set_ylabel(ylab)
        if row == 1:
            ax.set_xlabel("Day")
        ax.set_xlim(0.5, 27.5)
fig.suptitle("Each leaf over 26 days (shading: periods A, B, C)", x=0.02, ha="left", fontsize=12, color=INK)
save(fig, "fig26_each_leaf_days1-26")
print("figures written")
