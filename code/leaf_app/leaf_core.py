"""Measuring one leaf photo for the Leaf Landmarks app: the same steps as the project's scripts, which are imported
from ../scripts unchanged, so the app gives the numbers the project used.

  outline    auto_landmarks.segment(): colour mask + GrabCut, with the strict-colour retry when the hub ends up far
             off-centre (a merged shadow); or the user's hand trace
  landmarks  LM1 = the hub as clicked; LM2 where the line from the outline's centre through the hub meets the edge;
             LM3-13 every 30 degrees clockwise on screen (auto_landmarks.main)
  scale      auto_scale.grid_scale() for any grid square size, or two clicked points a known distance apart
  size       centroid size of the 13 landmarks (build_combined.py), outline area and perimeter (leaf_area.py),
             roundness = 4 pi area / perimeter^2
  colour     GCC = G/(R+G+B) inside the leaf after white-balancing to the paper around it, yellow % and glare %
             (leaf_colour.py)
Points are image pixels with y measured down from the top; only the .tps file uses tpsDig's y-up.
"""
import math
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import auto_landmarks as A  # noqa: E402
import auto_scale as S  # noqa: E402
import leaf_area  # noqa: E402

HEIC = (".heic", ".heif")


def load_photo(path):
    """BGR pixels as tpsDig shows them (EXIF rotation ignored, as in auto_landmarks.load_image). HEIC photos are
    decoded with pillow-heif the way convert_new_photos.py did it; tpsDig can't open them, so results get a JPEG copy."""
    if os.path.splitext(path)[1].lower() in HEIC:
        import pillow_heif
        from PIL import Image
        pillow_heif.register_heif_opener()
        return np.ascontiguousarray(np.asarray(Image.open(path).convert("RGB"))[:, :, ::-1])
    img = A.load_image(path)
    if img is None:
        raise ValueError("this file can't be read as a photo")
    return img


def grid_square_px(img):
    """One grid square in pixels, from auto_scale.grid_scale(). That function assumes 5 mm squares, so any square
    size works: mm per pixel = square_mm / square_px. It looks for squares of about 90-440 px; the photo is also
    tried at half and double size so bigger and smaller squares are found too (full size first, as in the project).
    Returns (square_px, info) or (None, info with a "note" saying why not)."""
    info = {}
    for f in (1.0, 0.5, 2.0):
        if f == 2.0 and max(img.shape[:2]) > 3000:            # would need too much memory; squares are big enough
            continue
        im = img if f == 1.0 else cv2.resize(img, None, fx=f, fy=f,
                                             interpolation=cv2.INTER_AREA if f < 1 else cv2.INTER_CUBIC)
        sc, info = S.grid_scale(im)
        if sc is not None:
            return S.SQUARE_MM / sc / f, info
    return None, info


def measure(img, hub, strokes=None):
    """Outline, 13 landmarks and pixel measurements for one photo. hub = (x, y). strokes = the user's hand trace as a
    list of strokes of (x, y) points; with 10+ points it replaces the automatic outline. Returns (result, None) or
    (None, what went wrong)."""
    hub = np.asarray(hub, float)
    warn, notes = [], []
    seg, err = A.segment(img, hub)
    traced = A.stitch(strokes or [])
    if len(traced) >= 10:                                  # the user traced the outline: use it instead
        cnt = np.array(traced, float)
        if cv2.pointPolygonTest(cnt.astype(np.float32).reshape(-1, 1, 2), (float(hub[0]), float(hub[1])), False) < 0:
            return None, "The hub is outside your traced outline. Click the hub again, inside the leaf."
        if seg is not None:
            gap = np.median([A.dist_to_poly(p, seg["contour"]) for p in cnt]) / A.contour_stats(cnt, hub)[2]
            notes.append(f"your trace is {gap:.1%} of the radius from the automatic edge (median)")
        seg, err, source = {"contour": cnt, "notch": 0.0, "touches_border": False}, None, "hand-traced"
    else:
        source = "automatic"
    if err:
        return None, f"No leaf found at the hub ({err}). Click the hub on the leaf, or trace the outline by hand."
    cnt, cen, radius, off = A.outline_stats(seg, hub)
    if off > 0.40 and source == "automatic":               # hub far off-centre: usually a grey cast shadow
        seg2, err2 = A.segment(img, hub, s_min=90)          # merged in; retry with the stricter colour test
        if not err2:
            c2 = A.outline_stats(seg2, hub)
            if c2[3] < off:
                seg, (cnt, cen, radius, off) = seg2, c2
                source = "automatic (strict colour)"
                warn.append("used the strict colour test because a shadow was merged in: check the outline")
    theta0 = math.atan2(hub[1] - cen[1], hub[0] - cen[0])
    pts = [A.ray_hit(hub, theta0 + k * 2 * math.pi / A.N_OUTLINE, cnt) for k in range(A.N_OUTLINE)]
    missing = [k + 2 for k, p in enumerate(pts) if p is None]
    if missing:
        return None, f"No edge found for landmark {missing[0]}. Click the hub again, or trace the outline by hand."
    if off < 0.08:
        warn.append(f"the hub is only {off:.0%} of the radius from the leaf's centre, so the 12 o'clock direction "
                    "(landmark 2) is unreliable")
    if seg["notch"] / radius > 0.15:
        warn.append(f"the outline has a bite {seg['notch'] / radius:.0%} of the radius deep (glare or shadow?): "
                    "trace by hand if it is wrong")
    if seg["touches_border"]:
        warn.append("the leaf touches the edge of the photo")
    lm = np.vstack([hub, pts])
    area_px = abs(cv2.contourArea(cnt.astype(np.float32)))
    perim_px = leaf_area.perimeter(cnt, 1 if source == "hand-traced" else 5)
    col = colour(img, cnt)
    if col is None:
        warn.append("not enough plain paper around the leaf to white-balance, so no greenness")
    return dict(contour=cnt, centre=cen, radius=radius, hub_offset=off, landmarks=lm, outline=source,
                centroid_size_px=float(np.sqrt(((lm - lm.mean(0)) ** 2).sum())), area_px=area_px,
                perimeter_px=perim_px, roundness=4 * math.pi * area_px / perim_px ** 2, colour=col,
                warnings=warn, notes=notes, H=img.shape[0], W=img.shape[1]), None


