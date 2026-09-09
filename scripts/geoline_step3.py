"""tier1/scripts/geoline_step3.py — GEOLINE STEP 3: A/B/C ranker-vs-pool dissociation.

*** EVAL / DIAGNOSTIC + one method-path arm.  The GT mesh (tune_lib.Harness ->
    mesh_oracle) is read for the EVALUATION and for arm C, which is an EVAL-ONLY CEILING
    and is never a method claim.  Arms A and B are mesh-free. ***

THE QUESTION
    STEP 2 banked a 2DGS ribbon VERIFIER at AUC 0.9294 on clean-solid crease-vs-offcrease.
    That is a ranker over the EXISTING candidate pool.  Does it convert into the deliverable
    metric, and is the binding constraint the RANKER or the POOL?

DESIGN — everything frozen except the RANKING SCORE
    One f=1.00 pulled pool (out/linelets_cadpartA_step3pool.npz, 32,476 candidates: every
    de-floatered gaussian, DT-pulled over the 80 TRAIN views, gate on, edge=sharp).  The
    pull, the length policy and the evaluator are identical across arms; only the score that
    selects the kept subset changes.  Each arm is swept over its keep fraction and the FULL
    P/R frontier is reported.  Evaluation is run_m1b.eval_segments at tau=1.5 on the
    held-out TEST views, i.e. the deliverable metric.

  A   shipped M1a OVERALL per-gaussian score        (control; mesh-free)
  A2  the shipped prune's own ranker, tuned inlier_ratio  (reference; mesh-free)
  B   2DGS ribbon dihedral, frozen rho/xi/n_min, computed over the 80 TRAIN views ONLY so
      the score never sees an evaluation view                              (mesh-free)
  C   ORACLE: -median TEST-view distance to the nearest GT crease pixel.  EVAL-ONLY.  The
      best any ranker could possibly do on this pool; no verifier can beat it.

TWO CEILINGS, as the user's push-back requires
    Arm C is the ceiling of the PULLED pool, i.e. after DT-pull has moved the candidates.
    Reported beside it, eval-only: the RAW gaussian-centre pool recall at tau=1.5, which is
    the ceiling before the pull moves anything.  The gap between them is exactly how much of
    the game the DT-pull is.

FROZEN GO/NO-GO (pre-registered, unchanged from the design argument)
    Conversion GO  iff arm B reaches R@1.5 >= 0.30 at P@1.5 >= 0.70.
    Pool       GO  iff arm C caps BELOW R@1.5 0.45 at P@1.5 >= 0.70.
    Temporal P_pop for the best arm-B point is reported UNGATED (cadpart's 15.3x is not
    calibrated against the chair/lego invariant and must not be transported).
"""
import argparse
import json
import os
import sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common, render, visibility, view_split, render2dgs      # noqa: E402
import diag2dgs                                                        # noqa: E402
import run_m1b                                                         # noqa: E402

OUT = os.path.join(TIER1, "out")
KF_GRID = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15,
           0.12, 0.1, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.015, 0.01]
CONV_R, CONV_P, POOL_R = 0.30, 0.70, 0.45


def sweep(h, P, T, Lh, s, name):
    """Rank by s (higher = better), keep the top kf, evaluate segments@1.5."""
    out = []
    fin = np.isfinite(s)
    ss = np.where(fin, s, -np.inf)
    for kf in KF_GRID:
        k = ss >= np.quantile(ss[fin], 1.0 - kf) if kf < 1.0 else np.ones(len(s), bool)
        k = k & fin if kf < 1.0 else fin
        if k.sum() < 10:
            continue
        e = run_m1b.eval_segments(h, P, T, Lh, keep=k, taus=(1.5,))
        out.append({"keep_frac": kf, "n": int(k.sum()),
                    "P1.5": e[1.5][0], "R1.5": e[1.5][1], "n_px": e["n_px"]})
        print(f"    {name:22s} kf {kf:5.3f}  n {int(k.sum()):6d}  "
              f"P {e[1.5][0]:.4f}  R {e[1.5][1]:.4f}", flush=True)
    return out


