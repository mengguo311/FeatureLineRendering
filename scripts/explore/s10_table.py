"""Consolidated deliverable table + per-view breakdown of the headline pools."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import build_knn, pca_normals, smooth_normals, make_pool
from tune_lib import Harness, structure_tensor, nms_along_e1
import score_pool

h = Harness("chair")
X = h.X
knn = build_knn(X, 32)


def show(tag, sel):
    p, r, nv = h.evaluate(X[sel])
    ps, rs, ns = h.evaluate(X[sel], per_view=True)
    print("%-44s n=%6d prec=%.4f rec=%.4f | v0 %.3f/%.3f  v25 %.3f/%.3f"
          % (tag, len(sel), p, r, ps[0], rs[0], ps[1], rs[1]))


print("=== headline pools, with per-view breakdown ===")
st = structure_tensor(X, h.N, 8)
cand = np.where(st["s_crease"] > 0.05)[0]
sel0 = nms_along_e1(X, cand, st["s_crease"], st["e1"], st["knn"])
show("BASELINE cov-normal k8 tau.05 nms.7", sel0)
show("ALL de-floatered gaussians (chance)", np.arange(len(X)))
n16 = pca_normals(X, knn, 16)
s6, _ = make_pool(X, n16, knn, 6, float(np.quantile(structure_tensor(X, n16, 6, knn=knn[:, :6])["s_crease"], 0.55)),
                  use_nms=True, cos_thr=0.7)
show("PCA16 normals, ST k6, tau q0.55, nms.7", s6)
show("opacity floor >0.7 only, no ST", np.where(h.opa > 0.7)[0])
show("BEST POOL build_pool(q=0.60)", score_pool.build_pool(h, q=0.60))
show("BEST POOL tuned w(1.5,1,1.5) q=0.625", score_pool.build_pool(h, q=0.625, weights=(1.5, 1.0, 1.5)))
show("BEST POOL build_pool(q=0.50) rec>=0.80", score_pool.build_pool(h, q=0.50))
