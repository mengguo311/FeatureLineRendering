"""Stage 3: Coaxial ring family + Co-circular arcs + (LINE_3D / ARC_3D / CUBIC_BSPLINE_3D) + MILP + RIBBON_3D."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csc_matrix
from scipy.spatial import cKDTree

from .co_circular_arcs import consolidate_cocircular_arcs
from .coaxial_rings import consolidate_coaxial_ring_families
from .contour_generators import build_lathe_contour_generator, discover_swept_tube_trunks
from .multimodal_data import MultiModalSceneBundle
from .planar_wireframe_reg import discover_and_regularize_planar_wireframes
from .ribbon_geometry import SurfaceRibbonEstimator
from .schema import (
    CoaxialRingFamilySpec,
    CurveNetwork3D,
    JunctionNode,
    LatheEnvelopeGenerator,
    ParametricCurvePrimitive,
    SweptTubeGenerator,
    clamped_uniform_knots,
    fit_circular_arc_to_polyline,
    fit_clamped_bspline_to_polyline,
)
from .stage1_ray_clean import GPUViewFieldEvaluator
from .stage2_scms_consolidate import ConsolidatedRidgeChain


def _adaptive_fit_primitive(
    ridge: ConsolidatedRidgeChain,
    line_tol_px: float = 0.50,
    arc_tol_px: float = 0.58,
    spline_tol_px: float = 0.50,
) -> ParametricCurvePrimitive:
    """Select parsimonious primitive among LINE_3D (2 pts), ARC_3D (3 pts), and CUBIC_BSPLINE_3D (4..28 pts)."""
    pts = ridge.points_3d
    p = max(ridge.pixel_scale, 1e-5)
    is_cocirc = ridge.confidence >= 100.0
    true_conf = ridge.confidence - 100.0 if is_cocirc else ridge.confidence
    role = (
        "COCIRCULAR_RING"
        if is_cocirc
        else ("SILHOUETTE_DEPTH_JUMP" if ridge.is_silhouette_jump else "CREASE_OR_RIB")
    )

    ctrl_line, knots_line, deg_line, err_line = fit_clamped_bspline_to_polyline(pts, num_ctrl=2)
    if not is_cocirc and (err_line <= line_tol_px * p or len(pts) <= 3):
        return ParametricCurvePrimitive(
            curve_id=ridge.ridge_id,
            primitive_type="LINE_3D",
            control_points=ctrl_line,
            knots=knots_line,
            degree=deg_line,
            pixel_scale=p,
            role=role,
            supporting_views=list(ridge.supporting_views),
            source_parent_ids=list(ridge.source_parent_ids),
            confidence=true_conf,
        )

    if len(pts) >= 4:
        ctrl_arc, err_arc, arc_meta = fit_circular_arc_to_polyline(pts, pin_endpoints=not is_cocirc)
        tol_a = (0.85 if is_cocirc else arc_tol_px) * p
        if (
            arc_meta.get("valid")
            and err_arc <= tol_a
            and math.radians(12.0) <= arc_meta["sweep_rad"] <= math.radians(350.0)
            and 2.5 * p <= arc_meta["radius"] <= 180.0 * p
        ):
            return ParametricCurvePrimitive(
                curve_id=ridge.ridge_id,
                primitive_type="ARC_3D",
                control_points=ctrl_arc,
                knots=clamped_uniform_knots(3, 2),
                degree=2,
                pixel_scale=p,
                role=role,
                supporting_views=list(ridge.supporting_views),
                source_parent_ids=list(ridge.source_parent_ids),
                confidence=true_conf,
            )

    length = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
    m_min = 4
    m_max = max(4, min(len(pts), min(28, int(np.ceil(length / (4.5 * p))) + 3)))

    best_ctrl, best_knots, best_deg = ctrl_line, knots_line, deg_line
    best_bic = (err_line / p) + 0.08 * 2

    cand_ms = sorted({m_min, min(m_max, 6), min(m_max, 10), min(m_max, 16), m_max})
    for m in cand_ms:
        if m > len(pts):
            continue
        ctrl, knots, deg, max_err = fit_clamped_bspline_to_polyline(pts, num_ctrl=m, reg_smooth=2e-3)
        bic = (max_err / p) + 0.025 * m
        if max_err <= spline_tol_px * p:
            best_ctrl, best_knots, best_deg = ctrl, knots, deg
            break
        if bic < best_bic:
            best_bic = bic
            best_ctrl, best_knots, best_deg = ctrl, knots, deg

    prim_type = "LINE_3D" if len(best_ctrl) == 2 else "CUBIC_BSPLINE_3D"
    return ParametricCurvePrimitive(
        curve_id=ridge.ridge_id,
        primitive_type=prim_type,
        control_points=best_ctrl,
        knots=best_knots,
        degree=best_deg,
        pixel_scale=p,
        role=role,
        supporting_views=list(ridge.supporting_views),
        source_parent_ids=list(ridge.source_parent_ids),
        confidence=true_conf,
    )


@dataclass
class ConnectionCandidate:
    """Candidate topological connection (End-to-End continuation bridge or End-to-Interior T-junction)."""

    cand_id: int
    kind: str  # "END_TO_END" or "END_TO_INTERIOR_T"
    curve_a: int
    end_a: int
    curve_b: int
    end_b: int
    target_u_b: float
    target_pt_b: np.ndarray
    bridge_ctrl: np.ndarray
    cost: float


def _hermite_bridge_controls(p0: np.ndarray, t0_out: np.ndarray, p1: np.ndarray, t1_out: np.ndarray) -> np.ndarray:
    d = float(np.linalg.norm(p1 - p0))
    alpha = d / 3.0
    return np.vstack([p0, p0 + alpha * t0_out, p1 + alpha * t1_out, p1])


def run_stage3_spline_topology(
    ridges: list[ConsolidatedRidgeChain],
    bundle: MultiModalSceneBundle,
    device: torch.device,
    enable_cocircular_consolidation: bool = True,
    enable_coaxial_consolidation: bool = False,
    enable_ribbon_annotation: bool = False,
    enable_contour_generators: bool = False,
    enable_planar_regularization: bool = True,
) -> tuple[CurveNetwork3D, dict[str, Any]]:
    """Consolidate coaxial/co-circular rings, fit smooth contour envelopes & curves, solve MILP, regularize planes, and build RIBBON_3D."""
    p_med = bundle.median_pixel_scale
    evaluator = GPUViewFieldEvaluator(bundle.train_views, device=device)

    coaxial_curves: list[ParametricCurvePrimitive] = []
    coaxial_nodes: list[JunctionNode] = []
    coaxial_families: list[CoaxialRingFamilySpec] = []
    coaxial_stats: dict[str, Any] = {"detected_families": 0}
    if enable_coaxial_consolidation and len(ridges) >= 10:
        ridges, coaxial_curves, coaxial_nodes, coaxial_families, coaxial_stats = consolidate_coaxial_ring_families(
            ridges, bundle=bundle, evaluator=evaluator, device=device
        )

    lathe_generators: list[LatheEnvelopeGenerator] = []
    tube_generators: list[SweptTubeGenerator] = []
    contour_gen_stats: dict[str, Any] = {"lathe_generators": 0, "swept_tube_generators": 0}
    if enable_contour_generators:
        for fam in coaxial_families:
            r_span_ok = float(np.max(fam.profile_r) - np.min(fam.profile_r)) <= 0.42 * float(np.max(fam.profile_r))
            if (fam.h_max - fam.h_min) >= 16.0 * p_med and len(fam.ring_heights) >= 2 and r_span_ok:
                lg_cand = build_lathe_contour_generator(fam, bundle, generator_id=len(lathe_generators))
                if lg_cand is not None:
                    lathe_generators.append(lg_cand)
        if coaxial_families and abs(float(coaxial_families[0].axis_dir[2])) > 0.94 and len(coaxial_families[0].ring_heights) >= 6:
            pot_top_z = coaxial_families[0].h_max
            ridges, tube_generators, tube_st = discover_swept_tube_trunks(ridges, bundle=bundle, pot_h_max=pot_top_z)
        else:
            tube_st = {"detected_swept_tubes": 0, "absorbed_bare_trunk_horizon_ridges": 0}
        contour_gen_stats = {
            "lathe_generators": len(lathe_generators),
            "swept_tube_generators": len(tube_generators),
            "tube_tracking": tube_st,
        }

    cocirc_stats: dict[str, Any] = {"verified_cocircular_groups": 0, "absorbed_short_arc_ridges": 0}
    if enable_cocircular_consolidation and len(ridges) >= 2:
        ridges, cocirc_stats = consolidate_cocircular_arcs(ridges, evaluator=evaluator, median_pixel_scale=p_med)

    curves: dict[int, ParametricCurvePrimitive] = {}
    for r in ridges:
        prim = _adaptive_fit_primitive(r)
        curves[prim.curve_id] = prim

    if not curves and not coaxial_curves:
        return CurveNetwork3D(scene_name=bundle.scene_name), {"num_curves": 0}

    view_names = [v.view_name for v in bundle.train_views]
    if curves:
        curve_id_order = sorted(curves.keys())
        S_eval = 16
        all_samples = np.concatenate([curves[cid].evaluate(num_samples=S_eval)[1] for cid in curve_id_order], axis=0)

        with torch.no_grad():
            pts_t = torch.as_tensor(all_samples, dtype=torch.float32, device=device)
            hit_counts = np.zeros((len(curve_id_order), len(view_names)), dtype=np.int32)
            for s in range(0, len(pts_t), S_eval * 512):
                e = min(len(pts_t), s + S_eval * 512)
                Xc = torch.einsum("vij,bj->vbi", evaluator.R, pts_t[s:e]) + evaluator.t[:, None, :]
                z = Xc[:, :, 2].clamp(min=1e-3)
                u = evaluator.fx[:, None] * (Xc[:, :, 0] / z) + evaluator.cx[:, None]
                v = evaluator.fy[:, None] * (Xc[:, :, 1] / z) + evaluator.cy[:, None]
                in_f = (Xc[:, :, 2] > 0.2) & (u >= 0.0) & (u <= evaluator.w - 1.0) & (v >= 0.0) & (v <= evaluator.h - 1.0)
                gx = 2.0 * (u / (evaluator.w - 1.0)) - 1.0
                gy = 2.0 * (v / (evaluator.h - 1.0)) - 1.0
                grid = torch.stack([gx, gy], dim=-1).unsqueeze(2)
                smp = torch.nn.functional.grid_sample(
                    evaluator.maps[:, [0, 2], :, :], grid, mode="bilinear", padding_mode="border", align_corners=True
                ).squeeze(-1)
                smp_d = torch.nn.functional.grid_sample(
                    evaluator.maps[:, [4, 5], :, :], grid, mode="nearest", padding_mode="border", align_corners=True
                ).squeeze(-1)
                smooth_op = evaluator.has_depth[:, None] & (smp[:, 0, :] > 0.95) & (smp_d[:, 0, :] > 0.2) & (smp_d[:, 1, :] < 0.004)
                occ = smooth_op & (z > smp_d[:, 0, :] + 5.0 * p_med)
                hit = (in_f & (~occ) & (smp[:, 1, :] <= 2.0)).cpu().numpy()
                n_c_chunk = (e - s) // S_eval
                hit_c = hit.reshape(len(view_names), n_c_chunk, S_eval).sum(axis=2).T
                c0 = s // S_eval
                hit_counts[c0 : c0 + n_c_chunk] = hit_c

        for idx, cid in enumerate(curve_id_order):
            corroborated = [view_names[v_i] for v_i in range(len(view_names)) if hit_counts[idx, v_i] >= int(0.55 * S_eval)]
            curves[cid].supporting_views = sorted(set(curves[cid].supporting_views) | set(corroborated))

    # Sub-pixel endpoint clustering (<= 1.15p) on non-lathe curves
    nodes: dict[int, JunctionNode] = {}
    raw_proposals: list[dict[str, Any]] = []
    accepted_candidates: list[ConnectionCandidate] = []
    selected_cands: list[ConnectionCandidate] = []
    num_e2e_bridges = 0
    num_t_junctions = 0
    unified_merges = 0

    if curves:
        ep_list: list[tuple[int, int]] = []
        ep_coords: list[np.ndarray] = []
        for cid in sorted(curves.keys()):
            c = curves[cid]
            ep_list.append((cid, 0))
            ep_coords.append(c.control_points[0])
            ep_list.append((cid, 1))
            ep_coords.append(c.control_points[-1])

        ep_arr = np.stack(ep_coords, axis=0)
        ep_tree = cKDTree(ep_arr)
        snap_pairs = ep_tree.query_pairs(r=1.15 * p_med)

        ep_uf = np.arange(len(ep_list), dtype=np.int32)

        def find_ep(i: int) -> int:
            while ep_uf[i] != i:
                ep_uf[i] = ep_uf[ep_uf[i]]
                i = int(ep_uf[i])
            return i

        for i_a, i_b in snap_pairs:
            if ep_list[i_a][0] == ep_list[i_b][0] and curves[ep_list[i_a][0]].arc_length() < 6.0 * p_med:
                continue
            ra, rb = find_ep(i_a), find_ep(i_b)
            if ra != rb:
                ep_uf[rb] = ra

        root_to_nid: dict[int, int] = {}
        next_nid = 0
        for ep_i, (cid, end_idx) in enumerate(ep_list):
            r = find_ep(ep_i)
            if r not in root_to_nid:
                nid = next_nid
                next_nid += 1
                root_to_nid[r] = nid
                nodes[nid] = JunctionNode(node_id=nid, position=ep_arr[ep_i].copy(), incident=[])
            nid = root_to_nid[r]
            nodes[nid].incident.append((cid, end_idx))
            if end_idx == 0:
                curves[cid].start_node_id = nid
            else:
                curves[cid].end_node_id = nid

        for nid, node in nodes.items():
            pts_inc = [curves[cid].control_points[0 if e_i == 0 else -1] for cid, e_i in node.incident]
            node.position = np.mean(pts_inc, axis=0)
            node.kind = "ENDPOINT" if node.degree == 1 else ("SMOOTH_CONTINUATION" if node.degree == 2 else "JUNCTION_TY")

        net = CurveNetwork3D(scene_name=bundle.scene_name, curves=curves, nodes=nodes)
        net.sync_endpoints_from_nodes()

        open_nodes = [nid for nid, node in net.nodes.items() if node.degree == 1]
        open_pos = np.array([net.nodes[nid].position for nid in open_nodes], dtype=np.float64) if open_nodes else np.zeros((0, 3))
        open_tang = np.array(
            [net.curves[net.nodes[nid].incident[0][0]].endpoint_tangent(net.nodes[nid].incident[0][1]) for nid in open_nodes],
            dtype=np.float64,
        ) if open_nodes else np.zeros((0, 3))

        if len(open_nodes) >= 2:
            o_tree = cKDTree(open_pos)
            for i, j in o_tree.query_pairs(r=9.0 * p_med):
                nid_a, nid_b = open_nodes[i], open_nodes[j]
                cid_a, end_a = net.nodes[nid_a].incident[0]
                cid_b, end_b = net.nodes[nid_b].incident[0]
                if cid_a == cid_b and net.curves[cid_a].arc_length() < 8.0 * p_med:
                    continue

                pa, pb = open_pos[i], open_pos[j]
                ta, tb = open_tang[i], open_tang[j]
                chord = pb - pa
                d = float(np.linalg.norm(chord))
                if d < 1e-6:
                    continue
                u_ab = chord / d
                cos_a = float(np.dot(ta, u_ab))
                cos_b = float(np.dot(tb, -u_ab))
                if cos_a < 0.60 or cos_b < 0.60:
                    continue
                b_ctrl = _hermite_bridge_controls(pa, ta, pb, tb)
                raw_proposals.append({
                    "kind": "END_TO_END",
                    "nid_a": nid_a,
                    "nid_b": nid_b,
                    "cid_a": cid_a,
                    "end_a": end_a,
                    "cid_b": cid_b,
                    "end_b": end_b,
                    "u_b": -1.0,
                    "target_pt": pb,
                    "ctrl": b_ctrl,
                    "dist_p": d / p_med,
                    "ang_pen": (1.0 - cos_a) + (1.0 - cos_b),
                })

        int_pts_list: list[np.ndarray] = []
        int_meta: list[tuple[int, float]] = []
        u_int_grid = np.linspace(0.10, 0.90, 17, dtype=np.float64)
        for cid, c in net.curves.items():
            if c.arc_length() < 3.5 * p_med:
                continue
            _, pts_all, _, _ = c.evaluate(num_samples=21)
            int_pts_list.append(pts_all[2:19])
            for u_val in u_int_grid:
                int_meta.append((cid, float(u_val)))

        if len(open_nodes) > 0 and int_pts_list:
            int_pts_arr = np.concatenate(int_pts_list, axis=0)
            int_tree = cKDTree(int_pts_arr)
            dists_t, idxs_t = int_tree.query(open_pos, k=6, distance_upper_bound=3.8 * p_med)
            for i, nid_a in enumerate(open_nodes):
                cid_a, end_a = net.nodes[nid_a].incident[0]
                pa, ta = open_pos[i], open_tang[i]
                seen_host: set[int] = set()
                for d_val, idx_m in zip(dists_t[i], idxs_t[i]):
                    if not np.isfinite(d_val) or idx_m >= len(int_pts_arr):
                        continue
                    cid_b, u_b = int_meta[int(idx_m)]
                    if cid_b == cid_a or cid_b in seen_host:
                        continue
                    seen_host.add(cid_b)
                    q_b = int_pts_arr[int(idx_m)]
                    d = float(d_val)
                    cos_approach = float(np.dot(ta, (q_b - pa) / d)) if d > 1e-6 else 1.0
                    if d > 1.5 * p_med and cos_approach < 0.55:
                        continue
                    raw_proposals.append({
                        "kind": "END_TO_INTERIOR_T",
                        "nid_a": nid_a,
                        "nid_b": -1,
                        "cid_a": cid_a,
                        "end_a": end_a,
                        "cid_b": cid_b,
                        "end_b": -1,
                        "u_b": u_b,
                        "target_pt": q_b.copy(),
                        "ctrl": np.vstack([pa, q_b]),
                        "dist_p": d / p_med,
                        "ang_pen": max(0.0, 1.0 - cos_approach),
                    })

        S_br = 10
        if raw_proposals:
            br_samples: list[np.ndarray] = []
            u_br = np.linspace(0.0, 1.0, S_br, dtype=np.float64)
            for prop in raw_proposals:
                ctrl = prop["ctrl"]
                if len(ctrl) == 2:
                    pts_b = (1.0 - u_br)[:, None] * ctrl[0] + u_br[:, None] * ctrl[1]
                else:
                    tmp_p = ParametricCurvePrimitive(0, "CUBIC_BSPLINE_3D", ctrl, clamped_uniform_knots(4, 3), 3)
                    _, pts_b, _, _ = tmp_p.evaluate(num_samples=S_br)
                br_samples.append(pts_b)
            br_eval = evaluator.query_points(np.concatenate(br_samples, axis=0), pixel_scale=p_med)

            max_fsv_br = max(1, int(0.12 * evaluator.num_depth_views))
            for idx_p, prop in enumerate(raw_proposals):
                sl = slice(idx_p * S_br, (idx_p + 1) * S_br)
                max_hull_v = float(br_eval["hull_viol_rate"][sl].max())
                tot_fsv = int(br_eval["free_space_viol"][sl].max())
                mean_edt = float(br_eval["edge_cost_mean"][sl].mean())
                min_sup = int(br_eval["edge_support_cnt"][sl].min())

                if max_hull_v > 0.065 or tot_fsv > max_fsv_br:
                    continue
                if mean_edt > 2.5 and prop["dist_p"] > 1.8:
                    continue

                geom_cost = 0.28 * prop["dist_p"] + 1.4 * prop["ang_pen"] + 0.55 * mean_edt - 0.12 * min(min_sup, 6)
                net_obj = geom_cost - 3.6
                if net_obj >= -0.05:
                    continue

                accepted_candidates.append(
                    ConnectionCandidate(
                        cand_id=len(accepted_candidates),
                        kind=prop["kind"],
                        curve_a=prop["cid_a"],
                        end_a=prop["end_a"],
                        curve_b=prop["cid_b"],
                        end_b=prop["end_b"],
                        target_u_b=prop["u_b"],
                        target_pt_b=prop["target_pt"],
                        bridge_ctrl=prop["ctrl"],
                        cost=float(net_obj),
                    )
                )

        if accepted_candidates:
            m_vars = len(accepted_candidates)
            c_obj = np.array([c.cost for c in accepted_candidates], dtype=np.float64)
            ep_to_vars: dict[tuple[int, int], list[int]] = {}
            pair_to_vars: dict[tuple[int, int], list[int]] = {}
            for v_i, cand in enumerate(accepted_candidates):
                ep_to_vars.setdefault((cand.curve_a, cand.end_a), []).append(v_i)
                if cand.kind == "END_TO_END":
                    ep_to_vars.setdefault((cand.curve_b, cand.end_b), []).append(v_i)
                pk = (min(cand.curve_a, cand.curve_b), max(cand.curve_a, cand.curve_b))
                pair_to_vars.setdefault(pk, []).append(v_i)

            rows_lp, cols_lp, vals_lp, ub_lp = [], [], [], []
            r_idx = 0
            for _, v_list in ep_to_vars.items():
                if len(v_list) > 1:
                    for vi in v_list:
                        rows_lp.append(r_idx)
                        cols_lp.append(vi)
                        vals_lp.append(1.0)
                    ub_lp.append(1.0)
                    r_idx += 1
            for (ca, cb), v_list in pair_to_vars.items():
                if ca != cb and len(v_list) > 1:
                    for vi in v_list:
                        rows_lp.append(r_idx)
                        cols_lp.append(vi)
                        vals_lp.append(1.0)
                    ub_lp.append(1.0)
                    r_idx += 1

            integrality = np.ones(m_vars, dtype=np.int8)
            bounds = Bounds(lb=np.zeros(m_vars), ub=np.ones(m_vars))
            if r_idx > 0:
                A_mat = csc_matrix((vals_lp, (rows_lp, cols_lp)), shape=(r_idx, m_vars))
                constraints = LinearConstraint(A_mat, -np.inf, np.array(ub_lp, dtype=np.float64))
                res = milp(c=c_obj, integrality=integrality, bounds=bounds, constraints=constraints)
            else:
                res = milp(c=c_obj, integrality=integrality, bounds=bounds)

            if res.success and res.x is not None:
                chosen_mask = res.x > 0.5
                selected_cands = [accepted_candidates[i] for i in range(m_vars) if chosen_mask[i]]

        next_cid = max(net.curves.keys()) + 1
        next_nid = max(net.nodes.keys()) + 1

        t_by_host: dict[int, list[ConnectionCandidate]] = {}
        e2e_cands: list[ConnectionCandidate] = []
        for cand in selected_cands:
            if cand.kind == "END_TO_INTERIOR_T":
                t_by_host.setdefault(cand.curve_b, []).append(cand)
            else:
                e2e_cands.append(cand)

        for host_cid, t_list in t_by_host.items():
            if host_cid not in net.curves:
                continue
            host = net.curves[host_cid]
            _, dense_pts, _, _ = host.evaluate(num_samples=65)
            t_list_sorted = sorted(t_list, key=lambda x: x.target_u_b)
            split_groups: list[tuple[float, list[ConnectionCandidate]]] = []
            for tc in t_list_sorted:
                if split_groups and abs(tc.target_u_b - split_groups[-1][0]) < 0.08:
                    split_groups[-1][1].append(tc)
                else:
                    split_groups.append((tc.target_u_b, [tc]))

            cut_indices = [0]
            cut_nodes = [host.start_node_id]
            created_t_nodes: list[tuple[int, list[ConnectionCandidate]]] = []
            for u_val, grp in split_groups:
                k_cut = int(np.clip(round(u_val * 64), 3, 61))
                if k_cut <= cut_indices[-1] + 2 or k_cut >= 62:
                    continue
                t_nid = next_nid
                next_nid += 1
                net.nodes[t_nid] = JunctionNode(node_id=t_nid, position=dense_pts[k_cut].copy(), incident=[], kind="JUNCTION_TY")
                cut_indices.append(k_cut)
                cut_nodes.append(t_nid)
                created_t_nodes.append((t_nid, grp))

            if not created_t_nodes:
                continue

            cut_indices.append(64)
            cut_nodes.append(host.end_node_id)
            was_cocirc = host.role == "COCIRCULAR_RING"
            del net.curves[host_cid]

            for seg_i in range(len(cut_indices) - 1):
                sub_pts = dense_pts[cut_indices[seg_i] : cut_indices[seg_i + 1] + 1]
                sub_ridge = ConsolidatedRidgeChain(
                    ridge_id=next_cid,
                    points_3d=sub_pts,
                    pixel_scale=host.pixel_scale,
                    supporting_views=list(host.supporting_views),
                    source_parent_ids=list(host.source_parent_ids),
                    is_silhouette_jump=(host.role == "SILHOUETTE_DEPTH_JUMP"),
                    confidence=host.confidence + (100.0 if was_cocirc else 0.0),
                )
                sub_prim = _adaptive_fit_primitive(sub_ridge)
                sub_prim.curve_id = next_cid
                sub_prim.start_node_id = cut_nodes[seg_i]
                sub_prim.end_node_id = cut_nodes[seg_i + 1]
                net.curves[next_cid] = sub_prim
                next_cid += 1

            for t_nid, grp in created_t_nodes:
                t_pos = net.nodes[t_nid].position
                for tc in grp:
                    if tc.curve_a not in net.curves:
                        continue
                    ca = net.curves[tc.curve_a]
                    ep_nid = ca.start_node_id if tc.end_a == 0 else ca.end_node_id
                    d_gap = float(np.linalg.norm(net.nodes[ep_nid].position - t_pos))
                    if d_gap <= 1.6 * p_med:
                        if tc.end_a == 0:
                            ca.start_node_id = t_nid
                        else:
                            ca.end_node_id = t_nid
                    else:
                        br_prim = ParametricCurvePrimitive(
                            curve_id=next_cid,
                            primitive_type="LINE_3D",
                            control_points=np.vstack([net.nodes[ep_nid].position, t_pos]),
                            knots=clamped_uniform_knots(2, 1),
                            degree=1,
                            start_node_id=ep_nid,
                            end_node_id=t_nid,
                            pixel_scale=ca.pixel_scale,
                            role="BRIDGE",
                            supporting_views=list(ca.supporting_views),
                            source_parent_ids=list(ca.source_parent_ids),
                            confidence=ca.confidence,
                        )
                        net.curves[next_cid] = br_prim
                        next_cid += 1
                    num_t_junctions += 1

        for cand in e2e_cands:
            if cand.curve_a not in net.curves or cand.curve_b not in net.curves:
                continue
            ca, cb = net.curves[cand.curve_a], net.curves[cand.curve_b]
            nid_a = ca.start_node_id if cand.end_a == 0 else ca.end_node_id
            nid_b = cb.start_node_id if cand.end_b == 0 else cb.end_node_id
            if nid_a == nid_b:
                continue
            pa, pb = net.nodes[nid_a].position, net.nodes[nid_b].position
            d_gap = float(np.linalg.norm(pb - pa))
            if d_gap <= 1.5 * p_med:
                net.nodes[nid_a].position = 0.5 * (pa + pb)
                for c_other in net.curves.values():
                    if c_other.start_node_id == nid_b:
                        c_other.start_node_id = nid_a
                    if c_other.end_node_id == nid_b:
                        c_other.end_node_id = nid_a
            else:
                ta = ca.endpoint_tangent(cand.end_a)
                tb = cb.endpoint_tangent(cand.end_b)
                b_ctrl = _hermite_bridge_controls(pa, ta, pb, tb)
                br_prim = ParametricCurvePrimitive(
                    curve_id=next_cid,
                    primitive_type="CUBIC_BSPLINE_3D",
                    control_points=b_ctrl,
                    knots=clamped_uniform_knots(4, 3),
                    degree=3,
                    start_node_id=nid_a,
                    end_node_id=nid_b,
                    pixel_scale=0.5 * (ca.pixel_scale + cb.pixel_scale),
                    role="BRIDGE",
                    supporting_views=sorted(set(ca.supporting_views) | set(cb.supporting_views)),
                    source_parent_ids=sorted(set(ca.source_parent_ids) | set(cb.source_parent_ids)),
                    confidence=0.5 * (ca.confidence + cb.confidence),
                )
                net.curves[next_cid] = br_prim
                next_cid += 1
            num_e2e_bridges += 1

        net.rebuild_node_incidence()
        net.sync_endpoints_from_nodes()

        cos_g1 = float(np.cos(np.deg2rad(28.0)))
        changed = True
        while changed:
            changed = False
            for nid in list(net.nodes.keys()):
                node = net.nodes.get(nid)
                if node is None or node.degree != 2:
                    continue
                (c1_id, e1_i), (c2_id, e2_i) = node.incident
                if c1_id == c2_id or c1_id not in net.curves or c2_id not in net.curves:
                    continue
                c1, c2 = net.curves[c1_id], net.curves[c2_id]
                t1_out = c1.endpoint_tangent(e1_i)
                t2_out = c2.endpoint_tangent(e2_i)
                if float(np.dot(t1_out, -t2_out)) < cos_g1:
                    node.kind = "CORNER"
                    continue

                _, pts1, _, _ = c1.evaluate(num_samples=max(16, len(c1.control_points) * 5))
                _, pts2, _, _ = c2.evaluate(num_samples=max(16, len(c2.control_points) * 5))
                seq1 = pts1 if e1_i == 1 else pts1[::-1]
                seq2 = pts2 if e2_i == 0 else pts2[::-1]
                start_nid = c1.start_node_id if e1_i == 1 else c1.end_node_id
                end_nid = c2.end_node_id if e2_i == 0 else c2.start_node_id
                if start_nid == end_nid:
                    continue

                joined_pts = np.vstack([seq1[:-1], seq2])
                was_cc = (c1.role == "COCIRCULAR_RING") or (c2.role == "COCIRCULAR_RING")
                merged_ridge = ConsolidatedRidgeChain(
                    ridge_id=next_cid,
                    points_3d=joined_pts,
                    pixel_scale=0.5 * (c1.pixel_scale + c2.pixel_scale),
                    supporting_views=sorted(set(c1.supporting_views) | set(c2.supporting_views)),
                    source_parent_ids=sorted(set(c1.source_parent_ids) | set(c2.source_parent_ids)),
                    is_silhouette_jump=(c1.role == "SILHOUETTE_DEPTH_JUMP" or c2.role == "SILHOUETTE_DEPTH_JUMP"),
                    confidence=max(c1.confidence, c2.confidence) + (100.0 if was_cc else 0.0),
                )
                new_prim = _adaptive_fit_primitive(merged_ridge)
                new_prim.curve_id = next_cid
                new_prim.start_node_id = start_nid
                new_prim.end_node_id = end_nid
                del net.curves[c1_id]
                del net.curves[c2_id]
                net.curves[next_cid] = new_prim
                next_cid += 1
                unified_merges += 1
                net.rebuild_node_incidence()
                changed = True
                break
    else:
        net = CurveNetwork3D(scene_name=bundle.scene_name)

    # Insert closed 360-degree COAXIAL_RING_FAMILY primitives cleanly (preserving exact antipodal C1/G1 closure)
    if coaxial_curves:
        cid_base = max(net.curves.keys(), default=-1) + 1
        nid_base = max(net.nodes.keys(), default=-1) + 1
        nid_remap: dict[int, int] = {}
        for cn in coaxial_nodes:
            new_nid = nid_base
            nid_base += 1
            nid_remap[cn.node_id] = new_nid
            net.nodes[new_nid] = JunctionNode(node_id=new_nid, position=cn.position.copy(), incident=[], kind="SMOOTH_CONTINUATION")

        cid_remap: dict[int, int] = {}
        for cc in coaxial_curves:
            new_cid = cid_base
            cid_base += 1
            cid_remap[cc.curve_id] = new_cid
            cc.curve_id = new_cid
            cc.start_node_id = nid_remap[cc.start_node_id]
            cc.end_node_id = nid_remap[cc.end_node_id]
            net.curves[new_cid] = cc

        for fam in coaxial_families:
            fam.member_curve_ids = [cid_remap[old_id] for old_id in fam.member_curve_ids if old_id in cid_remap]
        net.coaxial_families = coaxial_families
        net.rebuild_node_incidence()

    net.lathe_generators = lathe_generators
    net.tube_generators = tube_generators

    for node in net.nodes.values():
        if node.degree == 1:
            node.kind = "ENDPOINT"
        elif node.degree >= 3:
            node.kind = "JUNCTION_TY"
    net.sync_endpoints_from_nodes()

    planar_stats: dict[str, Any] = {"detected_planes": 0}
    if enable_planar_regularization and net.curves:
        planar_stats = discover_and_regularize_planar_wireframes(net, bundle=bundle, evaluator=evaluator)

    ribbon_stats: dict[str, Any] = {"annotated_ribbon_curves": 0}
    if enable_ribbon_annotation and net.curves:
        rib_est = SurfaceRibbonEstimator(bundle=bundle, evaluator=evaluator, device=device)
        ribbon_stats = rib_est.annotate_network_ribbons(net)

    stats = {
        "coaxial_ring_consolidation": coaxial_stats,
        "contour_generators": contour_gen_stats,
        "cocircular_consolidation": cocirc_stats,
        "planar_wireframe_regularization": planar_stats,
        "ribbon_3d_annotation": ribbon_stats,
        "initial_fitted_primitives": len(ridges) + len(coaxial_curves),
        "candidate_connections_scored": len(raw_proposals),
        "physically_valid_candidates": len(accepted_candidates),
        "milp_selected_connections": len(selected_cands),
        "selected_e2e_bridges": num_e2e_bridges,
        "selected_t_junctions": num_t_junctions,
        "g1_smooth_chain_unifications": unified_merges,
        "post_topology_summary": net.summary_stats(),
    }
    return net, stats
