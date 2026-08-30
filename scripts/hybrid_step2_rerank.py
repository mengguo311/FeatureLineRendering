"""STEP 2b — the 2DGS signal as a PRUNE RE-RANKER instead of a hard seed veto.

*** METHOD PATH for the ranking; EVAL ONLY below the banner. ***

WHY (this goes beyond the literal hybrid_spec, and is labelled as such)
    STEP 1c established that the 2DGS channel carries real information the vanilla M1a
    score does not (+0.043 seed precision above the f-frontier on VAL). STEP 2 then found
    that spending it as a HARD SEED VETO lands on/under the ungated f-frontier end-to-end,
    and scripts/hybrid_step2_redundancy.py says why: the vetoed linelets really are lower
    precision (0.573 vs 0.669) but they carry 81.6% of the drawn TEST recall, because
    neighbouring linelets cover the same GT crease pixels. Deleting a seed is an expensive
    way to spend a soft signal.

    The spec's own framing is "vanilla = WHERE lines are, 2DGS = WHICH survive". Survival
    is decided by the consensus prune, not by the seed set. So here the 2DGS support enters
    as a RANKING TERM alongside linelet_prune.consensus_statistic:

        s = rank01(consensus_statistic) + w * rank01(2dgs_support_fraction)

    w=0 reproduces the published baseline prune frontier exactly, so the curves are
    directly comparable and w>0 curves lying ABOVE it are the synergy, measured.
    The 2DGS support fraction is the per-seed fraction of TRAIN views in which the seed's
    reprojection had 2DGS geometric support -- the same mesh-free quantity the hard gate
    thresholded, used continuously instead.
"""
import json
import os
import sys
import time

import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import (common, render, linelet, dt_pull, linelet_prune, view_split,
                 hybrid_gate)
import run_m1b as M

OUT, CACHE = os.path.join(TIER1, "out"), os.path.join(TIER1, "cache")


def rank01(v):
    from scipy.stats import rankdata
    return rankdata(v) / len(v)


