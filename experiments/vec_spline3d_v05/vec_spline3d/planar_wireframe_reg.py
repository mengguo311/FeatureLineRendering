"""Architectural & Man-Made Planar Coplanarity and Parallel/Orthogonal Wireframe Regularization."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.signal import find_peaks
from scipy.spatial import cKDTree

from .multimodal_data import MultiModalSceneBundle
from .schema import (
    CurveNetwork3D,
    ParametricCurvePrimitive,
    clamped_uniform_knots,
    fit_clamped_bspline_to_polyline,
)
from .stage1_ray_clean import GPUViewFieldEvaluator


def _canonical_plane_normal(n_vec: np.ndarray) -> np.ndarray:
    u = np.asarray(n_vec, dtype=np.float64)
    u = u / max(float(np.linalg.norm(u)), 1e-12)
    if abs(u[2]) > 0.15:
        return u if u[2] > 0.0 else -u
    if abs(u[0]) > 0.15:
        return u if u[0] > 0.0 else -u
    return u if u[1] >= 0.0 else -u


def _plane_tangent_basis(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = _canonical_plane_normal(normal)
    ref = np.array([1.0, 0.0, 0.0], dtype=np.float64) if abs(n[0]) < 0.82 else np.array([0.0, 1.0, 0.0], dtype=np.float64)
    b1 = ref - float(np.dot(ref, n)) * n
    b1 /= max(float(np.linalg.norm(b1)), 1e-12)
    b2 = np.cross(n, b1)
    b2 /= max(float(np.linalg.norm(b2)), 1e-12)
    return b1, b2


def _fibonacci_hemisphere_dirs(num_dirs: int = 160) -> np.ndarray:
    idx = np.arange(num_dirs, dtype=np.float64) + 0.5
    phi = math.pi * (3.0 - math.sqrt(5.0)) * idx
    z = idx / num_dirs
    r = np.sqrt(np.maximum(1.0 - z * z, 0.0))
    dirs = np.column_stack([r * np.cos(phi), r * np.sin(phi), z])
    return dirs / np.maximum(np.linalg.norm(dirs, axis=1, keepdims=True), 1e-12)


def _gather_oriented_surface_points(bundle: MultiModalSceneBundle, max_pts: int = 110000) -> tuple[np.ndarray, np.ndarray]:
    """Unproject smooth opaque foreground pixels & world surface normals from training views."""
    orig_vs = [
        v for v in bundle.train_views
        if v.is_original_c2l_build and v.depth is not None and v.normal_map is not None and v.depth_jump is not None
    ]
    views_use = orig_vs if len(orig_vs) >= 6 else [
        v for v in bundle.train_views[:16]
        if v.depth is not None and v.normal_map is not None and v.depth_jump is not None
    ]

    pts_list: list[np.ndarray] = []
    nrm_list: list[np.ndarray] = []
    for vw in views_use:
        assert vw.depth is not None and vw.normal_map is not None and vw.depth_jump is not None
        d_s = vw.depth[::3, ::3]
        a_s = vw.alpha[::3, ::3]
        j_s = vw.depth_jump[::3, ::3]
        n_s = vw.normal_map[::3, ::3]
        n_nrm = np.linalg.norm(n_s, axis=-1)
        mask = (a_s > 0.92) & (d_s > 0.2) & (j_s < 0.006) & (n_nrm > 0.6)
        if not np.any(mask):
            continue
        rr, cc = np.where(mask)
        uu = (cc * 3).astype(np.float64)
        vv = (rr * 3).astype(np.float64)
        zc = d_s[rr, cc].astype(np.float64)
        xc = (uu - vw.cx) * zc / vw.fx
        yc = (vv - vw.cy) * zc / vw.fy
        R_c2w = vw.c2w[:3, :3]
        pts_w = (np.column_stack([xc, yc, zc]) @ R_c2w.T) + vw.c2w[:3, 3]
        nrm_w = n_s[rr, cc].astype(np.float64) @ R_c2w.T
        nrm_w /= np.maximum(np.linalg.norm(nrm_w, axis=1, keepdims=True), 1e-12)
        pts_list.append(pts_w)
        nrm_list.append(nrm_w)

    if not pts_list:
        return np.zeros((0, 3), dtype=np.float64), np.zeros((0, 3), dtype=np.float64)

    pts_all = np.concatenate(pts_list, axis=0)
    nrm_all = np.concatenate(nrm_list, axis=0)
    if len(pts_all) > max_pts:
        rng = np.random.default_rng(1729)
        sel = rng.choice(len(pts_all), size=max_pts, replace=False)
        pts_all = pts_all[sel]
        nrm_all = nrm_all[sel]
    return pts_all, nrm_all


def discover_and_regularize_planar_wireframes(
    net: CurveNetwork3D,
    bundle: MultiModalSceneBundle,
    evaluator: GPUViewFieldEvaluator,
) -> dict[str, Any]:
    """Discover dominant structural planes & Manhattan/parallel wireframe frames, regularize curves, and weld collinear gaps."""
    p = bundle.median_pixel_scale
    if len(net.curves) < 12:
        return {"detected_planes": 0}

    surf_pts, surf_nrms = _gather_oriented_surface_points(bundle)
    has_surf = len(surf_pts) >= 500

    # 1. Gather straight / near-straight candidate curves for plane & principal-axis discovery
    cand_cids: list[int] = []
    c_pts_map: dict[int, np.ndarray] = {}
    c_chord_dir: dict[int, np.ndarray] = {}
    c_len_map: dict[int, float] = {}
    c_line_err: dict[int, float] = {}

    for cid, c in net.curves.items():
        if c.role == "COAXIAL_RING":
            continue
        _, pts_ev, _, _ = c.evaluate(num_samples=12)
        chord = pts_ev[-1] - pts_ev[0]
        c_len = float(np.linalg.norm(chord))
        if c_len < 2.2 * p:
            continue
        _, _, _, max_err = fit_clamped_bspline_to_polyline(pts_ev, num_ctrl=2)
        if c.primitive_type == "LINE_3D" or max_err <= 0.78 * p:
            cand_cids.append(cid)
            c_pts_map[cid] = pts_ev
            c_chord_dir[cid] = chord / c_len
            c_len_map[cid] = c_len
            c_line_err[cid] = float(max_err)

    if len(cand_cids) < 10:
        return {"detected_planes": 0}

    # 2. Generate candidate plane hypotheses from (a) oriented surface modes and (b) intersecting line junctions
    cand_planes: list[tuple[np.ndarray, float]] = []

    if has_surf:
        hemi = _fibonacci_hemisphere_dirs(160)
        dots = np.abs(surf_nrms @ hemi.T)
        best_bin = np.argmax(dots, axis=1)
        counts = np.bincount(best_bin, minlength=len(hemi))
        top_bins = np.argsort(counts)[::-1][:16]
        cos_n_cone = float(np.cos(np.deg2rad(14.0)))
        for b_i in top_bins:
            if counts[b_i] < 300:
                continue
            n0 = _canonical_plane_normal(hemi[b_i])
            aligned = np.abs(surf_nrms @ n0) >= cos_n_cone
            if int(aligned.sum()) < 300:
                continue
            ds = surf_pts[aligned] @ n0
            d_min, d_max = float(np.percentile(ds, 1.0)), float(np.percentile(ds, 99.0))
            if d_max <= d_min + 2.0 * p:
                cand_planes.append((n0, float(np.median(ds))))
                continue
            bw = max(1.8 * p, (d_max - d_min) / 180.0)
            hist, edges = np.histogram(ds, bins=np.arange(d_min, d_max + bw, bw))
            pks, _ = find_peaks(hist, distance=2, height=max(120, int(0.06 * aligned.sum())))
            for pk in pks[:6]:
                cand_planes.append((n0, float(0.5 * (edges[pk] + edges[pk + 1]))))

    # Also propose planes from degree>=2 nodes where two straight lines meet at >= 25 deg
    cand_set = set(cand_cids)
    for node in net.nodes.values():
        inc_lines = [cid for cid, _ in node.incident if cid in cand_set and c_len_map[cid] >= 4.0 * p]
        if len(inc_lines) >= 2:
            for ia in range(min(3, len(inc_lines))):
                for ib in range(ia + 1, min(4, len(inc_lines))):
                    cr = np.cross(c_chord_dir[inc_lines[ia]], c_chord_dir[inc_lines[ib]])
                    cr_n = float(np.linalg.norm(cr))
                    if cr_n >= math.sin(math.radians(25.0)):
                        n_j = _canonical_plane_normal(cr / cr_n)
                        cand_planes.append((n_j, float(np.dot(node.position, n_j))))

    if not cand_planes:
        return {"detected_planes": 0}

    # Deduplicate initial plane seeds
    seed_planes: list[tuple[np.ndarray, float]] = []
    cos_dup_p = float(np.cos(np.deg2rad(8.5)))
    for n_c, d_c in cand_planes:
        is_dup = False
        for n_s, d_s in seed_planes:
            sgn = 1.0 if float(np.dot(n_c, n_s)) >= 0.0 else -1.0
            if abs(float(np.dot(n_c, n_s))) >= cos_dup_p and abs(d_c - sgn * d_s) <= 3.2 * p:
                is_dup = True
                break
        if not is_dup:
            seed_planes.append((n_c, d_c))

    # 3. Refine planes via IRLS SVD on surface + coplanar line points and enforce dual support (surface + >=10 lines)
    all_cand_pts = np.stack([c_pts_map[cid] for cid in cand_cids], axis=0)  # (Nc, 12, 3)
    all_cand_dirs = np.stack([c_chord_dir[cid] for cid in cand_cids], axis=0)  # (Nc, 3)
    all_cand_lens = np.array([c_len_map[cid] for cid in cand_cids], dtype=np.float64)
    sin_inplane = math.sin(math.radians(10.0))
    cos_surf_n = float(np.cos(np.deg2rad(15.0)))

    verified_planes: list[dict[str, Any]] = []
    for n_init, d_init in seed_planes:
        n_cur, d_cur = n_init.copy(), float(d_init)
        for _ in range(2):
            line_d = np.max(np.abs(all_cand_pts @ n_cur - d_cur), axis=1)
            line_orth = np.abs(all_cand_dirs @ n_cur)
            in_l = (line_d <= 2.5 * p) & (line_orth <= sin_inplane)
            if int(in_l.sum()) < 8:
                break
            pts_fit = all_cand_pts[in_l].reshape(-1, 3)
            if has_surf:
                s_in = (np.abs(surf_pts @ n_cur - d_cur) <= 2.4 * p) & (np.abs(surf_nrms @ n_cur) >= cos_surf_n)
                if int(s_in.sum()) >= 200:
                    s_sub = surf_pts[s_in]
                    if len(s_sub) > 3000:
                        s_sub = s_sub[:: max(1, len(s_sub) // 3000)]
                    pts_fit = np.vstack([pts_fit, s_sub])
            ctr = np.median(pts_fit, axis=0)
            _, _, vt = np.linalg.svd(pts_fit - ctr[None, :], full_matrices=False)
            n_cur = _canonical_plane_normal(vt[-1])
            d_cur = float(np.median(pts_fit @ n_cur))

        # Verify surface support (when available) + curve wireframe support
        surf_tree = None
        surf_cnt = 0
        if has_surf:
            s_in = (np.abs(surf_pts @ n_cur - d_cur) <= 2.4 * p) & (np.abs(surf_nrms @ n_cur) >= cos_surf_n)
            surf_cnt = int(s_in.sum())
            if surf_cnt < 380:
                continue
            s_patch = surf_pts[s_in]
            if float(np.percentile(np.abs(s_patch @ n_cur - d_cur), 90.0)) > 2.2 * p:
                continue
            surf_tree = cKDTree(s_patch[:: max(1, len(s_patch) // 8000)])

        line_d = np.max(np.abs(all_cand_pts @ n_cur - d_cur), axis=1)
        line_orth = np.abs(all_cand_dirs @ n_cur)
        in_l = (line_d <= 2.4 * p) & (line_orth <= sin_inplane)
        member_idx = np.where(in_l)[0]
        if surf_tree is not None and len(member_idx) > 0:
            mids_l = all_cand_pts[member_idx, 6, :]
            d_to_surf, _ = surf_tree.query(mids_l, k=1)
            member_idx = member_idx[d_to_surf <= 4.8 * p]

        if len(member_idx) < 10 or float(all_cand_lens[member_idx].sum()) < 42.0 * p:
            continue

        # Check deduplication against already verified planes
        dup_v = False
        for vp in verified_planes:
            sgn = 1.0 if float(np.dot(n_cur, vp["_normal_np"])) >= 0.0 else -1.0
            if abs(float(np.dot(n_cur, vp["_normal_np"]))) >= cos_dup_p and abs(d_cur - sgn * vp["offset_d"]) <= 3.0 * p:
                dup_v = True
                break
        if dup_v:
            continue

        # Discover Manhattan orthogonal principal axes (u1, u2) + optional diagonal gable axis via 4*theta resultant
        b1, b2 = _plane_tangent_basis(n_cur)
        dirs_m = all_cand_dirs[member_idx]
        wts_m = all_cand_lens[member_idx]
        thetas = np.mod(np.arctan2(dirs_m @ b2, dirs_m @ b1), math.pi)
        phi4 = np.sum(wts_m * np.exp(1j * 4.0 * thetas)) / max(float(wts_m.sum()), 1e-9)

        axes_3d: list[np.ndarray] = []
        has_manhattan = float(np.abs(phi4)) >= 0.25
        if has_manhattan:
            th0 = 0.25 * float(np.angle(phi4))
            # Refine th0 on lines within 10 deg of {th0, th0 + pi/2}
            for _ in range(2):
                d_th = np.mod(thetas - th0 + 0.25 * math.pi, 0.5 * math.pi) - 0.25 * math.pi
                inl_th = np.abs(d_th) <= math.radians(10.0)
                if np.any(inl_th):
                    th0 = float(th0 + np.average(d_th[inl_th], weights=wts_m[inl_th]))
            u1 = math.cos(th0) * b1 + math.sin(th0) * b2
            u1 /= max(float(np.linalg.norm(u1)), 1e-12)
            u2 = np.cross(n_cur, u1)
            u2 /= max(float(np.linalg.norm(u2)), 1e-12)
            axes_3d.extend([u1, u2])

        # Check residual lines (>12 deg away from existing axes) for pitched-roof / diagonal parallel family
        if axes_3d:
            max_al = np.max(np.stack([np.abs(dirs_m @ ax) for ax in axes_3d], axis=1), axis=1)
            rem_mask = max_al < math.cos(math.radians(12.0))
        else:
            rem_mask = np.ones(len(member_idx), dtype=bool)
        if int(rem_mask.sum()) >= 4 and float(wts_m[rem_mask].sum()) >= 16.0 * p:
            th_r = thetas[rem_mask]
            wt_r = wts_m[rem_mask]
            phi2 = np.sum(wt_r * np.exp(1j * 2.0 * th_r)) / max(float(wt_r.sum()), 1e-9)
            if float(np.abs(phi2)) >= 0.55:
                th_aux = 0.5 * float(np.angle(phi2))
                u_aux = math.cos(th_aux) * b1 + math.sin(th_aux) * b2
                u_aux /= max(float(np.linalg.norm(u_aux)), 1e-12)
                axes_3d.append(u_aux)

        member_cids = [cand_cids[i] for i in member_idx]
        verified_planes.append({
            "plane_id": len(verified_planes),
            "normal": [round(float(x), 6) for x in n_cur],
            "offset_d": round(float(d_cur), 6),
            "has_manhattan_frame": has_manhattan,
            "manhattan_strength": round(float(np.abs(phi4)), 4),
            "principal_axes": [[round(float(x), 6) for x in ax] for ax in axes_3d],
            "surface_support_points": surf_cnt,
            "num_member_curves": len(member_cids),
            "member_curve_ids": [int(c) for c in member_cids],
            "_normal_np": n_cur,
            "_axes_np": axes_3d,
            "_surf_tree": surf_tree,
        })

    if not verified_planes:
        return {"detected_planes": 0}

    # Sort planes by total member curve count descending and assign each curve to its tightest plane
    verified_planes.sort(key=lambda d: d["num_member_curves"], reverse=True)
    for i_p, vp in enumerate(verified_planes):
        vp["plane_id"] = i_p

    curve_to_plane: dict[int, int] = {}
    for cid in cand_cids:
        pts_c = c_pts_map[cid]
        best_pid = -1
        best_d = 2.2 * p
        for vp in verified_planes:
            n_p = vp["_normal_np"]
            d_p = vp["offset_d"]
            err_p = float(np.max(np.abs(pts_c @ n_p - d_p)))
            if err_p < best_d and abs(float(np.dot(c_chord_dir[cid], n_p))) <= sin_inplane:
                if vp["_surf_tree"] is not None:
                    ds_q, _ = vp["_surf_tree"].query(pts_c[6], k=1)
                    if float(ds_q) > 4.5 * p:
                        continue
                best_d = err_p
                best_pid = vp["plane_id"]
        if best_pid >= 0:
            curve_to_plane[cid] = best_pid

    # 4A. Linearize shallow arcs/splines on verified planes when aligned with a principal wireframe axis
    linearized_planar = 0
    cos_axis_lin = float(np.cos(np.deg2rad(8.0)))
    for cid, pid in list(curve_to_plane.items()):
        c = net.curves[cid]
        if c.primitive_type == "LINE_3D" or c_line_err[cid] > 0.72 * p:
            continue
        axes_p = verified_planes[pid]["_axes_np"]
        if axes_p and max(abs(float(np.dot(c_chord_dir[cid], ax))) for ax in axes_p) >= cos_axis_lin:
            if c.ribbon is not None and len(c.ribbon.control_normals) >= 2:
                cn = c.ribbon.control_normals
                c.ribbon.control_normals = np.vstack([cn[0], cn[-1]])
            c.primitive_type = "LINE_3D"
            c.control_points = np.vstack([c.control_points[0], c.control_points[-1]])
            c.knots = clamped_uniform_knots(2, 1)
            c.degree = 1
            linearized_planar += 1

    # 4B. Bounded Coplanar Node Projection (and Plane-Intersection Line Projection for Wall/Roof Corners!)
    coplanar_projected_nodes = 0
    max_node_shift = 1.15 * p
    for nid, node in net.nodes.items():
        inc_pids = sorted({curve_to_plane[cid] for cid, _ in node.incident if cid in curve_to_plane})
        if not inc_pids:
            continue
        pos0 = node.position.copy()
        target_pos = pos0.copy()
        if len(inc_pids) == 1:
            vp = verified_planes[inc_pids[0]]
            n_p = vp["_normal_np"]
            target_pos = pos0 - (float(np.dot(pos0, n_p)) - vp["offset_d"]) * n_p
        else:
            # Project onto intersection line of first two non-parallel planes (exact architectural corner/ridge!)
            vp1, vp2 = verified_planes[inc_pids[0]], verified_planes[inc_pids[1]]
            n1, d1 = vp1["_normal_np"], vp1["offset_d"]
            n2, d2 = vp2["_normal_np"], vp2["offset_d"]
            if abs(float(np.dot(n1, n2))) <= math.cos(math.radians(22.0)):
                A_int = np.vstack([n1, n2])
                b_int = np.array([d1, d2], dtype=np.float64)
                # Minimum-norm projection onto {x : A_int x = b_int}
                delta_x = A_int.T @ np.linalg.solve(A_int @ A_int.T, b_int - A_int @ pos0)
                target_pos = pos0 + delta_x
            else:
                target_pos = pos0 - (float(np.dot(pos0, n1)) - d1) * n1

        shift = target_pos - pos0
        s_len = float(np.linalg.norm(shift))
        if 1e-8 < s_len:
            if s_len > max_node_shift:
                shift = shift * (max_node_shift / s_len)
            node.position = pos0 + shift
            coplanar_projected_nodes += 1

    net.sync_endpoints_from_nodes()

    # 4C. Gentle Principal-Axis Alignment for LINE_3D segments within 6.5 deg of plane orthogonal/parallel axes
    cos_snap_ax = float(np.cos(np.deg2rad(6.5)))
    axis_aligned_map: dict[int, list[float]] = {}
    snapped_lines = 0
    for cid, pid in curve_to_plane.items():
        c = net.curves.get(cid)
        if c is None or c.primitive_type != "LINE_3D":
            continue
        axes_p = verified_planes[pid]["_axes_np"]
        if not axes_p:
            continue
        p0 = net.nodes[c.start_node_id].position
        p1 = net.nodes[c.end_node_id].position
        vec = p1 - p0
        seg_l = float(np.linalg.norm(vec))
        if seg_l < 2.2 * p:
            continue
        t_cur = vec / seg_l

        best_ax = max(axes_p, key=lambda ax: abs(float(np.dot(t_cur, ax))))
        align_val = abs(float(np.dot(t_cur, best_ax)))
        if align_val < cos_snap_ax:
            continue
        ax_oriented = best_ax if float(np.dot(t_cur, best_ax)) >= 0.0 else -best_ax
        axis_aligned_map[int(cid)] = [float(x) for x in ax_oriented]

        #Directly snap free/single-plane endpoints gently (clamped <= 0.95p)
        n_s = net.nodes[c.start_node_id]
        n_e = net.nodes[c.end_node_id]
        if n_s.degree <= 2 and n_e.degree <= 2:
            mid = 0.5 * (p0 + p1)
            t_blend = 0.75 * ax_oriented + 0.25 * t_cur
            t_blend /= max(float(np.linalg.norm(t_blend)), 1e-12)
            new_p0 = mid - 0.5 * seg_l * t_blend
            new_p1 = mid + 0.5 * seg_l * t_blend
            if float(np.linalg.norm(new_p0 - p0)) <= 0.95 * p and float(np.linalg.norm(new_p1 - p1)) <= 0.95 * p:
                if n_s.degree == 1:
                    n_s.position = new_p0
                if n_e.degree == 1:
                    n_e.position = new_p1
                snapped_lines += 1

    net.sync_endpoints_from_nodes()

    # 4D. Coplanar Collinear Gap Welding along Principal Axes (recovers broken window lintels/sills!)
    open_axis_eps: list[tuple[int, int, int, int, np.ndarray, np.ndarray]] = []
    # (nid, cid, end_idx, pid, pos, outward_axis_dir)
    for nid, node in net.nodes.items():
        if node.degree != 1:
            continue
        cid, end_i = node.incident[0]
        if cid not in curve_to_plane or cid not in axis_aligned_map:
            continue
        c = net.curves[cid]
        if c.primitive_type != "LINE_3D":
            continue
        t_out = c.endpoint_tangent(end_i)
        open_axis_eps.append((nid, cid, end_i, curve_to_plane[cid], node.position.copy(), t_out))

    bridge_props: list[tuple[int, int, int, np.ndarray]] = []
    used_open: set[int] = set()
    for i in range(len(open_axis_eps)):
        nid_a, cid_a, _, pid_a, pa, ta = open_axis_eps[i]
        if nid_a in used_open:
            continue
        best_j = -1
        best_gap = 8.5 * p
        for j in range(i + 1, len(open_axis_eps)):
            nid_b, cid_b, _, pid_b, pb, tb = open_axis_eps[j]
            if nid_b in used_open or pid_a != pid_b or cid_a == cid_b:
                continue
            # Outward tangents must point toward each other along the same axis
            if float(np.dot(ta, tb)) > -0.96:
                continue
            chord = pb - pa
            gap_d = float(np.linalg.norm(chord))
            if gap_d < 0.8 * p or gap_d >= best_gap:
                continue
            long_d = float(np.dot(chord, ta))
            if long_d <= 0.6 * p:
                continue
            lat_d = float(np.linalg.norm(chord - long_d * ta))
            if lat_d <= 1.25 * p:
                best_gap = gap_d
                best_j = j
        if best_j >= 0:
            nid_b = open_axis_eps[best_j][0]
            pb = open_axis_eps[best_j][4]
            used_open.add(nid_a)
            used_open.add(nid_b)
            u_s = np.linspace(0.0, 1.0, 8, dtype=np.float64)[:, None]
            bridge_props.append((nid_a, nid_b, pid_a, (1.0 - u_s) * pa[None, :] + u_s * pb[None, :]))

    welded_collinear = 0
    if bridge_props:
        q_br = evaluator.query_points(np.concatenate([bp[3] for bp in bridge_props], axis=0), pixel_scale=p)
        max_fsv_w = max(1, int(0.10 * max(1, evaluator.num_depth_views)))
        next_cid = (max(net.curves.keys()) + 1) if net.curves else 1
        for k_i, (nid_a, nid_b, pid_w, pts_b) in enumerate(bridge_props):
            sl = slice(k_i * 8, (k_i + 1) * 8)
            if float(q_br["hull_viol_rate"][sl].max()) > 0.05 or int(q_br["free_space_viol"][sl].max()) > max_fsv_w:
                continue
            if float(q_br["edge_cost_mean"][sl].mean()) > 2.25:
                continue
            cid_src = net.nodes[nid_a].incident[0][0]
            src_c = net.curves[cid_src]
            new_c = ParametricCurvePrimitive(
                curve_id=next_cid,
                primitive_type="LINE_3D",
                control_points=np.vstack([net.nodes[nid_a].position.copy(), net.nodes[nid_b].position.copy()]),
                knots=clamped_uniform_knots(2, 1),
                degree=1,
                start_node_id=nid_a,
                end_node_id=nid_b,
                pixel_scale=p,
                width_px=src_c.width_px,
                opacity=src_c.opacity,
                role="BRIDGE",
                supporting_views=list(src_c.supporting_views),
                source_parent_ids=list(src_c.source_parent_ids),
                confidence=src_c.confidence,
            )
            net.curves[next_cid] = new_c
            curve_to_plane[next_cid] = pid_w
            if cid_src in axis_aligned_map:
                axis_aligned_map[next_cid] = list(axis_aligned_map[cid_src])
            next_cid += 1
            welded_collinear += 1
        if welded_collinear > 0:
            net.rebuild_node_incidence()
            net.sync_endpoints_from_nodes()

    # Mark exact 90-degree planar corners on verified planes
    ortho_corners = 0
    for node in net.nodes.values():
        if node.degree == 2:
            (c1, e1_i), (c2, e2_i) = node.incident
            if c1 in net.curves and c2 in net.curves:
                t1 = net.curves[c1].endpoint_tangent(e1_i)
                t2 = net.curves[c2].endpoint_tangent(e2_i)
                if abs(float(np.dot(t1, t2))) <= math.sin(math.radians(12.0)):
                    node.kind = "CORNER"
                    ortho_corners += 1

    # Populate clean serializable metadata + internal tensors/maps for Stage 4 differentiable refinement
    for vp in verified_planes:
        pid = vp["plane_id"]
        vp["member_curve_ids"] = sorted(int(cid) for cid, p_id in curve_to_plane.items() if p_id == pid and cid in net.curves)
        vp["num_member_curves"] = len(vp["member_curve_ids"])
        vp["_axis_map"] = {int(cid): axis_aligned_map[cid] for cid in vp["member_curve_ids"] if cid in axis_aligned_map}
        del vp["_surf_tree"]

    net.planar_patches = [vp for vp in verified_planes if vp["num_member_curves"] >= 6]

    return {
        "detected_planes": len(net.planar_patches),
        "manhattan_planes": sum(1 for vp in net.planar_patches if vp["has_manhattan_frame"]),
        "coplanar_assigned_curves": sum(vp["num_member_curves"] for vp in net.planar_patches),
        "axis_aligned_lines": len(axis_aligned_map),
        "linearized_shallow_planar_curves": linearized_planar,
        "coplanar_projected_nodes": coplanar_projected_nodes,
        "axis_snapped_lines": snapped_lines,
        "welded_collinear_window_gaps": welded_collinear,
        "orthogonal_corner_nodes": ortho_corners,
    }
