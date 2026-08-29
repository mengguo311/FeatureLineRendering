#!/usr/bin/env python
"""TRACK P — temporal-win generalization: E_warp + per-stroke survival, 6 conditions.

*** MESH-FREE. No mesh is imported anywhere in this file. Cameras are the frozen held-out
    TEST views; the scene centre is the median gaussian position. ***

Arms (no arm C — culling is abandoned and Track O showed it hurts temporal):
  A = per-frame TEED on the rendered frame (image-space baseline)
  B = unculled object-space TEED-seeded linelets (our method)

Conditions = {chair, lego} x {T1_orbit, T2_orbit_zoom, T3_spline}. Trajectory generators are
IMPORTED from scripts/track_o_temporal.py so every arm sees identical, look-at-corrected
frames and T1 still reproduces the published motion.

METRIC 1 - E_warp. Frame t's strokes are forward-warped into frame t+1 through the rendered
depth and the two camera poses (for a rigid scene with known depth and pose this warp IS the
optical flow, computed exactly rather than estimated), then matched by
stroke_metric.match_strokes. E_warp = the MEDIAN, over every matched (stroke, frame-pair), of
the chamfer distance in pixels between the warped stroke and its match. Lower = more stable.
Reported as the ratio E_warp(A) / E_warp(B); higher means the object-space carrier is more
stable than per-frame detection.

METRIC 2 - per-stroke SURVIVAL. Stroke identity is chained across frames through
match_strokes' match_idx: a stroke survives a transition iff it warps (>= 2 vertices land)
AND matches a target within match_thresh. Its lifetime is the number of consecutive
transitions it survives. We report P(lifetime > K) for K in {2,4,8,16,32} and the median
lifetime, per arm, plus the ratio median_B / median_A.

Both metrics reuse the validated operators (warp_strokes / match_strokes); nothing is
reimplemented.
"""
import argparse, json, os, sys, time

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    if p not in sys.path:
        sys.path.insert(0, p)

import cv2                                                        # noqa: E402
import torch                                                      # noqa: E402
from src import common, render, stroke_metric                     # noqa: E402
import m1b_stroke_temporal as MST                                 # noqa: E402
import track_o_temporal as TO                                     # trajectories + TEED  # noqa: E402

OUT = os.path.join(TIER1, "out")
K_SURV = [2, 4, 8, 16, 32]


def lifetimes(frames, key, args):
    """Chain stroke identity across frames via match_idx -> per-stroke lifetimes.

    A stroke alive at frame t survives into t+1 iff it warps (>=2 vertices) and its warped
    polyline matches a target stroke within match_thresh. Lifetime counts the consecutive
    transitions survived; strokes still alive at the last frame are right-censored and are
    counted at their observed length (a conservative UNDER-estimate for both arms equally).
    """
    live = {}                       # current-frame stroke index -> lifetime so far
    done = []
    for i in range(len(frames) - 1):
        f0, f1 = frames[i], frames[i + 1]
        src, dst = f0[key], f1[key]
        for j in range(len(src)):
            live.setdefault(j, 0)
        w, surv = stroke_metric.warp_strokes(src, f0["depth"], f0["cam"], f1["cam"])
        m = stroke_metric.match_strokes(w, dst, n_resample=args.n_resample,
                                        max_cand=args.max_cand,
                                        cand_radius=args.cand_radius,
                                        match_thresh=args.match_thresh)
        midx = m["match_idx"]
        surv_ix = np.where(surv)[0]
        nxt = {}
        matched_src = set()
        for wi, si in enumerate(surv_ix):
            j = int(midx[wi]) if wi < len(midx) else -1
            if j >= 0:
                nxt[j] = max(nxt.get(j, 0), live.get(si, 0) + 1)
                matched_src.add(si)
        for si, lt in live.items():           # everything that did not carry forward dies
            if si not in matched_src:
                done.append(lt)
        live = nxt
    done.extend(live.values())
    return np.array(done, np.int64) if done else np.zeros(0, np.int64)


def e_warp(frames, key, args):
    """Median matched chamfer displacement (px) over all frame transitions."""
    ch, fr = [], []
    for i in range(len(frames) - 1):
        f0, f1 = frames[i], frames[i + 1]
        w, _ = stroke_metric.warp_strokes(f0[key], f0["depth"], f0["cam"], f1["cam"])
        m = stroke_metric.match_strokes(w, f1[key], n_resample=args.n_resample,
                                        max_cand=args.max_cand,
                                        cand_radius=args.cand_radius,
                                        match_thresh=args.match_thresh)
        if len(m["chamfer"]):
            ch.append(m["chamfer"]); fr.append(m["frechet"])
    if not ch:
        return {"E_warp": float("nan"), "E_frechet": float("nan"), "n_matched": 0}
    ch = np.concatenate(ch); fr = np.concatenate(fr)
    return {"E_warp": float(np.median(ch)), "E_warp_mean": float(ch.mean()),
            "E_frechet": float(np.median(fr)), "n_matched": int(len(ch))}


