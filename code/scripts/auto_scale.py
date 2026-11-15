"""Read the grid-paper scale (mm per pixel) from a photo automatically.

How:
  1. take the paper around the leaf (leaf, soil, tags, deep shadow and glare masked out)
  2. find the directions of the two families of grid lines (2D Fourier transform: only the direction is used)
  3. for each family, add up the darkness of the paper along the lines, giving a profile with one sharp
     dip per grid line; the spacing comes from the profile's autocorrelation, then a straight-line fit of
     the line positions against their number (many lines, so the spacing is found to a fraction of a pixel)
  4. SCALE = 5 mm (one grid square) / spacing, averaged over the two directions (they differ a little when
     the phone was tilted), in the raw pixel frame tpsDig uses.

Usage:
  python auto_scale.py validate <combined.tps> <image folder> <out.csv>   compare with the SCALE lines in the file
  python auto_scale.py measure <list.tps> <image folder> <out.csv>        scales for photos without one
"""
import csv
import math
import sys

import cv2
import numpy as np

import auto_landmarks as A

SQUARE_MM = 5.0
WORK = 2                       # work at half resolution: a grid square is ~60-155 px there
T_MIN, T_MAX = 45, 220         # accepted square size at half resolution (full-res scale ~0.011-0.056 mm/px)