def best_at(front, pmin):
    ok = [r for r in front if r["P1.5"] >= pmin]
    return max(ok, key=lambda r: r["R1.5"]) if ok else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="cadpartA")
    ap.add_argument("--pool_tag", default="_step3pool")
    ap.add_argument("--model2dgs", default=os.path.join(OUT, "2dgs_cadpartA"))
    ap.add_argument("--rho", type=float, default=4.0)     # lego-frozen, verbatim
    ap.add_argument("--xi", type=float, default=0.25)     # lego-frozen, verbatim
    ap.add_argument("--n_min", type=int, default=5)       # lego-frozen, verbatim
    ap.add_argument("--scores_only", action="store_true",
                    help="compute + cache the arm scores, skip the sweep")
    ap.add_argument("--rescore", action="store_true",
                    help="ignore the cached arm scores and recompute")
    ap.add_argument("--len_mod", action="store_true",
                    help="use the tuned length policy instead of the raw half-length")
    args = ap.parse_args()

    z = np.load(os.path.join(OUT, f"linelets_{args.scene}{args.pool_tag}.npz"))
    P0, P1, T1, L1 = z["p0"], z["p"], z["t"], z["l"]
    Lh = z["l_mod_tuned"] if (args.len_mod and "l_mod_tuned" in z.files) else L1
    print(f"[{args.scene}] pooled candidates {len(P1)}  "
          f"(length = {'tuned+len' if args.len_mod else 'raw'})", flush=True)

    from tune_lib import Harness                                  # EVAL ONLY (mesh)
    h = Harness(args.scene, views=tuple(view_split.TEST))
    cams, _ = common.load_cameras(args.scene)
    g = common.load_gaussians(args.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep_g]

    res = {"scene": args.scene, "n_pool": int(len(P1)), "n_gaussians": int(len(X)),
           "eval_views": list(view_split.TEST), "length": "tuned" if args.len_mod else "raw",
           "frozen": {"rho": args.rho, "xi": args.xi, "n_min": args.n_min},
           "gates": {"conversion": f"arm B R>={CONV_R} at P>={CONV_P}",
                     "pool": f"arm C caps BELOW R {POOL_R} at P>={CONV_P}"},
           "mesh_eval_only": ("mesh -> evaluation + arm C ceiling ONLY; arms A/A2/B are "
                              "mesh-free and arm C is never a method claim")}

    # ---------------- the RAW-centre ceiling (eval-only), the user's second ceiling -----
    pts_raw = run_m1b.eval_points(h, X, taus=(1.5, 2.5))
    res["raw_centre_pool"] = {
        "n": int(len(X)), "P1.5": pts_raw[1.5][0], "R1.5": pts_raw[1.5][1],
        "P2.5": pts_raw[2.5][0], "R2.5": pts_raw[2.5][1],
        "note": ("recall of ALL de-floatered gaussian CENTRES at tau=1.5 in the M1b "
                 "harness. Culling can only lower it, so this recall IS the raw-centre "
                 "ceiling. Distinct from the banked p1b 3-D point recall 0.2021 at radius "
                 "0.004860, which is a different harness and a different metric.")}
    print(f"  [raw centres] n {len(X)}  P@1.5 {pts_raw[1.5][0]:.4f}  "
          f"R@1.5 {pts_raw[1.5][1]:.4f}", flush=True)

    # ---------------- arm scores --------------------------------------------------------
    scache = os.path.join(OUT, f"geoline_step3_scores_{args.scene}.npz")
    if os.path.exists(scache) and not args.rescore:
        zc = np.load(scache)
        scores = {k: zc[k] for k in zc.files}
        print(f"  [scores] reusing {os.path.basename(scache)}", flush=True)
        return finish(args, res, h, P1, T1, Lh, scores, pts_raw)
    scores = {}
    sp = os.path.join(OUT, f"finalscore_overall_{args.scene}.npy")
    if os.path.exists(sp):
        sA = np.load(sp)
    else:
        import m1a_seeds
        _, sA, _, _ = m1a_seeds.extract_seeds(args.scene, "overall", keep_f=1.0)
        np.save(sp, sA)
    scores["A_overall"] = sA[z["seed_idx"]]
    scores["A2_pruneranker"] = z["inlier_ratio_tuned"] if "inlier_ratio_tuned" in z.files \
        else z["inlier_ratio"]

    # arm B: 2DGS ribbon over the 80 TRAIN views ONLY (never an evaluation view)
    import torch
    tv = list(view_split.TRAIN)
    g2, pipe2, meta2 = render2dgs.load_2dgs(args.model2dgs)

    class Shim:                       # what diag2dgs.ribbon_dihedral consumes
        pass
    print(f"  [armB] 2DGS ribbon over {len(tv)} TRAIN views, ONE VIEW AT A TIME",
          flush=True)
    # diag2dgs.ribbon_dihedral is called per view and the median is taken across views
    # here.  That is ARITHMETICALLY IDENTICAL to handing it all 80 views at once (it
    # medians the per-view values over the views where the linelet is visible and the
    # ribbon is valid), and it keeps one 800x800x3 normal map in RAM instead of eighty.
    # The estimator itself is still imported verbatim and unmodified.
    per_view = np.full((len(tv), len(P1)), np.nan, np.float32)
    for j, v in enumerate(tv):
        gb1 = render.render_gbuffer(g, keep_g, cams[v])
        sh = Shim()
        sh.cams = cams
        sh.gbufs = {v: {"depth": gb1["depth"]}}
        fgv = {v: (gb1["alpha"].detach().cpu().numpy() > 0.5)}
        gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe2, cams[v],
                                             bg_white=meta2.get("white_background", True))
        n2v = {v: gb2["normal"].detach().cpu().numpy().astype(np.float32)}
        th_v, nok_v = diag2dgs.ribbon_dihedral(P1, T1, sh, [v], n2v, fgv)
        per_view[j] = np.where(nok_v > 0, th_v, np.nan)
        del gb1, gb2, n2v, fgv, sh
        if (j + 1) % 20 == 0:
            torch.cuda.empty_cache()
            print(f"    [armB] {j + 1}/{len(tv)} views", flush=True)
    del g2
    torch.cuda.empty_cache()
    with np.errstate(all="ignore"):
        thB = np.nanmedian(per_view, axis=0)
    nokB = np.isfinite(per_view).sum(0)
    scores["B_ribbon2dgs"] = np.where(nokB > 0, thB, np.nan)
    res["armB_measurable_frac"] = float((nokB > 0).mean())
    del per_view
    torch.cuda.empty_cache()

    # arm C: ORACLE ceiling on the PULLED pool (eval-only)
    def oracle(Pos):
        dm = np.full(len(Pos), np.inf)
        acc = [[] for _ in range(len(Pos))]
        for v in view_split.TEST:
            vis, uv, _ = visibility.visible_mask(Pos, h.cams[v], h.gbufs[v]["depth"])
            _, _, cdt = h.crease[v]
            u = np.clip(np.round(uv[:, 0]).astype(int), 0, cdt.shape[1] - 1)
            w = np.clip(np.round(uv[:, 1]).astype(int), 0, cdt.shape[0] - 1)
            d = cdt[w, u]
            for i in np.where(vis)[0]:
                acc[i].append(d[i])
        for i, a in enumerate(acc):
            if a:
                dm[i] = np.median(a)
        return -dm
    scores["C_oracle"] = oracle(P1)
    np.savez(scache, **scores)
    print(f"  [scores] wrote {os.path.basename(scache)}", flush=True)
    if args.scores_only:
        print("  --scores_only: sweep skipped")
        return
    return finish(args, res, h, P1, T1, Lh, scores, pts_raw)


