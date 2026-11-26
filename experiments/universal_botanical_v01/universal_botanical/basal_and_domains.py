"""Pillar 1: Zero-Annotation, Color-Agnostic Basal Regime Discovery, 3-Family Container Fitting & Stem Extraction."""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull, cKDTree

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
    fit_clamped_bspline_3d,
)


def _transverse_basis(axis: np.ndarray) -> np.ndarray:
    a = axis / max(float(np.linalg.norm(axis)), 1e-12)
    x = np.eye(3)[int(np.argmin(np.abs(a)))]
    x = x - float(x @ a) * a
    x /= max(float(np.linalg.norm(x)), 1e-12)
    return np.stack([x, np.cross(a, x)], axis=0)


def _mesh_loft(sections: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Loft (H, R, 3) closed rings into a watertight capped triangle mesh."""
    n_levels, n_ring, _ = sections.shape
    vertices = sections.reshape(-1, 3).astype(np.float32)
    faces: list[tuple[int, int, int]] = []
    for h in range(n_levels - 1):
        lo = h * n_ring
        hi = (h + 1) * n_ring
        for i in range(n_ring):
            j = (i + 1) % n_ring
            faces.append((lo + i, lo + j, hi + j))
            faces.append((lo + i, hi + j, hi + i))
    top = (n_levels - 1) * n_ring
    for i in range(1, n_ring - 1):
        faces.append((0, i + 1, i))
        faces.append((top, top + i, top + i + 1))
    return vertices, np.asarray(faces, dtype=np.int32)


def fit_axisymmetric_lathe_mesh(points: np.ndarray, sectors: int = 64) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Fit smooth tilted/vertical axisymmetric revolution shell to exterior vessel points."""
    origin = np.median(points, axis=0)
    axis0 = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    xy_b = _transverse_basis(axis0)
    centered = points - origin[None, :]
    low, high = np.quantile(centered @ axis0, [0.012, 0.988])
    span = max(float(high - low), 1e-4)
    lat = centered @ xy_b.T
    c_init = np.quantile(lat, [0.05, 0.95], axis=0).mean(axis=0)
    radii = np.linalg.norm(lat - c_init[None, :], axis=1)
    prof_h = np.linspace(low, high, 12)

    r_init = []
    side_mask = np.zeros(len(centered), dtype=bool)
    for h_val in prof_h:
        band = np.abs((centered @ axis0) - h_val) <= span * 0.09
        if int(band.sum()) >= 10:
            r_init.append(float(np.quantile(radii[band], 0.88)))
            side_mask |= band & (radii >= np.quantile(radii[band], 0.45))
        else:
            r_init.append(float(np.quantile(radii, 0.85)))
    r_init_arr = np.asarray(r_init, dtype=np.float64)
    fit_pts = centered[side_mask] if int(side_mask.sum()) >= 60 else centered
    if len(fit_pts) > 10000:
        fit_pts = fit_pts[np.linspace(0, len(fit_pts) - 1, 10000, dtype=int)]
    size = max(float(np.quantile(radii, 0.95)), 0.01)

    def _pose(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        a = axis0 + x[2:4] @ xy_b
        a /= max(float(np.linalg.norm(a)), 1e-12)
        return x[:2] @ xy_b, a

    def _res(x: np.ndarray) -> np.ndarray:
        c_off, a_dir = _pose(x)
        rel = fit_pts - c_off[None, :]
        h_p = rel @ a_dir
        r_p = np.linalg.norm(rel - h_p[:, None] * a_dir[None, :], axis=1)
        pred = np.interp(h_p, prof_h, x[4:])
        smooth = 2.0 * np.diff(x[4:], n=2)
        return np.concatenate([r_p - pred, smooth, 0.15 * size * x[2:4]])

    lo_b = np.r_[c_init - 0.5 * size, [-0.25, -0.25], np.full(12, 0.005 * size)]
    hi_b = np.r_[c_init + 0.5 * size, [0.25, 0.25], np.full(12, 2.0 * size)]
    x0 = np.clip(np.r_[c_init, [0.0, 0.0], r_init_arr], lo_b + 1e-7, hi_b - 1e-7)
    sol = least_squares(_res, x0, bounds=(lo_b, hi_b), loss="soft_l1", f_scale=0.025 * size, max_nfev=45).x
    c_off, a_dir = _pose(sol)
    prof_r = sol[4:]

    tb = _transverse_basis(a_dir)
    th = np.linspace(0.0, 2.0 * math.pi, sectors, endpoint=False)
    dirs = np.column_stack([np.cos(th), np.sin(th)]) @ tb
    ctr_w = origin + c_off
    sections = ctr_w[None, None, :] + prof_h[:, None, None] * a_dir[None, None, :] + prof_r[:, None, None] * dirs[None, :, :]
    verts, faces = _mesh_loft(sections)
    info = {
        "axis_origin": ctr_w.tolist(),
        "axis_dir": a_dir.tolist(),
        "profile_h": prof_h.tolist(),
        "profile_r": prof_r.tolist(),
    }
    return verts, faces, info


def fit_rectangular_tray_mesh(points: np.ndarray, p_med: float) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Fit oriented 4-sided rectangular tray loft across height sections."""
    origin = np.median(points, axis=0)
    up = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    _, evecs = np.linalg.eigh(np.cov((points - origin[None, :]).T))
    cand_up = evecs[:, 0]
    if cand_up[2] < 0:
        cand_up = -cand_up
    if cand_up[2] >= 0.82:
        up = cand_up
    x_ax = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    x_ax -= float(x_ax @ up) * up
    x_ax /= max(float(np.linalg.norm(x_ax)), 1e-12)
    frame = np.stack([x_ax, np.cross(up, x_ax), up], axis=0)
    local = (points - origin[None, :]) @ frame.T

    height = local[:, 2]
    low, high = np.quantile(height, [0.015, 0.985])
    # Focus yaw alignment on dense upper rim/body slices to avoid stand corner noise
    rim_band = height >= (low + 0.35 * (high - low))
    xy_ref = local[rim_band, :2] if int(rim_band.sum()) >= 80 else local[:, :2]

    best = None
    for yaw in np.linspace(0.0, 0.5 * math.pi, 181, endpoint=False):
        basis = np.array([[math.cos(yaw), math.sin(yaw)], [-math.sin(yaw), math.cos(yaw)]])
        rot_xy = xy_ref @ basis.T
        edges = np.quantile(rot_xy, [0.015, 0.985], axis=0)
        area = float(np.prod(np.maximum(edges[1] - edges[0], 1e-4)))
        if best is None or area < best[0]:
            best = (area, float(yaw), basis)
    assert best is not None
    area_min, yaw_best, basis_best = best
    frame[:2] = basis_best @ frame[:2]
    rot_all = local[:, :2] @ basis_best.T

    span = max(float(high - low), 1e-4)
    fracs = [0.0, 0.25, 0.78, 1.0]
    sections = []
    extents_list = []
    for fr in fracs:
        z_s = low + span * fr
        band = np.abs(height - z_s) <= max(2.5 * p_med, 0.22 * span)
        sub_xy = rot_all[band] if int(band.sum()) >= 40 else rot_all
        ext = np.quantile(sub_xy, [0.014, 0.986], axis=0)
        x0, y0 = float(ext[0, 0]), float(ext[0, 1])
        x1, y1 = float(ext[1, 0]), float(ext[1, 1])
        corners = np.array([[x0, y0, z_s], [x1, y0, z_s], [x1, y1, z_s], [x0, y1, z_s]], dtype=np.float64)
        sections.append(corners @ frame + origin[None, :])
        extents_list.append([x1 - x0, y1 - y0])

    verts, faces = _mesh_loft(np.asarray(sections))
    info = {
        "center": origin.tolist(),
        "up": frame[2].tolist(),
        "yaw_radians": yaw_best,
        "section_extents": extents_list,
        "matched_rect_area": area_min,
    }
    return verts, faces, info


def fit_convex_loft_vessel_mesh(points: np.ndarray, p_med: float) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Fit non-axisymmetric 9-level x 24-azimuthal convex half-plane intersection loft."""
    origin = np.median(points, axis=0)
    up = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    x_ax = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    frame = np.stack([x_ax, np.cross(up, x_ax), up], axis=0)
    local = (points - origin[None, :]) @ frame.T
    height = local[:, 2]
    low, high = np.quantile(height, [0.010, 0.990])
    span = max(float(high - low), 1e-4)
    levels = np.linspace(low, high, 9)

    theta = np.linspace(0.0, 2.0 * math.pi, 24, endpoint=False)
    dirs = np.column_stack([np.cos(theta), np.sin(theta)])
    cos_mat = dirs @ dirs.T

    rings = []
    for z_s in levels:
        band = np.abs(height - z_s) <= max(2.2 * p_med, 0.15 * span)
        sec = local[band, :2] if int(band.sum()) >= 40 else local[:, :2]
        mid = np.median(sec, axis=0)
        support_d = np.maximum(np.quantile((sec - mid[None, :]) @ dirs.T, 0.975, axis=0), p_med)
        rad_mat = np.full(cos_mat.shape, np.inf, dtype=np.float64)
        np.divide(support_d[None, :], cos_mat, out=rad_mat, where=cos_mat > 0.16)
        r_az = np.min(rad_mat, axis=1)
        xy = mid[None, :] + r_az[:, None] * dirs
        rings.append(np.column_stack([xy, np.full(len(xy), z_s)]))

    sections = np.asarray(rings, dtype=np.float64)
    interior = sections[1:-1, :, :2].copy()
    sections[1:-1, :, :2] = 0.6 * interior + 0.2 * sections[:-2, :, :2] + 0.2 * sections[2:, :, :2]
    verts, faces = _mesh_loft(sections @ frame + origin[None, None, :])
    info = {
        "center": origin.tolist(),
        "z_bounds": [float(low), float(high)],
        "num_levels": 9,
        "num_azimuths": 24,
    }
    return verts, faces, info


def point_in_convex_rings_mask(all_pts: np.ndarray, verts: np.ndarray, vessel_bot_z: float, rim_z: float, pad: float) -> np.ndarray:
    """Fast 3D containment check inside a lofted convex/lathe/rectangular support mesh."""
    if len(verts) == 0:
        return np.zeros(len(all_pts), dtype=bool)
    z = all_pts[:, 2]
    in_z = (z >= vessel_bot_z - pad) & (z <= rim_z + pad)
    idx_z = np.flatnonzero(in_z)
    if len(idx_z) == 0:
        return np.zeros(len(all_pts), dtype=bool)
    # Check 2D convex hull inclusion in 6 height bands for tight lateral containment!
    z_bands = np.linspace(vessel_bot_z - pad, rim_z + pad, 7)
    v_xy = verts[:, :2]
    v_z = verts[:, 2]
    out = np.zeros(len(all_pts), dtype=bool)

    theta = np.linspace(0.0, 2.0 * math.pi, 32, endpoint=False)
    dirs = np.column_stack([np.cos(theta), np.sin(theta)])
    for b in range(6):
        bm = (z[idx_z] >= z_bands[b]) & (z[idx_z] <= z_bands[b + 1])
        if not np.any(bm):
            continue
        vm = (v_z >= z_bands[b] - 0.04) & (v_z <= z_bands[b + 1] + 0.04)
        ref_xy = v_xy[vm] if int(vm.sum()) >= 4 else v_xy
        ctr = ref_xy.mean(axis=0)
        max_proj = np.max((ref_xy - ctr[None, :]) @ dirs.T, axis=0) + pad
        cand_ids = idx_z[bm]
        cand_proj = (all_pts[cand_ids, :2] - ctr[None, :]) @ dirs.T
        inside = np.all(cand_proj <= max_proj[None, :], axis=1)
        out[cand_ids[inside]] = True
    return out


def discover_basal_support_and_domains(
    cloud: SceneGaussianCloud,
    train_views: list[CalibratedBuildOrEvalView],
    p_med: float,
    v05_trunks: list[dict[str, Any]],
    cfg: UniversalBotanicalConfig,
) -> tuple[BasalSupportModel, list[StemSplineChain], np.ndarray, np.ndarray, dict[str, Any]]:
    """Zero-annotation, zero-scene-name automatic discovery of Support, Stand/Table, and Stems."""
    n_total = len(cloud.means)
    pts_all = cloud.means.astype(np.float64)
    opac = cloud.opacities.astype(np.float64)
    nrms = cloud.surfel_normals.astype(np.float64)

    # 1. Measure multi-view front-surface smoothness (depth_jump & alpha solidity) on build views ONLY
    vis_cnt = np.zeros(n_total, dtype=np.int32)
    dj_sum = np.zeros(n_total, dtype=np.float64)
    al_sum = np.zeros(n_total, dtype=np.float64)

    stride = max(1, len(train_views) // 16)
    for vw in train_views[::stride]:
        dj_b = cv2.blur(vw.depth_jump.astype(np.float32), (5, 5))
        al_b = cv2.blur(vw.alpha.astype(np.float32), (5, 5))
        Xc = pts_all @ vw.w2c[:3, :3].T + vw.w2c[:3, 3][None, :]
        zc = Xc[:, 2]
        u = np.rint(vw.fx * Xc[:, 0] / np.maximum(zc, 1e-4) + vw.cx).astype(np.int32)
        v = np.rint(vw.fy * Xc[:, 1] / np.maximum(zc, 1e-4) + vw.cy).astype(np.int32)
        inb = (zc > 0.15) & (u >= 0) & (u < vw.width) & (v >= 0) & (v < vw.height) & (opac >= cfg.active_opacity_min)
        ids = np.flatnonzero(inb)
        on_front = (vw.alpha[v[ids], u[ids]] > 0.50) & (np.abs(zc[ids] - vw.front_depth[v[ids], u[ids]]) <= 3.5 * p_med)
        hit = ids[on_front]
        vis_cnt[hit] += 1
        dj_sum[hit] += dj_b[v[hit], u[hit]]
        al_sum[hit] += al_b[v[hit], u[hit]]

    act_vis = (opac >= cfg.active_opacity_min) & (vis_cnt >= 1)
    act_any = opac >= cfg.active_opacity_min
    z_act = pts_all[act_any, 2]
    z_min, z_max = [float(x) for x in np.quantile(z_act, [0.008, 0.992])]
    span_z = max(z_max - z_min, 1e-3)

    # 2. Scan 24 fine vertical slices across lower 60% of plant height
    n_slices = 24
    z_edges = np.linspace(z_min, z_min + 0.60 * span_z, n_slices + 1)
    slice_rows: list[dict[str, Any]] = []
    act_ids = np.flatnonzero(act_vis)
    dj_act = dj_sum[act_ids] / np.maximum(vis_cnt[act_ids], 1)
    al_act = al_sum[act_ids] / np.maximum(vis_cnt[act_ids], 1)
    nz_act = np.abs(nrms[act_ids, 2])
    z_vis = pts_all[act_ids, 2]

    for s_i in range(n_slices):
        sm = (z_vis >= z_edges[s_i]) & (z_vis < z_edges[s_i + 1])
        cnt = int(sm.sum())
        if cnt < 25:
            slice_rows.append({
                "idx": s_i, "z0": float(z_edges[s_i]), "z1": float(z_edges[s_i + 1]),
                "count": cnt, "hull_area": 0.0, "rect_fill": 0.0, "aspect": 1.0,
                "nz_mean": 0.0, "dj_mean": 1.0, "al_mean": 0.0, "smooth_shell": False,
            })
            continue
        xy = pts_all[act_ids[sm], :2]
        hull_a = float(ConvexHull(xy).volume) if len(xy) >= 6 else 0.0
        rect = cv2.minAreaRect(xy.astype(np.float32))
        bw, bh = max(float(rect[1][0]), 1e-4), max(float(rect[1][1]), 1e-4)
        rect_fill = min(hull_a / (bw * bh), 1.0)
        aspect = max(bw, bh) / min(bw, bh)
        dj_m = float(dj_act[sm].mean())
        al_m = float(al_act[sm].mean())
        nz_m = float(nz_act[sm].mean())
        is_smooth = (al_m >= 0.945) & (dj_m <= 0.0220)
        slice_rows.append({
            "idx": s_i, "z0": float(z_edges[s_i]), "z1": float(z_edges[s_i + 1]),
            "count": cnt, "hull_area": hull_a, "rect_fill": rect_fill, "aspect": aspect,
            "nz_mean": nz_m, "dj_mean": dj_m, "al_mean": al_m, "smooth_shell": bool(is_smooth),
        })

    # Find contiguous runs of smooth-shell slices (bridging at most 1 single slice if adjacent both pass)
    smooth_flags = [r["smooth_shell"] for r in slice_rows]
    runs: list[tuple[int, int]] = []
    cur_s = None
    for i, flg in enumerate(smooth_flags):
        if flg and cur_s is None:
            cur_s = i
        elif not flg and cur_s is not None:
            runs.append((cur_s, i - 1))
            cur_s = None
    if cur_s is not None:
        runs.append((cur_s, n_slices - 1))

    # Pick primary smooth vessel run (>= 4 slices in lower half)
    valid_runs = [(a, b) for (a, b) in runs if (b - a + 1) >= 4 and a <= 12]
    support_mask = np.zeros(n_total, dtype=bool)
    stand_mask = np.zeros(n_total, dtype=bool)
    verts_sup = np.zeros((0, 3), dtype=np.float32)
    faces_sup = np.zeros((0, 3), dtype=np.int32)

    basal_hull_max = max((r["hull_area"] for r in slice_rows[:6]), default=0.0)
    basal_width_equiv = math.sqrt(max(basal_hull_max, 0.0))

    if valid_runs:
        r_a, r_b = max(valid_runs, key=lambda ab: sum(slice_rows[k]["count"] for k in range(ab[0], ab[1] + 1)))

        # Check for an internal stand-to-tray air gap / density valley inside [r_a..r_b] (e.g., slatted stand below hollow tray!)
        counts_run = [slice_rows[k]["count"] for k in range(r_a, r_b + 1)]
        peak_cnt = max(counts_run)
        peak_rel_idx = int(np.argmax(counts_run))
        # Split at the DEEPEST air-gap minimum strictly below the main peak (preserves hollow vertical tray side walls above the gap!)
        if peak_rel_idx >= 2:
            min_rel = int(np.argmin(counts_run[:peak_rel_idx]))
            if counts_run[min_rel] < 0.05 * peak_cnt:
                r_a = r_a + min_rel + 1

        # Trim top of run if cross-sectional hull_area has already collapsed (< 35% of vessel peak hull_area -> trunk neck!)
        peak_hull = max(slice_rows[k]["hull_area"] for k in range(r_a, r_b + 1))
        while r_b > r_a and slice_rows[r_b]["hull_area"] < 0.36 * peak_hull:
            r_b -= 1

        vessel_bot_z = slice_rows[r_a]["z0"]
        rim_z = slice_rows[r_b]["z1"]

        # Everything strictly below vessel_bot_z (e.g. table reflection apron or wooden stand) is STATIC STAND/TABLE!
        stand_mask = pts_all[:, 2] < vessel_bot_z

        # Gather clean build-visible vessel points inside [vessel_bot_z, rim_z]
        cand_v = act_vis & (pts_all[:, 2] >= vessel_bot_z) & (pts_all[:, 2] <= rim_z)
        dj_all = dj_sum / np.maximum(vis_cnt, 1)
        al_all = al_sum / np.maximum(vis_cnt, 1)
        clean_v = cand_v & (al_all >= 0.80) & (dj_all <= 0.032)
        v_pts = pts_all[clean_v]

        # Robust XY outlier trim (removes stray background wisps on stand/table margins)
        q_lo, q_hi = np.quantile(v_pts[:, :2], [0.008, 0.992], axis=0)
        in_xy = np.all((v_pts[:, :2] >= q_lo) & (v_pts[:, :2] <= q_hi), axis=1)
        v_pts = v_pts[in_xy]

        # Select among the 3 geometric vessel families using cross-sectional invariants!
        core_slices = [slice_rows[k] for k in range(r_a, r_b + 1) if slice_rows[k]["hull_area"] >= 0.45 * peak_hull]
        med_rect_fill = float(np.median([s["rect_fill"] for s in core_slices]))
        med_aspect = float(np.median([s["aspect"] for s in core_slices]))

        if med_rect_fill >= cfg.rect_tray_fill_min:
            regime = "RECTANGULAR_TRAY_LOFT"
            verts_sup, faces_sup, fit_info = fit_rectangular_tray_mesh(v_pts, p_med)
        elif med_aspect <= cfg.lathe_aspect_max:
            regime = "AXISYMMETRIC_LATHE"
            verts_sup, faces_sup, fit_info = fit_axisymmetric_lathe_mesh(v_pts)
        else:
            regime = "CONVEX_SECTION_LOFT"
            verts_sup, faces_sup, fit_info = fit_convex_loft_vessel_mesh(v_pts, p_med)

        # Assign all Gaussians inside the fitted 3D container volume to LABEL_BASAL_SUPPORT (100% static!)
        support_mask = point_in_convex_rings_mask(pts_all, verts_sup, vessel_bot_z, rim_z, pad=2.0 * p_med) & (~stand_mask)
        sup_diag = {
            "vessel_slice_range": [r_a, r_b],
            "median_rect_fill": round(med_rect_fill, 4),
            "median_aspect_ratio": round(med_aspect, 4),
            "fit_info": fit_info,
        }
    elif (basal_width_equiv / span_z) >= cfg.open_ground_width_over_height_min:
        regime = "OPEN_GROUND_BED"
        vessel_bot_z = z_min
        # Ground carpet occupies the dense horizontal basal mat (lowest 24% of height)
        rim_z = z_min + 0.24 * span_z
        support_mask = pts_all[:, 2] <= rim_z
        sup_diag = {
            "basal_width_over_height": round(basal_width_equiv / span_z, 4),
            "ground_bed_top_z": round(rim_z, 4),
        }
    else:
        regime = "NO_ENCLOSED_SUPPORT"
        vessel_bot_z = z_min
        rim_z = z_min
        sup_diag = {
            "basal_width_over_height": round(basal_width_equiv / span_z, 4),
            "note": "Leafy foliage extends to base with no smooth rigid container shell.",
        }

    support_model = BasalSupportModel(
        regime=regime,
        vertices=verts_sup,
        faces=faces_sup,
        rim_z=float(rim_z),
        vessel_bot_z=float(vessel_bot_z),
        support_kernel_mask=support_mask,
        stand_kernel_mask=stand_mask,
        diagnostics=sup_diag,
    )

    # 3. Color-Agnostic 3D Stem / Trunk / Stalk Discovery (strictly excluding support & stand!)
    labels = np.full(n_total, LABEL_UNASSIGNED_CANOPY, dtype=np.int32)
    labels[stand_mask] = LABEL_STATIC_STAND_OR_TABLE
    labels[support_mask] = LABEL_BASAL_SUPPORT
    stem_owner = np.full(n_total, -1, dtype=np.int32)
    stem_chains: list[StemSplineChain] = []

    canopy_cand = np.flatnonzero((labels == LABEL_UNASSIGNED_CANOPY) & (opac >= cfg.active_opacity_min))
    c_pts = pts_all[canopy_cand]
    c_scales = np.sort(cloud.scales[canopy_cand].astype(np.float64), axis=1)  # s0 <= s1 <= s2

    # 3A: Verify supplied v05 SweptTube trunks against actual canopy Gaussians (never trust empty tubes!)
    for tr in v05_trunks:
        sp = np.asarray(tr["spine_ctrl"], dtype=np.float64)
        rad = np.asarray(tr["radii_ctrl"], dtype=np.float64)
        if len(sp) < 2 or len(c_pts) == 0:
            continue
        if sp[0, 2] > sp[-1, 2]:
            sp = sp[::-1].copy()
            rad = rad[::-1].copy()
        # Keep portion above vessel_bot_z
        u_dense = np.linspace(0.0, 1.0, 48)
        sp_d = np.column_stack([np.interp(u_dense, np.linspace(0.0, 1.0, len(sp)), sp[:, d]) for d in range(3)])
        r_d = np.interp(u_dense, np.linspace(0.0, 1.0, len(rad)), rad)
        t_tree = cKDTree(sp_d)
        dist_t, nn_t = t_tree.query(c_pts, k=1, distance_upper_bound=0.045)
        hit = np.isfinite(dist_t) & (dist_t <= np.maximum(1.35 * r_d[np.minimum(nn_t, len(r_d) - 1)], 2.8 * p_med))
        # Ensure we don't grab broad flat leaves crossing the trunk: require non-sheet or tight axial core
        planarity = (c_scales[:, 1] - c_scales[:, 0]) / np.maximum(c_scales[:, 2], 1e-8)
        core_hit = hit & ((dist_t <= 0.95 * r_d[np.minimum(nn_t, len(r_d) - 1)]) | (planarity < 0.62))
        if int(core_hit.sum()) >= 45:
            cid = len(stem_chains)
            glob_hit = canopy_cand[core_hit]
            labels[glob_hit] = LABEL_STEM_SKELETON
            stem_owner[glob_hit] = cid
            ctrl = fit_clamped_bspline_3d(sp, num_ctrl=min(7, max(4, len(sp))))
            stem_chains.append(
                StemSplineChain(
                    chain_id=cid,
                    level=0,
                    parent_chain_id=-1,
                    parent_u=0.0,
                    ctrl_points=ctrl,
                    radius_base=float(np.percentile(rad, 85.0)),
                    radius_tip=float(np.percentile(rad, 25.0)),
                    supported_kernel_count=int(core_hit.sum()),
                    basal_anchored=bool(sp[0, 2] <= rim_z + 0.15 * span_z),
                )
            )

    # 3B: Intrinsic 3D Neck-Passage & Cylindrical Stalk Discovery (for Bonsai gnarly trunk, Brassica green stalks, etc.)!
    if len(stem_chains) == 0 and len(canopy_cand) >= 100:
        rem_cand = np.flatnonzero((labels == LABEL_UNASSIGNED_CANOPY) & (opac >= 0.05))
        r_pts = pts_all[rem_cand]
        r_sc = np.sort(cloud.scales[rem_cand].astype(np.float64), axis=1)
        linearity = (r_sc[:, 2] - r_sc[:, 1]) / np.maximum(r_sc[:, 2], 1e-8)
        planarity = (r_sc[:, 1] - r_sc[:, 0]) / np.maximum(r_sc[:, 2], 1e-8)
        nz_rem = np.abs(nrms[rem_cand, 2])

        # Case 1: Enclosed container with a distinct trunk/stem column rising above rim_z (e.g. Bonsai gnarled trunk!)
        if regime in {"RECTANGULAR_TRAY_LOFT", "AXISYMMETRIC_LATHE", "CONVEX_SECTION_LOFT"}:
            neck_lo = rim_z - 0.015 * span_z
            neck_hi = rim_z + 0.28 * span_z
            in_neck = (r_pts[:, 2] >= neck_lo) & (r_pts[:, 2] <= neck_hi) & (nz_rem < 0.68)
            if int(in_neck.sum()) >= 60:
                neck_pts = r_pts[in_neck]
                xy_span_neck = np.quantile(neck_pts[:, :2], 0.85, axis=0) - np.quantile(neck_pts[:, :2], 0.15, axis=0)
                canopy_xy_span = np.quantile(r_pts[:, :2], 0.95, axis=0) - np.quantile(r_pts[:, :2], 0.05, axis=0)
                if float(np.mean(xy_span_neck)) < 0.58 * float(np.mean(canopy_xy_span)):
                    z_bins = np.linspace(neck_lo, neck_hi, 8)
                    spine_w = []
                    rad_w = []
                    for b in range(7):
                        bm = (neck_pts[:, 2] >= z_bins[b]) & (neck_pts[:, 2] < z_bins[b + 1])
                        if int(bm.sum()) >= 6:
                            med_p = np.median(neck_pts[bm], axis=0)
                            r_est = float(np.quantile(np.linalg.norm(neck_pts[bm, :2] - med_p[:2], axis=1), 0.68))
                            spine_w.append(med_p)
                            rad_w.append(np.clip(r_est, 2.5 * p_med, 0.085))
                    if len(spine_w) >= 4:
                        sp_arr = np.asarray(spine_w, dtype=np.float64)
                        rd_arr = np.asarray(rad_w, dtype=np.float64)
                        ctrl = fit_clamped_bspline_3d(sp_arr, num_ctrl=4, reg=1.5e-2)
                        t_tr = cKDTree(sp_arr)
                        d_q, nn_q = t_tr.query(r_pts, k=1, distance_upper_bound=0.095)
                        hit_q = np.isfinite(d_q) & (d_q <= 1.25 * rd_arr[np.minimum(nn_q, len(rd_arr) - 1)]) & (r_pts[:, 2] <= neck_hi + 0.03)
                        if int(hit_q.sum()) >= 60:
                            cid = len(stem_chains)
                            glob_q = rem_cand[hit_q]
                            labels[glob_q] = LABEL_STEM_SKELETON
                            stem_owner[glob_q] = cid
                            stem_chains.append(
                                StemSplineChain(
                                    chain_id=cid, level=0, parent_chain_id=-1, parent_u=0.0,
                                    ctrl_points=ctrl, radius_base=float(rd_arr[0]), radius_tip=float(rd_arr[-1]),
                                    supported_kernel_count=int(hit_q.sum()), basal_anchored=True,
                                )
                            )

        # Case 2: True 3D Cylindrical Stalk Ridges (tested via wide r=16*p_med 3D NEIGHBORHOOD point-cloud PCA,
        # NOT single-cigar splat scale, so cigar splats inside 2D flat leaf blades are NEVER misclassified as stems,
        # while genuine 1D stalks in Brassica/Flowers are cleanly separated!)
        rem_cand2 = np.flatnonzero((labels == LABEL_UNASSIGNED_CANOPY) & (opac >= 0.08))
        if len(rem_cand2) >= 250:
            p2 = pts_all[rem_cand2]
            p2_tree = cKDTree(p2)
            d_nb, idx_nb = p2_tree.query(p2, k=min(48, len(p2)), distance_upper_bound=16.0 * p_med)
            is_true_tube = np.zeros(len(p2), dtype=bool)
            sc2 = np.sort(cloud.scales[rem_cand2].astype(np.float64), axis=1)
            cand_sub = np.flatnonzero(((sc2[:, 2] - sc2[:, 1]) / np.maximum(sc2[:, 2], 1e-8) >= 0.52) & (p2[:, 2] >= rim_z + 0.03 * span_z))
            for ci in cand_sub.tolist():
                row = idx_nb[ci]
                valid = row[row < len(p2)]
                if len(valid) < 12:
                    continue
                loc_pts = p2[valid]
                ev = np.linalg.eigvalsh(np.cov((loc_pts - loc_pts.mean(axis=0)).T))
                s_ev = np.sqrt(np.maximum(ev, 0.0))
                if s_ev[2] > 4.0 * p_med and (s_ev[1] / s_ev[2]) <= 0.44 and s_ev[1] <= 4.8 * p_med:
                    is_true_tube[ci] = True

            if int(is_true_tube.sum()) >= 60:
                st_pts = p2[is_true_tube]
                st_ids = rem_cand2[is_true_tube]
                st_tree = cKDTree(st_pts)
                from scipy.sparse import csr_matrix
                from scipy.sparse.csgraph import connected_components

                d_s, nbr_s = st_tree.query(st_pts, k=min(10, len(st_pts)), distance_upper_bound=8.0 * p_med)
                rows_s, cols_s = [], []
                for k_c in range(1, d_s.shape[1]):
                    ok = np.isfinite(d_s[:, k_c]) & (nbr_s[:, k_c] < len(st_pts))
                    src = np.flatnonzero(ok)
                    dst = nbr_s[ok, k_c]
                    dz_ok = np.abs(st_pts[dst, 2] - st_pts[src, 2]) >= 0.40 * d_s[ok, k_c]
                    rows_s.extend([src[dz_ok], dst[dz_ok]])
                    cols_s.extend([dst[dz_ok], src[dz_ok]])
                if rows_s:
                    adj_s = csr_matrix(
                        (np.ones(sum(len(x) for x in rows_s)), (np.concatenate(rows_s), np.concatenate(cols_s))),
                        shape=(len(st_pts), len(st_pts)),
                    )
                    _, cc_lbl = connected_components(adj_s, directed=False)
                    counts_cc = np.bincount(cc_lbl)
                    for cc_id in np.argsort(-counts_cc):
                        if counts_cc[cc_id] < 30:
                            break
                        sub_p = st_pts[cc_lbl == cc_id]
                        z_span_cc = float(sub_p[:, 2].max() - sub_p[:, 2].min())
                        xy_std = float(np.linalg.norm(sub_p[:, :2].std(axis=0)))
                        if z_span_cc >= 0.12 * span_z and z_span_cc >= 3.2 * max(xy_std, 1e-4):
                            z_b = np.linspace(sub_p[:, 2].min(), sub_p[:, 2].max(), 6)
                            sp_c, rd_c = [], []
                            for b in range(5):
                                bm = (sub_p[:, 2] >= z_b[b]) & (sub_p[:, 2] <= z_b[b + 1])
                                if int(bm.sum()) >= 3:
                                    mp = np.median(sub_p[bm], axis=0)
                                    sp_c.append(mp)
                                    rd_c.append(np.clip(np.median(np.linalg.norm(sub_p[bm, :2] - mp[:2], axis=1)) * 1.35, 1.8 * p_med, 0.022))
                            if len(sp_c) >= 4:
                                cid = len(stem_chains)
                                glob_cc = st_ids[cc_lbl == cc_id]
                                labels[glob_cc] = LABEL_STEM_SKELETON
                                stem_owner[glob_cc] = cid
                                # Smooth 4-control clamped B-spline with strong regularization (zero wild extrapolation!)
                                ctrl = fit_clamped_bspline_3d(np.asarray(sp_c), num_ctrl=4, reg=2e-2)
                                stem_chains.append(
                                    StemSplineChain(
                                        chain_id=cid, level=0, parent_chain_id=-1, parent_u=0.0,
                                        ctrl_points=ctrl, radius_base=float(rd_c[0]), radius_tip=float(rd_c[-1]),
                                        supported_kernel_count=int(len(glob_cc)),
                                        basal_anchored=bool(sub_p[:, 2].min() <= rim_z + 0.35 * span_z),
                                    )
                                )
                                if len(stem_chains) >= 6:
                                    break

    domain_stats = {
        "basal_regime": regime,
        "vessel_bot_z": round(float(vessel_bot_z), 4),
        "rim_z": round(float(rim_z), 4),
        "total_kernels": n_total,
        "static_stand_or_table_kernels": int(stand_mask.sum()),
        "static_basal_support_kernels": int(support_mask.sum()),
        "verified_stem_chains": len(stem_chains),
        "stem_kernels": int((labels == LABEL_STEM_SKELETON).sum()),
        "canopy_candidate_kernels": int((labels == LABEL_UNASSIGNED_CANOPY).sum()),
    }
    return support_model, stem_chains, labels, stem_owner, domain_stats
