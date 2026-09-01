"""Matched-precision + matched-density coherence Pareto (pareto_spec.md).

*** EVAL / ANALYSIS. Mesh enters ONLY via the TEST-view GT-crease caches
    cache/oracle_<scene>_a30_v5-...-95.npz (precision scoring). The method path
    (linelet chains / Canny / PiDiNet on rendered frames) is mesh-free. ***

DESIGN — one measurement, three axes, all on the SAME line sets in the SAME image domain:
  * line sets: OURS = the banked f-sweep linelet clouds chained exactly as the published
    temporal eval chains them (m1b_stroke_temporal defaults), projected per frame with the
    same occlusion test; CANNY/PIDINET = per-frame detection on the same albedo-gray render.
  * domain: 3DGS albedo renders everywhere. Coherence on the published 240-frame look-at-
    corrected T1 orbit between TEST cams 5->15; precision+density on the 10 held-out TEST
    views. Every method is INTERIOR-restricted (alpha>0.5 eroded 2 px, the banked --fg_only
    control) so the silhouette warp-drop confound is removed at source for ALL methods.
  * E_warp POOLED (the spec's normalization): for every ON pixel of frame t's line mask with
    finite depth, forward-warp through the rendered depth + the two poses (exact rigid flow),
    then read the distance transform of frame t+1's line mask at the warped pixel. Pool ALL
    such distances over ALL 239 transitions -> median (primary) and mean(min(d,20)).
    No per-line averaging, no matching step: a vanished line's pixels land far from any
    target pixel and are charged automatically (popping is inside the metric, unlike the
    banked matched-stroke E_warp). Also reported: the banked pixel-pooled flicker
    (1px-tolerant XOR/union) and the warp-drop fraction.
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

from src import common, render, strokes                        # noqa: E402
from src.epipolar_consensus import nms_thin                    # noqa: E402
from src.view_split import TEST                                # noqa: E402
import temporal_m1b as TM                                      # orbit_cameras  # noqa: E402

OURS_SWEEP = {
    "chair": [("tc_teed05", f) for f in ("0.15", "0.22", "0.30", "0.35", "0.40", "0.45", "0.50")],
    "lego": [("tc_teed_native_0.5", f) for f in ("0.15", "0.22", "0.30", "0.35", "0.40",
                                                 "0.45", "0.50", "0.60", "0.70")],
}
CANNY_SWEEP = [(25, 75), (50, 150), (75, 200), (100, 250), (150, 300)]
PIDINET_SWEEP = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.9]
CHAIN_KW = dict(nms_radius_mult=1.0, k=10, cos_tan=0.60, cos_col=0.50, gap_mult=4.0,
                min_nodes=3)                                   # m1b_stroke_temporal defaults
FG_ERODE = 2
D_CAP = 20.0


# ---------------------------------------------------------------- frame machinery
def frame_buffers(g, keep_g, cam):
    gb = render.render_gbuffer(g, keep_g, cam, with_albedo=True)
    depth = gb["depth"].detach()
    zmin = -torch.nn.functional.max_pool2d(
        -torch.nan_to_num(depth, posinf=1e9).float()[None, None], 3, 1, 1)[0, 0]
    alb = gb["albedo"].detach().cpu().numpy()
    gray = np.clip(alb.mean(2) * 255.0, 0, 255).astype(np.uint8)
    a = (gb["alpha"].detach().cpu().numpy() > 0.5).astype(np.uint8)
    fg = cv2.erode(a, np.ones((2 * FG_ERODE + 1,) * 2, np.uint8)) > 0
    d_np = depth.cpu().numpy().astype(np.float32)
    d_np[~np.isfinite(d_np)] = np.inf
    out = {"depth": d_np, "zmin": zmin.cpu().numpy().astype(np.float32),
           "gray": gray, "fg": fg}
    del gb
    torch.cuda.empty_cache()
    return out


def project_visible(V, cam, fb, rel_tol=0.02):
    """visibility.visible_mask semantics on cached numpy buffers."""
    campts = (cam.w2c[:3, :3] @ V.T).T + cam.w2c[:3, 3]
    z = campts[:, 2]
    uv = (cam.K @ campts.T).T
    uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
    u = np.round(uv[:, 0]).astype(np.int64)
    v = np.round(uv[:, 1]).astype(np.int64)
    inb = (z > 0) & (u >= 0) & (u < cam.W) & (v >= 0) & (v < cam.H)
    vis = np.zeros(len(V), bool)
    idx = np.where(inb)[0]
    vis[idx] = z[idx] <= fb["zmin"][v[idx], u[idx]] + rel_tol * z[idx]
    vis[idx] &= fb["fg"][v[idx], u[idx]]
    return vis, uv


def ours_mask(chain3d, cam, fb, min_pts=2, _cat=None):
    """Project the static 3D stroke graph, split at occlusion, raster 1 px (interior).
    One vectorized projection for ALL chains; runs split per chain from the shared arrays."""
    if _cat is None:
        _cat = (np.concatenate(chain3d, 0),
                np.cumsum([0] + [len(c) for c in chain3d]))
    Vall, off = _cat
    vis, uv = project_visible(Vall, cam, fb)
    m = np.zeros((cam.H, cam.W), np.uint8)
    n_str = 0
    uvi = np.round(uv).astype(np.int32)
    for ci in range(len(off) - 1):
        a, b = off[ci], off[ci + 1]
        v = vis[a:b]
        if v.sum() < min_pts:
            continue
        # runs of consecutive visible vertices
        br = np.where(np.diff(v.astype(np.int8)) != 0)[0] + 1
        start = 0
        for end in list(br) + [b - a]:
            if v[start] and end - start >= min_pts:
                cv2.polylines(m, [uvi[a + start:a + end]], False, 1)
                n_str += 1
            start = end
    return (m > 0) & fb["fg"], n_str


def canny_mask(fb, lo, hi):
    return (cv2.Canny(fb["gray"], lo, hi) > 0) & fb["fg"]


def pidinet_mask(prob, fb, thr):
    return (nms_thin(prob.astype(np.float32)) >= thr) & fb["fg"]


# ---------------------------------------------------------------- pooled metrics
def warp_pixels(mask, fb0, cam0, cam1):
    """ON pixels of mask -> world via frame-0 depth -> frame-1 pixels. Returns
    (warped uv int [M,2] in-bounds, n_total, n_dropped)."""
    vv, uu = np.nonzero(mask)
    n = len(uu)
    z = fb0["depth"][vv, uu]
    ok = np.isfinite(z) & (z > 1e-6) & (z < 1e8)
    u = uu[ok].astype(np.float64)
    v_ = vv[ok].astype(np.float64)
    zk = z[ok].astype(np.float64)
    f, cx, cy = cam0.f, cam0.K[0, 2], cam0.K[1, 2]
    Xc = np.stack([zk * (u - cx) / f, zk * (v_ - cy) / f, zk], 1)
    R0, t0 = cam0.w2c[:3, :3], cam0.w2c[:3, 3]
    Xw = (Xc - t0) @ R0
    Xc1 = (cam1.w2c[:3, :3] @ Xw.T).T + cam1.w2c[:3, 3]
    z1 = Xc1[:, 2]
    u1 = cam1.f * Xc1[:, 0] / np.clip(z1, 1e-9, None) + cam1.K[0, 2]
    v1 = cam1.f * Xc1[:, 1] / np.clip(z1, 1e-9, None) + cam1.K[1, 2]
    inb = (z1 > 1e-6) & (u1 >= 0) & (u1 < cam1.W - 0.5) & (v1 >= 0) & (v1 < cam1.H - 0.5)
    w = np.stack([np.round(u1[inb]), np.round(v1[inb])], 1).astype(np.int64)
    return w, n, n - int(inb.sum())


def pooled_coherence(masks, fbs, cams):
    """Pooled E_warp + flicker across all consecutive transitions."""
    dists, drop_n, tot_n = [], 0, 0
    fl_x, fl_u = 0, 0
    for t in range(len(masks) - 1):
        L0, L1 = masks[t], masks[t + 1]
        if not L1.any() or not L0.any():
            tot_n += int(L0.sum())
            drop_n += int(L0.sum())
            continue
        dt1 = cv2.distanceTransform((~L1).astype(np.uint8), cv2.DIST_L2, 5)
        w, n, nd = warp_pixels(L0, fbs[t], cams[t], cams[t + 1])
        tot_n += n
        drop_n += nd
        if len(w):
            dists.append(dt1[w[:, 1], w[:, 0]])
        # banked-style pixel flicker with 1 px tolerance: warped mask vs target
        wm = np.zeros_like(L1)
        if len(w):
            wm[w[:, 1], w[:, 0]] = True
        k = np.ones((3, 3), np.uint8)
        wm_d = cv2.dilate(wm.astype(np.uint8), k) > 0
        L1_d = cv2.dilate(L1.astype(np.uint8), k) > 0
        inter = (wm & L1_d) | (L1 & wm_d)
        union = wm | L1
        fl_x += int(union.sum()) - int((inter & union).sum())
        fl_u += int(union.sum())
    d = np.concatenate(dists) if dists else np.zeros(0)
    out = {"E_pool_median": float(np.median(d)) if len(d) else float("nan"),
           "E_pool_mean": float(np.minimum(d, D_CAP).mean()) if len(d) else float("nan"),
           "n_pooled_px": int(len(d)),
           "warp_drop_frac": drop_n / max(tot_n, 1),
           "flicker": fl_x / max(fl_u, 1)}
    if len(d):
        for q in (75, 90, 95, 99):
            out[f"E_pool_p{q}"] = float(np.percentile(d, q))
        for k in (1, 2, 3, 5):
            # POP RATE: fraction of warped line pixels landing > k px from any line pixel
            # of the next frame. Free of the shared sub-pixel rasterization floor that
            # compresses the pooled-mean ratio at 240-frame motion; still fully pooled.
            out[f"pop_gt{k}px"] = float((d > k).mean())
    return out


def precision_density(masks_test, scene, taus=(1.5,)):
    z = np.load(os.path.join(TIER1, "cache",
                             f"oracle_{scene}_a30_v{'-'.join(map(str, TEST))}.npz"))
    ps, ns = [], []
    for v, m in zip(TEST, masks_test):
        ys, xs = np.nonzero(m)
        ns.append(len(xs))
        if not len(xs):
            continue
        cdt = z[f"cdt{v}"]
        ps.append(float((cdt[ys, xs] <= 1.5).mean()))
    return {"P15_macro": float(np.mean(ps)) if ps else 0.0,
            "px_per_view": float(np.mean(ns)),
            "n_views_scored": len(ps)}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, choices=["chair", "lego"])
    ap.add_argument("--frames", type=int, default=240)
    args = ap.parse_args()
    scene = args.scene
    t00 = time.time()

    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    target = np.median(g["mu"][keep_g], axis=0)
    traj = TM.orbit_cameras(cams[5], cams[15], args.frames, target)
    print(f"[pareto] {scene}: {args.frames}-frame look-at orbit TEST 5->15  "
          f"target {target.round(3)}", flush=True)

    # PiDiNet, frozen zero-shot (banked contract via cmepi_cache_edges)
    from cmepi_cache_edges import PiDiNetDetector
    det = PiDiNetDetector("cuda")

    # ---- render every trajectory frame once; cache buffers + pidinet prob
    fbs, probs = [], []
    for i, cam in enumerate(traj):
        fb = frame_buffers(g, keep_g, cam)
        bgr = np.repeat(fb["gray"][:, :, None], 3, axis=2)     # banked track_o convention
        probs.append(det.prob(bgr).astype(np.float16))
        fbs.append(fb)
        if i % 60 == 0:
            print(f"  traj frame {i}/{args.frames} ({time.time()-t00:.0f}s)", flush=True)
    # ---- and the 10 TEST views
    fbs_test = [frame_buffers(g, keep_g, cams[v]) for v in TEST]
    probs_test = [det.prob(np.repeat(fb["gray"][:, :, None], 3, axis=2)).astype(np.float16)
                  for fb in fbs_test]
    del det
    torch.cuda.empty_cache()
    print(f"[pareto] buffers ready ({time.time()-t00:.0f}s)", flush=True)

    rows = []

    def score(name, kind, param, masks_traj, masks_test, extra=None):
        co = pooled_coherence(masks_traj, fbs, traj)
        pd = precision_density(masks_test, scene)
        dens_traj = float(np.mean([int(m.sum()) for m in masks_traj]))
        row = {"name": name, "kind": kind, "param": param, **co, **pd,
               "px_per_frame": dens_traj, **(extra or {})}
        rows.append(row)
        print(f"  [{name:28s}] P@1.5 {pd['P15_macro']:.4f}  px/frame {dens_traj:7.0f}  "
              f"px/view {pd['px_per_view']:7.0f}  E_pool_med {co['E_pool_median']:.3f}  "
              f"mean {co['E_pool_mean']:.3f}  flicker {co['flicker']:.3f}  "
              f"drop {co['warp_drop_frac']:.3f}", flush=True)

    # ---- OURS f-sweep
    for variant, f in OURS_SWEEP[scene]:
        z = np.load(os.path.join(OUT, f"linelets_{scene}_{variant}_f{f}.npz"))
        keep = z["keep"].astype(bool)
        p, t_, l = z["p"][keep], z["t"][keep], z["l"][keep]
        conf = z["inlier_ratio"][keep]
        ch, kept = strokes.chain_linelets_3d(p, t_, l, conf=conf, **CHAIN_KW)
        P3 = p[kept]
        chain3d = [P3[c] for c in ch]
        cat = (np.concatenate(chain3d, 0), np.cumsum([0] + [len(c) for c in chain3d]))
        mt = [ours_mask(chain3d, traj[i], fbs[i], _cat=cat) for i in range(len(traj))]
        masks_traj = [m for m, _ in mt]
        n_str = float(np.mean([n for _, n in mt]))
        masks_test = [ours_mask(chain3d, cams[v], fb, _cat=cat)[0]
                      for v, fb in zip(TEST, fbs_test)]
        score(f"OURS f={f}", "ours", float(f), masks_traj, masks_test,
              {"strokes_per_frame": n_str, "n_linelets": int(keep.sum()),
               "n_chains": len(ch)})

    # ---- CANNY sweep
    for lo, hi in CANNY_SWEEP:
        score(f"CANNY {lo}/{hi}", "canny", [lo, hi],
              [canny_mask(fb, lo, hi) for fb in fbs],
              [canny_mask(fb, lo, hi) for fb in fbs_test])

    # ---- PIDINET sweep (NMS-thinned prob, per frame)
    thin_traj = [nms_thin(p.astype(np.float32)) for p in probs]
    thin_test = [nms_thin(p.astype(np.float32)) for p in probs_test]
    for thr in PIDINET_SWEEP:
        score(f"PIDINET thr={thr}", "pidinet", thr,
              [(tp >= thr) & fb["fg"] for tp, fb in zip(thin_traj, fbs)],
              [(tp >= thr) & fb["fg"] for tp, fb in zip(thin_test, fbs_test)])

    jp = os.path.join(OUT, f"pareto_{scene}.json")
    json.dump({"scene": scene, "frames": args.frames, "trajectory": "T1 orbit 5->15",
               "interior_restricted": True, "fg_erode": FG_ERODE,
               "pooling": "per-warped-pixel DT to next-frame line mask, all transitions",
               "rows": rows}, open(jp, "w"), indent=2)
    print(f"\nwrote {jp}  ({time.time()-t00:.0f}s)")


if __name__ == "__main__":
    main()
