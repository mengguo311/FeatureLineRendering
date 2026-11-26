"""Pillar 2: Color-Agnostic, Vein-Immune Multi-View 2D->3D Organ Partitioning & Curved-Lamina Consolidation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import torch
from scipy.ndimage import distance_transform_edt, maximum_filter
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from scipy.special import expit, logit
from skimage.segmentation import watershed

from .schema_and_io import (
    LABEL_BASAL_SUPPORT,
    LABEL_STATIC_STAND_OR_TABLE,
    LABEL_STEM_SKELETON,
    LABEL_UNASSIGNED_CANOPY,
    BasalSupportModel,
    CalibratedBuildOrEvalView,
    SceneGaussianCloud,
    StemSplineChain,
    UniversalBotanicalConfig,
)


@dataclass
class Universal2DCellMap:
    """Color-agnostic, occlusion-gated 2D enclosed botanical organ regions for a single view."""

    view_name: str
    cell_id_map: np.ndarray        # (H, W) int32: 0 = bg/support/boundary, 1..K = enclosed organ cell
    cell_area_px: np.ndarray       # (K+1,) int32
    occlusion_wall: np.ndarray     # (H, W) bool true physical occlusion/silhouette boundary
    num_valid_cells: int


def _project_support_and_stems_mask(
    view: CalibratedBuildOrEvalView,
    support: BasalSupportModel,
    stem_pts: np.ndarray,
    p_med: float,
) -> np.ndarray:
    """Project verified 3D support container/stand/ground and thick stem cores into 2D view to exclude from canopy."""
    h, w = view.height, view.width
    excl = np.zeros((h, w), dtype=np.uint8)

    # 1. Exclude pixels below rim_z (for OPEN_GROUND_BED) or inside projected 3D support mesh when front-visible!
    if support.regime == "OPEN_GROUND_BED":
        uu, vv = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        zc = view.front_depth
        xc = (uu - float(view.cx)) * zc / float(view.fx)
        yc = (vv - float(view.cy)) * zc / float(view.fy)
        R_c2w = view.c2w[:3, :3].astype(np.float32)
        t_c2w = view.c2w[:3, 3].astype(np.float32)
        world_z = xc * R_c2w[2, 0] + yc * R_c2w[2, 1] + zc * R_c2w[2, 2] + t_c2w[2]
        excl[(view.front_depth > 0.15) & (world_z <= float(support.rim_z))] = 1
    elif len(support.faces) > 0:
        # Project support mesh triangles that are not occluded behind foreground canopy
        pts_c = support.vertices.astype(np.float64) @ view.w2c[:3, :3].T + view.w2c[:3, 3][None, :]
        zc = pts_c[:, 2]
        uv = np.rint(
            np.column_stack([
                view.fx * pts_c[:, 0] / np.maximum(zc, 0.05) + view.cx,
                view.fy * pts_c[:, 1] / np.maximum(zc, 0.05) + view.cy,
            ])
        ).astype(np.int32)
        mesh_z = np.full((h, w), np.inf, dtype=np.float32)
        for tri in support.faces:
            zt = zc[tri]
            if np.any(zt <= 0.05):
                continue
            poly = uv[tri]
            tmp_m = np.zeros((h, w), dtype=np.uint8)
            cv2.fillConvexPoly(tmp_m, poly, 1)
            ys, xs = np.where(tmp_m > 0)
            if len(xs) > 0:
                z_mean = float(zt.mean())
                mesh_z[ys, xs] = np.minimum(mesh_z[ys, xs], z_mean)
        vis_sup = np.isfinite(mesh_z) & (mesh_z <= view.front_depth + 6.0 * p_med)
        excl[vis_sup] = 1

    # Also exclude under-vessel stand/table world_z < vessel_bot_z
    if support.vessel_bot_z > -1e8 and support.regime in {"RECTANGULAR_TRAY_LOFT", "AXISYMMETRIC_LATHE", "CONVEX_SECTION_LOFT"}:
        uu, vv = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        zc = view.front_depth
        xc = (uu - float(view.cx)) * zc / float(view.fx)
        yc = (vv - float(view.cy)) * zc / float(view.fy)
        R_c2w = view.c2w[:3, :3].astype(np.float32)
        t_c2w = view.c2w[:3, 3].astype(np.float32)
        world_z = xc * R_c2w[2, 0] + yc * R_c2w[2, 1] + zc * R_c2w[2, 2] + t_c2w[2]
        excl[(view.front_depth > 0.15) & (world_z < float(support.vessel_bot_z))] = 1

    # 2. Exclude unoccluded thick stem pixels
    if len(stem_pts) > 0:
        Xs = stem_pts @ view.w2c[:3, :3].T + view.w2c[:3, 3][None, :]
        zs = Xs[:, 2]
        us = np.rint(view.fx * Xs[:, 0] / np.maximum(zs, 0.05) + view.cx).astype(np.int32)
        vs = np.rint(view.fy * Xs[:, 1] / np.maximum(zs, 0.05) + view.cy).astype(np.int32)
        inb = (zs > 0.15) & (us >= 0) & (us < w) & (vs >= 0) & (vs < h)
        us, vs, zs = us[inb], vs[inb], zs[inb]
        vis_s = np.abs(zs - view.front_depth[vs, us]) <= 3.0 * p_med
        if np.any(vis_s):
            stem_px = np.zeros((h, w), dtype=np.uint8)
            stem_px[vs[vis_s], us[vis_s]] = 1
            stem_px = cv2.dilate(stem_px, np.ones((3, 3), np.uint8))
            excl |= stem_px

    return excl > 0


def detect_universal_2d_organ_cells(
    view: CalibratedBuildOrEvalView,
    support: BasalSupportModel,
    stem_pts: np.ndarray,
    curve_pts: np.ndarray,
    p_med: float,
    cfg: UniversalBotanicalConfig,
) -> Universal2DCellMap:
    """Color-agnostic, vein-immune 2D organ region detector with plane-detrended depth IQR validation."""
    h, w = view.height, view.width
    excl = _project_support_and_stems_mask(view, support, stem_pts, p_med)

    # 100% COLOR-AGNOSTIC foreground: works identically for green, pink, bronze, yellow, or tan dried foliage!
    is_canopy_fg = (view.alpha > 0.50) & (view.front_depth > 0.15) & (~excl)
    fg_total = int(is_canopy_fg.sum())
    min_area_eff = max(12, min(cfg.min_cell_area_px, int(0.0012 * fg_total)))
    if fg_total < min_area_eff:
        return Universal2DCellMap(
            view_name=view.view_name,
            cell_id_map=np.zeros((h, w), dtype=np.int32),
            cell_area_px=np.zeros(1, dtype=np.int32),
            occlusion_wall=~is_canopy_fg,
            num_valid_cells=0,
        )

    # Disentangle TRUE OCCLUDING LEAF MARGINS from INTERNAL PHOTOMETRIC LEAF VEINS!
    # Pixel-wise physical pixel size in 3D: p_pix(u, v) = z / sqrt(fx * fy)
    focal = math.sqrt(float(view.fx) * float(view.fy))
    p_pix = np.maximum(view.front_depth / max(focal, 1.0), 0.5 * p_med)

    # True depth step across overlapping leaves (>= 3.2 local pixel scales)
    true_depth_wall = view.depth_jump > np.maximum(3.2 * p_pix, 0.011)

    # Silhouette / alpha drop wall
    fg_u8 = is_canopy_fg.astype(np.uint8)
    sil_wall = (fg_u8 > 0) & (cv2.erode(fg_u8, np.ones((3, 3), np.uint8)) == 0)

    # Photometric C2L edge is ONLY promoted to a hard watershed barrier when corroborated by either:
    #   (a) moderate local depth gradient (dilated depth_jump > 1.6 * p_pix), OR
    #   (b) deep inter-leaf shadow cleft (darkness > 0.34 & skeleton)!
    # Flat painted midribs/veins inside a smooth cabbage/canna blade have depth_jump ~ 0 and darkness ~ 0.15-0.25 -> IGNORED!
    mod_depth_grad = cv2.dilate((view.depth_jump > np.maximum(1.65 * p_pix, 0.006)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    corroborated_c2l = (view.skeleton & mod_depth_grad) | (view.skeleton & (view.darkness > 0.36))

    # Optional 3D curve barrier ONLY where corroborated by local depth gradient (avoids 3D vein curves splitting blades!)
    proj_curve_wall = np.zeros((h, w), dtype=bool)
    if len(curve_pts) > 0:
        Xc = curve_pts @ view.w2c[:3, :3].T + view.w2c[:3, 3][None, :]
        zc = Xc[:, 2]
        ok = zc > 0.15
        if np.any(ok):
            uc = np.rint(view.fx * Xc[ok, 0] / zc[ok] + view.cx).astype(np.int32)
            vc = np.rint(view.fy * Xc[ok, 1] / zc[ok] + view.cy).astype(np.int32)
            zc_ok = zc[ok]
            inb = (uc >= 0) & (uc < w) & (vc >= 0) & (vc < h)
            uc, vc, zc_ok = uc[inb], vc[inb], zc_ok[inb]
            vis_c = zc_ok <= view.front_depth[vc, uc] + 3.5 * p_med
            raw_cw = np.zeros((h, w), dtype=np.uint8)
            raw_cw[vc[vis_c], uc[vis_c]] = 1
            proj_curve_wall = (raw_cw > 0) & mod_depth_grad

    edge_only = (true_depth_wall | sil_wall | corroborated_c2l | proj_curve_wall).astype(np.uint8)
    closed_edge = cv2.morphologyEx(edge_only, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) > 0
    wall = (~is_canopy_fg) | closed_edge

    interior = is_canopy_fg & (~wall)
    if int(interior.sum()) < cfg.min_cell_area_px:
        return Universal2DCellMap(
            view_name=view.view_name,
            cell_id_map=np.zeros((h, w), dtype=np.int32),
            cell_area_px=np.zeros(1, dtype=np.int32),
            occlusion_wall=wall,
            num_valid_cells=0,
        )

    dt = distance_transform_edt(interior).astype(np.float32)
    # Adaptive marker spacing scaled to actual interior blade thickness distribution of this plant!
    med_dt = float(np.percentile(dt[interior], 75.0))
    win_sz = int(np.clip(round(1.65 * med_dt), 7, 25))
    if win_sz % 2 == 0:
        win_sz += 1
    dt_smooth = cv2.GaussianBlur(dt, (5, 5), 1.0)
    loc_max = (dt_smooth == maximum_filter(dt_smooth, size=win_sz)) & (dt >= 1.8) & interior
    n_markers, markers = cv2.connectedComponents(loc_max.astype(np.uint8), connectivity=8)
    if n_markers <= 1:
        return Universal2DCellMap(
            view_name=view.view_name,
            cell_id_map=np.zeros((h, w), dtype=np.int32),
            cell_area_px=np.zeros(1, dtype=np.int32),
            occlusion_wall=wall,
            num_valid_cells=0,
        )

    # Elevation dominated by physical depth jumps and strong creases (NOT weak internal vein shading!)
    elevation = -dt_smooth + 28.0 * np.minimum(view.depth_jump / np.maximum(p_pix, 1e-4), 8.0) + 2.2 * np.maximum(view.darkness - 0.18, 0.0)
    ws_labels = watershed(elevation, markers=markers, mask=is_canopy_fg)

    max_area_px = max(4800, int(cfg.max_cell_area_frac * fg_total))
    counts = np.bincount(ws_labels.ravel())
    cand_ids = np.where((counts >= min_area_eff) & (counts <= max_area_px))[0]
    cand_ids = cand_ids[cand_ids > 0]

    flat_lbl = ws_labels.ravel()
    nz_idx = np.flatnonzero(flat_lbl > 0)
    nz_lbl = flat_lbl[nz_idx]
    order = np.argsort(nz_lbl)
    sorted_idx = nz_idx[order]
    sorted_lbl = nz_lbl[order]
    split_pos = np.searchsorted(sorted_lbl, cand_ids)
    split_end = np.searchsorted(sorted_lbl, cand_ids, side="right")

    phys_support = cv2.dilate((~is_canopy_fg | true_depth_wall | corroborated_c2l | (view.darkness > 0.24)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0

    valid_map = np.zeros((h, w), dtype=np.int32)
    areas = [0]
    next_id = 1

    for k_i, cid in enumerate(cand_ids):
        pix_flat = sorted_idx[split_pos[k_i] : split_end[k_i]]
        area = len(pix_flat)
        rs = pix_flat // w
        cs = pix_flat % w

        # PLANE-DETRENDED DEPTH SMOOTHNESS GATE!
        # Allows large tilted/slanted blades (Brassica, Flowers Canna, Garden palm) whose raw z spans 20+ cm,
        # while strictly rejecting cells that jump across two distinct depth surfaces!
        z_vals = view.front_depth[rs, cs].astype(np.float64)
        if area >= 12:
            rc_c = np.column_stack([np.ones(area), (rs - rs.mean()) / 50.0, (cs - cs.mean()) / 50.0])
            coef = np.linalg.lstsq(rc_c, z_vals, rcond=None)[0]
            z_res = z_vals - (rc_c @ coef)
        else:
            z_res = z_vals - np.median(z_vals)
        q75, q25 = np.percentile(z_res, [75.0, 25.0])
        local_p = float(np.median(p_pix[rs, cs]))
        if float(q75 - q25) > cfg.detrended_depth_iqr_mult * max(local_p, p_med):
            continue

        r0, r1 = max(0, int(rs.min()) - 1), min(h, int(rs.max()) + 2)
        c0, c1 = max(0, int(cs.min()) - 1), min(w, int(cs.max()) + 2)
        sub_m = (ws_labels[r0:r1, c0:c1] == cid).astype(np.uint8)
        eroded = cv2.erode(sub_m, np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8))
        perim = (sub_m > 0) & (eroded == 0)
        if int(perim.sum()) < 8:
            continue
        closure = float(np.mean(phys_support[r0:r1, c0:c1][perim]))
        if closure < 0.56:
            continue

        valid_map[rs, cs] = next_id
        areas.append(area)
        next_id += 1

    return Universal2DCellMap(
        view_name=view.view_name,
        cell_id_map=valid_map,
        cell_area_px=np.asarray(areas, dtype=np.int32),
        occlusion_wall=wall,
        num_valid_cells=next_id - 1,
    )


@torch.no_grad()
def _project_canopy_kernels_gpu(
    pts_act: np.ndarray,
    nrm_act: np.ndarray,
    views: list[CalibratedBuildOrEvalView],
    cmaps: list[Universal2DCellMap],
    p_med: float,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Project active canopy Gaussians onto build views with front-surface depth gating."""
    m = len(pts_act)
    v_cnt = len(views)
    cell_obs = np.zeros((m, v_cnt), dtype=np.int32)
    vis_cnt = np.zeros(m, dtype=np.int32)
    enc_cnt = np.zeros(m, dtype=np.int32)
    if m == 0:
        return cell_obs, vis_cnt, enc_cnt

    X_t = torch.tensor(pts_act, dtype=torch.float32, device=device)
    N_t = torch.tensor(nrm_act, dtype=torch.float32, device=device)

    for v_i, (vw, cmap) in enumerate(zip(views, cmaps)):
        R_t = torch.tensor(vw.w2c[:3, :3], dtype=torch.float32, device=device)
        t_t = torch.tensor(vw.w2c[:3, 3], dtype=torch.float32, device=device)
        cam_t = torch.tensor(vw.cam_center, dtype=torch.float32, device=device)

        Xc = X_t @ R_t.T + t_t[None, :]
        z = Xc[:, 2]
        u = torch.round(float(vw.fx) * (Xc[:, 0] / z.clamp(min=1e-3)) + float(vw.cx)).long()
        v_px = torch.round(float(vw.fy) * (Xc[:, 1] / z.clamp(min=1e-3)) + float(vw.cy)).long()

        inb = (z > 0.15) & (u >= 0) & (u < vw.width) & (v_px >= 0) & (v_px < vw.height)
        idx_in = torch.where(inb)[0]
        if len(idx_in) == 0:
            continue

        fd_t = torch.tensor(vw.front_depth, dtype=torch.float32, device=device)
        al_t = torch.tensor(vw.alpha, dtype=torch.float32, device=device)
        cid_t = torch.tensor(cmap.cell_id_map, dtype=torch.int32, device=device)

        u_in, v_in, z_in = u[idx_in], v_px[idx_in], z[idx_in]
        v_dir = torch.nn.functional.normalize(cam_t[None, :] - X_t[idx_in], dim=-1, eps=1e-8)
        not_grazing = torch.abs((N_t[idx_in] * v_dir).sum(dim=-1)) >= 0.12

        focal = math.sqrt(float(vw.fx) * float(vw.fy))
        tol_t = torch.clamp(3.0 * (z_in / max(focal, 1.0)), min=2.8 * p_med)
        front_vis = (al_t[v_in, u_in] > 0.45) & (fd_t[v_in, u_in] > 0.15) & (torch.abs(z_in - fd_t[v_in, u_in]) <= tol_t) & not_grazing

        vis_idx = idx_in[front_vis]
        if len(vis_idx) == 0:
            continue

        c_vals = cid_t[v_px[vis_idx], u[vis_idx]].cpu().numpy()
        vis_np = vis_idx.cpu().numpy()
        vis_cnt[vis_np] += 1
        has_c = c_vals > 0
        enc_cnt[vis_np[has_c]] += 1
        cell_obs[vis_np, v_i] = np.where(has_c, c_vals, -1)

    return cell_obs, vis_cnt, enc_cnt


