"""Semi-automatic leaf landmarks for tpsDig/MorphoJ.

Input : a TPS file where each record has the vein hub as landmark 1 and a SCALE
        (any extra landmarks are ignored for placement, but used to report how
        far they lie from the detected edge).
Output: a TPS file with 13 landmarks per record
          LM1      = the hub, copied exactly from the input
          LM2      = edge point on the line from the leaf centre through the hub
          LM3-13   = edge points every 30 degrees, clockwise on screen
        plus one check-sheet JPEG per input file.

How the outline is found (segment + refine):
  1. colour: pixels that are green enough (hue 25-95, saturation >= 45), plus
     near-black pixels, which are leaf in deep shadow (the paper is never that dark)
  2. keep the green patch touching the hub; a morphological "opening" cuts off
     the thin stalk and anything joined to the leaf by a narrow neck
  3. GrabCut sharpens the edge using colour models of leaf vs paper, which drops
     the stalk base, light reflected onto the paper and similar greenish fringes
  4. if the hub ends up > 40% of the radius from the centre, a grey cast shadow
     was probably merged in: redo with a stricter colour test (saturation >= 90)
  5. if the record has a hand-traced outline (tpsDig curve), use that instead and
     report how far it lies from the detected edge
Then the 13 points: LM1 = your hub; the 12 o'clock line runs from the outline's
centre (area centroid) through the hub; LM2-13 = where lines every 30 degrees
from the hub cross the outline.

tpsDig stores y measured from the BOTTOM of the image; this script converts.
Usage : python auto_landmarks.py <input.tps> <image_dir> <output.tps> <checksheet.jpg>
"""
import math
import sys

import cv2
import numpy as np

WORK = 2          # downscale factor for segmentation
N_OUTLINE = 12    # landmarks 2-13


def read_tps(path):
    """Records with landmarks in "pts" and any tpsDig curves (POINTS= blocks) in "curves"."""
    recs, cur, curve = [], None, None
    for line in open(path, encoding="utf-8", errors="replace").read().splitlines():
        line = line.strip()
        if not line:
            continue
        up = line.upper()
        if up.startswith("LM="):
            cur = {"pts": [], "fields": {}, "curves": []}
            recs.append(cur)
            curve = None
        elif up.startswith("POINTS="):
            curve = []
            cur["curves"].append(curve)
        elif "=" in line:
            k, v = line.split("=", 1)
            cur["fields"][k.strip().upper()] = v.strip()
        elif curve is not None:
            curve.append(tuple(map(float, line.split())))
        else:
            cur["pts"].append(tuple(map(float, line.split())))
    return recs


def load_image(path):
    data = np.fromfile(path, dtype=np.uint8)
    # tpsDig shows raw pixels, so ignore any EXIF rotation
    return cv2.imdecode(data, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)


def fill_holes(mask):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(mask)
    cv2.drawContours(out, cnts, -1, 255, cv2.FILLED)
    return out


def component_at(mask, pt):
    n, lab = cv2.connectedComponents(mask)
    x, y = int(round(pt[0])), int(round(pt[1]))
    h, w = mask.shape
    for r in range(0, 60, 3):                      # hub may sit on a pale vein
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and lab[yy, xx] > 0:
                    return (lab == lab[yy, xx]).astype(np.uint8) * 255
    return None


