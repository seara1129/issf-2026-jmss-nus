"""Growth per leaf in day windows: slope of ln(centroid size in mm) against day, as % per day, for leaves with
3+ photos in the window. Low vs High compared with an exact permutation test on the leaf values (every split).
Usage: python growth_windows.py <specimens.csv> <out.csv>
"""
import csv
import itertools
import sys

import numpy as np

WINDOWS = ((1, 16), (1, 10), (11, 16))


def exact(v, g):
    v, g = np.asarray(v), np.asarray(g)
    n, k = len(v), (g == "mh").sum()
    obs = abs(v[g == "mh"].mean() - v[g == "sh"].mean())
    hits = total = 0
    for idx in itertools.combinations(range(n), k):
        m = np.zeros(n, bool)
        m[list(idx)] = True
        hits += abs(v[m].mean() - v[~m].mean()) >= obs - 1e-12
        total += 1
    return hits / total


spec_csv, out_csv = sys.argv[1:3]
rows = list(csv.DictReader(open(spec_csv, encoding="utf-8")))
out = []
for lo, hi in WINDOWS:
    by = {}
    for r in rows:
        d = int(r["day"])
        if lo <= d <= hi:
            by.setdefault((r["condition"], r["leaf"]), []).append((d, float(r["centroid_size_mm"])))
    rate = {k: 100 * np.polyfit([x[0] for x in v], np.log([x[1] for x in v]), 1)[0] for k, v in by.items() if len(v) >= 3}
    g, v = [k[0] for k in rate], list(rate.values())
    p = exact(v, g)
    m = {c: [x for x, gg in zip(v, g) if gg == c] for c in ("mh", "sh")}
    print(f"Days {lo}-{hi}: Low {np.mean(m['mh']):+.2f} ± {np.std(m['mh'], ddof=1):.2f} (n={len(m['mh'])})  "
          f"High {np.mean(m['sh']):+.2f} ± {np.std(m['sh'], ddof=1):.2f} (n={len(m['sh'])})  exact p = {p:.3f}")
    for k in sorted(rate):
        out.append([f"{lo}-{hi}", k[0], k[1], len(by[k]), round(rate[k], 3)])
with open(out_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["days", "condition", "leaf", "n_photos", "growth_pct_per_day"])
    w.writerows(out)