def finish(args, res, h, P1, T1, Lh, scores, pts_raw):
    # ---------------- sweep every arm ---------------------------------------------------
    res["frontiers"] = {}
    for name, s in scores.items():
        print(f"  --- {name}", flush=True)
        res["frontiers"][name] = sweep(h, P1, T1, Lh, np.asarray(s, np.float64), name)

    # ---------------- verdict -----------------------------------------------------------
    v = {}
    for name in scores:
        b = best_at(res["frontiers"][name], CONV_P)
        v[name] = ({"best_at_P0.70": b} if b else {"best_at_P0.70": None})
    B = v["B_ribbon2dgs"]["best_at_P0.70"]
    C = v["C_oracle"]["best_at_P0.70"]
    conv = "GO" if (B and B["R1.5"] >= CONV_R) else "NO-GO"
    pool = "GO" if (C is None or C["R1.5"] < POOL_R) else "NO-GO"
    res["verdict"] = {"per_arm": v, "CONVERSION": conv, "POOL": pool}

    p = os.path.join(OUT, f"geoline_step3_{args.scene}"
                          f"{'_lenmod' if args.len_mod else ''}.json")
    json.dump(res, open(p, "w"), indent=1)
    print("\n  BEST POINT AT P@1.5 >= 0.70")
    for name in scores:
        b = v[name]["best_at_P0.70"]
        print(f"    {name:22s} " + (f"R {b['R1.5']:.4f}  P {b['P1.5']:.4f}  "
                                    f"n {b['n']}  kf {b['keep_frac']}" if b
                                    else "no point reaches P>=0.70"))
    print(f"\n  raw-centre pool recall@1.5 = {pts_raw[1.5][1]:.4f}  "
          f"(vs arm C pulled ceiling above)")
    print(f"  CONVERSION gate (B R>={CONV_R} at P>={CONV_P}): {conv}")
    print(f"  POOL gate (C caps below R {POOL_R}): {pool}")
    print(f"  -> {p}", flush=True)


if __name__ == "__main__":
    main()
