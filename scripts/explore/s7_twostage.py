"""Sweep 7: density variants, TWO-STAGE pool (re-estimate geometry on the survivors),
opacity-weighted structure tensor, and the oracle headroom for reference."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import build_knn, pca_normals, crease_label, auc
from tune_lib import Harness, structure_tensor
from scipy.spatial import cKDTree
from scipy.stats import rankdata

t0 = time.time()
h = Harness("chair")
X = h.X
N = len(X)
knn = build_knn(X)
lab_all = np.load(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/lab_all.npy"))
rows = []


def rec(tag, sel):
    if len(sel) < 300:
        return None
    p, r, nv = h.evaluate(X[sel])
    rows.append((tag, len(sel), p, r, nv))
    print("%-46s nsel=%6d prec=%.4f rec=%.4f" % (tag, len(sel), p, r), flush=True)
    return p, r


print("=== A. density variants (AUC over all gaussians) ===")
D = {}
for k in (4, 8, 16, 32):
    d = np.linalg.norm(X[knn[:, :k]] - X[:, None], axis=2)
    D[f"meanNN{k}"] = -d.mean(1)
    D[f"kthNN{k}"] = -d[:, -1]
D["ratio8/32"] = D["meanNN32"] / (D["meanNN8"] - 1e-30)   # scale-free
D["rel8v32"] = -(-D["meanNN8"]) / ((-D["meanNN32"]) + 1e-30)
for k, v in sorted(D.items(), key=lambda z: -auc(z[1], lab_all)):
    print("  %-14s AUC=%.4f" % (k, auc(v, lab_all)))

print("\n=== B. TWO-STAGE pool: filter first, re-estimate normals/ST on survivors ===")
dens32 = D["meanNN32"]
n32 = pca_normals(X, knn, 32)
st16 = structure_tensor(X, n32, 16, knn=knn[:, :16])
Rd, Rl, Ro = (rankdata(dens32) / N, rankdata(st16["l1"]) / N, rankdata(h.opa) / N)
pre = Rd + Rl + Ro
for qpre in (0.30, 0.45, 0.55):
    thr = np.quantile(pre, qpre)
    keep_idx = np.where(pre > thr)[0]
    Xs = X[keep_idx]
    tree = cKDTree(Xs)
    _, kn2 = tree.query(Xs, k=33, workers=-1)
    kn2 = kn2[:, 1:]
    n2 = pca_normals(Xs, kn2, 16)
    for k2 in (6, 16):
        st2 = structure_tensor(Xs, n2, k2, knn=kn2[:, :k2])
        for q2 in (0.0, 0.2, 0.35, 0.5):
            s2 = st2["l1"]
            t2 = np.quantile(s2, q2) if q2 > 0 else -1
            sub = keep_idx[s2 > t2]
            rec(f"2stage qpre{qpre} k{k2} l1>q{q2}", sub)

print("\n=== C. opacity-weighted structure tensor (stage-1 style) ===")
for k in (8, 16):
    nb = knn[:, :k]
    nj = n32[nb]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, n32))
    sg[sg == 0] = 1
    nj = nj * sg[..., None]
    w = h.opa[nb]
    w = w / w.sum(1, keepdims=True)
    nbar = (nj * w[..., None]).sum(1, keepdims=True)
    d = nj - nbar
    C = np.einsum("nkc,nkd,nk->ncd", d, d, w)
    ev = np.linalg.eigvalsh(C)
    l1w = ev[:, 2]
    print("  opa-weighted l1 k%d AUC=%.4f (unweighted %.4f)" % (k, auc(l1w, lab_all), auc(st16["l1"], lab_all)))
    Rw = rankdata(l1w) / N
    for q in (0.5, 0.55, 0.6, 0.65):
        c = Rd + Rw + Ro
        rec(f"dens+opaWl1(k{k})+opa q{q}", np.where(c > np.quantile(c, q))[0])

print("\n=== D. best simple combo, fine q sweep ===")
c = Rd + Rl + Ro
for q in np.arange(0.50, 0.76, 0.025):
    rec(f"dens32+l1n+opa q{q:.3f}", np.where(c > np.quantile(c, q))[0])

print("\n=== E. ORACLE headroom (EVAL ONLY, not achievable mesh-free) ===")
from src import visibility
cd = np.full(N, np.inf)
for v in h.views:
    vis, uv, _ = visibility.visible_mask(X, h.cams[v], h.gbufs[v]["depth"])
    u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
    vv = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
    d = np.where(vis, h.crease[v][2][vv, u], np.inf)
    cd = np.minimum(cd, d)
ordo = np.argsort(cd)
for f in (0.8, 0.6, 0.5, 0.4, 0.3, 0.2):
    rec(f"ORACLE top {f} of all gaussians", ordo[:int(f * N)])

a = [x for x in rows if x[3] >= 0.75 and not x[0].startswith("ORACLE")]
a.sort(key=lambda z: -x_ if False else -z[2])
print("\n=== BEST mesh-free @ rec>=0.75 ===")
for x in a[:12]:
    print("  %-46s nsel=%6d prec=%.4f rec=%.4f" % (x[0], x[1], x[2], x[3]))
print("\ntotal", time.time() - t0)
