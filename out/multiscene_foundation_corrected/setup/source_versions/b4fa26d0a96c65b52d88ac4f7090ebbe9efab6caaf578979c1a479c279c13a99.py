r"""tier1/src/tri_edges.py — METHOD PATH. MESH-FREE.
Multi-view epipolar triangulation of frozen zero-shot DexiNed edges.

`grep -n "mesh\|trimesh" src/tri_edges.py` finds nothing but this banner. It imports only
common / render / epipolar_consensus, none of which touch the GT mesh.

WHY THIS EXISTS
    Phase 0 NO-GO'd single-view depth lifting as a coverage-ceiling breaker, but diagnosed the
    two scenes differently. On chair the 2D signal IS there (DexiNed reaches 0.636 of the
    gaussian miss-set in 2D) while the single-view depth lift places it at only 0.486 in 3D.
    That residual is a LOCALIZATION failure, and localization is what multi-view triangulation
    is for. This module replaces "read the 3DGS depth at the edge pixel" with "find the depth
    along the viewing ray at which the point reprojects onto DexiNed edges in the neighbouring
    views too".

THE FORMULATION — epipolar matching without explicit correspondences
    A candidate depth z on the ray through reference edge pixel u traces out exactly the
    epipolar line of u in every neighbour view. So sweeping z IS the epipolar search, and no
    correspondence has to be committed to in advance:

        cost(z) = mean_n  min( DT_n( project_n( C_r + z * dir_r(u) ) ), CAP )

    DT_n = distance transform of neighbour n's NMS-thinned DexiNed edge mask. The truncation
    at CAP is what makes it robust: a neighbour in which the point is occluded, out of frame,
    or simply un-detected contributes a constant and therefore cannot drag the arg-min.
    z* = argmin cost, found coarse-to-fine in LOG depth (three levels, final resolution ~1e-4
    world units, i.e. ~50x finer than the 0.00515 scoring tolerance).

    SUPPORT = the number of neighbours whose DT at z* is <= tau. "2-view triangulation" is
    support >= 1 (reference + one neighbour); "K>=3-view bundle" is support >= 2. Support is
    CACHED PER POINT, so every threshold is free.

WHAT THE 3DGS DEPTH IS AND IS NOT USED FOR
    Used: (a) the INITIAL z, i.e. the centre of the search bracket, and (b) the occlusion /
    free-space prior in `surface_cull`. NOT used: the final position. The bracket is +-rho
    (default 20%) around the init, which at chair's ~3.8 depth is +-0.76 world units against a
    0.00515 tolerance -- ~150x the tolerance, so the optimum is free to move far away from the
    initialisation. `frac_moved_gt_tol` in the returned stats reports how often it does.
"""
import os

import cv2
import numpy as np
import torch

from . import common, render
from .epipolar_consensus import nms_thin, fill_depth


def edge_dt(cache_dir, v, thr=0.5, key="native", nms=True):
    """DexiNed prob map -> (binary NMS-thinned edge mask, its L2 distance transform)."""
    z = np.load(os.path.join(cache_dir, f"v{v:03d}.npz"))
    p = z[key].astype(np.float32)
    if nms:
        p = nms_thin(p)
    m = p >= thr
    if not m.any():
        return m, np.full(m.shape, 1e6, np.float32)
    return m, cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)


def neighbor_views(cams, v, K, pool):
    """K nearest cameras to v by camera-centre distance, drawn from `pool`, never v."""
    c = cams[v].center
    cand = [u for u in pool if u != v]
    d = [float(np.linalg.norm(cams[u].center - c)) for u in cand]
    return [cand[i] for i in np.argsort(d)[:K]]


def _sample(dt_t, u, v_, H, W):
    """Bilinear sample of a [H,W] map at PHOTO-INDEX continuous coords (u,v). Out of frame ->
    a large value (so it reads as 'no edge here', never as a spurious match)."""
    gx = (2.0 * u + 1.0) / W - 1.0
    gy = (2.0 * v_ + 1.0) / H - 1.0
    grid = torch.stack([gx, gy], -1)[None, ...]              # [1,N,S,2]
    out = torch.nn.functional.grid_sample(
        dt_t[None, None], grid, mode="bilinear", padding_mode="border",
        align_corners=False)[0, 0]
    oob = (u < 0) | (u > W - 1) | (v_ < 0) | (v_ > H - 1)
    return torch.where(oob, torch.full_like(out, 1e6), out)


