"""Extend the combined TPS file and the specimen table with newly landmarked photos.
The old combined file's records are copied line for line; new records come from auto_landmarks.py output
files (IDs rewritten to condition_leaf_day). Where the same photo appears in an override file (hand-traced
re-runs), that version is used instead. Landmark lines are always copied exactly. TPS written with CRLF.
Usage: python build_combined.py <old combined.tps> <old specimens.csv> <new auto files, comma-separated>
                                <override auto files, comma-separated> <hand-scale hub files, comma-separated>
                                <out combined.tps> <out specimens.csv> [hand-scale label, default "hand 10 Oct"]
A second photo of the same leaf and day (name ending _v2.jpg) replaces the first photo's record.
"""
import csv
import os
import sys

import numpy as np

import auto_landmarks as A

TAG = {"L01": "red", "L02": "yellow", "L03": "green", "L04": "white", "L05": "black", "L06": "brown",
       "L07": "pen", "L08": "pencil", "L09": "blue", "L10": "aqua", "L11": "orange",
       "L12": "pink", "L13": "purple", "L14": "grey"}                # L12-L14 from Day 21 (agreed 18 Oct)


def raw_blocks(path):
    """Records as their original text lines, keyed by IMAGE."""
    out, cur = {}, None
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.upper().startswith("LM="):
            cur = [line]
            continue
        cur.append(line)
        if line.upper().startswith("IMAGE="):
            out[line.split("=", 1)[1].strip()] = cur
    return out


old_tps, old_csv, new_files, over_files, hand_files, out_tps, out_csv = sys.argv[1:8]
HAND = sys.argv[8] if len(sys.argv) > 8 else "hand 10 Oct"
old_lines = open(old_tps, encoding="utf-8").read().splitlines()
old_rows = list(csv.DictReader(open(old_csv, encoding="utf-8")))
new = {}
for f in new_files.split(","):
    new.update(raw_blocks(f))
for f in over_files.split(","):
    new.update(raw_blocks(f))                                     # traced versions replace the automatic ones
for image in [i for i in new if i.endswith("_v2.jpg")]:
    new.pop(image.replace("_v2.jpg", ".jpg"), None)               # second photo replaces the first
hand = {r["fields"]["IMAGE"] for f in hand_files.split(",") for r in A.read_tps(f) if "SCALE" in r["fields"]}
old_images = {r["image"] for r in old_rows}
assert not old_images & set(new), "new photos overlap the old file"

lines = list(old_lines)
rows = list(old_rows)
first_day = {}
for r in old_rows:
    first_day[(r["condition"], r["leaf"])] = min(first_day.get((r["condition"], r["leaf"]), 99), int(r["day"]))
recs = []
for image, b in new.items():
    leaf, day, cond = image[:3], int(image[5:7]), image[8:10]
    recs.append((cond, leaf, day, image, b))
for cond, leaf, day, image, b in recs:
    first_day[(cond, leaf)] = min(first_day.get((cond, leaf), 99), day)
for cond, leaf, day, image, b in sorted(recs):
    rid = f"{cond}_{leaf}_D{day:02d}"
    body = [l for l in b if not l.upper().startswith(("ID=", "SCALE=", "IMAGE="))]
    scale = next(l for l in b if l.upper().startswith("SCALE=")).split("=", 1)[1].strip()
    lines += body + [f"IMAGE={image}", f"ID={rid}", f"SCALE={scale}"]
    pts = np.array([tuple(map(float, l.split())) for l in body[1:]])
    cs_px = float(np.sqrt(((pts - pts.mean(0)) ** 2).sum()))
    fd = first_day[(cond, leaf)]
    rows.append({"ID": rid, "condition": cond, "leaf": leaf, "tag": TAG[leaf], "day": day, "first_day_of_leaf": fd,
                 "days_since_first_photo": day - fd, "original_leaf": "yes" if leaf <= "L05" else "no (replacement)",
                 "image": image, "centroid_size_px": round(cs_px, 1), "centroid_size_mm": round(cs_px * float(scale), 2),
                 "source_file": os.path.basename(out_tps),
                 "scale_source": HAND if image in hand else "automatic (grid lines)"})
open(out_tps, "w", newline="").write("\r\n".join(lines) + "\r\n")
with open(out_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(old_rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"{out_tps}: {len(old_rows)} old + {len(recs)} new = {len(rows)} specimens; "
      f"{sum(r['scale_source'] == HAND for r in rows[len(old_rows):])} new hand scales")
