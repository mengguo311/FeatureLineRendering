"""Phase 2 (v02): Three 3DGS Leaf Kernel Optimization Operators & Joint Combination.

Implements:
  - Anatomical Leaf Frame Orientation: resolves PCA +/- sign ambiguity so s=0 is petiole base and s=1 is leaf apex.
  - M1 (Opacity Sharpening & Halo Suppression): Beer-Lambert sheet optical density consolidation
    alpha' = 1 - (1 - alpha)^gamma(rho) + faint volumetric fog suppression to eliminate multi-layer X-ray bleed.
  - M2 (Boundary-Straddling Wide Gaussian Splitting): 2-pass 3D seam-straddling wide kernel detection,
    exact 2-child moment-preserving Gaussian splitting along principal axes, and independent child leaf re-assignment.
  - M3 (Per-Leaf Anatomical UV Parameterization & 3D Botanical Venation / Watercolor Rim Mapping):
    in-plane texel-grade Gaussian subdivision + 3D midrib, 5-pair arcuate lateral veins, and watercolor margin pooling.
"""

from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from .data_io import GaussianCloud3D, PriorVectorGeometry
from .kernel_partitioner import LeafInstance3D, _build_closed_leaf_contour_3d
from .multiview_leaf_cells import LABEL_POT_OR_SOIL, LABEL_WOOD_STEM


@dataclass
class LeafPolarEnvelope:
    """Precomputed 24-sector local polar frame & radial boundary envelope for fast vectorized (u, v, rho) queries."""

    centroids: np.ndarray    # (L, 3) float64
    e_len: np.ndarray        # (L, 3) float64 anatomical petiole-base -> apex unit vector
    e_wid: np.ndarray        # (L, 3) float64 transverse blade width unit vector
    e_nrm: np.ndarray        # (L, 3) float64 blade normal unit vector
    a_half: np.ndarray       # (L,) float64 half-length scale
    b_half: np.ndarray       # (L,) float64 half-width scale
    h_thick: np.ndarray      # (L,) float64 half-thickness scale
    r_sectors: np.ndarray    # (L, 24) float64 normalized radial boundary per 15-deg sector
    tier_code: np.ndarray    # (L,) int32: 0=OUTER_ENCLOSED, 1=MID_PARTIAL_OCCLUDED, 2=DEEP_OCCLUDED


def build_cloud_from_arrays(
    means: np.ndarray,
    scales: np.ndarray,
    quats_wxyz: np.ndarray,
    opacities: np.ndarray,
    rgb_dc: np.ndarray,
    shs: np.ndarray,
) -> GaussianCloud3D:
    """Construct a valid GaussianCloud3D with freshly recomputed 3D covariance cov6 and surfel normals."""
    q = quats_wxyz.astype(np.float32, copy=True)
    q /= np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-12)
    sc = np.maximum(scales.astype(np.float32), 1e-7)
    R_mat = Rotation.from_quat(q[:, [1, 2, 3, 0]]).as_matrix().astype(np.float32)
    cov3 = (R_mat * (sc[:, None, :] ** 2)) @ R_mat.transpose(0, 2, 1)
    cov6 = np.ascontiguousarray(cov3[:, [0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]])
    min_ax = np.argmin(sc, axis=1)
    surfel_normals = np.ascontiguousarray(R_mat[np.arange(len(means)), :, min_ax])

    return GaussianCloud3D(
        means=np.ascontiguousarray(means, dtype=np.float32),
        scales=np.ascontiguousarray(sc, dtype=np.float32),
        quats_wxyz=np.ascontiguousarray(q, dtype=np.float32),
        cov6=cov6,
        surfel_normals=surfel_normals,
        opacities=np.ascontiguousarray(np.clip(opacities, 1e-5, 0.999), dtype=np.float32),
        rgb_dc=np.ascontiguousarray(np.clip(rgb_dc, 0.0, 1.0), dtype=np.float32),
        shs=np.ascontiguousarray(shs, dtype=np.float32),
    )


