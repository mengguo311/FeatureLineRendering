"""Layer 3: Self-Similarity Eigen-Leaf PCA Prior, Multi-View Dual-Arc B-Spline Optimization & Shadow-Zone Completion.

Implements:
  1. Anatomical Petiole-to-Apex Frame Extraction (orienting e1 away from wood stems).
  2. Initial Dual-Arc Pointed-Tip Cubic B-Spline fitting (fusing M1+M2 leaf Gaussians + v05 3D leaf-rim curves).
  3. Eigen-Leaf PCA Shape Space learning from the 264 high-confidence OUTER_ENCLOSED leaves.
  4. Multi-View C2L50 Edge Distance-Field Refinement + Eigen-Leaf Regularization / Amodal Spline Completion
     for the 208 MID_PARTIAL_OCCLUDED and DEEP_OCCLUDED inner-canopy leaves.
  5. Occlusion-Consistent Shadow-Zone Gaussian Infill (strictly behind training front_depth!) + Rim Tangent Alignment.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import torch
from scipy.interpolate import BSpline
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from .schema_and_io import (
    LABEL_WOOD_SKELETON,
    BotanicalTreeGraph,
    CalibratedSceneView,
    DualArcTrimmedLeafPatch,
    EigenLeafPriorModel,
    GaussianCloudBank,
    build_cloud_bank,
    clamped_cubic_knots,
    eval_clamped_bspline,
)


def compute_anatomical_leaf_frames(
    cloud: GaussianCloudBank,
    leaf_meta_list: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract oriented right-handed frames (p_base, e1, e2, e3, L_init) for all 472 leaves."""
    wood_m = (cloud.kernel_labels == LABEL_WOOD_SKELETON) & (cloud.opacities >= 0.03)
    wood_pts = cloud.means[wood_m].astype(np.float64)
    wood_tree = cKDTree(wood_pts) if len(wood_pts) > 0 else None

    frames: list[dict[str, Any]] = []
    means64 = cloud.means.astype(np.float64)

    for entry in leaf_meta_list:
        lid = int(entry["leaf_id"])
        k_idx = np.where(cloud.kernel_labels == lid)[0].astype(np.int32)
        act_k = k_idx[cloud.opacities[k_idx] >= 0.025]
        ref_k = act_k if len(act_k) >= 4 else k_idx
        pts = means64[ref_k]
        sc = cloud.scales[ref_k].astype(np.float64)

        ctr = pts.mean(axis=0)
        rel = pts - ctr[None, :]
        cov = (rel.T @ rel) / max(len(pts), 1)
        _, evecs = np.linalg.eigh(cov)
        e3 = evecs[:, 0]
        e2 = evecs[:, 1]
        e1 = evecs[:, 2]
        if e3[2] < 0.0:
            e3 = -e3
        if float(np.dot(np.cross(e1, e2), e3)) < 0.0:
            e2 = -e2

        u_raw = rel @ e1
        pad = float(np.median(sc.max(axis=1))) * 1.10 if len(sc) > 0 else 0.0035
        u_lo = float(np.percentile(u_raw, 2.5)) - pad
        u_hi = float(np.percentile(u_raw, 97.5)) + pad

        p_pos_end = ctr + u_hi * e1
        p_neg_end = ctr + u_lo * e1

        # Orient e1 strictly from petiole attachment (near wood stem) -> distal leaf apex!
        flip = False
        if wood_tree is not None:
            d_pos, _ = wood_tree.query(p_pos_end, k=1)
            d_neg, _ = wood_tree.query(p_neg_end, k=1)
            if float(d_pos) + 0.0025 < float(d_neg):
                flip = True
            elif abs(float(d_pos) - float(d_neg)) <= 0.0025:
                if np.linalg.norm(p_pos_end[:2]) < np.linalg.norm(p_neg_end[:2]):
                    flip = True
        elif np.linalg.norm(p_pos_end[:2]) < np.linalg.norm(p_neg_end[:2]):
            flip = True

        if flip:
            e1 = -e1
            e2 = -e2
            u_raw = -u_raw
            u_lo = float(np.percentile(u_raw, 2.5)) - pad
            u_hi = float(np.percentile(u_raw, 97.5)) + pad

        p_base = ctr + u_lo * e1
        L_init = max(u_hi - u_lo, 0.018)
        frames.append({
            "leaf_id": lid,
            "visibility_tier": str(entry["visibility_tier"]),
            "p_base": p_base,
            "e1": e1,
            "e2": e2,
            "e3": e3,
            "L_init": L_init,
            "pad": pad,
            "kernel_indices": k_idx,
            "ref_indices": ref_k,
        })
    return frames


