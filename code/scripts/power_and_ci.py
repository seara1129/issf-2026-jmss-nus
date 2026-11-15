"""What the results can and can't say: 95% confidence intervals and smallest detectable effects (Low vs High).

1. Confidence intervals for Low - High differences (greenness, growth, area growth; one value per leaf), made by
   inverting the same exact permutation test used for the p-values: the interval holds every shift delta for which
   "Low - delta vs High" is NOT rejected at 5%. So an interval excludes 0 exactly when p < 0.05.
2. Smallest detectable effect (80% power): take the real leaf values, remove the observed group difference (so there
   is no true effect), relabel leaves at random into groups of the real sizes, add an effect of size d to one group,
   and test with 999 random permutations. Power = share of 500 such experiments with p < 0.05; the smallest
   detectable effect is the d where power first reaches 80%. For shape the effect is a shift of the leaf-average
   shapes by Procrustes distance d in a random shape direction (also: along PC1, the hardest direction, and along
   the observed Low-High direction).
Usage: python power_and_ci.py <morpho folder> <out.csv>
"""
import csv
import itertools
import os
import sys

import numpy as np

import auto_landmarks as A
from growth_allometry import procrustes

RNG = np.random.default_rng(2026)
N_SIM, N_PERM, POWER = 500, 999, 0.8
root, out_csv = sys.argv[1:3]
res = os.path.join(root, "3_results")


def split_matrix(n, k):
    """Every way to pick k of n leaves: rows of weights so that W @ v = mean(picked) - mean(rest)."""
    rows = []
    for idx in itertools.combinations(range(n), k):
        w = np.full(n, -1.0 / (n - k))
        w[list(idx)] = 1.0 / k
        rows.append(w)
    return np.array(rows)


def exact_ci(v, low):
    """Exact permutation p and 95% CI for mean(low) - mean(high) by test inversion."""
    v = np.asarray(v, float)
    W = split_matrix(len(v), int(low.sum()))
    obs = v[low].mean() - v[~low].mean()
    p = np.mean(np.abs(W @ v) >= abs(obs) - 1e-12)
    s = np.std(v, ddof=1)
    deltas = np.linspace(obs - 6 * s, obs + 6 * s, 6001)
    keep = []
    for chunk in np.array_split(deltas, 30):
        V = v[:, None] - np.outer(low.astype(float), chunk)          # shift Low by delta
        stat = np.abs(W @ V)
        o = np.abs(obs - chunk)
        keep.append(np.mean(stat >= o - 1e-12, axis=0) > 0.05)
    keep = np.concatenate(keep)
    inside = deltas[keep]
    return obs, p, inside.min(), inside.max()


def perm_matrix(n, k):
    """N_PERM random relabellings as weight rows: M @ X = mean(first k) - mean(rest)."""
    M = np.zeros((N_PERM, n))
    for i in range(N_PERM):
        pm = RNG.permutation(n)
        M[i, pm[:k]] = 1.0 / k
        M[i, pm[k:]] = -1.0 / (n - k)
    return M


def mc_p(X, low, M):
    """Monte Carlo permutation p for the distance between group means (X: leaves x variables)."""
    d_obs = np.linalg.norm(X[low].mean(0) - X[~low].mean(0))
    d = np.linalg.norm(M @ X, axis=1)
    return (np.sum(d >= d_obs - 1e-12) + 1) / (len(M) + 1)


def power_curve(X, groups, grid, direction):
    """Power at each effect size in grid. X: leaves x variables (1 column for a single measure)."""
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    low_real = groups == "mh"
    base = X.copy()
    for g in (low_real, ~low_real):                                     # remove the observed difference
        base[g] -= X[g].mean(0) - X.mean(0)
    n, k = len(X), int(low_real.sum())
    M = perm_matrix(n, k)
    out = []
    for d in grid:
        hits = 0
        for _ in range(N_SIM):
            low = np.zeros(n, bool)
            low[RNG.choice(n, k, replace=False)] = True
            u = direction()
            Y = base.copy()
            Y[low] += d * u
            hits += mc_p(Y, low, M) < 0.05
        out.append(hits / N_SIM)
    return np.array(out)


def mde(grid, power):
    """Smallest effect with power >= 80%, linearly interpolated between grid points."""
    i = np.argmax(power >= POWER)
    if power[i] < POWER:
        return float("nan")
    if i == 0:
        return float(grid[0])
    g0, g1, p0, p1 = grid[i - 1], grid[i], power[i - 1], power[i]
    return float(g0 + (POWER - p0) * (g1 - g0) / (p1 - p0))


rows = []

# ---------- shape ----------
R = A.read_tps(os.path.join(root, "2_landmarks", "mh-sh_L01-L11_D01-D16_combined_v5.tps"))
ids = np.array([r["fields"]["ID"] for r in R])
V = procrustes(np.array([[complex(*p) for p in r["pts"]] for r in R]))
day = np.array([int(i[-2:]) for i in ids])
leaf = np.array([i[:6] for i in ids])
Z = V[:, :13] + 1j * V[:, 13:]
mu = Z.mean(0)


