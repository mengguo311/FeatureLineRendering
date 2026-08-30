r"""NG-MEC Stage 1 — epipolar-consensus SELECTIVITY gate over TEED proposals.

*** METHOD PATH. MESH-FREE. *** `grep -n "mesh\|trimesh" src/epipolar_consensus.py` finds
nothing but this banner. It imports only common / render / view_split, none of which touch
the GT mesh.

WHY THIS AND NOT A NORMAL GATE
    TRACK M established that what the M1a aggregate consumes from a learned edge detector is
    SELECTIVITY -- a correctly-registered "there is a contour here" -- and not edge placement
    (+0.2408 vs +0.0220, 11:1), not calibrated confidence, not stroke continuity.  Epipolar
    consensus is the same quantity computed from geometry instead of from a network: an edge
    pixel that is a real 3D feature line reprojects onto edge support in neighbouring views,
    while a single-view hallucination (fabric weave, a specular streak, a view-dependent
    occluding contour) does not.  So this is a second, independent selectivity device, and
    Stage 1 asks only whether it adds precision OVER raw TEED without destroying recall.

WHAT IT DOES, PRECISELY
    For every TEED edge pixel x in view v:
      1. read the 3DGS-rendered depth d(x)  (G-buffer, mesh-free; holes filled from the
         nearest valid pixel so silhouette edges are not silently dropped),
      2. sample the viewing ray at S depths spanning [d/(1+rho), d*(1+rho)] -- i.e. an
         EPIPOLAR SEGMENT in every neighbour view, whose length is set by rho,
      3. project those samples into each of the K nearest TRAIN-split neighbour cameras and
         read that view's TEED edge distance transform,
      4. the neighbour SUPPORTS x if the segment passes within tau px of one of its edges,
      5. keep x iff at least m of the K neighbours support it.

    rho is the one knob that decides what "epipolar" means here:
      rho = 0     -> pure reprojection at the rendered depth (strictest)
      rho = 0.2   -> a +-20% depth band, tolerant of G-buffer depth error
      rho = 7     -> d/8 .. 8d, i.e. essentially the whole epipolar line (the depth-free
                     reading of "epipolar band"; reported because it is the literal one, and
                     it is nearly vacuous -- see the results doc)

    The support COUNT (0..K) is what gets cached, so every m threshold is free.

WHAT IT MAY NOT DO
    It is a filter on TEED proposals: `out ⊆ TEED`.  It can only remove.  Recall can therefore
    only fall, which is exactly why the go/no-go pairs the precision bar with a recall-drop
    ceiling -- a filter that buys precision by culling true creases is localization failure
    dressed up as selectivity.
"""
import os

import cv2
import numpy as np
import torch
from scipy import ndimage

from . import common, render, view_split


