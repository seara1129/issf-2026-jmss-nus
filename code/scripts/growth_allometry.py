"""Growth and growth-related shape change (allometry), per leaf, Low (mh) vs High (sh).

1. Growth rate: slope of ln(centroid size in mm) against day, per leaf, as % per day.
2. Allometry: does shape change as a leaf grows? Pooled within-leaf regression of
   Procrustes shape on ln(centroid size): each leaf is centred on its own mean, so
   only changes within a leaf over time count, not differences between leaves.
Permutation tests shuffle labels between leaves (condition) or sizes within a leaf.
Usage: python growth_allometry.py <combined.tps> <specimens.csv> <out_growth.csv>
"""
import csv
import sys

import numpy as np

import auto_landmarks as A

RNG = np.random.default_rng(1)
N_PERM = 10000


def procrustes(X):
    norm = lambda z: (z - z.mean()) / np.sqrt((abs(z - z.mean()) ** 2).sum())
    Z = np.array([norm(z) for z in X])
    M = Z[0]
    for _ in range(30):
        Z = np.array([z * np.exp(1j * np.angle((z.conj() * M).sum())) for z in Z])
        M = norm(Z.mean(0))
    return np.hstack([Z.real, Z.imag])


def perm_p(obs, null):
    return ((np.abs(null) >= abs(obs)).sum() + 1) / (len(null) + 1)


def main(tps, spec_csv, out_csv):
    R = A.read_tps(tps)
    ids = [r["fields"]["ID"] for r in R]
    cs = {row["ID"]: float(row["centroid_size_mm"]) for row in csv.DictReader(open(spec_csv))}
    day = np.array([int(i[-2:]) for i in ids])
    leaf = np.array([i[:6] for i in ids])
    lncs = np.log(np.array([cs[i] for i in ids]))
    V = procrustes(np.array([[complex(*p) for p in r["pts"]] for r in R]))

    # 1. growth rate per leaf
    leaves = [l for l in sorted(set(leaf)) if (leaf == l).sum() >= 3]
    rate = {}
    for l in leaves:
        s = leaf == l
        rate[l] = 100 * np.polyfit(day[s], lncs[s], 1)[0]
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["leaf", "condition", "n_photos", "first_day", "last_day", "growth_pct_per_day"])
        for l in leaves:
            s = leaf == l
            w.writerow([l, l[:2], s.sum(), day[s].min(), day[s].max(), f"{rate[l]:.2f}"])
    cond = np.array([l[:2] for l in leaves])
    r_ = np.array([rate[l] for l in leaves])
    diff = r_[cond == "mh"].mean() - r_[cond == "sh"].mean()
    null = np.array([(lambda c: r_[c == "mh"].mean() - r_[c == "sh"].mean())(RNG.permutation(cond)) for _ in range(N_PERM)])
    print("GROWTH (% size change per day, per leaf with >= 3 photos)")
    for c in ("mh", "sh"):
        v = r_[cond == c]
        print(f"  {c}: n={len(v)} leaves, mean {v.mean():+.2f}%/day, median {np.median(v):+.2f}, range {v.min():+.2f} to {v.max():+.2f}")
    print(f"  difference mh - sh = {diff:+.2f}%/day, permutation p = {perm_p(diff, null):.3f}")

    # 2. pooled within-leaf allometry
    keep = np.isin(leaf, leaves)
    Vw, xw, lw = V[keep].copy(), lncs[keep].copy(), leaf[keep]
    for l in leaves:
        s = lw == l
        Vw[s] -= Vw[s].mean(0)
        xw[s] -= xw[s].mean()

    def fit(Vv, xv):
        b = (Vv * xv[:, None]).sum(0) / (xv ** 2).sum()
        pred = np.outer(xv, b)
        return b, (pred ** 2).sum() / (Vv ** 2).sum()

    def shuffle_within(xv, lv):
        out = xv.copy()
        for l in set(lv):
            s = np.where(lv == l)[0]
            out[s] = xv[RNG.permutation(s)]
        return out

    print("\nALLOMETRY (shape change that goes with size change, within leaves)")
    for label, sel in (("all leaves", np.ones(len(lw), bool)), ("mh only", np.char.startswith(lw, "mh")), ("sh only", np.char.startswith(lw, "sh"))):
        b, r2 = fit(Vw[sel], xw[sel])
        null = np.array([fit(Vw[sel], shuffle_within(xw[sel], lw[sel]))[1] for _ in range(2000)])
        p = ((null >= r2).sum() + 1) / (len(null) + 1)
        print(f"  {label}: size explains {100 * r2:.1f}% of within-leaf shape change, permutation p = {p:.3f}")
    bm, _ = fit(Vw[np.char.startswith(lw, "mh")], xw[np.char.startswith(lw, "mh")])
    bs, _ = fit(Vw[np.char.startswith(lw, "sh")], xw[np.char.startswith(lw, "sh")])
    ang = np.degrees(np.arccos(np.clip(bm @ bs / np.linalg.norm(bm) / np.linalg.norm(bs), -1, 1)))
    print(f"  angle between mh and sh allometry directions: {ang:.0f} deg (0 = same direction, 90 = unrelated)")


if __name__ == "__main__":
    main(*sys.argv[1:4])
