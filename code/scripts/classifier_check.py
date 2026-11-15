"""Can a simple model tell which tank a leaf photo came from? (exploratory; not part of the 18 Oct analysis plan)

Inputs per photo (Days 2-26; Day 1 is the baseline): shape PC1-PC5 (Procrustes coordinates, PCA fitted on the training
photos only), greenness (GCC) and yellow-brown share. Model: L2-penalised logistic regression (numpy, IRLS), features
standardised on the training photos only.
  wrong way  : photos split at random into 5 folds (20 repeats) - photos of the same leaf end up in training AND test.
  right way  : leave one whole leaf out at a time; score every photo of that leaf, and the leaf (mean probability > 0.5).
  baseline   : the right way with tank labels shuffled between leaves (group sizes kept), 500 times.
  fingerprint: for each photo, is its nearest other photo (same standardised features) a photo of the same leaf?
Usage: python classifier_check.py <morpho folder> <version>
Writes 3_results/classifier_check_<v>.csv, classifier_per_leaf_<v>.csv and poster_figures/fig29_classifier_check_<v>.png/.svg
"""
import csv
import math
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import auto_landmarks as A
from growth_allometry import procrustes

root, ver = sys.argv[1:3]
res = os.path.join(root, "3_results")
OUT, OUT_LEAF = os.path.join(res, f"classifier_check_{ver}.csv"), os.path.join(res, f"classifier_per_leaf_{ver}.csv")
for p in (OUT, OUT_LEAF):
    if os.path.exists(p):
        raise SystemExit(f"{p} already exists - not overwriting")
RNG = np.random.default_rng(2026)
N_PC, LAM, N_NULL, N_REP = 5, 1.0, 500, 20

# ---------- data: one row per photo ----------
R = [r for r in A.read_tps(os.path.join(root, "2_landmarks", "mh-sh_L01-L14_D01-D26_combined_v6.tps"))
     if int(r["fields"]["ID"][-2:]) >= 2]
ids = [r["fields"]["ID"] for r in R]
V = procrustes(np.array([[complex(*p) for p in r["pts"]] for r in R]))          # no labels used here
col = {r["ID"]: r for r in csv.DictReader(open(os.path.join(res, "leaf_colour_v4.csv"), encoding="utf-8"))}
C = np.array([[float(col[i]["gcc"]), float(col[i]["yellow_pct"])] for i in ids])
leaf = np.array([i[:6] for i in ids])
y = np.array([1.0 if i.startswith("mh") else 0.0 for i in ids])                # 1 = Low (dry) tank
leaves = sorted(set(leaf))
print(f"{len(ids)} photos, {len(leaves)} leaves ({sum(l.startswith('mh') for l in leaves)} Low, "
      f"{sum(l.startswith('sh') for l in leaves)} High)")


def features(train, test):
    """Shape PCs from the training photos only, plus colour; standardised on the training photos."""
    mu = V[train].mean(0)
    _, _, vt = np.linalg.svd(V[train] - mu, full_matrices=False)
    P = (V - mu) @ vt[:N_PC].T
    X = np.hstack([P, C])
    m, s = X[train].mean(0), X[train].std(0) + 1e-12
    X = (X - m) / s
    return X[train], X[test]


def fit(X, t):
    """L2 logistic regression by iteratively reweighted least squares."""
    Xb = np.hstack([np.ones((len(X), 1)), X])
    w = np.zeros(Xb.shape[1])
    pen = LAM * np.eye(Xb.shape[1])
    pen[0, 0] = 0
    for _ in range(50):
        p = 1 / (1 + np.exp(-Xb @ w))
        g = Xb.T @ (p - t) + pen @ w
        H = Xb.T @ (Xb * (p * (1 - p))[:, None]) + pen
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return w


def prob(w, X):
    return 1 / (1 + np.exp(-(np.hstack([np.ones((len(X), 1)), X]) @ w)))


def leave_one_leaf_out(labels):
    pr = np.zeros(len(ids))
    for l in leaves:
        te = leaf == l
        Xtr, Xte = features(~te, te)
        pr[te] = prob(fit(Xtr, labels[~te]), Xte)
    photo_acc = float(np.mean((pr > 0.5) == (labels == 1)))
    leaf_hit = {l: (pr[leaf == l].mean() > 0.5) == (labels[leaf == l][0] == 1) for l in leaves}
    return photo_acc, leaf_hit, pr


def random_split():
    accs = []
    for _ in range(N_REP):
        order = RNG.permutation(len(ids))
        hits = np.zeros(len(ids), bool)
        for k in range(5):
            te = np.zeros(len(ids), bool)
            te[order[k::5]] = True
            Xtr, Xte = features(~te, te)
            hits[te] = (prob(fit(Xtr, y[~te]), Xte) > 0.5) == (y[te] == 1)
        accs.append(hits.mean())
    return float(np.mean(accs))


def binom_ci(k, n, a=0.05):
    """Exact (Clopper-Pearson) 95% interval for k successes out of n."""
    cdf = lambda x, p: sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(x + 1))
    grid = np.linspace(0, 1, 20001)
    lo = 0.0 if k == 0 else grid[np.argmax([1 - cdf(k - 1, p) >= a / 2 for p in grid])]
    hi = 1.0 if k == n else grid[::-1][np.argmax([cdf(k, p) >= a / 2 for p in grid[::-1]])]
    return lo, hi


