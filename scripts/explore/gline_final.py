"""Final validation of score_gline: Pareto, AUC, held-out-view check.  EVAL-SIDE."""
import os
import sys
import time
import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore"))
from tune_lib import Harness, structure_tensor, nms_along_e1  # noqa: E402
from src import visibility  # noqa: E402
import score_gline as SG  # noqa: E402

FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]
FINE = [0.9, 0.7, 0.55, 0.45, 0.35, 0.25, 0.15, 0.10, 0.05]


def auc(s, y):
    r = rankdata(s)
    n1 = int(y.sum())
    n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def main():
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    P = h.X[sel]
    M = len(sel)
    print(f"pool {M} seeds; baseline {h.evaluate(P)}")

    near = np.zeros(M, bool)
    vis_eval = np.zeros(M, bool)
    dmin = np.full(M, 1e9)
    for v in h.views:
        vv, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
        cdt = h.crease[v][2]
        near |= vv & (cdt[w, u] <= 2.5)
        dmin = np.where(vv, np.minimum(dmin, cdt[w, u]), dmin)
        vis_eval |= vv
    ye = near[vis_eval]
    print(f"label: {near.sum()} near / {vis_eval.sum()} vis  rate={ye.mean():.3f}")

    def report(tag, s, fs):
        a_v = auc(s[vis_eval], ye)
        a_a = auc(s, near)
        rows = []
        order = np.argsort(-s, kind="mergesort")
        for f in fs:
            keep = np.zeros(M, bool)
            keep[order[:int(f * M)]] = True
            p, r, n = h.evaluate(P, extra_mask=keep)
            rows.append((f, p, r, n))
        print(f"\n--- {tag}   AUC(vis)={a_v:.4f}  AUC(all)={a_a:.4f}")
        for f, p, r, n in rows:
            print(f"    f={f:4.2f}  precision={p:.4f}  recall={r:.4f}  n_vis={n}")
        return a_v, rows

    print("\n########## VIEW SET A: range(0,100,8)  (INCLUDES eval view 0) ##########")
    allsc = SG.compute_all(h, sel, st, views=tuple(range(0, 100, 8)))
    aucs = {k: auc(v[vis_eval], ye) for k, v in allsc.items()}
    print("AUC of each variant:", {k: round(v, 4) for k, v in
                                   sorted(aucs.items(), key=lambda x: -x[1])})
    report("ORACLE (-dist to true crease)", -dmin, FS)
    for k in ["fusion3", "pair", "fusion4", "crease", "dihed", "nogmag", "ridgeval"]:
        report(k, allsc[k], FS)
    report("fusion3 FINE", allsc["fusion3"], FINE)

    print("\n########## VIEW SET B: range(4,100,8)  (EXCLUDES eval views 0 and 25) ####")
    hb = SG.compute_all(h, sel, st, views=tuple(range(4, 100, 8)))
    print("AUC of each variant:", {k: round(auc(v[vis_eval], ye), 4) for k, v in
                                   sorted(hb.items(), key=lambda x: -auc(x[1][vis_eval], ye))})
    report("fusion3 (held-out views)", hb["fusion3"], FS)
    report("pair (held-out views)", hb["pair"], FS)

    print("\n########## VIEW SET C: range(0,100,4) (25 views) ##########")
    hc = SG.compute_all(h, sel, st, views=tuple(range(0, 100, 4)))
    print("AUC of each variant:", {k: round(auc(v[vis_eval], ye), 4) for k, v in
                                   sorted(hc.items(), key=lambda x: -auc(x[1][vis_eval], ye))})
    report("fusion3 (25 views)", hc["fusion3"], FS)

    # combination with the pool's own saliency, for reference
    sc = (rankdata(allsc["fusion3"]) - 0.5) / M + 0.5 * (rankdata(st["s_crease"][sel]) - 0.5) / M
    report("fusion3 + 0.5*s_crease", sc, FS)
    print(f"\n[{time.time()-t0:.1f}s] done")


if __name__ == "__main__":
    main()
