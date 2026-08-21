"""tier1/scripts/temporal_m1b.py — M1b temporal-coherence payoff measurement.

FULLY METHOD-PATH: gaussians + cameras only. This script does not import mesh_oracle
and never touches the GT mesh — temporal coherence is a property of the representation,
not of any ground truth.

THE CLAIM UNDER TEST
    Object-space linelets are STATIC 3D primitives, so their projection is exact and
    continuous under camera motion by construction: the only thing that can change
    between frames is occlusion. The M1a image-space baseline (lines_image.py) instead
    re-thresholds a fresh G-buffer every frame, so a pixel sitting near tau flips on and
    off — the classic NPR shower-door flicker. This script quantifies the difference on
    a smooth orbit that passes THROUGH no training view in particular.

THE METRIC
    A raw frame-to-frame XOR would punish honest camera motion, so the comparison is
    geometry-compensated: every ON pixel of frame t-1 is un-projected with that frame's
    gaussian z-buffer and re-projected into frame t, and the flicker is the symmetric
    difference between that warped mask and the mask actually produced at t:

        flicker_t = |warp(L_{t-1}) XOR L_t| / |warp(L_{t-1}) OR L_t|

    Both methods are scored with the identical warp, so disocclusion (which is real, not
    flicker, and affects both) cancels out of the comparison. A 1px-tolerant variant is
    also reported so that pure resampling noise is not counted as flicker.
"""
import argparse
import json
import os
import sys
import time

import cv2
import numpy as np
import torch
from scipy.spatial.transform import Rotation, Slerp

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)

from src import common, render, visibility, lines_image, linelet

OUT = os.path.join(TIER1, "out")


def interp_cameras(cam_a, cam_b, n):
    """n intermediate cameras on a smooth arc from cam_a to cam_b (slerp R, arc C)."""
    ca = np.linalg.inv(cam_a.w2c)
    cb = np.linalg.inv(cam_b.w2c)
    rots = Rotation.from_matrix(np.stack([ca[:3, :3], cb[:3, :3]]))
    slerp = Slerp([0.0, 1.0], rots)
    Ca, Cb = ca[:3, 3], cb[:3, 3]
    ra, rb = np.linalg.norm(Ca), np.linalg.norm(Cb)
    ua, ub = Ca / ra, Cb / rb
    dot = float(np.clip(ua @ ub, -1, 1))
    om = np.arccos(dot)
    out = []
    for s in np.linspace(0.0, 1.0, n):
        R = slerp([s])[0].as_matrix()
        if om < 1e-6:
            u = ua
        else:
            u = (np.sin((1 - s) * om) * ua + np.sin(s * om) * ub) / np.sin(om)
        C = u * ((1 - s) * ra + s * rb)
        c2w = np.eye(4)
        c2w[:3, :3] = R
        c2w[:3, 3] = C
        out.append(common.Camera(cam_a.K, np.linalg.inv(c2w), cam_a.H, cam_a.W,
                                 name=f"interp{s:.3f}"))
    return out


def orbit_cameras(cam_a, cam_b, n, target):
    """Look-at-corrected arc from cam_a to cam_b about `target`.

    WHY THIS EXISTS. temporal_m1b.interp_cameras slerps the rotation and the camera
    centre INDEPENDENTLY. Both endpoints of the 5->15 arc look exactly at the origin
    (residual 0.000), but the interpolated poses in between do not, so the object drifts
    out of frame: measured on chair, the visible object area falls from 130664 px at
    frame 0 to 27012 px at frame 120 and is clipped against the border from frame ~40 to
    ~200. That is harmless for a metric where BOTH pipelines see identical cameras, but
    it makes an unwatchable video. Here the centre is slerped on the sphere about the
    target and the orientation is REBUILT as a look-at, so the object stays framed.
    `target` comes from the gaussians (mesh-free)."""
    ca, cb = np.linalg.inv(cam_a.w2c), np.linalg.inv(cam_b.w2c)
    Ca, Cb = ca[:3, 3] - target, cb[:3, 3] - target
    ra, rb = np.linalg.norm(Ca), np.linalg.norm(Cb)
    ua, ub = Ca / ra, Cb / rb
    om = float(np.arccos(np.clip(ua @ ub, -1, 1)))
    up_w = -(ca[:3, 1] + cb[:3, 1])
    up_w /= max(np.linalg.norm(up_w), 1e-12)
    out = []
    for s in np.linspace(0.0, 1.0, n):
        u = ua if om < 1e-6 else (np.sin((1 - s) * om) * ua +
                                  np.sin(s * om) * ub) / np.sin(om)
        C = target + u * ((1 - s) * ra + s * rb)
        f = target - C
        f /= max(np.linalg.norm(f), 1e-12)
        up = up_w if abs(f @ up_w) < 0.99 else np.array([0.0, 0.0, 1.0])
        r = np.cross(f, up)
        r /= max(np.linalg.norm(r), 1e-12)
        d = np.cross(f, r)
        c2w = np.eye(4)
        c2w[:3, 0], c2w[:3, 1], c2w[:3, 2] = r, d, f
        c2w[:3, 3] = C
        out.append(common.Camera(cam_a.K, np.linalg.inv(c2w), cam_a.H, cam_a.W,
                                 name=f"orbit{s:.3f}"))
    return out


