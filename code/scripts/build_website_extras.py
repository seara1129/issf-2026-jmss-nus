"""Web copies of the files given for the website (not project outputs), written into morpho/website:
  - the joint poster: a JPEG preview and a smaller PDF (pictures downsampled; author name and other hidden details
    removed), plus the sensor team's three figures cropped out of it at full sharpness (they are vector graphics)
  - set-up photos and Phase 1 photos (field trip, leaf macro photos, optical box): turned upright, resized, and saved
    without any hidden photo data (several have GPS locations)
Read straight from the PDF and the zips; nothing given is changed, and nothing in website/ is overwritten.
Usage: python build_website_extras.py <morpho folder> <poster.pdf> <set-up photos.zip> <phase 1 photos.zip>
"""
import io
import os
import sys
import zipfile

import pymupdf
from PIL import Image, ImageOps

root, poster, setup_zip, phase1_zip = sys.argv[1:5]
site = os.path.join(root, "website")
wrote, skipped = [], []


def save(data, rel):
    dst = os.path.join(site, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        skipped.append(rel)
        return
    open(dst, "wb").write(data)
    wrote.append(rel)


def jpeg(im, longest, quality=82):
    """Upright, at most `longest` px on the long side, saved with no EXIF/GPS."""
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((longest, longest), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


# ---- poster ----
doc = pymupdf.open(poster)
page = doc[0]
W, H = page.rect.width, page.rect.height
pix = page.get_pixmap(matrix=pymupdf.Matrix(2000 / W, 2000 / W))
save(jpeg(Image.open(io.BytesIO(pix.tobytes("png"))), 2830, 80), "assets/img/poster_preview.jpg")
for name, (x0, y0, x1, y1) in {"nus_fig5_gain": (0.7345, 0.5885, 0.997, 0.7745),
                               "nus_fig6_singapore": (0.012, 0.6295, 0.386, 0.7195),
                               "nus_fig7_melbourne": (0.392, 0.6315, 0.727, 0.7175)}.items():
    clip = pymupdf.Rect(x0 * W, y0 * H, x1 * W, y1 * H)
    s = 1600 / clip.width
    save(page.get_pixmap(matrix=pymupdf.Matrix(s, s), clip=clip).tobytes("png"), f"assets/img/{name}.png")
small = pymupdf.open(poster)
small.rewrite_images(dpi_threshold=160, dpi_target=150, quality=80)      # A0 at 150 dpi: sharp on screen, much smaller
small.set_metadata({})
small.del_xml_metadata()
save(small.tobytes(garbage=4, deflate=True, clean=True), "downloads/research/issf_poster_2026.pdf")

# ---- photos ----
PHOTOS = ((setup_zip, "PHOTO-2026-10-11-21-40-41.jpg", "setup_seedlings.jpg"),
          (setup_zip, "PHOTO-2026-10-25-13-27-48.jpg", "setup_tanks.jpg"),
          (phase1_zip, "IMG_6011.jpeg", "phase1_ficus.jpg"),
          (phase1_zip, "IMG_6278.jpeg", "phase1_macro_1.jpg"),
          (phase1_zip, "IMG_6459.jpeg", "phase1_macro_2.jpg"),
          (phase1_zip, "IMG_6463.jpeg", "phase1_macro_3.jpg"),
          (phase1_zip, "IMG_6467.jpeg", "phase1_macro_4.jpg"),
          (phase1_zip, "IMG_6475.jpeg", "phase1_optical_box.jpg"))
for zpath, member, rel in PHOTOS:
    with zipfile.ZipFile(zpath) as z:
        save(jpeg(Image.open(io.BytesIO(z.read(member))), 1400), f"assets/img/photos/{rel}")

print(f"wrote {len(wrote)}, already there {len(skipped)}")