def _fit_single_dual_arc_ctrl6(s_pts: np.ndarray, v_pos_pts: np.ndarray, weights: np.ndarray, L_val: float) -> np.ndarray:
    """Fit 4 interior positive control weights of a 6-point clamped cubic B-spline [0, c1, c2, c3, c4, 0]."""
    # Sample 8 envelope bins along s in (0.05, 0.95) so interior points don't drag boundary inward!
    bins = np.linspace(0.04, 0.96, 9)
    s_env = []
    v_env = []
    w_env = []
    for b_i in range(len(bins) - 1):
        in_b = (s_pts >= bins[b_i]) & (s_pts < bins[b_i + 1])
        if int(in_b.sum()) >= 2:
            s_env.append(0.5 * (bins[b_i] + bins[b_i + 1]))
            # 93rd percentile captures exact outer margin!
            v_sub = v_pos_pts[in_b]
            w_sub = weights[in_b]
            # Boost points coming from v05 3D rim curves (weight > 1.5)
            has_rim = w_sub > 1.5
            if int(has_rim.sum()) >= 2:
                v_val = float(np.percentile(v_sub[has_rim], 68.0))
                w_val = 2.5
            else:
                v_val = float(np.percentile(v_sub, 86.0))
                w_val = 1.0
            v_env.append(v_val)
            w_env.append(w_val)

    # Default sleek pointed-tip lanceolate ratio fallback if sparse
    default_q = np.array([0.055, 0.175, 0.165, 0.048], dtype=np.float64) * L_val
    if len(s_env) < 3:
        return np.concatenate([[0.0], default_q, [0.0]])

    s_arr = np.array(s_env, dtype=np.float64)
    v_arr = np.array(v_env, dtype=np.float64)
    w_arr = np.sqrt(np.array(w_env, dtype=np.float64))

    knots = clamped_cubic_knots(6)
    B_full = BSpline(knots, np.eye(6, dtype=np.float64), 3)(s_arr)
    B_in = B_full[:, 1:5] * w_arr[:, None]
    rhs = v_arr * w_arr

    # Tikhonov smoothness toward pointed lanceolate prior + unimodal botanical taper (prevents blunt/peanut tips!)
    reg_mat = 0.35 * np.eye(4, dtype=np.float64)
    reg_rhs = 0.35 * default_q
    A = np.vstack([B_in, reg_mat])
    b = np.concatenate([rhs, reg_rhs])
    c_in = np.linalg.lstsq(A, b, rcond=None)[0]
    c_in[1] = float(np.clip(c_in[1], 0.08 * L_val, 0.25 * L_val))
    c_in[2] = float(np.clip(c_in[2], 0.08 * L_val, 0.24 * L_val))
    # Enforce cuneate petiole base (c1 <= 0.46 * c2) and pointed acuminate leaf apex (c4 <= 0.42 * c3)!
    c_in[0] = float(np.clip(c_in[0], 0.025 * L_val, 0.46 * c_in[1]))
    c_in[3] = float(np.clip(c_in[3], 0.022 * L_val, 0.42 * c_in[2]))
    return np.concatenate([[0.0], c_in, [0.0]])


