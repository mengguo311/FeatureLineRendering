"""Complementary multi-view blind-spot 2D skeleton seeding & foreground-depth ray lifting."""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np
import torch
from scipy.spatial import cKDTree

from .multimodal_data import MultiModalSceneBundle, MultiModalView, ParentFragmentChain
from .stage1_ray_clean import CleanedChainSegment, run_stage1_ray_clean

_NBR8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _trace_2d_skeleton_chains(skel: np.ndarray, min_pixels: int = 7) -> list[np.ndarray]:
    """Trace ordered 8-connected (col=u, row=v) chains from a binary 1-px skeleton image."""
    h, w = skel.shape
    mask = skel.astype(np.uint8)
    if mask.sum() < min_pixels:
        return []

    kern = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.uint8)
    deg = cv2.filter2D(mask, cv2.CV_16U, kern, borderType=cv2.BORDER_CONSTANT) * mask

    visited = np.zeros((h, w), dtype=bool)
    chains: list[np.ndarray] = []

    ys, xs = np.where(mask > 0)
    # Order seeds: degree-1 endpoints first, then degree>=3 junctions, then remaining degree-2 loops
    degs_at = deg[ys, xs]
    order = np.argsort(np.where(degs_at == 1, 0, np.where(degs_at >= 3, 1, 2)))

    for idx in order:
        r0, c0 = int(ys[idx]), int(xs[idx])
        if visited[r0, c0] and deg[r0, c0] == 2:
            continue
        if deg[r0, c0] == 0:
            visited[r0, c0] = True
            continue

        # Try starting a walk into each unvisited neighbor
        for dr, dc in _NBR8:
            nr, nc = r0 + dr, c0 + dc
            if not (0 <= nr < h and 0 <= nc < w) or mask[nr, nc] == 0 or visited[nr, nc]:
                continue

            pts = [(c0, r0), (nc, nr)]
            visited[r0, c0] = True
            visited[nr, nr if False else nc] = True

            cr, cc = nr, nc
            while deg[cr, cc] == 2:
                nxt = None
                for dr2, dc2 in _NBR8:
                    rr, cc2 = cr + dr2, cc + dc2
                    if 0 <= rr < h and 0 <= cc2 < w and mask[rr, cc2] > 0 and not visited[rr, cc2]:
                        nxt = (rr, cc2)
                        break
                if nxt is None:
                    # Check if it closes onto a junction neighbor
                    for dr2, dc2 in _NBR8:
                        rr, cc2 = cr + dr2, cc + dc2
                        if (
                            0 <= rr < h
                            and 0 <= cc2 < w
                            and mask[rr, cc2] > 0
                            and deg[rr, cc2] >= 3
                            and (cc2, rr) != pts[-2]
                        ):
                            pts.append((cc2, rr))
                            break
                    break
                cr, cc = nxt
                visited[cr, cc] = True
                pts.append((cc, cr))

            if len(pts) >= min_pixels:
                chains.append(np.array(pts, dtype=np.int32))
            if deg[r0, c0] <= 2:
                break

    return chains


def _project_existing_coverage_mask(
    pts_3d: np.ndarray, view: MultiModalView, pixel_scale: float, dilate_radius_px: int = 2
) -> np.ndarray:
    """Project existing cleaned 3D curve points onto `view` to identify already-reconstructed 2D regions."""
    cov_map = np.zeros((view.height, view.width), dtype=np.uint8)
    if len(pts_3d) == 0:
        return cov_map > 0

    R = view.w2c[:3, :3]
    t = view.w2c[:3, 3]
    Xc = pts_3d @ R.T + t[None, :]
    z = Xc[:, 2]
    ok = z > 0.2
    if not np.any(ok):
        return cov_map > 0

    Xc = Xc[ok]
    z = z[ok]
    u = np.round(view.fx * (Xc[:, 0] / z) + view.cx).astype(np.int32)
    v = np.round(view.fy * (Xc[:, 1] / z) + view.cy).astype(np.int32)
    in_b = (u >= 0) & (u < view.width) & (v >= 0) & (v < view.height)
    u, v, z = u[in_b], v[in_b], z[in_b]

    if view.depth is not None and view.depth_jump is not None:
        sd = view.depth[v, u]
        al = view.alpha[v, u]
        dj = view.depth_jump[v, u]
        occ = (al > 0.95) & (sd > 0.2) & (dj < 0.004) & (z > sd + 5.0 * pixel_scale)
        u, v = u[~occ], v[~occ]

    cov_map[v, u] = 1
    ksize = 2 * dilate_radius_px + 1
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
    dilated = cv2.dilate(cov_map, kern)
    return dilated > 0