def orient_leaf_frames_anatomically(
    cloud: GaussianCloud3D,
    kernel_labels: np.ndarray,
    leaf_instances: list[LeafInstance3D],
    priors: PriorVectorGeometry,
) -> list[LeafInstance3D]:
    """Orient every leaf's axis_length from petiole attachment base (-u) toward distal leaf tip (+u)."""
    wood_mask = (kernel_labels == LABEL_WOOD_STEM) & (cloud.opacities >= 0.035)
    wood_pts_list = [cloud.means[wood_mask].astype(np.float64)]
    if len(priors.trunk_points) > 0:
        wood_pts_list.append(priors.trunk_points.astype(np.float64))
    wood_pts = np.concatenate(wood_pts_list, axis=0) if wood_pts_list else np.zeros((0, 3), dtype=np.float64)
    wood_tree = cKDTree(wood_pts) if len(wood_pts) > 0 else None

    pot_o = priors.pot_axis_origin
    pot_a = priors.pot_axis_dir

    oriented: list[LeafInstance3D] = []
    for lf in leaf_instances:
        elen = lf.axis_length.copy()
        ewid = lf.axis_width.copy()
        enrm = lf.normal.copy()
        arm = 0.40 * max(lf.length_world, 0.015)
        p_pos = lf.centroid + arm * elen
        p_neg = lf.centroid - arm * elen

        flip = False
        if wood_tree is not None:
            d_pos, _ = wood_tree.query(p_pos, k=1)
            d_neg, _ = wood_tree.query(p_neg, k=1)
            # Petiole base (-arm * elen) MUST be closer to woody stem than distal tip (+arm * elen)!
            if float(d_pos) + 0.003 < float(d_neg):
                flip = True
            elif abs(float(d_pos) - float(d_neg)) <= 0.003:
                # Fallback: distal leaf tip radiates farther outward from central pot/trunk axis
                r_pos = np.linalg.norm((p_pos - pot_o) - np.dot(p_pos - pot_o, pot_a) * pot_a)
                r_neg = np.linalg.norm((p_neg - pot_o) - np.dot(p_neg - pot_o, pot_a) * pot_a)
                if r_pos < r_neg:
                    flip = True
        else:
            r_pos = np.linalg.norm((p_pos - pot_o) - np.dot(p_pos - pot_o, pot_a) * pot_a)
            r_neg = np.linalg.norm((p_neg - pot_o) - np.dot(p_neg - pot_o, pot_a) * pot_a)
            if r_pos < r_neg:
                flip = True

        if flip:
            elen = -elen
            ewid = -ewid  # Preserves right-handedness elen x ewid = enrm

        oriented.append(replace(lf, axis_length=elen, axis_width=ewid, normal=enrm))
    return oriented


def build_polar_envelopes(leaf_instances: list[LeafInstance3D]) -> LeafPolarEnvelope:
    """Pack all 3D leaf frames and 24-sector closed polar contours into contiguous arrays for O(N) vectorized queries."""
    n_l = len(leaf_instances)
    centroids = np.zeros((n_l, 3), dtype=np.float64)
    e_len = np.zeros((n_l, 3), dtype=np.float64)
    e_wid = np.zeros((n_l, 3), dtype=np.float64)
    e_nrm = np.zeros((n_l, 3), dtype=np.float64)
    a_half = np.zeros(n_l, dtype=np.float64)
    b_half = np.zeros(n_l, dtype=np.float64)
    h_thick = np.zeros(n_l, dtype=np.float64)
    r_sectors = np.ones((n_l, 24), dtype=np.float64)
    tier_code = np.zeros(n_l, dtype=np.int32)

    for i, lf in enumerate(leaf_instances):
        centroids[i] = lf.centroid
        e_len[i] = lf.axis_length
        e_wid[i] = lf.axis_width
        e_nrm[i] = lf.normal
        a = max(0.5 * lf.length_world, 0.005)
        b = max(0.5 * lf.width_world, 0.003)
        a_half[i] = a
        b_half[i] = b
        h_thick[i] = max(0.5 * lf.thickness_world, 0.0035)
        if lf.visibility_tier == "OUTER_ENCLOSED":
            tier_code[i] = 0
        elif lf.visibility_tier == "MID_PARTIAL_OCCLUDED":
            tier_code[i] = 1
        else:
            tier_code[i] = 2

        # Recover 24-bin polar envelope r(theta) in the oriented (e_len, e_wid) frame
        rel_loop = lf.boundary_loop_3d - lf.centroid[None, :]
        ul = (rel_loop @ lf.axis_length) / a
        vl = (rel_loop @ lf.axis_width) / b
        rl = np.hypot(ul, vl)
        thl = np.arctan2(vl, ul)  # [-pi, pi]
        # Resample onto uniform 24 bins [-pi, pi)
        bins = np.linspace(-math.pi, math.pi, 24, endpoint=False)
        for b_idx, th0 in enumerate(bins):
            d_th = np.abs((thl - th0 + math.pi) % (2.0 * math.pi) - math.pi)
            best_k = int(np.argmin(d_th))
            r_sectors[i, b_idx] = max(float(rl[best_k]), 0.45)

    return LeafPolarEnvelope(
        centroids=centroids,
        e_len=e_len,
        e_wid=e_wid,
        e_nrm=e_nrm,
        a_half=a_half,
        b_half=b_half,
        h_thick=h_thick,
        r_sectors=r_sectors,
        tier_code=tier_code,
    )


