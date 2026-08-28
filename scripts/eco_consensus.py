"""ECO — per-gaussian EPIPOLAR-CONSENSUS score, spent ADDITIVELY into the M1a ranking vector.

*** METHOD PATH. MESH-FREE. ***  It imports src.{common,render,visibility,view_split,
epipolar_consensus} and final_recipe; none of those touch the GT mesh, and the neighbour pool
is the TRAIN split only, so the held-out TEST eval downstream stays clean.

WHY THIS EXISTS, AND HOW IT DIFFERS FROM NG-MEC STAGE 1
    NG-MEC Stage 1 used the same epipolar-consensus signal as a VETO: it deleted edge pixels
    with fewer than m supporting neighbours and rebuilt the M1a photometric DT from the
    survivors.  That is a hard cull, and it under-performed the learned prior ~7:1 downstream
    (+0.0394 vs +0.2673) even though the 2D gate provably worked (edge purity 0.510 -> 0.556
    while retaining 88.4% of crease pixels, 65.5% of the deletions hallucination-class).
    The lesson the arc has repeatedly paid for -- seed COVERAGE is binding, orthogonal
    information must be spent ADDITIVELY, not as a veto -- says to keep every proposal and
    instead let consensus REWEIGHT the ranking.  That is what this module computes.

WHAT IT COMPUTES, PRECISELY
    Fix a detector cache (the CMEPI carriers: DexiNed@0.7 or TEED@0.5), a band (tau, rho) and
    a neighbour count K.  src.epipolar_consensus.support_counts gives, per evidence view t, the
    detector's thinned+thresholded edge set E_t and a per-pixel support count cnt_t in 0..K.
    Define the nested edge sets  E_t^m = E_t & (cnt_t >= m)  for m = 1..K, so that
    E_t^1 ⊇ E_t^2 ⊇ ... ⊇ E_t^K, and let DT_t^m be the Euclidean distance transform of E_t^m
    and DT_t^0 that of E_t itself.  Then, with the recipe's own SIGMA = 16 px soft kernel,

        A[i] = sum_t  vis[t,i] * exp(-DT_t^0(proj_t(i)) / SIGMA)            (all edge evidence)
        B[i] = sum_t  vis[t,i] * (1/K) sum_{m=1..K} exp(-DT_t^m(proj_t(i)) / SIGMA)
        C[i] = B[i] / max(A[i], eps)                                        in [0, 1]

    C[i] is "of the photometric edge evidence this gaussian actually draws on, what fraction is
    multi-view consistent".  It is threshold-free in m (every m from 1 to K contributes), it
    reuses the recipe's own proximity kernel so it is commensurate with the DP channel, and it
    is normalised by the very evidence it reweights, so it does NOT smuggle in a second copy of
    the photometric signal -- a gaussian sitting on a strong but view-dependent contour gets a
    LOW C even though its A is high, which is exactly the FP class the spec targets.

    C = 1 <=> every edge near the gaussian had full K-neighbour support.
    C = 0 <=> the nearby edges had no support at all (a single-view contour).

HOW IT IS SPENT (scripts/eco_score.py does the spending; this module only produces C)
    Additively, in the recipe's own idiom -- final_recipe combines channels as
    g = _R(soft) + 0.5*_R(rq90) with _R = rankdata/len -- never as a cull.

WHAT IT IS NOT
    It is NOT a normal/geometry veto.  The normal-gate half of NG-MEC is refuted (vanilla-3DGS
    normals are AUC~0.5 for crease-vs-fabric) and is deliberately absent here.
"""
import os
import sys
import json
import time
import argparse

import cv2
import numpy as np
import torch
from scipy.ndimage import map_coordinates

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
SYN = os.path.join(TIER1, "scripts/explore/syn")
sys.path.insert(0, TIER1)
sys.path.insert(0, SYN)

from src import common, render, visibility, view_split, epipolar_consensus as EC
import final_recipe as FR

OUT = os.path.join(TIER1, "out")


def evidence_views(cams):
    """The 25 spread views the published M1a recipe accumulates evidence over."""
    return np.unique(np.round(np.linspace(0, len(cams) - 1, FR.N_VIEWS)).astype(int))


