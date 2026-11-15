"""Make a new version of the combined TPS file and specimen table with some records replaced: re-runs on
hand-traced outlines (same photo) or a second photo of the same leaf and day (IMAGE ends in _v2.jpg).
Every other record is copied line for line. A replaced record keeps its ID; its landmark lines, IMAGE and
SCALE are copied exactly from the auto_landmarks.py output. TPS written with CRLF.
scale_source: unchanged if the SCALE is unchanged, else "automatic (grid lines)" if it matches the auto
scale in the second-photo log, else "hand <date>".
Usage: python replace_records.py <old combined.tps> <old specimens.csv> <replacement auto files, comma-separated>
                                 <second-photo log.csv> <hand date, e.g. 11 Oct> <out combined.tps> <out specimens.csv>
"""
import csv
import os
import sys

import numpy as np



def raw_blocks(path):
    """Records as their original text lines, keyed by IMAGE (same as build_combined.py)."""
    out, cur = {}, None
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.upper().startswith("LM="):
            cur = [line]
            continue
        cur.append(line)
        if line.upper().startswith("IMAGE="):
            out[line.split("=", 1)[1].strip()] = cur
    return out

old_tps, old_csv, rep_files, log_csv, hand_date, out_tps, out_csv = sys.argv[1:8]
rep = {}
for f in rep_files.split(","):
    rep.update(raw_blocks(f))
auto_log = {r["new_file"]: r["auto_scale"] for r in csv.DictReader(open(log_csv, encoding="utf-8"))}
field = lambda b, k: next(l.split("=", 1)[1].strip() for l in b if l.upper().startswith(k + "="))
target = {img.replace("_v2.jpg", ".jpg"): img for img in rep}      # old IMAGE -> replacement IMAGE

lines, blocks, cur = [], [], None
for line in open(old_tps, encoding="utf-8").read().splitlines():
    if line.upper().startswith("LM="):
        cur = []
        blocks.append(cur)
    cur.append(line)
rows = {r["ID"]: r for r in csv.DictReader(open(old_csv, encoding="utf-8"))}
fields = list(next(iter(rows.values())))
done = []
for b in blocks:
    image, rid = field(b, "IMAGE"), field(b, "ID")
    if image not in target:
        lines += b
        continue
    new_img = target[image]
    nb = rep[new_img]
    body = [l for l in nb if not l.upper().startswith(("ID=", "SCALE=", "IMAGE="))]
    scale = field(nb, "SCALE")
    lines += body + [f"IMAGE={new_img}", f"ID={rid}", f"SCALE={scale}"]
    pts = np.array([tuple(map(float, l.split())) for l in body[1:]])
    cs_px = float(np.sqrt(((pts - pts.mean(0)) ** 2).sum()))
    r = rows[rid]
    if float(scale) != float(field(b, "SCALE")):
        r["scale_source"] = ("automatic (grid lines)" if auto_log.get(new_img) and float(auto_log[new_img]) == float(scale)
                             else f"hand {hand_date}")
    r.update(image=new_img, centroid_size_px=round(cs_px, 1), centroid_size_mm=round(cs_px * float(scale), 2),
             source_file=os.path.basename(out_tps))
    done.append(new_img)
missing = set(rep) - set(done)
assert not missing, f"no record to replace for {missing}"
open(out_tps, "w", newline="").write("\r\n".join(lines) + "\r\n")
with open(out_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows.values())
print(f"{out_tps}: {len(blocks)} specimens, {len(done)} replaced: {', '.join(done)}")