def compute_kernel_leaf_polar_coords(
    means: np.ndarray,
    kernel_labels: np.ndarray,
    env: LeafPolarEnvelope,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute local normalized leaf coordinates (s_01, t_signed, rho_boundary, zeta_normal) for all foliage kernels.

    Returns arrays of length N (matching means):
      fol_mask: (N,) bool (kernel_labels >= 0)
      s_01: (N,) float32 in [0, 1] (0 = anatomical petiole base, 1 = distal leaf tip)
      t_norm: (N,) float32 in [-1.5, 1.5] (0 = central midrib, +/-1 = local curved lateral margin!)
      rho: (N,) float32 polar radial fraction relative to closed 24-pt leaf loop (<1 inside leaf, >1 outside)
      zeta: (N,) float32 out-of-plane distance normalized by half-thickness
    """
    n = len(means)
    fol_mask = kernel_labels >= 0
    s_01 = np.zeros(n, dtype=np.float32)
    t_norm = np.zeros(n, dtype=np.float32)
    rho = np.zeros(n, dtype=np.float32)
    zeta = np.zeros(n, dtype=np.float32)

    idx = np.where(fol_mask)[0]
    if len(idx) == 0:
        return fol_mask, s_01, t_norm, rho, zeta

    lids = kernel_labels[idx]
    rel = means[idx].astype(np.float64) - env.centroids[lids]
    u = np.sum(rel * env.e_len[lids], axis=1)
    v = np.sum(rel * env.e_wid[lids], axis=1)
    w = np.sum(rel * env.e_nrm[lids], axis=1)

    un = u / env.a_half[lids]
    vn = v / env.b_half[lids]
    rn = np.hypot(un, vn)
    ang = np.arctan2(vn, un)  # [-pi, pi]

    # Continuous linear interpolation on 24-bin circular polar envelope
    pos_f = ((ang + math.pi) / (2.0 * math.pi)) * 24.0
    b0 = np.floor(pos_f).astype(np.int32) % 24
    b1 = (b0 + 1) % 24
    frac = pos_f - np.floor(pos_f)
    r_bound = (1.0 - frac) * env.r_sectors[lids, b0] + frac * env.r_sectors[lids, b1]

    rho_f = rn / np.maximum(r_bound, 0.35)
    # Anatomical base-to-tip s in [0, 1] accounting for polar tip/base extent
    r_tip = env.r_sectors[lids, 12]   # theta = 0 (+e_len)
    r_base = env.r_sectors[lids, 0]   # theta = -pi (-e_len)
    s_f = np.clip((un + r_base) / np.maximum(r_tip + r_base, 0.5), 0.0, 1.0)

    # Lanceolate width profile b_local(s) = sin-like arch max(0.22, sin(pi * clip(s, 0.04, 0.96))^0.75)
    blade_arch = np.maximum(0.22, np.power(np.sin(math.pi * np.clip(s_f, 0.04, 0.96)), 0.72))
    t_f = np.clip(vn / blade_arch, -1.5, 1.5)

    s_01[idx] = s_f.astype(np.float32)
    t_norm[idx] = t_f.astype(np.float32)
    rho[idx] = rho_f.astype(np.float32)
    zeta[idx] = (np.abs(w) / env.h_thick[lids]).astype(np.float32)
    return fol_mask, s_01, t_norm, rho, zeta


def apply_m1_opacity_sharpening(
    cloud: GaussianCloud3D,
    kernel_labels: np.ndarray,
    leaf_instances: list[LeafInstance3D],
    core_gamma_outer: float = 4.5,
    core_gamma_mid: float = 3.4,
    halo_thresh: float = 0.024,
) -> tuple[GaussianCloud3D, dict[str, Any]]:
    """M1: Beer-Lambert sheet optical density consolidation + faint halo tail suppression.

    Replaces semi-transparent leaf interior kernels via exact optical-thickness multiplication:
      alpha'_g = 1 - (1 - alpha_g)^gamma(rho)
    while suppressing faint inter-leaf fog kernels (alpha < halo_thresh) and tucking exterior fringe tails.
    """
    env = build_polar_envelopes(leaf_instances)
    fol_mask, _, _, rho, zeta = compute_kernel_leaf_polar_coords(cloud.means, kernel_labels, env)

    new_op = cloud.opacities.copy()
    new_sc = cloud.scales.copy()

    idx = np.where(fol_mask)[0]
    lids = kernel_labels[idx]
    op_f = new_op[idx].astype(np.float64)
    rho_f = rho[idx].astype(np.float64)
    zeta_f = zeta[idx].astype(np.float64)
    t_code = env.tier_code[lids]

    # 1. Suppress ultra-faint volumetric halo kernels & out-of-plane ghost floaters
    is_faint_halo = (op_f < halo_thresh) | ((zeta_f > 2.1) & (op_f < 0.085))
    is_outer_fringe = (~is_faint_halo) & (rho_f > 1.03) & (op_f < 0.20)

    # 2. Smooth radial optical density gain gamma(rho) on active leaf blade kernels
    base_gamma = np.where(t_code == 0, core_gamma_outer, np.where(t_code == 1, core_gamma_mid, 2.3))
    # Taper gamma smoothly from 1.0*base_gamma at rho<=0.80 to 1.55 at rho>=1.04 so margins stay anti-aliased!
    margin_t = np.clip((rho_f - 0.80) / 0.24, 0.0, 1.0)
    smooth_w = 0.5 * (1.0 + np.cos(math.pi * margin_t))
    gamma = 1.55 + (base_gamma - 1.55) * smooth_w

    op_sharp = 1.0 - np.power(np.clip(1.0 - op_f, 1e-6, 1.0), gamma)
    op_out = np.where(is_faint_halo, op_f * 0.06, np.where(is_outer_fringe, op_f * 0.22, op_sharp))
    new_op[idx] = np.clip(op_out, 1e-4, 0.994).astype(np.float32)

    # Slightly tighten scale on exterior fringe kernels so fuzzy tails don't spill past closed leaf rims
    fringe_global = idx[is_outer_fringe | ((rho_f > 0.96) & (op_f < 0.12))]
    new_sc[fringe_global] *= 0.84

    out_cloud = build_cloud_from_arrays(
        means=cloud.means,
        scales=new_sc,
        quats_wxyz=cloud.quats_wxyz,
        opacities=new_op,
        rgb_dc=cloud.rgb_dc,
        shs=cloud.shs,
    )
    stats = {
        "faint_halo_suppressed_count": int(is_faint_halo.sum()),
        "outer_fringe_tucked_count": int(is_outer_fringe.sum()),
        "median_active_leaf_opacity_before": round(float(np.median(op_f[~is_faint_halo])), 4),
        "median_active_leaf_opacity_after": round(float(np.median(new_op[idx][~is_faint_halo])), 4),
    }
    return out_cloud, stats


def rebuild_leaf_instances_for_cloud(
    cloud: GaussianCloud3D,
    kernel_labels: np.ndarray,
    prev_instances: list[LeafInstance3D],
    priors: PriorVectorGeometry,
    refit_contours: bool = False,
) -> list[LeafInstance3D]:
    """Update kernel_indices (and optionally refit contours) after Gaussian splitting while preserving leaf IDs & frames."""
    updated: list[LeafInstance3D] = []
    for lf in prev_instances:
        k_idxs = np.where(kernel_labels == lf.leaf_id)[0].astype(np.int32)
        act_k = k_idxs[cloud.opacities[k_idxs] >= 0.025]
        if refit_contours and len(act_k) >= 8:
            ctr, elen, ewid, enrm, l_w, w_w, t_w, area_w, loop_3d = _build_closed_leaf_contour_3d(
                cloud.means[act_k].astype(np.float64), cloud.scales[act_k].astype(np.float64)
            )
            # Preserve anatomical sign from prev_instances!
            if float(np.dot(elen, lf.axis_length)) < 0.0:
                elen = -elen
                ewid = -ewid
            updated.append(
                replace(
                    lf,
                    kernel_indices=k_idxs,
                    active_kernel_count=int(len(act_k)),
                    centroid=ctr,
                    axis_length=elen,
                    axis_width=ewid,
                    normal=enrm,
                    length_world=l_w,
                    width_world=w_w,
                    thickness_world=t_w,
                    area_world=area_w,
                    boundary_loop_3d=loop_3d,
                )
            )
        else:
            updated.append(replace(lf, kernel_indices=k_idxs, active_kernel_count=int(len(act_k))))
    return orient_leaf_frames_anatomically(cloud, kernel_labels, updated, priors)


def apply_m2_straddling_kernel_splitting(
    cloud: GaussianCloud3D,
    kernel_labels: np.ndarray,
    leaf_instances: list[LeafInstance3D],
    priors: PriorVectorGeometry,
    num_passes: int = 2,
    min_split_px: float = 1.65,
) -> tuple[GaussianCloud3D, np.ndarray, list[LeafInstance3D], dict[str, Any]]:
    """M2: 2-pass exact 3D Gaussian splitting of wide kernels straddling inter-leaf seams or leaf margins.

    Detects wide foliage kernels (sigma_max > min_split_px * p_med) whose +/- 1.25*sigma wings cross into an
    adjacent leaf, woody stem, or empty space outside the closed leaf loop; splits each into two half-scale
    child Gaussians along that principal axis and independently re-assigns each child to its local leaf!
    """
    p_med = priors.median_pixel_scale
    means = cloud.means.copy()
    scales = cloud.scales.copy()
    quats = cloud.quats_wxyz.copy()
    opac = cloud.opacities.copy()
    rgb_dc = cloud.rgb_dc.copy()
    shs = cloud.shs.copy()
    labels = kernel_labels.copy()

    env = build_polar_envelopes(leaf_instances)

    # Build trusted core reference tree (interior active foliage + woody stem kernels) for crisp seam localization!
    _, _, _, rho_init, zeta_init = compute_kernel_leaf_polar_coords(means, labels, env)
    trusted_fol = (labels >= 0) & (opac >= 0.032) & (rho_init <= 0.90) & (zeta_init <= 1.6)
    trusted_wood = (labels == LABEL_WOOD_STEM) & (opac >= 0.045)
    ref_mask = trusted_fol | trusted_wood
    if int(ref_mask.sum()) < 50:
        ref_mask = (labels >= 0) | (labels == LABEL_WOOD_STEM)

    ref_pts = means[ref_mask].astype(np.float64)
    ref_lbls = labels[ref_mask].copy()
    ref_nrms = cloud.surfel_normals[ref_mask].astype(np.float64)
    ref_tree = cKDTree(ref_pts)
    leaf_ctr_tree = cKDTree(env.centroids)

    def assign_wing_or_child(pts_q: np.ndarray, parent_lids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (assigned_label, is_outside_air) for query 3D points."""
        if len(pts_q) == 0:
            return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=bool)
        # Query k=4 nearest trusted core kernels
        d_k, nn_k = ref_tree.query(pts_q, k=4, distance_upper_bound=3.2 * p_med)
        valid_nn = np.isfinite(d_k) & (nn_k < len(ref_pts))

        out_lbl = parent_lids.copy()
        # Check out-of-plane consistency so a foreground wing doesn't jump to a parallel stacked leaf!
        safe_nn0 = np.where(valid_nn[:, 0], nn_k[:, 0], 0)
        delta0 = pts_q - ref_pts[safe_nn0]
        d_perp0 = np.abs(np.sum(delta0 * ref_nrms[safe_nn0], axis=1))
        accept_nn0 = valid_nn[:, 0] & (d_perp0 <= 1.55 * p_med)
        out_lbl = np.where(accept_nn0, ref_lbls[safe_nn0], parent_lids)

        # Also check polar envelope distance to parent leaf to detect empty-air silhouette overhang!
        rel_p = pts_q - env.centroids[parent_lids]
        un = np.sum(rel_p * env.e_len[parent_lids], axis=1) / env.a_half[parent_lids]
        vn = np.sum(rel_p * env.e_wid[parent_lids], axis=1) / env.b_half[parent_lids]
        rn = np.hypot(un, vn)
        ang = np.arctan2(vn, un)
        b0 = np.floor(((ang + math.pi) / (2.0 * math.pi)) * 24.0).astype(np.int32) % 24
        rho_p = rn / np.maximum(env.r_sectors[parent_lids, b0], 0.35)

        # Fallback anisotropic leaf-frame check if outside parent leaf and not near trusted_nn0
        far_from_core = ~valid_nn[:, 0]
        if np.any(far_from_core):
            k_c = min(6, len(leaf_instances))
            _, cand_l = leaf_ctr_tree.query(pts_q[far_from_core], k=k_c)
            if k_c == 1:
                cand_l = cand_l[:, None]
            dq = pts_q[far_from_core, None, :] - env.centroids[cand_l]
            du = np.sum(dq * env.e_len[cand_l], axis=-1) / env.a_half[cand_l]
            dv = np.sum(dq * env.e_wid[cand_l], axis=-1) / env.b_half[cand_l]
            dw = np.sum(dq * env.e_nrm[cand_l], axis=-1) / 0.0045
            best_c = np.argmin(du * du + dv * dv + dw * dw, axis=1)
            best_lid = cand_l[np.arange(int(far_from_core.sum())), best_c]
            min_cost = np.min(du * du + dv * dv + dw * dw, axis=1)
            # Switch if significantly inside another leaf's plane
            switch_m = min_cost < 0.95
            sub_idx = np.where(far_from_core)[0]
            out_lbl[sub_idx[switch_m]] = best_lid[switch_m]

        is_air_overhang = (~valid_nn[:, 0]) & (rho_p > 1.08)
        return out_lbl.astype(np.int32), is_air_overhang

    total_splits = 0
    total_reassigned_children = 0
    total_air_trimmed = 0

    for p_iter in range(num_passes):
        sc_thresh = (min_split_px if p_iter == 0 else min_split_px * 1.10) * p_med
        cand_mask = (labels >= 0) & (opac >= 0.018) & (scales.max(axis=1) > sc_thresh)
        cand_idx = np.where(cand_mask)[0]
        if len(cand_idx) == 0:
            break

        q_c = quats[cand_idx]
        q_c = q_c / np.maximum(np.linalg.norm(q_c, axis=1, keepdims=True), 1e-12)
        R_c = Rotation.from_quat(q_c[:, [1, 2, 3, 0]]).as_matrix().astype(np.float64)
        sc_c = scales[cand_idx].astype(np.float64)
        mu_c = means[cand_idx].astype(np.float64)
        lid_c = labels[cand_idx]

        # Order axes per candidate: ax1 = largest scale, ax2 = second largest scale
        order_ax = np.argsort(sc_c, axis=1)
        ax1 = order_ax[:, 2]
        ax2 = order_ax[:, 1]
        ar = np.arange(len(cand_idx))
        sig1 = sc_c[ar, ax1]
        sig2 = sc_c[ar, ax2]
        u1 = R_c[ar, :, ax1]
        u2 = R_c[ar, :, ax2]

        # Probe +/- 1.28 * sigma wings along primary axis u1
        w1_pos = mu_c + (1.28 * sig1)[:, None] * u1
        w1_neg = mu_c - (1.28 * sig1)[:, None] * u1
        lbl1_pos, air1_pos = assign_wing_or_child(w1_pos, lid_c)
        lbl1_neg, air1_neg = assign_wing_or_child(w1_neg, lid_c)
        straddle_1 = (lbl1_pos != lid_c) | (lbl1_neg != lid_c) | (air1_pos ^ air1_neg)

        # Probe secondary in-plane axis u2 if wide along u2 and not already splitting along u1
        wide_2 = (~straddle_1) & (sig2 > sc_thresh * 1.05)
        straddle_2 = np.zeros(len(cand_idx), dtype=bool)
        if np.any(wide_2):
            sub = np.where(wide_2)[0]
            w2_pos = mu_c[sub] + (1.28 * sig2[sub])[:, None] * u2[sub]
            w2_neg = mu_c[sub] - (1.28 * sig2[sub])[:, None] * u2[sub]
            lbl2_pos, air2_pos = assign_wing_or_child(w2_pos, lid_c[sub])
            lbl2_neg, air2_neg = assign_wing_or_child(w2_neg, lid_c[sub])
            straddle_2[sub] = (lbl2_pos != lid_c[sub]) | (lbl2_neg != lid_c[sub]) | (air2_pos ^ air2_neg)

        do_split_local = straddle_1 | straddle_2
        if not np.any(do_split_local):
            break

        sp_loc = np.where(do_split_local)[0]
        sp_glob = cand_idx[sp_loc]
        use_ax1 = straddle_1[sp_loc]
        split_ax = np.where(use_ax1, ax1[sp_loc], ax2[sp_loc])
        split_sig = np.where(use_ax1, sig1[sp_loc], sig2[sp_loc])
        split_dir = np.where(use_ax1[:, None], u1[sp_loc], u2[sp_loc])
        parent_lid_sp = lid_c[sp_loc]

        # Exact 2-child overlap-preserving split along split_dir:
        # Centers at mu +/- 0.44 * sigma * u, child scale along split_ax = 0.58 * sigma (zero central opacity dip!)
        offset = (0.44 * split_sig)[:, None] * split_dir
        mu_minus = (mu_c[sp_loc] - offset).astype(np.float32)
        mu_plus = (mu_c[sp_loc] + offset).astype(np.float32)

        sc_child = scales[sp_glob].copy()
        sc_child[np.arange(len(sp_glob)), split_ax] *= 0.58

        lbl_minus, air_minus = assign_wing_or_child(mu_minus.astype(np.float64), parent_lid_sp)
        lbl_plus, air_plus = assign_wing_or_child(mu_plus.astype(np.float64), parent_lid_sp)

        op_minus = opac[sp_glob].copy()
        op_plus = opac[sp_glob].copy()
        sc_minus = sc_child.copy()
        sc_plus = sc_child.copy()

        # Attenuate any child whose center landed out in empty air past the closed leaf silhouette!
        if np.any(air_minus):
            op_minus[air_minus] *= 0.22
            sc_minus[air_minus] *= 0.75
        if np.any(air_plus):
            op_plus[air_plus] *= 0.22
            sc_plus[air_plus] *= 0.75

        total_splits += len(sp_glob)
        total_reassigned_children += int(np.sum(lbl_minus != parent_lid_sp) + np.sum(lbl_plus != parent_lid_sp))
        total_air_trimmed += int(np.sum(air_minus) + np.sum(air_plus))

        # Replace parent in-place with minus-child, and append plus-child!
        means[sp_glob] = mu_minus
        scales[sp_glob] = sc_minus
        opac[sp_glob] = op_minus
        labels[sp_glob] = lbl_minus

        means = np.concatenate([means, mu_plus], axis=0)
        scales = np.concatenate([scales, sc_plus], axis=0)
        quats = np.concatenate([quats, quats[sp_glob]], axis=0)
        opac = np.concatenate([opac, op_plus], axis=0)
        rgb_dc = np.concatenate([rgb_dc, rgb_dc[sp_glob]], axis=0)
        shs = np.concatenate([shs, shs[sp_glob]], axis=0)
        labels = np.concatenate([labels, lbl_plus], axis=0)

    out_cloud = build_cloud_from_arrays(means, scales, quats, opac, rgb_dc, shs)
    out_instances = rebuild_leaf_instances_for_cloud(out_cloud, labels, leaf_instances, priors, refit_contours=False)
    stats = {
        "kernels_before": int(len(cloud.means)),
        "kernels_after": int(len(out_cloud.means)),
        "total_parent_splits": int(total_splits),
        "children_reassigned_across_seams": int(total_reassigned_children),
        "overhanging_air_children_trimmed": int(total_air_trimmed),
    }
    return out_cloud, labels, out_instances, stats


