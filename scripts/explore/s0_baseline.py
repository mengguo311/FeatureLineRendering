import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import *  # noqa
from tune_lib import Harness, structure_tensor, nms_along_e1

t0 = time.time()
h = Harness("chair")
print(f"harness {time.time()-t0:.1f}s  N={len(h.X)}")

st = structure_tensor(h.X, h.N, 8)
cand = np.where(st["s_crease"] > 0.05)[0]
sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
print("cand", len(cand), "sel", len(sel))
t1 = time.time()
p, r, nv = h.evaluate(h.X[sel])
print(f"BASELINE prec={p:.4f} rec={r:.4f} nvis={nv}  ({time.time()-t1:.2f}s per eval)")

# opacity / scale stats for later
print("opa quantiles", np.percentile(h.opa, [1, 10, 25, 50, 75, 90, 99]).round(3))
print("all gaussians", len(h.g["mu"]), "defloat kept", h.keep.sum())
np.save("/tmp/claude-1026/-home-u00134-3dgs-line/4ee6144a-2815-4286-bec9-0a63623a57f6/scratchpad/sel_base.npy", sel)
print("total", time.time() - t0)
