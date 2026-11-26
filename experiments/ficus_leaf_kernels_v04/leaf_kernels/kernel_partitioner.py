"""Stage 3 & 4: Occlusion-gated multi-view 2D->3D consensus + plane-bounded Kruskal 3DGS leaf kernel partitioning."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from scipy.spatial import cKDTree

from .data_io import CalibratedLeafView, GaussianCloud3D, PriorVectorGeometry
from .multiview_leaf_cells import (
    LABEL_POT_OR_SOIL,
    LABEL_UNASSIGNED_FOLIAGE,
    LABEL_WOOD_STEM,
    EnclosedLeaf2DViewMap,
    detect_2d_enclosed_leaves_for_view,
    preclassify_3dgs_semantic_domains,
)


@dataclass
class LeafInstance3D:
    """Single partitioned 3D leaf instance with assigned 3DGS kernel indices & closed 3D cambered boundary loop."""

    leaf_id: int
    kernel_indices: np.ndarray     # (K_l,) int32 indices into original 284,835-kernel PLY!
    active_kernel_count: int
    centroid: np.ndarray           # (3,) float64
    axis_length: np.ndarray        # (3,) float64 major leaf-blade axis (petiole -> tip)
    axis_width: np.ndarray         # (3,) float64 transverse blade axis
    normal: np.ndarray             # (3,) float64 blade surface normal
    length_world: float
    width_world: float
    thickness_world: float
    area_world: float
    mean_vis_views: float          # mean number of unoccluded front-surface views across kernels
    closure_confidence: float      # multi-view enclosed-cell support score in [0, 1]
    visibility_tier: str           # "OUTER_ENCLOSED", "MID_PARTIAL_OCCLUDED", or "DEEP_OCCLUDED"
    boundary_loop_3d: np.ndarray   # (24, 3) closed 3D cambered leaf contour vertices
    mean_rgb: np.ndarray           # (3,) natural mean leaf RGB


def _orient_foliage_normals_consistent(normals: np.ndarray) -> np.ndarray:
    """Canonicalize sign of undirected surfel normals for fast pairwise dot-products (still using |n_i · n_j|)."""
    out = normals.astype(np.float64).copy()
    nrm = np.linalg.norm(out, axis=1, keepdims=True)
    out = np.where(nrm > 1e-9, out / np.maximum(nrm, 1e-9), np.array([0.0, 0.0, 1.0]))
    return out


@torch.no_grad()
def _project_kernels_to_enclosed_cells_gpu(
    pts_active: np.ndarray,
    nrm_active: np.ndarray,
    views: list[CalibratedLeafView],
    cell_maps: list[EnclosedLeaf2DViewMap],
    p_med: float,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Project M active foliage Gaussians to V views on GPU with strict front-surface occlusion depth gating.

    Returns:
      cell_obs: (M, V) int32 — >0 cell_id if front-surface unoccluded & inside valid enclosed 2D leaf cell,
                                -1 if front-surface unoccluded on foliage but outside closed cell,
                                 0 if occluded behind foreground leaf or out of frustum!
      vis_views_cnt: (M,) int32 — number of views where kernel is unoccluded on front surface.
      enclosed_views_cnt: (M,) int32 — number of views where kernel lands unoccluded inside a valid closed 2D leaf cell.
    """
    m = len(pts_active)
    v_cnt = len(views)
    cell_obs = np.zeros((m, v_cnt), dtype=np.int32)
    vis_views_cnt = np.zeros(m, dtype=np.int32)
    enclosed_views_cnt = np.zeros(m, dtype=np.int32)

    X_t = torch.tensor(pts_active, dtype=torch.float32, device=device)
    N_t = torch.tensor(nrm_active, dtype=torch.float32, device=device)

    depth_gate_tol = 2.8 * p_med  # ~9.7 mm strict front-leaf surface gate (prevents X-ray bleed onto back leaves!)

    for v_i, (vw, cmap) in enumerate(zip(views, cell_maps)):
        R_t = torch.tensor(vw.w2c[:3, :3], dtype=torch.float32, device=device)
        t_t = torch.tensor(vw.w2c[:3, 3], dtype=torch.float32, device=device)
        cam_t = torch.tensor(vw.cam_center, dtype=torch.float32, device=device)

        Xc = X_t @ R_t.T + t_t[None, :]
        z = Xc[:, 2]
        u = torch.round(float(vw.fx) * (Xc[:, 0] / z.clamp(min=1e-3)) + float(vw.cx)).long()
        v_px = torch.round(float(vw.fy) * (Xc[:, 1] / z.clamp(min=1e-3)) + float(vw.cy)).long()

        in_b = (z > 0.2) & (u >= 0) & (u < vw.width) & (v_px >= 0) & (v_px < vw.height)
        idx_in = torch.where(in_b)[0]
        if len(idx_in) == 0:
            continue

        fd_t = torch.tensor(vw.front_depth, dtype=torch.float32, device=device)
        al_t = torch.tensor(vw.alpha, dtype=torch.float32, device=device)
        cid_t = torch.tensor(cmap.cell_id_map, dtype=torch.int32, device=device)

        u_in = u[idx_in]
        v_in = v_px[idx_in]
        z_in = z[idx_in]

        v_dir = torch.nn.functional.normalize(cam_t[None, :] - X_t[idx_in], dim=-1, eps=1e-8)
        # Two-sided thin leaf blade: check |n_i · view_dir| >= 0.14 so edge-on grazing surfels don't cross-contaminate
        not_grazing = torch.abs((N_t[idx_in] * v_dir).sum(dim=-1)) >= 0.14

        front_vis = (
            (al_t[v_in, u_in] > 0.45)
            & (fd_t[v_in, u_in] > 0.2)
            & (torch.abs(z_in - fd_t[v_in, u_in]) <= depth_gate_tol)
            & not_grazing
        )

        vis_idx = idx_in[front_vis]
        if len(vis_idx) == 0:
            continue

        c_vals = cid_t[v_px[vis_idx], u[vis_idx]].cpu().numpy()
        vis_np = vis_idx.cpu().numpy()

        vis_views_cnt[vis_np] += 1
        has_cell = c_vals > 0
        enclosed_views_cnt[vis_np[has_cell]] += 1
        cell_obs[vis_np, v_i] = np.where(has_cell, c_vals, -1)

    return cell_obs, vis_views_cnt, enclosed_views_cnt


