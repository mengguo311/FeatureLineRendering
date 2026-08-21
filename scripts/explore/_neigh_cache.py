"""EVAL-SIDE helper: build + cache the multi-scale structure tensors, the canonical
seed pool, and the (mesh-based, ANALYSIS-ONLY) per-seed crease labels.

Run once; everything lands in the scratchpad as .npz so sweeps are fast.
"""
import os
import sys
import time
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from tune_lib import Harness, structure_tensor, nms_along_e1
from src import visibility

SCRATCH = "/tmp/claude-1026/-home-u00134-3dgs-line/4ee6144a-2815-4286-bec9-0a63623a57f6/scratchpad"
KS = [6, 8, 12, 16, 24, 32, 48]
KMAX = max(KS)


def st_at(X, N, k, knn_full):
    return structure_tensor(X, N, k, knn=knn_full[:, :k])


def main():
    t0 = time.time()
    h = Harness("chair")
    print(f"harness {time.time()-t0:.1f}s  N={len(h.X)}")

    tree = cKDTree(h.X)
    t = time.time()
    _, knn_full = tree.query(h.X, k=KMAX + 1, workers=8)
    knn_full = knn_full[:, 1:]
    print(f"knn k={KMAX} {time.time()-t:.1f}s")

    sts = {}
    for k in KS:
        t = time.time()
        sts[k] = st_at(h.X, h.N, k, knn_full)
        print(f"  ST k={k} {time.time()-t:.1f}s")

    st = sts[8]
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    print(f"cand={len(cand)} sel={len(sel)}")
    P = h.X[sel]
    print("baseline evaluate:", h.evaluate(P))

    # ---- ANALYSIS-ONLY labels (mesh) ----
    lab = np.zeros(len(sel), bool)
    vis_any = np.zeros(len(sel), bool)
    dmin = np.full(len(sel), np.inf)
    for v in h.views:
        vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
        vv = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
        cu, cv_, cdt = h.crease[v]
        d = cdt[vv, u]
        lab |= vis & (d <= 2.5)
        vis_any |= vis
        dmin = np.where(vis, np.minimum(dmin, d), dmin)
    print(f"label pos={lab.sum()} ({lab.mean():.3f})  vis_any={vis_any.sum()}")

    out = {"sel": sel, "knn_full": knn_full.astype(np.int32),
           "label": lab, "vis_any": vis_any, "dmin": dmin}
    for k in KS:
        s = sts[k]
        out[f"sc{k}"] = s["s_crease"]
        out[f"sn{k}"] = s["s_corner"]
        out[f"e1_{k}"] = s["e1"]
        out[f"e3_{k}"] = s["e3"]
        out[f"l1_{k}"] = s["l1"]
        out[f"l2_{k}"] = s["l2"]
        out[f"l3_{k}"] = s["l3"]
    np.savez(os.path.join(SCRATCH, "neigh_cache.npz"), **out)
    print("saved", time.time() - t0)


if __name__ == "__main__":
    main()
