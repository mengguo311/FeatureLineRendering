"""Stage 1: Multi-view visual-hull space carving & ray-constrained depth re-triangulation for state=2 spikes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F

from .multimodal_data import MultiModalSceneBundle, MultiModalView, ParentFragmentChain


@dataclass
class CleanedChainSegment:
    """Cleaned, spike-free 3D polyline sub-chain ready for lateral consolidation."""

    chain_id: int
    parent_id: int
    source_view: str
    cam_center: np.ndarray  # (3,)
    points_3d: np.ndarray  # (L, 3)
    tangents_3d: np.ndarray  # (L, 3)
    ray_dirs: np.ndarray  # (L, 3) unit ray directions from source camera
    node_pixel: np.ndarray  # (L,)
    mv_support_views: np.ndarray  # (L,) int count of corroborating views
    was_repaired: np.ndarray  # (L,) bool
    is_silhouette_jump: bool


class GPUViewFieldEvaluator:
    """Vectorized GPU evaluator for 40-view visual hull, 3DGS depth buffer, and 2D edge DT fields."""

    def __init__(self, views: list[MultiModalView], device: torch.device) -> None:
        self.views = views
        self.device = device
        self.num_views = len(views)
        h, w = views[0].height, views[0].width
        self.h = h
        self.w = w

        self.R = torch.tensor(np.stack([v.w2c[:3, :3] for v in views]), dtype=torch.float32, device=device)  # (V,3,3)
        self.t = torch.tensor(np.stack([v.w2c[:3, 3] for v in views]), dtype=torch.float32, device=device)   # (V,3)
        self.fx = torch.tensor([v.fx for v in views], dtype=torch.float32, device=device)  # (V,)
        self.fy = torch.tensor([v.fy for v in views], dtype=torch.float32, device=device)  # (V,)
        self.cx = torch.tensor([v.cx for v in views], dtype=torch.float32, device=device)  # (V,)
        self.cy = torch.tensor([v.cy for v in views], dtype=torch.float32, device=device)  # (V,)

        # Pack (V, C, H, W): C = [alpha, outside_hull_dt, edge_dt, edge_strength, depth, has_depth, depth_jump]
        has_depth = np.array([1.0 if v.depth is not None else 0.0 for v in views], dtype=np.float32)
        self.has_depth = torch.tensor(has_depth > 0.5, dtype=torch.bool, device=device)  # (V,)
        self.num_depth_views = int(self.has_depth.sum().item())

        ch_list = []
        for v in views:
            d_arr = v.depth if v.depth is not None else np.zeros((h, w), dtype=np.float32)
            j_arr = v.depth_jump if v.depth_jump is not None else np.zeros((h, w), dtype=np.float32)
            ch = np.stack(
                [v.alpha, v.outside_hull_dt, v.edge_dt, v.edge_strength, d_arr, j_arr],
                axis=0,
            )
            ch_list.append(ch)
        # (V, 6, H, W)
        self.maps = torch.tensor(np.stack(ch_list, axis=0), dtype=torch.float32, device=device)
        # Separate 2D edge tangent maps (V, 2, H, W)
        self.tang2d = torch.tensor(
            np.stack([v.edge_tangent_2d.transpose(2, 0, 1) for v in views], axis=0),
            dtype=torch.float32,
            device=device,
        )

    @torch.no_grad()
    def query_points(
        self, pts_world: np.ndarray | torch.Tensor, pixel_scale: float, chunk_size: int = 24000
    ) -> dict[str, np.ndarray]:
        """Evaluate multi-view visual hull violation, free-space violation, and unoccluded edge support."""
        pts_t = torch.as_tensor(pts_world, dtype=torch.float32, device=self.device)
        n = len(pts_t)
        hull_viol_rate = np.zeros(n, dtype=np.float32)
        outside_dt_mean = np.zeros(n, dtype=np.float32)
        free_space_viol = np.zeros(n, dtype=np.int32)
        edge_support_cnt = np.zeros(n, dtype=np.int32)
        edge_cost_mean = np.zeros(n, dtype=np.float32)
        depth_jump_mean = np.zeros(n, dtype=np.float32)

        for s in range(0, n, chunk_size):
            e = min(n, s + chunk_size)
            X = pts_t[s:e]  # (B, 3)
            # (V, B, 3)
            Xc = torch.einsum("vij,bj->vbi", self.R, X) + self.t[:, None, :]
            z = Xc[:, :, 2].clamp(min=1e-3)
            u = self.fx[:, None] * (Xc[:, :, 0] / z) + self.cx[:, None]
            v = self.fy[:, None] * (Xc[:, :, 1] / z) + self.cy[:, None]
            in_frustum = (Xc[:, :, 2] > 0.2) & (u >= 0.0) & (u <= self.w - 1.0) & (v >= 0.0) & (v <= self.h - 1.0)

            gx = 2.0 * (u / (self.w - 1.0)) - 1.0
            gy = 2.0 * (v / (self.h - 1.0)) - 1.0
            grid = torch.stack([gx, gy], dim=-1).unsqueeze(2)  # (V, B, 1, 2)
            sampled = F.grid_sample(
                self.maps[:, :4, :, :], grid, mode="bilinear", padding_mode="border", align_corners=True
            ).squeeze(-1)  # (V, 4, B)
            sampled_d = F.grid_sample(
                self.maps[:, 4:6, :, :], grid, mode="nearest", padding_mode="border", align_corners=True
            ).squeeze(-1)  # (V, 2, B)

            alpha = sampled[:, 0, :]       # (V, B)
            out_dt = sampled[:, 1, :]      # (V, B)
            edt = sampled[:, 2, :]         # (V, B)
            surf_d = sampled_d[:, 0, :]    # (V, B)
            d_jump = sampled_d[:, 1, :]    # (V, B)

            # Visual hull check: ONLY count views whose frustum actually observes the point and sees empty sky (alpha < 0.03)!
            # (Immune to narrow-FOV close-up MVS frustum cropping on real-world DTU scenes!)
            in_f_f = in_frustum.float()
            in_f_cnt = in_f_f.sum(dim=0)
            sky_viol = (in_frustum & (alpha < 0.03)).float().sum(dim=0) / in_f_cnt.clamp(min=1.0)
            hull_viol = torch.where(in_f_cnt >= 2.0, sky_viol, torch.ones_like(sky_viol))
            hull_viol_rate[s:e] = hull_viol.cpu().numpy()
            outside_dt_mean[s:e] = ((out_dt * in_f_f).sum(dim=0) / in_f_cnt.clamp(min=1.0)).cpu().numpy()

            # Foreground free-space check ONLY on smooth single-layer opaque surfaces (avoids median_z background bias at leaf rims!)
            tol = 6.0 * pixel_scale
            smooth_opaque = self.has_depth[:, None] & in_frustum & (alpha > 0.95) & (surf_d > 0.2) & (d_jump < 0.004)
            fsv = smooth_opaque & (z < surf_d - tol)
            free_space_viol[s:e] = fsv.sum(dim=0).cpu().numpy()

            # Visibility / unoccluded mask: only mark occluded behind smooth opaque foreground surface
            occluded_on_depth = smooth_opaque & (z > surf_d + 5.0 * pixel_scale)
            vis = in_frustum & (~occluded_on_depth)
            sup = vis & (edt <= 2.4)
            edge_support_cnt[s:e] = sup.sum(dim=0).cpu().numpy()

            trunc_edt = torch.clamp(edt, max=8.0)
            vis_f = vis.float()
            denom = vis_f.sum(dim=0).clamp(min=1.0)
            edge_cost_mean[s:e] = ((trunc_edt * vis_f).sum(dim=0) / denom).cpu().numpy()

            d_vis = (self.has_depth[:, None] & vis).float()
            d_denom = d_vis.sum(dim=0).clamp(min=1.0)
            depth_jump_mean[s:e] = ((d_jump * d_vis).sum(dim=0) / d_denom).cpu().numpy()

        return {
            "hull_viol_rate": hull_viol_rate,
            "outside_dt_mean": outside_dt_mean,
            "free_space_viol": free_space_viol,
            "edge_support_cnt": edge_support_cnt,
            "edge_cost_mean": edge_cost_mean,
            "depth_jump_mean": depth_jump_mean,
        }

    @torch.no_grad()
    def score_ray_candidates(
        self,
        cam_centers: np.ndarray,  # (M, 3)
        rays: np.ndarray,         # (M, 3)
        z_grid: np.ndarray,       # (M, K)
        pixel_scale: float,
        node_chunk: int = 2048,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return (total_cost (M,K), hull_viol_rate (M,K)) for M rays x K depth hypotheses."""
        m, k = z_grid.shape
        total_cost = np.zeros((m, k), dtype=np.float32)
        hull_viol_out = np.zeros((m, k), dtype=np.float32)

        for s in range(0, m, node_chunk):
            e = min(m, s + node_chunk)
            o_t = torch.as_tensor(cam_centers[s:e], dtype=torch.float32, device=self.device)[:, None, :]  # (B,1,3)
            r_t = torch.as_tensor(rays[s:e], dtype=torch.float32, device=self.device)[:, None, :]         # (B,1,3)
            zg_t = torch.as_tensor(z_grid[s:e], dtype=torch.float32, device=self.device)[:, :, None]      # (B,K,1)
            pts = (o_t + zg_t * r_t).reshape(-1, 3)  # (B*K, 3)

            Xc = torch.einsum("vij,nj->vni", self.R, pts) + self.t[:, None, :]
            z = Xc[:, :, 2].clamp(min=1e-3)
            u = self.fx[:, None] * (Xc[:, :, 0] / z) + self.cx[:, None]
            v = self.fy[:, None] * (Xc[:, :, 1] / z) + self.cy[:, None]
            in_frustum = (Xc[:, :, 2] > 0.2) & (u >= 0.0) & (u <= self.w - 1.0) & (v >= 0.0) & (v <= self.h - 1.0)

            gx = 2.0 * (u / (self.w - 1.0)) - 1.0
            gy = 2.0 * (v / (self.h - 1.0)) - 1.0
            grid = torch.stack([gx, gy], dim=-1).unsqueeze(2)
            sampled = F.grid_sample(
                self.maps[:, :4, :, :], grid, mode="bilinear", padding_mode="border", align_corners=True
            ).squeeze(-1)
            sampled_d = F.grid_sample(
                self.maps[:, 4:6, :, :], grid, mode="nearest", padding_mode="border", align_corners=True
            ).squeeze(-1)

            alpha = sampled[:, 0, :]
            out_dt = sampled[:, 1, :]
            edt = sampled[:, 2, :]
            surf_d = sampled_d[:, 0, :]
            d_jump = sampled_d[:, 1, :]

            in_f_f = in_frustum.float()
            in_f_cnt = in_f_f.sum(dim=0)
            sky_viol = (in_frustum & (alpha < 0.03)).float().sum(dim=0) / in_f_cnt.clamp(min=1.0)
            h_viol = torch.where(in_f_cnt >= 2.0, sky_viol, torch.ones_like(sky_viol))
            out_pen = (out_dt * in_f_f).sum(dim=0) / in_f_cnt.clamp(min=1.0)

            smooth_opaque = self.has_depth[:, None] & in_frustum & (alpha > 0.95) & (surf_d > 0.2) & (d_jump < 0.004)
            fsv = smooth_opaque & (z < surf_d - 6.0 * pixel_scale)
            fsv_pen = fsv.float().sum(dim=0) * 6.0

            occluded = smooth_opaque & (z > surf_d + 5.0 * pixel_scale)
            vis = in_frustum & (~occluded)
            vis_f = vis.float()
            trunc_edt = torch.clamp(edt, max=7.0)
            edge_c = (trunc_edt * vis_f).sum(dim=0) / vis_f.sum(dim=0).clamp(min=1.0)
            sup_bonus = 0.22 * (vis & (edt <= 1.8)).float().sum(dim=0)

            cost = edge_c + 35.0 * torch.clamp(h_viol - 0.04, min=0.0) + 1.5 * out_pen + fsv_pen - sup_bonus
            total_cost[s:e] = cost.reshape(e - s, k).cpu().numpy()
            hull_viol_out[s:e] = h_viol.reshape(e - s, k).cpu().numpy()

        return total_cost, hull_viol_out