def subdivide_interior_leaf_texels_3d(
    cloud: GaussianCloud3D,
    kernel_labels: np.ndarray,
    leaf_instances: list[LeafInstance3D],
    priors: PriorVectorGeometry,
    num_passes: int = 2,
    texel_scale_px: float = 1.55,
) -> tuple[GaussianCloud3D, np.ndarray, list[LeafInstance3D], dict[str, Any]]:
    """In-plane 3D Gaussian texel refinement with gap-free overlap so leaves resolve crisp 3D midribs & rims."""
    p_med = priors.median_pixel_scale
    means = cloud.means.copy()
    scales = cloud.scales.copy()
    quats = cloud.quats_wxyz.copy()
    opac = cloud.opacities.copy()
    rgb_dc = cloud.rgb_dc.copy()
    shs = cloud.shs.copy()
    labels = kernel_labels.copy()

    target_s = texel_scale_px * p_med
    n_before = len(means)
    subdiv_cnt = 0

    for _ in range(num_passes):
        cand = np.where((labels >= 0) & (opac >= 0.025) & (scales.max(axis=1) > target_s))[0]
        if len(cand) == 0:
            break
        q_c = quats[cand]
        q_c = q_c / np.maximum(np.linalg.norm(q_c, axis=1, keepdims=True), 1e-12)
        R_c = Rotation.from_quat(q_c[:, [1, 2, 3, 0]]).as_matrix().astype(np.float32)
        sc_c = scales[cand]
        ax_max = np.argmax(sc_c, axis=1)
        ar = np.arange(len(cand))
        sig_m = sc_c[ar, ax_max]
        u_m = R_c[ar, :, ax_max]

        off = (0.40 * sig_m)[:, None] * u_m
        mu_a = means[cand] - off
        mu_b = means[cand] + off
        sc_new = sc_c.copy()
        sc_new[ar, ax_max] *= 0.62

        means[cand] = mu_a
        scales[cand] = sc_new

        means = np.concatenate([means, mu_b], axis=0)
        scales = np.concatenate([scales, sc_new], axis=0)
        quats = np.concatenate([quats, quats[cand]], axis=0)
        opac = np.concatenate([opac, opac[cand]], axis=0)
        rgb_dc = np.concatenate([rgb_dc, rgb_dc[cand]], axis=0)
        shs = np.concatenate([shs, shs[cand]], axis=0)
        labels = np.concatenate([labels, labels[cand]], axis=0)
        subdiv_cnt += len(cand)

    out_cloud = build_cloud_from_arrays(means, scales, quats, opac, rgb_dc, shs)
    out_instances = rebuild_leaf_instances_for_cloud(out_cloud, labels, leaf_instances, priors, refit_contours=False)
    return out_cloud, labels, out_instances, {
        "texel_kernels_before": int(n_before),
        "texel_kernels_after": int(len(out_cloud.means)),
        "texel_subdivisions": int(subdiv_cnt),
    }