@torch.no_grad()
def triangulate_view(cams, ref, nbrs, dts, d_init, uv_ref, halfpix=0.5, rho=0.2,
                     levels=(65, 33, 33), tau=1.5, cap=8.0, device="cuda"):
    """Triangulate every reference edge pixel by coarse-to-fine search along its viewing ray.

    uv_ref[N,2] PHOTO-INDEX coords of the reference edge pixels; d_init[N] the initial
    camera-space z; dts = {view: torch [H,W] edge distance transform}.
    Returns dict with P[N,3] world, z[N], support[N], resid[N], cost[N], moved[N].
    """
    cam = cams[ref]
    H, W = cam.H, cam.W
    dev = torch.device(device)
    f, cx, cy = cam.f, cam.K[0, 2], cam.K[1, 2]

    u_t = torch.tensor(uv_ref[:, 0] + halfpix, dtype=torch.float64, device=dev)
    v_t = torch.tensor(uv_ref[:, 1] + halfpix, dtype=torch.float64, device=dev)
    # ray, parameterised by CAMERA-SPACE Z so that z is directly the depth
    dcam = torch.stack([(u_t - cx) / f, (v_t - cy) / f, torch.ones_like(u_t)], 1)  # [N,3]
    Rr = torch.tensor(cam.w2c[:3, :3], dtype=torch.float64, device=dev)
    tr = torch.tensor(cam.w2c[:3, 3], dtype=torch.float64, device=dev)
    dir_w = dcam @ Rr                                        # R^T dcam  -> [N,3]
    C = torch.tensor(cam.center, dtype=torch.float64, device=dev)

    Rn, tn = {}, {}
    for n in nbrs:
        Rn[n] = torch.tensor(cams[n].w2c[:3, :3], dtype=torch.float64, device=dev)
        tn[n] = torch.tensor(cams[n].w2c[:3, 3], dtype=torch.float64, device=dev)

    z0 = torch.tensor(d_init, dtype=torch.float64, device=dev)
    zc = z0.clone()
    lhalf = float(np.log1p(rho))
    for S in levels:
        mult = torch.exp(torch.linspace(-lhalf, lhalf, S, dtype=torch.float64, device=dev))
        zs = zc[:, None] * mult[None, :]                     # [N,S]
        X = C[None, None] + zs[..., None] * dir_w[:, None, :]  # [N,S,3]
        cost = torch.zeros_like(zs)
        for n in nbrs:
            Xc = X @ Rn[n].T + tn[n]
            zn = Xc[..., 2]
            un = f * Xc[..., 0] / zn.clamp(min=1e-6) + cx - halfpix   # -> photo index
            vn = f * Xc[..., 1] / zn.clamp(min=1e-6) + cy - halfpix
            d = _sample(dts[n], un.float(), vn.float(), H, W).double()
            d = torch.where(zn > 1e-6, d, torch.full_like(d, 1e6))
            cost = cost + torch.clamp(d, max=cap)
        best = cost.argmin(1)
        ar = torch.arange(len(zc), device=dev)
        zc = zs[ar, best]
        lhalf = 2.0 * lhalf / (S - 1)                        # shrink to one grid step

    # final support / residual at z*
    Xf = C[None] + zc[:, None] * dir_w
    sup = torch.zeros(len(zc), dtype=torch.int32, device=dev)
    rsum = torch.zeros(len(zc), dtype=torch.float64, device=dev)
    cfin = torch.zeros(len(zc), dtype=torch.float64, device=dev)
    for n in nbrs:
        Xc = Xf @ Rn[n].T + tn[n]
        zn = Xc[:, 2]
        un = f * Xc[:, 0] / zn.clamp(min=1e-6) + cx - halfpix
        vn = f * Xc[:, 1] / zn.clamp(min=1e-6) + cy - halfpix
        d = _sample(dts[n], un.float()[None], vn.float()[None], H, W)[0].double()
        d = torch.where(zn > 1e-6, d, torch.full_like(d, 1e6))
        ok = d <= tau
        sup += ok.int()
        rsum += torch.where(ok, d, torch.zeros_like(d))
        cfin += torch.clamp(d, max=cap)
    resid = rsum / sup.clamp(min=1).double()
    return {
        "P": Xf.cpu().numpy(), "z": zc.cpu().numpy(),
        "support": sup.cpu().numpy(), "resid": resid.cpu().numpy(),
        "cost": (cfin / max(len(nbrs), 1)).cpu().numpy(),
        "moved": (zc - z0).abs().cpu().numpy(),
        "z_init": z0.cpu().numpy(),
    }


@torch.no_grad()
def surface_cull(P, cams, views, depth_mean, depth_med, rel_eps=0.02, min_frac=0.5,
                 device="cuda"):
    """FREE-SPACE / OCCLUSION cull using ONLY the 3DGS depth (mesh-free, prior not position).

    In every view where the point is in front of the camera and in frame, it must either be
    OCCLUDED (something nearer -> that view says nothing) or lie ON the surface
    (|z - depth_median| <= rel_eps * z). A point floating in free space in front of the
    surface, or buried behind it, is visible-and-off-surface and gets voted down.
    Kept iff on-surface in >= min_frac of the views that can see it.
    """
    dev = torch.device(device)
    Pt = torch.tensor(P, dtype=torch.float64, device=dev)
    n_on = torch.zeros(len(P), dtype=torch.float64, device=dev)
    n_vis = torch.zeros(len(P), dtype=torch.float64, device=dev)
    for v in views:
        cam = cams[v]
        H, W = cam.H, cam.W
        R = torch.tensor(cam.w2c[:3, :3], dtype=torch.float64, device=dev)
        t = torch.tensor(cam.w2c[:3, 3], dtype=torch.float64, device=dev)
        Xc = Pt @ R.T + t
        z = Xc[:, 2]
        u = cam.f * Xc[:, 0] / z.clamp(min=1e-6) + cam.K[0, 2]
        v_ = cam.f * Xc[:, 1] / z.clamp(min=1e-6) + cam.K[1, 2]
        ui = u.round().long().clamp(0, W - 1)
        vi = v_.round().long().clamp(0, H - 1)
        inb = (z > 1e-6) & (u >= 0) & (u <= W - 1) & (v_ >= 0) & (v_ <= H - 1)
        dm = depth_mean[v][vi, ui].double()
        dd = depth_med[v][vi, ui].double()
        has = torch.isfinite(dm) & torch.isfinite(dd)
        occluded = z > dm * (1.0 + rel_eps)          # something nearer -> abstains
        on_surf = (z - dd).abs() <= rel_eps * z
        counts = inb & has & ~occluded
        n_vis += counts.double()
        n_on += (counts & on_surf).double()
    keep = (n_vis > 0) & (n_on >= min_frac * n_vis)
    return keep.cpu().numpy(), n_vis.cpu().numpy(), n_on.cpu().numpy()


