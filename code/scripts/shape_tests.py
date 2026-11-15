"""Shape tests, Low (mh) vs High (sh) humidity, on a combined TPS file (13 landmarks, IDs like mh_L02_D11).
All shapes are Procrustes-fitted together (unit centroid size, rotated to the consensus).
  1. mean shape: Procrustes distance between the tanks' average shapes, each the average of its leaf averages
     (as MorphoJ's averaged dataset); exact permutation test (every possible split of the leaves)
  2. PC1 / PC2 of the leaf averages: same exact test
  3. shape vs day, within leaves: pooled within-leaf regression of shape on day (each leaf centred on its own
     mean); % of within-leaf shape change explained; permutation test shuffling days within each leaf
  4. day-to-day change: Procrustes distance between photos of a leaf on consecutive days, averaged per leaf;
     exact permutation test between tanks
Each test runs on all days and on the day windows given.
Usage: python shape_tests.py <combined.tps> <out.csv> [first-last ...]   e.g. 1-10 11-16
"""
import csv
import itertools
import sys

import numpy as np

import auto_landmarks as A
from growth_allometry import procrustes

RNG = np.random.default_rng(1)
N_PERM = 10000


def exact_split(values, groups, stat):
    """Exact permutation p: share of all splits of the leaves with a statistic >= the observed one."""
    g = np.asarray(groups)
    n, k = len(g), int((g == "mh").sum())
    obs = stat(values, g == "mh")
    hits = total = 0
    for idx in itertools.combinations(range(n), k):
        m = np.zeros(n, bool)
        m[list(idx)] = True
        hits += stat(values, m) >= obs - 1e-12
        total += 1
    return obs, hits / total


def mean_dist(V, m):
    return float(np.sqrt(((V[m].mean(0) - V[~m].mean(0)) ** 2).sum()))


def abs_diff(v, m):
    return abs(v[m].mean() - v[~m].mean())


def within_fit(V, x, leaf):
    Vw, xw = V.copy(), x.astype(float).copy()
    for l in set(leaf):
        s = leaf == l
        Vw[s] -= Vw[s].mean(0)
        xw[s] -= xw[s].mean()
    b = (Vw * xw[:, None]).sum(0) / (xw ** 2).sum()
    return (np.outer(xw, b) ** 2).sum() / (Vw ** 2).sum()


def run(V, ids, label):
    cond = np.array([i[:2] for i in ids])
    leaf = np.array([i[:6] for i in ids])
    day = np.array([int(i[-2:]) for i in ids])
    out = []
    leaves = sorted(set(leaf))
    LM = np.array([V[leaf == l].mean(0) for l in leaves])
    g = np.array([l[:2] for l in leaves])
    d, p = exact_split(LM, g, mean_dist)
    out.append((label, "mean shape Low vs High (leaf averages)", f"{(g == 'mh').sum()} vs {(g == 'sh').sum()} leaves",
                f"Procrustes distance {d:.4f}", p))
    C = LM - LM.mean(0)
    _, sv, Wt = np.linalg.svd(C, full_matrices=False)
    for k in (0, 1):
        sc = C @ Wt[k]
        _, p = exact_split(sc, g, abs_diff)
        out.append((label, f"PC{k + 1} of leaf averages ({100 * sv[k] ** 2 / (sv ** 2).sum():.0f}% of variation)", "",
                    f"Low {sc[g == 'mh'].mean():+.4f} vs High {sc[g == 'sh'].mean():+.4f}", p))
    for c in ("mh", "sh"):
        s = cond == c
        keep = np.isin(leaf, [l for l in set(leaf[s]) if (leaf == l).sum() >= 3])
        s &= keep
        r2 = within_fit(V[s], day[s], leaf[s])
        null = []
        for _ in range(N_PERM):
            dd = day[s].copy()
            for l in set(leaf[s]):
                m = leaf[s] == l
                dd[m] = RNG.permutation(dd[m])
            null.append(within_fit(V[s], dd, leaf[s]))
        p = (np.sum(np.array(null) >= r2) + 1) / (N_PERM + 1)
        out.append((label, f"shape vs day within leaves, {'Low' if c == 'mh' else 'High'}",
                    f"{len(set(leaf[s]))} leaves, {s.sum()} photos", f"{100 * r2:.1f}% of within-leaf change", p))
    steps = {}
    for l in leaves:
        ix = np.where(leaf == l)[0]
        ix = ix[np.argsort(day[ix])]
        dl = [np.sqrt(((V[a] - V[b]) ** 2).sum()) for a, b in zip(ix[:-1], ix[1:]) if day[b] - day[a] == 1]
        if dl:
            steps[l] = np.mean(dl)
    sl = sorted(steps)
    v = np.array([steps[l] for l in sl])
    gg = np.array([l[:2] for l in sl])
    _, p = exact_split(v, gg, abs_diff)
    out.append((label, "day-to-day shape change Low vs High", f"{(gg == 'mh').sum()} vs {(gg == 'sh').sum()} leaves",
                f"{v[gg == 'mh'].mean():.4f} vs {v[gg == 'sh'].mean():.4f}", p))
    between = [np.sqrt(((LM[i] - LM[j]) ** 2).sum()) for i, j in itertools.combinations(range(len(leaves)), 2) if g[i] == g[j]]
    out.append((label, "two leaves in the same tank (median distance)", "", f"{np.median(between):.4f}", ""))
    return out


def main(tps, out_csv, *windows):
    R = A.read_tps(tps)
    ids = np.array([r["fields"]["ID"] for r in R])
    V = procrustes(np.array([[complex(*p) for p in r["pts"]] for r in R]))
    day = np.array([int(i[-2:]) for i in ids])
    results = run(V, ids, f"Days {day.min()}-{day.max()}")
    for w in windows:
        a, b = map(int, w.split("-"))
        s = (day >= a) & (day <= b)
        results += run(V[s], ids[s], f"Days {a}-{b}")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["days", "test", "sample", "result", "p"])
        for r in results:
            wr.writerow(list(r[:4]) + ["" if r[4] == "" else round(r[4], 4)])
    for r in results:
        print(f"{r[0]:11} {r[1]:48} {r[2]:24} {r[3]:34} p = {r[4] if r[4] == '' else round(r[4], 3)}")


if __name__ == "__main__":
    main(*sys.argv[1:])