def _compute_polyline_tangents(pts: np.ndarray) -> np.ndarray:
    n = len(pts)
    tang = np.zeros_like(pts)
    if n == 1:
        tang[0] = np.array([1.0, 0.0, 0.0])
        return tang
    tang[0] = pts[1] - pts[0]
    tang[-1] = pts[-1] - pts[-2]
    if n > 2:
        tang[1:-1] = pts[2:] - pts[:-2]
    nrm = np.linalg.norm(tang, axis=1, keepdims=True)
    return np.where(nrm > 1e-12, tang / np.maximum(nrm, 1e-12), np.array([1.0, 0.0, 0.0]))


def _ray_aabb_interval(
    cam_o: np.ndarray, rays: np.ndarray, bbox_min: np.ndarray, bbox_max: np.ndarray, z_fallback: float = 3.0
) -> tuple[np.ndarray, np.ndarray]:
    """Scale-invariant intersection of cam_o (M,3) + z * rays (M,3) with 3D AABB [bbox_min, bbox_max]."""
    inv_d = np.where(np.abs(rays) > 1e-9, 1.0 / np.where(np.abs(rays) > 1e-9, rays, 1.0), 1e9)
    t0 = (bbox_min[None, :] - cam_o) * inv_d
    t1 = (bbox_max[None, :] - cam_o) * inv_d
    tmin = np.max(np.minimum(t0, t1), axis=1)
    tmax = np.min(np.maximum(t0, t1), axis=1)
    z_cap = max(z_fallback * 2.5, 10.0)
    valid = (tmax > tmin) & (tmax > 0.15)
    z_lo = np.where(valid, np.maximum(tmin, 0.15), max(0.2, 0.5 * z_fallback))
    z_hi = np.where(valid, np.minimum(tmax, z_cap), 1.6 * z_fallback)
    bad = z_hi <= z_lo + 1e-3
    z_lo[bad] = max(0.2, 0.5 * z_fallback)
    z_hi[bad] = 1.6 * z_fallback
    return z_lo, z_hi