@torch.no_grad()
def build(scene, ref_views, nbr_pool, cache_dir, thr=0.5, key="native", K=6, rho=0.2,
          tau=1.5, cap=8.0, halfpix=0.5, levels=(65, 33, 33), rel_eps=0.02,
          min_frac=0.5, device="cuda", verbose=True):
    """Full generator. Returns (out dict of arrays, stats dict). MESH-FREE end to end."""
    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])

    need = sorted(set(ref_views) | {n for r in ref_views
                                    for n in neighbor_views(cams, r, K, nbr_pool)})
    if verbose:
        print(f"[tri] {scene}: {len(ref_views)} ref views, K={K}, "
              f"{len(need)} views need a G-buffer", flush=True)

    dts, dmean, dmed = {}, {}, {}
    for v in need:
        _, dt = edge_dt(cache_dir, v, thr, key)
        dts[v] = torch.tensor(dt, dtype=torch.float32, device=device)
        gb = render.render_gbuffer(g, keep_g, cams[v], with_median_depth=True)
        dmean[v] = gb["depth"].float()
        dmed[v] = gb["depth_median"].float()
        del gb
        torch.cuda.empty_cache()

    Ps, sups, resids, costs, moveds, tags = [], [], [], [], [], []
    for r in ref_views:
        nbrs = neighbor_views(cams, r, K, nbr_pool)
        m, _ = edge_dt(cache_dir, r, thr, key)
        vv, uu = np.nonzero(m)
        uv = np.stack([uu, vv], 1).astype(np.float64)
        dm_np = dmed[r].cpu().numpy().astype(np.float64)
        dm_np[~np.isfinite(dm_np)] = np.nan
        d0 = fill_depth(dm_np)[vv, uu]                       # init only
        ok = np.isfinite(d0) & (d0 > 1e-6)
        uv, d0 = uv[ok], d0[ok]
        if not len(uv):
            continue
        res = triangulate_view(cams, r, nbrs, dts, d0, uv, halfpix=halfpix, rho=rho,
                               levels=levels, tau=tau, cap=cap, device=device)
        Ps.append(res["P"]); sups.append(res["support"]); resids.append(res["resid"])
        costs.append(res["cost"]); moveds.append(res["moved"])
        tags.append(np.full(len(uv), r))
        if verbose:
            print(f"  ref v{r:3d}: {len(uv):6d} edge px  sup>=1 {int((res['support']>=1).sum()):6d}"
                  f"  sup>=2 {int((res['support']>=2).sum()):6d}"
                  f"  med|dz| {np.median(res['moved']):.4f}", flush=True)
        torch.cuda.empty_cache()

    out = {"P": np.concatenate(Ps), "support": np.concatenate(sups),
           "resid": np.concatenate(resids), "cost": np.concatenate(costs),
           "moved": np.concatenate(moveds), "ref": np.concatenate(tags)}
    keep, n_vis, n_on = surface_cull(out["P"], cams, need, dmean, dmed,
                                     rel_eps=rel_eps, min_frac=min_frac, device=device)
    out["surface_keep"] = keep
    out["n_vis"], out["n_on"] = n_vis, n_on
    stats = {"n_raw": int(len(out["P"])), "K": K, "rho": rho, "tau": tau, "cap": cap,
             "halfpix": halfpix, "levels": list(levels), "rel_eps": rel_eps,
             "min_frac": min_frac, "n_ref_views": len(ref_views),
             "n_gbuf_views": len(need),
             "frac_sup_ge1": float((out["support"] >= 1).mean()),
             "frac_sup_ge2": float((out["support"] >= 2).mean()),
             "frac_sup_ge3": float((out["support"] >= 3).mean()),
             "frac_surface_keep": float(keep.mean()),
             "median_moved": float(np.median(out["moved"])),
             "frac_moved_gt_tol": float((out["moved"] > 0.00515).mean())}
    for v in need:
        del dts[v], dmean[v], dmed[v]
    torch.cuda.empty_cache()
    return out, stats