def main():
    scene = "chair"
    model = os.path.join(OUT, "2dgs_chair")
    f = 0.30
    t0 = time.time()

    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X, scale_g = g["mu"][keep_g], g["scale"][keep_g]
    idx, _ = M.get_seeds(scene, f, X)
    views = list(view_split.TRAIN)

    L = linelet.init_linelets(X[idx], X, scale_g)
    field = dt_pull.build_field(scene, g, keep_g, cams, rgb_paths, views,
                                cfg_name="sharp", device="cuda",
                                gate=dict(theta=20.0, tau_depth=0.015, dilate_px=2,
                                          soft=False))
    res = dt_pull.pull(field, L, steps=100, lr=0.35, delta_max=5.0, huber_delta=2.0,
                       lam_s=0.02, lam_t=0.02, opt_tangent=True, opt_length=False,
                       rel_tol=0.02, two_sided=True, view_chunk=25, vis_every=25)
    stat = linelet_prune.consensus_statistic(res["resid3"], res["vis"], knn=L["knn"])
    keep_t, st_t = linelet_prune.consensus_prune(
        res["resid"], res["vis"], tau_in=1.0, min_ratio=0.50, max_med=1.5,
        resid3=res["resid3"], use_resid3=True)
    l_mod = linelet.modulate_length(res["l"], st_t["inlier_ratio"], thr=0.9, lo=0.25,
                                    hi=1.5)
    print(f"  [pull+prune] {time.time()-t0:.0f}s, tuned keep {int(keep_t.sum())}",
          flush=True)

    # ---- the continuous 2DGS support fraction (METHOD PATH, mesh-free) --------
    depthmin, _ = dt_pull.build_geom_cache(scene, g, keep_g, cams, views)
    _, info = hybrid_gate.build_seed_gate(scene, model, X[idx], cams, views, depthmin,
                                          signal="gradn", tau_q=90.0, r=0, vote_frac=0.75)
    z = np.load(info["cache"])
    _, supp, nv = hybrid_gate.vote_keep(z["pass"], z["vis"], frac=0.0)
    print(f"  [2dgs support] median {np.median(supp):.3f}  "
          f"never-visible {int((nv == 0).sum())}", flush=True)

    # ------------------------------------------------------------ EVAL ONLY ----
    from tune_lib import Harness
    h = Harness(scene, views=tuple(view_split.TEST))
    KF = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3)
    rows = []
    print("\n" + "=" * 100)
    print("STEP 2b — prune frontier with the 2DGS support as a ranking term "
          "(chair, TEST, segments, tuned prune + length policy)")
    print("  w = 0 is the published baseline frontier; w > 0 adds the 2DGS term.")
    print("=" * 100)
    print(f"{'w':>5} {'keep':>6} {'n':>7} {'segP@1.5':>9} {'segR@1.5':>9} {'segP@2.5':>9} "
          f"{'segR@2.5':>9}")
    for w in (0.0, 0.25, 0.5, 1.0, 2.0):
        s = rank01(stat) + w * rank01(supp)
        for kf in KF:
            k = keep_t & (s >= np.quantile(s, 1.0 - kf)) if kf < 1.0 else keep_t
            e = M.eval_segments(h, res["p"], res["t"], l_mod, keep=k)
            rows.append({"w": w, "keep_frac": kf, "n": int(k.sum()),
                         "P1.5": e[1.5][0], "R1.5": e[1.5][1],
                         "P2.5": e[2.5][0], "R2.5": e[2.5][1]})
            print(f"{w:>5.2f} {kf:>6.2f} {int(k.sum()):>7} {e[1.5][0]:>9.4f} "
                  f"{e[1.5][1]:>9.4f} {e[2.5][0]:>9.4f} {e[2.5][1]:>9.4f}", flush=True)

    base = [r for r in rows if r["w"] == 0.0]
    bR = [r["R1.5"] for r in sorted(base, key=lambda x: x["R1.5"])]
    bP = [r["P1.5"] for r in sorted(base, key=lambda x: x["R1.5"])]
    print("-" * 100)
    print("  LIFT of each w>0 point over the w=0 frontier at the SAME recall:")
    best = None
    for r in rows:
        if r["w"] == 0.0 or not (bR[0] < r["R1.5"] < bR[-1]):
            r["lift"] = float("nan")
            continue
        r["lift"] = r["P1.5"] - float(np.interp(r["R1.5"], bR, bP))
        if best is None or r["lift"] > best["lift"]:
            best = r
    pos = [r for r in rows if np.isfinite(r.get("lift", float("nan"))) and r["lift"] > 0]
    for r in sorted([x for x in rows if np.isfinite(x.get("lift", float("nan")))],
                    key=lambda x: -x["lift"])[:10]:
        print(f"    w={r['w']:<4} keep={r['keep_frac']:<4} n={r['n']:<6} "
              f"P={r['P1.5']:.4f} R={r['R1.5']:.4f}  LIFT={r['lift']:+.4f}")
    print(f"  points above the w=0 frontier: {len(pos)}/"
          f"{len([x for x in rows if np.isfinite(x.get('lift', float('nan')))])}")
    if best:
        print(f"  best: w={best['w']} keep={best['keep_frac']} P={best['P1.5']:.4f} "
              f"R={best['R1.5']:.4f} LIFT={best['lift']:+.4f}")
    print("=" * 100)

    p = os.path.join(OUT, "hybrid_step2b_rerank.json")
    json.dump({"scene": scene, "f": f, "model": model, "rows": rows},
              open(p, "w"), indent=1, default=float)
    print(f"wrote {p}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(7.6, 6))
    for w in (0.0, 0.25, 0.5, 1.0, 2.0):
        rr = sorted([x for x in rows if x["w"] == w], key=lambda x: x["R1.5"])
        plt.plot([x["R1.5"] for x in rr], [x["P1.5"] for x in rr], "-o", ms=4,
                 lw=(2.5 if w == 0 else 1.4),
                 label=("w=0 (baseline consensus prune)" if w == 0
                        else f"w={w} (+ 2DGS support)"))
    plt.xlabel("segment recall @1.5px (TEST)")
    plt.ylabel("segment precision @1.5px (TEST)")
    plt.title("STEP 2b: 2DGS support as a prune RE-RANKER (chair, TEST)")
    plt.grid(alpha=0.3); plt.legend(fontsize=8)
    pp = os.path.join(OUT, "hybrid_step2b_rerank.png")
    plt.tight_layout(); plt.savefig(pp, dpi=120)
    print(f"wrote {pp}")


if __name__ == "__main__":
    main()
