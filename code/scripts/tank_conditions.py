"""Summarise the terrarium sensor log (humidity, temperature, VPD) per tank and per experiment day.
Reads only; writes hourly and daily CSVs.
Usage: python tank_conditions.py <sensor log .xlsx or .csv> <out_folder> [version, default v1]

Tank mapping is inferred from the readings (DHT1 sits at ~90% RH, DHT2 at ~50%):
DHT1 = High humidity (sh), DHT2 = Low humidity (mh). Confirm with the teammate who set up the sensors.
"""
import collections
import csv
import datetime as dt
import math
import os
import sys

import numpy as np
import openpyxl

DAY1 = dt.date(2026, 9, 21)
TANKS = {"High (sh)": (1, 2), "Low (mh)": (3, 4)}          # column indexes of (temperature, humidity)
IN_TARGET = {"High (sh)": lambda rh: rh >= 80, "Low (mh)": lambda rh: 40 <= rh <= 60}


def vpd(t, rh):
    """Vapour pressure deficit in kPa (Tetens equation)."""
    return 0.6108 * math.exp(17.27 * t / (t + 237.3)) * (1 - rh / 100)


log, out = sys.argv[1], sys.argv[2]
ver = sys.argv[3] if len(sys.argv) > 3 else "v1"
os.makedirs(out, exist_ok=True)
if log.lower().endswith(".csv"):                           # Google Sheets export: same columns as the xlsx
    rows = []
    with open(log, encoding="utf-8-sig") as fh:
        for r in csv.reader(fh):
            try:
                t = dt.datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            rows.append((t, *[float(x) if x.strip() else None for x in r[1:]]))
else:
    ws = openpyxl.load_workbook(log, data_only=True, read_only=True)["Sensor Data"]
    rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if isinstance(r[0], dt.datetime)]

# hourly means per tank (the logger samples every ~30-40 min, with a burst of 3-second readings at start-up)
hourly = {}
for tank, (ti, hi) in TANKS.items():
    acc = collections.defaultdict(list)
    for r in rows:
        if r[ti] is not None and r[hi] is not None and 0 < r[hi] <= 100:
            acc[r[0].replace(minute=0, second=0, microsecond=0)].append((r[ti], r[hi]))
    hourly[tank] = {h: (np.mean([a for a, _ in v]), np.mean([b for _, b in v])) for h, v in acc.items()}

with open(os.path.join(out, f"tank_conditions_hourly_{ver}.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["hour", "day", "tank", "temp_C", "rh_pct", "vpd_kPa"])
    for tank, H in hourly.items():
        for h in sorted(H):
            t, rh = H[h]
            w.writerow([h.strftime("%Y-%m-%d %H:00"), (h.date() - DAY1).days + 1, tank, round(t, 2), round(rh, 2), round(vpd(t, rh), 3)])

with open(os.path.join(out, f"tank_conditions_daily_{ver}.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["day", "date", "tank", "hours_logged", "rh_mean", "rh_sd", "rh_min", "rh_max",
                "temp_mean", "temp_min", "temp_max", "vpd_mean_kPa", "pct_hours_in_target"])
    for tank, H in hourly.items():
        days = collections.defaultdict(list)
        for h, (t, rh) in H.items():
            days[(h.date() - DAY1).days + 1].append((t, rh))
        for d in sorted(days):
            t = np.array([x[0] for x in days[d]])
            rh = np.array([x[1] for x in days[d]])
            ok = np.mean([IN_TARGET[tank](x) for x in rh]) * 100
            w.writerow([d, (DAY1 + dt.timedelta(days=d - 1)).isoformat(), tank, len(t), round(rh.mean(), 1), round(rh.std(), 1),
                        round(rh.min(), 1), round(rh.max(), 1), round(t.mean(), 1), round(t.min(), 1), round(t.max(), 1),
                        round(np.mean([vpd(a, b) for a, b in zip(t, rh)]), 2), round(ok)])

print(f"{len(rows)} readings, {rows[0][0]} to {rows[-1][0]}")
for label, d0, d1 in (("Days 1-10", 1, 10), ("Days 11-16", 11, 16), ("Days 17-26", 17, 26)):
    print(label)
    for tank, H in hourly.items():
        v = [(t, rh) for h, (t, rh) in H.items() if d0 <= (h.date() - DAY1).days + 1 <= d1]
        t = np.array([a for a, _ in v])
        rh = np.array([b for _, b in v])
        ok = np.mean([IN_TARGET[tank](x) for x in rh]) * 100
        print(f"  {tank:10} RH {rh.mean():5.1f} +/- {rh.std():4.1f}%  temp {t.mean():4.1f} +/- {t.std():3.1f} C (max {t.max():4.1f})"
              f"  VPD {np.mean([vpd(a, b) for a, b in v]):.2f} kPa  in target {ok:3.0f}% of {len(v)} h")
    both = [(hourly["High (sh)"][h], hourly["Low (mh)"][h]) for h in hourly["High (sh)"]
            if h in hourly["Low (mh)"] and d0 <= (h.date() - DAY1).days + 1 <= d1]
    print(f"  High minus Low, same hour: RH {np.mean([a[1] - b[1] for a, b in both]):+.1f} points,"
          f" temp {np.mean([a[0] - b[0] for a, b in both]):+.1f} C ({len(both)} h)")
pm = [r[6] for r in rows if r[6] is not None]
print(f"PM2.5 (ATM): above 0 in {sum(p > 0 for p in pm)} of {len(pm)} readings, max {max(pm)} ug/m3")
