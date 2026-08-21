"""Cascades (pre-filter then rank) and recall-protecting selection rules."""
import os, sys, itertools, numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from cache_scores import build
from fastgate import FastGate

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
h, st, sel = build("chair"); fg = FastGate(h, sel); M = len(sel)
z = dict(np.load(os.path.join(OUT, "scores_chair.npz")))
sa = dict(np.load(os.path.join(OUT, "sharpaggs_chair.npz")))
allf = {**{k: v for k, v in z.items() if not k.startswith(("lab_", "sel"))}, **sa}
R = {k: rankdata(np.nan_to_num(np.asarray(v, float), nan=-1e9)) / M for k, v in allf.items()}
X = h.X[sel]

BEST = ["dt", "view", "sparse.mean", "sparse.q75", "ridge45.mean", "ridge45.q90",
        "gline", "gline_dihed", "geom", "geom_nbopa", "pool", "neigh_smdih",
        "mid.q90", "geom_dih"]


def report(s, tag, rmin=0.72):
    o = np.argsort(-s, kind="stable"); b = None
    for f in np.arange(0.15, 0.90, 0.01):
        k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
        p, r, n = fg(k)
        if r >= rmin and (b is None or p > b[0]): b = (p, r, f)
    if b: print(f"  {tag:46s} p={b[0]:.3f} r={b[1]:.3f} f={b[2]:.2f}", flush=True)
    return b


print("=== CASCADE: hard pre-filter (top-q by A) THEN rank by B ===")
best = []
for a, bnm in itertools.permutations(BEST, 2):
    for q in (0.9, 0.8, 0.7, 0.6, 0.5):
        pre = R[a] >= (1 - q)
        s = np.where(pre, R[bnm] + 10.0, -1e9 + R[bnm])
        o = np.argsort(-s, kind="stable"); bb = None
        for f in np.arange(0.15, 0.90, 0.02):
            k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
            p, r, n = fg(k)
            if r >= 0.72 and (bb is None or p > bb[0]): bb = (p, r, f)
        if bb: best.append((bb[0], bb[1], bb[2], a, bnm, q))
best.sort(key=lambda t: -t[0])
for t in best[:12]:
    print(f"  p={t[0]:.3f} r={t[1]:.3f} f={t[2]:.2f}  pre={t[3]}(top {t[5]}) rank={t[4]}")

print("\n=== RECALL PROTECTION: global score + lambda * local rank within kNN seeds ===")
tree = cKDTree(X)
base = R["dt"] + 0.5 * R["view"]
for k in (8, 16, 32, 64):
    _, nb = tree.query(X, k=k)
    for lam in (0.1, 0.25, 0.5, 1.0):
        lr = (base[nb] < base[:, None]).sum(1) / k
        report(base + lam * lr, f"knn{k} lam{lam}")

print("\n=== RECALL PROTECTION: keep top-f globally UNION per-cell argmax ===")
for ncell in (16, 24, 32, 48):
    q = np.floor((X - X.min(0)) / (X.max(0) - X.min(0) + 1e-9) * ncell).clip(0, ncell - 1).astype(int)
    cid = (q[:, 0] * ncell + q[:, 1]) * ncell + q[:, 2]
    order = np.argsort(-base, kind="stable")
    # per-cell best
    seen = {}
    for i in order:
        if cid[i] not in seen: seen[cid[i]] = i
    rep = np.zeros(M, bool); rep[list(seen.values())] = True
    for f in (0.15, 0.2, 0.25, 0.3, 0.35):
        k = np.zeros(M, bool); k[order[:int(round(f * M))]] = True
        k |= rep
        p, r, n = fg(k)
        print(f"  cells{ncell} f={f}: p={p:.3f} r={r:.3f} n={n} (+{rep.sum()} reps)")
