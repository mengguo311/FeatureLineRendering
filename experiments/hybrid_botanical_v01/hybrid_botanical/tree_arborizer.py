"""Layer 2: 4-Level Botanical B-Spline Tree Arborization, Da Vinci Pipe-Model Radii & Wood Kernel Binding.

Constructs a complete connected kinematic branching tree:
  Level 0 (PRIMARY_TRUNK): 5 SweptTube main trunks from v05.
  Level 1 (SECONDARY_BRANCH): Geodesic shortest-path woody branches traced through 20k WOOD_STEM Gaussians.
  Level 2 (ROSETTE_STALK): Tapered umbel stalks connecting secondary branches to ~90 Palmate Rosette Hubs.
  Level 3 (PETIOLE_LINK): Individual petiole links connecting each Rosette Hub to all 472 leaf hinges p_base_l.

Also enforces Leonardo da Vinci's pipe-model radius conservation (r_parent^2.2 = sum r_child^2.2) and binds
all WOOD_STEM Gaussians (plus occluded petiole gap infill Gaussians) to Bishop frames along host B-splines!
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from .schema_and_io import (
    LABEL_WOOD_SKELETON,
    BotanicalTreeGraph,
    BranchSplineNode,
    GaussianCloudBank,
    LathePotPrimitive,
    build_cloud_bank,
    eval_clamped_bspline,
    fit_clamped_bspline_3d,
)


def compute_bishop_frame_along_spline(
    ctrl: np.ndarray, u_samples: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute curve points and twist-minimizing orthonormal Bishop frame (T, N1, N2) at u_samples in [0, 1]."""
    pts, d1 = eval_clamped_bspline(ctrl, u_samples)
    T = d1 / np.maximum(np.linalg.norm(d1, axis=1, keepdims=True), 1e-9)

    n = len(u_samples)
    N1 = np.zeros_like(T)
    N2 = np.zeros_like(T)

    # Stable initial normal orthogonal to T[0]
    ref = np.array([1.0, 0.0, 0.0]) if abs(float(T[0, 0])) < 0.85 else np.array([0.0, 1.0, 0.0])
    n0 = np.cross(T[0], ref)
    n0 /= max(float(np.linalg.norm(n0)), 1e-9)
    N1[0] = n0
    N2[0] = np.cross(T[0], N1[0])

    # Parallel transport along curve
    for i in range(1, n):
        axis = np.cross(T[i - 1], T[i])
        sin_a = float(np.linalg.norm(axis))
        cos_a = float(np.clip(np.dot(T[i - 1], T[i]), -1.0, 1.0))
        if sin_a < 1e-7:
            N1[i] = N1[i - 1]
        else:
            ax_u = axis / sin_a
            # Rodrigues rotation of N1[i-1]
            N1[i] = (
                N1[i - 1] * cos_a
                + np.cross(ax_u, N1[i - 1]) * sin_a
                + ax_u * float(np.dot(ax_u, N1[i - 1])) * (1.0 - cos_a)
            )
            N1[i] -= float(np.dot(N1[i], T[i])) * T[i]
            N1[i] /= max(float(np.linalg.norm(N1[i])), 1e-9)
        N2[i] = np.cross(T[i], N1[i])

    return pts, T, N1, N2


