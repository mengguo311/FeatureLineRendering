"""Co-circular 3D arc & rotational rib consolidation (unites broken dashes along curved rings/grooves)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

from .schema import fit_circular_arc_to_polyline
from .stage1_ray_clean import GPUViewFieldEvaluator, _compute_polyline_tangents
from .stage2_scms_consolidate import ConsolidatedRidgeChain


def _circle_from_two_oriented_segments(
    p1: np.ndarray, t1: np.ndarray, p2: np.ndarray, t2: np.ndarray, p_scale: float
) -> dict[str, Any] | None:
    """Parent-Zucker 3D co-circularity hypothesis from two oriented curve midpoints."""
    chord = p2 - p1
    d = float(np.linalg.norm(chord))
    if d < 1.5 * p_scale or d > 22.0 * p_scale:
        return None
    u_c = chord / d

    # Align t1 and t2 generally along u_c
    t1_a = t1 if float(np.dot(t1, u_c)) >= 0.0 else -t1
    t2_a = t2 if float(np.dot(t2, u_c)) >= 0.0 else -t2

    cos_c1 = float(np.dot(t1_a, u_c))
    cos_c2 = float(np.dot(t2_a, u_c))
    if cos_c1 < 0.72 or cos_c2 < 0.72:
        return None

    ang1 = math.acos(min(1.0, max(-1.0, cos_c1)))
    ang2 = math.acos(min(1.0, max(-1.0, cos_c2)))
    # Co-circular symmetry: chord makes nearly equal angles with both tangents, and total turn >= 8 deg
    if abs(ang1 - ang2) > math.radians(10.0) or (ang1 + ang2) < math.radians(8.0):
        return None

    n_vec = np.cross(t1_a, t2_a)
    n_len = float(np.linalg.norm(n_vec))
    if n_len < math.sin(math.radians(8.0)):
        return None
    normal = n_vec / n_len
    if normal[2] < 0:
        normal = -normal

    # Coplanarity check: chord must lie in the plane orthogonal to normal
    if abs(float(np.dot(chord, normal))) > 1.2 * p_scale:
        return None

    half_turn = 0.5 * (ang1 + ang2)
    sin_ht = math.sin(half_turn)
    if sin_ht < 1e-4:
        return None
    radius = d / (2.0 * sin_ht)
    if radius < 3.0 * p_scale or radius > 160.0 * p_scale:
        return None

    # Radial inward unit vectors in the circle plane
    # Since curve turns from t1_a toward t2_a around n_raw = t1_a x t2_a, center lies along (n_raw_unit x t_a)
    n_turn = np.cross(t1_a, t2_a) / n_len
    r_in_1 = np.cross(n_turn, t1_a)
    r_in_2 = np.cross(n_turn, t2_a)
    c1 = p1 + radius * r_in_1
    c2 = p2 + radius * r_in_2
    if float(np.linalg.norm(c1 - c2)) > 2.2 * p_scale:
        return None
    center = 0.5 * (c1 + c2)

    # Orthonormal basis in plane
    e1 = p1 - center
    e1 -= float(np.dot(e1, normal)) * normal
    e1_n = float(np.linalg.norm(e1))
    if e1_n < 1e-8:
        return None
    e1 /= e1_n
    e2 = np.cross(normal, e1)
    return {"center": center, "normal": normal, "e1": e1, "e2": e2, "radius": radius}


def consolidate_cocircular_arcs(
    ridges: list[ConsolidatedRidgeChain],
    evaluator: GPUViewFieldEvaluator,
    median_pixel_scale: float,
    max_gap_px: float = 16.0,
) -> tuple[list[ConsolidatedRidgeChain], dict[str, Any]]:
    """Discover co-circular ridge families (e.g., broken pot ribs & curved rims) and unite verified arcs."""
    if len(ridges) < 2:
        return ridges, {"consolidated_groups": 0, "merged_ridges": 0}

    p = median_pixel_scale
    n_r = len(ridges)
    mids = np.array([r.points_3d[len(r.points_3d) // 2] for r in ridges], dtype=np.float64)
    ridge_tangs = [_compute_polyline_tangents(r.points_3d) for r in ridges]
    mid_tangs = np.array([rt[len(rt) // 2] for rt in ridge_tangs], dtype=np.float64)
    ridge_lens = np.array(
        [np.linalg.norm(np.diff(r.points_3d, axis=0), axis=1).sum() for r in ridges], dtype=np.float64
    )

    # 1. Gather candidate 3D circles from (a) curved individual ridges and (b) co-circular neighbor pairs
    cand_circles: list[dict[str, Any]] = []
    for i, r in enumerate(ridges):
        if len(r.points_3d) >= 5 and ridge_lens[i] >= 4.0 * p:
            _, err, meta = fit_circular_arc_to_polyline(r.points_3d)
            if meta.get("valid") and err <= 0.65 * p and 3.0 * p <= meta["radius"] <= 160.0 * p:
                n_u = meta["normal"] / max(float(np.linalg.norm(meta["normal"])), 1e-12)
                if n_u[2] < 0:
                    n_u = -n_u
                e1 = r.points_3d[0] - meta["center"]
                e1 -= float(np.dot(e1, n_u)) * n_u
                en = float(np.linalg.norm(e1))
                if en > 1e-8:
                    e1 /= en
                    e2 = np.cross(n_u, e1)
                    cand_circles.append({
                        "center": meta["center"],
                        "normal": n_u,
                        "e1": e1,
                        "e2": e2,
                        "radius": meta["radius"],
                    })

    mid_tree = cKDTree(mids)
    for i, j in mid_tree.query_pairs(r=20.0 * p):
        if ridge_lens[i] > 28.0 * p or ridge_lens[j] > 28.0 * p:
            continue
        circ = _circle_from_two_oriented_segments(mids[i], mid_tangs[i], mids[j], mid_tangs[j], p)
        if circ is not None:
            cand_circles.append(circ)

    if not cand_circles:
        return ridges, {"candidate_circles": 0, "consolidated_groups": 0, "merged_ridges": 0}

    # Deduplicate candidate circles via quantized (center / 2p, normal / 0.12, radius / 2p)
    dedup_circles: list[dict[str, Any]] = []
    seen_keys: set[tuple[int, ...]] = set()
    for cc in cand_circles:
        key = (
            int(round(cc["center"][0] / (2.2 * p))),
            int(round(cc["center"][1] / (2.2 * p))),
            int(round(cc["center"][2] / (2.2 * p))),
            int(round(cc["normal"][0] / 0.12)),
            int(round(cc["normal"][1] / 0.12)),
            int(round(cc["normal"][2] / 0.12)),
            int(round(cc["radius"] / (2.2 * p))),
        )
        if key not in seen_keys:
            seen_keys.add(key)
            dedup_circles.append(cc)

    # Pre-build spatial index on ridge midpoints for fast circle bounding-sphere lookup
    # Evaluate each deduplicated circle to find compatible unassigned ridges
    all_gap_queries: list[np.ndarray] = []
    gap_proposals: list[tuple[int, list[tuple[int, float, float]], list[tuple[float, float]]]] = []

    cos_circ_tang = float(np.cos(np.deg2rad(19.0)))
    consumed: set[int] = set()
    consolidated_out: list[ConsolidatedRidgeChain] = []
    merged_ridge_count = 0
    group_count = 0

    # Score candidate circles by number of inlier ridges (greedy largest-support first)
    circle_inliers: list[tuple[int, dict[str, Any], list[tuple[int, float, float]]]] = []
    for cc in dedup_circles:
        c_pos = cc["center"]
        n_u = cc["normal"]
        e1, e2 = cc["e1"], cc["e2"]
        rad = cc["radius"]

        near_ids = mid_tree.query_ball_point(c_pos, r=rad + 3.0 * p)
        if len(near_ids) < 2:
            continue

        inliers: list[tuple[int, float, float]] = []
        for r_idx in near_ids:
            pts_r = ridges[r_idx].points_3d
            rel = pts_r - c_pos[None, :]
            z_plane = rel @ n_u
            if float(np.max(np.abs(z_plane))) > 1.25 * p:
                continue
            x_2d = rel @ e1
            y_2d = rel @ e2
            radii_r = np.hypot(x_2d, y_2d)
            if float(np.max(np.abs(radii_r - rad))) > 1.25 * p:
                continue

            # Check circumferential tangent alignment at every node
            circ_tang = (-y_2d[:, None] * e1[None, :] + x_2d[:, None] * e2[None, :]) / np.maximum(radii_r[:, None], 1e-9)
            align = np.abs(np.sum(ridge_tangs[r_idx] * circ_tang, axis=1))
            if float(np.min(align)) < cos_circ_tang:
                continue

            angs = np.unwrap(np.arctan2(y_2d, x_2d))
            th_lo, th_hi = float(np.min(angs)), float(np.max(angs))
            # Normalize th_lo into [-pi, pi)
            shift = math.floor((th_lo + math.pi) / (2.0 * math.pi)) * (2.0 * math.pi)
            inliers.append((r_idx, th_lo - shift, th_hi - shift))

        if len(inliers) >= 2:
            circle_inliers.append((len(inliers), cc, inliers))

    circle_inliers.sort(key=lambda x: x[0], reverse=True)

    # Collect candidate angular sub-chains and batch-verify gap arcs on GPU
    pending_groups: list[dict[str, Any]] = []
    gap_sample_batches: list[np.ndarray] = []
    S_gap = 8

    for _, cc, inliers in circle_inliers:
        avail = [(rid, a0, a1) for (rid, a0, a1) in inliers if rid not in consumed]
        if len(avail) < 2:
            continue
        avail.sort(key=lambda t: t[1])
        rad = cc["radius"]
        max_dtheta = min(math.radians(42.0), (max_gap_px * p) / max(rad, 1e-5))

        # Partition sorted angular intervals into contiguous chains where angular gap <= max_dtheta
        cur_chain = [avail[0]]
        cur_hi = avail[0][2]
        chains_found: list[list[tuple[int, float, float]]] = []

        for item in avail[1:]:
            gap_th = item[1] - cur_hi
            if gap_th <= max_dtheta:
                cur_chain.append(item)
                cur_hi = max(cur_hi, item[2])
            else:
                if len(cur_chain) >= 2:
                    chains_found.append(cur_chain)
                cur_chain = [item]
                cur_hi = item[2]
        if len(cur_chain) >= 2:
            chains_found.append(cur_chain)

        for ch_items in chains_found:
            tot_sweep = max(it[2] for it in ch_items) - ch_items[0][1]
            if tot_sweep < math.radians(15.0) or tot_sweep > math.radians(340.0):
                continue
            # Sample gap arcs between non-overlapping intervals
            gaps_idx: list[int] = []
            running_hi = ch_items[0][2]
            for it in ch_items[1:]:
                if it[1] > running_hi + 1e-4:
                    th_s = np.linspace(running_hi, it[1], S_gap, dtype=np.float64)
                    g_pts = cc["center"][None, :] + rad * (
                        np.cos(th_s)[:, None] * cc["e1"][None, :] + np.sin(th_s)[:, None] * cc["e2"][None, :]
                    )
                    gaps_idx.append(len(gap_sample_batches))
                    gap_sample_batches.append(g_pts)
                running_hi = max(running_hi, it[2])

            pending_groups.append({"cc": cc, "items": ch_items, "gap_ids": gaps_idx})

    max_fsv_gap = max(1, int(0.12 * evaluator.num_depth_views))
    gap_pass = np.ones(len(gap_sample_batches), dtype=bool)
    if gap_sample_batches:
        all_g_pts = np.concatenate(gap_sample_batches, axis=0)
        g_eval = evaluator.query_points(all_g_pts, pixel_scale=p)
        for g_i in range(len(gap_sample_batches)):
            sl = slice(g_i * S_gap, (g_i + 1) * S_gap)
            # Gap along the circle must stay inside multi-view visual hull, not float in front of smooth surface,
            # and have reasonable multi-view edge/rib proximity (<= 2.5 px)
            if (
                float(g_eval["hull_viol_rate"][sl].max()) > 0.06
                or int(g_eval["free_space_viol"][sl].max()) > max_fsv_gap
                or float(g_eval["edge_cost_mean"][sl].mean()) > 2.5
            ):
                gap_pass[g_i] = False

    for grp in pending_groups:
        if not all(gap_pass[g_i] for g_i in grp["gap_ids"]):
            continue
        member_rids = [it[0] for it in grp["items"] if it[0] not in consumed]
        if len(member_rids) < 2:
            continue

        # Refit clean circular arc across all member points!
        all_m_pts = np.concatenate([ridges[rid].points_3d for rid in member_rids], axis=0)
        cc = grp["cc"]
        rel = all_m_pts - cc["center"][None, :]
        angs = np.arctan2(rel @ cc["e2"], rel @ cc["e1"])
        # Unwrap relative to grp['items'][0][1]
        ref_a = grp["items"][0][1]
        angs_adj = ref_a + ((angs - ref_a + math.pi) % (2.0 * math.pi) - math.pi)
        # Handle > 180 deg span smoothly
        order = np.argsort(angs_adj)
        ordered_pts = all_m_pts[order]
        ctrl_arc, max_err, arc_meta = fit_circular_arc_to_polyline(ordered_pts, pin_endpoints=False)
        if not arc_meta.get("valid") or max_err > 1.35 * p:
            continue

        # Resample smooth circular ridge points so Stage 3 fits an exact ARC_3D with role="COCIRCULAR_RING"
        arc_len = arc_meta["radius"] * arc_meta["sweep_rad"]
        n_s = max(6, int(math.ceil(arc_len / (0.65 * p))) + 1)
        from .schema import evaluate_circular_arc_3pt_numpy

        arc_pts, _, _ = evaluate_circular_arc_3pt_numpy(ctrl_arc, np.linspace(0.0, 1.0, n_s))
        views_u = sorted({v for rid in member_rids for v in ridges[rid].supporting_views})
        pids_u = sorted({pid for rid in member_rids for pid in ridges[rid].source_parent_ids})
        px_u = float(np.median([ridges[rid].pixel_scale for rid in member_rids]))
        conf_u = float(np.mean([ridges[rid].confidence for rid in member_rids]))

        for rid in member_rids:
            consumed.add(rid)
        merged_ridge_count += len(member_rids)
        group_count += 1

        consolidated_out.append(
            ConsolidatedRidgeChain(
                ridge_id=-group_count,  # temporary negative ID; reindexed below
                points_3d=arc_pts,
                pixel_scale=px_u,
                supporting_views=views_u,
                source_parent_ids=pids_u,
                is_silhouette_jump=False,
                confidence=conf_u + 100.0,  # marker > 100 signals verified COCIRCULAR_RING
            )
        )

    final_ridges: list[ConsolidatedRidgeChain] = []
    for r in ridges:
        if r.ridge_id not in consumed:
            r.ridge_id = len(final_ridges)
            final_ridges.append(r)
    for cr in consolidated_out:
        cr.ridge_id = len(final_ridges)
        final_ridges.append(cr)

    stats = {
        "candidate_circles_tested": len(dedup_circles),
        "verified_cocircular_groups": group_count,
        "absorbed_short_arc_ridges": merged_ridge_count,
        "output_ridges_after_cocircular": len(final_ridges),
    }
    return final_ridges, stats
