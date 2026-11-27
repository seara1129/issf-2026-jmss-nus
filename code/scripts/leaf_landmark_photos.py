"""Real leaf photos with their 13 landmarks drawn on, in the style of the poster's method diagram: white dots (landmark 2
orange), the hub as a black "1", the dashed 12 o'clock line from the leaf centre through the hub, thin rays from the
hub to each landmark, and the outline the program found. Landmarks are the project's own (combined_v6.tps); the
outline and centre are rebuilt the way auto_landmarks.py found them. One square picture per photo (no text), plus a
2 x 2 panel with labels when four IDs are given (rows = tanks, columns = days). Transparent outside the photos.
--plain draws only the 13 landmarks as red dots, as on the project's check sheets: no numbers, lines, outline or
panel labels.
Usage: python leaf_landmark_photos.py <morpho folder> <version> [--plain] <ID> [ID ...]   e.g. mh_L02_D01 mh_L02_D26 ...
Writes 3_results/poster_figures/a0/leaf_landmark_photos/<ID>_landmarks_<v>.png (1500 px) and panel_<v>.png.
"""
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

import auto_landmarks as A

root, ver = sys.argv[1], sys.argv[2]
plain = "--plain" in sys.argv[3:]
ids = [a for a in sys.argv[3:] if not a.startswith("--")]
RED = "#e8281e"
out = os.path.join(root, "3_results", "poster_figures", "a0", "leaf_landmark_photos")
os.makedirs(out, exist_ok=True)
DARK, ORANGE, INK = "#25451a", "#d9822b", "#222222"
plt.rcParams.update({"font.family": "Arial"})
v6 = {r["fields"]["ID"]: r for r in A.read_tps(os.path.join(root, "2_landmarks", "mh-sh_L01-L14_D01-D26_combined_v6.tps"))}


def leaf(rid):
    """Square crop of the photo around the leaf, with landmarks, outline and centre in crop pixels."""
    r = v6[rid]
    img = A.load_image(os.path.join(root, "1_photos_tpsdig", r["fields"]["IMAGE"]))
    H, W = img.shape[:2]
    pts = np.array([(x, H - y) for x, y in r["pts"]])               # tps y runs up from the bottom
    seg, err = A.segment(img, pts[0])
    if err:
        raise SystemExit(f"{rid}: {err}")
    cnt, cen, radius, off = A.outline_stats(seg, pts[0])
    if off > 0.40:                                                  # same shadow retry as auto_landmarks.main
        seg2, err2 = A.segment(img, pts[0], s_min=90)
        if not err2 and A.outline_stats(seg2, pts[0])[3] < off:
            cnt, cen, radius, off = A.outline_stats(seg2, pts[0])
    c = (cnt.min(0) + cnt.max(0)) / 2
    half = (cnt.max(0) - cnt.min(0)).max() / 2 + 0.30 * radius      # room for the numbers outside the edge
    x0, y0 = np.maximum((c - half).astype(int), 0)
    x1, y1 = np.minimum((c + half).astype(int), [W, H])
    crop = img[y0:y1, x0:x1, ::-1]                                   # BGR -> RGB
    shift = np.array([x0, y0])
    return crop, pts - shift, cnt - shift, cen - shift


def draw(ax, crop, pts, cnt, cen):
    S = max(crop.shape[:2])
    ax.imshow(crop)
    ax.set_xlim(0, crop.shape[1])
    ax.set_ylim(crop.shape[0], 0)
    ax.axis("off")
    if plain:                                                        # just the 13 landmarks, red as on the check sheets
        for p in pts:
            ax.add_patch(Circle(p, 0.013 * S, facecolor=RED, edgecolor="white", lw=1.2, zorder=5))
        return
    hub = pts[0]
    stroke = [pe.withStroke(linewidth=3.2, foreground=DARK)]
    ax.plot(*np.vstack([cnt, cnt[:1]]).T, color="white", lw=1.4, alpha=0.75)       # the outline the program found
    for p in pts[1:]:
        ax.plot([hub[0], p[0]], [hub[1], p[1]], color="white", lw=1.1, alpha=0.8)
    ax.plot([cen[0], pts[1][0]], [cen[1], pts[1][1]], color=ORANGE, lw=2.2, ls=(0, (5, 3)))
    ax.plot([cen[0]], [cen[1]], marker="+", ms=13, mew=2.6, color=ORANGE)
    rd = 0.016 * S
    for k, p in enumerate(pts[1:]):
        ax.add_patch(Circle(p, rd, facecolor=ORANGE if k == 0 else "white", edgecolor=DARK, lw=1.6, zorder=5))
        u = (p - hub) / np.linalg.norm(p - hub)
        q = p + u * 3.4 * rd
        ax.text(*q, str(k + 2), fontsize=12, fontweight="bold", color="white", ha="center", va="center", zorder=6,
                path_effects=stroke)
    ax.add_patch(Circle(hub, 1.15 * rd, facecolor=INK, edgecolor="white", lw=1.4, zorder=6))
    ax.text(hub[0] - 3.0 * rd, hub[1] - 2.4 * rd, "1", fontsize=12, fontweight="bold", color="white", ha="center",
            va="center", zorder=7, bbox=dict(boxstyle="circle,pad=0.18", facecolor=INK, edgecolor="none"))


leaves = {rid: leaf(rid) for rid in ids}
for rid, parts in leaves.items():
    p = os.path.join(out, f"{rid}_landmarks_{ver}.png")
    if os.path.exists(p):
        raise SystemExit(f"{p} already exists - not overwriting")
    fig = plt.figure(figsize=(5, 5 * parts[0].shape[0] / parts[0].shape[1]))
    draw(fig.add_axes([0, 0, 1, 1]), *parts)
    fig.savefig(p, dpi=300)
    plt.close(fig)
    print("wrote", os.path.basename(p))

if len(ids) == 4:                                                    # rows: tanks, columns: days
    p = os.path.join(out, f"panel_{ver}.png")
    if os.path.exists(p):
        raise SystemExit(f"{p} already exists - not overwriting")
    fig, axes = plt.subplots(2, 2, figsize=(9, 9.6), gridspec_kw=dict(wspace=0.04, hspace=0.12))
    tank = {"mh": "Low humidity (Melbourne-like)", "sh": "High humidity (Singapore-like)"}
    for ax, rid in zip(axes.ravel(), ids):
        draw(ax, *leaves[rid])
        if not plain:
            ax.set_title(f"{tank[rid[:2]]} · Day {int(rid[-2:])}", fontsize=13, fontweight="bold", color=DARK, pad=6)
    fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.08, transparent=True)
    print("wrote", os.path.basename(p))