def extract_complementary_multiview_seeds(
    bundle: MultiModalSceneBundle,
    base_clean_segments: list[CleanedChainSegment],
    device: torch.device,
    roi_bounds: tuple[np.ndarray, np.ndarray] | None = None,
    min_uncovered_ratio: float = 0.55,
    min_mv_corroboration: int = 4,
) -> tuple[list[CleanedChainSegment], dict[str, Any]]:
    """Extract uncovered 2D edge chains from extra full-sphere train views, lift via foreground depth, and ray-clean."""
    extra_views = [v for v in bundle.train_views if not v.is_original_c2l_build and v.depth is not None and v.skeleton is not None]
    if not extra_views:
        return [], {"extra_seed_views": 0, "new_clean_segments": 0}

    p_med = bundle.median_pixel_scale
    base_pts = (
        np.concatenate([s.points_3d for s in base_clean_segments], axis=0)
        if base_clean_segments
        else np.zeros((0, 3), dtype=np.float64)
    )
    base_tree = cKDTree(base_pts) if len(base_pts) > 0 else None

    seed_parents: list[ParentFragmentChain] = []
    next_pid = 100000
    raw_2d_chains_considered = 0
    uncovered_2d_chains_lifted = 0

    for vw in extra_views:
        assert vw.skeleton is not None and vw.front_depth is not None and vw.depth is not None
        alpha_dil = cv2.dilate((vw.alpha > 0.25).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        cand_skel = vw.skeleton & (vw.edge_strength > 0.24) & alpha_dil
        chains_2d = _trace_2d_skeleton_chains(cand_skel, min_pixels=8)
        raw_2d_chains_considered += len(chains_2d)

        R_c2w = vw.c2w[:3, :3]
        fx, fy, cx, cy = vw.fx, vw.fy, vw.cx, vw.cy
        fg_mask = (vw.alpha > 0.55) & (vw.front_depth > 0.2)

        for uv_full in chains_2d:
            # Subsample every 2 pixels keeping endpoints
            idx_sub = list(range(0, len(uv_full) - 1, 2)) + [len(uv_full) - 1]
            uv_sub = uv_full[idx_sub].astype(np.float64)

            z_init = np.zeros(len(uv_sub), dtype=np.float64)
            states = np.ones(len(uv_sub), dtype=np.uint8)
            valid_nodes = np.ones(len(uv_sub), dtype=bool)

            for k_i, (u_val, v_val) in enumerate(uv_sub):
                ci, ri = int(round(u_val)), int(round(v_val))
                r_lo, r_hi = max(0, ri - 2), min(vw.height, ri + 3)
                c_lo, c_hi = max(0, ci - 2), min(vw.width, ci + 3)
                patch_fg = fg_mask[r_lo:r_hi, c_lo:c_hi]
                if int(patch_fg.sum()) < 2:
                    valid_nodes[k_i] = False
                    continue
                patch_z = vw.front_depth[r_lo:r_hi, c_lo:c_hi][patch_fg]
                z0 = float(np.percentile(patch_z, 25.0))
                z_init[k_i] = z0
                z_span = float(patch_z.max() - patch_z.min())
                p_loc = z0 / math.sqrt(fx * fy)
                if vw.alpha[ri, ci] < 0.80 or z_span > 4.0 * p_loc:
                    states[k_i] = 2  # Flag rim/step node for multi-view Viterbi ray refinement!

            if int(valid_nodes.sum()) < 4:
                continue

            uv_sub = uv_sub[valid_nodes]
            z_init = z_init[valid_nodes]
            states = states[valid_nodes]

            # Exact world ray per unit camera-z: R_c2w @ [(u - cx)/fx, (v - cy)/fy, 1]
            cam_dirs = np.stack(
                [(uv_sub[:, 0] - cx) / fx, (uv_sub[:, 1] - cy) / fy, np.ones(len(uv_sub), dtype=np.float64)],
                axis=1,
            )
            rays_w = cam_dirs @ R_c2w.T
            pts_3d = vw.cam_center[None, :] + z_init[:, None] * rays_w

            # True 3D blind-spot check (immune to 2D X-ray background occlusion collisions!)
            if base_tree is not None:
                d3_init, _ = base_tree.query(pts_3d, k=1)
                if float(np.mean(d3_init > 3.0 * p_med)) < min_uncovered_ratio:
                    continue

            node_px = z_init / float(np.sqrt(fx * fy))

            seed_parents.append(
                ParentFragmentChain(
                    parent_id=next_pid,
                    source_view=vw.view_name,
                    cam_center=vw.cam_center.copy(),
                    uv=uv_sub,
                    rays=rays_w,
                    fitted_z=z_init,
                    raw_z=z_init.copy(),
                    second_z=np.full(len(uv_sub), np.nan, dtype=np.float64),
                    state=states,
                    node_pixel=node_px,
                    points_3d=pts_3d,
                    is_complementary_seed=True,
                )
            )
            next_pid += 1
            uncovered_2d_chains_lifted += 1

    if not seed_parents:
        return [], {
            "extra_seed_views": len(extra_views),
            "raw_2d_chains_considered": raw_2d_chains_considered,
            "uncovered_2d_chains_lifted": 0,
            "new_clean_segments": 0,
        }

    # Run Stage 1 Multi-View Visual-Hull & Viterbi Ray Depth Refinement on the newly lifted seeds
    seed_bundle = MultiModalSceneBundle(
        scene_name=bundle.scene_name,
        train_views=bundle.train_views,
        eval_views=bundle.eval_views,
        parents=seed_parents,
        canonical_gaussians_path=bundle.canonical_gaussians_path,
        median_pixel_scale=bundle.median_pixel_scale,
    )
    cleaned_seeds, seed_s1_stats = run_stage1_ray_clean(
        seed_bundle, device=device, roi_bounds=roi_bounds, num_ray_samples=80
    )

    # Filter complementary seeds: require post-Viterbi 3D novelty (truly uncovered in 3D) AND multi-view corroboration
    strong_seeds: list[CleanedChainSegment] = []
    base_next_id = max((s.chain_id for s in base_clean_segments), default=-1) + 1
    eff_min_mv = max(min_mv_corroboration, 5 if len(bundle.train_views) >= 30 else 4)
    for seg in cleaned_seeds:
        if float(np.median(seg.mv_support_views)) < eff_min_mv:
            continue
        if base_tree is not None:
            d3_post, _ = base_tree.query(seg.points_3d, k=1)
            if float(np.mean(d3_post > 2.6 * p_med)) < 0.50:
                continue
        seg.chain_id = base_next_id
        base_next_id += 1
        strong_seeds.append(seg)

    stats = {
        "extra_seed_views": len(extra_views),
        "raw_2d_chains_considered": raw_2d_chains_considered,
        "uncovered_2d_chains_lifted": uncovered_2d_chains_lifted,
        "stage1_ray_refined_seeds": len(cleaned_seeds),
        "accepted_strong_complementary_segments": len(strong_seeds),
        "added_complementary_3d_nodes": int(sum(len(s.points_3d) for s in strong_seeds)),
        "seed_stage1_stats": seed_s1_stats,
    }
    return strong_seeds, stats