def colour(img, cnt):
    """leaf_colour.py's measurement for one outline: dict(gcc, yellow_pct, glare_pct), or None when there is not
    enough paper around the leaf for the white balance. Only the leaf's own pixels are balanced (same numbers as
    balancing the whole photo, much less memory)."""
    mask = np.zeros(img.shape[:2], np.uint8)
    cv2.drawContours(mask, [cnt.astype(np.int32).reshape(-1, 1, 2)], -1, 255, cv2.FILLED)
    radius = np.sqrt(mask.sum() / 255 / np.pi)
    d_in = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    d_out = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    inner = d_in > max(3, 0.05 * radius)                                  # keep away from the edge
    ring = (d_out > 0.15 * radius) & (d_out < 0.35 * radius)
    if not ring.any() or not inner.any():
        return None
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # paper = bright, unsaturated pixels in a ring around the leaf (skips grid lines, stalks, shadow)
    paper = ring & (hsv[..., 1] < 45) & (hsv[..., 2] > np.percentile(hsv[..., 2][ring], 50))
    if paper.sum() < 500:
        return None
    white = img[paper].astype(float).mean(0)                              # B, G, R of the paper
    bal = np.clip(img[inner].astype(float) * (white.mean() / white), 0, 255).astype(np.uint8)
    px = bal.astype(float)
    gcc = float(np.mean(px[:, 1] / np.maximum(px.sum(1), 1)))
    hb = cv2.cvtColor(bal.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
    pale = (hb[:, 1] < 40) & (hb[:, 2] > 150)
    yellow = (~pale) & (hb[:, 0] < 30) & (hb[:, 1] > 60)                  # hue below yellow-green
    return dict(gcc=gcc, yellow_pct=100 * float(yellow.mean()), glare_pct=100 * float(pale.mean()))


def tps_record(res, image_name, rid, scale):
    """One tpsDig record: 13 landmarks with y measured up from the bottom, IMAGE, ID and SCALE (mm per pixel)."""
    H = res["H"]
    lines = [f"LM={len(res['landmarks'])}"] + [f"{x:.5f} {H - y:.5f}" for x, y in res["landmarks"]]
    lines += [f"IMAGE={image_name}", f"ID={rid}"]
    if scale:
        lines.append(f"SCALE={scale:.8f}")
    return lines


def check_picture(img, res, title):
    """Crop of the leaf with the outline, centre, hub and numbered landmarks drawn on, as in auto_landmarks' check
    sheets, labelled with the photo's ID and "ok" or "CHECK"."""
    cnt, cen, radius, lm = res["contour"], res["centre"], res["radius"], res["landmarks"]
    H, W = img.shape[:2]
    x0, y0 = np.maximum(cnt.min(0) - 0.15 * radius, 0).astype(int)
    x1, y1 = np.minimum(cnt.max(0) + 0.15 * radius, [W - 1, H - 1]).astype(int)
    crop = img[y0:y1, x0:x1].copy()
    sc = 700 / max(crop.shape[:2])
    crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    T = lambda p: (int((p[0] - x0) * sc), int((p[1] - y0) * sc))
    step = 5 if len(cnt) > 500 else 1                       # hand traces have few points: draw them all
    cv2.polylines(crop, [np.array([T(p) for p in cnt[::step]], np.int32)], True, (255, 200, 0), 2)
    cv2.line(crop, T(cen), T(lm[1]), (0, 255, 255), 1)
    cv2.drawMarker(crop, T(cen), (0, 255, 255), cv2.MARKER_CROSS, 14, 2)
    cv2.circle(crop, T(lm[0]), 6, (0, 0, 255), -1)
    cv2.putText(crop, "1", (T(lm[0])[0] + 6, T(lm[0])[1] - 6), 0, 0.6, (0, 0, 255), 2)
    for k, p in enumerate(lm[1:]):
        q = np.array(T(p))
        cv2.circle(crop, tuple(int(v) for v in q), 6, (0, 0, 255) if k else (0, 140, 255), -1)
        c = q + 18 * (q - np.array(T(lm[0]))) / max(np.linalg.norm(q - np.array(T(lm[0]))), 1)
        for colour_, w in (((0, 0, 0), 3), ((255, 255, 255), 1)):
            cv2.putText(crop, str(k + 2), (int(c[0]) - 8, int(c[1]) + 6), 0, 0.6, colour_, w)
    tile = np.full((crop.shape[0] + 40, max(crop.shape[1], 400) + 20, 3), 255, np.uint8)
    tile[0:crop.shape[0], 0:crop.shape[1]] = crop
    flag = res["warnings"]
    cv2.putText(tile, title + ("  CHECK" if flag else "  ok"), (8, crop.shape[0] + 28), 0, 0.6,
                (0, 0, 200) if flag else (0, 120, 0), 2)
    return tile
