"""PARETO-2 — the oracle-flow temporally-accumulated 2D edge baseline (pareto2_flowbaseline_spec.md).

*** EVAL / ANALYSIS. Mesh enters ONLY for precision labels (GT-crease DTs, incl. trajectory
    frames via mesh_oracle.visible_crease_uv — accumulation is trajectory-dependent, so
    precision is measured on the SAME frames coherence is, for EVERY method). The line
    generation (ours' chains / per-frame detectors / the EMA accumulator with exact rigid
    flow) is mesh-free. ***

THE BASELINE BEING BUILT — deliberately the strongest possible accumulator:
  A_t = alpha * warpback(A_{t-1}) + (1 - alpha) * E_t     ;  L_t = A_t >= 0.5
  * E_t = the per-frame BINARY edge mask (Canny(lo,hi) or nms_thin(pidinet) >= thr),
    so alpha = 0 reproduces the memoryless PARETO-1 point exactly.
  * warpback = EXACT rigid backward flow: each frame-t pixel is unprojected with frame-t
    rendered depth, reprojected into frame t-1, and A_{t-1} is bilinearly sampled there.
    NOT RAFT — the oracle flow, the same geometry PARETO-1's metric uses.
  * OCCLUSION-AWARE (a strengthening no reviewer's RAFT baseline would have): where the
    backprojected point was OCCLUDED in t-1 (z behind the t-1 z-buffer + 2% tol) or lands
    out of frame, the memory is untrustworthy and the accumulator falls back to E_t there
    (locally alpha=0) instead of ghosting the occluder's edges through.
  Sweep: (detector, thr) x alpha in {0.0, 0.3, 0.5, 0.7, 0.85}.

Everything else is the PARETO-1 machinery, imported not reimplemented: frame buffers,
interior restriction (--fg_only semantics), ours' chained f-sweep masks, pooled coherence
(per-warped-pixel DT, pop-rates, flicker). Trajectories T1 orbit + T3 spline, 240 frames.
"""
import os
import sys
import json
import time
import argparse

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    sys.path.insert(0, p)
OUT = os.path.join(TIER1, "out")

from src import common, render, strokes                              # noqa: E402
from src.epipolar_consensus import nms_thin                          # noqa: E402
import temporal_m1b as TM                                            # noqa: E402
import track_o_temporal as TO                                        # T3 spline  # noqa: E402
import pareto_coherence as P1                                        # the PARETO-1 glue  # noqa: E402

ALPHAS = [0.0, 0.3, 0.5, 0.7, 0.85]
CANNY_SWEEP2 = [(50, 150), (100, 250), (150, 300)]
PIDINET_SWEEP2 = [0.3, 0.5, 0.7]
GT_EVERY = 10                     # trajectory frames scored for precision (every 10th)


# ------------------------------------------------------------- oracle backward flow
def backwarp(A_prev, fb_prev, fb_cur, cam_prev, cam_cur, rel_tol=0.02):
    """Sample A_prev at the exact rigid backward flow of every current-frame pixel.
    Returns (warped A [H,W], trust [H,W] bool: sample is in-frame AND unoccluded in t-1)."""
    H, W = A_prev.shape
    d = fb_cur["depth"]
    vv, uu = np.mgrid[0:H, 0:W]
    z = d.reshape(-1)
    ok = np.isfinite(z) & (z > 1e-6) & (z < 1e8)
    u = uu.reshape(-1)[ok].astype(np.float64)
    v_ = vv.reshape(-1)[ok].astype(np.float64)
    zk = z[ok].astype(np.float64)
    f, cx, cy = cam_cur.f, cam_cur.K[0, 2], cam_cur.K[1, 2]
    Xc = np.stack([zk * (u - cx) / f, zk * (v_ - cy) / f, zk], 1)
    R, t = cam_cur.w2c[:3, :3], cam_cur.w2c[:3, 3]
    Xw = (Xc - t) @ R
    Xp = (cam_prev.w2c[:3, :3] @ Xw.T).T + cam_prev.w2c[:3, 3]
    zp = Xp[:, 2]
    up = cam_prev.f * Xp[:, 0] / np.clip(zp, 1e-9, None) + cam_prev.K[0, 2]
    vp = cam_prev.f * Xp[:, 1] / np.clip(zp, 1e-9, None) + cam_prev.K[1, 2]
    inb = (zp > 1e-6) & (up >= 0) & (up <= W - 1.001) & (vp >= 0) & (vp <= H - 1.001)
    # occlusion in t-1: the point sits behind the t-1 z-buffer (3x3-min via cached zmin)
    ui = np.clip(np.round(up).astype(np.int64), 0, W - 1)
    vi = np.clip(np.round(vp).astype(np.int64), 0, H - 1)
    unocc = zp <= fb_prev["zmin"][vi, ui] + rel_tol * zp
    trust_flat = inb & unocc
    Aw = np.zeros(H * W, np.float32)
    tr = np.zeros(H * W, bool)
    idx = np.where(ok)[0]
    good = idx[trust_flat]
    Aw[good] = _bil(A_prev, up[trust_flat], vp[trust_flat])
    tr[good] = True
    return Aw.reshape(H, W), tr.reshape(H, W)


