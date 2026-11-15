"""Leaf area, perimeter and roundness from the same outlines that auto_landmarks.py uses.
For every record in the combined TPS file: rebuild the outline (colour mask + GrabCut, the strict-colour
retry for merged shadows, or the hand-traced outline where one exists), then measure it in mm with the
record's SCALE. Also reports how far the record's landmarks 2-13 sit from the rebuilt outline, as a check
that the outline is the one the landmarks were placed on. Reads only; writes one CSV.
Usage: python leaf_area.py <combined.tps> <hub file(s) with traced outlines, comma-separated> <image folder> <out.csv>
"""
import csv
import math
import sys

import cv2
import numpy as np

import auto_landmarks as A


def perimeter(cnt, smooth):
    """Outline length. Pixel outlines are smoothed first (circular moving average) so the
    staircase of pixel edges does not inflate the length; hand traces are used as drawn."""
    if smooth > 1:
        k = np.ones(smooth) / smooth
        pad = np.vstack([cnt[-smooth:], cnt, cnt[:smooth]])
        cnt = np.column_stack([np.convolve(pad[:, j], k, "same") for j in (0, 1)])[smooth:-smooth]
    return float(np.sqrt((np.diff(np.vstack([cnt, cnt[:1]]), axis=0) ** 2).sum(1)).sum())


def main(tps, traced_tps, img_dir, out_csv):
    traced = {r["fields"]["IMAGE"]: r["curves"] for path in traced_tps.split(",")      # comma-separated files allowed
              for r in A.read_tps(path) if r["curves"]}
    rows = []
    for r in A.read_tps(tps):
        f = r["fields"]
        name, rid, scale = f["IMAGE"], f["ID"], float(f["SCALE"])
        img = A.load_image(f"{img_dir}/{name}")
        H = img.shape[0]
        hub = np.array([r["pts"][0][0], H - r["pts"][0][1]])
        seg, err = A.segment(img, hub)
        trace = A.stitch([[(x, H - y) for x, y in c] for c in traced.get(name, [])])
        if len(trace) >= 10:
            cnt, source = np.array(trace, float), "hand-traced"
        else:
            if err:
                print(f"  {rid}: {err} - skipped")
                continue
            cnt, cen, radius, off = A.outline_stats(seg, hub)
            source = "auto"
            if off > 0.40:
                seg2, err2 = A.segment(img, hub, s_min=90)
                if not err2:
                    c2 = A.outline_stats(seg2, hub)
                    if c2[3] < off:
                        cnt, source = c2[0], "auto (strict colour)"
        area_px = abs(cv2.contourArea(cnt.astype(np.float32)))
        perim_px = perimeter(cnt, 1 if source == "hand-traced" else 5)
        radius = math.sqrt(area_px / math.pi)
        lm = [np.array([x, H - y]) for x, y in r["pts"][1:]]
        gap = max(A.dist_to_poly(p, cnt) for p in lm) / radius
        area, perim = area_px * scale ** 2, perim_px * scale
        rows.append([rid, rid[:2], rid[3:6], int(rid[-2:]), name, round(area_px), round(perim_px, 1), scale,
                     round(area, 1), round(perim, 2), round(4 * math.pi * area / perim ** 2, 4), source, round(100 * gap, 2)])
        print(f"  {rid:12} {area:8.1f} mm2  {perim:6.1f} mm  roundness {rows[-1][10]:.3f}  {source:20} landmark gap {100 * gap:.2f}% of radius")
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ID", "condition", "leaf", "day", "image", "area_px", "perimeter_px", "scale_mm_per_px",
                    "area_mm2", "perimeter_mm", "roundness", "outline_source", "landmark_gap_pct_radius"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out_csv}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
