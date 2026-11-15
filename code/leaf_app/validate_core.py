"""Check that the app's measuring code (leaf_core.py) gives the project's numbers: for photos in the combined v6 file,
re-measure from the same hub (landmark 1) and, for traced photos, the same hand trace, then compare with the
project's landmarks, centroid sizes (specimens_v6), area/perimeter (leaf_area_perimeter_v4), greenness
(leaf_colour_v4) and automatic grid scales. Reads only; writes one CSV. GrabCut is not fully deterministic, so
tiny differences (well under 1% of the radius, ~0.0005 GCC) are expected.
Usage: python validate_core.py <morpho folder> <every Nth photo> <out.csv>
"""
import csv
import os
import sys
import time

import numpy as np

import leaf_core as C
from leaf_core import A

root, every, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
if os.path.exists(out):
    raise SystemExit(f"{out} already exists - not overwriting")
res = os.path.join(root, "3_results")
photos = os.path.join(root, "1_photos_tpsdig")
rd = lambda name: {r["ID"]: r for r in csv.DictReader(open(os.path.join(res, name), encoding="utf-8"))}
spec, area, col = rd("mh-sh_L01-L14_D01-D26_specimens_v6.csv"), rd("leaf_area_perimeter_v4.csv"), rd("leaf_colour_v4.csv")
traces = {}                                                     # later trace files replace earlier ones
for f in ("L02-L09_mh_D04-D10_hub_v4.tps", "trace_8photos_D11-D16_done.tps", "trace_4photos_v2_done.tps",
          "trace_24photos_D17-D26_done.tps", "hub_L13_D24_sh_v2_done.tps"):
    for r in A.read_tps(os.path.join(photos, f)):
        if r["curves"]:
            traces[r["fields"]["IMAGE"]] = r["curves"]
recs = A.read_tps(os.path.join(root, "2_landmarks", "mh-sh_L01-L14_D01-D26_combined_v6.tps"))
pick = [r for i, r in enumerate(recs) if i % every == 0 or area[r["fields"]["ID"]]["outline_source"] != "auto"]
rows = []
for r in pick:
    f = r["fields"]
    rid, name = f["ID"], f["IMAGE"]
    t0 = time.time()
    img = C.load_photo(os.path.join(photos, name))
    H = img.shape[0]
    proj = np.array([(x, H - y) for x, y in r["pts"]])
    strokes = [[(x, H - y) for x, y in c] for c in traces.get(name, [])]
    want_traced = area[rid]["outline_source"] == "hand-traced"
    out_, err = C.measure(img, proj[0], strokes if want_traced else None)
    row = dict(ID=rid, outline_project=area[rid]["outline_source"])
    if err:
        row["error"] = err
    else:
        gap = np.linalg.norm(out_["landmarks"] - proj, axis=1).max() / out_["radius"]
        row.update(outline_app=out_["outline"], max_landmark_gap_pct_radius=round(100 * gap, 3),
                   cs_px_app=round(out_["centroid_size_px"], 1), cs_px_project=spec[rid]["centroid_size_px"],
                   area_px_app=round(out_["area_px"]), area_px_project=area[rid]["area_px"],
                   perim_px_app=round(out_["perimeter_px"], 1), perim_px_project=area[rid]["perimeter_px"],
                   gcc_app="" if out_["colour"] is None else round(out_["colour"]["gcc"], 4), gcc_project=col[rid]["gcc"])
    if spec[rid]["scale_source"].startswith("automatic"):
        sq, info = C.grid_square_px(img)
        row.update(scale_app="" if sq is None else round(5 / sq, 6), scale_project=f["SCALE"])
    row["seconds"] = round(time.time() - t0, 1)
    rows.append(row)
    print(row, flush=True)
keys = list(dict.fromkeys(k for r in rows for k in r))
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, keys)
    w.writeheader()
    w.writerows(rows)
ok = [r for r in rows if "error" not in r]
num = lambda k: np.array([float(r[k]) for r in ok if r.get(k) not in ("", None)])
print(f"\n{len(rows)} photos, {len(rows) - len(ok)} errors")
print("landmark gap % of radius: median", np.median(num("max_landmark_gap_pct_radius")), "max", num("max_landmark_gap_pct_radius").max())
for a, b in (("cs_px_app", "cs_px_project"), ("area_px_app", "area_px_project"), ("perim_px_app", "perim_px_project")):
    pair = np.array([(float(r[a]), float(r[b])) for r in ok])
    d = 100 * (pair[:, 0] - pair[:, 1]) / pair[:, 1]
    print(f"{a[:-4]}: % diff median {np.median(np.abs(d)):.3f}, max {np.abs(d).max():.3f}")
g = np.array([(float(r["gcc_app"]), float(r["gcc_project"])) for r in ok if r["gcc_app"] != ""])
print(f"gcc: |diff| median {np.median(np.abs(g[:, 0] - g[:, 1])):.5f}, max {np.abs(g[:, 0] - g[:, 1]).max():.5f}")
s = np.array([(float(r["scale_app"]), float(r["scale_project"])) for r in rows if r.get("scale_app") not in ("", None)])
if len(s):
    print(f"grid scale: {len(s)} photos, % diff max {100 * np.abs(s[:, 0] / s[:, 1] - 1).max():.4f}")