def leaf_box(small):
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    green = (((h >= 25) & (h <= 95) & (s >= 45) & (v >= 12)) | (v < 25)).astype(np.uint8) * 255
    blob = cv2.morphologyEx(green, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    n, lab, st, cen = cv2.connectedComponentsWithStats(blob)
    if n < 2:
        return None, green
    i = 1 + int(np.argmax(st[1:, 4]))
    return (cen[i], max(st[i, 2], st[i, 3])), green


def line_directions(lines, ok):
    """Angles (radians) of the normals of the two grid-line families."""
    x = np.where(ok, lines, 0).astype(np.float64)
    x *= np.outer(np.hanning(x.shape[0]), np.hanning(x.shape[1]))
    pad = 2048
    F = np.abs(np.fft.fftshift(np.fft.fft2(x, (pad, pad))))
    f = np.fft.fftshift(np.fft.fftfreq(pad))
    FX, FY = np.meshgrid(f, f)
    R, ang = np.hypot(FX, FY), np.arctan2(FY, FX)
    ring = (R > 1 / T_MAX) & (R < 0.2) & (FY >= 0)
    k1 = np.unravel_index(np.argmax(np.where(ring, F, 0)), F.shape)
    a1 = ang[k1]
    perp = np.abs(((ang - a1 - np.pi / 2) + np.pi / 2) % np.pi - np.pi / 2) < np.radians(20)
    k2 = np.unravel_index(np.argmax(np.where(ring & perp, F, 0)), F.shape)
    return a1, ang[k2]


def spacing(lines, ok, a):
    """Grid spacing (px) along normal direction a, and the number of lines used."""
    yy, xx = np.nonzero(ok)
    u = xx * math.cos(a) + yy * math.sin(a)
    u -= u.min()
    b = np.round(u).astype(int)
    cnt = np.bincount(b)
    prof = np.bincount(b, weights=lines[yy, xx]) / np.maximum(cnt, 1)
    good = cnt > 0.25 * np.median(cnt[cnt > 0])
    prof = np.where(good, prof, 0.0)
    prof = cv2.GaussianBlur(prof.reshape(1, -1).astype(np.float32), (0, 0), 1.0).ravel()
    # autocorrelation: first strong peak = one square (a line comb has nothing at half a square)
    p = prof - prof[good].mean()
    p[~good] = 0
    ac = np.correlate(p, p, "full")[len(p) - 1:]
    ac /= ac[0] if ac[0] else 1
    lag = np.arange(len(ac))
    cand = [i for i in range(T_MIN, min(T_MAX, len(ac) - 1)) if ac[i] >= ac[i - 1] and ac[i] >= ac[i + 1] and ac[i] > 0.15]
    if not cand:
        return None, 0
    t0 = max(cand, key=lambda i: ac[i]) if ac[cand[0]] < 0.6 * max(ac[i] for i in cand) else cand[0]
    # line positions near the comb predicted by t0, refined to sub-pixel, then a straight-line fit
    peaks = [i for i in range(2, len(prof) - 2) if good[i] and prof[i] == prof[i - 2:i + 3].max()]
    if not peaks:
        return None, 0
    start = max(peaks, key=lambda i: prof[i]) % t0
    pos, idx = [], []
    for n in range(int((len(prof) - start) / t0) + 1):
        c = start + n * t0
        lo, hi = int(max(c - 0.2 * t0, 1)), int(min(c + 0.2 * t0, len(prof) - 2))
        if hi <= lo or not good[lo:hi + 1].all():
            continue
        j = lo + int(np.argmax(prof[lo:hi + 1]))
        if prof[j] <= np.percentile(prof[good], 75):
            continue
        a_, b_, c_ = prof[j - 1], prof[j], prof[j + 1]
        den = a_ - 2 * b_ + c_
        pos.append(j + (0.5 * (a_ - c_) / den if den else 0))
        idx.append(n)
    if len(pos) < 4:
        return None, len(pos)
    pos, idx = np.array(pos), np.array(idx, float)
    for _ in range(2):                                             # drop lines that sit off the fitted comb
        T, c0 = np.polyfit(idx, pos, 1)
        res = np.abs(pos - (c0 + T * idx))
        keep = res < 0.12 * T
        if keep.sum() < 4:
            break
        pos, idx = pos[keep], idx[keep]
    T, _ = np.polyfit(idx, pos, 1)
    return T, len(pos)


def grid_scale(img):
    small = cv2.resize(img, None, fx=1 / WORK, fy=1 / WORK, interpolation=cv2.INTER_AREA)
    H, W = small.shape[:2]
    box, green = leaf_box(small)
    (cx, cy), d = box if box else ((W / 2, H / 2), min(W, H) / 3)
    half = int(min(max(1.4 * d, 700), max(W, H)) / 2)
    x0, x1 = int(max(cx - half, 0)), int(min(cx + half, W))
    y0, y1 = int(max(cy - half, 0)), int(min(cy + half, H))
    crop = small[y0:y1, x0:x1]
    _, s, v = cv2.split(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV))
    bad = cv2.dilate(green[y0:y1, x0:x1], cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41))) > 0
    bad |= (s > 70) | (v < 35) | (v > 250)                         # tags, soil, deep shadow, glare
    ok = ~(cv2.dilate(bad.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
    if ok.mean() < 0.15:
        return None, {"note": "too little clear paper"}
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lines = cv2.GaussianBlur(g, (0, 0), 6) - g                      # positive on thin dark lines
    lines /= cv2.GaussianBlur(np.abs(lines), (0, 0), 30) + 1.0     # equal weight in shadow and in light
    a1, a2 = line_directions(lines, ok)
    out = []
    for a in (a1, a2):
        T, n = spacing(lines, ok, a)
        if T is None:
            return None, {"note": f"grid lines not found ({n} lines)"}
        out.append((T * WORK, n))
    (p1, n1), (p2, n2) = out
    tilt = 100 * abs(p1 - p2) / ((p1 + p2) / 2)
    note = ""
    if tilt <= 10:
        scale = SQUARE_MM / math.sqrt(p1 * p2)
    else:                                        # directions disagree: one picked up something else (shadow edge, tank rim)
        return None, {"note": f"directions disagree ({p1:.0f} vs {p2:.0f} px) - measure by hand"}
    return scale, {"square_px_dir1": round(p1, 2), "square_px_dir2": round(p2, 2),
                   "lines_used": f"{n1}+{n2}", "tilt_pct": round(tilt, 2),
                   "grid_angle_deg": round(math.degrees(a1) % 90, 1), "note": note}


def main(mode, tps, img_dir, out_csv):
    rows = []
    for r in A.read_tps(tps):
        f = r["fields"]
        img = A.load_image(f"{img_dir}/{f['IMAGE']}")
        sc, info = grid_scale(img)
        row = {"ID": f.get("ID", ""), "image": f["IMAGE"], "auto_scale": "" if sc is None else round(sc, 6), **info}
        if mode == "validate":
            hand = float(f["SCALE"])
            row["hand_scale"] = hand
            row["diff_pct"] = "" if sc is None else round(100 * (sc - hand) / hand, 2)
        rows.append(row)
        print(f"  {row['image']:18} auto {row['auto_scale']}" + (f"  hand {row['hand_scale']}  diff {row['diff_pct']}%" if mode == "validate" else "")
              + f"  {info}")
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, keys)
        w.writeheader()
        w.writerows(rows)
    if mode == "validate":
        d = np.array([r["diff_pct"] for r in rows if r["diff_pct"] != ""], float)
        print(f"\n{len(d)} of {len(rows)} photos measured; difference auto vs hand: median {np.median(d):+.2f}%, "
              f"median |diff| {np.median(np.abs(d)):.2f}%, within 2%: {np.mean(np.abs(d) <= 2):.0%}, within 5%: {np.mean(np.abs(d) <= 5):.0%}, "
              f"worst {d[np.argmax(np.abs(d))]:+.1f}%")


if __name__ == "__main__":
    main(*sys.argv[1:5])
