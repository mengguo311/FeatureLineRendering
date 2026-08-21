"""EVAL-SIDE screen 9: can a redundancy penalty (coverage protection) buy recall back?"""
import os
import sys
import numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore"))
from tune_lib import structure_tensor
from _neigh_lite import LiteHarness

SCRATCH = "/tmp/claude-1026/-home-u00134-3dgs-line/4ee6144a-2815-4286-bec9-0a63623a57f6/scratchpad"
Z = np.load(os.path.join(SCRATCH, "neigh_cache.npz"))
sel, lab = Z["sel"], Z["label"]
EPS = 1e-12
h = LiteHarness("chair")
X, Nrm = h.X, h.N
P = X[sel]
M = len(sel)
treeX = cKDTree(X)
dk, knnB = treeX.query(X, k=385, workers=8)
dk, knnB = dk[:, 1:], knnB[:, 1:]
sp = 0.00625


def rk(v):
    return rankdata(v) / len(v)


def auc(s, y):
    r = rankdata(np.asarray(s, float))
    n1 = int(y.sum()); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def two_plane(k):
    nb = knnB[:, :k]
    nj = Nrm[nb]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, Nrm)); sg[sg == 0] = 1.0
    nj = nj * sg[..., None]
    st = structure_tensor(X, Nrm, k, knn=nb)
    a = np.einsum("nkc,nc->nk", nj - nj.mean(1, keepdims=True), st["e1"])
    A = a > 0
    ok = (A.sum(1) >= 2) & ((~A).sum(1) >= 2)

    def gm(m, arr):
        w = m[..., None].astype(np.float64)
        return (arr * w).sum(1) / np.clip(w.sum(1), 1, None)
    nA, nB_ = gm(A, nj), gm(~A, nj)
    nA /= np.linalg.norm(nA, axis=1, keepdims=True) + EPS
    nB_ /= np.linalg.norm(nB_, axis=1, keepdims=True) + EPS
    g = np.clip(np.einsum("nc,nc->n", nA, nB_), -0.9999, 0.9999)
    d = np.degrees(np.arccos(np.abs(g))); d[~ok] = 0.0
    return d


dih = two_plane(192)
base = (0.5 * rk(-dk[:, 95][sel])
        + 1.0 * rk(dih[knnB[:, :384]].mean(1)[sel])
        + 0.5 * rk(np.stack([rankdata(Z[f"sc{kk}"])[sel]
                             for kk in [6, 8, 12, 16, 24, 32, 48]]).min(0)))
treeP = cKDTree(P)
_, knnP = treeP.query(P, k=65, workers=8)
knnP = knnP[:, 1:]
dP = np.linalg.norm(P[knnP] - P[:, None], axis=2)

FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]


def pareto(name, score, show=True):
    order = np.argsort(-score)
    rows = []
    for f in FS:
        keep = np.zeros(M, bool)
        keep[order[:int(round(f * M))]] = True
        p, r, n = h.evaluate(P, extra_mask=keep)
        rows.append((f, p, r, n))
    if show:
        print(f"\n--- {name} (AUC={auc(score, lab):.4f}) ---")
        for f, p, r, n in rows:
            fl = "  <== GATE PASS" if (p >= 0.80 and r >= 0.70) else ""
            print(f"  f={f:.2f} prec={p:.4f} rec={r:.4f} nvis={n}{fl}")
    return rows


print("baseline combo:")
pareto("combo", base)

print("\n=== redundancy penalty:  s = rk(base) - lam*rk(#higher-scoring seeds within r) ===")
best = (0, None)
for rmult in [2, 4, 8, 16]:
    within = dP < rmult * sp
    higher = ((base[knnP] > base[:, None]) & within).sum(1).astype(float)
    for lam in [0.1, 0.25, 0.5, 1.0]:
        s = rk(base) - lam * rk(higher)
        rows = pareto(f"r={rmult}sp lam={lam}", s, show=False)
        ok = [(p, r, f) for f, p, r, n in rows if r >= 0.70]
        o = max([p for p, r, f in ok], default=0.0)
        det = max(ok, default=(0, 0, 0))
        print(f"  r={rmult}sp lam={lam:<5} prec@rec>=.70 = {o:.4f} (f={det[2]}, rec={det[1]:.3f})")
        if o > best[0]:
            best = (o, (rmult, lam, s))
print("\nbest redundancy-penalised:", best[0], "r/lam=", best[1][0], best[1][1])
pareto("best redundancy-penalised", best[1][2])
