#!/usr/bin/env python
"""URS — Unprojected Ridge Seeding: build the carrier, then score it with the FROZEN metric.

*** MESH-FREE CARRIER. This builder imports common / render / render2dgs / visibility /
    view_split / final_recipe only. It never imports mesh_oracle and never reads the GT mesh.
    The mesh appears ONLY inside scripts/urs_verdict.py:coverage(), the eval-only scorer
    frozen and committed at 09acd9b before any coverage number existed. ***

THE CARRIER (no ranking, no culling, no precision filtering — a pure coverage ceiling):
  1. per source view, take the TEED ridge map: raw sigmoid, NMS-thinned, thresholded,
     restricted to the 3DGS foreground (alpha > 0.5);
  2. UNPROJECT each ridge pixel through the vanilla-3DGS rendered DEPTH buffer, placing a 3D
     point where the ridge actually lands in object space. Seeds are NOT snapped to gaussian
     centroids -- that decoupling is the whole point of the probe;
  3. multi-view EPIPOLAR INTERSECTION: keep a point only if, in at least K_MIN OTHER source
     views where it is the front surface, its projection lands within EPI_PX of a TEED ridge.
     This is the "triangulated ridge" requirement, computed by consensus rather than by
     pairwise matching;
  4. voxel-dedup to respect the budget cap. Dedup is NOT ranking: it removes duplicates of
     the same object-space location, keeping spatial diversity, and never prefers one point
     over another by any quality score.

SPLIT DISCIPLINE. Two arms are built and BOTH are reported:
  train  source views are TRAIN only -> method-legal, no contact with the scored TEST views.
         PRIMARY.
  all    source views include TEST -> deliberately leaky, an upper-upper bound. If even this
         arm falls short of 0.75 the NO-GO is airtight; it is never quoted as the headline.
"""
import argparse, json, os, sys, time

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src import common, render, visibility, view_split            # noqa: E402
import cv2                                                        # noqa: E402

EPI_PX = 1.5
K_MIN = 2          # overridable per-arm; K_MIN=1 disables the consensus filter


def teed_ridge(scene, v, thr, nms=True):
    """Raw TEED sigmoid -> optional NMS thinning -> threshold. Mesh-free."""
    import final_recipe as FR
    z = np.load(os.path.join(TIER1, f"out/teed_edges_{scene}", f"v{v:03d}.npz"))
    p = z["native"].astype(np.float32)
    if nms:
        p = FR.nms_thin(p)
    return p >= thr


def unproject(cam, ys, xs, depth):
    """Pixel + depth -> world point. Inverse of visibility.visible_mask's projection."""
    z = depth[ys, xs].astype(np.float64)
    Kin = np.linalg.inv(cam.K)
    uv1 = np.stack([xs.astype(np.float64), ys.astype(np.float64), np.ones(len(xs))], 1)
    cpts = (Kin @ uv1.T).T * z[:, None]
    R, t = cam.w2c[:3, :3], cam.w2c[:3, 3]
    return (R.T @ (cpts - t).T).T


def voxel_dedup(P, vox):
    if vox <= 0 or not len(P):
        return P
    k = np.round(P / vox).astype(np.int64)
    _, idx = np.unique(k, axis=0, return_index=True)
    return P[np.sort(idx)]


def build(scene, source_views, thr, budget, vox0=0.0015, verbose=True, k_min=None):
    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])

    # ---- pass 1: unproject ridges, and cache each view's ridge DT for the consensus pass
    pts, ridges, depths = [], {}, {}
    t0 = time.time()
    for v in source_views:
        cam = cams[v]
        gb = render.render_gbuffer(g, keep, cam)
        d = gb["depth"].cpu().numpy().astype(np.float64)
        al = gb["alpha"].cpu().numpy()
        del gb
        try:
            import torch; torch.cuda.empty_cache()
        except Exception:
            pass
        fg = (al > 0.5) & np.isfinite(d)
        R = teed_ridge(scene, v, thr) & fg
        ys, xs = np.nonzero(R)
        if len(ys):
            pts.append(unproject(cam, ys, xs, d))
        ridges[v] = cv2.distanceTransform((~R).astype(np.uint8), cv2.DIST_L2, 5)
        depths[v] = d
        if verbose:
            print(f"    [urs] view {v:3d}  ridge px {len(ys):7d}   {time.time()-t0:.0f}s",
                  flush=True)
    P = np.concatenate(pts, 0) if pts else np.zeros((0, 3))
    n_raw = len(P)
    P = voxel_dedup(P, vox0)
    n_dedup0 = len(P)
    if verbose:
        print(f"    [urs] unprojected {n_raw} -> {n_dedup0} after vox {vox0:g} dedup",
              flush=True)

    # ---- pass 2: multi-view epipolar consensus (the "intersection" requirement)
    sup = np.zeros(len(P), np.int32)
    for v in source_views:
        cam = cams[v]
        c = (cam.w2c[:3, :3] @ P.T).T + cam.w2c[:3, 3]
        z = c[:, 2]
        uv = (cam.K @ c.T).T
        uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
        u = np.round(uv[:, 0]).astype(np.int64); w = np.round(uv[:, 1]).astype(np.int64)
        inb = (z > 0) & (u >= 0) & (u < cam.W) & (w >= 0) & (w < cam.H)
        uu = np.clip(u, 0, cam.W - 1); ww = np.clip(w, 0, cam.H - 1)
        dv = depths[v][ww, uu]
        front = inb & np.isfinite(dv) & (np.abs(z - dv) < 0.02)   # front-surface in this view
        near = ridges[v][ww, uu] <= EPI_PX
        sup += (front & near).astype(np.int32)
    km = K_MIN if k_min is None else int(k_min)
    P = P[sup >= km]
    n_consensus = len(P)
    if verbose:
        print(f"    [urs] epipolar consensus K>={K_MIN} within {EPI_PX}px: "
              f"{n_dedup0} -> {n_consensus}", flush=True)

    # ---- pass 3: respect the budget by coarsening the dedup voxel (never by ranking).
    #      BISECTED, not ratcheted: a 1.25x ratchet overshoots badly (it landed 68k points
    #      under an 89.7k budget), and under-spending the budget biases a CEILING probe
    #      toward NO-GO. Bisection lands as close under the cap as the voxel grid allows,
    #      which is the most generous carrier the budget permits. Dedup is still not
    #      ranking: it never prefers one point over another by any quality score.
    vox = vox0
    if len(P) > budget:
        lo, hi = vox0, vox0
        while len(voxel_dedup(P, hi)) > budget and hi < 0.5:
            hi *= 2.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if len(voxel_dedup(P, mid)) > budget:
                lo = mid
            else:
                hi = mid
        vox = hi
        P = voxel_dedup(P, vox)
    if verbose:
        print(f"    [urs] budget {budget}: final {len(P)} pts at vox {vox:.5f}", flush=True)
    return P, {"n_raw_unprojected": int(n_raw), "n_after_vox0": int(n_dedup0),
               "n_after_consensus": int(n_consensus), "n_final": int(len(P)),
               "vox_final": float(vox), "vox0": float(vox0), "thr": float(thr),
               "K_min": km, "epi_px": EPI_PX,
               "n_source_views": len(source_views),
               "source_views": [int(x) for x in source_views]}