def consensus_per_gaussian(scene, cache, thr, tau, rho, K, key="native", nms=True,
                           device="cuda", verbose=True, sigma_c=None, cmode="nested"):
    """-> (C [M] float64 in [0,1], A [M], diag dict).  Mesh-free."""
    cams, rgb_paths = common.load_cameras(scene)
    views = evidence_views(cams)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep]
    M = len(X)

    z = np.load(os.path.join(SYN, f"final_evid_{scene}.npz"))
    VIS = z["vis"]
    assert VIS.shape == (len(views), M), (VIS.shape, (len(views), M))

    t0 = time.time()
    counts = EC.support_counts(scene, list(views), cache, [(tau, rho)], K=K, thr=thr,
                               key=key, pool=list(view_split.TRAIN), device=device,
                               verbose=verbose, nms=nms)[(tau, rho)]
    if verbose:
        print(f"[eco] support counts done in {time.time()-t0:.0f}s", flush=True)

    # The consensus kernel need not equal the DP channel's SIGMA=16 px.  At 16 px the ratio
    # B/A integrates such a wide neighbourhood that almost every gaussian finds SOME fully
    # supported edge inside it and C collapses towards 1 (measured: q10 0.746, q50 0.938).  A
    # sharper kernel makes C reflect the edges the gaussian actually sits on.  It is swept on
    # chair VAL like every other ECO knob; SIGMA is the default so the un-swept behaviour is
    # the recipe's own.
    sig = FR.SIGMA if sigma_c is None else float(sigma_c)
    A = np.zeros(M, np.float64)
    B = np.zeros(M, np.float64)
    hist = np.zeros(K + 1, np.int64)
    n_edge = 0
    for vi, v in enumerate(views):
        cam = cams[v]
        Ev, cmap = counts[v]
        n_edge += int(Ev.sum())
        hist += np.bincount(cmap[Ev], minlength=K + 1)[:K + 1]

        # DT of ALL detector edges.  LICENSING SELF-CHECK: this must be the very distance
        # transform the M1a photometric channel consumes for this detector, otherwise the
        # consensus is being measured on a different edge set than the score it reweights.
        dt0 = cv2.distanceTransform((~Ev).astype(np.uint8), cv2.DIST_L2, 5)
        if vi == 0:
            FR.set_edge_source("teed", cache=cache, key=key, thr=thr, nms=nms)
            ref_E = FR.photo_edge_map(rgb_paths[v]) > 0
            ref_dt = FR.photo_edge_dt(rgb_paths[v])
            assert np.array_equal(Ev, ref_E), "consensus edge set != M1a edge set"
            assert np.array_equal(dt0, ref_dt), "consensus DT != M1a photometric DT"
            FR.set_edge_source("canny")
            if verbose:
                print("    [eco] licensing self-check PASS: consensus is computed on exactly "
                      "the edge set / DT the M1a photometric channel consumes", flush=True)
        dts = [dt0]
        if cmode == "nested":
            for m in range(1, K + 1):
                Em = Ev & (cmap >= m)
                dts.append(cv2.distanceTransform((~Em).astype(np.uint8), cv2.DIST_L2, 5)
                           if Em.any() else np.full(Ev.shape, 1e6, np.float32))
        else:                                     # "nearest": cfrac of the NEAREST edge pixel
            _, lab = cv2.distanceTransformWithLabels(
                (~Ev).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
            ys, xs = np.nonzero(Ev)
            lut = np.zeros(int(lab.max()) + 1, np.float32)
            lut[lab[ys, xs]] = cmap[ys, xs].astype(np.float32) / K
            cf_near = lut[lab]

        gb = render.render_gbuffer(g, keep, cam)
        _, uv, _ = visibility.visible_mask(X, cam, gb["depth"])
        del gb
        torch.cuda.empty_cache()
        uu = np.clip(uv[:, 0], 0, cam.W - 1)
        ww = np.clip(uv[:, 1], 0, cam.H - 1)

        vis_v = VIS[vi]
        e0 = np.exp(-map_coordinates(dts[0], [ww, uu], order=1, mode="nearest") / sig)
        A += np.where(vis_v, e0, 0.0)
        if cmode == "nested":
            acc = np.zeros(M, np.float64)
            for m in range(1, K + 1):
                acc += np.exp(-map_coordinates(dts[m], [ww, uu], order=1,
                                               mode="nearest") / sig)
            B += np.where(vis_v, acc / K, 0.0)
        else:
            cfn = map_coordinates(cf_near, [ww, uu], order=1, mode="nearest")
            B += np.where(vis_v, e0 * cfn, 0.0)
        if verbose and (vi % 8 == 0 or vi == len(views) - 1):
            print(f"    [eco] view {vi+1}/{len(views)} (v{v})  {time.time()-t0:.0f}s",
                  flush=True)

    C = np.where(A > 1e-12, B / np.maximum(A, 1e-12), 0.0)
    C = np.clip(C, 0.0, 1.0)
    # Match the recipe's own convention for gaussians visible in NO evidence view: score_from_
    # evidence pushes them below every real value (soft[never] = soft.min() - 1) rather than
    # letting them tie at 0 with genuinely zero-consensus gaussians.
    never = VIS.sum(0) == 0
    n_never = int(never.sum())
    if n_never:
        C[never] = C.min() - 1.0
    diag = {
        "scene": scene, "cache": cache, "thr": thr, "tau": tau, "rho": rho, "K": K,
        "key": key, "nms": nms, "sigma_c": float(sig), "cmode": cmode,
        "n_never_visible": n_never, "M": int(M),
        "n_evidence_views": int(len(views)),
        "evidence_views": [int(v) for v in views],
        "neighbour_pool": "TRAIN", "n_pool": int(len(view_split.TRAIN)),
        "edge_px_total": int(n_edge),
        "support_hist_over_edge_px": hist.tolist(),
        "frac_edge_px_full_support": float(hist[K] / max(hist.sum(), 1)),
        "frac_edge_px_zero_support": float(hist[0] / max(hist.sum(), 1)),
        "C_mean": float(C.mean()), "C_std": float(C.std()),
        "C_quantiles": {q: float(np.quantile(C, q))
                        for q in (0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99)},
        "A_mean": float(A.mean()),
        "runtime_s": time.time() - t0,
    }
    return C, A, diag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--det", required=True, choices=["dexined", "teed", "pidinet"],
                    help="which CMEPI carrier's cached probability maps to run consensus on")
    ap.add_argument("--thr", type=float, default=None,
                    help="default: the CMEPI carrier threshold (dexined 0.7, teed 0.5)")
    ap.add_argument("--tau", type=float, default=1.5, help="epipolar support radius, px")
    ap.add_argument("--rho", type=float, default=0.0,
                    help="depth-band half-width; 0 = pure reprojection at the rendered depth. "
                         "NG-MEC measured rho=7 (the depth-free reading) to be nearly vacuous "
                         "-- it removes 0.7%% of pixels -- so only depth-anchored bands are used.")
    ap.add_argument("--K", type=int, default=3, help="neighbour count (spec sweeps 1/3/5)")
    ap.add_argument("--key", default="native")
    ap.add_argument("--cmode", default="nested", choices=["nested", "nearest"],
                    help="nested: (1/K)sum_m exp(-DT(E&cnt>=m)/sig) / exp(-DT(E)/sig). "
                         "nearest: proximity-weighted mean of the consensus FRACTION of the "
                         "nearest edge pixel. Both are threshold-free in m; which one wins is "
                         "decided on chair VAL like every other knob.")
    ap.add_argument("--sigma_c", type=float, default=None,
                    help="soft kernel (px) for the consensus channel; default = the recipe's "
                         "SIGMA=16. Swept on chair VAL only.")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--tag", default=None, help="output stem; default derived from the args")
    args = ap.parse_args()

    thr = args.thr if args.thr is not None else (0.7 if args.det == "dexined" else 0.5)
    cache = os.path.join(OUT, f"{args.det}_edges_{args.scene}")
    assert os.path.isdir(cache), f"missing detector cache {cache}"
    sg = args.sigma_c if args.sigma_c is not None else FR.SIGMA
    tag = args.tag or (f"{args.det}{thr:g}_K{args.K}_t{args.tau:g}_r{args.rho:g}_s{sg:g}"
                       + ("" if args.cmode == "nested" else "_near"))

    print(f"[eco] scene={args.scene} det={args.det} thr={thr} tau={args.tau} rho={args.rho} "
          f"K={args.K}\n[eco] cache={cache}\n[eco] tag={tag}", flush=True)
    C, A, diag = consensus_per_gaussian(args.scene, cache, thr, args.tau, args.rho, args.K,
                                        key=args.key, device=args.device,
                                        sigma_c=args.sigma_c, cmode=args.cmode)
    diag["tag"] = tag
    np.save(os.path.join(OUT, f"eco_C_{args.scene}__{tag}.npy"), C)
    jp = os.path.join(OUT, f"eco_consensus_{args.scene}__{tag}.json")
    json.dump(diag, open(jp, "w"), indent=2)
    h = diag["support_hist_over_edge_px"]
    print(f"[eco] edge px {diag['edge_px_total']}, support hist (0..K) {h}", flush=True)
    print(f"[eco] C mean {diag['C_mean']:.4f} sd {diag['C_std']:.4f}  "
          f"q10 {diag['C_quantiles'][0.1]:.4f} q50 {diag['C_quantiles'][0.5]:.4f} "
          f"q90 {diag['C_quantiles'][0.9]:.4f}", flush=True)
    print(f"[eco] wrote out/eco_C_{args.scene}__{tag}.npy and {os.path.basename(jp)} "
          f"({diag['runtime_s']:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
