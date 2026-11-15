"""Leaf colour (greenness / yellowing) for every photo in a combined TPS file.

For each record: find the leaf outline the same way auto_landmarks.py does (or use
a hand-traced outline if one exists for that photo), white-balance the photo
against the grid paper around the leaf, then measure the colour inside the leaf.

Output CSV columns:
  gcc        green chromatic coordinate G/(R+G+B) inside the leaf, after white
             balance (higher = greener)
  yellow_pct % of leaf pixels whose hue is yellow-brown rather than green
  glare_pct  % of leaf pixels that are very pale (glare); high values = less reliable
Usage: python leaf_colour.py <combined.tps> <image_dir> <traced_outlines.tps[,more.tps]|-> <out.csv>
"""
import csv
import sys

import cv2
import numpy as np

import auto_landmarks as A


def leaf_mask(img, hub, traced):
    if traced:
        cnt = np.array(traced, float)
    else:
        seg, err = A.segment(img, hub)
        if err:
            return None, err
        cnt = seg["contour"]
        if A.outline_stats(seg, hub)[3] > 0.40:              # same shadow retry as the landmarks
            seg2, err2 = A.segment(img, hub, s_min=90)
            if not err2 and A.outline_stats(seg2, hub)[3] < A.outline_stats(seg, hub)[3]:
                cnt = seg2["contour"]
    mask = np.zeros(img.shape[:2], np.uint8)
    cv2.drawContours(mask, [cnt.astype(np.int32).reshape(-1, 1, 2)], -1, 255, cv2.FILLED)
    return mask, None


def main(tps, img_dir, traced_tps, out_csv):
    traced = {}
    if traced_tps != "-":
        for path in traced_tps.split(","):                   # several files allowed, comma-separated
            for r in A.read_tps(path):
                if r["curves"]:
                    traced[r["fields"]["IMAGE"]] = r["curves"]
    rows = []
    for r in A.read_tps(tps):
        name, pid = r["fields"]["IMAGE"], r["fields"]["ID"]
        img = A.load_image(f"{img_dir}/{name}")
        H = img.shape[0]
        hub = np.array([r["pts"][0][0], H - r["pts"][0][1]])
        tr = A.stitch([[(x, H - y) for x, y in c] for c in traced.get(name, [])])
        mask, err = leaf_mask(img, hub, tr if len(tr) >= 10 else None)
        if err:
            print(f"  {pid}: {err}")
            continue
        radius = np.sqrt(mask.sum() / 255 / np.pi)
        # distances to the leaf edge (fast, unlike erode/dilate with huge kernels on 12 MP photos)
        d_in = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        d_out = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
        inner = ((d_in > max(3, 0.05 * radius)) * 255).astype(np.uint8)  # keep away from the edge
        ring = (((d_out > 0.15 * radius) & (d_out < 0.35 * radius)) * 255).astype(np.uint8)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # paper = bright, unsaturated pixels in a ring around the leaf (skips grid lines, stalks, shadow)
        paper = (ring > 0) & (hsv[..., 1] < 45) & (hsv[..., 2] > np.percentile(hsv[..., 2][ring > 0], 50))
        if paper.sum() < 500:
            print(f"  {pid}: not enough paper around the leaf for white balance")
            continue
        white = img[paper].astype(float).mean(0)                         # B, G, R of the paper
        bal = np.clip(img.astype(float) * (white.mean() / white), 0, 255).astype(np.uint8)
        px = bal[inner > 0].astype(float)
        b, g, rr = px[:, 0], px[:, 1], px[:, 2]
        gcc = float(np.mean(g / np.maximum(b + g + rr, 1)))
        hb = cv2.cvtColor(bal, cv2.COLOR_BGR2HSV)[inner > 0]
        pale = (hb[:, 1] < 40) & (hb[:, 2] > 150)
        yellow = (~pale) & (hb[:, 0] < 30) & (hb[:, 1] > 60)            # hue below yellow-green
        rows.append(dict(ID=pid, condition=pid[:2], leaf=pid[3:6], day=int(pid[-2:]), image=name,
                         gcc=f"{gcc:.4f}", yellow_pct=f"{100 * yellow.mean():.2f}",
                         glare_pct=f"{100 * pale.mean():.2f}", traced="yes" if len(tr) >= 10 else ""))
        print(f"  {pid}: gcc {gcc:.3f}  yellow {100 * yellow.mean():5.1f}%  glare {100 * pale.mean():5.1f}%", flush=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main(*sys.argv[1:5])