if __name__ == "__main__":
    from urs_verdict import coverage, segments_to_points, BUDGET_MULT

    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--baseline_npz", default="out/linelets_lego_gated_test.npz")
    ap.add_argument("--thr", type=float, default=0.5,
                    help="TEED ridge threshold; ceiling probe is deliberately generous "
                         "(repo default for the pipeline is 0.90, reported as an arm)")
    ap.add_argument("--thr_arms", default="0.5,0.9")
    ap.add_argument("--stride", type=int, default=4, help="source-view subsampling")
    ap.add_argument("--k_min", type=int, default=1,
                    help="multi-view ridge support required. DEFAULT 1 = NO consensus "
                         "filter, because urs_spec.md mandates 'NO ranking, NO culling, NO "
                         "precision filtering'. A K>=2 requirement IS culling and is "
                         "reported only as a labelled sensitivity arm.")
    ap.add_argument("--chair_control", action="store_true")
    ap.add_argument("--out", default="out/urs_coverage.json")
    a = ap.parse_args()

    # ---- baseline control, scored with the SAME frozen metric ----------------------
    z = np.load(a.baseline_npz, allow_pickle=True)
    base_pts = segments_to_points(z["p"], z["t"], z["l"])
    n_base_linelets = int(len(z["p"]))
    budget = int(round(BUDGET_MULT * n_base_linelets))
    print(f"[urs] baseline {a.baseline_npz}: {n_base_linelets} linelets "
          f"-> {len(base_pts)} sampled pts;  budget cap {budget} carrier pts\n")
    print("=== BASELINE coverage (control, frozen metric) ===", flush=True)
    base_cov = coverage(a.scene, base_pts)
    base_cov["n_linelets"] = n_base_linelets

    TR = list(view_split.TRAIN)
    arms = {}
    for thr in [float(x) for x in a.thr_arms.split(",")]:
        for arm, sv in (("train", TR[::a.stride]),
                        ("all_leaky", list(range(0, 100, a.stride)))):
            print(f"\n=== URS arm={arm} thr={thr:g} ({len(sv)} source views) ===", flush=True)
            P, diag = build(a.scene, sv, thr, budget, k_min=a.k_min)
            cov = coverage(a.scene, P)
            cov.update(diag)
            arms[f"{arm}|thr{thr:g}|K{a.k_min}"] = cov
            print(f"    [urs] arm={arm} thr={thr:g} K{a.k_min}  COVERAGE = {cov['coverage']:.4f}  "
                  f"n_carrier={cov['n_carrier_pts']}", flush=True)

    # primary = the method-legal TRAIN arm at the most generous threshold
    prim = max([k for k in arms if k.startswith("train")],
               key=lambda k: arms[k]["coverage"])
    res = {"scene": a.scene, "baseline": base_cov, "arms": arms,
           "primary_arm": prim, "urs": arms[prim], "budget_cap": budget}

    if a.chair_control:
        print("\n=== CHAIR sanity control (baseline carrier, same metric) ===", flush=True)
        zc = np.load(os.path.join(TIER1, "out/linelets_chair_gated_test.npz"),
                     allow_pickle=True)
        res["chair_control"] = coverage("chair", segments_to_points(zc["p"], zc["t"], zc["l"]))

    json.dump(res, open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