def tangent(z):
    """Project a complex 13-vector onto the shape tangent space at the mean shape and scale to unit length."""
    z = z - z.mean()
    z = z - (np.vdot(mu, z) / np.vdot(mu, mu)) * mu
    z = z / np.linalg.norm(z)
    return np.concatenate([z.real, z.imag])


def random_dir():
    return tangent(RNG.normal(size=13) + 1j * RNG.normal(size=13))


grid = np.round(np.arange(0.005, 0.0651, 0.005), 3)
for lo, hi in ((1, 16), (1, 10), (11, 16)):
    s = (day >= lo) & (day <= hi)
    leaves = sorted(set(leaf[s]))
    LM = np.array([V[s & (leaf == l)].mean(0) for l in leaves])
    g = np.array([l[:2] for l in leaves])
    low = g == "mh"
    obs = float(np.linalg.norm(LM[low].mean(0) - LM[~low].mean(0)))
    dirs = {"random direction": random_dir}
    if (lo, hi) == (1, 16):
        C = LM - LM.mean(0)
        pc1 = np.linalg.svd(C, full_matrices=False)[2][0]
        obs_dir = LM[low].mean(0) - LM[~low].mean(0)
        dirs["along PC1 (hardest)"] = lambda: pc1 / np.linalg.norm(pc1)
        dirs["along the observed Low-High difference"] = lambda: obs_dir / np.linalg.norm(obs_dir)
    for name, fn in dirs.items():
        pw = power_curve(LM, g, grid, fn)
        m = mde(grid, pw)
        print(f"shape Days {lo}-{hi} ({low.sum()} vs {(~low).sum()} leaves), {name}: observed {obs:.4f}; "
              f"80% power at d = {m:.4f}; power by d: " + ", ".join(f"{d:.3f}:{p:.2f}" for d, p in zip(grid, pw)))
        rows.append(["shape (Procrustes distance between mean shapes)", f"Days {lo}-{hi}", int(low.sum()), int((~low).sum()),
                     "", "", round(obs, 4), "", "", "", round(m, 4), name])

# ---------- single measures per leaf ----------
colour = list(csv.DictReader(open(os.path.join(res, "leaf_colour_v3.csv"), encoding="utf-8")))


def colour_means(lo, hi):
    acc = {}
    for r in colour:
        if lo <= int(r["day"]) <= hi:
            acc.setdefault((r["condition"], r["leaf"]), []).append(float(r["gcc"]))
    keys = sorted(acc)
    return np.array([np.mean(acc[k]) for k in keys]), np.array([k[0] for k in keys])


gw = list(csv.DictReader(open(os.path.join(res, "growth_by_window_v5.csv"), encoding="utf-8")))
ap = list(csv.DictReader(open(os.path.join(res, "area_perimeter_per_leaf_v3.csv"), encoding="utf-8")))
measures = []
for lo, hi in ((2, 10), (11, 16), (1, 16)):
    v, g = colour_means(lo, hi)
    measures.append(("greenness (leaf average)", f"Days {lo}-{hi}", v, g, 4))
for w in ("1-10", "11-16", "1-16"):
    sel = [r for r in gw if r["days"] == w]
    measures.append(("growth (% size change per day)", f"Days {w}", np.array([float(r["growth_pct_per_day"]) for r in sel]),
                     np.array([r["condition"] for r in sel]), 2))
for col, w in (("area_growth_d1_10", "1-10"), ("area_growth_d11_16", "11-16"), ("area_growth_d1_16", "1-16")):
    sel = [r for r in ap if r[col]]
    measures.append(("area growth (% per day)", f"Days {w}", np.array([float(r[col]) for r in sel]),
                     np.array([r["condition"] for r in sel]), 2))
for name, win, v, g, dg in measures:
    low = g == "mh"
    obs, p, c0, c1 = exact_ci(v, low)
    sd = np.sqrt(((v[low] - v[low].mean()) ** 2).sum() + ((v[~low] - v[~low].mean()) ** 2).sum()) / np.sqrt(len(v) - 2)
    sgrid = np.linspace(0.25, 3.0, 12) * sd                       # effects in units of the pooled SD
    pw = power_curve(v, g, sgrid, lambda: np.array([1.0]))
    m = mde(sgrid, pw)
    print(f"{name} {win}: Low {v[low].mean():.4f} (n={low.sum()}) vs High {v[~low].mean():.4f} (n={(~low).sum()}); "
          f"diff {obs:+.4f}, 95% CI {c0:+.4f} to {c1:+.4f}, exact p = {p:.3f}; 80% power at |diff| = {m:.4f} ({m / sd:.2f} SD)")
    rows.append([name, win, int(low.sum()), int((~low).sum()), round(v[low].mean(), dg + 1), round(v[~low].mean(), dg + 1),
                 round(obs, dg + 1), round(c0, dg + 1), round(c1, dg + 1), round(p, 4), round(m, dg + 1), ""])

with open(out_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["measure", "days", "n_low", "n_high", "low_mean", "high_mean", "difference_low_minus_high",
                "ci95_low", "ci95_high", "exact_p", "smallest_detectable_80pct_power", "shape_effect_direction"])
    w.writerows(rows)
print("wrote", out_csv)
