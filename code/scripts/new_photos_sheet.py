"""Overview sheet of one tank's photos: one row per leaf, one column per day; uses a _v2 photo where one exists.
Never overwrites. Usage: python new_photos_sheet.py <photo dir> <mh|sh> <first day> <last day> <out.jpg>
"""
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

photo_dir, cond, d0, d1, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
if os.path.exists(out):
    raise SystemExit(f"{out} already exists - not overwriting")
files = {}
for f in os.listdir(photo_dir):
    m = re.fullmatch(rf"(L\d+)_D(\d+)_{cond}(_v2)?\.jpg", f)
    if m and d0 <= int(m.group(2)) <= d1 and (m.group(3) or (m.group(1), int(m.group(2))) not in files):
        files[(m.group(1), int(m.group(2)))] = f
leaves = sorted({k[0] for k in files})
days = range(d0, d1 + 1)
CW, RH, LW, TH = 310, 310, 110, 50
sheet = Image.new("RGB", (LW + CW * len(days), TH + RH * len(leaves)), "white")
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype("arialbd.ttf", 26)
for j, d in enumerate(days):
    draw.text((LW + CW * j + CW // 2, TH // 2), f"Day {d}", fill="black", font=font, anchor="mm")
for i, leaf in enumerate(leaves):
    draw.text((10, TH + RH * i + RH // 2), leaf, fill="black", font=font, anchor="lm")
    for j, d in enumerate(days):
        if (leaf, d) not in files:
            continue
        im = Image.open(os.path.join(photo_dir, files[(leaf, d)])).convert("RGB")
        im.thumbnail((CW - 10, RH - 34))
        x, y = LW + CW * j + 5, TH + RH * i
        sheet.paste(im, (x, y))
        if files[(leaf, d)].endswith("_v2.jpg"):
            draw.text((x, y + im.height + 2), "v2", fill=(200, 0, 0), font=ImageFont.truetype("arialbd.ttf", 20))
sheet.save(out, quality=85)
print("wrote", out, f"{len(leaves)} leaves x {len(days)} days, {len(files)} photos,",
      "v2:", sorted(f for f in files.values() if f.endswith("_v2.jpg")))
