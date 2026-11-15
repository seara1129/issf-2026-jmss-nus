"""Draw the app icon: a round nasturtium-like leaf with veins spreading from an off-centre hub, the hub in red and a
ring of landmark dots. Writes leaf_icon.ico (16-256 px) and leaf_icon.png next to this script; refuses to overwrite.
Usage: python make_icon.py
"""
import math
import os

from PIL import Image, ImageDraw

here = os.path.dirname(os.path.abspath(__file__))
paths = [os.path.join(here, "leaf_icon.ico"), os.path.join(here, "leaf_icon.png")]
for p in paths:
    if os.path.exists(p):
        raise SystemExit(f"{p} already exists - not overwriting")
S = 1024                                                    # drawn large, then shrunk for smooth edges
im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
c, r = S / 2, 0.44 * S
d.ellipse([c - r, c - r, c + r, c + r], fill=(64, 99, 39, 255))                  # poster dark green #406327
d.ellipse([c - r + 34, c - r + 34, c + r - 34, c + r - 34], fill=(108, 160, 64, 255))
hub = (c + 0.06 * S, c + 0.08 * S)
for k in range(12):                                          # veins and the 12 edge landmarks
    a = math.radians(-90 + 30 * k + 8)
    # where the ray from the hub meets the inner circle
    dx, dy = math.cos(a), math.sin(a)
    px, py = hub[0] - c, hub[1] - c
    b = px * dx + py * dy
    t = -b + math.sqrt(b * b - (px * px + py * py - (r - 34) ** 2))
    e = (hub[0] + t * dx, hub[1] + t * dy)
    d.line([hub, e], fill=(214, 232, 180, 255), width=18)
    d.ellipse([e[0] - 30, e[1] - 30, e[0] + 30, e[1] + 30], fill=(255, 140, 0, 255) if k == 0 else (230, 40, 40, 255),
              outline=(255, 255, 255, 255), width=8)
d.ellipse([hub[0] - 46, hub[1] - 46, hub[0] + 46, hub[1] + 46], fill=(230, 40, 40, 255), outline=(255, 255, 255, 255),
          width=10)
icon = im.resize((256, 256), Image.LANCZOS)
icon.save(paths[1])
icon.save(paths[0], sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("wrote", *map(os.path.basename, paths))
