"""Convert the first photo of each leaf-day from the Google Drive zip (HEIC) to JPEG, named
L##_D##_mh/sh.jpg, and write a photo log and tpsDig list files (LM=0) ready for hub + scale clicks.
Never overwrites an existing JPEG. The zip is only read.
Usage: python convert_new_photos.py <zip> <morpho folder>
"""
import csv
import io
import os
import re
import sys
import zipfile

import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()

LEAF = {"red": "L01", "yellow": "L02", "green": "L03", "white": "L04", "black": "L05", "brown": "L06",
        "pen": "L07", "pen colour": "L07", "pencil": "L08", "pencil colour": "L08", "blue": "L09", "aqua": "L10",
        "orange": "L11"}
COND = {"melbourne terrarium": "mh", "singapore terrarium": "sh"}
WANTED = {"mh": range(11, 17), "sh": range(10, 17)}   # days not yet converted
# folders whose colour name does not match the leaf in the photo (checked by eye against the days either side)
OVERRIDE = {("mh", 14, "red"): ("L07", "folder named 'red' but it is the pen leaf: same shape and yellow-brown left edge as pen on Days 13 and 15")}
NOTE = {"L11": "new tag colour (orange), first seen Day 12; replaces aqua (L10), last seen Day 11"}

zpath, root = sys.argv[1], sys.argv[2]
photo_dir = os.path.join(root, "1_photos_tpsdig")
z = zipfile.ZipFile(zpath)
groups = {}
for n in z.namelist():
    m = re.match(r"leaf pictures/(.+?)/humidity/day (\d+) - ([\d-]+)/(.+?)/(IMG_(\d+)\.HEIC)$", n, re.I)
    if m:
        groups.setdefault((COND[m.group(1)], int(m.group(2)), m.group(3), m.group(4).lower()), []).append((int(m.group(6)), m.group(5), n))

# check: for days converted before, the logged photo must be the first (lowest IMG number) of its folder
old = {}
for log in ("photo_log_mh_D04-D10_v2.csv", "photo_log_sh_D04-D09.csv"):
    for r in csv.DictReader(open(os.path.join(root, "4_docs", log), encoding="utf-8")):
        old[r["new_file"]] = r["original_file"]
mismatch = []
for (c, d, _, col), files in groups.items():
    if col in LEAF and d >= 4:
        name = f"{LEAF[col]}_D{d:02d}_{c}.jpg"
        if name in old and old[name] != min(files)[1]:
            mismatch.append((name, old[name], min(files)[1]))
print("earlier logs vs first photo:", "all match" if not mismatch else mismatch)

rows, made = [], []
for (c, d, date, col), files in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][3])):
    if d not in WANTED[c]:
        continue
    leaf, note = OVERRIDE.get((c, d, col), (LEAF[col], NOTE.get(LEAF[col], "")))
    files.sort()
    _, orig, zname = files[0]
    out = f"{leaf}_D{d:02d}_{c}.jpg"
    dest = os.path.join(photo_dir, out)
    if os.path.exists(dest):
        raise SystemExit(f"{out} already exists - not overwriting")
    Image.open(io.BytesIO(z.read(zname))).convert("RGB").save(dest, "JPEG", quality=95)
    rows.append([leaf, col, f"D{d:02d}", date.replace("-", "/"), zname.split("/humidity/", 1)[1], orig, out,
                 f"{len(files)} photo(s) in folder; first used" + (f"; {note}" if note else "")])
    made.append((c, leaf, d, out))
    print(f"  {out:18} <- {zname.split('/humidity/', 1)[1]}" + (f"   [{note}]" if note else ""))

with open(os.path.join(root, "4_docs", "photo_log_mh-sh_D10-D16.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["leaf", "tag", "day", "date", "zip_path", "original_file", "new_file", "note"])
    w.writerows(rows)

for c, fname in (("mh", "L02-L09_mh_D11-D16.tps"), ("sh", "L01-L11_sh_D10-D16.tps")):
    recs = sorted([m for m in made if m[0] == c], key=lambda m: (m[1], m[2]))
    lines = []
    for i, (_, _, _, out) in enumerate(recs):
        lines += ["LM=0", f"IMAGE={out}", f"ID={i}"]
    open(os.path.join(photo_dir, fname), "w", newline="").write("\r\n".join(lines) + "\r\n")
    print(f"wrote {fname} ({len(recs)} images)")
print(f"converted {len(made)} photos; log: 4_docs/photo_log_mh-sh_D10-D16.csv")
