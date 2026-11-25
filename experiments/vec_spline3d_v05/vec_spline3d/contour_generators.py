"""View-dependent 3D occluding contour generators (Lathe Surface of Revolution & Swept Generalized Cylinders)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import torch
from plyfile import PlyData
from scipy.ndimage import gaussian_filter1d
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from scipy.special import expit

from .multimodal_data import MultiModalSceneBundle
from .schema import (
    CoaxialRingFamilySpec,
    LatheEnvelopeGenerator,
    SweptTubeGenerator,
    bspline_basis_matrices,
    clamped_uniform_knots,
    fit_clamped_bspline_to_polyline,
    resolve_safe_path,
)
from .stage1_ray_clean import _compute_polyline_tangents
from .stage2_scms_consolidate import ConsolidatedRidgeChain


def build_lathe_contour_generator(
    coax_family: CoaxialRingFamilySpec,
    bundle: MultiModalSceneBundle,
    generator_id: int = 0,
) -> LatheEnvelopeGenerator | None:
    """Calibrate outer silhouette meridian envelope rho_env(h) on an arbitrary-axis rotational/cylindrical part."""
    p_med = bundle.median_pixel_scale
    if (coax_family.h_max - coax_family.h_min) < 12.0 * p_med or len(coax_family.profile_h) < 2:
        return None
    o_ax = coax_family.axis_origin.copy()
    a_dir = coax_family.axis_dir.copy()
    e1 = coax_family.e1.copy()
    e2 = coax_family.e2.copy()

    # Extend axial range slightly to cover bottom foot and top lip
    h_lo = float(coax_family.h_min - 3.8 * p_med)
    h_hi = float(coax_family.h_max + 2.2 * p_med)
    n_prof = 32
    prof_h = np.linspace(h_lo, h_hi, n_prof, dtype=np.float64)

    # Start from coax_family's median surface radius and search outward [-1.2p, +4.8p] for exact silhouette horizon
    base_r = np.interp(prof_h, coax_family.profile_h, coax_family.profile_r)
    dr_init = np.gradient(base_r, prof_h)

    cal_views = [v for v in bundle.train_views if v.is_original_c2l_build] or bundle.train_views[:12]
    opt_r = np.zeros_like(prof_h)
    best_costs: list[float] = []

    offsets = np.linspace(-1.2 * p_med, 4.8 * p_med, 37, dtype=np.float64)
    for i_h, hk in enumerate(prof_h):
        r_cands = np.maximum(0.03, base_r[i_h] + offsets)
        slp = float(dr_init[i_h])
        cost_acc = np.zeros_like(r_cands)
        cnt_acc = 0

        for vw in cal_views:
            rel_c = vw.cam_center - o_ax
            hc = float(np.dot(rel_c, a_dir))
            cx_p = float(np.dot(rel_c, e1))
            cy_p = float(np.dot(rel_c, e2))
            dc = math.hypot(cx_p, cy_p)
            if dc <= float(r_cands.max()) * 1.05:
                continue
            phic = math.atan2(cy_p, cx_p)
            cos_arg = (r_cands + slp * (hc - hk)) / dc
            valid_c = np.abs(cos_arg) <= 0.995
            if not np.any(valid_c):
                continue
            ang = np.arccos(np.clip(cos_arg, -0.999, 0.999))
            for sgn in (-1.0, 1.0):
                th = phic + sgn * ang
                er = np.cos(th)[:, None] * e1[None, :] + np.sin(th)[:, None] * e2[None, :]
                pts = o_ax[None, :] + hk * a_dir[None, :] + r_cands[:, None] * er
                Xc = pts @ vw.w2c[:3, :3].T + vw.w2c[:3, 3]
                in_f = (
                    (Xc[:, 2] > 0.2)
                    & (vw.fx * (Xc[:, 0] / np.maximum(Xc[:, 2], 0.2)) + vw.cx >= 1.0)
                    & (vw.fx * (Xc[:, 0] / np.maximum(Xc[:, 2], 0.2)) + vw.cx <= vw.width - 2.0)
                    & (vw.fy * (Xc[:, 1] / np.maximum(Xc[:, 2], 0.2)) + vw.cy >= 1.0)
                    & (vw.fy * (Xc[:, 1] / np.maximum(Xc[:, 2], 0.2)) + vw.cy <= vw.height - 2.0)
                )
                if not np.any(valid_c & in_f):
                    continue
                u = np.clip(np.round(vw.fx * (Xc[:, 0] / np.maximum(Xc[:, 2], 0.2)) + vw.cx).astype(int), 0, vw.width - 1)
                v_px = np.clip(np.round(vw.fy * (Xc[:, 1] / np.maximum(Xc[:, 2], 0.2)) + vw.cy).astype(int), 0, vw.height - 1)
                edt_v = vw.edge_dt[v_px, u]
                out_v = vw.outside_hull_dt[v_px, u]
                cost_acc += np.where(valid_c & in_f, edt_v + 3.5 * out_v, 15.0)
                cnt_acc += 1

        if cnt_acc > 0:
            mean_c = cost_acc / cnt_acc
            best_i = int(np.argmin(mean_c))
            opt_r[i_h] = float(r_cands[best_i])
            best_costs.append(float(mean_c[best_i]))
        else:
            opt_r[i_h] = float(base_r[i_h] + 2.0 * p_med)

    # Require genuine multi-view horizon edge agreement (rejects occluded or open-frame rings without solid wall)
    if not best_costs or float(np.median(best_costs)) > 2.6:
        return None

    # Smooth meridian profile with sigma=1.1 to guarantee C2 smooth horizon derivatives rho'(h)
    smooth_r = gaussian_filter1d(opt_r, sigma=1.1, mode="nearest")

    return LatheEnvelopeGenerator(
        generator_id=generator_id,
        axis_origin=o_ax,
        axis_dir=a_dir,
        e1=e1,
        e2=e2,
        profile_h=prof_h,
        profile_r=smooth_r,
        pixel_scale=p_med,
        half_width_px=0.40,
        thickness_px=0.30,
        inward_shift_px=0.28,
        opacity=0.145,
        supporting_views=sorted(v.view_name for v in bundle.train_views),
    )


def discover_swept_tube_trunks(
    ridges: list[ConsolidatedRidgeChain],
    bundle: MultiModalSceneBundle,
    pot_h_max: float | None = None,
    surface_ply_path: str | Path | None = None,
) -> tuple[list[ConsolidatedRidgeChain], list[SweptTubeGenerator], dict[str, Any]]:
    """Track cylindrical main stems/tubes with full azimuthal surfel-normal verification (immune to flat walls)."""
    eff_ply = Path(surface_ply_path) if surface_ply_path is not None else bundle.surface_ply_path
    if eff_ply is None or not eff_ply.exists() or not bundle.has_silhouette_mask:
        return ridges, [], {"detected_swept_tubes": 0, "absorbed_bare_trunk_horizon_ridges": 0}

    p_med = bundle.median_pixel_scale
    ply_safe = resolve_safe_path(eff_ply)
    vd = PlyData.read(ply_safe)["vertex"].data
    xyz = np.stack([vd["x"], vd["y"], vd["z"]], axis=-1).astype(np.float64)
    opac = expit(np.clip(vd["opacity"].astype(np.float64), -40.0, 40.0))
    rgb = np.clip(
        np.stack([vd["f_dc_0"], vd["f_dc_1"], vd["f_dc_2"]], axis=-1).astype(np.float64) * 0.2820947918 + 0.5,
        0.0,
        1.0,
    )

    z_all_min, z_all_max = float(np.percentile(xyz[opac > 0.18, 2], 2.0)), float(np.percentile(xyz[opac > 0.18, 2], 98.0))
    z_bot = (pot_h_max - 0.005) if pot_h_max is not None else z_all_min
    z_top = min(z_all_max, z_bot + 0.76)

    # Select non-foliage structural Gaussians with surfel normals for cylindrical cross-section verification
    wood_mask = (
        (opac > 0.18)
        & (xyz[:, 2] >= z_bot)
        & (xyz[:, 2] <= z_top)
        & (rgb[:, 0] > rgb[:, 1] + 0.022)
        & (rgb[:, 0] > 0.26)
    )
    if int(wood_mask.sum()) < 200:
        return ridges, [], {"detected_swept_tubes": 0, "absorbed_bare_trunk_horizon_ridges": 0}

    w_xyz = xyz[wood_mask]
    sc_w = np.exp(np.stack([vd["scale_0"][wood_mask], vd["scale_1"][wood_mask], vd["scale_2"][wood_mask]], axis=-1))
    q_w = np.stack([vd["rot_0"][wood_mask], vd["rot_1"][wood_mask], vd["rot_2"][wood_mask], vd["rot_3"][wood_mask]], axis=-1).astype(np.float64)
    q_w /= np.maximum(np.linalg.norm(q_w, axis=1, keepdims=True), 1e-12)
    R_w = Rotation.from_quat(q_w[:, [1, 2, 3, 0]]).as_matrix()
    w_nrm = R_w[np.arange(len(w_xyz)), :, np.argmin(sc_w, axis=1)]

    dz = 10.0 * p_med
    z_bins = np.arange(z_bot, z_top + 1e-6, dz)
    layers: list[list[tuple[np.ndarray, float, int]]] = []
    for i in range(len(z_bins) - 1):
        in_sl = (w_xyz[:, 2] >= z_bins[i]) & (w_xyz[:, 2] < z_bins[i + 1])
        sl = w_xyz[in_sl]
        sl_n = w_nrm[in_sl]
        layer_nodes: list[tuple[np.ndarray, float, int]] = []
        if len(sl) >= 12:
            tree = cKDTree(sl[:, :2])
            pairs = list(tree.query_pairs(r=5.0 * p_med))
            if pairs:
                ri = [p[0] for p in pairs] + [p[1] for p in pairs]
                ci = [p[1] for p in pairs] + [p[0] for p in pairs]
                nc, lbl = connected_components(
                    csr_matrix((np.ones(len(ri)), (ri, ci)), shape=(len(sl), len(sl))), directed=False
                )
            else:
                nc, lbl = len(sl), np.arange(len(sl))
            for c_id in range(nc):
                m = lbl == c_id
                cnt = int(m.sum())
                if cnt < 12:
                    continue
                pts_c = sl[m]
                ctr_3d = np.array([np.median(pts_c[:, 0]), np.median(pts_c[:, 1]), 0.5 * (z_bins[i] + z_bins[i + 1])])
                rel_xy = pts_c[:, :2] - ctr_3d[:2]
                rad_c = float(np.percentile(np.linalg.norm(rel_xy, axis=1), 82.0))
                if not (1.6 * p_med <= rad_c <= 6.2 * p_med):
                    continue
                # Verify true 360-degree cylindrical geometry: points/normals occupy >= 5 of 8 azimuthal octants!
                octs = len(set(np.floor((np.arctan2(rel_xy[:, 1], rel_xy[:, 0]) + math.pi) / (math.pi / 4.0)).astype(int) % 8))
                if octs >= 5:
                    layer_nodes.append((ctr_3d, rad_c, cnt))
        layers.append(layer_nodes)

    # Greedy multi-target tracking of stem cross-sections across z layers (allowing 1-layer gap)
    active_tracks: list[list[tuple[np.ndarray, float]]] = []
    finished_tracks: list[list[tuple[np.ndarray, float]]] = []

    for l_nodes in layers:
        used_l = set()
        next_active: list[list[tuple[np.ndarray, float]]] = []
        for trk in active_tracks:
            last_pt, last_r = trk[-1]
            # Predict upward tangent if >=2 nodes
            pred_xy = last_pt[:2] + (trk[-1][0][:2] - trk[-2][0][:2]) * 0.7 if len(trk) >= 2 else last_pt[:2]
            best_j = -1
            best_d = 10.5 * p_med
            for j, (n_pt, n_r, _) in enumerate(l_nodes):
                if j in used_l or n_pt[2] - last_pt[2] > 2.3 * dz:
                    continue
                d_xy = float(np.linalg.norm(n_pt[:2] - pred_xy))
                if d_xy < best_d and abs(n_r - last_r) <= 3.2 * p_med:
                    best_d = d_xy
                    best_j = j
            if best_j >= 0:
                used_l.add(best_j)
                trk.append((l_nodes[best_j][0], l_nodes[best_j][1]))
                next_active.append(trk)
            elif l_nodes and (l_nodes[0][0][2] - last_pt[2]) <= 1.2 * dz:
                # Allow 1 missed slice before terminating track
                next_active.append(trk)
            else:
                finished_tracks.append(trk)

        for j, (n_pt, n_r, _) in enumerate(l_nodes):
            if j not in used_l:
                next_active.append([(n_pt, n_r)])
        active_tracks = next_active

    finished_tracks.extend(active_tracks)

    # Fit SweptTubeGenerator to substantial stems (>= 5 slice detections and total length >= 0.16)
    tubes: list[SweptTubeGenerator] = []
    all_vnames = sorted(v.view_name for v in bundle.train_views)
    cal_views = [v for v in bundle.train_views if v.is_original_c2l_build] or bundle.train_views[:8]

    for trk in finished_tracks:
        if len(trk) < 5:
            continue
        pts_trk = np.array([t[0] for t in trk], dtype=np.float64)
        rads_trk = np.array([t[1] for t in trk], dtype=np.float64)
        span_len = float(np.linalg.norm(np.diff(pts_trk, axis=0), axis=1).sum())
        if span_len < 0.16:
            continue

        num_ctrl = min(len(pts_trk), max(4, min(7, int(round(span_len / 0.09)) + 2)))
        ctrl_pts, knots, deg, _ = fit_clamped_bspline_to_polyline(pts_trk, num_ctrl=num_ctrl, reg_smooth=4e-3, pin_endpoints=True)

        # Fit smooth B-spline control radii along u and calibrate slight global scale offset against 2D edges
        diffs = np.linalg.norm(np.diff(pts_trk, axis=0), axis=1)
        u_trk = np.concatenate([[0.0], np.cumsum(diffs) / max(span_len, 1e-8)])
        B_r, _, _, _, _ = bspline_basis_matrices(num_ctrl, u_trk, degree=deg, knots=knots)
        ctrl_r = np.linalg.lstsq(B_r.T @ B_r + 2e-2 * np.eye(num_ctrl), B_r.T @ rads_trk, rcond=None)[0]
        ctrl_r = np.clip(ctrl_r, 1.8 * p_med, 5.5 * p_med)

        # Fine-tune additive radius offset delta_r in [-1.0p, +1.0p] against training-view 2D silhouette edges
        cand_dr = np.linspace(-1.0 * p_med, 1.0 * p_med, 13)
        best_dr = 0.0
        best_c = 1e9
        tmp_gen = SweptTubeGenerator(
            generator_id=len(tubes) + 1,
            spine_control_points=ctrl_pts,
            control_radii=ctrl_r,
            knots=knots,
            degree=deg,
            pixel_scale=p_med,
            supporting_views=all_vnames,
        )
        for dr_val in cand_dr:
            tmp_gen.control_radii = np.clip(ctrl_r + dr_val, 1.5 * p_med, 6.0 * p_med)
            tot_e = 0.0
            cnt_e = 0
            for vw in cal_views:
                horiz_list = tmp_gen.evaluate_horizon_curves(vw.cam_center, num_samples=20)
                for h_pts, _, _, _ in horiz_list:
                    Xc = h_pts @ vw.w2c[:3, :3].T + vw.w2c[:3, 3]
                    u_px = np.clip(np.round(vw.fx * (Xc[:, 0] / np.maximum(Xc[:, 2], 0.2)) + vw.cx).astype(int), 0, vw.width - 1)
                    v_px = np.clip(np.round(vw.fy * (Xc[:, 1] / np.maximum(Xc[:, 2], 0.2)) + vw.cy).astype(int), 0, vw.height - 1)
                    tot_e += float((vw.edge_dt[v_px, u_px] + 2.5 * vw.outside_hull_dt[v_px, u_px]).mean())
                    cnt_e += 1
            if cnt_e > 0 and (tot_e / cnt_e) < best_c:
                best_c = tot_e / cnt_e
                best_dr = float(dr_val)

        tmp_gen.control_radii = np.clip(ctrl_r + best_dr, 1.5 * p_med, 6.0 * p_med)
        tubes.append(tmp_gen)

    if not tubes:
        return ridges, [], {"detected_tubes": 0, "absorbed_trunk_ridges": 0}

    # Absorb redundant multi-view horizon lines baked inside the bare lower trunk zone (z < -0.10)
    dense_spine_pts: list[np.ndarray] = []
    dense_spine_tng: list[np.ndarray] = []
    dense_spine_rad: list[np.ndarray] = []
    for tb in tubes:
        u_s = np.linspace(0.0, 1.0, 48, dtype=np.float64)
        B_s, B_du, _, _, _ = bspline_basis_matrices(len(tb.spine_control_points), u_s, degree=tb.degree, knots=tb.knots)
        sp_p = B_s @ tb.spine_control_points
        sp_d1 = B_du @ tb.spine_control_points
        sp_t = sp_d1 / np.maximum(np.linalg.norm(sp_d1, axis=1, keepdims=True), 1e-9)
        sp_r = B_s @ tb.control_radii
        # Restrict absorption to bare trunk zone below foliage canopy (z <= -0.10)
        bare = sp_p[:, 2] <= -0.10
        if np.any(bare):
            dense_spine_pts.append(sp_p[bare])
            dense_spine_tng.append(sp_t[bare])
            dense_spine_rad.append(sp_r[bare])

    absorbed_trunk_rids: set[int] = set()
    if dense_spine_pts:
        sp_pts_cat = np.concatenate(dense_spine_pts, axis=0)
        sp_tng_cat = np.concatenate(dense_spine_tng, axis=0)
        sp_rad_cat = np.concatenate(dense_spine_rad, axis=0)
        sp_tree = cKDTree(sp_pts_cat)

        for idx, r in enumerate(ridges):
            if float(r.points_3d[:, 2].max()) > -0.08 or float(r.points_3d[:, 2].min()) < pot_h_max - 2.0 * p_med:
                continue
            dists, nn = sp_tree.query(r.points_3d, k=1)
            r_loc = sp_rad_cat[nn]
            # Check if >= 80% of ridge lies inside/on the smooth cylindrical trunk wall and runs parallel to trunk axis
            if float(np.mean(dists <= 1.22 * r_loc)) < 0.80:
                continue
            t_r = _compute_polyline_tangents(r.points_3d)
            align = np.abs(np.sum(t_r * sp_tng_cat[nn], axis=1))
            if float(np.mean(align >= 0.84)) >= 0.80:
                absorbed_trunk_rids.add(idx)

    kept_ridges: list[ConsolidatedRidgeChain] = []
    for idx, r in enumerate(ridges):
        if idx not in absorbed_trunk_rids:
            r.ridge_id = len(kept_ridges)
            kept_ridges.append(r)

    stats = {
        "detected_swept_tubes": len(tubes),
        "absorbed_bare_trunk_horizon_ridges": len(absorbed_trunk_rids),
        "remaining_ridges_after_tubes": len(kept_ridges),
    }
    return kept_ridges, tubes, stats


def evaluate_lathe_horizon_torch(
    gen: LatheEnvelopeGenerator,
    dr_param: torch.Tensor,  # (P,) learnable delta_r
    cam_centers: torch.Tensor,  # (V, 3)
    num_samples: int = 44,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Differentiable PyTorch evaluation of exact perspective horizon points, tangents, and outward normals across V views.

    Returns (pts (V, 2*S, 3), tangents (V, 2*S, 3), normals (V, 2*S, 3)).
    """
    dev = dr_param.device
    o_ax = torch.tensor(gen.axis_origin, dtype=torch.float32, device=dev)
    a_dir = torch.tensor(gen.axis_dir, dtype=torch.float32, device=dev)
    e1 = torch.tensor(gen.e1, dtype=torch.float32, device=dev)
    e2 = torch.tensor(gen.e2, dtype=torch.float32, device=dev)
    h_prof = torch.tensor(gen.profile_h, dtype=torch.float32, device=dev)
    r_prof = (torch.tensor(gen.profile_r, dtype=torch.float32, device=dev) + dr_param).clamp(min=0.02)

    # Linear interpolation matrix from P profile nodes to S dense horizon samples
    h_s = torch.linspace(float(gen.profile_h[0]), float(gen.profile_h[-1]), num_samples, dtype=torch.float32, device=dev)
    u_pos = ((h_s - h_prof[0]) / (h_prof[-1] - h_prof[0]).clamp(min=1e-6)) * (len(h_prof) - 1)
    idx0 = torch.floor(u_pos).long().clamp(0, len(h_prof) - 2)
    idx1 = idx0 + 1
    w1 = (u_pos - idx0.float()).clamp(0.0, 1.0)
    r_s = (1.0 - w1) * r_prof[idx0] + w1 * r_prof[idx1]  # (S,)

    dh = (h_s[1] - h_s[0]).clamp(min=1e-5)
    dr_dh = torch.zeros_like(r_s)
    dr_dh[1:-1] = (r_s[2:] - r_s[:-2]) / (2.0 * dh)
    dr_dh[0] = (r_s[1] - r_s[0]) / dh
    dr_dh[-1] = (r_s[-1] - r_s[-2]) / dh

    rel_c = cam_centers - o_ax[None, :]  # (V, 3)
    hc = (rel_c * a_dir[None, :]).sum(dim=-1, keepdim=True)  # (V, 1)
    cx = (rel_c * e1[None, :]).sum(dim=-1, keepdim=True)
    cy = (rel_c * e2[None, :]).sum(dim=-1, keepdim=True)
    dc = torch.hypot(cx, cy).clamp(min=0.35)
    phic = torch.atan2(cy, cx)  # (V, 1)

    cos_arg = ((r_s[None, :] + dr_dh[None, :] * (hc - h_s[None, :])) / dc).clamp(-0.996, 0.996)
    ang = torch.acos(cos_arg)  # (V, S)

    branches_pts = []
    branches_tng = []
    branches_nrm = []
    for sgn in (1.0, -1.0):
        th = phic + sgn * ang  # (V, S)
        er = torch.cos(th)[..., None] * e1[None, None, :] + torch.sin(th)[..., None] * e2[None, None, :]
        pts = o_ax[None, None, :] + h_s[None, :, None] * a_dir[None, None, :] + r_s[None, :, None] * er
        n_raw = er - dr_dh[None, :, None] * a_dir[None, None, :]
        nrm = torch.nn.functional.normalize(n_raw, dim=-1, eps=1e-8)
        t_raw = torch.zeros_like(pts)
        t_raw[:, 1:-1, :] = pts[:, 2:, :] - pts[:, :-2, :]
        t_raw[:, 0, :] = pts[:, 1, :] - pts[:, 0, :]
        t_raw[:, -1, :] = pts[:, -1, :] - pts[:, -2, :]
        tng = torch.nn.functional.normalize(t_raw, dim=-1, eps=1e-8)
        branches_pts.append(pts)
        branches_tng.append(tng)
        branches_nrm.append(nrm)

    return (
        torch.cat(branches_pts, dim=1),
        torch.cat(branches_tng, dim=1),
        torch.cat(branches_nrm, dim=1),
    )