def surv_stats(lt):
    if not len(lt):
        return {"n": 0, "median": float("nan"),
                **{f"P_gt_{k}": float("nan") for k in K_SURV}}
    return {"n": int(len(lt)), "median": float(np.median(lt)),
            "mean": float(lt.mean()), "max": int(lt.max()),
            **{f"P_gt_{k}": float((lt > k).mean()) for k in K_SURV}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=["chair", "lego"])
    ap.add_argument("--trajectories", nargs="+", default=list(TO.TRAJ))
    ap.add_argument("--variants", nargs="+", default=["chair=tcteed", "lego=tcteed040"])
    ap.add_argument("--frames", type=int, default=240)
    ap.add_argument("--teed_thr", type=float, default=0.5)
    ap.add_argument("--out", default="out/track_p_temporal.json")
    for k, v in (("nms_mult", 1.0), ("cos_tan", 0.60), ("cos_col", 0.50),
                 ("gap_mult", 4.0), ("approx_eps", 1.0), ("cand_radius", 40.0),
                 ("match_thresh", 3.0), ("cp_ratio", 0.8)):
        ap.add_argument(f"--{k}", type=float, default=v)
    for k, v in (("knn", 10), ("min_nodes", 3), ("min_len", 4), ("n_resample", 16),
                 ("max_cand", 6), ("cp_views", 20), ("fg_erode", 2)):
        ap.add_argument(f"--{k}", type=int, default=v)
    ap.add_argument("--carrier_persistence", action="store_true")
    ap.add_argument("--fg_only", action="store_true")
    a = ap.parse_args()
    VAR = dict(x.split("=", 1) for x in a.variants)

    det = TO.TEED()
    res = {"arms": {"A": "per-frame TEED", "B": "unculled object-space linelets"},
           "frames": a.frames, "teed_thr": a.teed_thr, "variants": VAR,
           "held_out": "TEST cams only", "conditions": {}}

    for scene in a.scenes:
        cams, _ = common.load_cameras(scene)
        g = common.load_gaussians(scene)
        keep_g = render.defloat_mask(g["mu"], g["opacity"])
        target = np.median(g["mu"][keep_g], axis=0)
        chB, iB = MST.build_chains(scene, VAR[scene], a)
        print(f"[track-p] {scene}: B={VAR[scene]} -> {iB['n_strokes']} strokes", flush=True)
        for tname in a.trajectories:
            path = TO.TRAJ[tname](cams, target, a.frames)
            t0 = time.time()
            frames = []
            for c in path:
                gb = render.render_gbuffer(g, keep_g, c, with_albedo=True)
                depth = gb["depth"].detach().cpu().numpy()
                alb = gb["albedo"].detach().cpu().numpy()
                gray = np.clip(alb.mean(2) * 255.0, 0, 255).astype(np.uint8)
                fg = None
                if a.fg_only:
                    al = (gb["alpha"].detach().cpu().numpy() > 0.5).astype(np.uint8)
                    fg = cv2.erode(al, np.ones((2 * a.fg_erode + 1,) * 2, np.uint8)) > 0
                sB = MST.ours_strokes(chB, c, gb["depth"], fg=fg)
                sA = TO.teed_strokes(det, gray, a.teed_thr, a.min_len, a.approx_eps, fg=fg)
                del gb
                torch.cuda.empty_cache()
                frames.append({"depth": depth, "cam": c, "A": sA, "B": sB})
            eA, eB = e_warp(frames, "A", a), e_warp(frames, "B", a)
            lA, lB = lifetimes(frames, "A", a), lifetimes(frames, "B", a)
            sA_, sB_ = surv_stats(lA), surv_stats(lB)
            ratio = (eA["E_warp"] / eB["E_warp"]) if eB["E_warp"] > 0 else float("inf")
            lr = (sB_["median"] / sA_["median"]) if sA_["median"] > 0 else float("inf")
            key = f"{scene}|{tname}"
            res["conditions"][key] = {
                "scene": scene, "trajectory": tname,
                "E_warp_A": eA, "E_warp_B": eB, "E_warp_ratio_A_over_B": ratio,
                "survival_A": sA_, "survival_B": sB_,
                "median_lifetime_ratio_B_over_A": lr,
                "n_strokes_B_chain": iB["n_strokes"], "_seconds": time.time() - t0}
            print(f"  [{key:22s}] E_warp A {eA['E_warp']:.3f} / B {eB['E_warp']:.3f} "
                  f"= {ratio:6.2f}x | median life A {sA_['median']:.1f} / B "
                  f"{sB_['median']:.1f} = {lr:6.2f}x  ({time.time()-t0:.0f}s)", flush=True)
            json.dump(res, open(os.path.join(TIER1, a.out), "w"), indent=1, default=float)
    json.dump(res, open(os.path.join(TIER1, a.out), "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
