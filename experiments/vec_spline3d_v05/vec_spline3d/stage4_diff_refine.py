"""Stage 4: Multi-modal differentiable refinement for LINE_3D, ARC_3D, COAXIAL_RING, CUBIC_BSPLINE_3D, and RIBBON_3D."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from diff_gaussian_rasterization import GaussianRasterizationSettings, GaussianRasterizer
from scipy.spatial import cKDTree

from .contour_generators import evaluate_lathe_horizon_torch, evaluate_tubes_horizon_torch
from .multimodal_data import MultiModalSceneBundle, MultiModalView
from .schema import (
    CurveNetwork3D,
    bspline_basis_matrices,
    clamped_uniform_knots,
    evaluate_circular_arc_3pt_torch,
    fit_circular_arc_to_polyline,
    fit_clamped_bspline_to_polyline,
)
from .stage1_ray_clean import GPUViewFieldEvaluator


def _make_raster_settings(view: MultiModalView, device: torch.device, bg_val: float = 1.0) -> GaussianRasterizationSettings:
    w, h = view.width, view.height
    E = view.w2c.astype(np.float32)
    P = np.zeros((4, 4), dtype=np.float32)
    near, far = 0.2, 100.0
    P[0, 0] = 2.0 * view.fx / w
    P[1, 1] = 2.0 * view.fy / h
    P[0, 2] = (2.0 * view.cx + 1.0 - w) / w
    P[1, 2] = (2.0 * view.cy + 1.0 - h) / h
    P[2, 2] = far / (far - near)
    P[2, 3] = -far * near / (far - near)
    P[3, 2] = 1.0

    bg = torch.tensor([bg_val, bg_val, bg_val], dtype=torch.float32, device=device)
    viewmat = torch.tensor(E.T, dtype=torch.float32, device=device).contiguous()
    projmat = torch.tensor((P @ E).T, dtype=torch.float32, device=device).contiguous()
    campos = torch.tensor(view.cam_center, dtype=torch.float32, device=device).contiguous()

    return GaussianRasterizationSettings(
        image_height=h,
        image_width=w,
        tanfovx=float(w / (2.0 * view.fx)),
        tanfovy=float(h / (2.0 * view.fy)),
        bg=bg,
        scale_modifier=1.0,
        viewmatrix=viewmat,
        projmatrix=projmat,
        sh_degree=0,
        campos=campos,
        prefiltered=False,
        debug=False,
    )


def _post_refine_topology_cleanup(
    net: CurveNetwork3D,
    evaluator: GPUViewFieldEvaluator,
    p_med: float,
) -> dict[str, int]:
    """Execute surface-normal-aware post-refinement Merge, Arc-Upgrade/Linearize, and Spur Prune."""
    net.sync_endpoints_from_nodes()

    cids = sorted(net.curves.keys())
    S_chk = 15
    pts_per_c: dict[int, np.ndarray] = {}
    tang_per_c: dict[int, np.ndarray] = {}
    nrm_per_c: dict[int, np.ndarray | None] = {}
    all_mid_pts: list[np.ndarray] = []
    pt_owner: list[int] = []

    for cid in cids:
        _, pts, d1, _ = net.curves[cid].evaluate(num_samples=S_chk)
        nrm = np.linalg.norm(d1, axis=1, keepdims=True)
        u_d1 = np.where(nrm > 1e-9, d1 / np.maximum(nrm, 1e-9), np.array([1.0, 0.0, 0.0]))
        pts_per_c[cid] = pts
        tang_per_c[cid] = u_d1
        nrm_per_c[cid] = net.curves[cid].mean_surface_normal()
        all_mid_pts.append(pts)
        pt_owner.extend([cid] * S_chk)

    merged_duplicates = 0
    if len(cids) >= 2:
        pts_cat = np.concatenate(all_mid_pts, axis=0)
        owner_arr = np.array(pt_owner, dtype=np.int32)
        tree = cKDTree(pts_cat)
        dists, nbrs = tree.query(pts_cat, k=10, distance_upper_bound=0.80 * p_med)

        cos_dup = float(np.cos(np.deg2rad(20.0)))
        lengths = {cid: net.curves[cid].arc_length(num_samples=24) for cid in cids}
        cid_to_pos = {cid: i for i, cid in enumerate(cids)}
        absorbed: set[int] = set()
        for cid_short in sorted(cids, key=lambda c: lengths[c]):
            if cid_short in absorbed or cid_short not in net.curves:
                continue
            c_short = net.curves[cid_short]
            if c_short.role == "COAXIAL_RING":
                continue
            if c_short.start_node_id in net.nodes and c_short.end_node_id in net.nodes:
                if net.nodes[c_short.start_node_id].degree >= 2 and net.nodes[c_short.end_node_id].degree >= 2:
                    if c_short.role in ("BRIDGE", "COCIRCULAR_RING"):
                        continue

            n_short = nrm_per_c[cid_short]
            base_row = cid_to_pos[cid_short] * S_chk
            host_votes: dict[int, int] = {}
            for s_i in range(S_chk):
                g_i = base_row + s_i
                t_a = tang_per_c[cid_short][s_i]
                matched_hosts_for_sample: set[int] = set()
                for d_val, g_j in zip(dists[g_i], nbrs[g_i]):
                    if not np.isfinite(d_val) or g_j >= len(pts_cat):
                        continue
                    cid_h = int(owner_arr[g_j])
                    if cid_h == cid_short or cid_h in absorbed or lengths[cid_h] < lengths[cid_short]:
                        continue
                    # RIBBON_3D surface normal compatibility guard: never collapse opposing front/back leaf rims!
                    n_host = nrm_per_c[cid_h]
                    if n_short is not None and n_host is not None and float(np.dot(n_short, n_host)) < -0.25:
                        continue
                    s_j = int(g_j) % S_chk
                    if abs(float(np.dot(t_a, tang_per_c[cid_h][s_j]))) >= cos_dup:
                        matched_hosts_for_sample.add(cid_h)
                for mh in matched_hosts_for_sample:
                    host_votes[mh] = host_votes.get(mh, 0) + 1

            best_host = max(host_votes.items(), key=lambda kv: kv[1])[0] if host_votes else None
            if best_host is not None and host_votes[best_host] >= int(0.80 * S_chk):
                host_c = net.curves[best_host]
                host_c.supporting_views = sorted(set(host_c.supporting_views) | set(c_short.supporting_views))
                host_c.source_parent_ids = sorted(set(host_c.source_parent_ids) | set(c_short.source_parent_ids))
                del net.curves[cid_short]
                absorbed.add(cid_short)
                merged_duplicates += 1

    net.rebuild_node_incidence()

    # 2. Simplify refined CUBIC_BSPLINE_3D to LINE_3D or ARC_3D (preserving RibbonGeometry control_normals length!)
    planar_line_cids: set[int] = set()
    for pp in net.planar_patches:
        planar_line_cids.update(int(c) for c in pp.get("member_curve_ids", []))
    linearized_count = 0
    upgraded_to_arc_count = 0
    for cid_k, curve in net.curves.items():
        if curve.primitive_type == "CUBIC_BSPLINE_3D":
            _, pts, _, _ = curve.evaluate(num_samples=24)
            ctrl_l, knots_l, deg_l, max_err_l = fit_clamped_bspline_to_polyline(pts, num_ctrl=2)
            tol_lin = 0.56 * curve.pixel_scale if cid_k in planar_line_cids else 0.42 * curve.pixel_scale
            if max_err_l <= tol_lin:
                if curve.ribbon is not None and len(curve.ribbon.control_normals) >= 2:
                    cn = curve.ribbon.control_normals
                    curve.ribbon.control_normals = np.vstack([cn[0], cn[-1]])
                curve.primitive_type = "LINE_3D"
                curve.control_points = ctrl_l
                curve.knots = knots_l
                curve.degree = deg_l
                linearized_count += 1
                continue

            if cid_k in planar_line_cids:
                continue
            ctrl_a, max_err_a, arc_meta = fit_circular_arc_to_polyline(pts, pin_endpoints=True)
            if (
                arc_meta.get("valid")
                and max_err_a <= 0.54 * curve.pixel_scale
                and math.radians(12.0) <= arc_meta["sweep_rad"] <= math.radians(350.0)
                and 2.5 * curve.pixel_scale <= arc_meta["radius"] <= 180.0 * curve.pixel_scale
            ):
                if curve.ribbon is not None and len(curve.ribbon.control_normals) >= 2:
                    _, _, _, _, N_sm = curve.evaluate_darboux_frame(num_samples=5)
                    curve.ribbon.control_normals = np.vstack([N_sm[0], N_sm[2], N_sm[4]])
                curve.primitive_type = "ARC_3D"
                curve.control_points = ctrl_a
                curve.knots = clamped_uniform_knots(3, 2)
                curve.degree = 2
                upgraded_to_arc_count += 1

    # 3. Weak-Support Isolated Spur Pruning (protecting closed COAXIAL_RING loops)
    pruned_count = 0
    rem_cids = sorted(net.curves.keys())
    if rem_cids:
        S_pr = 12
        chk_pts = np.concatenate([net.curves[c].evaluate(num_samples=S_pr)[1] for c in rem_cids], axis=0)
        q_res = evaluator.query_points(chk_pts, pixel_scale=p_med)
        for i_c, cid in enumerate(rem_cids):
            c = net.curves[cid]
            if c.role == "COAXIAL_RING":
                continue
            sl = slice(i_c * S_pr, (i_c + 1) * S_pr)
            h_viol = float(q_res["hull_viol_rate"][sl].max())
            m_edt = float(q_res["edge_cost_mean"][sl].mean())
            d_start = net.nodes[c.start_node_id].degree if c.start_node_id in net.nodes else 1
            d_end = net.nodes[c.end_node_id].degree if c.end_node_id in net.nodes else 1
            is_isolated = d_start == 1 and d_end == 1
            if h_viol > 0.10 or (is_isolated and c.arc_length() < 3.0 * p_med and m_edt > 2.4):
                del net.curves[cid]
                pruned_count += 1

    for fam in net.coaxial_families:
        fam.member_curve_ids = [cid for cid in fam.member_curve_ids if cid in net.curves]

    net.rebuild_node_incidence()
    net.sync_endpoints_from_nodes()
    return {
        "post_merged_duplicates": merged_duplicates,
        "linearized_to_line3d": linearized_count,
        "upgraded_splines_to_arc3d": upgraded_to_arc_count,
        "pruned_weak_spurs": pruned_count,
    }


def run_stage4_diff_refine(
    net: CurveNetwork3D,
    bundle: MultiModalSceneBundle,
    device: torch.device,
    num_steps: int = 80,
    lr: float = 2.5e-4,
    samples_per_curve: int = 14,
) -> tuple[CurveNetwork3D, dict[str, Any]]:
    """Jointly optimize JunctionNodes, Line/Arc/BSpline controls, Coaxial Ring heights/radii, and Darboux Ribbon widths."""
    if not net.curves:
        return net, {"steps": 0}

    net.rebuild_node_incidence()
    net.sync_endpoints_from_nodes()
    p_med = bundle.median_pixel_scale
    evaluator = GPUViewFieldEvaluator(bundle.train_views, device=device)

    build_views = [v for v in bundle.train_views if v.depth is not None]
    raster_settings = [_make_raster_settings(v, device=device, bg_val=1.0) for v in build_views]
    target_ink_maps = [torch.tensor(v.edge_strength, dtype=torch.float32, device=device) for v in build_views]
    target_band_masks = [
        torch.tensor((v.edge_dt <= 4.5).astype(np.float32), dtype=torch.float32, device=device)
        for v in build_views
    ]

    nid_list = sorted(net.nodes.keys())
    nid_to_idx = {nid: i for i, nid in enumerate(nid_list)}
    init_node_pos = np.stack([net.nodes[nid].position for nid in nid_list], axis=0)

    # Partition curves into: (1) Splines/Lines, (2) Free ARC_3D, and (3) Exact Coaxial Ring ARC_3D pairs!
    spline_cids = [cid for cid in sorted(net.curves.keys()) if net.curves[cid].primitive_type != "ARC_3D"]
    free_arc_cids = [
        cid for cid in sorted(net.curves.keys())
        if net.curves[cid].primitive_type == "ARC_3D" and net.curves[cid].role != "COAXIAL_RING"
    ]
    coax_arc_cids = [
        cid for cid in sorted(net.curves.keys())
        if net.curves[cid].primitive_type == "ARC_3D" and net.curves[cid].role == "COAXIAL_RING"
    ]

    node_param = torch.nn.Parameter(torch.tensor(init_node_pos, dtype=torch.float32, device=device))
    node_init_t = node_param.detach().clone()

    int_ctrl_chunks: list[np.ndarray] = []
    ctrl_is_int: list[bool] = []
    ctrl_src_idx: list[int] = []
    curve_ctrl_slices: list[tuple[int, int]] = []
    int_cursor = 0
    tot_ctrl_cursor = 0

    for cid in spline_cids:
        c = net.curves[cid]
        m = len(c.control_points)
        c_start = tot_ctrl_cursor
        ctrl_is_int.append(False)
        ctrl_src_idx.append(nid_to_idx[c.start_node_id])
        tot_ctrl_cursor += 1
        if m > 2:
            int_ctrl_chunks.append(c.control_points[1:-1])
            for k in range(m - 2):
                ctrl_is_int.append(True)
                ctrl_src_idx.append(int_cursor + k)
                tot_ctrl_cursor += 1
            int_cursor += m - 2
        ctrl_is_int.append(False)
        ctrl_src_idx.append(nid_to_idx[c.end_node_id])
        tot_ctrl_cursor += 1
        curve_ctrl_slices.append((c_start, tot_ctrl_cursor))

    K_spline_ctrl = tot_ctrl_cursor
    init_int_ctrl = np.concatenate(int_ctrl_chunks, axis=0) if int_ctrl_chunks else np.zeros((0, 3), dtype=np.float64)
    int_param = torch.nn.Parameter(torch.tensor(init_int_ctrl, dtype=torch.float32, device=device))
    int_init_t = int_param.detach().clone()

    # Free ARC_3D midpoint parameters
    init_arc_mid = (
        np.stack([net.curves[cid].control_points[1] for cid in free_arc_cids], axis=0)
        if free_arc_cids
        else np.zeros((0, 3), dtype=np.float64)
    )
    arc_mid_param = torch.nn.Parameter(torch.tensor(init_arc_mid, dtype=torch.float32, device=device))
    arc_mid_init_t = arc_mid_param.detach().clone()
    arc_start_nidx = torch.tensor(
        [nid_to_idx[net.curves[cid].start_node_id] for cid in free_arc_cids], dtype=torch.long, device=device
    )
    arc_end_nidx = torch.tensor(
        [nid_to_idx[net.curves[cid].end_node_id] for cid in free_arc_cids], dtype=torch.long, device=device
    )

    # Coaxial Ring Manifold Parameters: 2 intrinsic DOF (delta_h, delta_r) per 360-degree ring across ALL arbitrary-axis families!
    num_coax_rings = len(coax_arc_cids) // 2
    coax_dh_param = torch.nn.Parameter(torch.zeros(num_coax_rings, dtype=torch.float32, device=device))
    coax_dr_param = torch.nn.Parameter(torch.zeros(num_coax_rings, dtype=torch.float32, device=device))
    coax_o_t = None
    coax_a_t = None
    coax_e1_t = None
    coax_e2_t = None
    coax_h0_t = None
    coax_r0_t = None
    coax_sl_t = None
    fam_by_id = {fam.family_id: fam for fam in net.coaxial_families}
    if num_coax_rings > 0 and net.coaxial_families:
        o_list, a_list, e1_list, e2_list = [], [], [], []
        h0_list, r0_list, sl_list = [], [], []
        for r_idx in range(num_coax_rings):
            c_even = net.curves[coax_arc_cids[2 * r_idx]]
            fid = c_even.ribbon.coaxial_family_id if c_even.ribbon is not None else net.coaxial_families[0].family_id
            fam = fam_by_id.get(fid, net.coaxial_families[0])
            dr_dh_np = np.gradient(fam.profile_r, fam.profile_h) if len(fam.profile_h) >= 2 else np.zeros_like(fam.profile_r)
            hk = c_even.ribbon.coaxial_ring_h if c_even.ribbon is not None else fam.ring_heights[0]
            rk = c_even.ribbon.coaxial_ring_r if c_even.ribbon is not None else fam.ring_radii[0]
            o_list.append(fam.axis_origin)
            a_list.append(fam.axis_dir)
            e1_list.append(fam.e1)
            e2_list.append(fam.e2)
            h0_list.append(hk)
            r0_list.append(rk)
            sl_list.append(float(np.interp(np.clip(hk, fam.h_min, fam.h_max), fam.profile_h, dr_dh_np)) if len(fam.profile_h) >= 2 else 0.0)
        coax_o_t = torch.tensor(np.stack(o_list, axis=0), dtype=torch.float32, device=device)
        coax_a_t = torch.tensor(np.stack(a_list, axis=0), dtype=torch.float32, device=device)
        coax_e1_t = torch.tensor(np.stack(e1_list, axis=0), dtype=torch.float32, device=device)
        coax_e2_t = torch.tensor(np.stack(e2_list, axis=0), dtype=torch.float32, device=device)
        coax_h0_t = torch.tensor(h0_list, dtype=torch.float32, device=device)
        coax_r0_t = torch.tensor(r0_list, dtype=torch.float32, device=device)
        coax_sl_t = torch.tensor(sl_list, dtype=torch.float32, device=device)

    S = samples_per_curve
    u_grid_np = np.linspace(0.0, 1.0, S, dtype=np.float64)
    u_grid_t = torch.tensor(u_grid_np, dtype=torch.float32, device=device)

    B_sp = None
    B_du_sp = None
    D2_sp = None
    if spline_cids:
        is_int_mask = torch.tensor(ctrl_is_int, dtype=torch.bool, device=device)
        node_gather_idx = torch.tensor(
            [idx for flag, idx in zip(ctrl_is_int, ctrl_src_idx) if not flag], dtype=torch.long, device=device
        )
        int_gather_idx = torch.tensor(
            [idx for flag, idx in zip(ctrl_is_int, ctrl_src_idx) if flag], dtype=torch.long, device=device
        )
        node_slot_idx = torch.where(~is_int_mask)[0]
        int_slot_idx = torch.where(is_int_mask)[0]

        rows_b, cols_b, vals_b, vals_d1 = [], [], [], []
        rows_d2, cols_d2, vals_d2 = [], [], []
        d2_row_cursor = 0
        for c_i, cid in enumerate(spline_cids):
            c = net.curves[cid]
            c_lo, c_hi = curve_ctrl_slices[c_i]
            m = c_hi - c_lo
            B, B_du, _, _, _ = bspline_basis_matrices(m, u_grid_np, degree=c.degree, knots=c.knots)
            r_base = c_i * S
            rr, cc = np.nonzero(np.abs(B) > 1e-10)
            rows_b.append(r_base + rr)
            cols_b.append(c_lo + cc)
            vals_b.append(B[rr, cc])

            rr_u, cc_u = np.nonzero((np.abs(B) > 1e-10) | (np.abs(B_du) > 1e-10))
            vals_d1.append((r_base + rr_u, c_lo + cc_u, B_du[rr_u, cc_u]))

            if m >= 3:
                D2 = np.diff(np.eye(m, dtype=np.float64), n=2, axis=0)
                r2, c2 = np.nonzero(D2)
                rows_d2.append(d2_row_cursor + r2)
                cols_d2.append(c_lo + c2)
                vals_d2.append(D2[r2, c2])
                d2_row_cursor += m - 2

        N_sp_samples = len(spline_cids) * S
        B_sp = torch.sparse_coo_tensor(
            torch.tensor(np.vstack([np.concatenate(rows_b), np.concatenate(cols_b)]), dtype=torch.long, device=device),
            torch.tensor(np.concatenate(vals_b), dtype=torch.float32, device=device),
            size=(N_sp_samples, K_spline_ctrl),
        ).coalesce()
        d1_r = np.concatenate([x[0] for x in vals_d1])
        d1_c = np.concatenate([x[1] for x in vals_d1])
        d1_v = np.concatenate([x[2] for x in vals_d1])
        B_du_sp = torch.sparse_coo_tensor(
            torch.tensor(np.vstack([d1_r, d1_c]), dtype=torch.long, device=device),
            torch.tensor(d1_v, dtype=torch.float32, device=device),
            size=(N_sp_samples, K_spline_ctrl),
        ).coalesce()
        if d2_row_cursor > 0:
            D2_sp = torch.sparse_coo_tensor(
                torch.tensor(np.vstack([np.concatenate(rows_d2), np.concatenate(cols_d2)]), dtype=torch.long, device=device),
                torch.tensor(np.concatenate(vals_d2), dtype=torch.float32, device=device),
                size=(d2_row_cursor, K_spline_ctrl),
            ).coalesce()

    ordered_all_cids = spline_cids + free_arc_cids + coax_arc_cids
    has_ribbons = any(net.curves[c].ribbon is not None for c in ordered_all_cids)

    # Learnable per-curve Darboux ribbon half-width (in pixels) + precomputed Darboux surface normals per segment!
    init_widths = np.array(
        [net.curves[c].ribbon.half_width_px if net.curves[c].ribbon is not None else net.curves[c].width_px for c in ordered_all_cids],
        dtype=np.float32,
    )
    width_param = torch.nn.Parameter(torch.tensor(init_widths, dtype=torch.float32, device=device))
    width_init_t = width_param.detach().clone()

    seg_normals_np = np.zeros((len(ordered_all_cids), S - 1, 3), dtype=np.float32)
    seg_inshift_np = np.zeros((len(ordered_all_cids), S - 1), dtype=np.float32)
    for idx_c, cid in enumerate(ordered_all_cids):
        c = net.curves[cid]
        _, _, _, _, N_f = c.evaluate_darboux_frame(num_samples=S)
        n_m = 0.5 * (N_f[1:] + N_f[:-1])
        n_m /= np.maximum(np.linalg.norm(n_m, axis=1, keepdims=True), 1e-8)
        seg_normals_np[idx_c] = n_m.astype(np.float32)
        if c.ribbon is not None:
            seg_inshift_np[idx_c] = float(c.ribbon.inward_shift_px * c.ribbon.inward_sign)

    seg_normals_t = torch.tensor(seg_normals_np.reshape(-1, 3), dtype=torch.float32, device=device)
    seg_inshift_t = torch.tensor(seg_inshift_np.reshape(-1), dtype=torch.float32, device=device)

    px_per_seg = torch.tensor(
        np.repeat([net.curves[c].pixel_scale for c in ordered_all_cids], S - 1), dtype=torch.float32, device=device
    )
    opac_per_seg = torch.tensor(
        np.repeat([net.curves[c].opacity for c in ordered_all_cids], S - 1), dtype=torch.float32, device=device
    )[:, None]
    black_colors = torch.zeros((len(ordered_all_cids) * (S - 1), 3), dtype=torch.float32, device=device)

    # View-Dependent Envelope Radius Parameters (Lathe meridian profile delta_r & SweptTube B-spline delta_r)
    has_lathe_gen = len(net.lathe_generators) > 0
    has_tube_gen = len(net.tube_generators) > 0
    lathe_dr_params = torch.nn.ParameterList([
        torch.nn.Parameter(torch.zeros(len(lg.profile_r), dtype=torch.float32, device=device))
        for lg in net.lathe_generators
    ])
    tube_dr_params = torch.nn.ParameterList([
        torch.nn.Parameter(torch.zeros(len(tg.control_radii), dtype=torch.float32, device=device))
        for tg in net.tube_generators
    ])

    # Precompute Architectural Planar Coplanarity & Principal-Axis Orthogonality Regularizer Tensors
    pln_nidx_list: list[int] = []
    pln_nrm_list: list[list[float]] = []
    pln_off_list: list[float] = []
    ax_s_list: list[int] = []
    ax_e_list: list[int] = []
    ax_u_list: list[list[float]] = []
    for pp in net.planar_patches:
        n_vec = pp["normal"]
        d_val = float(pp["offset_d"])
        ax_map = pp.get("_axis_map", {})
        seen_p_nodes: set[int] = set()
        for cid_p in pp.get("member_curve_ids", []):
            cp = net.curves.get(int(cid_p))
            if cp is None:
                continue
            for end_nid in (cp.start_node_id, cp.end_node_id):
                if end_nid in nid_to_idx and end_nid not in seen_p_nodes:
                    seen_p_nodes.add(end_nid)
                    pln_nidx_list.append(nid_to_idx[end_nid])
                    pln_nrm_list.append(n_vec)
                    pln_off_list.append(d_val)
            if int(cid_p) in ax_map and cp.primitive_type == "LINE_3D" and cp.start_node_id in nid_to_idx and cp.end_node_id in nid_to_idx:
                ax_s_list.append(nid_to_idx[cp.start_node_id])
                ax_e_list.append(nid_to_idx[cp.end_node_id])
                ax_u_list.append(ax_map[int(cid_p)])

    has_planar_reg = len(pln_nidx_list) > 0
    pln_nidx_t = torch.tensor(pln_nidx_list, dtype=torch.long, device=device) if has_planar_reg else None
    pln_nrm_t = torch.tensor(pln_nrm_list, dtype=torch.float32, device=device) if has_planar_reg else None
    pln_off_t = torch.tensor(pln_off_list, dtype=torch.float32, device=device) if has_planar_reg else None
    has_axis_reg = len(ax_s_list) > 0
    ax_s_t = torch.tensor(ax_s_list, dtype=torch.long, device=device) if has_axis_reg else None
    ax_e_t = torch.tensor(ax_e_list, dtype=torch.long, device=device) if has_axis_reg else None
    ax_u_t = torch.tensor(ax_u_list, dtype=torch.float32, device=device) if has_axis_reg else None

    train_cams_t = torch.tensor(
        np.stack([v.cam_center for v in bundle.train_views], axis=0), dtype=torch.float32, device=device
    )
    build_cams_t = (
        torch.tensor(np.stack([v.cam_center for v in build_views], axis=0), dtype=torch.float32, device=device)
        if build_views
        else torch.zeros((0, 3), dtype=torch.float32, device=device)
    )

    env_param_list = list(lathe_dr_params) + list(tube_dr_params)
    optimizer = torch.optim.Adam(
        [
            {"params": [node_param, int_param, arc_mid_param], "lr": lr},
            {"params": [coax_dh_param, coax_dr_param], "lr": lr * 1.5},
            {"params": env_param_list, "lr": lr * 1.2},
            {"params": [width_param], "lr": 4e-3},
        ]
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, num_steps), eta_min=lr * 0.15)

    loss_history: list[dict[str, float]] = []
    rng = np.random.default_rng(42)
    num_train_v = len(bundle.train_views)
    batch_v_size = min(16, num_train_v)

    for step in range(num_steps):
        optimizer.zero_grad()

        pts_parts: list[torch.Tensor] = []
        d1_parts: list[torch.Tensor] = []
        loss_smooth = torch.tensor(0.0, dtype=torch.float32, device=device)

        if spline_cids and B_sp is not None and B_du_sp is not None:
            P_all = torch.zeros((K_spline_ctrl, 3), dtype=torch.float32, device=device)
            P_all[node_slot_idx] = node_param[node_gather_idx]
            if len(int_slot_idx) > 0:
                P_all[int_slot_idx] = int_param[int_gather_idx]
            pts_parts.append(torch.sparse.mm(B_sp, P_all))
            d1_parts.append(torch.sparse.mm(B_du_sp, P_all))
            if D2_sp is not None:
                loss_smooth = ((torch.sparse.mm(D2_sp, P_all) / max(p_med, 1e-4)) ** 2).mean()

        if free_arc_cids:
            a_p0 = node_param[arc_start_nidx]
            a_p1 = node_param[arc_end_nidx]
            pts_a, d1_a = evaluate_circular_arc_3pt_torch(a_p0, arc_mid_param, a_p1, u_grid_t)
            pts_parts.append(pts_a)
            d1_parts.append(d1_a)

        if num_coax_rings > 0 and coax_o_t is not None and coax_a_t is not None and coax_e1_t is not None and coax_e2_t is not None and coax_h0_t is not None and coax_r0_t is not None and coax_sl_t is not None:
            # Exact differentiable coaxial manifold evaluation across all arbitrary-axis families: two 180-deg arcs per ring
            h_cur = coax_h0_t + coax_dh_param
            r_cur = (coax_r0_t + coax_sl_t * coax_dh_param + coax_dr_param).clamp(min=0.01)
            ctrs_r = coax_o_t + h_cur[:, None] * coax_a_t  # (R, 3)

            p0_r = ctrs_r + r_cur[:, None] * coax_e1_t
            p90_r = ctrs_r + r_cur[:, None] * coax_e2_t
            p180_r = ctrs_r - r_cur[:, None] * coax_e1_t
            p270_r = ctrs_r - r_cur[:, None] * coax_e2_t

            # Interleave [half0, half1] per ring to match coax_arc_cids order
            c_p0 = torch.stack([p0_r, p180_r], dim=1).reshape(-1, 3)
            c_pm = torch.stack([p90_r, p270_r], dim=1).reshape(-1, 3)
            c_p1 = torch.stack([p180_r, p0_r], dim=1).reshape(-1, 3)
            pts_cx, d1_cx = evaluate_circular_arc_3pt_torch(c_p0, c_pm, c_p1, u_grid_t)
            pts_parts.append(pts_cx)
            d1_parts.append(d1_cx)

        pts_3d = torch.cat(pts_parts, dim=0)
        d1_3d = torch.cat(d1_parts, dim=0)
        t_3d = F.normalize(d1_3d, dim=-1, eps=1e-8)

        v_indices = rng.choice(num_train_v, size=batch_v_size, replace=False)
        v_idx_t = torch.tensor(v_indices, dtype=torch.long, device=device)

        R_sub = evaluator.R[v_idx_t]
        t_sub = evaluator.t[v_idx_t]
        fx_sub = evaluator.fx[v_idx_t]
        fy_sub = evaluator.fy[v_idx_t]
        cx_sub = evaluator.cx[v_idx_t]
        cy_sub = evaluator.cy[v_idx_t]
        has_d_sub = evaluator.has_depth[v_idx_t]

        Xc = torch.einsum("vij,nj->vni", R_sub, pts_3d) + t_sub[:, None, :]
        z = Xc[:, :, 2].clamp(min=1e-2)
        u = fx_sub[:, None] * (Xc[:, :, 0] / z) + cx_sub[:, None]
        v = fy_sub[:, None] * (Xc[:, :, 1] / z) + cy_sub[:, None]

        gx = 2.0 * (u / (evaluator.w - 1.0)) - 1.0
        gy = 2.0 * (v / (evaluator.h - 1.0)) - 1.0
        grid = torch.stack([gx, gy], dim=-1).unsqueeze(2)

        sampled = F.grid_sample(
            evaluator.maps[v_idx_t, :4, :, :], grid, mode="bilinear", padding_mode="border", align_corners=True
        ).squeeze(-1)
        sampled_d = F.grid_sample(
            evaluator.maps[v_idx_t, 4:6, :, :], grid, mode="nearest", padding_mode="border", align_corners=True
        ).squeeze(-1)
        tang2d_smp = F.grid_sample(
            evaluator.tang2d[v_idx_t], grid, mode="bilinear", padding_mode="border", align_corners=True
        ).squeeze(-1).permute(0, 2, 1)

        alpha = sampled[:, 0, :]
        out_dt = sampled[:, 1, :]
        edt = sampled[:, 2, :]
        surf_d = sampled_d[:, 0, :]
        d_jump = sampled_d[:, 1, :]

        with torch.no_grad():
            in_f = (Xc[:, :, 2] > 0.2) & (u >= 1.0) & (u <= evaluator.w - 2.0) & (v >= 1.0) & (v <= evaluator.h - 2.0)
            smooth_opaque = has_d_sub[:, None] & (alpha > 0.95) & (surf_d > 0.2) & (d_jump < 0.004)
            occluded = smooth_opaque & (z > surf_d + 5.0 * p_med)
            vis_weight = (in_f & (~occluded) & (edt <= 6.0)).float()

        loss_chamfer = (F.smooth_l1_loss(edt, torch.zeros_like(edt), reduction="none", beta=1.0) * vis_weight).sum() / vis_weight.sum().clamp(min=1.0)

        Tc = torch.einsum("vij,nj->vni", R_sub, t_3d)
        du_t = fx_sub[:, None] * (Tc[:, :, 0] / z - Xc[:, :, 0] * Tc[:, :, 2] / (z * z))
        dv_t = fy_sub[:, None] * (Tc[:, :, 1] / z - Xc[:, :, 1] * Tc[:, :, 2] / (z * z))
        proj_t2d = F.normalize(torch.stack([du_t, dv_t], dim=-1), dim=-1, eps=1e-6)
        tgt_t2d = F.normalize(tang2d_smp, dim=-1, eps=1e-6)
        cos_2d = torch.abs((proj_t2d * tgt_t2d).sum(dim=-1))
        near_edge_w = vis_weight * (edt.detach() <= 3.5).float()
        loss_tang = ((1.0 - cos_2d) * near_edge_w).sum() / near_edge_w.sum().clamp(min=1.0)

        loss_hull = F.relu(out_dt - 0.35).mean()
        fsv_mask = (in_f & smooth_opaque).float()
        loss_freespace = (F.relu(surf_d.detach() - 6.0 * p_med - z) * fsv_mask).sum() / fsv_mask.sum().clamp(min=1.0)

        # Differentiable View-Dependent Occluding Contour Loss on each camera's own horizon!
        loss_env = torch.tensor(0.0, dtype=torch.float32, device=device)
        if has_lathe_gen or has_tube_gen:
            cams_sub = train_cams_t[v_idx_t]
            h_pts_list, h_tng_list = [], []
            for lg_i, l_dr in zip(net.lathe_generators, lathe_dr_params):
                lp_h, lt_h, _ = evaluate_lathe_horizon_torch(lg_i, l_dr, cams_sub, num_samples=36)
                h_pts_list.append(lp_h)
                h_tng_list.append(lt_h)
            if has_tube_gen:
                tp_h, tt_h, _ = evaluate_tubes_horizon_torch(net.tube_generators, list(tube_dr_params), cams_sub, num_samples=18)
                h_pts_list.append(tp_h)
                h_tng_list.append(tt_h)

            pts_h = torch.cat(h_pts_list, dim=1)  # (V_sub, M_h, 3)
            tng_h = torch.cat(h_tng_list, dim=1)  # (V_sub, M_h, 3)
            Xc_h = torch.einsum("vij,vnj->vni", R_sub, pts_h) + t_sub[:, None, :]
            z_h = Xc_h[:, :, 2].clamp(min=1e-2)
            u_h = fx_sub[:, None] * (Xc_h[:, :, 0] / z_h) + cx_sub[:, None]
            v_h = fy_sub[:, None] * (Xc_h[:, :, 1] / z_h) + cy_sub[:, None]
            grid_h = torch.stack([2.0 * (u_h / (evaluator.w - 1.0)) - 1.0, 2.0 * (v_h / (evaluator.h - 1.0)) - 1.0], dim=-1).unsqueeze(2)
            smp_h = F.grid_sample(
                evaluator.maps[v_idx_t, :3, :, :], grid_h, mode="bilinear", padding_mode="border", align_corners=True
            ).squeeze(-1)
            t2d_h = F.grid_sample(
                evaluator.tang2d[v_idx_t], grid_h, mode="bilinear", padding_mode="border", align_corners=True
            ).squeeze(-1).permute(0, 2, 1)

            in_fh = ((Xc_h[:, :, 2] > 0.2) & (u_h >= 2.0) & (u_h <= evaluator.w - 3.0) & (v_h >= 2.0) & (v_h <= evaluator.h - 3.0) & (smp_h[:, 2, :].detach() <= 6.5)).float()
            env_cham = (F.smooth_l1_loss(smp_h[:, 2, :], torch.zeros_like(smp_h[:, 2, :]), reduction="none", beta=1.0) * in_fh).sum() / in_fh.sum().clamp(min=1.0)
            env_hull = F.relu(smp_h[:, 1, :] - 0.15).mean()

            Tc_h = torch.einsum("vij,vnj->vni", R_sub, tng_h)
            du_h = fx_sub[:, None] * (Tc_h[:, :, 0] / z_h - Xc_h[:, :, 0] * Tc_h[:, :, 2] / (z_h * z_h))
            dv_h = fy_sub[:, None] * (Tc_h[:, :, 1] / z_h - Xc_h[:, :, 1] * Tc_h[:, :, 2] / (z_h * z_h))
            pt2_h = F.normalize(torch.stack([du_h, dv_h], dim=-1), dim=-1, eps=1e-6)
            tt2_h = F.normalize(t2d_h, dim=-1, eps=1e-6)
            env_tang = ((1.0 - torch.abs((pt2_h * tt2_h).sum(dim=-1))) * in_fh).sum() / in_fh.sum().clamp(min=1.0)

            env_reg = torch.tensor(0.0, dtype=torch.float32, device=device)
            for l_dr in lathe_dr_params:
                if len(l_dr) >= 3:
                    env_reg = env_reg + ((l_dr[1:] - l_dr[:-1]) / max(p_med, 1e-4)).pow(2).mean()
            for tp in tube_dr_params:
                if len(tp) >= 2:
                    env_reg = env_reg + ((tp[1:] - tp[:-1]) / max(p_med, 1e-4)).pow(2).mean()
            loss_env = 0.45 * env_cham + 0.20 * env_tang + 2.5 * env_hull + 0.08 * env_reg

        loss_render = torch.tensor(0.0, dtype=torch.float32, device=device)
        if build_views:
            bv_i = step % len(build_views)
            pts_c = pts_3d.reshape(len(ordered_all_cids), S, 3)
            seg_vecs = pts_c[:, 1:, :] - pts_c[:, :-1, :]
            seg_mids = (0.5 * (pts_c[:, 1:, :] + pts_c[:, :-1, :])).reshape(-1, 3)
            seg_lens = torch.linalg.norm(seg_vecs, dim=-1).reshape(-1)
            seg_dir = F.normalize(seg_vecs.reshape(-1, 3), dim=-1, eps=1e-8)

            w_seg = width_param.clamp(0.32, 0.52).repeat_interleave(S - 1)
            sig_para = torch.maximum(0.75 * px_per_seg, 0.65 * seg_lens)
            sig_width = w_seg * px_per_seg

            if has_ribbons:
                n_orth = seg_normals_t - (seg_normals_t * seg_dir).sum(dim=-1, keepdim=True) * seg_dir
                N_cur = F.normalize(n_orth, dim=-1, eps=1e-6)
                B_cur = F.normalize(torch.linalg.cross(N_cur, seg_dir, dim=-1), dim=-1, eps=1e-6)
                seg_mids = seg_mids + (seg_inshift_t * px_per_seg)[:, None] * B_cur
                sig_thick = 0.65 * sig_width

                tt = seg_dir[:, :, None] * seg_dir[:, None, :]
                bb = B_cur[:, :, None] * B_cur[:, None, :]
                nn = N_cur[:, :, None] * N_cur[:, None, :]
                cov3 = (sig_para[:, None, None] ** 2) * tt + (sig_width[:, None, None] ** 2) * bb + (sig_thick[:, None, None] ** 2) * nn
            else:
                tt = seg_dir[:, :, None] * seg_dir[:, None, :]
                eye3 = torch.eye(3, dtype=torch.float32, device=device)[None, :, :]
                cov3 = (sig_para[:, None, None] ** 2) * tt + (sig_width[:, None, None] ** 2) * (eye3 - tt)

            cov6 = cov3[:, [0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]]
            rast_mids = seg_mids
            rast_opac = opac_per_seg
            rast_cols = black_colors

            # Include bv_i's differentiable envelope horizon surflets in the CUDA rasterizer pass!
            if has_lathe_gen or has_tube_gen:
                cam_bv = build_cams_t[bv_i : bv_i + 1]
                hm_list, hc_list, ho_list = [], [], []
                for lg0, l_dr in zip(net.lathe_generators, lathe_dr_params):
                    lp_b, _, ln_b = evaluate_lathe_horizon_torch(lg0, l_dr, cam_bv, num_samples=44)
                    for br_p, br_n in ((lp_b[0, :44], ln_b[0, :44]), (lp_b[0, 44:], ln_b[0, 44:])):
                        sv = br_p[1:] - br_p[:-1]
                        sl_len = torch.linalg.norm(sv, dim=-1)
                        sd = F.normalize(sv, dim=-1, eps=1e-8)
                        nm = F.normalize(0.5 * (br_n[1:] + br_n[:-1]) - ((0.5 * (br_n[1:] + br_n[:-1]) * sd).sum(-1, keepdim=True)) * sd, dim=-1, eps=1e-6)
                        bm = F.normalize(torch.linalg.cross(nm, sd, dim=-1), dim=-1, eps=1e-6)
                        sm = 0.5 * (br_p[1:] + br_p[:-1]) - (lg0.inward_shift_px * lg0.pixel_scale) * nm
                        sp = torch.maximum(torch.full_like(sl_len, 0.75 * lg0.pixel_scale), 0.65 * sl_len)
                        sw = torch.full_like(sl_len, lg0.half_width_px * lg0.pixel_scale)
                        sb = torch.full_like(sl_len, lg0.thickness_px * lg0.pixel_scale)
                        c3 = (sp[:, None, None] ** 2) * (sd[:, :, None] * sd[:, None, :]) + (sw[:, None, None] ** 2) * (nm[:, :, None] * nm[:, None, :]) + (sb[:, None, None] ** 2) * (bm[:, :, None] * bm[:, None, :])
                        hm_list.append(sm)
                        hc_list.append(c3[:, [0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]])
                        ho_list.append(torch.full((len(sm), 1), lg0.opacity, dtype=torch.float32, device=device))

                if hm_list:
                    hm_cat = torch.cat(hm_list, dim=0)
                    rast_mids = torch.cat([rast_mids, hm_cat], dim=0)
                    cov6 = torch.cat([cov6, torch.cat(hc_list, dim=0)], dim=0)
                    rast_opac = torch.cat([rast_opac, torch.cat(ho_list, dim=0)], dim=0)
                    rast_cols = torch.cat([rast_cols, torch.zeros_like(hm_cat)], dim=0)

            means2d = torch.zeros_like(rast_mids, requires_grad=True)
            rendered_rgb = GaussianRasterizer(raster_settings[bv_i])(
                means3D=rast_mids.contiguous(),
                means2D=means2d,
                opacities=rast_opac.contiguous(),
                colors_precomp=rast_cols,
                cov3D_precomp=cov6.contiguous(),
            )[0]
            pred_ink = (1.0 - rendered_rgb.mean(dim=0)).clamp(0.0, 1.0)
            band = target_band_masks[bv_i]
            loss_render = (
                0.7 * (torch.abs(pred_ink - target_ink_maps[bv_i]) * band).sum() / band.sum().clamp(min=1.0)
                + 0.3 * (pred_ink * (1.0 - band)).mean()
            )

        disp_node = ((node_param - node_init_t) / max(p_med, 1e-4)) ** 2
        disp_int = ((int_param - int_init_t) / max(p_med, 1e-4)) ** 2 if len(int_param) > 0 else torch.zeros_like(disp_node[:1])
        disp_arc = ((arc_mid_param - arc_mid_init_t) / max(p_med, 1e-4)) ** 2 if len(arc_mid_param) > 0 else torch.zeros_like(disp_node[:1])
        disp_w = (width_param - width_init_t) ** 2
        loss_anchor = (disp_node.mean() + disp_int.mean() + disp_arc.mean()) / 3.0 + 0.25 * disp_w.mean()
        if num_coax_rings > 0:
            loss_anchor = loss_anchor + 0.08 * (((coax_dh_param / max(p_med, 1e-4)) ** 2).mean() + ((coax_dr_param / max(p_med, 1e-4)) ** 2).mean())

        loss_planar = torch.tensor(0.0, dtype=torch.float32, device=device)
        if has_planar_reg and pln_nidx_t is not None and pln_nrm_t is not None and pln_off_t is not None:
            p_res = ((node_param[pln_nidx_t] * pln_nrm_t).sum(dim=-1) - pln_off_t) / max(p_med, 1e-4)
            loss_planar = loss_planar + 0.18 * (p_res ** 2).mean()
        if has_axis_reg and ax_s_t is not None and ax_e_t is not None and ax_u_t is not None:
            e_dir = F.normalize(node_param[ax_e_t] - node_param[ax_s_t], dim=-1, eps=1e-6)
            loss_planar = loss_planar + 0.22 * (1.0 - (e_dir * ax_u_t).sum(dim=-1) ** 2).mean()

        total_loss = (
            1.0 * loss_chamfer
            + 0.35 * loss_tang
            + 2.5 * loss_hull
            + 4.0 * loss_freespace
            + 0.45 * loss_render
            + 1.0 * loss_env
            + 1.0 * loss_planar
            + 0.04 * loss_smooth
            + 0.06 * loss_anchor
        )

        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(
            [node_param, int_param, arc_mid_param, coax_dh_param, coax_dr_param, width_param] + env_param_list,
            max_norm=1.0,
        )
        optimizer.step()

        with torch.no_grad():
            max_drift = 2.5 * p_med
            for par, init_t in ((node_param, node_init_t), (int_param, int_init_t), (arc_mid_param, arc_mid_init_t)):
                if len(par) > 0:
                    d_p = par.data - init_t
                    p_len = torch.linalg.norm(d_p, dim=-1, keepdim=True)
                    par.data.copy_(init_t + torch.where(p_len > max_drift, d_p * (max_drift / p_len.clamp(min=1e-9)), d_p))
            if num_coax_rings > 0:
                coax_dh_param.data.clamp_(-1.6 * p_med, 1.6 * p_med)
                coax_dr_param.data.clamp_(-0.7 * p_med, 0.7 * p_med)
            for l_dr in lathe_dr_params:
                l_dr.data.clamp_(-1.2 * p_med, 1.2 * p_med)
            for tp in tube_dr_params:
                tp.data.clamp_(-0.8 * p_med, 0.8 * p_med)
            width_param.data.clamp_(0.32, 0.52)

        scheduler.step()

        if step == 0 or (step + 1) % 20 == 0 or step == num_steps - 1:
            loss_history.append({
                "step": int(step + 1),
                "total": float(total_loss.item()),
                "chamfer_px": float(loss_chamfer.item()),
                "tang": float(loss_tang.item()),
                "hull": float(loss_hull.item()),
                "render": float(loss_render.item()),
            })

    final_nodes = node_param.detach().cpu().numpy().astype(np.float64)
    final_ints = int_param.detach().cpu().numpy().astype(np.float64)
    final_arc_mids = arc_mid_param.detach().cpu().numpy().astype(np.float64)
    final_widths = width_param.detach().cpu().numpy().astype(np.float64)

    for i, nid in enumerate(nid_list):
        net.nodes[nid].position = final_nodes[i].copy()

    int_read = 0
    for cid in spline_cids:
        c = net.curves[cid]
        m = len(c.control_points)
        c.control_points[0] = net.nodes[c.start_node_id].position.copy()
        if m > 2:
            c.control_points[1:-1] = final_ints[int_read : int_read + (m - 2)].copy()
            int_read += m - 2
        c.control_points[-1] = net.nodes[c.end_node_id].position.copy()

    for i_a, cid in enumerate(free_arc_cids):
        c = net.curves[cid]
        c.control_points[0] = net.nodes[c.start_node_id].position.copy()
        c.control_points[1] = final_arc_mids[i_a].copy()
        c.control_points[-1] = net.nodes[c.end_node_id].position.copy()

    # Write back exact coaxial ring positions & updated per-family ring heights/radii across all arbitrary-axis families!
    if num_coax_rings > 0 and net.coaxial_families:
        dh_np = coax_dh_param.detach().cpu().numpy().astype(np.float64)
        dr_np = coax_dr_param.detach().cpu().numpy().astype(np.float64)
        fam_new_hs: dict[int, list[float]] = {fam.family_id: [] for fam in net.coaxial_families}
        fam_new_rs: dict[int, list[float]] = {fam.family_id: [] for fam in net.coaxial_families}
        for r_idx in range(num_coax_rings):
            c0 = net.curves[coax_arc_cids[2 * r_idx]]
            c1 = net.curves[coax_arc_cids[2 * r_idx + 1]]
            fid = c0.ribbon.coaxial_family_id if c0.ribbon is not None else net.coaxial_families[0].family_id
            fam = fam_by_id.get(fid, net.coaxial_families[0])
            dr_dh_np = np.gradient(fam.profile_r, fam.profile_h) if len(fam.profile_h) >= 2 else np.zeros_like(fam.profile_r)
            h0 = c0.ribbon.coaxial_ring_h if c0.ribbon is not None else fam.ring_heights[0]
            r0 = c0.ribbon.coaxial_ring_r if c0.ribbon is not None else fam.ring_radii[0]
            sl = float(np.interp(np.clip(h0, fam.h_min, fam.h_max), fam.profile_h, dr_dh_np)) if len(fam.profile_h) >= 2 else 0.0
            hk = float(h0 + dh_np[r_idx])
            rk = max(0.01, float(r0 + sl * dh_np[r_idx] + dr_np[r_idx]))
            ctr = fam.axis_origin + hk * fam.axis_dir
            p0 = ctr + rk * fam.e1
            p90 = ctr + rk * fam.e2
            p180 = ctr - rk * fam.e1
            p270 = ctr - rk * fam.e2

            net.nodes[c0.start_node_id].position = p0.copy()
            net.nodes[c0.end_node_id].position = p180.copy()
            c0.control_points = np.vstack([p0, p90, p180])
            c1.control_points = np.vstack([p180, p270, p0])
            if c0.ribbon is not None:
                c0.ribbon.coaxial_ring_h = hk
                c0.ribbon.coaxial_ring_r = rk
            if c1.ribbon is not None:
                c1.ribbon.coaxial_ring_h = hk
                c1.ribbon.coaxial_ring_r = rk
            fam_new_hs.setdefault(fam.family_id, []).append(hk)
            fam_new_rs.setdefault(fam.family_id, []).append(rk)
        for fam in net.coaxial_families:
            if fam_new_hs.get(fam.family_id):
                fam.ring_heights = fam_new_hs[fam.family_id]
                fam.ring_radii = fam_new_rs[fam.family_id]

    for idx_c, cid in enumerate(ordered_all_cids):
        c = net.curves[cid]
        w_opt = float(final_widths[idx_c])
        c.width_px = w_opt
        if c.ribbon is not None:
            c.ribbon.half_width_px = w_opt
            c.ribbon.thickness_px = round(0.65 * w_opt, 4)

    for lg, l_dr in zip(net.lathe_generators, lathe_dr_params):
        ldr_np = l_dr.detach().cpu().numpy().astype(np.float64)
        lg.profile_r = np.maximum(0.02, lg.profile_r + ldr_np)
    if has_tube_gen:
        for tg, tp in zip(net.tube_generators, tube_dr_params):
            tdr_np = tp.detach().cpu().numpy().astype(np.float64)
            tg.control_radii = np.maximum(1.2 * p_med, tg.control_radii + tdr_np)

    cleanup_stats = _post_refine_topology_cleanup(net, evaluator=evaluator, p_med=p_med)
    stats = {
        "optimization_steps": num_steps,
        "loss_history": loss_history,
        "topology_cleanup": cleanup_stats,
        "final_summary": net.summary_stats(),
    }
    return net, stats
