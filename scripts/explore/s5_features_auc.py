"""Sweep 5: per-feature AUC on the crease label over ALL de-floatered gaussians,
including classic position-PCA eigenvalue features (surface variation etc).
"""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import build_knn, pca_normals, smooth_normals, crease_label, auc
from tune_lib import Harness, structure_tensor

t0 = time.time()
h = Harness("chair")
X = h.X
N = len(X)
knn = build_knn(X)
lab, seen = crease_label(h, X, np.arange(N))
print(f"label: {lab.sum()}/{N} positives ({lab.mean():.3f}); visible in >=1 view: {seen.sum()}")
np.save(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/lab_all.npy"), lab)
np.save(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/seen_all.npy"), seen)

F = {}
F["opacity"] = h.opa
smax = h.scale.max(1)
ssort = np.sort(h.scale, 1)
F["-scale_max"] = -smax
F["-scale_mid"] = -ssort[:, 1]
F["-scale_min"] = -ssort[:, 0]

# position-PCA eigen features at several k
for k in (8, 16, 32):
    nb = X[knn[:, :k]]
    mu = nb.mean(1, keepdims=True)
    d = nb - mu
    C = np.einsum("nkc,nkd->ncd", d, d) / k
    w, V = np.linalg.eigh(C)          # ascending w[:,0]<=w[:,1]<=w[:,2]
    l3, l2, l1 = w[:, 0], w[:, 1], w[:, 2]
    ssum = l1 + l2 + l3 + 1e-30
    F[f"surfvar_k{k}"] = l3 / ssum
    F[f"planarity_k{k}"] = (l2 - l3) / (l1 + 1e-30)
    F[f"linearity_k{k}"] = (l1 - l2) / (l1 + 1e-30)
    F[f"-dens_k{k}"] = -np.linalg.norm(X[knn[:, :k]] - X[:, None], axis=2).mean(1)
    F[f"rms_resid_k{k}"] = np.sqrt(np.maximum(l3, 0))

# normal structure tensor with several normal defs
n_cov = h.N
for nm, n in [("cov", n_cov), ("pca8", pca_normals(X, knn, 8)),
              ("pca16", pca_normals(X, knn, 16)), ("pca32", pca_normals(X, knn, 32)),
              ("sm12", smooth_normals(n_cov, knn, 12))]:
    for k in (6, 8, 16):
        st = structure_tensor(X, n, k, knn=knn[:, :k])
        F[f"screase_{nm}_k{k}"] = st["s_crease"]
        F[f"l1_{nm}_k{k}"] = st["l1"]
        if k == 8:
            F[f"scorner_{nm}_k{k}"] = st["s_corner"]

# normal-def agreement
n16 = pca_normals(X, knn, 16)
F["-|n_cov.n_pca16|"] = -np.abs(np.einsum("nc,nc->n", n_cov, n16))

res = [(name, auc(f, lab)) for name, f in F.items()]
res.sort(key=lambda z: -z[1])
print("\n=== AUC (crease-within-2.5px label), ALL de-floatered gaussians ===")
for name, a in res:
    print("  %-26s AUC=%.4f" % (name, a))

# also AUC restricted to gaussians visible in >=1 view (the ones precision is measured on)
print("\n=== AUC restricted to seen (visible) gaussians ===")
res2 = [(name, auc(f[seen], lab[seen])) for name, f in F.items()]
res2.sort(key=lambda z: -z[1])
for name, a in res2[:18]:
    print("  %-26s AUC=%.4f" % (name, a))
np.savez(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/feats.npz"), **F)
print("\ntotal", time.time() - t0)