def raster_linelets(p, t, l, cam, depth, shift=4, max_seg_px=64.0):
    """Project + rasterise the visible linelets into a bool mask (METHOD PATH)."""
    vis, _, _ = visibility.visible_mask(p, cam, depth)
    a, b = linelet.endpoints(p, t, l)
    uva, _ = common.project(a, cam)
    uvb, _ = common.project(b, cam)
    S = 1 << shift
    m = np.zeros((cam.H, cam.W), np.uint8)
    za = (cam.w2c[:3, :3] @ a.T).T[:, 2] + cam.w2c[2, 3]
    zb = (cam.w2c[:3, :3] @ b.T).T[:, 2] + cam.w2c[2, 3]
    vis = vis & (za > 1e-6) & (zb > 1e-6) & \
        (np.linalg.norm(uvb - uva, axis=1) < max_seg_px)
    idx = np.where(vis)[0]
    A = np.clip(uva[idx], -1e4, 1e4) * S
    B = np.clip(uvb[idx], -1e4, 1e4) * S
    for i in range(len(idx)):
        cv2.line(m, (int(A[i, 0]), int(A[i, 1])), (int(B[i, 0]), int(B[i, 1])),
                 1, 1, cv2.LINE_8, shift)
    return m > 0


def warp_mask(mask, depth, cam_from, cam_to):
    """Un-project the ON pixels of `mask` with `depth` and re-project into cam_to."""
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return np.zeros_like(mask)
    z = depth[ys, xs]
    ok = np.isfinite(z) & (z > 1e-6) & (z < 1e8)
    ys, xs, z = ys[ok], xs[ok], z[ok]
    f = cam_from.f
    cx, cy = cam_from.K[0, 2], cam_from.K[1, 2]
    cam_pts = np.stack([(xs - cx) * z / f, (ys - cy) * z / f, z], 1)
    Rw = cam_from.w2c[:3, :3]
    tw = cam_from.w2c[:3, 3]
    world = (Rw.T @ (cam_pts - tw).T).T
    uv, zz = common.project(world, cam_to)
    u = np.round(uv[:, 0]).astype(np.int64)
    v = np.round(uv[:, 1]).astype(np.int64)
    good = (zz > 0) & (u >= 0) & (u < cam_to.W) & (v >= 0) & (v < cam_to.H)
    out = np.zeros_like(mask)
    out[v[good], u[good]] = True
    return out


