"""Figure 12: what Procrustes superimposition does. Left: every photo's landmarks in mm as photographed
(centred only). Right: after Procrustes (same size, centre and rotation), with the average shape.
Usage: python fig12_procrustes.py <combined.tps> <out file stem, e.g. ../3_results/poster_figures/fig12_procrustes_v3>
"""
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import auto_landmarks as A
from growth_allometry import procrustes

LOW, HIGH, INK, QUIET = "#1f6fd1", "#8a8a8a", "#222222", "#666666"
plt.rcParams.update({"font.family": "Arial", "font.size": 11, "svg.fonttype": "none"})
tps, stem = sys.argv[1:3]
R = A.read_tps(tps)
n = len(R)
cond = [r["fields"]["ID"][:2] for r in R]
raw = [np.array(r["pts"]) * float(r["fields"]["SCALE"]) for r in R]          # mm, as photographed
V = procrustes(np.array([[complex(*p) for p in r["pts"]] for r in R]))
Z = V[:, :13] + 1j * V[:, 13:]
cons = Z.mean(0)
rot = np.exp(1j * (np.pi / 2 - np.angle(cons[1] - cons[0])))
fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
ax = axes[0]
for p, c in zip(raw, cond):
    q = p - p.mean(0)
    ring = np.vstack([q[1:], q[1]])
    ax.plot(ring[:, 0], ring[:, 1], color=LOW if c == "mh" else HIGH, alpha=0.25, linewidth=0.8)
    ax.scatter(q[0, 0], q[0, 1], s=6, color=LOW if c == "mh" else HIGH, alpha=0.5)
ax.set_title(f"Before: {n} leaves as photographed\n(different sizes, positions and rotations)", fontsize=12, color=INK)
ax = axes[1]
for z, c in zip(Z, cond):
    z = z * rot
    ring = np.append(z[1:], z[1])
    ax.plot(ring.real, ring.imag, color=LOW if c == "mh" else HIGH, alpha=0.25, linewidth=0.8)
    ax.scatter(z.real, z.imag, s=4, color=LOW if c == "mh" else HIGH, alpha=0.4)
m = cons * rot
ring = np.append(m[1:], m[1])
ax.plot(ring.real, ring.imag, color=INK, linewidth=2.4, label="average shape")
ax.scatter(m.real, m.imag, s=22, color=INK, zorder=5)
ax.set_title("After Procrustes: same size, centre and rotation\n(only shape differences are left)", fontsize=12, color=INK)
for a in axes:
    a.set_aspect("equal")
    a.axis("off")
axes[1].plot([], [], color=LOW, label="Low humidity")
axes[1].plot([], [], color=HIGH, label="High humidity")
axes[1].legend(frameon=False, loc="lower center", bbox_to_anchor=(-0.1, -0.1), ncol=3, fontsize=11)
fig.suptitle(f"Procrustes superimposition of all {n} leaf photos (13 landmarks each)", x=0.03, ha="left",
             fontsize=14, fontweight="bold", color=INK)
for ext in ("png", "svg"):
    fig.savefig(f"{stem}.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
print("wrote", stem)