def refine(small, leaf, hub_s, k):
    """Sharpen the first-pass leaf mask with GrabCut. Colour models learnt from the
    leaf and the paper separate the leaf from things next to it that are greenish
    but a different colour: the stalk base, light reflected onto the paper, and
    pale glare on the leaf edge. Returns None if it fails."""
    el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    r0 = cv2.distanceTransform(leaf, cv2.DIST_L2, 5).max()
    band = max(4, int(0.08 * r0))                  # how far the edge may move
    x, y, w, h = cv2.boundingRect(leaf)
    m = 3 * band
    x0, y0 = max(x - m, 0), max(y - m, 0)
    x1, y1 = min(x + w + m, leaf.shape[1]), min(y + h + m, leaf.shape[0])
    lf = leaf[y0:y1, x0:x1]
    mask = np.full(lf.shape, cv2.GC_BGD, np.uint8)
    mask[cv2.dilate(lf, el(band)) > 0] = cv2.GC_PR_BGD
    mask[lf > 0] = cv2.GC_PR_FGD
    mask[cv2.erode(lf, el(band)) > 0] = cv2.GC_FGD
    try:
        cv2.grabCut(small[y0:y1, x0:x1], mask, None, np.zeros((1, 65)), np.zeros((1, 65)), 5,
                    cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return None
    out = np.zeros_like(leaf)
    out[y0:y1, x0:x1] = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0)
    out = cv2.morphologyEx(out, cv2.MORPH_OPEN, el(k))   # stalk again, if it crept back
    out = component_at(out, hub_s)
    return None if out is None else fill_holes(out)


