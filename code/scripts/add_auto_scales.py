"""Copy a hub TPS file, adding SCALE= lines from auto_scale.py's CSV to records that have none.
Records that already have a SCALE (set by hand in tpsDig) keep it. All other lines are copied exactly.
Usage: python add_auto_scales.py <hub.tps> <auto_scale.csv> <out.tps>
"""
import csv
import sys

hub, scale_csv, out = sys.argv[1:4]
auto = {r["image"]: r["auto_scale"] for r in csv.DictReader(open(scale_csv, encoding="utf-8"))}
blocks, cur = [], None
for line in open(hub, encoding="utf-8").read().splitlines():
    if line.upper().startswith("LM="):
        cur = []
        blocks.append(cur)
    cur.append(line)
lines, added, kept, missing = [], 0, 0, []
for b in blocks:
    image = next(l.split("=", 1)[1].strip() for l in b if l.upper().startswith("IMAGE="))
    lines += b
    if any(l.upper().startswith("SCALE=") for l in b):
        kept += 1
    elif auto.get(image):
        lines.append(f"SCALE={auto[image]}")
        added += 1
    else:
        missing.append(image)
open(out, "w", newline="").write("\r\n".join(lines) + "\r\n")
print(f"{out}: {added} automatic scales added, {kept} hand scales kept" + (f", NO SCALE: {missing}" if missing else ""))
