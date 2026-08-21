"""Sweep 8: normal-BIMODALITY / dihedral-angle features (the mesh-free analogue of the
oracle's 'face adjacency angle >= 30 deg' criterion) + larger-k density + rich rank combos."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import build_knn, pca_normals, auc
from tune_lib import Harness, structure_tensor
from scipy.stats import rankdata

t0 = time.time()
h = Harness("chair")
X = h.X
N = len(X)
KB = 96
knn = build_knn(X, KB)
lab = np.load(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/lab_all.npy"))
rows = []


def rec(tag, sel):
    if len(sel) < 300:
        return
    p, r, nv = h.evaluate(X[sel])
    rows.append((tag, len(sel), p, r, nv))
    print("%-40s nsel=%6d prec=%.4f rec=%.4f" % (tag, len(sel), p, r), flush=True)


print("=== A. larger-k density ===")
Dfe = {}
for k in (32, 48, 64, 96):
    d = np.linalg.norm(X[knn[:, :k]] - X[:, None], axis=2)
    Dfe[f"kthNN{k}"] = -d[:, -1]
    print("  kthNN%-3d AUC=%.4f" % (k, auc(Dfe[f"kthNN{k}"], lab)))

print("\n=== B. dihedral / bimodality of the kNN normal distribution ===")
n32 = pca_normals(X, knn, 32)
BF = {}
for k in (8, 16, 32):
    nb = knn[:, :k]
    nj = n32[nb]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, n32))
    sg[sg == 0] = 1
    nj = nj * sg[..., None]                       # [N,k,3] sign-aligned
    st = structure_tensor(X, n32, k, knn=nb)
    e1 = st["e1"]
    t = np.einsum("nkc,nc->nk", nj - nj.mean(1, keepdims=True), e1)   # [N,k] proj on e1
    # split into two clusters at t=0 (the e1 axis is the max-variation axis)
    A = t > 0
    nA = A.sum(1).astype(float)
    nB = k - nA
    ok = (nA >= 2) & (nB >= 2)
    mA = np.where(A[..., None], nj, 0).sum(1) / np.clip(nA, 1, None)[:, None]
    mB = np.where(~A[..., None], nj, 0).sum(1) / np.clip(nB, 1, None)[:, None]
    mA /= np.linalg.norm(mA, axis=1, keepdims=True) + 1e-12
    mB /= np.linalg.norm(mB, axis=1, keepdims=True) + 1e-12
    ang = np.degrees(np.arccos(np.clip(np.einsum("nc,nc->n", mA, mB), -1, 1)))
    ang[~ok] = 0.0
    # bimodality: 1 - within/total variance of t
    tv = t.var(1) + 1e-30
    wv = (np.where(A, t - (np.where(A, t, 0).sum(1) / np.clip(nA, 1, None))[:, None], 0) ** 2).sum(1)
    wv += (np.where(~A, t - (np.where(~A, t, 0).sum(1) / np.clip(nB, 1, None))[:, None], 0) ** 2).sum(1)
    wv /= k
    bim = 1.0 - wv / tv
    bal = np.minimum(nA, nB) / k
    BF[f"dihed_k{k}"] = ang
    BF[f"bimod_k{k}"] = bim
    BF[f"dihed*bim_k{k}"] = ang * np.clip(bim, 0, None)
    BF[f"dihed*bal_k{k}"] = ang * bal
    for nm in (f"dihed_k{k}", f"bimod_k{k}", f"dihed*bim_k{k}", f"dihed*bal_k{k}"):
        print("  %-18s AUC=%.4f" % (nm, auc(BF[nm], lab)))
    print("    frac with dihedral>=30deg: %.3f (of which %.3f are true creases)"
          % ((ang >= 30).mean(), lab[ang >= 30].mean() if (ang >= 30).any() else 0))

print("\n=== C. absolute dihedral threshold as a POOL rule (mesh-free, transferable) ===")
for k in (8, 16, 32):
    for thr in (20, 30, 40, 50):
        sel = np.where(BF[f"dihed_k{k}"] >= thr)[0]
        rec(f"dihedral_k{k}>={thr}deg", sel)

print("\n=== D. rich rank combos ===")
st16 = structure_tensor(X, n32, 16, knn=knn[:, :16])
R = lambda v: rankdata(v) / N
base = {
    "dens": R(Dfe["kthNN64"]),
    "l1n": R(st16["l1"]),
    "opa": R(h.opa),
    "dihed": R(BF["dihed*bim_k16"]),
}
combos = {
    "dens+l1n+opa": base["dens"] + base["l1n"] + base["opa"],
    "dens+l1n+opa+dihed": base["dens"] + base["l1n"] + base["opa"] + base["dihed"],
    "dens+dihed+opa": base["dens"] + base["dihed"] + base["opa"],
    "dens+l1n": base["dens"] + base["l1n"],
    "dens+dihed": base["dens"] + base["dihed"],
    "2dens+l1n+opa": 2 * base["dens"] + base["l1n"] + base["opa"],
}
for nm, c in combos.items():
    print("  %-22s AUC=%.4f" % (nm, auc(c, lab)))
print()
for nm, c in combos.items():
    for q in (0.55, 0.60, 0.65):
        rec(f"{nm} q{q}", np.where(c > np.quantile(c, q))[0])

a = [x for x in rows if x[3] >= 0.75]
a.sort(key=lambda z: -z[2])
print("\n=== BEST @ rec>=0.75 ===")
for x in a[:12]:
    print("  %-40s nsel=%6d prec=%.4f rec=%.4f" % (x[0], x[1], x[2], x[3]))
print("total", time.time() - t0)
