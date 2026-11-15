"""Check sheets for every photo in a combined TPS file: the outline the landmarks sit on (hand trace where one
exists, else the automatic one) and the 13 landmarks, one sheet per tank, rows = leaves, columns = days.
Usage: python check_grid.py <combined.tps> <traced files, comma-separated> <image folder> <out folder> [pending images, comma-separated]
"""
import os
import sys

import cv2
import numpy as np

import auto_landmarks as A

TILE, LABEL = 360, 34


def outline(img, hub, curves, H):
    trace = A.stitch([[(x, H - y) for x, y in c] for c in curves])
    if len(trace) >= 10:
        return np.array(trace, float), "traced"
    seg, err = A.segment(img, hub)
    if err:
        return None, err
    cnt, cen, rad, off = A.outline_stats(seg, hub)
    if off > 0.40:
        seg2, err2 = A.segment(img, hub, s_min=90)
        if not err2 and A.outline_stats(seg2, hub)[3] < off:
            cnt = A.outline_stats(seg2, hub)[0]
    return cnt, "auto"


def main(tps, traced_files, img_dir, out_dir, pending=""):
    traced = {r["fields"]["IMAGE"]: r["curves"] for f in traced_files.split(",") for r in A.read_tps(f) if r["curves"]}
    pending = set(p for p in pending.split(",") if p)
    ver = os.path.splitext(os.path.basename(tps))[0].rsplit("_", 1)[-1]     # e.g. v5 from ..._combined_v5.tps
    tiles = {}
    for r in A.read_tps(tps):
        f = r["fields"]
        img = A.load_image(f"{img_dir}/{f['IMAGE']}")
        H = img.shape[0]
        pts = np.array([(x, H - y) for x, y in r["pts"]])
        cnt, how = outline(img, pts[0], traced.get(f["IMAGE"], []), H)
        c = pts.mean(0)
        half = 1.2 * np.abs(pts - c).max()
        x0, y0 = int(max(c[0] - half, 0)), int(max(c[1] - half, 0))
        crop = img[y0:int(min(c[1] + half, H)), x0:int(min(c[0] + half, img.shape[1]))].copy()
        s = TILE / max(crop.shape[:2])
        crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        T = lambda p: (int((p[0] - x0) * s), int((p[1] - y0) * s))
        if cnt is not None:
            cv2.polylines(crop, [np.array([T(p) for p in cnt[::3]], np.int32)], True, (255, 200, 0), 2)
        for k, p in enumerate(pts):
            cv2.circle(crop, T(p), 5 if k else 6, (0, 0, 255) if k else (0, 140, 255), -1)
        tile = np.full((TILE + LABEL, TILE, 3), 255, np.uint8)
        tile[:crop.shape[0], :crop.shape[1]] = crop
        name = f["IMAGE"][:-4]
        status = "TO TRACE" if f["IMAGE"] in pending else ("traced" if how == "traced" else "ok")
        colour = (0, 0, 200) if status == "TO TRACE" else (0, 110, 0)
        cv2.putText(tile, f"{name}  {status}", (6, TILE + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2)
        tiles[f["ID"]] = tile
        print(f"  {f['ID']}: {status}", flush=True)
    for cond in ("mh", "sh"):
        ids = [i for i in tiles if i.startswith(cond)]
        leaves = sorted({i[3:6] for i in ids})
        days = range(1, max(int(i[-2:]) for i in ids) + 1)
        L, TOP = 110, 60
        sheet = np.full((TOP + (TILE + LABEL) * len(leaves), L + TILE * len(days), 3), 255, np.uint8)
        for j, d in enumerate(days):
            cv2.putText(sheet, f"Day {d}", (L + j * TILE + 120, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 2)
        for i, lf in enumerate(leaves):
            cv2.putText(sheet, lf, (12, TOP + i * (TILE + LABEL) + 200), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3)
            for j, d in enumerate(days):
                t = tiles.get(f"{cond}_{lf}_D{d:02d}")
                if t is not None:
                    y, x = TOP + i * (TILE + LABEL), L + j * TILE
                    sheet[y:y + t.shape[0], x:x + t.shape[1]] = t
        out = os.path.join(out_dir, f"all_{cond}_D01-D{max(days):02d}_check_{ver}.jpg")
        cv2.imencode(".jpg", sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tofile(out)
        print("wrote", out, sheet.shape[1], "x", sheet.shape[0])


if __name__ == "__main__":
    main(*sys.argv[1:6])