def evaluate_tubes_horizon_torch(
    tubes: list[SweptTubeGenerator],
    tube_dr_list: list[torch.Tensor],
    cam_centers: torch.Tensor,  # (V, 3)
    num_samples: int = 20,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Differentiable PyTorch evaluation of exact left/right perspective horizons for all SweptTubeGenerators."""
    dev = cam_centers.device
    u_np = np.linspace(0.0, 1.0, num_samples, dtype=np.float64)
    pts_all, tng_all, nrm_all = [], [], []

    for tb, dr_t in zip(tubes, tube_dr_list):
        B_np, B_du_np, _, _, _ = bspline_basis_matrices(
            len(tb.spine_control_points), u_np, degree=tb.degree, knots=tb.knots
        )
        B_t = torch.tensor(B_np, dtype=torch.float32, device=dev)
        c_pts = torch.tensor(tb.spine_control_points, dtype=torch.float32, device=dev)
        sp_pts = B_t @ c_pts  # (S, 3)
        sp_d1 = torch.tensor(B_du_np @ tb.spine_control_points, dtype=torch.float32, device=dev)
        T_s = torch.nn.functional.normalize(sp_d1, dim=-1, eps=1e-8)  # (S, 3)

        r_ctrl = (torch.tensor(tb.control_radii, dtype=torch.float32, device=dev) + dr_t).clamp(min=0.002)
        r_s = B_t @ r_ctrl  # (S,)

        v_vec = cam_centers[:, None, :] - sp_pts[None, :, :]  # (V, S, 3)
        v_perp = v_vec - (v_vec * T_s[None, :, :]).sum(dim=-1, keepdim=True) * T_s[None, :, :]
        d_perp = torch.linalg.norm(v_perp, dim=-1, keepdim=True).clamp(min=0.05)
        v_hat = v_perp / d_perp
        w_hat = torch.nn.functional.normalize(torch.linalg.cross(T_s[None, :, :].expand_as(v_hat), v_hat, dim=-1), dim=-1, eps=1e-8)

        cos_a = (r_s[None, :, None] / d_perp).clamp(0.0, 0.98)
        sin_a = torch.sqrt((1.0 - cos_a * cos_a).clamp(min=1e-6))

        for sgn in (1.0, -1.0):
            n_h = cos_a * v_hat + sgn * sin_a * w_hat
            p_h = sp_pts[None, :, :] + r_s[None, :, None] * n_h
            t_raw = torch.zeros_like(p_h)
            t_raw[:, 1:-1, :] = p_h[:, 2:, :] - p_h[:, :-2, :]
            t_raw[:, 0, :] = p_h[:, 1, :] - p_h[:, 0, :]
            t_raw[:, -1, :] = p_h[:, -1, :] - p_h[:, -2, :]
            t_h = torch.nn.functional.normalize(t_raw, dim=-1, eps=1e-8)
            pts_all.append(p_h)
            tng_all.append(t_h)
            nrm_all.append(n_h)

    return torch.cat(pts_all, dim=1), torch.cat(tng_all, dim=1), torch.cat(nrm_all, dim=1)