def _bil(img, u, v_):
    H, W = img.shape[:2]
    x0 = np.floor(u).astype(np.int64); y0 = np.floor(v_).astype(np.int64)
    fx = u - x0; fy = v_ - y0
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; dd = img[y0 + 1, x0 + 1]
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + dd * fx * fy


def accumulate_masks(E_seq, fbs, cams, alpha):
    """EMA accumulator with occlusion-aware fallback. E_seq = per-frame BINARY masks.
    Returns (masks L_t, mean disocclusion fraction, mean ghost density in the
    disocclusion band)."""
    if alpha <= 0:
        return list(E_seq), 0.0, 0.0
    masks, dis_fr, ghost = [], [], []
    A = E_seq[0].astype(np.float32)
    masks.append(E_seq[0])
    for t in range(1, len(E_seq)):
        Aw, trust = backwarp(A, fbs[t - 1], fbs[t], cams[t - 1], cams[t])
        E = E_seq[t].astype(np.float32)
        A = np.where(trust, alpha * Aw + (1 - alpha) * E, E)
        L = (A >= 0.5) & fbs[t]["fg"]
        masks.append(L)
        dis = (~trust) & fbs[t]["fg"]
        dis_fr.append(dis.mean())
        band = cv2.dilate(dis.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        if band.any():
            ghost.append(float(L[band].mean()))
    return masks, float(np.mean(dis_fr)), float(np.mean(ghost)) if ghost else 0.0


# ------------------------------------------------------------- trajectory-frame GT (EVAL)
def traj_gt_cdt(scene, tname, traj, force=False):
    """GT-crease distance transforms for every GT_EVERY-th trajectory frame (EVAL-ONLY)."""
    p = os.path.join(TIER1, "cache", f"pareto2_gt_{scene}_{tname}_e{GT_EVERY}.npz")
    if os.path.exists(p) and not force:
        z = np.load(p)
        return {int(k[1:]): z[k] for k in z.files}
    from src.mesh_oracle import MeshOracle                            # EVAL ONLY
    o = MeshOracle(scene)
    out = {}
    for i in range(0, len(traj), GT_EVERY):
        uv = o.visible_crease_uv(traj[i], view_key=("p2", scene, tname, i))
        m = np.zeros((800, 800), bool)
        cu = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
        cv_ = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
        m[cv_, cu] = True
        out[i] = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
        o._depth_cache.clear()
        torch.cuda.empty_cache()
    np.savez(p, **{f"f{k}": v for k, v in out.items()})
    print(f"  [gt] wrote {p} ({len(out)} frames)", flush=True)
    return out


def precision_traj(masks, cdts):
    ps, ns = [], []
    for i, cdt in cdts.items():
        ys, xs = np.nonzero(masks[i])
        ns.append(len(xs))
        if len(xs):
            ps.append(float((cdt[ys, xs] <= 1.5).mean()))
    return {"P15_traj": float(np.mean(ps)) if ps else 0.0,
            "px_per_frame": float(np.mean([int(m.sum()) for m in masks]))}


# ------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, choices=["chair", "lego"])
    ap.add_argument("--traj", required=True, choices=["T1_orbit", "T3_spline"])
    ap.add_argument("--frames", type=int, default=240)
    args = ap.parse_args()
    scene, tname = args.scene, args.traj
    t00 = time.time()

    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    target = np.median(g["mu"][keep_g], axis=0)
    traj = (TM.orbit_cameras(cams[5], cams[15], args.frames, target)
            if tname == "T1_orbit" else TO.traj_spline(cams, target, args.frames))
    print(f"[p2] {scene} {tname} {args.frames}f", flush=True)

    from cmepi_cache_edges import PiDiNetDetector
    det = PiDiNetDetector("cuda")
    fbs, probs = [], []
    for i, cam in enumerate(traj):
        fb = P1.frame_buffers(g, keep_g, cam)
        probs.append(det.prob(np.repeat(fb["gray"][:, :, None], 3, axis=2)).astype(np.float16))
        fbs.append(fb)
        if i % 80 == 0:
            print(f"  frame {i}/{args.frames} ({time.time()-t00:.0f}s)", flush=True)
    del det
    torch.cuda.empty_cache()
    cdts = traj_gt_cdt(scene, tname, traj)
    print(f"[p2] buffers + GT ready ({time.time()-t00:.0f}s)", flush=True)

    rows = []

    def score(name, kind, param, masks, extra=None):
        co = P1.pooled_coherence(masks, fbs, traj)
        pd = precision_traj(masks, cdts)
        row = {"name": name, "kind": kind, "param": param, **co, **pd, **(extra or {})}
        rows.append(row)
        print(f"  [{name:30s}] P@1.5 {pd['P15_traj']:.4f} px/fr {pd['px_per_frame']:7.0f} "
              f"pop>2 {co.get('pop_gt2px', float('nan')):.4f} flick {co['flicker']:.3f} "
              f"E_mean {co['E_pool_mean']:.3f}", flush=True)

    # ---- OURS f-sweep (chained exactly as PARETO-1 / the published temporal eval)
    for variant, f in P1.OURS_SWEEP[scene]:
        z = np.load(os.path.join(OUT, f"linelets_{scene}_{variant}_f{f}.npz"))
        keep = z["keep"].astype(bool)
        p, t_, l = z["p"][keep], z["t"][keep], z["l"][keep]
        ch, kept = strokes.chain_linelets_3d(p, t_, l, conf=z["inlier_ratio"][keep],
                                             **P1.CHAIN_KW)
        P3 = p[kept]
        chain3d = [P3[c] for c in ch]
        cat = (np.concatenate(chain3d, 0), np.cumsum([0] + [len(c) for c in chain3d]))
        masks = [P1.ours_mask(chain3d, traj[i], fbs[i], _cat=cat)[0]
                 for i in range(len(traj))]
        score(f"OURS f={f}", "ours", float(f), masks)

    # ---- accumulated baselines: (detector, thr) x alpha
    for lo, hi in CANNY_SWEEP2:
        E = [P1.canny_mask(fb, lo, hi) for fb in fbs]
        for a in ALPHAS:
            masks, disf, ghost = accumulate_masks(E, fbs, traj, a)
            score(f"CANNY {lo}/{hi} a={a}", "canny_acc" if a > 0 else "canny",
                  [lo, hi, a], masks, {"alpha": a, "disocc_frac": disf,
                                       "ghost_density_disocc_band": ghost})
    thin = [nms_thin(p.astype(np.float32)) for p in probs]
    for thr in PIDINET_SWEEP2:
        E = [(tp >= thr) & fb["fg"] for tp, fb in zip(thin, fbs)]
        for a in ALPHAS:
            masks, disf, ghost = accumulate_masks(E, fbs, traj, a)
            score(f"PIDINET {thr} a={a}", "pidinet_acc" if a > 0 else "pidinet",
                  [thr, a], masks, {"alpha": a, "disocc_frac": disf,
                                    "ghost_density_disocc_band": ghost})

    jp = os.path.join(OUT, f"pareto2_{scene}_{tname}.json")
    json.dump({"scene": scene, "traj": tname, "frames": args.frames,
               "precision_frames": sorted(cdts), "alphas": ALPHAS,
               "accumulator": "A_t = a*backwarp(A_{t-1}) + (1-a)*E_t, rethr 0.5, "
                              "occlusion-aware fallback to E_t; exact rigid flow",
               "rows": rows}, open(jp, "w"), indent=2)
    print(f"\nwrote {jp}  ({time.time()-t00:.0f}s)")


if __name__ == "__main__":
    main()
