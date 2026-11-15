"""Convert Days 17-26 from the second Drive zip (HEIC) to JPEG, named L##_D##_mh/sh.jpg: the first photo of each
leaf-day folder (lowest IMG number, as before). Only tag colours with an agreed leaf number are converted; any other
folder is listed and skipped until its leaf number is confirmed. Never overwrites a JPEG; the zip is only read.
Usage: python convert_d17_d26.py <zip> <morpho folder> <out log csv> [colours to convert, comma-separated]
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
sys.stdout.reconfigure(encoding="utf-8")
LEAF = {"red": "L01", "yellow": "L02", "green": "L03", "white": "L04", "black": "L05", "brown": "L06",
        "pen": "L07", "pen colour": "L07", "pencil": "L08", "pencil colour": "L08", "blue": "L09", "aqua": "L10",
        "orange": "L11", "pink": "L12", "purple": "L13", "grey": "L14"}   # L12-L14 agreed with the user 18 Oct 2026
SKIP = {("sh", 20, "blue"): "left out (user, 18 Oct 2026): one photo of an unidentified round leaf; blue was replaced by aqua on Day 9"}
DAYS = range(17, 27)

zpath, root, log_csv = sys.argv[1:4]
ONLY = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else None   # optional: convert only these tag colours
photo_dir = os.path.join(root, "1_photos_tpsdig")
z = zipfile.ZipFile(zpath)
groups, odd = {}, []
for n in z.namelist():
    m = re.match(r"leaf pictures/(melbourne|singapore) terrarium/humidity/day (\d+) - ([\d-]+)/(.+?)/(.+)$", n, re.I)
    if not m or not m.group(5) or int(m.group(2)) not in DAYS:
        continue
    f = re.match(r"IMG_(\d+)\.HEIC$", m.group(5), re.I)
    if not f:
        odd.append(n)
        continue
    c = "mh" if m.group(1).lower() == "melbourne" else "sh"
    groups.setdefault((c, int(m.group(2)), m.group(3), m.group(4).lower()), []).append((int(f.group(1)), m.group(5), n))
if odd:
    print("files with unusual names (not used):", odd)

rows, skipped = [], []
for (c, d, date, col), files in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][3])):
    if ONLY is not None and col not in ONLY:
        continue
    if col not in LEAF or (c, d, col) in SKIP:
        skipped.append(f"{c} D{d} {col}" + (f" ({SKIP[(c, d, col)]})" if (c, d, col) in SKIP else " (new tag colour)"))
        continue
    files.sort()
    _, orig, zname = files[0]
    out = f"{LEAF[col]}_D{d:02d}_{c}.jpg"
    dest = os.path.join(photo_dir, out)
    if os.path.exists(dest):
        raise SystemExit(f"{out} already exists - not overwriting")
    Image.open(io.BytesIO(z.read(zname))).convert("RGB").save(dest, "JPEG", quality=95)
    rows.append([LEAF[col], col, f"D{d:02d}", date.replace("-", "/"), zname.split("/humidity/", 1)[1], orig, out,
                 f"{len(files)} photo(s) in folder; first used"])
    print(f"  {out:18} <- {zname.split('/humidity/', 1)[1]}", flush=True)

with open(log_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["leaf", "tag", "day", "date", "zip_path", "original_file", "new_file", "note"])
    w.writerows(rows)
print(f"converted {len(rows)} photos; log {log_csv}")
print("skipped until confirmed:", len(skipped))
for s in skipped:
    print("   ", s)
