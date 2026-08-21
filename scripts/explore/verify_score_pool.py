"""Definitive verification of score_pool.py: standalone import, timing, Pareto, AUC."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from tune_lib import Harness, structure_tensor, nms_along_e1
from _pool_common import crease_label, auc
import score_pool

T = time.time()
h = Harness("chair")
st = structure_tensor(h.X, h.N, 8)
cand = np.where(st["s_crease"] > 0.05)[0]
sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
P = h.X[sel]
p0, r0, n0 = h.evaluate(P)
print(f"canonical pool: nsel={len(sel)} prec={p0:.4f} rec={r0:.4f} nvis={n0}")

t = time.time()
s = score_pool.compute(h, sel, st)
print(f"compute() took {time.time()-t:.2f}s (first call, includes kNN); shape={s.shape}")
t = time.time(); _ = score_pool.compute(h, sel, st); print(f"  cached call {time.time()-t:.2f}s")

lab, seen = crease_label(h, h.X, sel)
FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]

print("\n=== PARETO on the CANONICAL pool (extra_mask = top-f) ===")
print("score                     " + "".join(f"   f={f:<4.1f}" for f in FS))
variants = {
    "compute (dens+l1+opa)": score_pool.compute(h, sel, st),
    "compute_dens_l1": score_pool.compute_dens_l1(h, sel, st),
    "compute_density": score_pool.compute_density(h, sel, st),
    "compute_l1_pca": score_pool.compute_l1_pca(h, sel, st),
    "compute_screase_pca": score_pool.compute_screase_pca(h, sel, st),
    "BASELINE st['s_crease']": st["s_crease"][sel],
}
best_rows = {}
for nm, sc in variants.items():
    order = np.argsort(-sc)
    pr = []
    for f in FS:
        keep = np.zeros(len(sel), bool)
        keep[order[:int(f * len(sel))]] = True
        p, r, nv = h.evaluate(P, extra_mask=keep)
        pr.append((f, p, r))
    best_rows[nm] = pr
    print("%-24s " % nm + " ".join("%.3f/%.3f" % (p, r) for _, p, r in pr)
          + "   AUC=%.4f" % auc(sc, lab))

print("\n=== AUC (label = seed within 2.5px of a GT crease pixel in >=1 visible view) ===")
print("  canonical-pool positives: %d/%d (%.3f)" % (lab.sum(), len(lab), lab.mean()))
for nm, sc in variants.items():
    print("  %-24s AUC=%.4f" % (nm, auc(sc, lab)))

print("\n=== build_pool() : the POOL recipe ===")
for q in (0.50, 0.55, 0.60, 0.625, 0.65):
    idx = score_pool.build_pool(h, q=q)
    p, r, nv = h.evaluate(h.X[idx])
    print("  q=%.3f nsel=%6d prec=%.4f rec=%.4f nvis=%6d" % (q, len(idx), p, r, nv))
print("  tuned weights (1.5,1.0,1.5) q=0.625:")
idx = score_pool.build_pool(h, q=0.625, weights=(1.5, 1.0, 1.5))
p, r, nv = h.evaluate(h.X[idx])
print("    nsel=%6d prec=%.4f rec=%.4f" % (len(idx), p, r))

print("\n=== POOL + ranking filter stacked (best pool, then top-f by compute) ===")
idx = score_pool.build_pool(h, q=0.50)
Pp = h.X[idx]
sc = score_pool.compute(h, idx, None)
order = np.argsort(-sc)
for f in (1.0, 0.8, 0.7, 0.6, 0.5):
    keep = np.zeros(len(idx), bool); keep[order[:int(f*len(idx))]] = True
    p, r, nv = h.evaluate(Pp, extra_mask=keep)
    print("  f=%.2f nsel=%6d prec=%.4f rec=%.4f" % (f, keep.sum(), p, r))

print("\ntotal %.1fs" % (time.time() - T))