def build_4level_botanical_tree_and_bind_wood(
    cloud: GaussianCloudBank,
    leaf_p_bases: np.ndarray,
    swept_trunks: list[dict[str, Any]],
    pot_spec: LathePotPrimitive,
    p_med: float,
    train_views: list[Any] | None = None,
) -> tuple[BotanicalTreeGraph, GaussianCloudBank, dict[str, Any]]:
    """Construct the connected 4-level B-spline branching tree, apply pipe-model radii, and bind/infill wood kernels."""
    n_leaves = len(leaf_p_bases)

    # -----------------------------------------------------------------------
    # Step 1: Cluster 472 leaf petiole bases into natural Palmate Rosette Hubs (~85-105 umbels, ~4.8 leaflets/hub)
    # -----------------------------------------------------------------------
    if n_leaves >= 2:
        Z_link = linkage(leaf_p_bases, method="average")
        hub_labels_1based = fcluster(Z_link, t=0.088, criterion="distance")
        _, leaf_to_hub = np.unique(hub_labels_1based, return_inverse=True)
    else:
        leaf_to_hub = np.zeros(n_leaves, dtype=np.int32)

    n_hubs = int(leaf_to_hub.max()) + 1
    hub_positions = np.zeros((n_hubs, 3), dtype=np.float64)

    wood_mask_active = (cloud.kernel_labels == LABEL_WOOD_SKELETON) & (cloud.opacities >= 0.03)
    wood_pts_active = cloud.means[wood_mask_active].astype(np.float64)
    wood_rgb_active = cloud.rgb[wood_mask_active].astype(np.float32)
    wood_tree = cKDTree(wood_pts_active) if len(wood_pts_active) > 0 else None

    for h_i in range(n_hubs):
        m_h = leaf_to_hub == h_i
        mean_pet = leaf_p_bases[m_h].mean(axis=0)
        # Pull rosette hub slightly downward/inward toward nearest observed woody twig tip if within 1.8 cm!
        hub_pt = mean_pet - np.array([0.0, 0.0, 0.005])
        if wood_tree is not None:
            d_w, nn_w = wood_tree.query(hub_pt, k=1)
            if float(d_w) <= 0.018:
                hub_pt = 0.35 * hub_pt + 0.65 * wood_pts_active[int(nn_w)]
        hub_positions[h_i] = hub_pt

    # -----------------------------------------------------------------------
    # Step 2: Build Level-0 Primary Trunk Splines from v05 SweptTubeGenerators
    # -----------------------------------------------------------------------
    branches: list[BranchSplineNode] = []
    trunk_sample_pts: list[np.ndarray] = []
    trunk_sample_bid: list[int] = []
    trunk_sample_u: list[float] = []

    if not swept_trunks:
        # Fallback central trunk if synthetic scene has no swept_trunks
        swept_trunks = [{
            "spine_ctrl": np.array([[0.0, 0.0, pot_spec.h_max], [0.0, 0.0, 0.35]], dtype=np.float64),
            "radii_ctrl": np.array([0.012, 0.006], dtype=np.float64),
        }]

    for t_idx, tr in enumerate(swept_trunks):
        sp_raw = np.asarray(tr["spine_ctrl"], dtype=np.float64)
        # Ensure proximal root (u=0) is at bottom (min Z) and distal apex (u=1) is at top (max Z)!
        if sp_raw[0, 2] > sp_raw[-1, 2]:
            sp_raw = sp_raw[::-1].copy()
        ctrl_t = fit_clamped_bspline_3d(sp_raw, num_ctrl=min(8, max(4, len(sp_raw))))
        r_ctrl = np.asarray(tr["radii_ctrl"], dtype=np.float64)
        r_base = float(np.percentile(r_ctrl, 85.0))
        r_tip = float(np.percentile(r_ctrl, 25.0))
        branches.append(
            BranchSplineNode(
                branch_id=t_idx,
                level=0,
                parent_branch_id=-1,
                parent_u_attach=0.0,
                ctrl_points=ctrl_t,
                radius_base=max(r_base, 0.006),
                radius_tip=max(r_tip, 0.0035),
            )
        )
        u_dense = np.linspace(0.05, 1.0, 36)
        pts_d, _ = eval_clamped_bspline(ctrl_t, u_dense)
        for u_v, pt_v in zip(u_dense, pts_d):
            trunk_sample_pts.append(pt_v)
            trunk_sample_bid.append(t_idx)
            trunk_sample_u.append(float(u_v))

    n_trunk_nodes = len(trunk_sample_pts)
    trunk_pts_arr = np.array(trunk_sample_pts, dtype=np.float64)

    # -----------------------------------------------------------------------
    # Step 3: Voxel-Downsample WOOD_STEM Gaussians & Run Geodesic Dijkstra Arborization!
    # -----------------------------------------------------------------------
    # Downsample wood_pts_active onto a 6 mm grid to form clean candidate secondary branch waypoints
    if len(wood_pts_active) > 0:
        vox_keys = np.floor(wood_pts_active / 0.006).astype(np.int64)
        _, uniq_idx = np.unique(vox_keys, axis=0, return_index=True)
        stem_waypoints = wood_pts_active[np.sort(uniq_idx)]
        # Exclude waypoints already inside 1.2 cm of primary trunks so they represent genuine lateral twigs
        t_tree0 = cKDTree(trunk_pts_arr)
        d_to_tr, _ = t_tree0.query(stem_waypoints, k=1)
        stem_waypoints = stem_waypoints[d_to_tr > 0.012]
    else:
        stem_waypoints = np.zeros((0, 3), dtype=np.float64)

    n_wp = len(stem_waypoints)
    # Graph vertices: [0 .. n_trunk_nodes-1] = Trunk Roots (zero source cost!),
    #                 [n_trunk_nodes .. n_trunk_nodes+n_wp-1] = Woody Twig Waypoints,
    #                 [n_trunk_nodes+n_wp .. +n_hubs-1] = Palmate Rosette Hubs!
    all_graph_pts = np.vstack([trunk_pts_arr, stem_waypoints, hub_positions])
    n_verts = len(all_graph_pts)
    g_tree = cKDTree(all_graph_pts)

    # Connect k=18 neighbors within 14 cm; weight edges inside wood_pts heavily lower than empty-air gap jumps!
    k_g = min(18, n_verts)
    d_nn, idx_nn = g_tree.query(all_graph_pts, k=k_g, distance_upper_bound=0.14)

    rows_g, cols_g, wts_g = [], [], []
    for col_k in range(1, k_g):
        ok = np.isfinite(d_nn[:, col_k]) & (idx_nn[:, col_k] < n_verts) & (d_nn[:, col_k] > 1e-7)
        src = np.where(ok)[0]
        dst = idx_nn[ok, col_k]
        dist_v = d_nn[ok, col_k]

        # Botanical acropetal bias: branches grow upward & radially outward from trunks toward hubs!
        mids = 0.5 * (all_graph_pts[src] + all_graph_pts[dst])
        if wood_tree is not None:
            d_wood_mid, _ = wood_tree.query(mids, k=1)
        else:
            d_wood_mid = np.zeros(len(src))

        # Edges hugging observed wood kernels cost 1.0 * dist; occlusion gap bridges cost up to 3.8 * dist^1.25!
        gap_mult = 1.0 + 2.8 * np.clip(d_wood_mid / 0.018, 0.0, 1.5)
        edge_cost = (dist_v ** 1.22) * gap_mult
        rows_g.extend([src, dst])
        cols_g.extend([dst, src])
        wts_g.extend([edge_cost, edge_cost])

    # Ensure every hub has at least a direct fallback edge to its nearest trunk/waypoint if > 14 cm isolated
    hub_start = n_trunk_nodes + n_wp
    non_hub_tree = cKDTree(all_graph_pts[:hub_start])
    d_fb, nn_fb = non_hub_tree.query(hub_positions, k=1)
    h_arange = np.arange(hub_start, n_verts)
    fb_cost = (d_fb ** 1.25) * 4.0
    rows_g.extend([h_arange, nn_fb])
    cols_g.extend([nn_fb, h_arange])
    wts_g.extend([fb_cost, fb_cost])

    r_cat = np.concatenate(rows_g)
    c_cat = np.concatenate(cols_g)
    w_cat = np.concatenate(wts_g)
    adj = csr_matrix((w_cat, (r_cat, c_cat)), shape=(n_verts, n_verts))

    # Multi-source Dijkstra from all Primary Trunk nodes!
    trunk_sources = np.arange(n_trunk_nodes, dtype=np.int32)
    _, predecessors, min_src = dijkstra(
        adj, directed=False, indices=trunk_sources, return_predecessors=True, min_only=True
    )

    # -----------------------------------------------------------------------
    # Step 4: Group Shared Secondary Branch Paths & Fit Level-1, Level-2, Level-3 B-Splines!
    # -----------------------------------------------------------------------
    # Trace each hub's path back to its root trunk sample
    hub_paths: list[list[int]] = []
    first_step_groups: dict[tuple[int, int], list[int]] = {}
    for h_i in range(n_hubs):
        curr = hub_start + h_i
        chain = [curr]
        guard = 0
        while curr >= n_trunk_nodes and predecessors[curr] >= 0 and guard < 64:
            curr = int(predecessors[curr])
            chain.append(curr)
            guard += 1
        if chain[-1] >= n_trunk_nodes:
            # Fallback to nearest trunk node
            _, near_t = t_tree0.query(hub_positions[h_i], k=1)
            chain.append(int(near_t))
        chain.reverse()  # [trunk_sample_node, wp_1, wp_2, ..., hub_node]
        hub_paths.append(chain)
        key = (chain[0], chain[1] if len(chain) >= 3 else chain[0])
        first_step_groups.setdefault(key, []).append(h_i)

    # Create Level-1 (SECONDARY_BRANCH) for shared multi-hub woody boughs or medium branches,
    # and Level-2 (ROSETTE_STALK) into each Rosette Hub!
    hub_to_stalk_bid = np.zeros(n_hubs, dtype=np.int32)

    for (t_node, wp_first), h_list in first_step_groups.items():
        parent_tr_bid = trunk_sample_bid[t_node]
        parent_tr_u = trunk_sample_u[t_node]
        root_pt = all_graph_pts[t_node]

        if len(h_list) >= 2 and wp_first != t_node:
            # Shared Level-1 Secondary Branch Spine up to the centroid of intermediate waypoints!
            mid_pts = []
            for h_i in h_list:
                ch = hub_paths[h_i]
                if len(ch) >= 3:
                    mid_pts.append(all_graph_pts[ch[len(ch) // 2]])
                else:
                    mid_pts.append(0.55 * root_pt + 0.45 * hub_positions[h_i])
            fork_pt = np.mean(mid_pts, axis=0)
            wp1_pt = all_graph_pts[wp_first]
            sec_poly = np.vstack([root_pt, 0.5 * (root_pt + wp1_pt), fork_pt])
            sec_ctrl = fit_clamped_bspline_3d(sec_poly, num_ctrl=4)
            sec_bid = len(branches)
            branches.append(
                BranchSplineNode(
                    branch_id=sec_bid,
                    level=1,
                    parent_branch_id=parent_tr_bid,
                    parent_u_attach=parent_tr_u,
                    ctrl_points=sec_ctrl,
                    radius_base=0.0042,
                    radius_tip=0.0026,
                )
            )
            branches[parent_tr_bid].child_branch_ids.append(sec_bid)

            for h_i in h_list:
                hub_pt = hub_positions[h_i]
                # Smooth tangent-continuous stalk from fork_pt to hub_pt
                sec_tng = sec_ctrl[-1] - sec_ctrl[-2]
                sec_tng /= max(float(np.linalg.norm(sec_tng)), 1e-8)
                span_sh = float(np.linalg.norm(hub_pt - fork_pt))
                stalk_poly = np.vstack([
                    fork_pt,
                    fork_pt + 0.32 * span_sh * sec_tng,
                    0.35 * fork_pt + 0.65 * hub_pt,
                    hub_pt,
                ])
                stalk_ctrl = fit_clamped_bspline_3d(stalk_poly, num_ctrl=4)
                st_bid = len(branches)
                branches.append(
                    BranchSplineNode(
                        branch_id=st_bid,
                        level=2,
                        parent_branch_id=sec_bid,
                        parent_u_attach=1.0,
                        ctrl_points=stalk_ctrl,
                        radius_base=0.0024,
                        radius_tip=0.0016,
                    )
                )
                branches[sec_bid].child_branch_ids.append(st_bid)
                hub_to_stalk_bid[h_i] = st_bid
        else:
            # Single-rosette Secondary Branch + Stalk chain along its Dijkstra path
            for h_i in h_list:
                ch = hub_paths[h_i]
                poly_pts = all_graph_pts[ch]
                if len(poly_pts) == 2:
                    mid = 0.5 * (poly_pts[0] + poly_pts[1]) + np.array([0.0, 0.0, 0.008])
                    poly_pts = np.vstack([poly_pts[0], mid, poly_pts[1]])
                split_pt = 0.55 * poly_pts[0] + 0.45 * poly_pts[-1] if len(poly_pts) < 4 else poly_pts[len(poly_pts) // 2]
                sec_ctrl = fit_clamped_bspline_3d(np.vstack([poly_pts[0], 0.5 * (poly_pts[0] + split_pt), split_pt]), num_ctrl=4)
                sec_bid = len(branches)
                branches.append(
                    BranchSplineNode(
                        branch_id=sec_bid,
                        level=1,
                        parent_branch_id=parent_tr_bid,
                        parent_u_attach=parent_tr_u,
                        ctrl_points=sec_ctrl,
                        radius_base=0.0034,
                        radius_tip=0.0022,
                    )
                )
                branches[parent_tr_bid].child_branch_ids.append(sec_bid)

                st_ctrl = fit_clamped_bspline_3d(np.vstack([split_pt, 0.4 * split_pt + 0.6 * poly_pts[-1], poly_pts[-1]]), num_ctrl=4)
                st_bid = len(branches)
                branches.append(
                    BranchSplineNode(
                        branch_id=st_bid,
                        level=2,
                        parent_branch_id=sec_bid,
                        parent_u_attach=1.0,
                        ctrl_points=st_ctrl,
                        radius_base=0.0022,
                        radius_tip=0.0015,
                    )
                )
                branches[sec_bid].child_branch_ids.append(st_bid)
                hub_to_stalk_bid[h_i] = st_bid

    # Level-3 (PETIOLE_LINK): short petiole spline from each Palmate Rosette Hub to each of the 472 leaf hinges!
    leaf_to_pet_bid = np.zeros(n_leaves, dtype=np.int32)
    for lid in range(n_leaves):
        h_i = int(leaf_to_hub[lid])
        st_bid = int(hub_to_stalk_bid[h_i])
        h_pt = hub_positions[h_i]
        l_pt = leaf_p_bases[lid]
        st_tng = branches[st_bid].ctrl_points[-1] - branches[st_bid].ctrl_points[-2]
        st_tng /= max(float(np.linalg.norm(st_tng)), 1e-8)
        d_hl = max(float(np.linalg.norm(l_pt - h_pt)), 0.003)
        pet_poly = np.vstack([h_pt, h_pt + 0.35 * d_hl * st_tng, l_pt])
        pet_ctrl = fit_clamped_bspline_3d(pet_poly, num_ctrl=3)
        pet_bid = len(branches)
        branches.append(
            BranchSplineNode(
                branch_id=pet_bid,
                level=3,
                parent_branch_id=st_bid,
                parent_u_attach=1.0,
                ctrl_points=pet_ctrl,
                radius_base=0.0013,
                radius_tip=0.0009,
                attached_leaf_ids=[lid],
            )
        )
        branches[st_bid].child_branch_ids.append(pet_bid)
        leaf_to_pet_bid[lid] = pet_bid

    # -----------------------------------------------------------------------
    # Step 5: Enforce Leonardo da Vinci Pipe-Model Radius Conservation Bottom-Up!
    # r_parent^eta = sum(r_child^eta), eta = 2.15 (preserving measured trunk radii as lower bound on Level 0)
    # -----------------------------------------------------------------------
    eta = 2.15
    for lvl in (2, 1, 0):
        for br in branches:
            if br.level != lvl or not br.child_branch_ids:
                continue
            r_sum = sum(branches[cid].radius_base ** eta for cid in br.child_branch_ids)
            r_pipe = float(r_sum ** (1.0 / eta))
            if lvl == 0:
                br.radius_base = max(br.radius_base, min(0.018, 1.15 * r_pipe))
                br.radius_tip = max(br.radius_tip, min(0.011, 0.72 * r_pipe))
            else:
                br.radius_tip = float(np.clip(0.88 * r_pipe, 0.0012, 0.009))
                br.radius_base = float(np.clip(1.18 * r_pipe, br.radius_tip + 0.0003, 0.011))

    # -----------------------------------------------------------------------
    # Step 6: Infill Occluded Twig/Petiole Gaps & Bind All WOOD_SKELETON Gaussians to Bishop Frames!
    # -----------------------------------------------------------------------
    mean_wood_rgb = (
        np.median(wood_rgb_active, axis=0).astype(np.float32)
        if len(wood_rgb_active) > 0
        else np.array([0.42, 0.32, 0.22], dtype=np.float32)
    )
    infill_means: list[np.ndarray] = []
    infill_scales: list[np.ndarray] = []
    infill_quats: list[np.ndarray] = []
    infill_opac: list[float] = []
    infill_rgb: list[np.ndarray] = []

    # Sample dense spline table for binding & check Level 1..3 segments for missing wood kernels
    bind_pts_list: list[np.ndarray] = []
    bind_bid_list: list[np.ndarray] = []
    bind_u_list: list[np.ndarray] = []
    bind_n1_list: list[np.ndarray] = []
    bind_n2_list: list[np.ndarray] = []

    for br in branches:
        n_s = 28 if br.level <= 1 else 12
        u_s = np.linspace(0.0, 1.0, n_s)
        pts_b, T_b, N1_b, N2_b = compute_bishop_frame_along_spline(br.ctrl_points, u_s)
        bind_pts_list.append(pts_b)
        bind_bid_list.append(np.full(n_s, br.branch_id, dtype=np.int32))
        bind_u_list.append(u_s.astype(np.float32))
        bind_n1_list.append(N1_b.astype(np.float32))
        bind_n2_list.append(N2_b.astype(np.float32))

        if br.level >= 1 and wood_tree is not None:
            # Check where observed wood Gaussians are missing (> 8 mm away) along occluded twigs/petioles
            d_obs, _ = wood_tree.query(pts_b, k=1)
            for k_s in range(n_s):
                if float(d_obs[k_s]) > 0.0085:
                    rad_k = (1.0 - u_s[k_s]) * br.radius_base + u_s[k_s] * br.radius_tip
                    t_vec = T_b[k_s]
                    n1_vec = N1_b[k_s]
                    n2_vec = N2_b[k_s]
                    R_k = np.column_stack([t_vec, n1_vec, n2_vec])
                    if np.linalg.det(R_k) < 0:
                        R_k[:, 2] *= -1.0
                    q_xyzw = Rotation.from_matrix(R_k).as_quat()
                    q_wxyz = np.array([q_xyzw[3], q_xyzw[0], q_xyzw[1], q_xyzw[2]], dtype=np.float32)
                    seg_step = float(np.linalg.norm(pts_b[min(k_s + 1, n_s - 1)] - pts_b[max(k_s - 1, 0)])) * 0.5
                    infill_means.append(pts_b[k_s].astype(np.float32))
                    infill_scales.append(np.array([max(seg_step * 0.85, 0.0022), rad_k * 0.85, rad_k * 0.85], dtype=np.float32))
                    infill_quats.append(q_wxyz)
                    infill_opac.append(0.62 if br.level <= 2 else 0.48)
                    # Petioles blend slightly greener-olive toward the leaf base!
                    c_bark = mean_wood_rgb if br.level == 1 else (0.75 * mean_wood_rgb + 0.25 * np.array([0.28, 0.42, 0.20], dtype=np.float32))
                    infill_rgb.append(c_bark)

    n_infill = len(infill_means)
    if n_infill > 0 and train_views:
        # Visual-hull silhouette filter: never synthesize twig Gaussians sticking out into open background sky!
        cand_tw = np.array(infill_means, dtype=np.float64)
        out_sky_cnt = np.zeros(n_infill, dtype=np.int32)
        for vw in train_views[::2]:
            Xc = cand_tw @ vw.w2c[:3, :3].T + vw.w2c[:3, 3]
            zc = Xc[:, 2]
            ok = zc > 0.2
            us = np.round(vw.fx * (Xc[:, 0] / np.maximum(zc, 0.2)) + vw.cx).astype(np.int32)
            vs = np.round(vw.fy * (Xc[:, 1] / np.maximum(zc, 0.2)) + vw.cy).astype(np.int32)
            in_b = ok & (us >= 0) & (us < vw.width) & (vs >= 0) & (vs < vw.height)
            idx_b = np.where(in_b)[0]
            sky = vw.alpha[vs[idx_b], us[idx_b]] < 0.40
            out_sky_cnt[idx_b[sky]] += 1
        keep_tw = out_sky_cnt == 0
        infill_means = [infill_means[i] for i in range(n_infill) if keep_tw[i]]
        infill_scales = [infill_scales[i] for i in range(n_infill) if keep_tw[i]]
        infill_quats = [infill_quats[i] for i in range(n_infill) if keep_tw[i]]
        infill_opac = [infill_opac[i] for i in range(n_infill) if keep_tw[i]]
        infill_rgb = [infill_rgb[i] for i in range(n_infill) if keep_tw[i]]
        n_infill = len(infill_means)

    if n_infill > 0:
        new_means = np.concatenate([cloud.means, np.array(infill_means, dtype=np.float32)], axis=0)
        new_scales = np.concatenate([cloud.scales, np.array(infill_scales, dtype=np.float32)], axis=0)
        new_quats = np.concatenate([cloud.quats_wxyz, np.array(infill_quats, dtype=np.float32)], axis=0)
        new_opac = np.concatenate([cloud.opacities, np.array(infill_opac, dtype=np.float32)], axis=0)
        new_rgb = np.concatenate([cloud.rgb, np.array(infill_rgb, dtype=np.float32)], axis=0)
        new_lbls = np.concatenate([cloud.kernel_labels, np.full(n_infill, LABEL_WOOD_SKELETON, dtype=np.int32)], axis=0)
        cloud_out = build_cloud_bank(new_means, new_scales, new_quats, new_opac, new_rgb, new_lbls)
    else:
        cloud_out = cloud

    # Bind EVERY WOOD_SKELETON kernel (original + infilled) to its closest spline sample!
    all_bind_pts = np.concatenate(bind_pts_list, axis=0)
    all_bind_bid = np.concatenate(bind_bid_list, axis=0)
    all_bind_u = np.concatenate(bind_u_list, axis=0)
    all_bind_n1 = np.concatenate(bind_n1_list, axis=0)
    all_bind_n2 = np.concatenate(bind_n2_list, axis=0)

    b_tree = cKDTree(all_bind_pts)
    wood_all_idx = np.where(cloud_out.kernel_labels == LABEL_WOOD_SKELETON)[0].astype(np.int32)
    _, nn_b = b_tree.query(cloud_out.means[wood_all_idx].astype(np.float64), k=1)
    delta_w = cloud_out.means[wood_all_idx] - all_bind_pts[nn_b].astype(np.float32)
    off_n1 = np.sum(delta_w * all_bind_n1[nn_b], axis=1).astype(np.float32)
    off_n2 = np.sum(delta_w * all_bind_n2[nn_b], axis=1).astype(np.float32)

    tree_graph = BotanicalTreeGraph(
        branches=branches,
        rosette_hub_positions=hub_positions,
        leaf_to_hub_id=leaf_to_hub.astype(np.int32),
        leaf_to_petiole_branch=leaf_to_pet_bid,
        wood_kernel_indices=wood_all_idx,
        wood_host_branch=all_bind_bid[nn_b],
        wood_u_param=all_bind_u[nn_b],
        wood_local_n1=off_n1,
        wood_local_n2=off_n2,
        num_infilled_twig_kernels=n_infill,
    )

    # Verify 100% root-reachability for all 472 leaves!
    reachable = 0
    for lid in range(n_leaves):
        curr_b = int(leaf_to_pet_bid[lid])
        hops = 0
        while curr_b >= 0 and branches[curr_b].level > 0 and hops < 10:
            curr_b = branches[curr_b].parent_branch_id
            hops += 1
        if curr_b >= 0 and branches[curr_b].level == 0:
            reachable += 1

    stats = {
        "num_primary_trunks_lvl0": sum(1 for b in branches if b.level == 0),
        "num_secondary_branches_lvl1": sum(1 for b in branches if b.level == 1),
        "num_rosette_stalks_lvl2": sum(1 for b in branches if b.level == 2),
        "num_petiole_links_lvl3": sum(1 for b in branches if b.level == 3),
        "total_bspline_branches": len(branches),
        "num_palmate_rosette_hubs": n_hubs,
        "mean_leaflets_per_rosette_hub": round(float(n_leaves) / max(n_hubs, 1), 2),
        "leaf_to_root_reachability_pct": round(100.0 * reachable / max(n_leaves, 1), 2),
        "infilled_occluded_twig_kernels": n_infill,
        "bound_wood_kernels_total": int(len(wood_all_idx)),
    }
    return tree_graph, cloud_out, stats
