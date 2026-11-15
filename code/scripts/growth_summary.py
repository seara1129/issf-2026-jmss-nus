"""Descriptive growth table (not a planned test): leaf size (centroid size) growth per day for each tank in each period
(leaves with 3+ photos in the period; Day 1 left out of period A, as in the plan), and each leaf's total growth from its
first to its last photo for leaves followed 12 days or more. Per-day rate = slope of ln(size) against day; total = the
fitted change over the days the leaf was followed.
Usage: python growth_summary.py <morpho folder> <out.csv>
"""
import csv
import os
import sys

import numpy as np

root, out = sys.argv[1:3]
if os.path.exists(out):
    raise SystemExit(f"{out} already exists - not overwriting")
spec = list(csv.DictReader(open(os.path.join(root, "3_results", "mh-sh_L01-L14_D01-D26_specimens_v6.csv"), encoding="utf-8")))


def per_leaf(lo, hi):
    acc = {}
    for r in spec:
        d = int(r["day"])
        if lo <= d <= hi:
            acc.setdefault((r["condition"], r["leaf"]), []).append((d, float(r["centroid_size_mm"])))
    res = {}
    for k, v in acc.items():
        if len(v) >= 3:
            v.sort()
            days, vals = np.array([a for a, _ in v]), np.array([b for _, b in v])
            slope = np.polyfit(days, np.log(vals), 1)[0]
            res[k] = (100 * slope, 100 * (np.exp(slope * (days[-1] - days[0])) - 1), int(days[-1] - days[0]), len(v))
    return res


rows = []
for name, lo, hi in (("A Days 2-10", 2, 10), ("B Days 11-16", 11, 16), ("C Days 17-26", 17, 26)):
    res = per_leaf(lo, hi)
    for t, lab in (("mh", "Low"), ("sh", "High")):
        pd = np.array([v[0] for k, v in res.items() if k[0] == t])
        rows.append(["period", name, lab, len(pd), round(pd.mean(), 2), round(pd.std(ddof=1), 2), "", ""])
for k, (pd, tot, span, n) in sorted(per_leaf(1, 26).items()):
    if span >= 12:
        rows.append(["leaf, whole record", k[1], "Low" if k[0] == "mh" else "High", n, round(pd, 2), "", round(tot, 1), span])
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["table", "period_or_leaf", "tank", "n (leaves, or photos for a leaf)", "growth_pct_per_day", "sd", "total_growth_pct", "days_followed"])
    w.writerows(rows)
for r in rows:
    print(r)
