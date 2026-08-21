"""Final: AUC of every exposed score in score_geom.py, per the deliverable spec.
Label (EVAL ONLY) = seed within 2.5px of a GT crease pixel in >=1 view."""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tune_lib import Harness, structure_tensor, nms_along_e1
from explore_geom import auc, labels
import score_geom as SG

h = Harness("chair")
st = structure_tensor(h.X, h.N, 8)
cand = np.where(st["s_crease"] > 0.05)[0]
sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
P = h.X[sel]
near, visa, ncnt, vcnt = labels(h, P)
print(f"pool={len(sel)}  visible(any view)={visa.sum()}  positives={near.sum()} "
      f"({near.sum()/visa.sum():.3f} of visible)")
print(f"{'score':24s} {'AUC_all':>8s} {'AUC_vis':>8s}")
for n in ["compute", "compute_auc_best", "compute_dihedral", "compute_seed_density",
          "compute_nb_opacity", "compute_flatness"]:
    s = getattr(SG, n)(h, sel, st)
    print(f"{n:24s} {auc(s, near):8.3f} {auc(s[visa], near[visa]):8.3f}")

# per-view breakdown of the headline operating point
s = SG.compute(h, sel, st)
o = np.argsort(-s)
for f in [0.5, 0.45, 0.4]:
    keep = np.zeros(len(sel), bool)
    keep[o[:int(round(f * len(sel)))]] = True
    ps, rs, ns = h.evaluate(P, extra_mask=keep, per_view=True)
    print(f"f={f:.2f}  per-view prec={[round(x,3) for x in ps]} "
          f"rec={[round(x,3) for x in rs]} nvis={ns}  mean={np.mean(ps):.3f}/"
          f"{np.mean(rs):.3f}")
