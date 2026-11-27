"""Make the white (and the poster's light-green) background of a drawing transparent, so it sits on the poster's
colour. Black and grey linework fades smoothly: each grey pixel becomes black with partial transparency, so line edges
have no light halo on any background. Coloured parts (water, sensors, wires) stay solid in their own colour. The
drawing is enlarged first (smooth interpolation), which helps when only a small screenshot is available.
Usage: python remove_white_bg.py <in image> <out .png> [enlarge factor, default 4]
"""
import os
import sys

import numpy as np
from PIL import Image

src, out = sys.argv[1:3]
scale = int(sys.argv[3]) if len(sys.argv) > 3 else 4
if os.path.exists(out):
    raise SystemExit(f"{out} already exists - not overwriting")
POSTER_BG = np.array([226, 234, 214], float)      # the poster's #e4e9d9 where the screenshot caught it
WHITE_MIN = 250.0                                  # a channel this bright counts as paper

im = Image.open(src).convert("RGB")
im = im.resize((im.width * scale, im.height * scale), Image.BICUBIC)
rgb = np.clip(np.asarray(im).astype(float), 0, 255)
lo, hi = rgb.min(2), rgb.max(2)
# linework: how dark the pixel is against white paper (grey 200 -> 20% black, black -> solid black)
a_line = np.clip((WHITE_MIN - lo) / WHITE_MIN, 0, 1)
# coloured parts: solid once clearly coloured (saturation), whatever their brightness
a_colour = np.clip((hi - lo - 30) / 40, 0, 1)
alpha = np.maximum(a_line, a_colour)
alpha[np.linalg.norm(rgb - POSTER_BG, axis=2) < 14] = 0           # poster background caught in the screenshot
# colour: lines become black (un-mixed from white); coloured parts keep their colour
a = np.maximum(alpha, 1e-3)[..., None]
unmixed = np.clip((rgb - (1 - a) * 255) / a, 0, 255)
w = a_colour[..., None]
colour = w * rgb + (1 - w) * unmixed
rgba = np.dstack([colour, alpha * 255]).round().astype(np.uint8)
Image.fromarray(rgba, "RGBA").save(out)
print(f"wrote {out} ({im.width} x {im.height}), {100 * (alpha == 0).mean():.0f}% transparent")