def _build_closed_leaf_contour_3d(
    pts_leaf: np.ndarray,
    scales_leaf: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, float, float, float, np.ndarray]:
    """Fit local 3D PCA blade frame + quadratic camber + smooth 24-vertex closed 3D leaf contour."""
    centroid = pts_leaf.mean(axis=0)
    centered = pts_leaf - centroid[None, :]
    cov = (centered.T @ centered) / max(len(pts_leaf), 1)
    eigvals, eigvecs = np.linalg.eigh(cov)
    # Ascending order from eigh: 0=normal (thinnest), 1=width, 2=length!
    e_norm = eigvecs[:, 0]
    e_wid = eigvecs[:, 1]
    e_len = eigvecs[:, 2]
    if e_norm[2] < 0:
        e_norm = -e_norm
    # Ensure right-handed frame: e_len x e_wid = e_norm
    if float(np.dot(np.cross(e_len, e_wid), e_norm)) < 0.0:
        e_wid = -e_wid

    u_coord = centered @ e_len
    v_coord = centered @ e_wid
    w_coord = centered @ e_norm

    # Account for Gaussian kernel in-plane footprint radius (~1.2 * max_scale)
    pad = np.median(scales_leaf.max(axis=1)) * 1.15 if len(scales_leaf) > 0 else 0.004
    len_span = float(np.percentile(u_coord, 97.0) - np.percentile(u_coord, 3.0)) + 2.0 * pad
    wid_span = float(np.percentile(v_coord, 97.0) - np.percentile(v_coord, 3.0)) + 2.0 * pad
    thick_span = float(np.percentile(w_coord, 95.0) - np.percentile(w_coord, 5.0))

    # Fit gentle quadratic leaf camber w(u, v) = c0 + c1*u + c2*u^2 + c3*v^2
    if len(pts_leaf) >= 8:
        A_cam = np.column_stack([np.ones(len(u_coord)), u_coord, u_coord ** 2, v_coord ** 2])
        cam_coef = np.linalg.lstsq(A_cam.T @ A_cam + 1e-2 * np.eye(4), A_cam.T @ w_coord, rcond=None)[0]
    else:
        cam_coef = np.zeros(4, dtype=np.float64)

    # Polar radial envelope in normalized (u / a, v / b) space to preserve pointed lanceolate leaf tips!
    a_half = max(0.5 * len_span, 0.005)
    b_half = max(0.5 * wid_span, 0.003)
    un = u_coord / a_half
    vn = v_coord / b_half
    rn = np.hypot(un, vn)
    ang = np.arctan2(vn, un)

    n_verts = 24
    th_bins = np.linspace(-math.pi, math.pi, n_verts, endpoint=False)
    r_env = np.ones(n_verts, dtype=np.float64) * 0.92
    for b_i, th0 in enumerate(th_bins):
        d_ang = np.abs((ang - th0 + math.pi) % (2.0 * math.pi) - math.pi)
        in_sec = d_ang <= (math.pi / 8.0)
        if int(in_sec.sum()) >= 3:
            r_env[b_i] = float(np.clip(np.percentile(rn[in_sec], 94.0) + pad / max(a_half, 1e-4), 0.55, 1.18))

    # Circular 3-tap smoothing on polar envelope
    r_pad = np.concatenate([[r_env[-1]], r_env, [r_env[0]]])
    r_smooth = 0.22 * r_pad[:-2] + 0.56 * r_pad[1:-1] + 0.22 * r_pad[2:]

    u_loop = r_smooth * a_half * np.cos(th_bins)
    v_loop = r_smooth * b_half * np.sin(th_bins)
    w_loop = cam_coef[0] + cam_coef[1] * u_loop + cam_coef[2] * (u_loop ** 2) + cam_coef[3] * (v_loop ** 2)
    loop_3d = centroid[None, :] + u_loop[:, None] * e_len[None, :] + v_loop[:, None] * e_wid[None, :] + w_loop[:, None] * e_norm[None, :]

    # Polygon area in 2D tangent plane (shoelace formula)
    u_next = np.roll(u_loop, -1)
    v_next = np.roll(v_loop, -1)
    area_2d = 0.5 * float(np.abs(np.sum(u_loop * v_next - u_next * v_loop)))

    return centroid, e_len, e_wid, e_norm, len_span, wid_span, thick_span, area_2d, loop_3d