def partition_and_consolidate_canopy_organs(
    cloud: SceneGaussianCloud,
    train_views: list[CalibratedBuildOrEvalView],
    support: BasalSupportModel,
    stem_chains: list[StemSplineChain],
    domain_labels: np.ndarray,
    curve_pts: np.ndarray,
    p_med: float,
    cfg: UniversalBotanicalConfig,
    device: torch.device,
) -> tuple[SceneGaussianCloud, np.ndarray, list[dict[str, Any]], list[Universal2DCellMap], dict[str, Any]]:
    """Color-agnostic 2D->3D organ partitioning + curved-lamina geodesic seam consolidation + selective M1+M2."""
    labels = domain_labels.copy()
    stem_pts = cloud.means[labels == LABEL_STEM_SKELETON].astype(np.float64)

    # Stage 2A: 32-view color-agnostic, vein-immune 2D organ region detection
    train_cmaps = [detect_universal_2d_organ_cells(vw, support, stem_pts, curve_pts, p_med, cfg) for vw in train_views]
    total_2d_cells = int(sum(cm.num_valid_cells for cm in train_cmaps))

    canopy_all = np.flatnonzero(labels == LABEL_UNASSIGNED_CANOPY)
    if len(canopy_all) == 0:
        return cloud, labels, [], train_cmaps, {"total_2d_cells": total_2d_cells, "num_organs": 0}

    act_mask = cloud.opacities[canopy_all] >= 0.025
    act_idx = canopy_all[act_mask]
    halo_idx = canopy_all[~act_mask]

    pts_act = cloud.means[act_idx].astype(np.float64)
    nrm_raw = cloud.surfel_normals[act_idx].astype(np.float64)
    nrm_len = np.linalg.norm(nrm_raw, axis=1, keepdims=True)
    nrm_surfel = np.where(nrm_len > 1e-9, nrm_raw / np.maximum(nrm_len, 1e-9), np.array([0.0, 0.0, 1.0]))
    op_act = cloud.opacities[act_idx].astype(np.float64)

    # CRITICAL VANILLA-3DGS GENERALIZATION FIX:
    # Many vanilla 3DGS leaf models (Brassica, Garden, Flowers, Bonsai) use 1D cigar splats (s0 ~ s1 << s2) tangent
    # to the leaf surface, whose shortest-scale axis spins randomly around the cigar!
    # Estimate true local 3D point-cloud surface normals via vectorized k=16 neighborhood covariance PCA, and fuse
    # with surfel_normals ONLY when the Gaussian itself is a flat pancake (planarity > 0.48)!
    n_act = len(pts_act)
    act_tree = cKDTree(pts_act)
    k_pca = min(16, n_act)
    _, nb_pca = act_tree.query(pts_act, k=k_pca)
    if nb_pca.ndim == 1:
        nb_pca = nb_pca[:, None]
    nb_pts = pts_act[nb_pca]  # (N_act, k_pca, 3)
    nb_ctr = nb_pts.mean(axis=1, keepdims=True)
    nb_rel = nb_pts - nb_ctr
    cov_loc = np.einsum("nki,nkj->nij", nb_rel, nb_rel) / max(k_pca, 1)
    _, evecs_loc = np.linalg.eigh(cov_loc)
    nrm_pca = evecs_loc[:, :, 0]  # shortest neighborhood axis = true sheet surface normal!

    sc_sorted = np.sort(cloud.scales[act_idx].astype(np.float64), axis=1)
    splat_planarity = (sc_sorted[:, 1] - sc_sorted[:, 0]) / np.maximum(sc_sorted[:, 2], 1e-8)
    # Align nrm_pca sign with nrm_surfel where possible
    flip_sign = np.where(np.sum(nrm_pca * nrm_surfel, axis=1) >= 0.0, 1.0, -1.0)
    nrm_pca = nrm_pca * flip_sign[:, None]
    w_surf = np.clip((splat_planarity - 0.35) / 0.30, 0.0, 1.0)[:, None]
    nrm_fused = w_surf * nrm_surfel + (1.0 - w_surf) * nrm_pca
    nrm_act = nrm_fused / np.maximum(np.linalg.norm(nrm_fused, axis=1, keepdims=True), 1e-9)

    cell_obs, vis_cnt, enc_cnt = _project_canopy_kernels_gpu(pts_act, nrm_act, train_views, train_cmaps, p_med, device)

    # Stage 2B: Scale-Free Co-Planar / Smooth-Curvature 3D Surfel Graph (NO hardcoded 6.2cm Ficus size cap!)
    k_nn = min(16, n_act)
    dists_k, nbrs_k = act_tree.query(pts_act, k=k_nn, distance_upper_bound=5.0 * p_med)

    rows_l, cols_l, d_l = [], [], []
    for kc in range(1, k_nn):
        ok = np.isfinite(dists_k[:, kc]) & (nbrs_k[:, kc] < n_act)
        s = np.flatnonzero(ok)
        t = nbrs_k[ok, kc]
        lo, hi = np.minimum(s, t), np.maximum(s, t)
        neq = lo < hi
        rows_l.append(lo[neq])
        cols_l.append(hi[neq])
        d_l.append(dists_k[ok, kc][neq])

    if rows_l:
        ei = np.concatenate(rows_l)
        ej = np.concatenate(cols_l)
        ed = np.concatenate(d_l)
        pkeys = ei.astype(np.int64) * int(n_act) + ej.astype(np.int64)
        _, upos = np.unique(pkeys, return_index=True)
        ei, ej, ed = ei[upos], ej[upos], ed[upos]
    else:
        ei = np.zeros(0, dtype=np.int32)
        ej = np.zeros(0, dtype=np.int32)
        ed = np.zeros(0, dtype=np.float64)

    diff_ij = pts_act[ej] - pts_act[ei]
    cos_nij = np.abs(np.sum(nrm_act[ei] * nrm_act[ej], axis=1))
    d_perp = 0.5 * (np.abs(np.sum(diff_ij * nrm_act[ei], axis=1)) + np.abs(np.sum(diff_ij * nrm_act[ej], axis=1)))

    # Local co-surface compatibility (allows curved sheets because check is strictly pairwise local!)
    cos_min = math.cos(math.radians(cfg.coplanar_normal_deg))
    coplanar_ok = (cos_nij >= cos_min) & (d_perp <= cfg.coplanar_step_mult * p_med)
    ei, ej, ed, cos_nij, d_perp = ei[coplanar_ok], ej[coplanar_ok], ed[coplanar_ok], cos_nij[coplanar_ok], d_perp[coplanar_ok]

    # Multi-view cell co-membership votes
    n_same = np.zeros(len(ei), dtype=np.int32)
    n_diff = np.zeros(len(ei), dtype=np.int32)
    chunk = 200000
    for s0 in range(0, len(ei), chunk):
        s1 = min(len(ei), s0 + chunk)
        ci = cell_obs[ei[s0:s1]]
        cj = cell_obs[ej[s0:s1]]
        both = (ci > 0) & (cj > 0)
        n_same[s0:s1] = (both & (ci == cj)).sum(axis=1)
        n_diff[s0:s1] = (both & (ci != cj)).sum(axis=1)

    # Veto ONLY when multi-view cells strongly disagree
    keep = ~((n_diff >= 2) & (n_diff > n_same))
    ei, ej, ed, cos_nij, d_perp, n_same, n_diff = ei[keep], ej[keep], ed[keep], cos_nij[keep], d_perp[keep], n_same[keep], n_diff[keep]

    geom_aff = np.exp(-0.5 * ((ed / (2.5 * p_med)) ** 2) - 0.5 * ((d_perp / (0.75 * p_med)) ** 2)) * (cos_nij ** 3)
    mv_boost = 1.0 + 0.65 * np.minimum(n_same, 6) - 0.45 * n_diff
    aff = geom_aff * np.maximum(mv_boost, 0.0)
    pos_a = aff > 0.10
    ei, ej, aff = ei[pos_a], ej[pos_a], aff[pos_a]

    order_e = np.argsort(-aff)
    ei, ej, aff = ei[order_e], ej[order_e], aff[order_e]

    # Thickness-only Kruskal Union-Find: prevents merging stacked parallel leaf layers while allowing ARBITRARY blade width/length!
    # Also tracks each cluster's dominant (view, cell_id) signature so distinct narrow leaflets in dense rosettes stay separate
    # unless verified continuous in Stage 2C!
    parent = np.arange(n_act, dtype=np.int32)
    comp_cnt = np.ones(n_act, dtype=np.int32)
    w_node = np.clip(op_act, 0.05, 1.0)
    sum_w = w_node.copy()
    sum_x = pts_act * w_node[:, None]
    sum_xx = pts_act[:, :, None] * pts_act[:, None, :] * w_node[:, None, None]

    def find_r(u: int) -> int:
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u

    for u_i, v_i in zip(ei.tolist(), ej.tolist()):
        ru, rv = find_r(u_i), find_r(v_i)
        if ru == rv:
            continue
        wt = sum_w[ru] + sum_w[rv]
        xt = sum_x[ru] + sum_x[rv]
        xxt = sum_xx[ru] + sum_xx[rv]
        mean_t = xt / wt
        cov_t = (xxt / wt) - np.outer(mean_t, mean_t)
        evals = np.linalg.eigvalsh(cov_t)
        # Scale-adaptive sheet thickness guard: prevents merging distinct fronds/bouquets into a 3D ball
        # while allowing arbitrarily wide gently-cambered broad leaves (up to ~5.2 * p_med camber std)!
        l0 = max(float(evals[0]), 0.0)
        l2 = max(float(evals[2]), 1e-8)
        max_thk_sq = min((5.2 * p_med) ** 2, max((2.2 * p_med) ** 2, (0.19 ** 2) * l2))
        if comp_cnt[ru] + comp_cnt[rv] >= 24 and l0 > max_thk_sq:
            continue
        if comp_cnt[ru] < comp_cnt[rv]:
            ru, rv = rv, ru
        parent[rv] = ru
        comp_cnt[ru] += comp_cnt[rv]
        sum_w[ru] = wt
        sum_x[ru] = xt
        sum_xx[ru] = xxt

    roots = np.array([find_r(i) for i in range(n_act)], dtype=np.int32)
    u_roots, inv_c, cnt_c = np.unique(roots, return_inverse=True, return_counts=True)

    # Merge tiny orphan fragments (< 14 active kernels) into nearest normal-compatible larger cluster
    large_mask = cnt_c >= 14
    if not np.any(large_mask):
        large_mask[:] = True
    large_cids = np.flatnonzero(large_mask)
    init_cid = np.full(n_act, -1, dtype=np.int32)
    for new_id, old_c in enumerate(large_cids):
        init_cid[inv_c == old_c] = new_id

    rem_small = np.flatnonzero(init_cid < 0)
    assigned = np.flatnonzero(init_cid >= 0)
    if len(rem_small) > 0 and len(assigned) > 0:
        asg_tree = cKDTree(pts_act[assigned])
        dk, nk = asg_tree.query(pts_act[rem_small], k=min(8, len(assigned)))
        if dk.ndim == 1:
            dk, nk = dk[:, None], nk[:, None]
        for r_pos, s_idx in enumerate(rem_small):
            best_c = int(init_cid[assigned[int(nk[r_pos, 0])]])
            best_sc = -1e9
            for c_k in range(dk.shape[1]):
                nb = assigned[int(nk[r_pos, c_k])]
                cs = abs(float(np.dot(nrm_act[s_idx], nrm_act[nb])))
                sc = cs - float(dk[r_pos, c_k]) / max(8.0 * p_med, 1e-4)
                if sc > best_sc:
                    best_sc = sc
                    best_c = int(init_cid[nb])
            init_cid[s_idx] = best_c

    # -----------------------------------------------------------------------
    # Stage 2C: Multi-View Seam Co-Surface Geodesic Consolidation!
    # Directly heals broad, veined, ruffled leaves (e.g., Brassica, Canna) that got split into adjacent sub-patches,
    # while preserving true inter-leaf boundaries backed by multi-view depth steps or shadow clefts!
    # -----------------------------------------------------------------------
    n_clusters_init = int(init_cid.max()) + 1
    seam_merges = 0
    if n_clusters_init >= 2:
        # Find spatial boundary contacts between distinct clusters within 4.5 * p_med
        d_seam, nb_seam = act_tree.query(pts_act, k=min(12, n_act), distance_upper_bound=4.5 * p_med)
        pair_contacts: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for kc in range(1, d_seam.shape[1]):
            ok = np.isfinite(d_seam[:, kc]) & (nb_seam[:, kc] < n_act)
            s = np.flatnonzero(ok)
            t = nb_seam[ok, kc]
            ca, cb = init_cid[s], init_cid[t]
            diff_c = ca < cb
            for si, ti, cai, cbi in zip(s[diff_c].tolist(), t[diff_c].tolist(), ca[diff_c].tolist(), cb[diff_c].tolist()):
                lst = pair_contacts.setdefault((cai, cbi), [])
                if len(lst) < 48:
                    lst.append((si, ti))

        # Precompute blurred depth_jump & darkness on 16 build views for fast seam barrier checking
        check_views = train_views[:: max(1, len(train_views) // 16)][:16]
        vw_dj = [cv2.dilate(vw.depth_jump.astype(np.float32), np.ones((3, 3), np.uint8)) for vw in check_views]

        c_parent = np.arange(n_clusters_init, dtype=np.int32)

        def find_cp(c: int) -> int:
            while c_parent[c] != c:
                c_parent[c] = c_parent[c_parent[c]]
                c = c_parent[c]
            return c

        cos_seam_min = math.cos(math.radians(cfg.seam_merge_normal_deg))
        # Sort candidate pairs by number of boundary contact pairs descending
        sorted_pairs = sorted(pair_contacts.items(), key=lambda kv: -len(kv[1]))
        for (ca, cb), contacts in sorted_pairs:
            ra, rb = find_cp(ca), find_cp(cb)
            if ra == rb or len(contacts) < 4:
                continue
            ia = np.array([p[0] for p in contacts], dtype=np.int32)
            ib = np.array([p[1] for p in contacts], dtype=np.int32)

            # 1. Local 3D seam co-surface check: smooth normal transition & small out-of-plane step right at the seam!
            na_mean = nrm_act[ia].mean(axis=0)
            na_mean /= max(float(np.linalg.norm(na_mean)), 1e-9)
            # Align individual normals in ib to their local consensus before averaging
            signs_b = np.where((nrm_act[ib] @ na_mean) >= 0.0, 1.0, -1.0)
            nb_mean = (nrm_act[ib] * signs_b[:, None]).mean(axis=0)
            nb_mean /= max(float(np.linalg.norm(nb_mean)), 1e-9)
            cos_ab = abs(float(np.dot(na_mean, nb_mean)))
            if cos_ab < cos_seam_min:
                continue

            d_vec = pts_act[ib] - pts_act[ia]
            step_perp = float(np.median(0.5 * (np.abs(d_vec @ na_mean) + np.abs(d_vec @ nb_mean))))
            if step_perp > cfg.seam_merge_step_mult * p_med:
                continue

            # 2. Check combined quadratic-camber-detrended 3D sheet thickness!
            # Allows strongly curved/ruffled broad Brassica leaves (low residual around quadratic sheet!) while blocking 3D bouquet balls!
            all_ab = np.where((init_cid == ra) | (init_cid == rb))[0]
            if len(all_ab) >= 24:
                p_ab = pts_act[all_ab]
                rel_ab = p_ab - p_ab.mean(axis=0)
                ev_ab, evec_ab = np.linalg.eigh(np.cov(rel_ab.T))
                u_ab = rel_ab @ evec_ab[:, 2]
                v_ab = rel_ab @ evec_ab[:, 1]
                w_ab = rel_ab @ evec_ab[:, 0]
                A_q = np.column_stack([np.ones(len(u_ab)), u_ab, v_ab, u_ab ** 2, u_ab * v_ab, v_ab ** 2])
                c_q = np.linalg.lstsq(A_q.T @ A_q + 1e-3 * np.eye(6), A_q.T @ w_ab, rcond=None)[0]
                w_res_iqr = float(np.percentile(w_ab - (A_q @ c_q), 85.0) - np.percentile(w_ab - (A_q @ c_q), 15.0))
                if w_res_iqr > 8.2 * p_med:
                    continue

            # 3. Multi-view build seam barrier check: project 3D seam midpoints into check_views!
            mids = 0.5 * (pts_act[ia] + pts_act[ib])
            seam_dj_ratios: list[float] = []
            seam_dark_vals: list[float] = []
            for vw, dj_map in zip(check_views, vw_dj):
                Xc = mids @ vw.w2c[:3, :3].T + vw.w2c[:3, 3][None, :]
                zc = Xc[:, 2]
                um = np.rint(vw.fx * Xc[:, 0] / np.maximum(zc, 0.05) + vw.cx).astype(np.int32)
                vm = np.rint(vw.fy * Xc[:, 1] / np.maximum(zc, 0.05) + vw.cy).astype(np.int32)
                inb = (zc > 0.15) & (um >= 0) & (um < vw.width) & (vm >= 0) & (vm < vw.height)
                if not np.any(inb):
                    continue
                um, vm, zc = um[inb], vm[inb], zc[inb]
                vis_m = (vw.alpha[vm, um] > 0.55) & (np.abs(zc - vw.front_depth[vm, um]) <= 4.0 * p_med)
                if int(vis_m.sum()) >= 2:
                    focal = math.sqrt(float(vw.fx) * float(vw.fy))
                    loc_p = np.maximum(zc[vis_m] / max(focal, 1.0), p_med)
                    seam_dj_ratios.append(float(np.median(dj_map[vm[vis_m], um[vis_m]] / loc_p)))
                    seam_dark_vals.append(float(np.median(vw.darkness[vm[vis_m], um[vis_m]])))

            if len(seam_dj_ratios) == 0:
                continue
            # Merge ONLY if the seam lies inside a continuous depth surface (no depth jump & no deep inter-leaf shadow cleft!)
            if float(np.median(seam_dj_ratios)) <= cfg.seam_merge_djump_mult and float(np.median(seam_dark_vals)) <= 0.30:
                c_parent[rb] = ra
                # Update init_cid eagerly so subsequent thickness checks reflect merged state
                init_cid[init_cid == rb] = ra
                seam_merges += 1

    # Compact organ IDs 0 .. N_organs - 1
    _, final_act_oid = np.unique(init_cid, return_inverse=True)
    labels[act_idx] = final_act_oid

    # Assign faint halo canopy Gaussians (< 0.025 opacity) to nearest active organ
    if len(halo_idx) > 0:
        _, nn_h = act_tree.query(cloud.means[halo_idx].astype(np.float64), k=1)
        labels[halo_idx] = final_act_oid[nn_h]

    # -----------------------------------------------------------------------
    # Stage 2D: Classify Organs into LAMINAR_BLADE vs VOLUMETRIC_CLUSTER & Apply SH3-Preserving Selective M1+M2!
    # -----------------------------------------------------------------------
    n_organs = int(final_act_oid.max()) + 1
    organ_records: list[dict[str, Any]] = []
    laminar_organ_ids: set[int] = set()

    for oid in range(n_organs):
        k_all = np.flatnonzero(labels == oid)
        k_act = k_all[cloud.opacities[k_all] >= 0.025]
        ref_k = k_act if len(k_act) >= 4 else k_all
        pts_o = cloud.means[ref_k].astype(np.float64)
        ctr = pts_o.mean(axis=0)
        rel = pts_o - ctr[None, :]
        evals, evecs = np.linalg.eigh((rel.T @ rel) / max(len(pts_o), 1))
        e3, e2, e1 = evecs[:, 0], evecs[:, 1], evecs[:, 2]
        if e3[2] < 0.0:
            e3 = -e3
        if float(np.dot(np.cross(e1, e2), e3)) < 0.0:
            e2 = -e2

        pad = float(np.median(cloud.scales[ref_k].max(axis=1))) * 1.25 if len(ref_k) > 0 else 2.0 * p_med
        u_c = rel @ e1
        v_c = rel @ e2
        w_c = rel @ e3
        L_span = max(float(np.percentile(u_c, 98.0) - np.percentile(u_c, 2.0)) + 2.0 * pad, 4.0 * p_med)
        W_span = max(float(np.percentile(v_c, 98.0) - np.percentile(v_c, 2.0)) + 2.0 * pad, 3.0 * p_med)
        T_span = float(np.percentile(w_c, 95.0) - np.percentile(w_c, 5.0))

        act_sub = np.isin(act_idx, k_act)
        mean_vis = float(vis_cnt[act_sub].mean()) if np.any(act_sub) else 0.0
        enc_frac = float((enc_cnt[act_sub] >= 2).mean()) if np.any(act_sub) else 0.0
        if enc_frac >= 0.25 and mean_vis >= 2.0:
            tier = "OUTER_ENCLOSED"
        elif mean_vis >= 1.0:
            tier = "MID_PARTIAL_OCCLUDED"
        else:
            tier = "DEEP_OCCLUDED"

        # Laminar vs Volumetric physical geometry criterion:
        # Require multi-view enclosed evidence (OUTER_ENCLOSED), above container rim, and thin quadratic-detrended sheet residual!
        thk_ratio = T_span / max(L_span, 1e-4)
        if len(pts_o) >= 16:
            Aq_o = np.column_stack([np.ones(len(u_c)), u_c, v_c, u_c ** 2, u_c * v_c, v_c ** 2])
            cq_o = np.linalg.lstsq(Aq_o.T @ Aq_o + 1e-3 * np.eye(6), Aq_o.T @ w_c, rcond=None)[0]
            w_detrend_iqr = float(np.percentile(w_c - (Aq_o @ cq_o), 85.0) - np.percentile(w_c - (Aq_o @ cq_o), 15.0))
        else:
            w_detrend_iqr = T_span
        above_rim = (support.regime == "NO_ENCLOSED_SUPPORT") or (float(ctr[2]) > float(support.rim_z) + 0.015)
        is_laminar = (
            (tier == "OUTER_ENCLOSED")
            and above_rim
            and (len(k_act) >= cfg.min_laminar_active_kernels)
            and (thk_ratio <= cfg.laminar_thickness_ratio_max)
            and (w_detrend_iqr <= 5.2 * p_med)
        )
        kind = "LAMINAR_BLADE" if is_laminar else "VOLUMETRIC_CLUSTER"
        if is_laminar:
            laminar_organ_ids.add(oid)

        organ_records.append({
            "organ_id": oid,
            "organ_kind": kind,
            "visibility_tier": tier,
            "active_kernel_count": int(len(k_act)),
            "centroid": ctr,
            "e1": e1, "e2": e2, "e3": e3,
            "length": L_span, "width": W_span, "thickness": T_span,
            "mean_vis_views": round(mean_vis, 2),
            "enclosed_kernel_frac": round(enc_frac, 3),
            "mean_rgb": cloud.rgb_dc[ref_k].mean(axis=0).astype(np.float32),
        })

    # Selective SH3-Preserving M2 Seam Split (ONLY for oversized wide Gaussians straddling two distinct LAMINAR_BLADEs!)
    refined_cloud, labels_ref, m12_stats = _apply_sh3_preserving_selective_m2(
        cloud, labels, laminar_organ_ids, organ_records, p_med
    )

    part_stats = {
        "total_build_2d_cells": total_2d_cells,
        "mean_build_2d_cells_per_view": round(total_2d_cells / max(len(train_views), 1), 2),
        "initial_3d_clusters_before_seam_merge": n_clusters_init,
        "curved_lamina_seam_merges": seam_merges,
        "num_3d_organs": n_organs,
        "num_laminar_blades": len(laminar_organ_ids),
        "num_volumetric_clusters": n_organs - len(laminar_organ_ids),
        "tier_counts": {
            t: sum(1 for r in organ_records if r["visibility_tier"] == t)
            for t in ("OUTER_ENCLOSED", "MID_PARTIAL_OCCLUDED", "DEEP_OCCLUDED")
        },
        "selective_m2_seam_refinement": m12_stats,
    }
    return refined_cloud, labels_ref, organ_records, train_cmaps, part_stats


def _build_cov6(scales: np.ndarray, quats_wxyz: np.ndarray) -> np.ndarray:
    q = quats_wxyz / np.maximum(np.linalg.norm(quats_wxyz, axis=1, keepdims=True), 1e-12)
    xyzw = np.column_stack([q[:, 1], q[:, 2], q[:, 3], q[:, 0]])
    Rm = Rotation.from_quat(xyzw).as_matrix()
    S2 = (scales ** 2)[:, None, :] * np.eye(3)[None, :, :]
    cov = Rm @ S2 @ np.transpose(Rm, (0, 2, 1))
    cov6 = np.zeros((len(scales), 6), dtype=np.float32)
    cov6[:, 0], cov6[:, 1], cov6[:, 2] = cov[:, 0, 0], cov[:, 0, 1], cov[:, 0, 2]
    cov6[:, 3], cov6[:, 4], cov6[:, 5] = cov[:, 1, 1], cov[:, 1, 2], cov[:, 2, 2]
    return cov6


def _apply_sh3_preserving_selective_m2(
    cloud: SceneGaussianCloud,
    labels: np.ndarray,
    laminar_ids: set[int],
    organ_records: list[dict[str, Any]],
    p_med: float,
) -> tuple[SceneGaussianCloud, np.ndarray, dict[str, int]]:
    """Split wide boundary-straddling laminar Gaussians while preserving EXACT SH3 appearance on all untouched rows!"""
    if len(laminar_ids) < 2:
        return cloud, labels, {"split_parents": 0, "reassigned_children": 0}

    lam_mask = np.isin(labels, list(laminar_ids)) & (cloud.opacities >= 0.035)
    lam_idx = np.flatnonzero(lam_mask)
    if len(lam_idx) < 20:
        return cloud, labels, {"split_parents": 0, "reassigned_children": 0}

    lam_pts = cloud.means[lam_idx].astype(np.float64)
    lam_lbl = labels[lam_idx]
    lam_tree = cKDTree(lam_pts)
    max_sc = cloud.scales[lam_idx].max(axis=1)
    wide_local = np.flatnonzero(max_sc >= 2.2 * p_med)
    if len(wide_local) == 0:
        return cloud, labels, {"split_parents": 0, "reassigned_children": 0}

    _, nbrs = lam_tree.query(lam_pts[wide_local], k=min(10, len(lam_pts)), distance_upper_bound=5.5 * p_med)
    if nbrs.ndim == 1:
        nbrs = nbrs[:, None]

    # Identify wide Gaussians that have a close neighbor belonging to a DIFFERENT laminar organ
    straddle_global: list[int] = []
    alt_organ: list[int] = []
    for pos, loc_i in enumerate(wide_local.tolist()):
        my_l = int(lam_lbl[loc_i])
        nb_row = nbrs[pos]
        valid_nb = nb_row[nb_row < len(lam_pts)]
        other = valid_nb[lam_lbl[valid_nb] != my_l]
        if len(other) > 0:
            g_idx = int(lam_idx[loc_i])
            if max_sc[loc_i] >= 0.65 * float(np.linalg.norm(lam_pts[int(other[0])] - lam_pts[loc_i])):
                straddle_global.append(g_idx)
                alt_organ.append(int(lam_lbl[int(other[0])]))

    if not straddle_global:
        return cloud, labels, {"split_parents": 0, "reassigned_children": 0}

    sp_idx = np.asarray(straddle_global, dtype=np.int32)
    keep_m = np.ones(len(cloud.means), dtype=bool)
    keep_m[sp_idx] = False

    # Split each straddling parent along its longest axis into 2 children preserving optical density & full SH3!
    q_sp = cloud.quats_wxyz[sp_idx]
    q_sp = q_sp / np.maximum(np.linalg.norm(q_sp, axis=1, keepdims=True), 1e-12)
    Rm = Rotation.from_quat(np.column_stack([q_sp[:, 1], q_sp[:, 2], q_sp[:, 3], q_sp[:, 0]])).as_matrix()
    sc_sp = cloud.scales[sp_idx].copy()
    ax_max = np.argmax(sc_sp, axis=1)
    rows = np.arange(len(sp_idx))
    v_long = Rm[rows, :, ax_max]
    s_long = sc_sp[rows, ax_max]

    shift = 0.45 * s_long[:, None] * v_long
    m_c1 = (cloud.means[sp_idx] - shift).astype(np.float32)
    m_c2 = (cloud.means[sp_idx] + shift).astype(np.float32)

    sc_child = sc_sp.copy()
    sc_child[rows, ax_max] *= 0.56
    op_child = (1.0 - np.power(np.clip(1.0 - cloud.opacities[sp_idx], 1e-5, 1.0), 0.72)).astype(np.float32)

    # Reassign child to nearest laminar organ centroid/core if closer to neighbor organ
    _, nn1 = lam_tree.query(m_c1.astype(np.float64), k=1)
    _, nn2 = lam_tree.query(m_c2.astype(np.float64), k=1)
    l_c1 = lam_lbl[nn1].astype(np.int32)
    l_c2 = lam_lbl[nn2].astype(np.int32)
    reassigned = int((l_c1 != labels[sp_idx]).sum() + (l_c2 != labels[sp_idx]).sum())

    means_new = np.vstack([cloud.means[keep_m], m_c1, m_c2]).astype(np.float32)
    scales_new = np.vstack([cloud.scales[keep_m], sc_child, sc_child]).astype(np.float32)
    quats_new = np.vstack([cloud.quats_wxyz[keep_m], q_sp, q_sp]).astype(np.float32)
    nrms_new = np.vstack([cloud.surfel_normals[keep_m], cloud.surfel_normals[sp_idx], cloud.surfel_normals[sp_idx]]).astype(np.float32)
    op_new = np.concatenate([cloud.opacities[keep_m], op_child, op_child]).astype(np.float32)
    rgb_new = np.vstack([cloud.rgb_dc[keep_m], cloud.rgb_dc[sp_idx], cloud.rgb_dc[sp_idx]]).astype(np.float32)
    shs_new = np.concatenate([cloud.shs[keep_m], cloud.shs[sp_idx], cloud.shs[sp_idx]], axis=0).astype(np.float32)
    lbl_new = np.concatenate([labels[keep_m], l_c1, l_c2]).astype(np.int32)

    cov_c = _build_cov6(np.vstack([sc_child, sc_child]), np.vstack([q_sp, q_sp]))
    cov6_new = np.vstack([cloud.cov6[keep_m], cov_c]).astype(np.float32)

    out_cloud = SceneGaussianCloud(
        means=means_new, scales=scales_new, quats_wxyz=quats_new, cov6=cov6_new,
        surfel_normals=nrms_new, opacities=op_new, rgb_dc=rgb_new, shs=shs_new,
    )
    return out_cloud, lbl_new, {"split_parents": int(len(sp_idx)), "reassigned_children": reassigned}