def build_v02_uv_venation_color_banks(
    cloud: GaussianCloud3D,
    kernel_labels: np.ndarray,
    leaf_instances: list[LeafInstance3D],
    enable_m3_venation: bool = True,
) -> dict[str, np.ndarray]:
    """Build instance_palette, flat_instance_id, and botanical_stylized RGB banks (with or without M3 3D UV venation)."""
    base_rgb = cloud.rgb_dc.copy()
    lum = (0.299 * base_rgb[:, 0] + 0.587 * base_rgb[:, 1] + 0.114 * base_rgb[:, 2])[:, None]

    pot_mask = kernel_labels == LABEL_POT_OR_SOIL
    wood_mask = kernel_labels == LABEL_WOOD_STEM

    inst_colors = base_rgb.copy()
    flat_inst_colors = np.ones_like(base_rgb)
    stylized_colors = base_rgb.copy()

    inst_colors[pot_mask] = 0.22 + 0.35 * base_rgb[pot_mask]
    inst_colors[wood_mask] = np.array([0.48, 0.38, 0.28], dtype=np.float32) * (0.65 + 0.6 * lum[wood_mask])
    flat_inst_colors[pot_mask] = 0.25
    flat_inst_colors[wood_mask] = np.array([0.45, 0.35, 0.25], dtype=np.float32)

    # Stylized ceramic glaze for pot & warm bark shading for woody stems
    stylized_colors[pot_mask] = np.clip(0.14 + 0.72 * base_rgb[pot_mask], 0.0, 1.0)
    stylized_colors[wood_mask] = np.clip(
        np.array([0.44, 0.33, 0.22], dtype=np.float32) * (0.62 + 0.72 * lum[wood_mask]), 0.0, 1.0
    )

    env = build_polar_envelopes(leaf_instances)
    fol_mask, s_01, t_norm, rho, _ = compute_kernel_leaf_polar_coords(cloud.means, kernel_labels, env)
    idx = np.where(fol_mask)[0]
    if len(idx) == 0:
        return {
            "instance_palette": inst_colors,
            "flat_instance_palette": flat_inst_colors,
            "botanical_stylized": stylized_colors,
        }

    lids = kernel_labels[idx]
    s_f = s_01[idx]
    t_f = t_norm[idx]
    rho_f = rho[idx]
    lum_f = lum[idx, 0]

    # Precompute per-leaf palette entries (L, 3)
    n_l = len(leaf_instances)
    golden = 0.618033988749895
    c_inst_lut = np.zeros((n_l, 3), dtype=np.float32)
    c_base_lut = np.zeros((n_l, 3), dtype=np.float32)
    c_tip_lut = np.zeros((n_l, 3), dtype=np.float32)
    c_vein_lut = np.zeros((n_l, 3), dtype=np.float32)
    c_rim_lut = np.zeros((n_l, 3), dtype=np.float32)

    z_leaves = env.centroids[:, 2]
    z_lo = float(np.percentile(z_leaves, 5.0)) if n_l > 0 else -0.3
    z_hi = float(np.percentile(z_leaves, 95.0)) if n_l > 0 else 0.9

    for i, lf in enumerate(leaf_instances):
        hue_i = (lf.leaf_id * golden) % 1.0
        sat_i = 0.72 + 0.18 * ((lf.leaf_id * 0.37) % 1.0)
        c_inst_lut[i] = colorsys.hsv_to_rgb(hue_i, sat_i, 0.90)

        sun_t = float(np.clip((lf.centroid[2] - z_lo) / max(z_hi - z_lo, 1e-4), 0.0, 1.0))
        leaf_rand = ((lf.leaf_id * 1103515245 + 12345) & 0x7FFFFFFF) / float(0x7FFFFFFF)
        warmth = float(np.clip(0.65 * sun_t + 0.35 * leaf_rand, 0.0, 1.0))

        h_aut = 0.30 * (1.0 - warmth) + 0.035 * warmth
        s_aut = 0.62 + 0.22 * warmth
        v_aut = 0.76 + 0.17 * warmth
        c_base_lut[i] = colorsys.hsv_to_rgb(h_aut, min(0.92, s_aut + 0.04), max(0.45, v_aut - 0.08))
        c_tip_lut[i] = colorsys.hsv_to_rgb(max(0.01, h_aut - 0.045), min(0.92, s_aut + 0.08), min(0.99, v_aut + 0.10))
        # Luminous warm chartreuse/gold botanical midrib & lateral veins + rich watercolor sepia-emerald rim!
        c_vein_lut[i] = colorsys.hsv_to_rgb(max(0.06, h_aut + 0.03), max(0.28, s_aut - 0.30), min(1.0, v_aut + 0.22))
        c_rim_lut[i] = colorsys.hsv_to_rgb(max(0.01, h_aut - 0.03), min(0.96, s_aut + 0.16), max(0.18, 0.42 * v_aut))

    flat_c = c_inst_lut[lids]
    flat_inst_colors[idx] = flat_c
    shade = np.clip(0.68 + 0.55 * lum_f, 0.55, 1.12)[:, None]
    inst_colors[idx] = np.clip(flat_c * shade, 0.0, 1.0)

    # Base anatomical petiole-to-apex color gradient
    u_w = s_f[:, None]
    lamina_col = (1.0 - u_w) * c_base_lut[lids] + u_w * c_tip_lut[lids]
    cel_shade = np.where(lum_f > 0.52, 1.06, np.where(lum_f > 0.34, 0.92, 0.77)).astype(np.float32)[:, None]
    lamina_col = np.clip(lamina_col * cel_shade, 0.0, 1.0)

    if enable_m3_venation:
        abs_t = np.abs(t_f)
        # 1. Central anatomical midrib: tapers from petiole base (s=0, half-width 0.085) toward leaf apex (s=0.92, 0.025)
        midrib_hw = 0.085 * (1.0 - 0.68 * s_f) * np.clip((0.94 - s_f) / 0.12, 0.0, 1.0)
        midrib_w = np.exp(-0.5 * ((abs_t / np.maximum(midrib_hw, 0.012)) ** 2)) * np.clip((0.93 - s_f) * 8.0, 0.0, 1.0)

        # 2. 5 pairs of arcuate pinnate lateral veins s_vein(t) = s_k + 0.15 * |t|^1.35
        lat_w = np.zeros_like(s_f)
        in_lat_span = (abs_t >= 0.03) & (abs_t <= 0.86)
        t_curve = 0.15 * np.power(np.clip(abs_t, 0.0, 1.0), 1.35)
        for s_anchor in (0.14, 0.28, 0.42, 0.56, 0.70):
            ds = s_f - (s_anchor + t_curve)
            taper_lat = np.clip(1.0 - abs_t / 0.88, 0.0, 1.0)
            w_k = np.exp(-0.5 * ((ds / 0.022) ** 2)) * taper_lat
            lat_w = np.maximum(lat_w, w_k)
        lat_w = np.where(in_lat_span, 0.72 * lat_w, 0.0)

        vein_strength = np.clip(np.maximum(midrib_w, lat_w), 0.0, 0.92)[:, None]
        lamina_col = (1.0 - vein_strength) * lamina_col + vein_strength * c_vein_lut[lids]

        # 3. Botanical Watercolor Edge Pigment Pooling + Crisp Self-Rim Darkening along closed contour rho in [0.82, 1.05]
        rim_band = np.clip((rho_f - 0.82) / 0.15, 0.0, 1.0)
        rim_pool = (0.74 * (rim_band ** 1.5))[:, None]
        lamina_col = (1.0 - rim_pool) * lamina_col + rim_pool * c_rim_lut[lids]

    stylized_colors[idx] = lamina_col.astype(np.float32)
    return {
        "instance_palette": inst_colors,
        "flat_instance_palette": flat_inst_colors,
        "botanical_stylized": stylized_colors,
    }