def flicker(prev_mask, prev_depth, cam_prev, cur_mask, cam_cur, tol=1):
    """(strict, tolerant, n_flip, n_union) symmetric difference after the warp."""
    w = warp_mask(prev_mask, prev_depth, cam_prev, cam_cur)
    union = w | cur_mask
    if not union.any():
        return 0.0, 0.0, 0, 0
    xor = w ^ cur_mask
    strict = xor.sum() / union.sum()
    k = np.ones((2 * tol + 1, 2 * tol + 1), np.uint8)
    wd = cv2.dilate(w.astype(np.uint8), k) > 0
    cd = cv2.dilate(cur_mask.astype(np.uint8), k) > 0
    tolerant = ((w & ~cd) | (cur_mask & ~wd)).sum() / union.sum()
    return float(strict), float(tolerant), int(xor.sum()), int(union.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--linelets", default=None, help="out/linelets_{scene}{tag}.npz")
    ap.add_argument("--tag", default="", help="which out/linelets_{scene}{tag}.npz to load")
    ap.add_argument("--out_tag", default=None, help="suffix for this run's outputs")
    ap.add_argument("--frames", type=int, default=30)
    ap.add_argument("--view_a", type=int, default=0)
    ap.add_argument("--view_b", type=int, default=1)
    ap.add_argument("--tau_d", type=float, default=0.20)
    ap.add_argument("--tau_n", type=float, default=1.0)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    lp = args.linelets or os.path.join(OUT, f"linelets_{args.scene}{args.tag}.npz")
    otag = args.tag if args.out_tag is None else args.out_tag
    z = np.load(lp)
    keep = z["keep"].astype(bool)
    p, t, l = z["p"][keep], z["t"][keep], z["l"][keep]
    print(f"[temporal] {args.scene}: {keep.sum()} pulled+pruned linelets from "
          f"{os.path.basename(lp)}")

    cams, _ = common.load_cameras(args.scene)
    g = common.load_gaussians(args.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    path = interp_cameras(cams[args.view_a], cams[args.view_b], args.frames)
    print(f"[temporal] orbit: {args.frames} interpolated poses between train views "
          f"{args.view_a} and {args.view_b}")

    prev = None
    rows = []
    traj = []          # projected linelet centres per frame, for A_temp
    t0 = time.time()
    strips = {"obj": [], "img": []}
    for i, cam in enumerate(path):
        gb = render.render_gbuffer(g, keep_g, cam, device=args.device)
        depth = gb["depth"].detach().cpu().numpy()
        uvc, _ = common.project(p, cam)
        vis_c, _, _ = visibility.visible_mask(p, cam, gb["depth"])
        traj.append((uvc.copy(), vis_c.copy()))
        m_obj = raster_linelets(p, t, l, cam, gb["depth"])
        m_img = lines_image.extract_lines(gb, tau_d=args.tau_d, tau_n=args.tau_n)
        del gb
        torch.cuda.empty_cache()
        if prev is not None:
            so, to_, fo, uo = flicker(prev["obj"], prev["depth"], prev["cam"], m_obj, cam)
            si, ti, fi, ui = flicker(prev["img"], prev["depth"], prev["cam"], m_img, cam)
            rows.append({"frame": i, "obj_strict": so, "obj_tol": to_,
                         "img_strict": si, "img_tol": ti,
                         "obj_flip": fo, "img_flip": fi,
                         "obj_on": int(m_obj.sum()), "img_on": int(m_img.sum())})
        if i in (0, args.frames // 2, args.frames - 1):
            strips["obj"].append((255 * ~m_obj).astype(np.uint8))
            strips["img"].append((255 * ~m_img).astype(np.uint8))
        prev = {"obj": m_obj, "img": m_img, "depth": depth, "cam": cam}
    dt = time.time() - t0

    # ---- A_temp: second difference of the PROJECTED linelet positions (spec STEP 3).
    # For a static 3D primitive under smooth camera motion this measures only the
    # curvature of the projection, so it is the direct test of whether a change (e.g.
    # threshold chattering in a gate) has injected any per-frame instability.
    acc = []
    for i in range(len(traj) - 2):
        (u0, v0), (u1, v1), (u2, v2) = traj[i], traj[i + 1], traj[i + 2]
        m = v0 & v1 & v2
        if not m.any():
            continue
        d2 = u2[m] - 2.0 * u1[m] + u0[m]
        acc.append(float(np.linalg.norm(d2, axis=1).mean()))
    a_temp = float(np.mean(acc)) if acc else float("nan")

    ob = np.array([r["obj_strict"] for r in rows])
    ib = np.array([r["img_strict"] for r in rows])
    obt = np.array([r["obj_tol"] for r in rows])
    ibt = np.array([r["img_tol"] for r in rows])
    ofl = np.array([r["obj_flip"] for r in rows])
    ifl = np.array([r["img_flip"] for r in rows])
    on_o = np.mean([r["obj_on"] for r in rows])
    on_i = np.mean([r["img_on"] for r in rows])

    print("\n" + "=" * 88)
    print(f"TEMPORAL COHERENCE — {args.scene}, {len(rows)} frame pairs on a smooth orbit")
    print("=" * 88)
    print(f"{'representation':28s} {'on-px/frame':>12s} {'flicker(strict)':>16s} "
          f"{'flicker(1px tol)':>17s} {'flip-px/frame':>14s}")
    print(f"{'object-space linelets (M1b)':28s} {on_o:12.0f} {ob.mean():16.4f} "
          f"{obt.mean():17.4f} {ofl.mean():14.0f}")
    print(f"{'image-space lines (M1a base)':28s} {on_i:12.0f} {ib.mean():16.4f} "
          f"{ibt.mean():17.4f} {ifl.mean():14.0f}")
    red_s = ib.mean() / max(ob.mean(), 1e-9)
    red_t = ibt.mean() / max(obt.mean(), 1e-9)
    print("-" * 88)
    print(f"flicker reduction: {red_s:.2f}x strict, {red_t:.2f}x at 1px tolerance   "
          f"({dt:.1f}s for {args.frames} frames)")
    print(f"A_temp (mean ||pi_t+2 - 2 pi_t+1 + pi_t|| over visible linelets) = "
          f"{a_temp:.5f} px/frame^2")

    for k in ("obj", "img"):
        if strips[k]:
            cv2.imwrite(os.path.join(OUT, f"m1b_temporal_{args.scene}{otag}_{k}.png"),
                        cv2.hconcat(strips[k]))
    jp = os.path.join(OUT, f"m1b_temporal_{args.scene}{otag}.json")
    json.dump({"scene": args.scene, "frames": args.frames, "rows": rows,
               "obj_strict": float(ob.mean()), "img_strict": float(ib.mean()),
               "obj_tol": float(obt.mean()), "img_tol": float(ibt.mean()),
               "obj_flip_per_frame": float(ofl.mean()),
               "img_flip_per_frame": float(ifl.mean()),
               "obj_on_px": float(on_o), "img_on_px": float(on_i),
               "reduction_strict": float(red_s), "reduction_tol": float(red_t),
               "a_temp_px": a_temp,
               "n_linelets": int(keep.sum()), "runtime_s": dt},
              open(jp, "w"), indent=2)
    print(f"  wrote {jp}")


if __name__ == "__main__":
    main()