def fit_eigen_leaf_dual_arc_patches_and_complete(
    cloud: GaussianCloudBank,
    skeleton: BotanicalTreeGraph,
    leaf_frames: list[dict[str, Any]],
    rim_points: np.ndarray,
    train_views: list[CalibratedSceneView],
    p_med: float,
    device: torch.device,
) -> tuple[list[DualArcTrimmedLeafPatch], EigenLeafPriorModel, GaussianCloudBank, dict[str, Any]]:
    """Fit Dual-Arc Cubic B-Splines, learn Eigen-Leaf PCA prior, refine on C2L50 views, and infill occluded shadow zones."""
    means64 = cloud.means.astype(np.float64)
    rim_tree = cKDTree(rim_points) if len(rim_points) > 0 else None

    # -----------------------------------------------------------------------
    # Stage 3A: Initial Dual-Arc B-Spline + Camber Fit (Gaussians + v05 3D Rim Snapping)
    # -----------------------------------------------------------------------
    raw_fits: list[dict[str, Any]] = []
    for lf in leaf_frames:
        ref_k = lf["ref_indices"]
        p_base = lf["p_base"]
        e1, e2, e3 = lf["e1"], lf["e2"], lf["e3"]
        L_val = lf["L_init"]
        pad = lf["pad"]

        rel_g = means64[ref_k] - p_base[None, :]
        ug = rel_g @ e1
        vg = rel_g @ e2
        wg = rel_g @ e3

        # Fit quadratic leaf camber w(u, v) = c0 + c1*u + c2*u^2 + c3*v^2 anchored near w(0,0) ~ 0
        if len(ug) >= 8:
            A_c = np.column_stack([np.ones(len(ug)), ug, ug ** 2, vg ** 2])
            P_reg = np.diag([2.0, 0.2, 0.05, 0.05])
            cam_coef = np.linalg.lstsq(A_c.T @ A_c + P_reg, A_c.T @ wg, rcond=None)[0]
        else:
            cam_coef = np.zeros(4, dtype=np.float64)

        # Query nearby coplanar v05 3D leaf-rim curve samples within 1.1 cm!
        s_all = np.clip(ug / L_val, 0.0, 1.0)
        v_all = vg + np.sign(np.where(vg == 0, 1.0, vg)) * (0.22 * pad)
        w_all = np.ones(len(ug), dtype=np.float64)

        if rim_tree is not None:
            leaf_ctr = p_base + 0.5 * L_val * e1
            near_r = rim_tree.query_ball_point(leaf_ctr, r=0.65 * L_val)
            if near_r:
                r_pts = rim_points[near_r] - p_base[None, :]
                ur = r_pts @ e1
                vr = r_pts @ e2
                wr = r_pts @ e3
                w_pred = cam_coef[0] + cam_coef[1] * ur + cam_coef[2] * (ur ** 2) + cam_coef[3] * (vr ** 2)
                coplanar_r = (
                    (ur >= -0.004)
                    & (ur <= L_val + 0.006)
                    & (np.abs(vr) <= 0.45 * L_val)
                    & (np.abs(wr - w_pred) <= 0.0075)
                )
                if int(coplanar_r.sum()) >= 3:
                    s_r = np.clip(ur[coplanar_r] / L_val, 0.0, 1.0)
                    v_r = vr[coplanar_r]
                    s_all = np.concatenate([s_all, s_r])
                    v_all = np.concatenate([v_all, v_r])
                    w_all = np.concatenate([w_all, np.full(len(s_r), 2.6)])

        left_m = v_all >= 0.0
        right_m = v_all <= 0.0
        vl_ctrl = _fit_single_dual_arc_ctrl6(s_all[left_m], v_all[left_m], w_all[left_m], L_val)
        vr_pos_ctrl = _fit_single_dual_arc_ctrl6(s_all[right_m], -v_all[right_m], w_all[right_m], L_val)

        raw_fits.append({
            "L": L_val,
            "vl_ctrl": vl_ctrl,
            "vr_ctrl": -vr_pos_ctrl,
            "camber": cam_coef,
        })

    # -----------------------------------------------------------------------
    # Stage 3B: Learn Self-Similarity Eigen-Leaf PCA Prior from 264 OUTER_ENCLOSED Leaves!
    # -----------------------------------------------------------------------
    outer_q8 = []
    outer_lengths = []
    outer_wratios = []
    outer_cambers = []
    for lf, rf in zip(leaf_frames, raw_fits):
        if lf["visibility_tier"] == "OUTER_ENCLOSED":
            L_v = rf["L"]
            q_vec = np.concatenate([rf["vl_ctrl"][1:5] / L_v, -rf["vr_ctrl"][1:5] / L_v])
            w_rat = float((rf["vl_ctrl"].max() - rf["vr_ctrl"].min()) / max(L_v, 1e-4))
            if 0.22 <= w_rat <= 0.78 and 0.035 <= L_v <= 0.18:
                outer_q8.append(q_vec)
                outer_lengths.append(L_v)
                outer_wratios.append(w_rat)
                outer_cambers.append(rf["camber"])

    if len(outer_q8) >= 6:
        Q_mat = np.array(outer_q8, dtype=np.float64)
        mean_q8 = Q_mat.mean(axis=0)
        Q_centered = Q_mat - mean_q8[None, :]
        _, s_svd, vt_svd = np.linalg.svd(Q_centered, full_matrices=False)
        pca_comp = vt_svd[:3]
        pca_std = s_svd[:3] / math.sqrt(max(len(Q_mat) - 1, 1))
        med_len = float(np.median(outer_lengths))
        med_wrat = float(np.median(outer_wratios))
        med_cam = np.median(np.array(outer_cambers), axis=0)
    else:
        mean_q8 = np.array([0.16, 0.26, 0.24, 0.13, 0.16, 0.26, 0.24, 0.13], dtype=np.float64)
        pca_comp = np.eye(3, 8, dtype=np.float64)
        pca_std = np.full(3, 0.03, dtype=np.float64)
        med_len = 0.105
        med_wrat = 0.46
        med_cam = np.zeros(4, dtype=np.float64)

    eigen_prior = EigenLeafPriorModel(
        mean_norm_ctrl8=mean_q8,
        pca_components=pca_comp,
        pca_std=pca_std,
        median_length=med_len,
        median_width_ratio=med_wrat,
        median_camber=med_cam,
    )

    # -----------------------------------------------------------------------
    # Stage 3C: Eigen-Leaf Projection (Amodal Completion for Occluded Leaves) + Multi-View C2L50 Edge Refinement!
    # -----------------------------------------------------------------------
    # Select 12 well-spread training views for fast vectorized multi-view C2L50 edge snapping of OUTER leaves
    ref_views = train_views[:: max(1, len(train_views) // 12)][:12]
    s_eval20 = np.linspace(0.08, 0.96, 18, dtype=np.float64)
    B_eval20 = BSpline(clamped_cubic_knots(6), np.eye(6, dtype=np.float64), 3)(s_eval20)

    refined_fits: list[dict[str, Any]] = []
    amodal_expanded_leaves = 0

    for lf, rf in zip(leaf_frames, raw_fits):
        tier = lf["visibility_tier"]
        L_v = rf["L"]
        q_raw = np.concatenate([rf["vl_ctrl"][1:5] / L_v, -rf["vr_ctrl"][1:5] / L_v])

        # Project onto 3D Eigen-Leaf PCA space!
        z_pca = pca_comp @ (q_raw - mean_q8)
        z_clamped = np.clip(z_pca, -2.2 * pca_std, 2.2 * pca_std)
        q_prior = np.clip(mean_q8 + pca_comp.T @ z_clamped, 0.05, 0.42)

        if tier == "OUTER_ENCLOSED":
            # Blend 75% empirical fit + 25% Eigen-Leaf prior, then refine scale against multi-view C2L50 edge_dt!
            q_init = 0.75 * q_raw + 0.25 * q_prior
            best_L = L_v
            best_w_scale = 1.0
            best_cost = 1e9

            p_base = lf["p_base"]
            e1, e2, e3 = lf["e1"], lf["e2"], lf["e3"]
            cam = rf["camber"]

            # 5x5 grid search around (L_scale in [0.95..1.06], W_scale in [0.92..1.08]) on multi-view C2L50 edge_dt!
            for l_sc in (0.96, 1.00, 1.04):
                L_cand = L_v * l_sc
                u_s = s_eval20 * L_cand
                for w_sc in (0.93, 0.98, 1.02, 1.07):
                    q_c = q_init * w_sc
                    vl_s = (B_eval20[:, 1:5] @ q_c[:4]) * L_cand
                    vr_s = -(B_eval20[:, 1:5] @ q_c[4:]) * L_cand
                    wl_s = cam[0] + cam[1] * u_s + cam[2] * (u_s ** 2) + cam[3] * (vl_s ** 2)
                    wr_s = cam[0] + cam[1] * u_s + cam[2] * (u_s ** 2) + cam[3] * (vr_s ** 2)
                    pts_3d = np.vstack([
                        p_base + u_s[:, None] * e1 + vl_s[:, None] * e2 + wl_s[:, None] * e3,
                        p_base + u_s[:, None] * e1 + vr_s[:, None] * e2 + wr_s[:, None] * e3,
                    ])

                    tot_edt = 0.0
                    n_vis = 0
                    for vw in ref_views:
                        Xc = pts_3d @ vw.w2c[:3, :3].T + vw.w2c[:3, 3]
                        zc = Xc[:, 2]
                        ok = zc > 0.2
                        if not np.any(ok):
                            continue
                        us = np.round(vw.fx * (Xc[ok, 0] / zc[ok]) + vw.cx).astype(np.int32)
                        vs = np.round(vw.fy * (Xc[ok, 1] / zc[ok]) + vw.cy).astype(np.int32)
                        in_b = (us >= 0) & (us < vw.width) & (vs >= 0) & (vs < vw.height)
                        if not np.any(in_b):
                            continue
                        us, vs, z_sub = us[in_b], vs[in_b], zc[ok][in_b]
                        vis_m = z_sub <= vw.front_depth[vs, us] + 3.2 * p_med
                        if np.any(vis_m):
                            edt_vals = vw.edge_dt[vs[vis_m], us[vis_m]]
                            out_pen = np.where(vw.alpha[vs[vis_m], us[vis_m]] < 0.25, 6.0, 0.0)
                            tot_edt += float(np.sum(edt_vals + out_pen))
                            n_vis += int(vis_m.sum())

                    reg_pen = 0.35 * ((l_sc - 1.0) ** 2 + (w_sc - 1.0) ** 2) * 10.0
                    c_score = (tot_edt / n_vis + reg_pen) if n_vis >= 8 else (2.5 + reg_pen)
                    if c_score < best_cost:
                        best_cost = c_score
                        best_L = L_cand
                        best_w_scale = w_sc

            q_final = np.clip(q_init * best_w_scale, 0.022, 0.28)
            q_final[0] = min(q_final[0], 0.46 * q_final[1])
            q_final[3] = min(q_final[3], 0.42 * q_final[2])
            q_final[4] = min(q_final[4], 0.46 * q_final[5])
            q_final[7] = min(q_final[7], 0.42 * q_final[6])
            cam_final = rf["camber"]
        else:
            # Amodal Botanical Completion for MID_PARTIAL_OCCLUDED & DEEP_OCCLUDED inner leaves!
            obs_width = float(rf["vl_ctrl"].max() - rf["vr_ctrl"].min())
            implied_L = obs_width / max(med_wrat, 0.28)
            target_L = float(np.clip(max(L_v, 0.45 * implied_L + 0.50 * med_len), 0.075, 1.12 * med_len))
            if target_L > L_v * 1.05:
                amodal_expanded_leaves += 1
            best_L = target_L
            q_final = 0.25 * q_raw + 0.75 * q_prior if tier == "MID_PARTIAL_OCCLUDED" else q_prior
            q_final[0] = min(q_final[0], 0.46 * q_final[1])
            q_final[3] = min(q_final[3], 0.42 * q_final[2])
            q_final[4] = min(q_final[4], 0.46 * q_final[5])
            q_final[7] = min(q_final[7], 0.42 * q_final[6])
            z_clamped = pca_comp @ (q_final - mean_q8)
            cam_final = 0.5 * rf["camber"] + 0.5 * med_cam

        vl_f = np.concatenate([[0.0], q_final[:4] * best_L, [0.0]])
        vr_f = np.concatenate([[0.0], -q_final[4:] * best_L, [0.0]])
        refined_fits.append({
            "L": best_L,
            "vl_ctrl": vl_f,
            "vr_ctrl": vr_f,
            "camber": cam_final,
            "pca_code": z_clamped,
        })

    # -----------------------------------------------------------------------
    # Stage 3D: Shadow-Zone Amodal Gaussian Infill (Strictly Behind Training front_depth!)
    #           + Object-Space Rim Tangent Alignment & Clipping!
    # -----------------------------------------------------------------------
    new_means = cloud.means.copy()
    new_scales = cloud.scales.copy()
    new_quats = cloud.quats_wxyz.copy()
    new_opac = cloud.opacities.copy()
    new_rgb = cloud.rgb.copy()
    new_lbls = cloud.kernel_labels.copy()

    # Collect candidate infill surfels across all 208 occluded leaves first, then batch-verify shadow-zone occlusion on GPU!
    cand_pts: list[np.ndarray] = []
    cand_lids: list[int] = []
    cand_rgb: list[np.ndarray] = []
    cand_quats: list[np.ndarray] = []
    cand_scales: list[np.ndarray] = []

    knots6 = clamped_cubic_knots(6)
    for lf, rf in zip(leaf_frames, refined_fits):
        lid = lf["leaf_id"]
        k_idx = lf["kernel_indices"]
        p_base = lf["p_base"]
        e1, e2, e3 = lf["e1"], lf["e2"], lf["e3"]
        L_b = rf["L"]
        vl_c = rf["vl_ctrl"]
        vr_c = rf["vr_ctrl"]
        cam = rf["camber"]

        spl_l = BSpline(knots6, vl_c, 3)
        spl_r = BSpline(knots6, vr_c, 3)

        # 1. Trim & tangent-align existing kernels of leaf `lid` to strictly conform to [vr(s), vl(s)]!
        pts_k = new_means[k_idx].astype(np.float64)
        rel_k = pts_k - p_base[None, :]
        uk = rel_k @ e1
        vk = rel_k @ e2
        wk = rel_k @ e3

        # Clamp longitudinal u inside [0.005*L, 0.995*L] and only tuck genuinely overhanging kernels (> 1.02 * spline)
        uk_clamped = np.clip(uk, 0.005 * L_b, 0.995 * L_b)
        sk = uk_clamped / L_b
        vl_bound = spl_l(sk)
        vr_bound = spl_r(sk)
        over_l = vk > 1.02 * vl_bound
        over_r = vk < 1.02 * vr_bound
        vk_clamped = np.where(over_l, 0.96 * vl_bound, np.where(over_r, 0.96 * vr_bound, vk))
        need_move = (uk != uk_clamped) | over_l | over_r

        if np.any(need_move):
            wk_surf = cam[0] + cam[1] * uk_clamped + cam[2] * (uk_clamped ** 2) + cam[3] * (vk_clamped ** 2)
            wk_new = np.where(need_move, wk_surf, wk)
            pts_moved = p_base[None, :] + uk_clamped[:, None] * e1 + vk_clamped[:, None] * e2 + wk_new[:, None] * e3
            new_means[k_idx[need_move]] = pts_moved[need_move].astype(np.float32)

            # Align rim kernel major axis tangent to the cubic B-spline margin & shrink transverse overhang!
            dv_ds = np.where(over_l, spl_l.derivative(1)(sk), spl_r.derivative(1)(sk))
            rim_sub = np.where(over_l | over_r)[0]
            if len(rim_sub) > 0:
                tng_3d = e1[None, :] + (dv_ds[rim_sub] / max(L_b, 1e-4))[:, None] * e2[None, :]
                tng_3d /= np.maximum(np.linalg.norm(tng_3d, axis=1, keepdims=True), 1e-9)
                lat_3d = np.cross(e3[None, :], tng_3d)
                lat_3d /= np.maximum(np.linalg.norm(lat_3d, axis=1, keepdims=True), 1e-9)
                R_rim = np.stack([tng_3d, lat_3d, np.broadcast_to(e3, tng_3d.shape)], axis=2)
                q_xyzw = Rotation.from_matrix(R_rim).as_quat()
                q_wxyz = np.column_stack([q_xyzw[:, 3], q_xyzw[:, 0], q_xyzw[:, 1], q_xyzw[:, 2]]).astype(np.float32)
                glob_rim = k_idx[rim_sub]
                max_s = np.minimum(new_scales[glob_rim].max(axis=1), float(2.1 * p_med))
                local_hw = np.maximum(0.28 * (vl_bound[rim_sub] - vr_bound[rim_sub]), 0.0012).astype(np.float32)
                new_quats[glob_rim] = q_wxyz
                new_scales[glob_rim] = np.column_stack([
                    max_s,
                    np.minimum(max_s * 0.52, local_hw),
                    np.full(len(rim_sub), 1e-4, dtype=np.float32),
                ])

        # 2. Generate candidate amodal infill surfels in empty holes of occluded leaves!
        if lf["visibility_tier"] != "OUTER_ENCLOSED":
            act_local = new_means[k_idx[new_opac[k_idx] >= 0.04]].astype(np.float64)
            loc_tree = cKDTree(act_local) if len(act_local) > 0 else None
            leaf_med_rgb = np.median(new_rgb[k_idx], axis=0).astype(np.float32)

            R_blade = np.column_stack([e1, e2, e3])
            if np.linalg.det(R_blade) < 0:
                R_blade[:, 1] *= -1.0
            qb_xyzw = Rotation.from_matrix(R_blade).as_quat()
            qb_wxyz = np.array([qb_xyzw[3], qb_xyzw[0], qb_xyzw[1], qb_xyzw[2]], dtype=np.float32)

            s_grid = np.linspace(0.08, 0.93, 14)
            for s_g in s_grid:
                vl_g = float(spl_l(s_g))
                vr_g = float(spl_r(s_g))
                span_w = vl_g - vr_g
                if span_w < 0.004:
                    continue
                n_lat = max(2, int(round(span_w / (1.8 * p_med))))
                v_vals = np.linspace(vr_g * 0.84, vl_g * 0.84, n_lat)
                u_g = s_g * L_b
                for v_g in v_vals:
                    w_g = cam[0] + cam[1] * u_g + cam[2] * (u_g ** 2) + cam[3] * (v_g ** 2)
                    pt_c = p_base + u_g * e1 + v_g * e2 + w_g * e3
                    if loc_tree is not None:
                        d_ex, _ = loc_tree.query(pt_c, k=1)
                        if float(d_ex) < 1.65 * p_med:
                            continue
                    cand_pts.append(pt_c)
                    cand_lids.append(lid)
                    # Gentle natural shading gradient from base to apex
                    shade_g = float(0.88 + 0.22 * s_g)
                    cand_rgb.append(np.clip(leaf_med_rgb * shade_g, 0.0, 1.0))
                    cand_quats.append(qb_wxyz)
                    cand_scales.append(np.array([1.45 * p_med, 1.15 * p_med, 1e-4], dtype=np.float32))

    # Verify Shadow-Zone Consistency on GPU across all 32 training views!
    # Keep candidate surfel iff in >= 80% of training views where it projects inside frustum,
    # it lies behind the observed foreground surface (z_cam >= front_depth - 1.5 * p_med) AND inside visual hull!
    infilled_per_leaf = np.zeros(len(leaf_frames), dtype=np.int32)
    total_infilled_foliage = 0

    # Snapshot rim-trimmed cloud BEFORE amodal shadow-zone infill for exact controlled pruning comparison!
    cloud_trimmed_no_infill = build_cloud_bank(new_means, new_scales, new_quats, new_opac, new_rgb, new_lbls)

    if len(cand_pts) > 0:
        pts_c_arr = np.array(cand_pts, dtype=np.float32)
        with torch.cuda.device(device):
            X_t = torch.tensor(pts_c_arr, dtype=torch.float32, device=device)
            in_frustum_cnt = torch.zeros(len(pts_c_arr), dtype=torch.int32, device=device)
            shadow_occluded_cnt = torch.zeros(len(pts_c_arr), dtype=torch.int32, device=device)
            freespace_viol_cnt = torch.zeros(len(pts_c_arr), dtype=torch.int32, device=device)
            outside_hull_cnt = torch.zeros(len(pts_c_arr), dtype=torch.int32, device=device)

            for vw in train_views:
                R_t = torch.tensor(vw.w2c[:3, :3], dtype=torch.float32, device=device)
                t_t = torch.tensor(vw.w2c[:3, 3], dtype=torch.float32, device=device)
                Xc = X_t @ R_t.T + t_t[None, :]
                zc = Xc[:, 2]
                us = torch.round(float(vw.fx) * (Xc[:, 0] / zc.clamp(min=0.1)) + float(vw.cx)).long()
                vs = torch.round(float(vw.fy) * (Xc[:, 1] / zc.clamp(min=0.1)) + float(vw.cy)).long()
                in_b = (zc > 0.2) & (us >= 0) & (us < vw.width) & (vs >= 0) & (vs < vw.height)
                idx_b = torch.where(in_b)[0]
                if len(idx_b) == 0:
                    continue

                fd_t = torch.tensor(vw.front_depth, dtype=torch.float32, device=device)
                al_t = torch.tensor(vw.alpha, dtype=torch.float32, device=device)
                ub, vb, zb = us[idx_b], vs[idx_b], zc[idx_b]

                in_frustum_cnt[idx_b] += 1
                outside_sky = al_t[vb, ub] < 0.42
                outside_hull_cnt[idx_b[outside_sky]] += 1
                # Space-carving: must NOT step in front of observed front_depth by > 2.2 * p_med!
                viol = (~outside_sky) & (fd_t[vb, ub] > 0.2) & (zb < fd_t[vb, ub] - 2.2 * p_med)
                freespace_viol_cnt[idx_b[viol]] += 1
                # Genuine occluded shadow support: behind a foreground leaf in at least several views
                occ = (~outside_sky) & (zb >= fd_t[vb, ub] + 1.5 * p_med)
                shadow_occluded_cnt[idx_b[occ]] += 1

            keep_cand = (
                (in_frustum_cnt >= 6)
                & (outside_hull_cnt == 0)
                & (freespace_viol_cnt <= 1)
                & (shadow_occluded_cnt >= 4)
            ).cpu().numpy()

        kept_idx = np.where(keep_cand)[0]
        total_infilled_foliage = len(kept_idx)
        if total_infilled_foliage > 0:
            c_lids_kept = np.array(cand_lids, dtype=np.int32)[kept_idx]
            for kl in c_lids_kept:
                infilled_per_leaf[kl] += 1

            new_means = np.concatenate([new_means, pts_c_arr[kept_idx]], axis=0)
            new_scales = np.concatenate([new_scales, np.array(cand_scales, dtype=np.float32)[kept_idx]], axis=0)
            new_quats = np.concatenate([new_quats, np.array(cand_quats, dtype=np.float32)[kept_idx]], axis=0)
            new_opac = np.concatenate([new_opac, np.full(total_infilled_foliage, 0.58, dtype=np.float32)], axis=0)
            new_rgb = np.concatenate([new_rgb, np.array(cand_rgb, dtype=np.float32)[kept_idx]], axis=0)
            new_lbls = np.concatenate([new_lbls, c_lids_kept], axis=0)

    cloud_completed = build_cloud_bank(new_means, new_scales, new_quats, new_opac, new_rgb, new_lbls)

    # Assemble final 472 DualArcTrimmedLeafPatch records!
    s_quad = np.linspace(0.0, 1.0, 64)
    patches: list[DualArcTrimmedLeafPatch] = []
    for lf, rf in zip(leaf_frames, refined_fits):
        lid = lf["leaf_id"]
        k_final = np.where(cloud_completed.kernel_labels == lid)[0].astype(np.int32)
        vl_q, _ = eval_clamped_bspline(rf["vl_ctrl"][:, None], s_quad)
        vr_q, _ = eval_clamped_bspline(rf["vr_ctrl"][:, None], s_quad)
        area_m2 = float(np.trapz(np.maximum(vl_q[:, 0] - vr_q[:, 0], 0.0), s_quad * rf["L"]))

        patches.append(
            DualArcTrimmedLeafPatch(
                leaf_id=lid,
                parent_branch_id=int(skeleton.leaf_to_petiole_branch[lid]),
                hub_id=int(skeleton.leaf_to_hub_id[lid]),
                visibility_tier=lf["visibility_tier"],
                p_base=lf["p_base"],
                e1=lf["e1"],
                e2=lf["e2"],
                e3=lf["e3"],
                blade_length=float(rf["L"]),
                v_left_ctrl=rf["vl_ctrl"],
                v_right_ctrl=rf["vr_ctrl"],
                camber_coef=rf["camber"],
                eigen_pca_code=rf["pca_code"],
                kernel_indices=k_final,
                infilled_kernel_count=int(infilled_per_leaf[lid]),
                area_cm2=round(area_m2 * 1e4, 2),
            )
        )

    stats = {
        "num_dual_arc_leaf_patches": len(patches),
        "eigen_leaf_pca_singular_stds": [round(float(x), 4) for x in pca_std],
        "eigen_leaf_median_length_cm": round(100.0 * med_len, 2),
        "eigen_leaf_median_width_ratio": round(med_wrat, 3),
        "occluded_leaves_amodally_expanded": int(amodal_expanded_leaves),
        "shadow_zone_infilled_foliage_kernels": int(total_infilled_foliage),
        "total_canopy_leaf_area_m2": round(sum(p.area_cm2 for p in patches) * 1e-4, 4),
    }
    return patches, eigen_prior, cloud_completed, cloud_trimmed_no_infill, stats
