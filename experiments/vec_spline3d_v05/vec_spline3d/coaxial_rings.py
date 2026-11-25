"""Coaxial surface-of-revolution ring discovery, lathe rib consolidation, and opaque-interior ghost cleaning."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from scipy.signal import find_peaks
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from .co_circular_arcs import _circle_from_two_oriented_segments
from .multimodal_data import MultiModalSceneBundle
from .planar_wireframe_reg import _fibonacci_hemisphere_dirs, _gather_oriented_surface_points
from .schema import (
    CoaxialRingFamilySpec,
    JunctionNode,
    ParametricCurvePrimitive,
    RibbonGeometry,
    clamped_uniform_knots,
    fit_circular_arc_to_polyline,
)
from .stage1_ray_clean import GPUViewFieldEvaluator, _compute_polyline_tangents
from .stage2_scms_consolidate import ConsolidatedRidgeChain


def _fit_circle_2d_robust(xy: np.ndarray, init_center: np.ndarray, band_tol: float = 0.015) -> tuple[np.ndarray, float, float] | None:
    """Fit 2D circle (center_2d, radius, p90_residual) invariant to uneven azimuthal view density."""
    if len(xy) < 40:
        return None
    # Density-invariant bounding-box center (immune to uneven multi-view pixel density around azimuth!)
    c_est = 0.5 * (np.percentile(xy, 2.0, axis=0) + np.percentile(xy, 98.0, axis=0))
    rad = float(np.percentile(np.linalg.norm(xy - c_est[None, :], axis=1), 80.0))
    inl = xy

    for _it in range(3):
        r0 = np.linalg.norm(xy - c_est[None, :], axis=1)
        r_outer = float(np.percentile(r0, 78.0))
        inl = xy[np.abs(r0 - r_outer) <= band_tol]
        if len(inl) < 25:
            return None
        A = np.column_stack([2.0 * inl[:, 0], 2.0 * inl[:, 1], np.ones(len(inl), dtype=np.float64)])
        rhs = inl[:, 0] ** 2 + inl[:, 1] ** 2
        sol, _, rank, _ = np.linalg.lstsq(A, rhs, rcond=None)
        if rank < 3:
            return None
        cx, cy, c0 = float(sol[0]), float(sol[1]), float(sol[2])
        r_sq = c0 + cx * cx + cy * cy
        if r_sq <= 1e-8 or r_sq > 4.0:
            return None
        c_est = np.array([cx, cy], dtype=np.float64)
        rad = math.sqrt(r_sq)

    cx, cy = float(c_est[0]), float(c_est[1])
    dx = inl[:, 0] - cx
    dy = inl[:, 1] - cy
    dist = np.hypot(dx, dy)
    if np.all(dist > 1e-6):
        res0 = dist - rad
        J = np.column_stack([-dx / dist, -dy / dist, -np.ones(len(inl))])
        step, _, _, _ = np.linalg.lstsq(J, -res0, rcond=None)
        cx += float(step[0])
        cy += float(step[1])
        rad = max(1e-4, rad + float(step[2]))

    res = np.abs(np.hypot(inl[:, 0] - cx, inl[:, 1] - cy) - rad)
    p90_res = float(np.percentile(res, 90.0))
    return np.array([cx, cy], dtype=np.float64), float(rad), p90_res


def _discover_lathe_part_from_multiview_depth(
    bundle: MultiModalSceneBundle, p_med: float
) -> dict[str, Any] | None:
    """Automatically detect a rotational sub-part (e.g., ceramic pot) from unprojected multi-view opaque depths."""
    # Prefer homogeneous median-transmittance depth views when >=4 surround the object (avoids mixing softmin envelope offset)
    orig_depth_views = [v for v in bundle.train_views if v.is_original_c2l_build and v.depth is not None and v.depth_jump is not None]
    depth_views_to_use = orig_depth_views if len(orig_depth_views) >= 4 else [
        v for v in bundle.train_views if v.depth is not None and v.depth_jump is not None
    ]

    surf_chunks: list[np.ndarray] = []
    for vw in depth_views_to_use:
        assert vw.depth is not None and vw.depth_jump is not None
        d_sub = vw.depth[::2, ::2]
        a_sub = vw.alpha[::2, ::2]
        j_sub = vw.depth_jump[::2, ::2]
        mask = (a_sub > 0.94) & (d_sub > 0.2) & (j_sub < 0.008)
        if not np.any(mask):
            continue
        rr, cc = np.where(mask)
        uu = (cc * 2).astype(np.float64)
        vv = (rr * 2).astype(np.float64)
        zc = d_sub[rr, cc].astype(np.float64)
        xc = (uu - vw.cx) * zc / vw.fx
        yc = (vv - vw.cy) * zc / vw.fy
        pts_w = (np.column_stack([xc, yc, zc]) @ vw.c2w[:3, :3].T) + vw.c2w[:3, 3]
        surf_chunks.append(pts_w)

    if not surf_chunks:
        return None
    surf_pts = np.concatenate(surf_chunks, axis=0)
    if len(surf_pts) < 500:
        return None

    z_min, z_max = float(np.percentile(surf_pts[:, 2], 0.3)), float(np.percentile(surf_pts[:, 2], 99.7))
    slice_step = max(5.5 * p_med, 0.018)
    z_edges = np.arange(z_min, z_max + slice_step * 0.5, slice_step)
    if len(z_edges) < 10:
        return None

    slice_records: list[tuple[float, np.ndarray, float, float, float]] = []
    for i in range(len(z_edges) - 1):
        zlo, zhi = float(z_edges[i]), float(z_edges[i + 1])
        sl = surf_pts[(surf_pts[:, 2] >= zlo) & (surf_pts[:, 2] < zhi)]
        if len(sl) < 150:
            continue
        med_xy = np.median(sl[:, :2], axis=0)
        fit = _fit_circle_2d_robust(sl[:, :2], med_xy, band_tol=max(4.2 * p_med, 0.014))
        if fit is None:
            continue
        c_xy, rad, p90_res = fit
        rel_xy = sl[:, :2] - c_xy[None, :]
        near_ring = np.abs(np.hypot(rel_xy[:, 0], rel_xy[:, 1]) - rad) <= max(4.5 * p_med, 0.015)
        if int(near_ring.sum()) < 180:
            continue
        angs = np.arctan2(rel_xy[near_ring, 1], rel_xy[near_ring, 0])
        octants = len(set(np.floor((angs + math.pi) / (math.pi / 4.0)).astype(int) % 8))
        if octants >= 6 and p90_res <= 4.2 * p_med and 35.0 * p_med <= rad <= 140.0 * p_med:
            slice_records.append((0.5 * (zlo + zhi), c_xy, rad, p90_res, float(octants)))

    if len(slice_records) < 8:
        return None

    # Find longest contiguous run of slices with consistent circle centers and smooth meridian radius!
    best_run: list[tuple[float, np.ndarray, float, float, float]] = []
    cur_run = [slice_records[0]]
    for rec in slice_records[1:]:
        prev = cur_run[-1]
        z_gap = rec[0] - prev[0]
        c_shift = float(np.linalg.norm(rec[1] - np.median([r[1] for r in cur_run], axis=0)))
        r_step = abs(rec[2] - prev[2])
        if z_gap <= 2.2 * slice_step and c_shift <= 2.5 * p_med and r_step <= 8.0 * p_med:
            cur_run.append(rec)
        else:
            if len(cur_run) > len(best_run):
                best_run = cur_run
            cur_run = [rec]
    if len(cur_run) > len(best_run):
        best_run = cur_run

    if len(best_run) < 8:
        return None

    zs = np.array([r[0] for r in best_run], dtype=np.float64)
    ctrs = np.array([r[1] for r in best_run], dtype=np.float64)
    rads = np.array([r[2] for r in best_run], dtype=np.float64)

    # Fit exact 3D revolution axis line: x(z) = sx*z + ix, y(z) = sy*z + iy
    sx, ix = np.polyfit(zs, ctrs[:, 0], 1)
    sy, iy = np.polyfit(zs, ctrs[:, 1], 1)
    axis_dir = np.array([sx, sy, 1.0], dtype=np.float64)
    axis_dir /= float(np.linalg.norm(axis_dir))
    axis_origin = np.array([ix, iy, 0.0], dtype=np.float64)
    # Project origin orthogonal to axis_dir so h = (X - axis_origin) · axis_dir matches z closely
    axis_origin = axis_origin - float(np.dot(axis_origin, axis_dir)) * axis_dir

    # Orthonormal basis (e1, e2, axis_dir)
    ref_x = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    e1 = ref_x - float(np.dot(ref_x, axis_dir)) * axis_dir
    e1 /= float(np.linalg.norm(e1))
    e2 = np.cross(axis_dir, e1)
    e2 /= float(np.linalg.norm(e2))

    # Recompute axial coordinates h of slices along axis_dir and lightly smooth profile_r
    slice_pts_3d = np.column_stack([ctrs[:, 0], ctrs[:, 1], zs])
    hs = (slice_pts_3d - axis_origin[None, :]) @ axis_dir
    if len(rads) >= 5:
        r_pad = np.pad(rads, 1, mode="edge")
        rads_smooth = 0.25 * r_pad[:-2] + 0.50 * r_pad[1:-1] + 0.25 * r_pad[2:]
    else:
        rads_smooth = rads

    center_std = float(np.hypot(ctrs[:, 0] - (sx * zs + ix), ctrs[:, 1] - (sy * zs + iy)).std())
    tilt_deg = float(math.degrees(math.acos(np.clip(axis_dir[2], -1.0, 1.0))))

    return {
        "axis_origin": axis_origin,
        "axis_dir": axis_dir,
        "e1": e1,
        "e2": e2,
        "profile_h": hs,
        "profile_r": rads_smooth,
        "h_min": float(hs[0]),
        "h_max": float(hs[-1]),
        "center_std_world": center_std,
        "axis_tilt_deg": tilt_deg,
    }


def _canonical_unit_axis(vec: np.ndarray) -> np.ndarray:
    """Canonicalize an unoriented 3D axis direction in RP^2 to a deterministic hemisphere."""
    u = np.asarray(vec, dtype=np.float64)
    u = u / max(float(np.linalg.norm(u)), 1e-12)
    if abs(u[2]) > 0.15:
        return u if u[2] > 0.0 else -u
    if abs(u[0]) > 0.15:
        return u if u[0] > 0.0 else -u
    return u if u[1] >= 0.0 else -u


def _make_axis_frame(axis_dir: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    a = _canonical_unit_axis(axis_dir)
    ref = np.array([1.0, 0.0, 0.0], dtype=np.float64) if abs(a[0]) < 0.82 else np.array([0.0, 1.0, 0.0], dtype=np.float64)
    e1 = ref - float(np.dot(ref, a)) * a
    e1 /= max(float(np.linalg.norm(e1)), 1e-12)
    e2 = np.cross(a, e1)
    e2 /= max(float(np.linalg.norm(e2)), 1e-12)
    return a, e1, e2


def _fit_disc_outer_boundary_2d(
    xy: np.ndarray, p_scale: float
) -> tuple[np.ndarray, float, float, float, int, int] | None:
    """Fit 97th-percentile 2D outer boundary circle to a filled or annular planar/conical patch across 36 sectors."""
    if len(xy) < 65:
        return None
    c_est = 0.5 * (np.percentile(xy, 2.0, axis=0) + np.percentile(xy, 98.0, axis=0))
    bp: np.ndarray | None = None
    rad = 0.0
    for _ in range(3):
        rel = xy - c_est[None, :]
        rr = np.hypot(rel[:, 0], rel[:, 1])
        ang = np.arctan2(rel[:, 1], rel[:, 0])
        sec = np.floor((ang + math.pi) / (2.0 * math.pi / 36.0)).astype(int) % 36
        b_pts: list[np.ndarray] = []
        for s in range(36):
            m = sec == s
            if int(m.sum()) >= 3:
                r_top = float(np.percentile(rr[m], 97.0))
                tol_r = max(2.2 * p_scale, 0.03 * r_top)
                idx_s = np.where(m & (np.abs(rr - r_top) <= tol_r))[0]
                if len(idx_s) > 0:
                    b_pts.append(xy[idx_s].mean(axis=0))
        if len(b_pts) < 15:
            return None
        bp = np.asarray(b_pts, dtype=np.float64)
        A = np.column_stack([2.0 * bp[:, 0], 2.0 * bp[:, 1], np.ones(len(bp), dtype=np.float64)])
        try:
            sol, _, rk, _ = np.linalg.lstsq(A, bp[:, 0] ** 2 + bp[:, 1] ** 2, rcond=None)
        except np.linalg.LinAlgError:
            return None
        if rk < 3:
            return None
        cx, cy, c0 = float(sol[0]), float(sol[1]), float(sol[2])
        r_sq = c0 + cx * cx + cy * cy
        if not np.isfinite(r_sq) or r_sq <= 1e-8 or r_sq > 4.0:
            return None
        c_est = np.array([cx, cy], dtype=np.float64)
        rad = math.sqrt(r_sq)

    if bp is None:
        return None
    res = np.abs(np.hypot(bp[:, 0] - c_est[0], bp[:, 1] - c_est[1]) - rad)
    p90_res = float(np.percentile(res, 90.0))
    rr_all = np.hypot(xy[:, 0] - c_est[0], xy[:, 1] - c_est[1])
    if float(np.median(rr_all)) < 0.84 * rad:
        rad /= math.sqrt(0.96)
    outside_frac = float(np.mean(rr_all > rad + 3.6 * p_scale))
    octs = len(
        set(np.floor((np.arctan2(bp[:, 1] - c_est[1], bp[:, 0] - c_est[0]) + math.pi) / (math.pi / 4.0)).astype(int) % 8)
    )
    return c_est, rad, p90_res, outside_frac, len(bp), octs


def _discover_arbitrary_axis_coaxial_families(
    ridges: list[ConsolidatedRidgeChain],
    bundle: MultiModalSceneBundle,
    evaluator: GPUViewFieldEvaluator,
    device: torch.device,
    start_fam_id: int = 0,
    start_cid: int = 510000,
    start_nid: int = 510000,
) -> tuple[
    list[ConsolidatedRidgeChain],
    list[ParametricCurvePrimitive],
    list[JunctionNode],
    list[CoaxialRingFamilySpec],
    dict[str, Any],
]:
    """Discover arbitrary-axis (a in S^2: tilted, horizontal, or vertical) coaxial cylinders, cones, & circular discs."""
    if len(ridges) < 4:
        return ridges, [], [], [], {"arb_detected_families": 0, "arb_coaxial_rings": 0}

    p = bundle.median_pixel_scale
    mids = np.array([r.points_3d[len(r.points_3d) // 2] for r in ridges], dtype=np.float64)
    ridge_tangs = [_compute_polyline_tangents(r.points_3d) for r in ridges]
    mid_tangs = np.array([rt[len(rt) // 2] for rt in ridge_tangs], dtype=np.float64)
    ridge_lens = np.array([np.linalg.norm(np.diff(r.points_3d, axis=0), axis=1).sum() for r in ridges], dtype=np.float64)
    mid_tree = cKDTree(mids)

    # --- Source A: Surface-normal 36-sector circular disc/drumhead discovery + axial drum-hoop scan ---
    surf_pts, surf_nrms = _gather_oriented_surface_points(bundle, max_pts=120000)
    disc_seeds: list[dict[str, Any]] = []
    if len(surf_pts) >= 300:
        hemi = _fibonacci_hemisphere_dirs(180)
        best_b = np.argmax(np.abs(surf_nrms @ hemi.T), axis=1)
        b_counts = np.bincount(best_b, minlength=len(hemi))
        cos_cone = math.cos(math.radians(15.0))
        raw_discs: list[dict[str, Any]] = []
        for b_i in np.where(b_counts >= 55)[0]:
            n0 = hemi[b_i]
            sub_p = surf_pts[np.abs(surf_nrms @ n0) >= cos_cone]
            if len(sub_p) < 70:
                continue
            sdm = cKDTree(sub_p).sparse_distance_matrix(cKDTree(sub_p), max_distance=6.8 * p, output_type="coo_matrix")
            _, labels = connected_components(sdm, directed=False)
            _, cnts = np.unique(labels, return_counts=True)
            for cid_c in np.where(cnts >= 70)[0]:
                comp = sub_p[labels == cid_c]
                c_m = comp.mean(axis=0)
                _, _, vt = np.linalg.svd(comp - c_m[None, :], full_matrices=False)
                a_dir, e1, e2 = _make_axis_frame(vt[-1])
                if float(np.percentile(np.abs((comp - c_m[None, :]) @ a_dir), 90.0)) > 8.5 * p:
                    continue
                xy = np.column_stack([(comp - c_m[None, :]) @ e1, (comp - c_m[None, :]) @ e2])
                fit = _fit_disc_outer_boundary_2d(xy, p)
                if fit is None:
                    continue
                c2, rad, p90_r, out_f, n_sec, octs = fit
                if octs >= 5 and n_sec >= 16 and out_f <= 0.042 and p90_r <= 2.7 * p and 15.0 * p <= rad <= 165.0 * p:
                    c3 = c_m + c2[0] * e1 + c2[1] * e2
                    raw_discs.append({
                        "center": c3,
                        "normal": a_dir,
                        "e1": e1,
                        "e2": e2,
                        "radius": rad,
                        "n_sec": n_sec,
                        "octs": octs,
                        "p90_p": p90_r / p,
                        "surf_cnt": len(comp),
                    })
        raw_discs.sort(key=lambda d: (-d["n_sec"], d["p90_p"]))
        for rd in raw_discs:
            if not any(
                abs(float(np.dot(rd["normal"], u["normal"]))) > 0.975
                and float(np.linalg.norm(rd["center"] - u["center"])) < 5.0 * p
                and abs(rd["radius"] - u["radius"]) < 5.0 * p
                for u in disc_seeds
            ):
                disc_seeds.append(rd)

    # --- Source B: 3D curved ridge arcs & Parent-Zucker oriented segment pairs ---
    cand_circles: list[dict[str, Any]] = []
    for i, r in enumerate(ridges):
        if len(r.points_3d) >= 5 and ridge_lens[i] >= 5.0 * p:
            _, err, meta = fit_circular_arc_to_polyline(r.points_3d)
            if (
                meta.get("valid")
                and err <= 1.15 * p
                and math.radians(14.0) <= meta["sweep_rad"] <= math.radians(355.0)
                and 12.0 * p <= meta["radius"] <= 165.0 * p
            ):
                n_u, e1, e2 = _make_axis_frame(meta["normal"])
                cand_circles.append({"center": meta["center"].copy(), "normal": n_u, "e1": e1, "e2": e2, "radius": float(meta["radius"])})

    for i, j in mid_tree.query_pairs(r=28.0 * p):
        if ridge_lens[i] > 40.0 * p or ridge_lens[j] > 40.0 * p:
            continue
        circ = _circle_from_two_oriented_segments(mids[i], mid_tangs[i], mids[j], mid_tangs[j], p)
        if circ is not None and 12.0 * p <= circ["radius"] <= 165.0 * p:
            n_u, e1, e2 = _make_axis_frame(circ["normal"])
            cand_circles.append({"center": circ["center"].copy(), "normal": n_u, "e1": e1, "e2": e2, "radius": float(circ["radius"])})

    # Also seed axial hoop candidates along each discovered circular disc/drumhead axis!
    for ds in disc_seeds:
        for dh_step in np.linspace(-150.0 * p, 150.0 * p, 61):
            for dr_step in (-2.6 * p, -1.6 * p, -0.6 * p, 0.4 * p, 1.8 * p):
                cand_circles.append({
                    "center": ds["center"] + float(dh_step) * ds["normal"],
                    "normal": ds["normal"].copy(),
                    "e1": ds["e1"].copy(),
                    "e2": ds["e2"].copy(),
                    "radius": float(ds["radius"] + dr_step),
                    "from_disc": abs(float(dh_step)) <= 5.5 * p,
                    "disc_n_sec": ds["n_sec"],
                    "disc_octs": ds["octs"],
                    "disc_cnt": ds["surf_cnt"],
                })

    if not cand_circles:
        return ridges, [], [], [], {"arb_detected_families": 0, "arb_coaxial_rings": 0}

    dedup: list[dict[str, Any]] = []
    seen_k: set[tuple[int, ...]] = set()
    for cc in cand_circles:
        k = (
            int(round(cc["center"][0] / (2.2 * p))),
            int(round(cc["center"][1] / (2.2 * p))),
            int(round(cc["center"][2] / (2.2 * p))),
            int(round(cc["normal"][0] / 0.10)),
            int(round(cc["normal"][1] / 0.10)),
            int(round(cc["normal"][2] / 0.10)),
            int(round(cc["radius"] / (2.2 * p))),
        )
        if k not in seen_k or cc.get("from_disc", False):
            seen_k.add(k)
            dedup.append(cc)

    cos_tang_thr = float(np.cos(np.deg2rad(24.0)))
    refined_cands: list[dict[str, Any]] = []
    for cc in dedup:
        c_pos, n_u, e1, e2, rad = cc["center"], cc["normal"], cc["e1"], cc["e2"], cc["radius"]
        is_disc_seed = bool(cc.get("from_disc", False))
        near_ids = mid_tree.query_ball_point(c_pos, r=rad + 5.0 * p)

        inlier_rids: list[int] = []
        pts_chunks: list[np.ndarray] = []
        for r_idx in near_ids:
            pts_r = ridges[r_idx].points_3d
            rel = pts_r - c_pos[None, :]
            if float(np.max(np.abs(rel @ n_u))) > 3.2 * p:
                continue
            x2 = rel @ e1
            y2 = rel @ e2
            rr = np.hypot(x2, y2)
            if float(np.max(np.abs(rr - rad))) > 3.2 * p:
                continue
            ct = (-y2[:, None] * e1[None, :] + x2[:, None] * e2[None, :]) / np.maximum(rr[:, None], 1e-9)
            if float(np.mean(np.abs(np.sum(ridge_tangs[r_idx] * ct, axis=1)) >= cos_tang_thr)) < 0.75:
                continue
            inlier_rids.append(r_idx)
            pts_chunks.append(pts_r)

        if is_disc_seed:
            # Surface-calibrated disc boundary already has high-accuracy 3D plane & circle fit!
            refined_cands.append({
                "center": c_pos.copy(),
                "normal": n_u.copy(),
                "e1": e1.copy(),
                "e2": e2.copy(),
                "radius": float(rad),
                "inlier_rids": inlier_rids,
                "num_pts": max(int(cc.get("disc_cnt", 120)), sum(len(x) for x in pts_chunks)),
                "obs_deg": float(10.0 * cc.get("disc_n_sec", 18)),
                "obs_octants": int(cc.get("disc_octs", 6)),
                "from_disc": True,
            })
            continue

        if not pts_chunks:
            continue
        pts_all = np.concatenate(pts_chunks, axis=0)
        if len(pts_all) < 14:
            continue

        c_mean = pts_all.mean(axis=0)
        _, _, vt = np.linalg.svd(pts_all - c_mean[None, :], full_matrices=False)
        n_ref, e1_r, e2_r = _make_axis_frame(vt[-1])
        rel_a = pts_all - c_mean[None, :]
        if float(np.percentile(np.abs(rel_a @ n_ref), 90.0)) > 2.8 * p:
            continue
        xy = np.column_stack([rel_a @ e1_r, rel_a @ e2_r])
        A = np.column_stack([2.0 * xy[:, 0], 2.0 * xy[:, 1], np.ones(len(xy), dtype=np.float64)])
        try:
            sol, _, rank, _ = np.linalg.lstsq(A, xy[:, 0] ** 2 + xy[:, 1] ** 2, rcond=None)
        except np.linalg.LinAlgError:
            continue
        if rank < 3:
            continue
        cx2, cy2, c0 = float(sol[0]), float(sol[1]), float(sol[2])
        r_sq = c0 + cx2 * cx2 + cy2 * cy2
        if not np.isfinite(r_sq) or r_sq <= 0.0:
            continue
        r_ref = math.sqrt(r_sq)
        if not (14.0 * p <= r_ref <= 165.0 * p):
            continue
        dx = xy[:, 0] - cx2
        dy = xy[:, 1] - cy2
        d_xy = np.hypot(dx, dy)
        if float(np.percentile(np.abs(d_xy - r_ref), 90.0)) > 2.8 * p:
            continue

        c_3d = c_mean + cx2 * e1_r + cy2 * e2_r
        angs = np.arctan2(dy, dx)
        bins_10deg = set(np.floor((angs + math.pi) / (math.pi / 18.0)).astype(int) % 36)
        octs = set(np.floor((angs + math.pi) / (math.pi / 4.0)).astype(int) % 8)
        obs_deg = 10.0 * len(bins_10deg)
        if len(octs) < 4 or obs_deg < 110.0:
            continue

        refined_cands.append({
            "center": c_3d,
            "normal": n_ref,
            "e1": e1_r,
            "e2": e2_r,
            "radius": r_ref,
            "inlier_rids": inlier_rids,
            "num_pts": len(pts_all),
            "obs_deg": obs_deg,
            "obs_octants": len(octs),
            "from_disc": False,
        })

    if not refined_cands:
        return ridges, [], [], [], {"arb_detected_families": 0, "arb_coaxial_rings": 0}

    # Batch 360-degree GPU multi-view verification (72 angular samples per candidate circle)
    S_ring = 72
    th_grid = np.linspace(0.0, 2.0 * math.pi, S_ring, endpoint=False, dtype=np.float64)
    cos_g, sin_g = np.cos(th_grid), np.sin(th_grid)
    ring_pts_batch: list[np.ndarray] = []
    ring_tng_batch: list[np.ndarray] = []
    for rc in refined_cands:
        er = cos_g[:, None] * rc["e1"][None, :] + sin_g[:, None] * rc["e2"][None, :]
        et = -sin_g[:, None] * rc["e1"][None, :] + cos_g[:, None] * rc["e2"][None, :]
        ring_pts_batch.append(rc["center"][None, :] + rc["radius"] * er)
        ring_tng_batch.append(et)

    pts_flat = np.concatenate(ring_pts_batch, axis=0)
    tng_flat = np.concatenate(ring_tng_batch, axis=0)
    M_tot = len(pts_flat)
    max_fsv_views = max(1, int(0.12 * max(1, evaluator.num_depth_views)))
    cos_2d_thr = float(np.cos(np.deg2rad(24.0)))

    hull_viol_arr = np.zeros(M_tot, dtype=np.float64)
    fsv_cnt_arr = np.zeros(M_tot, dtype=np.int32)
    unocc_cnt_arr = np.zeros(M_tot, dtype=np.int32)
    corrob_cnt_arr = np.zeros(M_tot, dtype=np.int32)

    with torch.no_grad():
        X_t = torch.tensor(pts_flat, dtype=torch.float32, device=device)
        T_t = torch.tensor(tng_flat, dtype=torch.float32, device=device)
        chunk = 14400
        for s in range(0, M_tot, chunk):
            e = min(M_tot, s + chunk)
            Xc = torch.einsum("vij,nj->vni", evaluator.R, X_t[s:e]) + evaluator.t[:, None, :]
            z = Xc[:, :, 2].clamp(min=1e-3)
            u = evaluator.fx[:, None] * (Xc[:, :, 0] / z) + evaluator.cx[:, None]
            v = evaluator.fy[:, None] * (Xc[:, :, 1] / z) + evaluator.cy[:, None]
            in_f = (Xc[:, :, 2] > 0.2) & (u >= 2.0) & (u <= evaluator.w - 3.0) & (v >= 2.0) & (v <= evaluator.h - 3.0)

            gx = 2.0 * (u / (evaluator.w - 1.0)) - 1.0
            gy = 2.0 * (v / (evaluator.h - 1.0)) - 1.0
            grid = torch.stack([gx, gy], dim=-1).unsqueeze(2)
            smp = F.grid_sample(
                evaluator.maps[:, [0, 2], :, :], grid, mode="bilinear", padding_mode="border", align_corners=True
            ).squeeze(-1)
            smp_d = F.grid_sample(
                evaluator.maps[:, [4, 5], :, :], grid, mode="nearest", padding_mode="border", align_corners=True
            ).squeeze(-1)
            t2d = F.grid_sample(
                evaluator.tang2d, grid, mode="bilinear", padding_mode="border", align_corners=True
            ).squeeze(-1).permute(0, 2, 1)

            alpha = smp[:, 0, :]
            edt = smp[:, 1, :]
            surf_d = smp_d[:, 0, :]
            d_jump = smp_d[:, 1, :]

            in_f_sum = in_f.sum(dim=0)
            h_viol = torch.where(
                in_f_sum >= 2,
                (in_f & (alpha < 0.03)).float().sum(dim=0) / in_f_sum.clamp(min=1).float(),
                torch.zeros_like(in_f_sum, dtype=torch.float32),
            )
            smooth_op = evaluator.has_depth[:, None] & in_f & (alpha > 0.94) & (surf_d > 0.2) & (d_jump < 0.006)
            # Guard against foreground cymbal/hoop rim projecting over background drum: true empty-space violation has edt > 3.8!
            fsv = (smooth_op & (z < surf_d - 6.5 * p) & (edt > 3.8)).sum(dim=0)
            occ = smooth_op & (z > surf_d + 6.5 * p)
            unocc = in_f & (~occ)

            Tc = torch.einsum("vij,nj->vni", evaluator.R, T_t[s:e])
            du = evaluator.fx[:, None] * (Tc[:, :, 0] / z - Xc[:, :, 0] * Tc[:, :, 2] / (z * z))
            dv = evaluator.fy[:, None] * (Tc[:, :, 1] / z - Xc[:, :, 1] * Tc[:, :, 2] / (z * z))
            pt2 = F.normalize(torch.stack([du, dv], dim=-1), dim=-1, eps=1e-6)
            tt2 = F.normalize(t2d, dim=-1, eps=1e-6)
            align2 = torch.abs((pt2 * tt2).sum(dim=-1))

            edge_hit = unocc & (edt <= 2.8) & (align2 >= cos_2d_thr)
            hull_viol_arr[s:e] = h_viol.cpu().numpy()
            fsv_cnt_arr[s:e] = fsv.cpu().numpy()
            unocc_cnt_arr[s:e] = unocc.sum(dim=0).cpu().numpy()
            corrob_cnt_arr[s:e] = edge_hit.sum(dim=0).cpu().numpy()

    verified_rings: list[dict[str, Any]] = []
    for idx_c, rc in enumerate(refined_cands):
        sl = slice(idx_c * S_ring, (idx_c + 1) * S_ring)
        if bundle.has_silhouette_mask and float(hull_viol_arr[sl].max()) > 0.048:
            continue
        if float(np.mean(fsv_cnt_arr[sl] > max_fsv_views)) > 0.08:
            continue
        vis_mask = unocc_cnt_arr[sl] >= 2
        if int(vis_mask.sum()) < int(0.36 * S_ring):
            continue
        corrob_ratio = float(np.mean(corrob_cnt_arr[sl][vis_mask] >= 2))
        min_corrob = 0.80 if rc.get("from_disc", False) else 0.84
        if corrob_ratio < min_corrob:
            continue
        rc["corrob_ratio"] = corrob_ratio
        rc["score"] = float(rc["num_pts"]) * (corrob_ratio ** 3)
        verified_rings.append(rc)

    if not verified_rings:
        return ridges, [], [], [], {"arb_detected_families": 0, "arb_coaxial_rings": 0}

    # Greedy NMS on overlapping 3D circles
    verified_rings.sort(key=lambda d: d["score"], reverse=True)
    nms_rings: list[dict[str, Any]] = []
    cos_nms = float(np.cos(np.deg2rad(9.0)))
    for vr in verified_rings:
        dup = False
        for kr in nms_rings:
            if (
                abs(float(np.dot(vr["normal"], kr["normal"]))) >= cos_nms
                and float(np.linalg.norm(vr["center"] - kr["center"])) <= 3.5 * p
                and abs(vr["radius"] - kr["radius"]) <= 3.5 * p
            ):
                dup = True
                break
        if not dup:
            nms_rings.append(vr)

    # Cluster verified rings into arbitrary-axis coaxial families:
    # same axis orientation (<= 8.5 deg) AND collinear centers orthogonal to axis (<= 3.8p)!
    n_v = len(nms_rings)
    uf = list(range(n_v))

    def find_u(x: int) -> int:
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x

    cos_ax_match = float(np.cos(np.deg2rad(8.5)))
    for i in range(n_v):
        for j in range(i + 1, n_v):
            ni, nj = nms_rings[i]["normal"], nms_rings[j]["normal"]
            dot_n = float(np.dot(ni, nj))
            if abs(dot_n) < cos_ax_match:
                continue
            nj_aligned = nj if dot_n >= 0.0 else -nj
            n_avg = _canonical_unit_axis(ni + nj_aligned)
            dc = nms_rings[j]["center"] - nms_rings[i]["center"]
            dh = abs(float(np.dot(dc, n_avg)))
            d_perp = float(np.linalg.norm(dc - float(np.dot(dc, n_avg)) * n_avg))
            r_max = max(nms_rings[i]["radius"], nms_rings[j]["radius"])
            r_min = min(nms_rings[i]["radius"], nms_rings[j]["radius"])
            # Allow coaxial drum shells/cones (same axis, separated h) OR concentric cymbal bell+rim (dh ~ 0)
            if d_perp <= 3.8 * p and dh <= 190.0 * p and (dh <= 4.5 * p or (r_min / max(r_max, 1e-6)) >= 0.52):
                ri, rj = find_u(i), find_u(j)
                if ri != rj:
                    uf[rj] = ri

    groups: dict[int, list[dict[str, Any]]] = {}
    for i, vr in enumerate(nms_rings):
        groups.setdefault(find_u(i), []).append(vr)

    out_curves: list[ParametricCurvePrimitive] = []
    out_nodes: list[JunctionNode] = []
    out_fams: list[CoaxialRingFamilySpec] = []
    absorbed_rids: set[int] = set()
    next_cid = start_cid
    next_nid = start_nid
    cur_fam_id = start_fam_id
    view_names = [v.view_name for v in bundle.train_views]

    for grp in sorted(groups.values(), key=lambda g: -sum(x["score"] for x in g)):
        # Multi-ring coaxial family (>=2 rings) OR high-confidence standalone 360-deg disc/cymbal/hoop
        if len(grp) == 1:
            r0 = grp[0]
            if r0["obs_deg"] < 145.0 or r0["obs_octants"] < 5 or r0["corrob_ratio"] < 0.80 or r0["radius"] < 14.0 * p:
                continue

        # Fit shared 3D axis (o_ax, a_dir) across group rings
        n0 = grp[0]["normal"]
        aligned_ns = [
            (g["normal"] if float(np.dot(g["normal"], n0)) >= 0.0 else -g["normal"]) * g["score"]
            for g in grp
        ]
        a_dir, e1, e2 = _make_axis_frame(np.sum(aligned_ns, axis=0))
        weights_g = np.array([g["score"] for g in grp], dtype=np.float64)
        ctrs_g = np.array([g["center"] for g in grp], dtype=np.float64)
        o_mean = np.average(ctrs_g, axis=0, weights=weights_g)
        o_ax = o_mean - float(np.dot(o_mean, a_dir)) * a_dir

        hs_g = np.array([float(np.dot(g["center"] - o_ax, a_dir)) for g in grp], dtype=np.float64)
        rs_g = np.array([float(g["radius"]) for g in grp], dtype=np.float64)
        order = np.argsort(hs_g)
        grp_sorted = [grp[idx] for idx in order]
        hs_sorted = hs_g[order]
        rs_sorted = rs_g[order]

        # Build monotonic/smooth axial profile (handles concentric coplanar rings cleanly)
        if float(hs_sorted[-1] - hs_sorted[0]) >= 3.0 * p and len(hs_sorted) >= 2:
            uniq_h: list[float] = []
            uniq_r: list[float] = []
            for hk, rk in zip(hs_sorted, rs_sorted):
                if not uniq_h or hk - uniq_h[-1] > 1.5 * p:
                    uniq_h.append(float(hk))
                    uniq_r.append(float(rk))
                else:
                    uniq_r[-1] = max(uniq_r[-1], float(rk))
            if len(uniq_h) >= 2:
                prof_h = np.array(uniq_h, dtype=np.float64)
                prof_r = np.array(uniq_r, dtype=np.float64)
                dr_dh_arr = np.gradient(prof_r, prof_h)
            else:
                h_mid = float(hs_sorted.mean())
                prof_h = np.array([h_mid - 1.0 * p, h_mid + 1.0 * p], dtype=np.float64)
                prof_r = np.array([float(rs_sorted.max()), float(rs_sorted.max())], dtype=np.float64)
                dr_dh_arr = np.zeros(2, dtype=np.float64)
        else:
            h_mid = float(hs_sorted.mean())
            prof_h = np.array([h_mid - 1.0 * p, h_mid + 1.0 * p], dtype=np.float64)
            prof_r = np.array([float(rs_sorted.max()), float(rs_sorted.max())], dtype=np.float64)
            dr_dh_arr = np.zeros(2, dtype=np.float64)

        fam_cids: list[int] = []
        fam_hs: list[float] = []
        fam_rs: list[float] = []
        for g_item, hk, rk in zip(grp_sorted, hs_sorted, rs_sorted):
            slk = float(np.interp(np.clip(hk, prof_h[0], prof_h[-1]), prof_h, dr_dh_arr))
            ring_ctr = o_ax + float(hk) * a_dir
            local_inliers = set(g_item["inlier_rids"])
            for r_cand in mid_tree.query_ball_point(ring_ctr, r=float(rk) + 4.5 * p):
                pts_rc = ridges[r_cand].points_3d
                rel_rc = pts_rc - ring_ctr[None, :]
                if float(np.max(np.abs(rel_rc @ a_dir))) <= 3.0 * p:
                    x_rc = rel_rc @ e1
                    y_rc = rel_rc @ e2
                    rr_rc = np.hypot(x_rc, y_rc)
                    if float(np.max(np.abs(rr_rc - rk))) <= 3.0 * p:
                        ct_rc = (-y_rc[:, None] * e1[None, :] + x_rc[:, None] * e2[None, :]) / np.maximum(rr_rc[:, None], 1e-9)
                        if float(np.mean(np.abs(np.sum(ridge_tangs[r_cand] * ct_rc, axis=1)) >= cos_tang_thr)) >= 0.78:
                            local_inliers.add(r_cand)
            absorbed_rids.update(local_inliers)

            near_views: set[str] = set()
            near_pids: set[int] = set()
            for r_i in local_inliers:
                near_views.update(ridges[r_i].supporting_views)
                near_pids.update(ridges[r_i].source_parent_ids)
            if len(near_views) < 4:
                near_views.update(view_names[:8])

            def pt_nrm(theta: float) -> tuple[np.ndarray, np.ndarray]:
                er = math.cos(theta) * e1 + math.sin(theta) * e2
                pt = ring_ctr + float(rk) * er
                # Disc-like when axial span is tiny; cylinder/cone outward normal otherwise
                ns = a_dir.copy() if (prof_h[-1] - prof_h[0]) < 3.0 * p else (er - slk * a_dir)
                ns /= max(float(np.linalg.norm(ns)), 1e-9)
                return pt, ns

            p0, n0_r = pt_nrm(0.0)
            p90, n90_r = pt_nrm(0.5 * math.pi)
            p180, n180_r = pt_nrm(math.pi)
            p270, n270_r = pt_nrm(1.5 * math.pi)

            nid_a, nid_b = next_nid, next_nid + 1
            next_nid += 2
            out_nodes.append(JunctionNode(node_id=nid_a, position=p0, incident=[], kind="SMOOTH_CONTINUATION"))
            out_nodes.append(JunctionNode(node_id=nid_b, position=p180, incident=[], kind="SMOOTH_CONTINUATION"))

            for s_nid, e_nid, c_pts, c_nrms in (
                (nid_a, nid_b, np.vstack([p0, p90, p180]), np.vstack([n0_r, n90_r, n180_r])),
                (nid_b, nid_a, np.vstack([p180, p270, p0]), np.vstack([n180_r, n270_r, n0_r])),
            ):
                cid = next_cid
                next_cid += 1
                rib = RibbonGeometry(
                    edge_class="COAXIAL_RING",
                    control_normals=c_nrms,
                    half_width_px=0.40,
                    thickness_px=0.26,
                    inward_shift_px=0.0,
                    inward_sign=1.0,
                    dihedral_deg=55.0,
                    depth_jump_rel=0.0,
                    albedo_contrast=float(g_item["corrob_ratio"]),
                    coaxial_family_id=cur_fam_id,
                    coaxial_ring_h=float(hk),
                    coaxial_ring_r=float(rk),
                )
                out_curves.append(
                    ParametricCurvePrimitive(
                        curve_id=cid,
                        primitive_type="ARC_3D",
                        control_points=c_pts,
                        knots=clamped_uniform_knots(3, 2),
                        degree=2,
                        start_node_id=s_nid,
                        end_node_id=e_nid,
                        pixel_scale=p,
                        width_px=0.40,
                        opacity=0.135,
                        role="COAXIAL_RING",
                        supporting_views=sorted(near_views),
                        source_parent_ids=sorted(near_pids),
                        confidence=12.0,
                        ribbon=rib,
                    )
                )
                fam_cids.append(cid)
            fam_hs.append(float(hk))
            fam_rs.append(float(rk))

        out_fams.append(
            CoaxialRingFamilySpec(
                family_id=cur_fam_id,
                axis_origin=o_ax,
                axis_dir=a_dir,
                e1=e1,
                e2=e2,
                h_min=float(prof_h[0]),
                h_max=float(prof_h[-1]),
                profile_h=prof_h,
                profile_r=prof_r,
                ring_heights=fam_hs,
                ring_radii=fam_rs,
                member_curve_ids=fam_cids,
            )
        )
        cur_fam_id += 1

    kept: list[ConsolidatedRidgeChain] = []
    for idx, r in enumerate(ridges):
        if idx not in absorbed_rids:
            r.ridge_id = len(kept)
            kept.append(r)

    tilt_angles = [
        round(float(math.degrees(math.acos(np.clip(abs(f.axis_dir[2]), 0.0, 1.0)))), 2) for f in out_fams
    ]
    arb_stats = {
        "arb_detected_families": len(out_fams),
        "arb_coaxial_rings": sum(len(f.ring_heights) for f in out_fams),
        "arb_axis_tilt_deg_list": tilt_angles,
        "arb_absorbed_ridges": len(absorbed_rids),
    }
    return kept, out_curves, out_nodes, out_fams, arb_stats


def consolidate_coaxial_ring_families(
    ridges: list[ConsolidatedRidgeChain],
    bundle: MultiModalSceneBundle,
    evaluator: GPUViewFieldEvaluator,
    device: torch.device,
) -> tuple[
    list[ConsolidatedRidgeChain],
    list[ParametricCurvePrimitive],
    list[JunctionNode],
    list[CoaxialRingFamilySpec],
    dict[str, Any],
]:
    """Detect both vertical lathe vessels AND arbitrary-axis (tilted/horizontal) coaxial cylinders & discs."""
    p_med = bundle.median_pixel_scale
    lathe = _discover_lathe_part_from_multiview_depth(bundle, p_med=p_med)
    if lathe is None:
        rem_r, arb_c, arb_n, arb_f, arb_st = _discover_arbitrary_axis_coaxial_families(
            ridges, bundle=bundle, evaluator=evaluator, device=device, start_fam_id=0, start_cid=510000, start_nid=510000
        )
        arb_st["detected_families"] = len(arb_f)
        arb_st["num_coaxial_rings"] = arb_st.get("arb_coaxial_rings", 0)
        arb_st["num_coaxial_arc_primitives"] = len(arb_c)
        return rem_r, arb_c, arb_n, arb_f, arb_st

    o_ax = lathe["axis_origin"]
    a_dir = lathe["axis_dir"]
    e1 = lathe["e1"]
    e2 = lathe["e2"]
    prof_h = lathe["profile_h"]
    prof_r = lathe["profile_r"]
    h_min = lathe["h_min"]
    h_max = lathe["h_max"]
    dr_dh = np.gradient(prof_r, prof_h)

    # 1. Classify existing ridges relative to the calibrated surface of revolution
    absorbed_shell_rids: list[int] = []
    pruned_interior_ghost_rids: list[int] = []
    pruned_grazing_scratch_rids: list[int] = []
    shell_rib_h_samples: list[np.ndarray] = []
    shell_rib_views: list[tuple[float, list[str], list[int]]] = []

    # Pre-collect meridional candidates on the pot wall to check front-facing edge support
    merid_cands: list[int] = []
    for idx, r in enumerate(ridges):
        pts = r.points_3d
        rel = pts - o_ax[None, :]
        h_pts = rel @ a_dir
        h_mean = float(h_pts.mean())
        if not (h_min - 3.0 * p_med <= h_mean <= h_max + 2.0 * p_med):
            continue

        x_p = rel @ e1
        y_p = rel @ e2
        rho_pts = np.hypot(x_p, y_p)
        rho_mean = float(rho_pts.mean())
        r_exp = float(np.interp(np.clip(h_mean, h_min, h_max), prof_h, prof_r))

        # Opaque closed vessel interior (below the open top soil plane h_max - 5.5p): nothing inside can be seen!
        if h_mean < h_max - 5.5 * p_med and float(np.max(rho_pts)) < r_exp - 3.5 * p_med:
            pruned_interior_ghost_rids.append(idx)
            continue

        # Near the outer rotational shell
        if abs(rho_mean - r_exp) <= 6.8 * p_med:
            tangs = _compute_polyline_tangents(pts)
            e_theta = (-y_p[:, None] * e1[None, :] + x_p[:, None] * e2[None, :]) / np.maximum(rho_pts[:, None], 1e-8)
            cos_circ = float(np.mean(np.abs(np.sum(tangs * e_theta, axis=1))))
            cos_ax = float(np.mean(np.abs(tangs @ a_dir)))

            if cos_circ >= 0.66:
                absorbed_shell_rids.append(idx)
                shell_rib_h_samples.append(h_pts)
                shell_rib_views.append((h_mean, list(r.supporting_views), list(r.source_parent_ids)))
            elif h_mean < h_max - 5.0 * p_med and cos_ax >= 0.72 and abs(rho_mean - r_exp) <= 3.8 * p_med:
                merid_cands.append(idx)

    # Verify whether meridional candidates on the smooth rotational wall are fake grazing horizon lines
    if merid_cands:
        cams = np.stack([v.cam_center for v in bundle.train_views], axis=0)
        with torch.no_grad():
            for idx in merid_cands:
                mid_pt = ridges[idx].points_3d[len(ridges[idx].points_3d) // 2]
                rel_m = mid_pt - o_ax
                hm = float(np.dot(rel_m, a_dir))
                slp = float(np.interp(np.clip(hm, h_min, h_max), prof_h, dr_dh))
                rx, ry = float(np.dot(rel_m, e1)), float(np.dot(rel_m, e2))
                rn = max(math.hypot(rx, ry), 1e-8)
                n_surf = (rx / rn) * e1 + (ry / rn) * e2 - slp * a_dir
                n_surf /= float(np.linalg.norm(n_surf))

                # Check front-facing views (cos_inc > 0.55)
                v_dirs = cams - mid_pt[None, :]
                v_dirs /= np.maximum(np.linalg.norm(v_dirs, axis=1, keepdims=True), 1e-8)
                front_vs = np.where((v_dirs @ n_surf) > 0.55)[0]
                if len(front_vs) >= 2:
                    # Project mid_pt onto those front views and check 2D edge_dt
                    front_edts = [
                        float(
                            bundle.train_views[vi].edge_dt[
                                int(np.clip(round(bundle.train_views[vi].fy * ((bundle.train_views[vi].w2c[:3, :3] @ mid_pt + bundle.train_views[vi].w2c[:3, 3])[1] / max((bundle.train_views[vi].w2c[:3, :3] @ mid_pt + bundle.train_views[vi].w2c[:3, 3])[2], 0.2)) + bundle.train_views[vi].cy), 0, bundle.train_views[vi].height - 1)),
                                int(np.clip(round(bundle.train_views[vi].fx * ((bundle.train_views[vi].w2c[:3, :3] @ mid_pt + bundle.train_views[vi].w2c[:3, 3])[0] / max((bundle.train_views[vi].w2c[:3, :3] @ mid_pt + bundle.train_views[vi].w2c[:3, 3])[2], 0.2)) + bundle.train_views[vi].cx), 0, bundle.train_views[vi].width - 1)),
                            ]
                        )
                        for vi in front_vs
                    ]
                    if min(front_edts) > 3.2:
                        pruned_grazing_scratch_rids.append(idx)

    # 2. Dense 32-view circumferential groove response scan along TRUE surface of revolution
    n_h = max(160, int(round((h_max - h_min) / (0.55 * p_med))))
    h_dense = np.linspace(h_min, h_max, n_h, dtype=np.float64)
    r_dense = np.interp(h_dense, prof_h, prof_r)
    sl_dense = np.interp(h_dense, prof_h, dr_dh)
    n_th = 160
    thetas = np.linspace(0.0, 2.0 * math.pi, n_th, endpoint=False, dtype=np.float64)

    Hg, Tg = np.meshgrid(h_dense, thetas, indexing="ij")
    Rg = np.interp(Hg, prof_h, prof_r)
    Sg = np.interp(Hg, prof_h, dr_dh)
    cos_t, sin_t = np.cos(Tg), np.sin(Tg)

    er_grid = cos_t[..., None] * e1[None, None, :] + sin_t[..., None] * e2[None, None, :]
    et_grid = -sin_t[..., None] * e1[None, None, :] + cos_t[..., None] * e2[None, None, :]
    pts_grid = (o_ax[None, None, :] + Hg[..., None] * a_dir[None, None, :] + Rg[..., None] * er_grid).reshape(-1, 3)
    tang_grid = et_grid.reshape(-1, 3)
    nrm_grid = (er_grid - Sg[..., None] * a_dir[None, None, :]).reshape(-1, 3)
    nrm_grid /= np.maximum(np.linalg.norm(nrm_grid, axis=1, keepdims=True), 1e-9)

    with torch.no_grad():
        X_t = torch.tensor(pts_grid, dtype=torch.float32, device=device)
        T_t = torch.tensor(tang_grid, dtype=torch.float32, device=device)
        N_t = torch.tensor(nrm_grid, dtype=torch.float32, device=device)
        cams_t = torch.tensor(np.stack([v.cam_center for v in bundle.train_views]), dtype=torch.float32, device=device)
        orig_v_mask = torch.tensor(
            [bool(v.is_original_c2l_build and v.depth is not None) for v in bundle.train_views],
            dtype=torch.bool,
            device=device,
        )
        scan_v_mask = orig_v_mask if int(orig_v_mask.sum().item()) >= 4 else evaluator.has_depth

        rib_resp = np.zeros(len(pts_grid), dtype=np.float64)
        vis_cnt = np.zeros(len(pts_grid), dtype=np.int32)
        chunk = 12800
        for s in range(0, len(pts_grid), chunk):
            e = min(len(pts_grid), s + chunk)
            Xc = torch.einsum("vij,nj->vni", evaluator.R, X_t[s:e]) + evaluator.t[:, None, :]
            z = Xc[:, :, 2].clamp(min=1e-3)
            u = evaluator.fx[:, None] * (Xc[:, :, 0] / z) + evaluator.cx[:, None]
            v = evaluator.fy[:, None] * (Xc[:, :, 1] / z) + evaluator.cy[:, None]
            gx = 2.0 * (u / (evaluator.w - 1.0)) - 1.0
            gy = 2.0 * (v / (evaluator.h - 1.0)) - 1.0
            grid = torch.stack([gx, gy], dim=-1).unsqueeze(2)

            # evaluator.maps channels: [0:alpha, 1:outside_dt, 2:edge_dt, 3:edge_strength, 4:depth, 5:depth_jump]
            smp = F.grid_sample(
                evaluator.maps[:, [0, 2, 3], :, :], grid, mode="bilinear", padding_mode="border", align_corners=True
            ).squeeze(-1)
            smp_d = F.grid_sample(
                evaluator.maps[:, 4:5, :, :], grid, mode="nearest", padding_mode="border", align_corners=True
            ).squeeze(-1)
            t2d = F.grid_sample(
                evaluator.tang2d, grid, mode="bilinear", padding_mode="border", align_corners=True
            ).squeeze(-1).permute(0, 2, 1)

            v_dir = F.normalize(cams_t[:, None, :] - X_t[None, s:e, :], dim=-1, eps=1e-8)
            cos_inc = (N_t[None, s:e, :] * v_dir).sum(dim=-1)

            front_ok = (
                scan_v_mask[:, None]
                & (Xc[:, :, 2] > 0.2)
                & (u >= 2.0)
                & (u <= evaluator.w - 3.0)
                & (v >= 2.0)
                & (v <= evaluator.h - 3.0)
                & (cos_inc > 0.25)
                & (smp[:, 0, :] > 0.88)
                & (z <= smp_d[:, 0, :] + 7.5 * p_med)
            )

            Tc = torch.einsum("vij,nj->vni", evaluator.R, T_t[s:e])
            du = evaluator.fx[:, None] * (Tc[:, :, 0] / z - Xc[:, :, 0] * Tc[:, :, 2] / (z * z))
            dv = evaluator.fy[:, None] * (Tc[:, :, 1] / z - Xc[:, :, 1] * Tc[:, :, 2] / (z * z))
            pt2 = F.normalize(torch.stack([du, dv], dim=-1), dim=-1, eps=1e-6)
            tt2 = F.normalize(t2d, dim=-1, eps=1e-6)
            c_align = torch.abs((pt2 * tt2).sum(dim=-1))

            # Combine darkness (smp[:, 2, :] in 3-channel slice -> edge_strength!) weighted by circumferential tangent
            edge_str = smp[:, 2, :]
            hit_val = front_ok.float() * edge_str * (0.35 + 0.65 * (c_align ** 4))
            f_sum = front_ok.float().sum(dim=0)
            rib_resp[s:e] = (hit_val.sum(dim=0) / f_sum.clamp(min=1.0)).cpu().numpy()
            vis_cnt[s:e] = (front_ok & (smp[:, 1, :] <= 2.2) & (c_align >= 0.86)).sum(dim=0).cpu().numpy()

    resp_2d = rib_resp.reshape(n_h, n_th)
    mean_resp = resp_2d.mean(axis=1)

    # Boost with empirical KDE of absorbed circumferential ridge heights so every detected rib band is captured
    if shell_rib_h_samples:
        all_rib_h = np.concatenate(shell_rib_h_samples)
        kde = np.exp(-0.5 * ((h_dense[:, None] - all_rib_h[None, :]) / (1.5 * p_med)) ** 2).sum(axis=1)
        if float(kde.max()) > 0.0:
            kde /= float(kde.max())
        combined_score = 0.75 * mean_resp + 0.04 * kde
    else:
        combined_score = mean_resp

    min_pk_dist = max(5, int(round((6.0 * p_med) / max(h_dense[1] - h_dense[0], 1e-6))))
    peaks, _ = find_peaks(combined_score, distance=min_pk_dist, prominence=0.008)
    chosen_pk_indices = list(int(pk) for pk in peaks)

    # Ensure top mouth rim (near h_max) and base ring (near h_min) are included if not already within 5p
    if not any(abs(h_dense[i] - h_min) < 5.5 * p_med for i in chosen_pk_indices):
        chosen_pk_indices.insert(0, 1)
    if not any(abs(h_dense[i] - h_max) < 5.5 * p_med for i in chosen_pk_indices):
        chosen_pk_indices.append(n_h - 2)
    chosen_pk_indices = sorted(set(chosen_pk_indices))

    # 3. Instantiate exact closed 360-degree coaxial rings (each as two 180-degree ARC_3D halves sharing 2 antipodal nodes)
    view_names = [v.view_name for v in bundle.train_views]
    coaxial_curves: list[ParametricCurvePrimitive] = []
    coaxial_nodes: list[JunctionNode] = []
    ring_heights_out: list[float] = []
    ring_radii_out: list[float] = []
    member_cids: list[int] = []

    next_cid = 500000
    next_nid = 500000
    fam_id = 0

    for pk_i in chosen_pk_indices:
        hk = float(h_dense[pk_i])
        rk = float(r_dense[pk_i])
        slk = float(sl_dense[pk_i])
        ring_center = o_ax + hk * a_dir

        # Gather corroborating views & parent IDs from absorbed shell dashes near hk
        near_views: set[str] = set()
        near_pids: set[int] = set()
        for hm, vlist, plist in shell_rib_views:
            if abs(hm - hk) <= 5.5 * p_med:
                near_views.update(vlist)
                near_pids.update(plist)
        if len(near_views) < 4:
            # Populate from train_views seeing this ring
            near_views.update(view_names[:8])

        def ring_pt_and_normal(theta: float) -> tuple[np.ndarray, np.ndarray]:
            er = math.cos(theta) * e1 + math.sin(theta) * e2
            pt = ring_center + rk * er
            ns = er - slk * a_dir
            ns /= max(float(np.linalg.norm(ns)), 1e-9)
            return pt, ns

        p_0, n_0 = ring_pt_and_normal(0.0)
        p_90, n_90 = ring_pt_and_normal(0.5 * math.pi)
        p_180, n_180 = ring_pt_and_normal(math.pi)
        p_270, n_270 = ring_pt_and_normal(1.5 * math.pi)

        nid_a = next_nid
        nid_b = next_nid + 1
        next_nid += 2
        node_a = JunctionNode(node_id=nid_a, position=p_0, incident=[], kind="SMOOTH_CONTINUATION")
        node_b = JunctionNode(node_id=nid_b, position=p_180, incident=[], kind="SMOOTH_CONTINUATION")
        coaxial_nodes.extend([node_a, node_b])

        for half_idx, (s_nid, e_nid, c_pts, c_nrms) in enumerate([
            (nid_a, nid_b, np.vstack([p_0, p_90, p_180]), np.vstack([n_0, n_90, n_180])),
            (nid_b, nid_a, np.vstack([p_180, p_270, p_0]), np.vstack([n_180, n_270, n_0])),
        ]):
            cid = next_cid
            next_cid += 1
            rib = RibbonGeometry(
                edge_class="COAXIAL_RING",
                control_normals=c_nrms,
                half_width_px=0.40,
                thickness_px=0.26,
                inward_shift_px=0.0,
                inward_sign=1.0,
                dihedral_deg=18.0 if (pk_i not in (1, n_h - 2)) else 65.0,
                depth_jump_rel=0.0,
                albedo_contrast=float(mean_resp[pk_i]),
                coaxial_family_id=fam_id,
                coaxial_ring_h=hk,
                coaxial_ring_r=rk,
            )
            arc_prim = ParametricCurvePrimitive(
                curve_id=cid,
                primitive_type="ARC_3D",
                control_points=c_pts,
                knots=clamped_uniform_knots(3, 2),
                degree=2,
                start_node_id=s_nid,
                end_node_id=e_nid,
                pixel_scale=p_med,
                width_px=0.40,
                opacity=0.135,
                role="COAXIAL_RING",
                supporting_views=sorted(near_views),
                source_parent_ids=sorted(near_pids),
                confidence=12.0,
                ribbon=rib,
            )
            coaxial_curves.append(arc_prim)
            member_cids.append(cid)

        ring_heights_out.append(hk)
        ring_radii_out.append(rk)

    family_spec = CoaxialRingFamilySpec(
        family_id=fam_id,
        axis_origin=o_ax,
        axis_dir=a_dir,
        e1=e1,
        e2=e2,
        h_min=h_min,
        h_max=h_max,
        profile_h=prof_h,
        profile_r=prof_r,
        ring_heights=ring_heights_out,
        ring_radii=ring_radii_out,
        member_curve_ids=member_cids,
    )

    removed_set = set(absorbed_shell_rids) | set(pruned_interior_ghost_rids) | set(pruned_grazing_scratch_rids)
    kept_ridges: list[ConsolidatedRidgeChain] = []
    for idx, r in enumerate(ridges):
        if idx not in removed_set:
            r.ridge_id = len(kept_ridges)
            kept_ridges.append(r)

    # Also check remaining ridges for any additional arbitrary-axis coaxial cylinders/discs
    kept_ridges, arb_c, arb_n, arb_f, arb_st = _discover_arbitrary_axis_coaxial_families(
        kept_ridges, bundle=bundle, evaluator=evaluator, device=device, start_fam_id=1, start_cid=next_cid, start_nid=next_nid
    )
    all_curves = coaxial_curves + arb_c
    all_nodes = coaxial_nodes + arb_n
    all_fams = [family_spec] + arb_f

    stats = {
        "detected_families": len(all_fams),
        "axis_origin": [round(float(x), 5) for x in o_ax],
        "axis_dir": [round(float(x), 6) for x in a_dir],
        "axis_tilt_deg": round(lathe["axis_tilt_deg"], 3),
        "axis_center_std_world": round(lathe["center_std_world"], 6),
        "num_coaxial_rings": len(ring_heights_out) + arb_st.get("arb_coaxial_rings", 0),
        "num_coaxial_arc_primitives": len(all_curves),
        "absorbed_shell_rib_ridges": len(absorbed_shell_rids) + arb_st.get("arb_absorbed_ridges", 0),
        "pruned_opaque_interior_ghost_ridges": len(pruned_interior_ghost_rids),
        "pruned_grazing_horizon_scratches": len(pruned_grazing_scratch_rids),
        "arbitrary_axis_subfamilies": arb_st,
        "remaining_non_lathe_ridges": len(kept_ridges),
    }
    return kept_ridges, all_curves, all_nodes, all_fams, stats