def run_ficus_leaf_kernel_partitioning(
    cloud: GaussianCloud3D,
    train_views: list[CalibratedLeafView],
    priors: PriorVectorGeometry,
    device: torch.device,
) -> tuple[np.ndarray, list[LeafInstance3D], list[EnclosedLeaf2DViewMap], dict[str, Any]]:
    """End-to-end 3DGS leaf region delineation & Gaussian kernel partitioning."""
    p_med = priors.median_pixel_scale

    # Stage 1: Pre-separate POT (-1), WOOD_STEM (-2), and FOLIAGE (-3)
    kernel_labels, sem_stats = preclassify_3dgs_semantic_domains(cloud, priors)

    # Stage 2: Detect 2D enclosed leaf cells across all 32 training views
    cell_maps = [detect_2d_enclosed_leaves_for_view(vw, priors) for vw in train_views]
    total_2d_cells = int(sum(cm.num_valid_cells for cm in cell_maps))

    # Stage 3: Select active foliage kernels (opacity >= 0.025) and project with strict front-depth occlusion gate
    foliage_all_idx = np.where(kernel_labels == LABEL_UNASSIGNED_FOLIAGE)[0]
    active_mask = cloud.opacities[foliage_all_idx] >= 0.025
    active_idx = foliage_all_idx[active_mask]
    halo_idx = foliage_all_idx[~active_mask]

    pts_act = cloud.means[active_idx].astype(np.float64)
    nrm_act = _orient_foliage_normals_consistent(cloud.surfel_normals[active_idx])
    sc_act = cloud.scales[active_idx].astype(np.float64)
    op_act = cloud.opacities[active_idx].astype(np.float64)

    cell_obs, vis_cnt, enc_cnt = _project_kernels_to_enclosed_cells_gpu(
        pts_act, nrm_act, train_views, cell_maps, p_med=p_med, device=device
    )

    # Build 3D kNN surfel graph over active foliage Gaussians
    n_act = len(pts_act)
    act_tree = cKDTree(pts_act)
    k_nn = 14
    max_edge_r = 4.2 * p_med  # ~14.6 mm local 3D neighborhood
    dists_k, nbrs_k = act_tree.query(pts_act, k=k_nn, distance_upper_bound=max_edge_r)

    # Build unordered unique edge list (i < j)
    rows_list, cols_list, d_list = [], [], []
    for k_col in range(1, k_nn):
        ok = np.isfinite(dists_k[:, k_col]) & (nbrs_k[:, k_col] < n_act)
        src = np.where(ok)[0]
        dst = nbrs_k[ok, k_col]
        lo = np.minimum(src, dst)
        hi = np.maximum(src, dst)
        neq = lo < hi
        rows_list.append(lo[neq])
        cols_list.append(hi[neq])
        d_list.append(dists_k[ok, k_col][neq])

    ei = np.concatenate(rows_list)
    ej = np.concatenate(cols_list)
    ed = np.concatenate(d_list)
    # Deduplicate (ei, ej) pairs via 64-bit key
    pair_keys = ei.astype(np.int64) * int(n_act) + ej.astype(np.int64)
    _, uniq_pos = np.unique(pair_keys, return_index=True)
    ei, ej, ed = ei[uniq_pos], ej[uniq_pos], ed[uniq_pos]

    # Compute 3D co-planarity: |n_i · n_j| and out-of-plane step d_perp!
    diff_ij = pts_act[ej] - pts_act[ei]
    cos_nij = np.abs(np.sum(nrm_act[ei] * nrm_act[ej], axis=1))
    d_perp = 0.5 * (np.abs(np.sum(diff_ij * nrm_act[ei], axis=1)) + np.abs(np.sum(diff_ij * nrm_act[ej], axis=1)))

    # Hard geometric co-planarity filter: stacked parallel leaves (> 1.45 * p_med apart along normal) NEVER link!
    coplanar_ok = (cos_nij >= math.cos(math.radians(32.0))) & (d_perp <= 1.45 * p_med)
    ei, ej, ed, diff_ij, cos_nij, d_perp = (
        ei[coplanar_ok],
        ej[coplanar_ok],
        ed[coplanar_ok],
        diff_ij[coplanar_ok],
        cos_nij[coplanar_ok],
        d_perp[coplanar_ok],
    )

    # 3D v04 Rim-Curve Barrier Check: penalize/sever edges crossing a 3D leaf-rim curve!
    rim_pen = np.zeros(len(ei), dtype=np.float64)
    if len(priors.rim_points) > 0 and len(ei) > 0:
        rim_tree = cKDTree(priors.rim_points)
        edge_mids = 0.5 * (pts_act[ei] + pts_act[ej])
        d_rim, nn_rim = rim_tree.query(edge_mids, k=1, distance_upper_bound=1.25 * p_med)
        hit_rim = np.isfinite(d_rim) & (nn_rim < len(priors.rim_tangents))
        if np.any(hit_rim):
            e_dir = diff_ij[hit_rim] / np.maximum(ed[hit_rim, None], 1e-9)
            r_tng = priors.rim_tangents[nn_rim[hit_rim]]
            # Transverse crossing of rim curve (|e_dir · r_tng| < 0.65)
            transverse = np.abs(np.sum(e_dir * r_tng, axis=1)) < 0.68
            rim_pen[hit_rim] = np.where(transverse, 1.0, 0.25)

    # Multi-view enclosed-cell co-membership vote across all 32 views (chunked vectorized)
    n_same = np.zeros(len(ei), dtype=np.int32)
    n_diff = np.zeros(len(ei), dtype=np.int32)
    e_chunk = 200000
    for s in range(0, len(ei), e_chunk):
        e_hi = min(len(ei), s + e_chunk)
        ci = cell_obs[ei[s:e_hi]]  # (B, V)
        cj = cell_obs[ej[s:e_hi]]  # (B, V)
        both_in_cell = (ci > 0) & (cj > 0)
        same_m = both_in_cell & (ci == cj)
        diff_m = both_in_cell & (ci != cj)
        # Also count when one is inside a closed cell and the other is unoccluded outside (-1)
        one_out = ((ci > 0) & (cj == -1)) | ((cj > 0) & (ci == -1))
        n_same[s:e_hi] = same_m.sum(axis=1)
        n_diff[s:e_hi] = diff_m.sum(axis=1) + (one_out.sum(axis=1) // 2)

    # Filter out edges vetoed by multi-view leaf boundaries or strong 3D rim barriers!
    mv_veto = ((n_diff >= 2) & (n_diff > n_same)) | ((rim_pen >= 0.95) & (n_same == 0))
    keep_e = ~mv_veto
    ei, ej, ed, cos_nij, d_perp, n_same, n_diff, rim_pen = (
        ei[keep_e],
        ej[keep_e],
        ed[keep_e],
        cos_nij[keep_e],
        d_perp[keep_e],
        n_same[keep_e],
        n_diff[keep_e],
        rim_pen[keep_e],
    )

    # Compute affinity score W_ij for Plane-Bounded Kruskal Agglomeration
    geom_aff = np.exp(-0.5 * ((ed / (2.2 * p_med)) ** 2) - 0.5 * ((d_perp / (0.65 * p_med)) ** 2)) * (cos_nij ** 4)
    mv_boost = 1.0 + 0.55 * np.minimum(n_same, 6) - 0.45 * n_diff - 0.60 * rim_pen
    affinity = geom_aff * np.maximum(mv_boost, 0.0)
    pos_e = affinity > 0.08
    ei, ej, affinity = ei[pos_e], ej[pos_e], affinity[pos_e]

    order_e = np.argsort(-affinity)
    ei, ej, affinity = ei[order_e], ej[order_e], affinity[order_e]

    # Stage 4A: Plane-Constrained & Leaflet-Size-Bounded Kruskal Union-Find!
    # Maintains exact running 1st & 2nd moments (w_sum, sum_wx, sum_wxxT) per cluster in O(1) per merge!
    parent = np.arange(n_act, dtype=np.int32)
    comp_cnt = np.ones(n_act, dtype=np.int32)
    w_node = np.clip(op_act, 0.05, 1.0)
    sum_w = w_node.copy()
    sum_x = pts_act * w_node[:, None]
    sum_xx = pts_act[:, :, None] * pts_act[:, None, :] * w_node[:, None, None]

    # Physical Ficus single-leaflet geometric bounds (derived from botanical leaflet dimensions):
    # Max leaflet length ~ 13.5 cm -> sqrt(lambda_max) <= 0.039
    # Max leaflet width  ~  6.2 cm -> sqrt(lambda_mid) <= 0.0185
    # Max blade thickness (with gentle camber) -> sqrt(lambda_min) <= 0.0058
    max_eig_len = 0.039 ** 2
    max_eig_wid = 0.0185 ** 2
    max_eig_thk = 0.0058 ** 2

    def find_root(u: int) -> int:
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = int(parent[u])
        return u

    for u_i, v_i in zip(ei, ej):
        ra = find_root(int(u_i))
        rb = find_root(int(v_i))
        if ra == rb:
            continue

        wt_ab = sum_w[ra] + sum_w[rb]
        sx_ab = sum_x[ra] + sum_x[rb]
        sxx_ab = sum_xx[ra] + sum_xx[rb]

        if comp_cnt[ra] + comp_cnt[rb] >= 6:
            mean_ab = sx_ab / wt_ab
            cov_ab = (sxx_ab / wt_ab) - np.outer(mean_ab, mean_ab)
            # Fast analytical symmetric 3x3 eigenvalues
            ev = np.linalg.eigvalsh(cov_ab)
            if ev[0] > max_eig_thk or ev[1] > max_eig_wid or ev[2] > max_eig_len:
                continue

        if comp_cnt[ra] < comp_cnt[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        comp_cnt[ra] += comp_cnt[rb]
        sum_w[ra] = wt_ab
        sum_x[ra] = sx_ab
        sum_xx[ra] = sxx_ab

    # Collect core leaf clusters (>= 22 active kernels)
    roots_all = np.array([find_root(i) for i in range(n_act)], dtype=np.int32)
    uniq_roots, inv_r, r_counts = np.unique(roots_all, return_inverse=True, return_counts=True)
    min_core_kernels = 22
    core_root_mask = r_counts >= min_core_kernels
    core_roots = uniq_roots[core_root_mask]

    if len(core_roots) == 0:
        # Fallback if synthetic tiny test
        core_roots = uniq_roots[: max(1, len(uniq_roots))]

    root_to_leaf_id = {int(r_val): lid for lid, r_val in enumerate(core_roots)}
    act_leaf_id = np.array([root_to_leaf_id.get(int(r_val), -1) for r_val in roots_all], dtype=np.int32)

    # Pre-compute local PCA frames of all valid leaf cores for anisotropic Mahalanobis assignment of crumbs & halo!
    n_leaves = len(core_roots)
    core_centers = np.zeros((n_leaves, 3), dtype=np.float64)
    core_elen = np.zeros((n_leaves, 3), dtype=np.float64)
    core_ewid = np.zeros((n_leaves, 3), dtype=np.float64)
    core_enrm = np.zeros((n_leaves, 3), dtype=np.float64)
    core_a = np.zeros(n_leaves, dtype=np.float64)
    core_b = np.zeros(n_leaves, dtype=np.float64)

    for lid in range(n_leaves):
        m_l = act_leaf_id == lid
        pts_l = pts_act[m_l]
        ctr_l = pts_l.mean(axis=0)
        rel_l = pts_l - ctr_l[None, :]
        cov_l = (rel_l.T @ rel_l) / max(len(pts_l), 1)
        evals, evecs = np.linalg.eigh(cov_l)
        core_centers[lid] = ctr_l
        core_enrm[lid] = evecs[:, 0]
        core_ewid[lid] = evecs[:, 1]
        core_elen[lid] = evecs[:, 2]
        core_a[lid] = max(2.0 * math.sqrt(max(float(evals[2]), 1e-6)), 0.012)
        core_b[lid] = max(2.0 * math.sqrt(max(float(evals[1]), 1e-6)), 0.007)

    core_tree = cKDTree(core_centers)

    def assign_points_anisotropic(query_pts: np.ndarray) -> np.ndarray:
        if len(query_pts) == 0:
            return np.zeros(0, dtype=np.int32)
        k_cand = min(10, n_leaves)
        _, cand_lids = core_tree.query(query_pts, k=k_cand)
        if k_cand == 1:
            cand_lids = cand_lids[:, None]
        # (Q, K, 3)
        delta = query_pts[:, None, :] - core_centers[cand_lids]
        du = np.sum(delta * core_elen[cand_lids], axis=-1) / core_a[cand_lids]
        dv = np.sum(delta * core_ewid[cand_lids], axis=-1) / core_b[cand_lids]
        # Heavy 4x out-of-plane penalty prevents assigning across stacked leaves!
        dw = np.sum(delta * core_enrm[cand_lids], axis=-1) / 0.0045
        cost = du * du + dv * dv + dw * dw
        best_pos = np.argmin(cost, axis=1)
        return cand_lids[np.arange(len(query_pts)), best_pos].astype(np.int32)

    # Assign small leftover active crumbs (< 22 kernels) and faint halo kernels (< 0.025 opacity)
    unassigned_act = np.where(act_leaf_id < 0)[0]
    if len(unassigned_act) > 0:
        act_leaf_id[unassigned_act] = assign_points_anisotropic(pts_act[unassigned_act])

    kernel_labels[active_idx] = act_leaf_id
    if len(halo_idx) > 0:
        kernel_labels[halo_idx] = assign_points_anisotropic(cloud.means[halo_idx].astype(np.float64))

    # Build rich LeafInstance3D records with closed 3D contours & explicit occlusion confidence diagnostics
    act_vis_full = np.zeros(len(cloud.means), dtype=np.float32)
    act_enc_full = np.zeros(len(cloud.means), dtype=np.float32)
    act_vis_full[active_idx] = vis_cnt.astype(np.float32)
    act_enc_full[active_idx] = enc_cnt.astype(np.float32)

    # Fast index grouping of all kernels per leaf_id
    leaf_instances: list[LeafInstance3D] = []
    tier_counts = {"OUTER_ENCLOSED": 0, "MID_PARTIAL_OCCLUDED": 0, "DEEP_OCCLUDED": 0}

    for lid in range(n_leaves):
        k_idxs = np.where(kernel_labels == lid)[0].astype(np.int32)
        act_k = k_idxs[cloud.opacities[k_idxs] >= 0.025]
        ref_k = act_k if len(act_k) >= 4 else k_idxs

        pts_l = cloud.means[ref_k].astype(np.float64)
        sc_l = cloud.scales[ref_k].astype(np.float64)
        ctr, elen, ewid, enrm, l_w, w_w, t_w, area_w, loop_3d = _build_closed_leaf_contour_3d(pts_l, sc_l)

        mean_vis = float(np.mean(act_vis_full[ref_k]))
        mean_enc = float(np.mean(act_enc_full[ref_k]))
        closure_conf = float(np.clip(mean_enc / max(mean_vis, 1.5), 0.0, 1.0))

        # Classify occlusion tier honestly!
        if mean_vis >= 4.0 and mean_enc >= 2.0:
            tier = "OUTER_ENCLOSED"
        elif mean_vis >= 1.8:
            tier = "MID_PARTIAL_OCCLUDED"
        else:
            tier = "DEEP_OCCLUDED"
        tier_counts[tier] += 1

        leaf_instances.append(
            LeafInstance3D(
                leaf_id=lid,
                kernel_indices=k_idxs,
                active_kernel_count=int(len(act_k)),
                centroid=ctr,
                axis_length=elen,
                axis_width=ewid,
                normal=enrm,
                length_world=l_w,
                width_world=w_w,
                thickness_world=t_w,
                area_world=area_w,
                mean_vis_views=mean_vis,
                closure_confidence=closure_conf,
                visibility_tier=tier,
                boundary_loop_3d=loop_3d,
                mean_rgb=cloud.rgb_dc[ref_k].mean(axis=0).astype(np.float64),
            )
        )

    partition_stats = {
        "semantic_preclassification": sem_stats,
        "multiview_2d_detection": {
            "num_train_views": len(train_views),
            "total_valid_2d_enclosed_cells": total_2d_cells,
            "mean_2d_enclosed_cells_per_view": round(total_2d_cells / max(1, len(train_views)), 1),
        },
        "leaf_3d_partitioning": {
            "num_3d_leaf_instances": n_leaves,
            "visibility_tier_counts": tier_counts,
            "median_active_kernels_per_leaf": float(np.median([l.active_kernel_count for l in leaf_instances])),
            "mean_active_kernels_per_leaf": round(float(np.mean([l.active_kernel_count for l in leaf_instances])), 1),
            "median_leaf_length_cm_equiv": round(100.0 * float(np.median([l.length_world for l in leaf_instances])), 2),
            "median_leaf_width_cm_equiv": round(100.0 * float(np.median([l.width_world for l in leaf_instances])), 2),
            "median_leaf_thickness_mm_equiv": round(1000.0 * float(np.median([l.thickness_world for l in leaf_instances])), 2),
            "unassigned_foliage_kernels_remaining": int(np.sum(kernel_labels == LABEL_UNASSIGNED_FOLIAGE)),
        },
    }
    return kernel_labels, leaf_instances, cell_maps, partition_stats