def nms_thin(p, blur=1.0):
    """Canonical edge NMS -- identical implementation to final_recipe.nms_thin."""
    ps = cv2.GaussianBlur(p, (0, 0), blur) if blur > 0 else p
    gx = cv2.Sobel(ps, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(ps, cv2.CV_32F, 0, 1, ksize=3)
    n = np.sqrt(gx * gx + gy * gy)
    flat = n < 1e-9
    dx = np.where(flat, 1.0, gx / np.maximum(n, 1e-9)).astype(np.float32)
    dy = np.where(flat, 0.0, gy / np.maximum(n, 1e-9)).astype(np.float32)
    H, W = p.shape
    xs, ys = np.meshgrid(np.arange(W, dtype=np.float32),
                         np.arange(H, dtype=np.float32), indexing="xy")
    keep = np.ones((H, W), bool)
    for s in (1.0, -1.0):
        q = cv2.remap(p, np.clip(xs + s * dx, 0, W - 1),
                      np.clip(ys + s * dy, 0, H - 1), cv2.INTER_LINEAR)
        keep &= p >= q - 1e-6
    return np.where(keep, p, 0.0).astype(np.float32)


def teed_binary(cache, v, thr=0.5, key="native", nms=True):
    z = np.load(os.path.join(cache, f"v{v:03d}.npz"))
    p = z[key].astype(np.float32)
    if nms:
        p = nms_thin(p)
    return p >= thr


def fill_depth(depth):
    """Replace non-finite depth with the nearest finite value (exact EDT nearest-neighbour).

    Silhouette edges sit on the fg/bg boundary and half of them land on background pixels
    with no rendered depth.  Dropping them would make the gate look precise by deleting every
    occluding contour -- the exact failure the recall ceiling exists to catch -- so they are
    given their nearest foreground depth instead."""
    bad = ~np.isfinite(depth)
    if not bad.any():
        return depth.astype(np.float32)
    if bad.all():
        return np.ones_like(depth, np.float32)
    idx = ndimage.distance_transform_edt(bad, return_distances=False, return_indices=True)
    return depth[tuple(idx)].astype(np.float32)


def neighbor_views(cams, v, K, pool):
    """K nearest cameras to v, by camera-centre distance, drawn from `pool` and never v."""
    c = cams[v].center
    cand = [u for u in pool if u != v]
    d = [float(np.linalg.norm(cams[u].center - c)) for u in cand]
    return [cand[i] for i in np.argsort(d)[:K]]


def _mults(rho, n_samples=None):
    if n_samples is None:
        n_samples = 1 if rho <= 0 else (9 if rho <= 0.5 else 64)
    if n_samples == 1:
        return np.array([1.0], np.float32)
    return np.exp(np.linspace(-np.log(1.0 + rho), np.log(1.0 + rho),
                              n_samples)).astype(np.float32)


def support_counts(scene, views, teed_cache, configs, K=4, thr=0.5, key="native",
                   pool=None, device="cuda", verbose=True, nms=True):
    """configs = [(tau, rho), ...].

    `teed_cache` is any PROPOSAL cache in the TEED file layout (key "native").  Passing a
    cache of Canny proposals with nms=False is how the gate gets tested on a detector that
    does NOT already have a selectivity prior -- see NGMEC_S1_RESULTS.md.

    -> {(tau, rho): {v: (E_v bool[H,W], count uint8[H,W])}}

    The G-buffer render and the neighbour edge/DT maps are shared across configs, so adding a
    (tau, rho) pair costs only a handful of grid_sample lookups."""
    cams, _ = common.load_cameras(scene)
    pool = list(view_split.TRAIN) if pool is None else list(pool)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])

    rhos = sorted({r for _, r in configs})
    mult = {r: _mults(r) for r in rhos}
    need = sorted(set(views) | {u for v in views
                                for u in neighbor_views(cams, v, K, pool)})
    if verbose:
        print(f"[epi] {scene}: {len(views)} target views, {len(need)} edge maps needed, "
              f"K={K}, rho={rhos}, neighbour pool = TRAIN ({len(pool)} views)", flush=True)
    E, DT = {}, {}
    for u in need:
        E[u] = teed_binary(teed_cache, u, thr=thr, key=key, nms=nms)
        DT[u] = cv2.distanceTransform((~E[u]).astype(np.uint8), cv2.DIST_L2, 5)

    dev = torch.device(device)
    out = {c: {} for c in configs}
    for n_done, v in enumerate(views):
        cam = cams[v]
        H, W = cam.H, cam.W
        gb = render.render_gbuffer(g, keep, cam)
        depth = fill_depth(gb["depth"].detach().cpu().numpy())
        del gb
        torch.cuda.empty_cache()

        yy, xx = np.nonzero(E[v])
        if len(yy) == 0:
            for c in configs:
                out[c][v] = (E[v], np.zeros((H, W), np.uint8))
            continue
        d0 = depth[yy, xx]
        Kinv = np.linalg.inv(cam.K)
        pix = np.stack([xx, yy, np.ones(len(xx))], 1).astype(np.float64)
        ray_c = (Kinv @ pix.T).T
        ray_c /= ray_c[:, 2:3]
        R, t = cam.w2c[:3, :3], cam.w2c[:3, 3]
        Rt = R.T
        ray_t = torch.tensor((Rt @ ray_c.T).T, dtype=torch.float32, device=dev)
        org_t = torch.tensor((Rt @ (-t))[None], dtype=torch.float32, device=dev)
        d_t = torch.tensor(d0, dtype=torch.float32, device=dev)

        # best[rho] = min over the epipolar segment of the neighbour's edge distance
        cnt = {c: torch.zeros(len(xx), dtype=torch.uint8, device=dev) for c in configs}
        for u in neighbor_views(cams, v, K, pool):
            cu = cams[u]
            w2c = torch.tensor(cu.w2c, dtype=torch.float32, device=dev)
            Kt = torch.tensor(cu.K, dtype=torch.float32, device=dev)
            dt_t = torch.tensor(DT[u], dtype=torch.float32, device=dev)[None, None]
            best = {}
            for r in rhos:
                b = torch.full((len(xx),), 1e9, device=dev)
                for s in torch.tensor(mult[r], device=dev):
                    X = org_t + ray_t * (d_t * s)[:, None]
                    cp = X @ w2c[:3, :3].T + w2c[:3, 3]
                    z = cp[:, 2]
                    uvw = cp @ Kt.T
                    uu = uvw[:, 0] / uvw[:, 2].clamp(min=1e-9)
                    vv = uvw[:, 1] / uvw[:, 2].clamp(min=1e-9)
                    inb = ((z > 1e-6) & (uu >= 0) & (uu <= cu.W - 1)
                           & (vv >= 0) & (vv <= cu.H - 1))
                    grid = torch.stack([(uu / (cu.W - 1) * 2 - 1).clamp(-1, 1),
                                        (vv / (cu.H - 1) * 2 - 1).clamp(-1, 1)],
                                       -1)[None, None]
                    samp = torch.nn.functional.grid_sample(
                        dt_t, grid, mode="bilinear", align_corners=True)[0, 0, 0]
                    b = torch.minimum(b, torch.where(inb, samp,
                                                     torch.full_like(samp, 1e9)))
                best[r] = b
            for (tau, r) in configs:
                cnt[(tau, r)] += (best[r] <= tau).to(torch.uint8)

        for c in configs:
            cmap = np.zeros((H, W), np.uint8)
            cmap[yy, xx] = cnt[c].cpu().numpy()
            out[c][v] = (E[v], cmap)
        if verbose and (n_done % 8 == 0 or n_done == len(views) - 1):
            c0 = configs[0]
            h = np.bincount(out[c0][v][1][yy, xx], minlength=K + 1).tolist()
            print(f"    [epi] {n_done + 1}/{len(views)} v{v}: {len(yy)} TEED px, "
                  f"support hist @tau={c0[0]},rho={c0[1]}: {h}", flush=True)
    return out


def write_cache(counts, out_dir, m):
    """Materialise the arm `count >= m` as a binary edge cache with the TEED file layout."""
    os.makedirs(out_dir, exist_ok=True)
    stats = []
    for v, (Ev, cmap) in counts.items():
        keep = Ev & (cmap >= m)
        np.savez_compressed(os.path.join(out_dir, f"v{v:03d}.npz"),
                            native=keep.astype(np.float16))
        stats.append({"view": int(v), "n_teed": int(Ev.sum()), "n_keep": int(keep.sum()),
                      "frac_kept": float(keep.sum() / max(Ev.sum(), 1))})
    return stats