acc_random = random_split()
acc_lolo, leaf_hit, pr = leave_one_leaf_out(y)
k = sum(leaf_hit.values())
lo, hi = binom_ci(k, len(leaves))
print(f"wrong way (random photo split): {acc_random:.1%} of photos right")
print(f"right way (leave one leaf out): {acc_lolo:.1%} of photos; {k} of {len(leaves)} leaves (95% CI {lo:.0%}-{hi:.0%})")
# baseline: shuffle tank labels between leaves
leaf_lab = {l: 1.0 if l.startswith("mh") else 0.0 for l in leaves}
null = []
for i in range(N_NULL):
    perm = dict(zip(leaves, RNG.permutation([leaf_lab[l] for l in leaves])))
    null.append(leave_one_leaf_out(np.array([perm[l] for l in leaf]))[0])
null = np.array(null)
p_null = float((np.sum(null >= acc_lolo) + 1) / (N_NULL + 1))
n_lo, n_hi = np.percentile(null, [2.5, 97.5])
print(f"baseline (labels shuffled between leaves): middle 95% {n_lo:.1%}-{n_hi:.1%}; p = {p_null:.3f}")
# fingerprint: nearest other photo - same leaf?
mu = V.mean(0)
_, _, vt = np.linalg.svd(V - mu, full_matrices=False)
X = np.hstack([(V - mu) @ vt[:N_PC].T, C])
X = (X - X.mean(0)) / X.std(0)
D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
np.fill_diagonal(D, np.inf)
same = float(np.mean(leaf[D.argmin(1)] == leaf))
chance_same = float(np.mean([(np.sum(leaf == l) - 1) / (len(leaf) - 1) for l in leaf]))
print(f"fingerprint: nearest other photo is the same leaf for {same:.1%} of photos (by chance {chance_same:.1%})")
# exploratory: right way within each period
per = {}
for name, (d0, d1) in {"A Days 2-10": (2, 10), "B Days 11-16": (11, 16), "C Days 17-26": (17, 26)}.items():
    s = np.array([d0 <= int(i[-2:]) <= d1 for i in ids])
    per[name] = float(np.mean((pr[s] > 0.5) == (y[s] == 1)))
    print(f"   right way, photos in {name}: {per[name]:.1%}")

rows = [["wrong way: photos split at random (5-fold, 20 repeats)", "photos", round(acc_random, 4), "", "", "", "leaf photos in training and test"],
        ["right way: one whole leaf held out at a time", "photos", round(acc_lolo, 4), "", "", round(p_null, 4), "p vs shuffled-label baseline"],
        ["right way: one whole leaf held out at a time", "leaves", round(k / len(leaves), 4), round(lo, 4), round(hi, 4), "",
         f"{k} of {len(leaves)} leaves; exact 95% CI"],
        ["baseline: tank labels shuffled between leaves (500x)", "photos", round(float(null.mean()), 4), round(n_lo, 4), round(n_hi, 4), "",
         "middle 95% of guessing scores"],
        ["fingerprint: nearest other photo is the same leaf", "photos", round(same, 4), "", "", "", f"by chance {chance_same:.4f}"]]
rows += [[f"right way, photos in {n} (exploratory)", "photos", round(a, 4), "", "", "", ""] for n, a in per.items()]
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["evaluation", "unit", "accuracy", "ci95_low", "ci95_high", "p", "note"])
    w.writerows(rows)
with open(OUT_LEAF, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["leaf", "tank", "photos", "mean_prob_low_tank", "correct"])
    for l in leaves:
        w.writerow([l, "Low" if l.startswith("mh") else "High", int(np.sum(leaf == l)), round(float(pr[leaf == l].mean()), 3), leaf_hit[l]])

# ---------- figure ----------
INK, QUIET = "#222222", "#666666"
plt.rcParams.update({"font.family": "Arial", "font.size": 11, "svg.fonttype": "none"})
fig, ax = plt.subplots(figsize=(8.5, 4.2))
bars = [("Photos split at random\n(same leaf in training and test)", acc_random, "#c0502a"),
        ("One whole leaf held out\n(photos)", acc_lolo, INK),
        ("One whole leaf held out\n(leaves)", k / len(leaves), INK)]
ax.axhspan(n_lo, n_hi, color="#eeeeee", zorder=0)
ax.text(2.45, n_hi + 0.01, "grey band: range of pure guessing (labels shuffled)", ha="right", va="bottom", fontsize=9, color=QUIET)
for i, (lab, v, c) in enumerate(bars):
    ax.bar(i, v, color=c, width=0.55)
    if i == 2:                                                       # error bar above: label inside the bar
        ax.text(i, v - 0.06, f"{v:.0%}", ha="center", fontsize=11, color="white", fontweight="bold")
    else:
        ax.text(i, v + 0.02, f"{v:.0%}", ha="center", fontsize=11, color=INK, fontweight="bold")
ax.errorbar(2, k / len(leaves), yerr=[[k / len(leaves) - lo], [hi - k / len(leaves)]], color=QUIET, capsize=4)
ax.axhline(0.5, color=QUIET, ls="--", lw=0.8)
ax.set_xticks(range(3))
ax.set_xticklabels([b[0] for b in bars], fontsize=9.5)
ax.set_ylim(0, 1.08)
ax.set_ylabel("Share guessed right (which tank?)")
ax.spines[["top", "right"]].set_visible(False)
ax.set_title(f"Can a model tell the tank from leaf shape and colour?  Fingerprint: a photo's closest match is the same leaf "
             f"{same:.0%} of the time", loc="left", fontsize=10.5, color=INK)
for ext in ("png", "svg"):
    fig.savefig(os.path.join(res, "poster_figures", f"fig29_classifier_check_{ver}.{ext}"), dpi=200, bbox_inches="tight")
print("wrote", OUT, OUT_LEAF)