def segment(img, hub_px, s_min=45):
    small = cv2.resize(img, None, fx=1 / WORK, fy=1 / WORK, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    # leaf in shadow is dark (V ~25) but still saturated; grey paper is not.
    # Near-black (V < 25) is leaf in deep shadow: the paper is never that dark.
    mask = (((h >= 25) & (h <= 95) & (s >= s_min) & (v >= 12)) | (v < 25)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    mask = fill_holes(mask)
    hub_s = (hub_px[0] / WORK, hub_px[1] / WORK)
    comp = component_at(mask, hub_s)
    if comp is None:
        return None, "hub not on a green region"
    r0 = cv2.distanceTransform(comp, cv2.DIST_L2, 5).max()
    k = max(3, int(0.12 * r0))                     # removes the stalk and thin attachments
    opened = cv2.morphologyEx(comp, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
    leaf = component_at(opened, hub_s)
    if leaf is None:
        return None, "leaf vanished after stalk removal"
    leaf = fill_holes(leaf)
    removed = 1 - leaf.sum() / max(comp.sum(), 1)
    sharp = refine(small, leaf, hub_s, k)             # sharpen the edge; keep first pass if it fails
    if sharp is not None:
        leaf = sharp
    cnts, _ = cv2.findContours(leaf, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(cnts, key=cv2.contourArea).reshape(-1, 2).astype(float) * WORK + (WORK - 1) / 2
    notch = 0.0                                    # deepest bite into the outline, e.g. a missed shadow
    defects = cv2.convexityDefects(cnt.astype(np.int32).reshape(-1, 1, 2),
                                   cv2.convexHull(cnt.astype(np.int32).reshape(-1, 1, 2), returnPoints=False))
    if defects is not None:
        notch = defects.reshape(-1, 4)[:, 3].max() / 256.0
    border = (cnt[:, 0] < 5).any() or (cnt[:, 1] < 5).any() or \
             (cnt[:, 0] > img.shape[1] - 6).any() or (cnt[:, 1] > img.shape[0] - 6).any()
    return {"contour": cnt, "removed": removed, "touches_border": border, "notch": notch}, None


def stitch(curves):
    """Join a trace drawn in several pieces into one loop: always continue with the
    piece whose nearer end is closest to where the loop currently ends, reversing
    that piece if needed. Points are only reordered, never changed. A curve that is
    one point clicked repeatedly is a stray click, not part of the outline, and is skipped."""
    pieces = [list(c) for c in curves if len(set(map(tuple, c))) >= 2]
    if not pieces:
        return []
    loop = pieces.pop(0)
    while pieces:
        end = np.array(loop[-1])
        best = min(range(len(pieces)), key=lambda i: min(np.linalg.norm(end - pieces[i][0]),
                                                         np.linalg.norm(end - pieces[i][-1])))
        p = pieces.pop(best)
        if np.linalg.norm(end - p[-1]) < np.linalg.norm(end - p[0]):
            p = p[::-1]
        loop += p
    return loop


def outline_stats(seg, hub):
    return contour_stats(seg["contour"], hub)


def contour_stats(cnt, hub):
    m = cv2.moments(cnt.astype(np.float32))
    cen = np.array([m["m10"] / m["m00"], m["m01"] / m["m00"]])
    radius = math.sqrt(abs(m["m00"]) / math.pi)
    return cnt, cen, radius, np.linalg.norm(hub - cen) / radius


def ray_hit(origin, ang, poly):
    d = np.array([math.cos(ang), math.sin(ang)])
    a, b = poly, np.roll(poly, -1, axis=0)
    e = b - a
    den = d[0] * e[:, 1] - d[1] * e[:, 0]
    ok = np.abs(den) > 1e-12
    w = a - origin
    t = np.where(ok, (w[:, 0] * e[:, 1] - w[:, 1] * e[:, 0]) / np.where(ok, den, 1), -1)
    u = np.where(ok, (w[:, 0] * d[1] - w[:, 1] * d[0]) / np.where(ok, den, 1), -1)
    good = ok & (t > 1e-6) & (u >= 0) & (u <= 1)
    if not good.any():
        return None
    return origin + d * t[good].min()


def dist_to_poly(p, poly):
    a, b = poly, np.roll(poly, -1, axis=0)
    e = b - a
    t = np.clip(((p - a) * e).sum(1) / np.maximum((e * e).sum(1), 1e-12), 0, 1)
    return np.sqrt(((a + e * t[:, None] - p) ** 2).sum(1)).min()


def main(tps_in, img_dir, tps_out, sheet_out):
    recs = read_tps(tps_in)
    out_lines, tiles, report = [], [], []
    for i, r in enumerate(recs):
        f = r["fields"]
        name = f.get("IMAGE", "")
        img = load_image(f"{img_dir}/{name}")
        H = img.shape[0]
        hub_tps = r["pts"][0]
        hub = np.array([hub_tps[0], H - hub_tps[1]])          # to image rows
        flags = []
        seg, err = segment(img, hub)
        traced = stitch([[(x, H - y) for x, y in c] for c in r["curves"]])
        if len(traced) >= 10:                               # user traced the outline: use it instead
            cnt = np.array(traced, float)
            if seg is not None:                             # sanity check against the photo
                gap = np.median([dist_to_poly(p, seg["contour"]) for p in cnt]) / contour_stats(cnt, hub)[2]
                flags.append(f"used your traced outline (median {gap:.1%} of radius from detected edge)")
                if gap > 0.05:
                    flags.append("TRACE DOES NOT MATCH THE PHOTO - tpsDig zoom fault?")
            else:
                flags.append("used your traced outline")
            seg, err = {"contour": cnt, "notch": 0.0, "touches_border": False, "removed": 0.0}, None
        if err:
            report.append((name, None, [err, "NOT WRITTEN - click the hub again"]))
            continue
        cnt, cen, radius, off = outline_stats(seg, hub)
        if off > 0.40 and not traced:                       # hub far off-centre: usually a grey cast
            seg2, err2 = segment(img, hub, s_min=90)        # shadow merged in; retry, stricter colour
            if not err2:
                c2 = outline_stats(seg2, hub)
                if c2[3] < off:
                    seg, (cnt, cen, radius, off) = seg2, c2
                    flags.append("used strict colour test (shadow merged)")
        theta0 = math.atan2(hub[1] - cen[1], hub[0] - cen[0])
        pts = []
        for k in range(N_OUTLINE):                          # increasing angle = clockwise on screen
            p = ray_hit(hub, theta0 + k * 2 * math.pi / N_OUTLINE, cnt)
            if p is None:
                flags.append(f"no edge for LM{k + 2}")
            pts.append(p)
        if any(p is None for p in pts):                     # never write a broken record
            report.append((name, None, flags + ["NOT WRITTEN - click the hub again"]))
            continue
        if off < 0.08:
            flags.append(f"hub only {off:.0%} off-centre: 12 o'clock unreliable")
        if seg["notch"] / radius > 0.15:
            flags.append(f"outline has a notch {seg['notch'] / radius:.0%} of radius deep (shadow/glare?)")
        if seg["touches_border"]:
            flags.append("leaf touches photo edge")
        # agreement with any hand-placed edge points already in the file
        hand = [np.array([x, H - y]) for x, y in r["pts"][1:]]
        agree = None
        if hand:
            agree = max(dist_to_poly(p, cnt) for p in hand) / radius
            if agree > 0.05:
                flags.append(f"a hand edge point is {agree:.0%} of radius off the detected edge")
        report.append((name, (off, radius, agree), flags))
        # TPS record (y back to bottom-origin), hub copied exactly
        out_lines.append(f"LM={1 + N_OUTLINE}")
        out_lines.append(f"{hub_tps[0]:.5f} {hub_tps[1]:.5f}")
        for p in pts:
            out_lines.append(f"{p[0]:.5f} {H - p[1]:.5f}")
        out_lines.append(f"IMAGE={name}")
        out_lines.append(f"ID={f.get('ID', i)}")
        if "SCALE" in f:
            out_lines.append(f"SCALE={f['SCALE']}")
        # check tile
        x0, y0 = np.maximum(cnt.min(0) - 0.15 * radius, 0).astype(int)
        x1, y1 = np.minimum(cnt.max(0) + 0.15 * radius, [img.shape[1] - 1, H - 1]).astype(int)
        crop = img[y0:y1, x0:x1].copy()
        sc = 600 / max(crop.shape[:2])
        crop = cv2.resize(crop, None, fx=sc, fy=sc)
        T = lambda p: (int((p[0] - x0) * sc), int((p[1] - y0) * sc))
        step = 5 if len(cnt) > 500 else 1                   # hand traces have few points: draw them all
        cv2.polylines(crop, [np.array([T(p) for p in cnt[::step]], np.int32)], True, (255, 200, 0), 2)
        for p in hand:
            cv2.circle(crop, T(p), 4, (255, 0, 255), -1)
        cv2.line(crop, T(cen), T(pts[0]), (0, 255, 255), 1)
        cv2.drawMarker(crop, T(cen), (0, 255, 255), cv2.MARKER_CROSS, 14, 2)
        cv2.circle(crop, T(hub), 6, (0, 0, 255), -1)
        cv2.putText(crop, "1", (T(hub)[0] + 6, T(hub)[1] - 6), 0, 0.6, (0, 0, 255), 2)
        for k, p in enumerate(pts):
            q = T(p)
            cv2.circle(crop, q, 6, (0, 0, 255) if k else (0, 140, 255), -1)
            c = np.array(q) + 18 * (np.array(q) - np.array(T(hub))) / max(np.linalg.norm(np.array(q) - np.array(T(hub))), 1)
            cv2.putText(crop, str(k + 2), (int(c[0]) - 8, int(c[1]) + 6), 0, 0.6, (0, 0, 0), 3)
            cv2.putText(crop, str(k + 2), (int(c[0]) - 8, int(c[1]) + 6), 0, 0.6, (255, 255, 255), 1)
        tile = np.full((660, 620, 3), 255, np.uint8)
        tile[0:crop.shape[0], 0:crop.shape[1]] = crop
        cv2.putText(tile, name + ("  CHECK" if flags else "  ok"), (8, 650), 0, 0.6,
                    (0, 0, 200) if flags else (0, 120, 0), 2)
        tiles.append(tile)
    open(tps_out, "w", newline="").write("\r\n".join(out_lines) + "\r\n")
    if tiles:
        per_row = 6                                         # wrap long sheets into rows
        while len(tiles) > per_row and len(tiles) % per_row:
            tiles.append(np.full_like(tiles[0], 255))
        rows = [np.hstack(tiles[i:i + per_row]) for i in range(0, len(tiles), per_row)]
        cv2.imencode(".jpg", np.vstack(rows))[1].tofile(sheet_out)
    for name, stats, flags in report:
        s = "" if not stats else f"hub offset {stats[0]:.0%}  radius {stats[1]:.0f}px" + \
            ("" if stats[2] is None else f"  worst hand-point gap {stats[2]:.1%} of radius")
        print(f"  {name:16} {s}  {'; '.join(flags) or 'ok'}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