def run_stage1_ray_clean(
    bundle: MultiModalSceneBundle,
    device: torch.device,
    roi_bounds: tuple[np.ndarray, np.ndarray] | None = None,
    num_ray_samples: int = 96,
) -> tuple[list[CleanedChainSegment], dict[str, Any]]:
    """Repair state=2 ray-extrapolated depths using 40-view visual hull + edge DT, and prune sky spikes."""
    evaluator = GPUViewFieldEvaluator(bundle.train_views, device=device)
    p_med = bundle.median_pixel_scale

    # Stack all nodes across all parents
    parents = bundle.parents
    offsets: list[tuple[int, int]] = []
    all_pts_list: list[np.ndarray] = []
    all_state_list: list[np.ndarray] = []
    cur = 0
    for ch in parents:
        m = len(ch.points_3d)
        offsets.append((cur, cur + m))
        all_pts_list.append(ch.points_3d)
        all_state_list.append(ch.state)
        cur += m

    all_pts = np.concatenate(all_pts_list, axis=0)
    all_state = np.concatenate(all_state_list, axis=0)

    max_fsv_allowed = max(1, int(0.12 * evaluator.num_depth_views))
    init_eval = evaluator.query_points(all_pts, pixel_scale=p_med)
    init_hull_bad = init_eval["hull_viol_rate"] > 0.055
    init_fsv_bad = init_eval["free_space_viol"] > max_fsv_allowed

    # Trusted 3D bounding box of the object from clean state==1 nodes
    trusted_mask = (all_state == 1) & (~init_hull_bad) & (~init_fsv_bad)
    if np.any(trusted_mask):
        t_pts = all_pts[trusted_mask]
        bbox_min = np.percentile(t_pts, 0.2, axis=0) - 0.08
        bbox_max = np.percentile(t_pts, 99.8, axis=0) + 0.08
    else:
        bbox_min = np.array([-1.2, -1.2, -1.2])
        bbox_max = np.array([1.2, 1.2, 1.2])

    # Identify nodes whose depth needs multi-view ray re-triangulation:
    # Any node violating visual hull / smooth foreground free space, OR state==2 with weak multi-view edge support (<3 views)
    needs_repair = (
        init_hull_bad
        | init_fsv_bad
        | ((all_state == 2) & (init_eval["edge_support_cnt"] < 3))
    )

    # Also flag nodes adjacent to large depth jumps along a chain
    for pid, ch in enumerate(parents):
        lo, hi = offsets[pid]
        if hi - lo >= 2:
            dz = np.abs(np.diff(ch.fitted_z))
            jump = dz > 5.0 * ch.node_pixel[:-1]
            if np.any(jump):
                idx = np.where(jump)[0]
                needs_repair[lo + idx] = True
                needs_repair[lo + idx + 1] = True

    repaired_pts = all_pts.copy()
    was_repaired = np.zeros(len(all_pts), dtype=bool)

    flagged_indices = np.where(needs_repair)[0]
    if len(flagged_indices) > 0:
        # Build per-node camera center, ray, and candidate z grid
        node_cam_o = np.zeros((len(flagged_indices), 3), dtype=np.float64)
        node_rays = np.zeros((len(flagged_indices), 3), dtype=np.float64)
        node_z_orig = np.zeros(len(flagged_indices), dtype=np.float64)
        node_z_raw = np.zeros(len(flagged_indices), dtype=np.float64)
        node_z_sec = np.zeros(len(flagged_indices), dtype=np.float64)

        # Map global node index -> (parent_id, local_idx)
        parent_of_node = np.empty(len(all_pts), dtype=np.int32)
        local_of_node = np.empty(len(all_pts), dtype=np.int32)
        for pid, (lo, hi) in enumerate(offsets):
            parent_of_node[lo:hi] = pid
            local_of_node[lo:hi] = np.arange(hi - lo, dtype=np.int32)

        for k_idx, g_idx in enumerate(flagged_indices):
            ch = parents[parent_of_node[g_idx]]
            li = local_of_node[g_idx]
            node_cam_o[k_idx] = ch.cam_center
            node_rays[k_idx] = ch.rays[li]
            node_z_orig[k_idx] = ch.fitted_z[li]
            node_z_raw[k_idx] = ch.raw_z[li]
            node_z_sec[k_idx] = ch.second_z[li]

        z_med_fb = float(np.median(node_z_orig)) if len(node_z_orig) > 0 else 3.0
        z_lo, z_hi = _ray_aabb_interval(node_cam_o, node_rays, bbox_min, bbox_max, z_fallback=z_med_fb)
        u_lin = np.linspace(0.0, 1.0, num_ray_samples, dtype=np.float64)[None, :]
        z_uniform = z_lo[:, None] + (z_hi - z_lo)[:, None] * u_lin
        extra_z = np.stack(
            [
                np.clip(node_z_orig, z_lo, z_hi),
                np.where(np.isfinite(node_z_raw), np.clip(node_z_raw, z_lo, z_hi), 0.5 * (z_lo + z_hi)),
                np.where(np.isfinite(node_z_sec), np.clip(node_z_sec, z_lo, z_hi), 0.5 * (z_lo + z_hi)),
            ],
            axis=1,
        )
        z_grid = np.concatenate([z_uniform, extra_z], axis=1)  # (M, K+3)
        z_grid.sort(axis=1)

        unary_cost, cand_hull_viol = evaluator.score_ray_candidates(
            node_cam_o, node_rays, z_grid, pixel_scale=p_med
        )
        # Gentle preference to stay near original z ONLY when original z is inside visual hull
        orig_dist_p = np.abs(z_grid - node_z_orig[:, None]) / max(p_med, 1e-4)
        unary_cost += 0.03 * np.minimum(orig_dist_p, 20.0).astype(np.float32)

        # Map flagged global index -> position in flagged_indices
        flag_pos = np.full(len(all_pts), -1, dtype=np.int32)
        flag_pos[flagged_indices] = np.arange(len(flagged_indices), dtype=np.int32)

        # Chain-level Viterbi DP with truncated L1 transition (preserves real occlusion steps, smooths spikes)
        k_tot = z_grid.shape[1]
        for pid, ch in enumerate(parents):
            lo, hi = offsets[pid]
            f_slice = flag_pos[lo:hi]
            if not np.any(f_slice >= 0):
                continue

            # Process contiguous runs or whole chain where flagged nodes exist
            m_len = hi - lo
            chain_z = ch.fitted_z.copy()
            # Build per-node candidate arrays of size K_tot (for unflagged trusted nodes, replicate fitted_z)
            c_z = np.repeat(chain_z[:, None], k_tot, axis=1)
            c_cost = np.zeros((m_len, k_tot), dtype=np.float32)
            for li in range(m_len):
                fp = f_slice[li]
                if fp >= 0:
                    c_z[li] = z_grid[fp]
                    c_cost[li] = unary_cost[fp]
                else:
                    # Trusted anchor node: zero cost at index 0, high cost elsewhere
                    c_cost[li, 1:] = 1e4

            dp = c_cost[0].copy()
            back = np.zeros((m_len, k_tot), dtype=np.int32)
            lam_step = 0.45
            max_jump_pen = 3.2
            for li in range(1, m_len):
                p_scale = max(float(ch.node_pixel[li]), 1e-4)
                # Pairwise (K_prev, K_curr)
                dz_p = np.abs(c_z[li - 1, :, None] - c_z[li, None, :]) / p_scale
                trans = lam_step * np.minimum(dz_p, max_jump_pen / lam_step).astype(np.float32)
                scores = dp[:, None] + trans
                best_prev = np.argmin(scores, axis=0)
                back[li] = best_prev
                dp = c_cost[li] + scores[best_prev, np.arange(k_tot)]

            curr_k = int(np.argmin(dp))
            chosen_z = np.empty(m_len, dtype=np.float64)
            for li in range(m_len - 1, -1, -1):
                chosen_z[li] = c_z[li, curr_k]
                curr_k = int(back[li, curr_k])

            for li in range(m_len):
                if f_slice[li] >= 0 and abs(chosen_z[li] - ch.fitted_z[li]) > 0.25 * ch.node_pixel[li]:
                    g_i = lo + li
                    repaired_pts[g_i] = ch.cam_center + chosen_z[li] * ch.rays[li]
                    was_repaired[g_i] = True

    # Re-evaluate all points after ray repair
    post_eval = evaluator.query_points(repaired_pts, pixel_scale=p_med)

    # Keep nodes that are inside the multi-view visual hull, free of foreground space violations, and corroborated
    valid_node = (
        (post_eval["hull_viol_rate"] <= 0.065)
        & (post_eval["free_space_viol"] <= max_fsv_allowed)
        & (post_eval["edge_support_cnt"] >= 2)
        & np.all(repaired_pts >= bbox_min[None, :] - 0.05, axis=1)
        & np.all(repaired_pts <= bbox_max[None, :] + 0.05, axis=1)
    )

    if roi_bounds is not None:
        r_min, r_max = roi_bounds
        in_roi = np.all((repaired_pts >= r_min[None, :]) & (repaired_pts <= r_max[None, :]), axis=1)
        valid_node = valid_node & in_roi

    # Split chains at invalid nodes, depth discontinuities (> 4.5p), or sharp corners (> 60 deg)
    cleaned_segments: list[CleanedChainSegment] = []
    next_cid = 0
    cos_turn_min = float(np.cos(np.deg2rad(62.0)))

    for pid, ch in enumerate(parents):
        lo, hi = offsets[pid]
        v_mask = valid_node[lo:hi]
        pts_c = repaired_pts[lo:hi]
        px_c = ch.node_pixel
        sup_c = post_eval["edge_support_cnt"][lo:hi]
        rep_c = was_repaired[lo:hi]
        djump_c = post_eval["depth_jump_mean"][lo:hi]

        # Extract contiguous valid runs
        idx = 0
        m_len = hi - lo
        while idx < m_len:
            if not v_mask[idx]:
                idx += 1
                continue
            run_start = idx
            idx += 1
            while idx < m_len and v_mask[idx]:
                step_d = float(np.linalg.norm(pts_c[idx] - pts_c[idx - 1]))
                if step_d > 5.0 * max(float(px_c[idx]), p_med):
                    break
                if idx - run_start >= 2:
                    v1 = pts_c[idx - 1] - pts_c[idx - 2]
                    v2 = pts_c[idx] - pts_c[idx - 1]
                    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
                    if n1 > 1e-9 and n2 > 1e-9 and float(np.dot(v1, v2) / (n1 * n2)) < cos_turn_min:
                        break
                idx += 1

            sub_pts = pts_c[run_start:idx]
            if len(sub_pts) < 3:
                continue
            arc_l = float(np.linalg.norm(np.diff(sub_pts, axis=0), axis=1).sum())
            if arc_l < 1.5 * p_med:
                continue

            sub_rays = pts_c[run_start:idx] - ch.cam_center[None, :]
            r_nrm = np.linalg.norm(sub_rays, axis=1, keepdims=True)
            sub_rays = sub_rays / np.maximum(r_nrm, 1e-9)

            cleaned_segments.append(
                CleanedChainSegment(
                    chain_id=next_cid,
                    parent_id=pid,
                    source_view=ch.source_view,
                    cam_center=ch.cam_center.copy(),
                    points_3d=sub_pts.copy(),
                    tangents_3d=_compute_polyline_tangents(sub_pts),
                    ray_dirs=sub_rays,
                    node_pixel=px_c[run_start:idx].copy(),
                    mv_support_views=sup_c[run_start:idx].copy(),
                    was_repaired=rep_c[run_start:idx].copy(),
                    is_silhouette_jump=bool(np.median(djump_c[run_start:idx]) > 0.025),
                )
            )
            next_cid += 1

    stats = {
        "total_input_parents": len(parents),
        "total_input_nodes": int(len(all_pts)),
        "state2_extrapolated_nodes": int(np.sum(all_state == 2)),
        "initial_hull_violation_nodes": int(np.sum(init_hull_bad)),
        "initial_free_space_violation_nodes": int(np.sum(init_fsv_bad)),
        "flagged_for_ray_retriangulation": int(len(flagged_indices)),
        "repaired_nodes": int(np.sum(was_repaired)),
        "post_repair_hull_violation_nodes": int(np.sum(post_eval["hull_viol_rate"] > 0.075)),
        "kept_valid_nodes": int(np.sum(valid_node)),
        "pruned_outlier_nodes": int(np.sum(~valid_node)),
        "output_clean_subchains": len(cleaned_segments),
    }
    return cleaned_segments, stats
