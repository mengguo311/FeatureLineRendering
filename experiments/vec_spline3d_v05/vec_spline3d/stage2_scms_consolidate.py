"""Stage 2: Ray-uncertainty-aware anisotropic SCMS lateral consolidation & echelon overlap curve merging."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from .stage1_ray_clean import CleanedChainSegment


@dataclass
class ConsolidatedRidgeChain:
    """Single 1D consolidated ridge polyline produced from 1..K overlapping single-view chains."""

    ridge_id: int
    points_3d: np.ndarray  # (M, 3) ordered smooth 3D ridge points
    pixel_scale: float
    supporting_views: list[str]
    source_parent_ids: list[int]
    is_silhouette_jump: bool
    confidence: float


def _order_and_resample_cluster_points(
    pts: np.ndarray,
    tangents: np.ndarray,
    weights: np.ndarray,
    spacing: float,
) -> np.ndarray:
    """Order a thin 1D tubular point cloud into a clean 1D curve sequence and smooth via local kernel."""
    n = len(pts)
    if n <= 2:
        return pts.copy()

    # Build kNN graph to trace geodesic 1D ordering (handles strongly curved arcs > 180 deg, unlike global PCA!)
    k_nn = min(n, 16)
    tree = cKDTree(pts)
    dists, idxs = tree.query(pts, k=k_nn)
    if k_nn == 1:
        return pts.copy()

    # Find diameter endpoints via 2-sweep Dijkstra/BFS on local Euclidean graph
    # Connect each point to its kNN neighbors; add MST-like fallback if disconnected
    adj: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    max_edge = max(spacing * 8.0, float(np.percentile(dists[:, min(2, k_nn - 1)], 98)) * 2.5)
    for i in range(n):
        for d_val, j_val in zip(dists[i, 1:], idxs[i, 1:]):
            j = int(j_val)
            w_d = float(d_val)
            if w_d <= max_edge:
                adj[i].append((j, w_d))
                adj[j].append((i, w_d))

    # Ensure single connected graph by linking components at closest pair if needed
    rows_g, cols_g = [], []
    for i in range(n):
        for j, _ in adj[i]:
            rows_g.append(i)
            cols_g.append(j)
    if rows_g:
        g_mat = csr_matrix((np.ones(len(rows_g)), (rows_g, cols_g)), shape=(n, n))
        n_comp, labels = connected_components(g_mat, directed=False)
    else:
        n_comp, labels = n, np.arange(n)

    if n_comp > 1:
        # Greedily connect components via nearest endpoints
        comp_pts = [np.where(labels == c)[0] for c in range(n_comp)]
        connected = {0}
        rem = set(range(1, n_comp))
        while rem:
            u_nodes = np.concatenate([comp_pts[c] for c in connected])
            u_tree = cKDTree(pts[u_nodes])
            best_d = 1e18
            best_pair = (0, 0, 0)
            for rc in rem:
                r_nodes = comp_pts[rc]
                d_q, idx_q = u_tree.query(pts[r_nodes], k=1)
                min_pos = int(np.argmin(d_q))
                if float(d_q[min_pos]) < best_d:
                    best_d = float(d_q[min_pos])
                    best_pair = (int(u_nodes[idx_q[min_pos]]), int(r_nodes[min_pos]), rc)
            a_i, b_i, chosen_c = best_pair
            adj[a_i].append((b_i, best_d))
            adj[b_i].append((a_i, best_d))
            connected.add(chosen_c)
            rem.remove(chosen_c)

    import heapq

    def dijkstra(src: int) -> np.ndarray:
        dist = np.full(n, np.inf, dtype=np.float64)
        dist[src] = 0.0
        pq = [(0.0, src)]
        while pq:
            d_u, u = heapq.heappop(pq)
            if d_u > dist[u]:
                continue
            for v, w_uv in adj[u]:
                nd = d_u + w_uv
                if nd < dist[v]:
                    dist[v] = nd
                    heapq.heappush(pq, (nd, v))
        return dist

    d0 = dijkstra(0)
    end_a = int(np.argmax(np.where(np.isfinite(d0), d0, -1.0)))
    d_from_a = dijkstra(end_a)
    end_b = int(np.argmax(np.where(np.isfinite(d_from_a), d_from_a, -1.0)))
    d_from_b = dijkstra(end_b)

    total_span = float(d_from_a[end_b])
    if not np.isfinite(total_span) or total_span < spacing * 0.8:
        return np.vstack([pts[end_a], pts[end_b]])

    # Smooth 1D coordinate s in [0, total_span] combining geodesic distance from A and (span - distance from B)
    s_coord = 0.5 * (d_from_a + (total_span - d_from_b))
    s_coord = np.clip(s_coord, 0.0, total_span)

    num_bins = max(3, int(np.ceil(total_span / spacing)) + 1)
    s_samples = np.linspace(0.0, total_span, num_bins, dtype=np.float64)
    bandwidth = max(spacing * 0.85, 1e-5)

    diff_s = (s_samples[:, None] - s_coord[None, :]) / bandwidth
    kern = np.exp(-0.5 * (diff_s ** 2)) * weights[None, :]
    k_sum = kern.sum(axis=1, keepdims=True)
    # Fallback to nearest point if a bin has negligible weight
    valid_bin = k_sum[:, 0] > 1e-10
    ridge_pts = np.zeros((num_bins, 3), dtype=np.float64)
    if np.any(valid_bin):
        ridge_pts[valid_bin] = (kern[valid_bin] @ pts) / k_sum[valid_bin]
    if not np.all(valid_bin):
        nearest = np.argmin(np.abs(s_samples[~valid_bin, None] - s_coord[None, :]), axis=1)
        ridge_pts[~valid_bin] = pts[nearest]

    # Deduplicate any nearly identical consecutive points
    keep = [0]
    for i in range(1, len(ridge_pts)):
        if float(np.linalg.norm(ridge_pts[i] - ridge_pts[keep[-1]])) >= spacing * 0.25 or i == len(ridge_pts) - 1:
            keep.append(i)
    if len(keep) < 2:
        return np.vstack([ridge_pts[0], ridge_pts[-1]])
    return ridge_pts[keep]


def run_stage2_scms_consolidate(
    segments: list[CleanedChainSegment],
    median_pixel_scale: float,
    num_scms_iters: int = 5,
) -> tuple[list[ConsolidatedRidgeChain], dict[str, Any]]:
    """Collapse multi-view parallel double-rims via Ray-Anisotropic SCMS and merge overlapping chains."""
    if not segments:
        return [], {"input_segments": 0, "output_ridges": 0}

    p = median_pixel_scale
    offsets: list[tuple[int, int]] = []
    pts_list: list[np.ndarray] = []
    tang_list: list[np.ndarray] = []
    ray_list: list[np.ndarray] = []
    seg_id_list: list[np.ndarray] = []
    wt_list: list[np.ndarray] = []

    cur = 0
    for idx, seg in enumerate(segments):
        m = len(seg.points_3d)
        offsets.append((cur, cur + m))
        pts_list.append(seg.points_3d)
        tang_list.append(seg.tangents_3d)
        ray_list.append(seg.ray_dirs)
        seg_id_list.append(np.full(m, idx, dtype=np.int32))
        # Higher weight for un-repaired trusted multi-view nodes
        w_node = np.clip(seg.mv_support_views.astype(np.float64), 1.0, 10.0) * np.where(seg.was_repaired, 0.75, 1.25)
        wt_list.append(w_node)
        cur += m

    X_orig = np.concatenate(pts_list, axis=0)
    X = X_orig.copy()
    T = np.concatenate(tang_list, axis=0)
    D_ray = np.concatenate(ray_list, axis=0)
    seg_of_pt = np.concatenate(seg_id_list, axis=0)
    W_pt = np.concatenate(wt_list, axis=0)

    # Step 2A: Ray-Uncertainty-Aware Normal-Plane SCMS Contraction
    search_r = 3.4 * p
    sigma_perp = 1.05 * p
    sigma_ray = 3.0 * p
    cos_tang_min = float(np.cos(np.deg2rad(30.0)))

    for _it in range(num_scms_iters):
        tree = cKDTree(X)
        # Query up to 32 neighbors within search_r for vectorized speed
        dists, nbrs = tree.query(X, k=32, distance_upper_bound=search_r)
        valid = np.isfinite(dists) & (nbrs < len(X))
        safe_nbrs = np.where(valid, nbrs, 0)

        X_j = X[safe_nbrs]          # (N, K, 3)
        T_j = T[safe_nbrs]          # (N, K, 3)
        D_j = D_ray[safe_nbrs]      # (N, K, 3)
        W_j = W_pt[safe_nbrs]       # (N, K)

        delta = X[:, None, :] - X_j  # (N, K, 3)
        # Decompose delta along neighbor j's viewing ray D_j vs image-plane perpendicular
        d_along_ray = np.sum(delta * D_j, axis=-1)  # (N, K)
        delta_perp_sq = np.maximum(np.sum(delta * delta, axis=-1) - d_along_ray ** 2, 0.0)
        mah_sq = (delta_perp_sq / (sigma_perp ** 2)) + ((d_along_ray ** 2) / (sigma_ray ** 2))

        t_align = np.abs(np.sum(T[:, None, :] * T_j, axis=-1))
        ang_ok = valid & (t_align >= cos_tang_min)

        omega = np.where(ang_ok, W_j * (t_align ** 4) * np.exp(-0.5 * mah_sq), 0.0)
        omega_sum = omega.sum(axis=1, keepdims=True)
        has_nbr = omega_sum[:, 0] > 1e-9

        X_bar = np.where(has_nbr[:, None], np.sum(omega[:, :, None] * X_j, axis=1) / np.maximum(omega_sum, 1e-9), X)

        # Update local tangent aligning signs with T[i]
        sign_flip = np.where(np.sum(T[:, None, :] * T_j, axis=-1) >= 0.0, 1.0, -1.0)
        T_bar = np.sum((omega * sign_flip)[:, :, None] * T_j, axis=1)
        t_nrm = np.linalg.norm(T_bar, axis=1, keepdims=True)
        T_new = np.where(t_nrm > 1e-9, T_bar / np.maximum(t_nrm, 1e-9), T)

        # Project shift strictly onto the 2D normal plane perpendicular to T_new
        raw_shift = X_bar - X
        normal_shift = raw_shift - np.sum(raw_shift * T_new, axis=1, keepdims=True) * T_new

        # Bound maximum drift from original camera ray in image-plane coordinates (<= 1.2p)
        X_cand = X + 0.75 * normal_shift
        tot_disp = X_cand - X_orig
        disp_along_own_ray = np.sum(tot_disp * D_ray, axis=1, keepdims=True) * D_ray
        disp_perp_own_ray = tot_disp - disp_along_own_ray
        perp_norm = np.linalg.norm(disp_perp_own_ray, axis=1, keepdims=True)
        max_perp = 1.25 * p
        disp_perp_clamped = np.where(
            perp_norm > max_perp, disp_perp_own_ray * (max_perp / np.maximum(perp_norm, 1e-9)), disp_perp_own_ray
        )
        # Bound along-ray adjustment to <= 4.0p
        ray_mag = np.sum(tot_disp * D_ray, axis=1, keepdims=True)
        ray_clamped = np.clip(ray_mag, -4.0 * p, 4.0 * p) * D_ray
        X = X_orig + disp_perp_clamped + ray_clamped
        T = T_new

    # Step 2B: Side-by-Side & Echelon Overlap Chain Clustering (with Y-branch divergence guard!)
    n_segs = len(segments)
    seg_pts = [X[lo:hi] for lo, hi in offsets]
    seg_tangs = [T[lo:hi] for lo, hi in offsets]
    seg_lens = np.array([len(s) for s in seg_pts], dtype=np.int32)

    tree_final = cKDTree(X)
    merge_r = 1.15 * p
    cos_merge = float(np.cos(np.deg2rad(24.0)))
    dists_m, nbrs_m = tree_final.query(X, k=20, distance_upper_bound=merge_r)

    # Count directed node-to-segment matches
    pair_hits: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for g_i in range(len(X)):
        s_a = int(seg_of_pt[g_i])
        li_a = g_i - offsets[s_a][0]
        for d_val, g_j in zip(dists_m[g_i], nbrs_m[g_i]):
            if not np.isfinite(d_val) or g_j >= len(X):
                continue
            s_b = int(seg_of_pt[g_j])
            if s_a == s_b:
                continue
            if abs(float(np.dot(T[g_i], T[g_j]))) < cos_merge:
                continue
            key = (min(s_a, s_b), max(s_a, s_b))
            li_b = int(g_j) - offsets[s_b][0]
            pair_hits.setdefault(key, []).append((li_a, li_b) if s_a < s_b else (li_b, li_a))

    parent_uf = np.arange(n_segs, dtype=np.int32)

    def find_uf(x: int) -> int:
        while parent_uf[x] != x:
            parent_uf[x] = parent_uf[parent_uf[x]]
            x = int(parent_uf[x])
        return x

    def union_uf(a: int, b: int) -> None:
        ra, rb = find_uf(a), find_uf(b)
        if ra != rb:
            parent_uf[rb] = ra

    merged_pair_count = 0
    for (s_a, s_b), hits in pair_hits.items():
        pts_a, pts_b = seg_pts[s_a], seg_pts[s_b]
        len_a, len_b = len(pts_a), len(pts_b)
        min_len = min(len_a, len_b)

        uniq_a = sorted({h[0] for h in hits})
        uniq_b = sorted({h[1] for h in hits})
        cov_a = len(uniq_a) / max(1, len_a)
        cov_b = len(uniq_b) / max(1, len_b)

        # Require substantial overlap (>=40% of shorter segment, or >=4 nodes echelon tail overlap)
        is_contained = max(cov_a, cov_b) >= 0.42 and min(len(uniq_a), len(uniq_b)) >= 3
        is_echelon = (
            min(len(uniq_a), len(uniq_b)) >= 4
            and (uniq_a[0] <= 1 or uniq_a[-1] >= len_a - 2)
            and (uniq_b[0] <= 1 or uniq_b[-1] >= len_b - 2)
        )
        if not (is_contained or is_echelon):
            continue

        # Y-branch divergence guard: check if BOTH segments extend well past the overlap zone on the SAME side
        # while diverging > 2.2p!
        # Align orientation of B relative to A along matched indices
        corr = np.corrcoef([h[0] for h in hits], [h[1] for h in hits])[0, 1] if len(hits) >= 3 else 1.0
        b_oriented = pts_b if (not np.isfinite(corr) or corr >= 0) else pts_b[::-1]

        # Check endpoint-to-curve distance on non-overlapping tails
        tree_a = cKDTree(pts_a)
        tree_b = cKDTree(b_oriented)
        d_b_to_a, _ = tree_a.query(b_oriented, k=1)
        d_a_to_b, _ = tree_b.query(pts_a, k=1)

        # If both curves have >3 nodes far (> 2.3p) from the other curve on the same end, it's a Y-fork — don't merge!
        a_far_start = int(np.sum(d_a_to_b[: min(6, len_a)] > 2.3 * p))
        b_far_start = int(np.sum(d_b_to_a[: min(6, len_b)] > 2.3 * p))
        a_far_end = int(np.sum(d_a_to_b[max(0, len_a - 6) :] > 2.3 * p))
        b_far_end = int(np.sum(d_b_to_a[max(0, len_b - 6) :] > 2.3 * p))
        if (a_far_start >= 3 and b_far_start >= 3) or (a_far_end >= 3 and b_far_end >= 3):
            continue

        union_uf(s_a, s_b)
        merged_pair_count += 1

    clusters: dict[int, list[int]] = {}
    for s_idx in range(n_segs):
        root = find_uf(s_idx)
        clusters.setdefault(root, []).append(s_idx)

    ridges: list[ConsolidatedRidgeChain] = []
    next_rid = 0
    spacing = 0.65 * p

    for _, member_ids in sorted(clusters.items()):
        if len(member_ids) == 1:
            seg = segments[member_ids[0]]
            lo, hi = offsets[member_ids[0]]
            r_pts = X[lo:hi].copy()
            views = [seg.source_view]
            pids = [seg.parent_id]
            is_sil = seg.is_silhouette_jump
            conf = float(np.mean(seg.mv_support_views))
            px_scale = float(np.median(seg.node_pixel))
        else:
            c_pts = np.concatenate([X[offsets[m][0] : offsets[m][1]] for m in member_ids], axis=0)
            c_tng = np.concatenate([T[offsets[m][0] : offsets[m][1]] for m in member_ids], axis=0)
            c_wts = np.concatenate([W_pt[offsets[m][0] : offsets[m][1]] for m in member_ids], axis=0)
            px_scale = float(np.median(np.concatenate([segments[m].node_pixel for m in member_ids])))
            r_pts = _order_and_resample_cluster_points(c_pts, c_tng, c_wts, spacing=max(0.65 * px_scale, 1e-4))
            views = sorted({segments[m].source_view for m in member_ids})
            pids = sorted({segments[m].parent_id for m in member_ids})
            is_sil = sum(1 for m in member_ids if segments[m].is_silhouette_jump) >= (len(member_ids) / 2.0)
            conf = float(np.mean(np.concatenate([segments[m].mv_support_views for m in member_ids])))

        if len(r_pts) < 2:
            continue
        arc_len = float(np.linalg.norm(np.diff(r_pts, axis=0), axis=1).sum())
        if arc_len < 1.5 * px_scale:
            continue

        # Corner-preserving split: partition sharp L/Z corners (> 50 deg localized turn) so straight architectural
        # / man-made creases become crisp LINE_3D segments meeting at exact CORNER nodes rather than rounded arcs.
        sub_polylines = [r_pts]
        if len(r_pts) >= 5:
            step_med = float(np.median(np.linalg.norm(np.diff(r_pts, axis=0), axis=1)))
            k_arm = max(2, min((len(r_pts) - 1) // 2, int(round(2.4 * px_scale / max(step_med, 1e-6)))))
            cos_thr = float(np.cos(np.deg2rad(50.0)))
            turn_cos = np.ones(len(r_pts), dtype=np.float64)
            for vi in range(k_arm, len(r_pts) - k_arm):
                v_in = r_pts[vi] - r_pts[vi - k_arm]
                v_out = r_pts[vi + k_arm] - r_pts[vi]
                l_in = float(np.linalg.norm(v_in))
                l_out = float(np.linalg.norm(v_out))
                if l_in >= 1.6 * px_scale and l_out >= 1.6 * px_scale:
                    turn_cos[vi] = float(np.dot(v_in, v_out) / (l_in * l_out))
            split_idxs: list[int] = []
            vi = k_arm
            while vi < len(r_pts) - k_arm:
                if turn_cos[vi] < cos_thr:
                    win_hi = min(len(r_pts) - k_arm, vi + k_arm + 1)
                    apex = vi + int(np.argmin(turn_cos[vi:win_hi]))
                    if not split_idxs or apex - split_idxs[-1] >= k_arm:
                        split_idxs.append(apex)
                    vi = apex + k_arm
                else:
                    vi += 1
            if split_idxs:
                sub_polylines = []
                prev_i = 0
                for sp_i in split_idxs + [len(r_pts) - 1]:
                    sub_p = r_pts[prev_i : sp_i + 1]
                    if len(sub_p) >= 2 and float(np.linalg.norm(np.diff(sub_p, axis=0), axis=1).sum()) >= 1.3 * px_scale:
                        sub_polylines.append(sub_p)
                    prev_i = sp_i
                if not sub_polylines:
                    sub_polylines = [r_pts]

        for sub_p in sub_polylines:
            ridges.append(
                ConsolidatedRidgeChain(
                    ridge_id=next_rid,
                    points_3d=sub_p,
                    pixel_scale=px_scale,
                    supporting_views=views,
                    source_parent_ids=pids,
                    is_silhouette_jump=is_sil,
                    confidence=conf,
                )
            )
            next_rid += 1

    mv_ridges = sum(1 for r in ridges if len(r.supporting_views) >= 2)
    stats = {
        "input_clean_segments": n_segs,
        "scms_iterations": num_scms_iters,
        "mean_scms_displacement_px": float(np.linalg.norm(X - X_orig, axis=1).mean() / max(p, 1e-6)),
        "merged_segment_pairs": merged_pair_count,
        "output_consolidated_ridges": len(ridges),
        "multiview_merged_ridges": mv_ridges,
        "multiview_merged_ratio": float(mv_ridges / max(1, len(ridges))),
    }
    return ridges, stats
