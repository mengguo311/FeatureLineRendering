"""EVAL-SIDE final verification of score_neigh against the OFFICIAL tune_lib.Harness gate."""
import os
import sys
import time
import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore"))
from tune_lib import Harness, structure_tensor, nms_along_e1
from src import visibility
import score_neigh as S

FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]


def auc(s, y):
    r = rankdata(np.asarray(s, float))
    n1 = int(y.sum()); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


h = Harness("chair")
st = structure_tensor(h.X, h.N, 8)
cand = np.where(st["s_crease"] > 0.05)[0]
sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
P = h.X[sel]
M = len(sel)
print(f"pool {M}  baseline {h.evaluate(P)}")

# ANALYSIS-ONLY label
lab = np.zeros(M, bool)
vis_any = np.zeros(M, bool)
for v in h.views:
    vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
    u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
    vv = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
    lab |= vis & (h.crease[v][2][vv, u] <= 2.5)
    vis_any |= vis
print(f"label pos={lab.sum()} ({lab.mean():.4f})  vis_any={vis_any.sum()}")

scores = {
    "compute (BEST COMBO)": S.compute(h, sel, st),
    "density k96": S.compute_density(h, sel, st),
    "smooth_dihedral": S.compute_smooth_dihedral(h, sel, st),
    "dihedral k192": S.compute_dihedral(h, sel, st),
    "multiscale_agreement": S.compute_multiscale_agreement(h, sel, st),
    "tangent_coherence": S.compute_tangent_coherence(h, sel, st),
    "chain_support(cc)": S.compute_chain_support(h, sel, st),
    "chain_support(deg)": S.compute_chain_support(h, sel, st, mode="deg"),
    "s_crease k8 (pool score)": st["s_crease"][sel],
}
print("\n=== AUC (label = within 2.5px of a visible GT crease in >=1 view) ===")
for n, s in scores.items():
    print(f"  {n:26s} AUC_all={auc(s, lab):.4f}   AUC_visible_only={auc(s[vis_any], lab[vis_any]):.4f}")

for n in ["compute (BEST COMBO)", "density k96", "smooth_dihedral", "multiscale_agreement",
          "tangent_coherence", "chain_support(cc)"]:
    s = scores[n]
    order = np.argsort(-s)
    print(f"\n--- PARETO {n} ---")
    for f in FS:
        keep = np.zeros(M, bool)
        keep[order[:int(round(f * M))]] = True
        p, r, nv = h.evaluate(P, extra_mask=keep)
        fl = "  <== GATE PASS" if (p >= 0.80 and r >= 0.70) else ""
        print(f"  f={f:.2f}  precision={p:.4f}  recall={r:.4f}  n_visible={nv}{fl}")

# per-view breakdown at the chosen operating point
s = scores["compute (BEST COMBO)"]
order = np.argsort(-s)
keep = np.zeros(M, bool)
keep[order[:int(round(0.6 * M))]] = True
print("\nper-view at f=0.6:", h.evaluate(P, extra_mask=keep, per_view=True))
