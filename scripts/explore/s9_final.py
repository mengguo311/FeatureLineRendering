"""Sweep 9: de-floater on/off for seed eligibility, local-rank (spatially stratified)
selection, and the final fine grid for the best pool."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import build_knn, pca_normals, auc
from tune_lib import Harness, structure_tensor
from scipy.spatial import cKDTree
from scipy.stats import rankdata

t0 = time.time()
h = Harness("chair")
X = h.X
N = len(X)
knn = build_knn(X, 32)
lab = np.load(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/lab_all.npy"))
rows = []


def rec(tag, pos, nsel=None):
    if len(pos) < 300:
        return
    p, r, nv = h.evaluate(pos)
    rows.append((tag, len(pos), p, r, nv))
    print("%-46s nsel=%6d prec=%.4f rec=%.4f" % (tag, len(pos), p, r), flush=True)


print("=== A. de-floater ON/OFF for seed eligibility (G-buffer unchanged) ===")
muA = h.g["mu"]
opaA = h.g["opacity"]
print("  all gaussians in ply:", len(muA), " defloatered:", N)
for tag, m in [("no filter at all", np.ones(len(muA), bool)),
               ("opa>0.1 only (no knn-defloat)", opaA > 0.1),
               ("defloat (harness default)", h.keep)]:
    rec(f"seeds from {tag}", muA[m])
# defloat + opacity floor on the FULL set
kA = cKDTree(muA[opaA > 0.1])
idxA = np.where(opaA > 0.1)[0]
dA, _ = kA.query(muA[idxA], k=33, workers=-1)
densA = -dA[:, 1:].mean(1)
for q in (0.5, 0.6):
    thr = np.quantile(densA, q)
    sub = idxA[(densA > thr) & (opaA[idxA] > 0.5)]
    rec(f"nodefloat & dens>q{q} & opa>0.5", muA[sub])

print("\n=== B. local-rank (spatially stratified) selection ===")
n32 = pca_normals(X, knn, 32)
st16 = structure_tensor(X, n32, 16, knn=knn[:, :16])
dens32 = -np.linalg.norm(X[knn[:, :32]] - X[:, None], axis=2).mean(1)
R = lambda v: rankdata(v) / N
gscore = R(dens32) + R(st16["l1"]) + R(h.opa)
# local rank of gscore among 32 neighbours
gnb = gscore[knn[:, :32]]
lrank = (gnb < gscore[:, None]).mean(1)     # in [0,1], 1 = best in its neighbourhood
print("  AUC gscore=%.4f  lrank=%.4f  g+lrank=%.4f  g+2lrank=%.4f"
      % (auc(gscore, lab), auc(lrank, lab), auc(R(gscore) + lrank, lab),
         auc(R(gscore) + 2 * lrank, lab)))
for nm, c in [("lrank", lrank), ("g+lrank", R(gscore) + lrank),
              ("g+0.5lrank", R(gscore) + 0.5 * lrank), ("g+2lrank", R(gscore) + 2 * lrank)]:
    for q in (0.45, 0.55, 0.6, 0.65):
        rec(f"{nm} q{q}", X[c > np.quantile(c, q)])

print("\n=== C. fine grid around the best recipe ===")
best = None
for wd in (0.5, 1.0, 1.5, 2.0):
    for wl in (0.5, 1.0, 1.5):
        for wo in (0.5, 1.0, 1.5, 2.0):
            c = wd * R(dens32) + wl * R(st16["l1"]) + wo * R(h.opa)
            for q in (0.50, 0.55, 0.575, 0.60, 0.625):
                sel = np.where(c > np.quantile(c, q))[0]
                p, r, nv = h.evaluate(X[sel])
                if r >= 0.75 and (best is None or p > best[0]):
                    best = (p, r, wd, wl, wo, q, len(sel))
print("  best @rec>=0.75:  prec=%.4f rec=%.4f  w=(dens %.1f, l1 %.1f, opa %.1f) q=%.3f nsel=%d" % best)
bd, bl, bo, bq = best[2], best[3], best[4], best[5]

best80 = None
for wd in (0.5, 1.0, 1.5, 2.0):
    for wl in (0.5, 1.0, 1.5):
        for wo in (0.5, 1.0, 1.5, 2.0):
            c = wd * R(dens32) + wl * R(st16["l1"]) + wo * R(h.opa)
            for q in (0.35, 0.40, 0.45, 0.50, 0.55):
                sel = np.where(c > np.quantile(c, q))[0]
                p, r, nv = h.evaluate(X[sel])
                if r >= 0.80 and (best80 is None or p > best80[0]):
                    best80 = (p, r, wd, wl, wo, q, len(sel))
print("  best @rec>=0.80:  prec=%.4f rec=%.4f  w=(dens %.1f, l1 %.1f, opa %.1f) q=%.3f nsel=%d" % best80)

print("\n=== D. Pareto of the winning POOL score over ALL gaussians ===")
c = bd * R(dens32) + bl * R(st16["l1"]) + bo * R(h.opa)
print("  AUC of winning pool score (all gaussians) = %.4f" % auc(c, lab))
order = np.argsort(-c)
for f in (1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2):
    sel = order[:int(f * N)]
    p, r, nv = h.evaluate(X[sel])
    print("    f=%.1f nsel=%6d prec=%.4f rec=%.4f nvis=%6d" % (f, len(sel), p, r, nv))
np.save(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/best_w.npy"),
        np.array([bd, bl, bo, bq]))
print("\ntotal", time.time() - t0)
