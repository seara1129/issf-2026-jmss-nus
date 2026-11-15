"""Gather the project website's files into morpho/website (the folder that becomes the GitHub Pages repository):
web-sized copies of the poster figures, the app screenshot, cropped leaf photos of one Low and one High humidity
leaf over the 26 days (with the project's 13 landmarks drawn on Day 26), the final data files plus a zip of them,
the analysis code and the app's source code. index.html is written by hand, not by this script.
Only copies and new files: nothing in the project is changed, and a file already in website/ is never overwritten
(it is skipped, and reported if it differs from what this run would write).
Usage: python build_website.py <morpho folder> <app screenshot.png>
"""
import filecmp
import io
import os
import shutil
import sys
import zipfile

import cv2
import numpy as np
from PIL import Image

import auto_landmarks as A

root, shot = sys.argv[1:3]
site = os.path.join(root, "website")
res, a0 = os.path.join(root, "3_results"), os.path.join(root, "3_results", "poster_figures", "a0")
skipped, differs, wrote = [], [], []


def target(rel):
    path = os.path.join(site, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def copy(src, rel):
    dst = target(rel)
    if os.path.exists(dst):
        (skipped if filecmp.cmp(src, dst, shallow=False) else differs).append(rel)
        return
    shutil.copy2(src, dst)
    wrote.append(rel)


def save_bytes(data, rel):
    dst = target(rel)
    if os.path.exists(dst):
        (skipped if open(dst, "rb").read() == data else differs).append(rel)
        return
    open(dst, "wb").write(data)
    wrote.append(rel)


def web_image(src, rel, width, fmt="PNG"):
    """Shrunk copy for phones: at most `width` px wide; PNG keeps the figures' transparent background."""
    im = Image.open(src)
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    if fmt == "PNG":
        im.save(buf, "PNG", optimize=True)
    else:
        im.convert("RGB").save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    save_bytes(buf.getvalue(), rel)


# ---- figures from the poster (same files as on the poster) ----
for src, rel in (("a0_methods_diagram_v5.png", "fig1_method.png"), ("a0_fig21_greenness_box_v5.png", "fig2_greenness.png"),
                 ("a0_size_per_leaf_v3.png", "fig3_size.png"), ("a0_fig23_shape_v5.png", "fig4_shape.png"),
                 ("a0_setup_diagram_v1.png", "setup_diagram.png"), ("a0_city_comparison_v2.png", "cities.png"),
                 ("a0_fig20_tank_humidity_v2.png", "extra_humidity.png"),       # not on the poster
                 ("a0_fig27_heat_and_colour_by_day_v2.png", "extra_heat_colour.png"),
                 ("a0_fig28_leaf_lifespans_v2.png", "extra_lifespans.png")):
    web_image(os.path.join(a0, src), f"assets/img/{rel}", 1600)
web_image(shot, "assets/img/app_screenshot.jpg", 1600, "JPEG")
web_image(os.path.join(root, "leaf_app", "leaf_icon.png"), "assets/img/icon.png", 256)

# ---- leaf photos: Low tank L02 and High tank L04 (both photographed all 26 days), cropped to the leaf ----
v6 = {r["fields"]["ID"]: r for r in A.read_tps(os.path.join(root, "2_landmarks", "mh-sh_L01-L14_D01-D26_combined_v6.tps"))}
photos = os.path.join(root, "1_photos_tpsdig")
for cond, leaf in (("mh", "L02"), ("sh", "L04")):
    for day in (1, 5, 10, 16, 21, 26):
        r = v6[f"{cond}_{leaf}_D{day:02d}"]
        img = A.load_image(os.path.join(photos, r["fields"]["IMAGE"]))
        H, W = img.shape[:2]
        pts = np.array([(x, H - y) for x, y in r["pts"]])        # tps y is measured up from the bottom
        c, half = (pts.min(0) + pts.max(0)) / 2, 0.68 * (pts.max(0) - pts.min(0)).max()
        x0, y0 = np.maximum((c - half).astype(int), 0)
        x1, y1 = np.minimum((c + half).astype(int), [W, H])
        crop = cv2.resize(img[y0:y1, x0:x1], (720, round(720 * (y1 - y0) / (x1 - x0))), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 82])
        save_bytes(buf.tobytes(), f"assets/img/leaves/{cond}_{leaf}_D{day:02d}.jpg")
        if day == 26:                                             # the project's own 13 landmarks on the same crop
            s = 720 / (x1 - x0)
            q = [(int((x - x0) * s), int((y - y0) * s)) for x, y in pts]
            cv2.polylines(crop, [np.array(q[1:], np.int32)], True, (255, 200, 0), 2, cv2.LINE_AA)
            cv2.line(crop, q[0], q[1], (0, 255, 255), 1, cv2.LINE_AA)
            for k, p in enumerate(q):
                cv2.circle(crop, p, 7, (0, 140, 255) if k == 1 else (0, 0, 255), -1, cv2.LINE_AA)
                cv2.circle(crop, p, 7, (255, 255, 255), 1, cv2.LINE_AA)
                d = np.array(p) - np.array(q[0])
                t = (np.array(p) + (6, -10)) if k == 0 else np.array(p) + 22 * d / max(np.linalg.norm(d), 1) + (-8, 6)
                for col, w in (((0, 0, 0), 4), ((255, 255, 255), 1)):
                    cv2.putText(crop, str(k + 1), tuple(int(v) for v in t), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, w, cv2.LINE_AA)
            ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
            save_bytes(buf.tobytes(), f"assets/img/leaves/{cond}_{leaf}_D26_landmarks.jpg")

# ---- data (final versions only) ----
DATA = (("2_landmarks/mh-sh_L01-L14_D01-D26_combined_v6.tps", "mh-sh_L01-L14_D01-D26_combined_v6.tps"),
        ("3_results/mh-sh_L01-L14_D01-D26_specimens_v6.csv", "mh-sh_L01-L14_D01-D26_specimens_v6.csv"),
        ("3_results/leaf_colour_v4.csv", "leaf_colour_v4.csv"),
        ("3_results/leaf_area_perimeter_v4.csv", "leaf_area_perimeter_v4.csv"),
        ("3_results/plan_D17-D26_results_v2.csv", "plan_D17-D26_results_v2.csv"),
        ("3_results/plan_D17-D26_per_leaf_v2.csv", "plan_D17-D26_per_leaf_v2.csv"),
        ("3_results/growth_summary_D01-D26_v1.csv", "growth_summary_D01-D26_v1.csv"),
        ("3_results/tank_conditions/tank_conditions_daily_v2.csv", "tank_conditions_daily_v2.csv"),
        ("3_results/tank_conditions/tank_conditions_hourly_v2.csv", "tank_conditions_hourly_v2.csv"),
        ("Sensor Data Logging - Sensor Data.csv", "sensor_log_raw_to_D28.csv"))     # copy named without spaces
for src, name in DATA:
    copy(os.path.join(root, src), f"downloads/data/{name}")
copy(os.path.join(root, "website_src", "README_data.md"), "downloads/data/README_data.md")
zbuf = io.BytesIO()
with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
    for name in [n for _, n in DATA] + ["README_data.md"]:
        z.write(os.path.join(site, "downloads", "data", name), f"leaf_project_data/{name}")
zip_rel = "downloads/leaf_project_data_v1.zip"
if not os.path.exists(os.path.join(site, zip_rel)):                  # zips differ byte-wise between runs: only once
    save_bytes(zbuf.getvalue(), zip_rel)
else:
    skipped.append(zip_rel)

# ---- code: analysis scripts and the app's source (code/scripts keeps leaf_core.py's ../scripts import working) ----
for f in sorted(os.listdir(os.path.join(root, "scripts"))):
    if f.endswith((".py", ".js")):
        copy(os.path.join(root, "scripts", f), f"code/scripts/{f}")
for f in ("leaf_app.py", "leaf_core.py", "validate_core.py", "make_icon.py", "build_exe.ps1", "README.txt",
          "leaf_icon.ico", "leaf_icon.png", "validation/core_vs_project_v2.csv", "validation/core_vs_project_v2_log.txt"):
    copy(os.path.join(root, "leaf_app", f), f"code/leaf_app/{f}")

print(f"wrote {len(wrote)} files, {len(skipped)} already there")
for rel in differs:
    print("  NOT OVERWRITTEN (differs from this run):", rel)
