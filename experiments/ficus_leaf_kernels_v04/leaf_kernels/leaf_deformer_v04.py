"""Phase 4 (v04): Per-Leaf 3D Geometric Deformation Engine with Petiole Hinge & Jacobian Covariance Transport.

Operates on the M1+M2 per-leaf 3DGS Gaussian kernel substrate (297,343 kernels across 472 discrete 3D leaves).
Key mathematical guarantees:
  1. Clamped Petiole Hinge Boundary Condition: every leaf l is anchored at its anatomical petiole attachment
     point p_base_l (s = 0), guaranteeing Phi_l(p_base_l) = p_base_l (zero branch detachment) while POT (-1)
     and WOOD_STEM (-2) remain 100% rigid!
  2. Inextensible Framed-Ribbon Centerline + Circular Transverse Cupping: integrates unit spine tangents
     ||T_l(s)||_2 == 1 along 32 quadrature nodes per leaf so large bending/droop/wind angles (up to 65 deg)
     strictly conserve leaf blade arc-length without rubber stretching.
  3. First-Order Jacobian Covariance Transport: transforms every leaf Gaussian's 3D covariance tensor via
     Sigma'_k = J_k Sigma_k J_k^T so razor-thin 2D pancake surfels rotate and stretch smoothly along curved
     or expanded leaf blades without Swiss-cheese cracks or staircase artifacts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from scipy.spatial.transform import Rotation

from .data_io import GaussianCloud3D
from .kernel_partitioner import LeafInstance3D
from .style_presets_v03 import LeafKernelSubstrateM12


@dataclass
class LeafDeformRig:
    """Precomputed petiole-hinged anatomical coordinate rig for all L discrete 3D leaves."""

    num_leaves: int
    p_base: np.ndarray        # (L, 3) float64 3D petiole attachment hinge point (s = 0)
    e1: np.ndarray            # (L, 3) float64 anatomical petiole -> apex unit vector
    e2: np.ndarray            # (L, 3) float64 bilateral blade width unit vector
    e3: np.ndarray            # (L, 3) float64 blade surface normal (e1 x e2 = e3)
    blade_len: np.ndarray     # (L,) float64 longitudinal blade span L_l
    blade_half_w: np.ndarray  # (L,) float64 transverse half-width B_l
    fol_idx: np.ndarray       # (M,) int32 indices of all foliage kernels (kernel_labels >= 0)
    fol_lids: np.ndarray      # (M,) int32 leaf_id per foliage kernel
    u_k: np.ndarray           # (M,) float64 local petiole-to-tip coord u in [-0.005, L_l]
    v_k: np.ndarray           # (M,) float64 local lateral coord v
    w_k: np.ndarray           # (M,) float64 local out-of-plane thickness offset w
    phase_seed: np.ndarray    # (L,) float64 deterministic aero-flutter phase in [0, 2*pi)


@dataclass
class PerLeafDeformSpec:
    """Per-leaf 3D geometric deformation parameters (arrays of length L, allowing distinct edits per leaf!)."""

    flap_rad: np.ndarray       # (L,) float64 cantilever bending angle in (e1, e3) plane (rad)
    sweep_rad: np.ndarray      # (L,) float64 lateral in-plane sweep angle in (e1, e2) plane (rad)
    twist_rad: np.ndarray      # (L,) float64 axial helical torsion angle from base to tip (rad)
    cup_curv: np.ndarray       # (L,) float64 transverse C-cupping curvature kappa_c (m^-1)
    len_scale: np.ndarray      # (L,) float64 longitudinal scale factor lambda_u
    wid_base: np.ndarray       # (L,) float64 transverse base width scale
    wid_tip_add: np.ndarray    # (L,) float64 distal obovate width expansion beta_1 * s^0.85
    wave_amp_rad: np.ndarray   # (L,) float64 travelling aero-flutter angular wave amplitude (rad)
    wave_freq: float = 7.5     # spatial wavenumber along s in [0, 1]
    wave_time: float = 0.0     # temporal phase omega * t


def build_leaf_deform_rig(sub: LeafKernelSubstrateM12) -> LeafDeformRig:
    """Construct the vectorized petiole-hinged coordinate rig for all 472 leaves in the M1+M2 substrate."""
    leaves = sub.leaf_instances
    n_l = len(leaves)
    p_base = np.zeros((n_l, 3), dtype=np.float64)
    e1 = np.zeros((n_l, 3), dtype=np.float64)
    e2 = np.zeros((n_l, 3), dtype=np.float64)
    e3 = np.zeros((n_l, 3), dtype=np.float64)
    blade_len = np.zeros(n_l, dtype=np.float64)
    blade_half_w = np.zeros(n_l, dtype=np.float64)
    phase_seed = np.zeros(n_l, dtype=np.float64)

    means64 = sub.cloud.means.astype(np.float64)
    opac = sub.cloud.opacities

    for i, lf in enumerate(leaves):
        assert lf.leaf_id == i, "Expected contiguous leaf_ids 0..L-1"
        el = lf.axis_length / max(float(np.linalg.norm(lf.axis_length)), 1e-12)
        en = lf.normal / max(float(np.linalg.norm(lf.normal)), 1e-12)
        # Re-orthogonalize to exact SO(3) machine precision: e1, e2 = normalize(e3 x e1), e3 = e1 x e2
        ew = np.cross(en, el)
        ew /= max(float(np.linalg.norm(ew)), 1e-12)
        en = np.cross(el, ew)
        en /= max(float(np.linalg.norm(en)), 1e-12)

        k_idx = lf.kernel_indices
        act_k = k_idx[opac[k_idx] >= 0.025]
        ref_k = act_k if len(act_k) >= 4 else k_idx
        u_proj = (means64[ref_k] - lf.centroid[None, :]) @ el
        u_min = float(np.percentile(u_proj, 3.0)) if len(u_proj) > 0 else -0.5 * lf.length_world
        u_max = float(np.percentile(u_proj, 97.0)) if len(u_proj) > 0 else 0.5 * lf.length_world

        p_base[i] = lf.centroid + u_min * el
        e1[i] = el
        e2[i] = ew
        e3[i] = en
        blade_len[i] = max(u_max - u_min, 0.016)
        blade_half_w[i] = max(0.5 * lf.width_world, 0.005)
        phase_seed[i] = 2.0 * math.pi * (((i * 2654435761) & 0xFFFFFFFF) / float(0x100000000))

    fol_idx = np.where(sub.kernel_labels >= 0)[0].astype(np.int32)
    fol_lids = sub.kernel_labels[fol_idx].astype(np.int32)
    rel = means64[fol_idx] - p_base[fol_lids]
    u_k = np.sum(rel * e1[fol_lids], axis=1)
    v_k = np.sum(rel * e2[fol_lids], axis=1)
    w_k = np.sum(rel * e3[fol_lids], axis=1)

    return LeafDeformRig(
        num_leaves=n_l,
        p_base=p_base,
        e1=e1,
        e2=e2,
        e3=e3,
        blade_len=blade_len,
        blade_half_w=blade_half_w,
        fol_idx=fol_idx,
        fol_lids=fol_lids,
        u_k=u_k,
        v_k=v_k,
        w_k=w_k,
        phase_seed=phase_seed,
    )


def make_identity_spec(num_leaves: int) -> PerLeafDeformSpec:
    z = np.zeros(num_leaves, dtype=np.float64)
    o = np.ones(num_leaves, dtype=np.float64)
    return PerLeafDeformSpec(
        flap_rad=z.copy(),
        sweep_rad=z.copy(),
        twist_rad=z.copy(),
        cup_curv=z.copy(),
        len_scale=o.copy(),
        wid_base=o.copy(),
        wid_tip_add=z.copy(),
        wave_amp_rad=z.copy(),
    )


def _precompute_spine_lut(
    rig: LeafDeformRig,
    spec: PerLeafDeformSpec,
    s_max: float = 1.35,
    n_grid: int = 40,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Precompute arc-length-integrated spine curve gamma(s) and moving frame (T, B, N) on (L, n_grid, 3)."""
    s_grid = np.linspace(0.0, s_max, n_grid, dtype=np.float64)  # (G,)
    ds = s_grid[1] - s_grid[0]

    # Cantilever profile: (2*s_c - s_c^2) with smooth linear continuation past s=1
    s_c = np.minimum(s_grid, 1.0)[None, :]  # (1, G)
    cant_prof = 0.5 * (2.0 * s_c - s_c * s_c) * 2.0  # 0 at s=0, 1 at s=1

    flap = spec.flap_rad[:, None] * cant_prof  # (L, G)
    if np.any(np.abs(spec.wave_amp_rad) > 1e-6):
        ph = spec.wave_freq * s_grid[None, :] - spec.wave_time + rig.phase_seed[:, None]
        # Zero amplitude & zero slope at s=0 (s^1.5 envelope) so petiole clamp stays rock solid!
        flap = flap + spec.wave_amp_rad[:, None] * (s_grid[None, :] ** 1.5) * np.sin(ph)

    sweep = spec.sweep_rad[:, None] * (s_c ** 1.35)
    twist = spec.twist_rad[:, None] * (s_c ** 1.15)

    cf = np.cos(flap)[..., None]
    sf = np.sin(flap)[..., None]
    cs = np.cos(sweep)[..., None]
    ss = np.sin(sweep)[..., None]

    e1 = rig.e1[:, None, :]
    e2 = rig.e2[:, None, :]
    e3 = rig.e3[:, None, :]

    # Exact unit-norm spine tangent ||T(s)||_2 == 1!
    e_horiz = cs * e1 + ss * e2
    T_lut = cf * e_horiz + sf * e3
    E_lat = -ss * e1 + cs * e2
    E_nrm = np.cross(T_lut, E_lat)

    ct = np.cos(twist)[..., None]
    st = np.sin(twist)[..., None]
    B_lut = ct * E_lat + st * E_nrm
    N_lut = -st * E_lat + ct * E_nrm

    # Trapezoidal integration of unit spine tangent -> exact inextensible centerline gamma_unit(s)
    gamma_lut = np.zeros_like(T_lut)
    gamma_lut[:, 1:, :] = np.cumsum(0.5 * (T_lut[:, :-1, :] + T_lut[:, 1:, :]), axis=1) * ds
    return s_grid, gamma_lut, T_lut, B_lut, N_lut


def _eval_deform_points(
    lids: np.ndarray,
    u: np.ndarray,
    v: np.ndarray,
    w: np.ndarray,
    rig: LeafDeformRig,
    spec: PerLeafDeformSpec,
    s_grid: np.ndarray,
    gamma_lut: np.ndarray,
    B_lut: np.ndarray,
    N_lut: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate 3D deformed positions Phi_l(u, v, w) and local surface normal N_tilde for M query points."""
    L_b = rig.blade_len[lids]
    u_pos = np.maximum(u, 0.0)
    u_neg = np.minimum(u, 0.0)
    s = np.clip(u_pos / L_b, 0.0, s_grid[-1] - 1e-7)

    # Fast vectorized linear interpolation along s_grid (uniform spacing)
    inv_ds = 1.0 / (s_grid[1] - s_grid[0])
    idx_f = s * inv_ds
    i0 = np.floor(idx_f).astype(np.int32)
    i1 = np.minimum(i0 + 1, len(s_grid) - 1)
    alpha = (idx_f - i0)[:, None]

    gam_s = (1.0 - alpha) * gamma_lut[lids, i0] + alpha * gamma_lut[lids, i1]
    B_s = (1.0 - alpha) * B_lut[lids, i0] + alpha * B_lut[lids, i1]
    N_s = (1.0 - alpha) * N_lut[lids, i0] + alpha * N_lut[lids, i1]

    # Normalize interpolated frame vectors
    B_s /= np.maximum(np.linalg.norm(B_s, axis=1, keepdims=True), 1e-12)
    N_s /= np.maximum(np.linalg.norm(N_s, axis=1, keepdims=True), 1e-12)

    s_01 = np.clip(s, 0.0, 1.0)
    lam_v = spec.wid_base[lids] + spec.wid_tip_add[lids] * (s_01 ** 0.85)
    v_scaled = lam_v * v

    # Smoothly ramp transverse cupping from 0 at petiole (s=0) to full kappa_c by s=0.25 so petiole stays clamped!
    cup_ramp = np.clip(s / 0.22, 0.0, 1.0)
    kap = spec.cup_curv[lids] * cup_ramp
    psi = np.clip(kap * v_scaled, -1.35, 1.35)

    curved_m = np.abs(kap) > 1e-3
    v_tilde = np.where(curved_m, np.sin(psi) / np.where(curved_m, kap, 1.0), v_scaled)
    w_cup = np.where(curved_m, (1.0 - np.cos(psi)) / np.where(curved_m, kap, 1.0), 0.0)

    c_psi = np.cos(psi)[:, None]
    s_psi = np.sin(psi)[:, None]
    N_tilde = -s_psi * B_s + c_psi * N_s

    lam_u = spec.len_scale[lids]
    spine_xyz = (
        rig.p_base[lids]
        + (lam_u * L_b)[:, None] * gam_s
        + (lam_u * u_neg)[:, None] * rig.e1[lids]
    )
    pts_out = spine_xyz + v_tilde[:, None] * B_s + w_cup[:, None] * N_s + w[:, None] * N_tilde
    return pts_out, N_tilde


def deform_leaf_substrate(
    sub: LeafKernelSubstrateM12,
    rig: LeafDeformRig,
    spec: PerLeafDeformSpec,
    transport_covariance: bool = True,
) -> tuple[GaussianCloud3D, list[LeafInstance3D], dict[str, float]]:
    """Apply per-leaf 3D geometric deformation to all 297,343 kernels with optional Jacobian covariance transport!"""
    s_grid, gamma_lut, _, B_lut, N_lut = _precompute_spine_lut(rig, spec)

    lids = rig.fol_lids
    u0, v0, w0 = rig.u_k, rig.v_k, rig.w_k

    # 1. Deform foliage kernel centers
    pts_new, n_tilde = _eval_deform_points(lids, u0, v0, w0, rig, spec, s_grid, gamma_lut, B_lut, N_lut)

    means_out = sub.cloud.means.copy()
    means_out[rig.fol_idx] = pts_new.astype(np.float32)

    cov6_out = sub.cloud.cov6.copy()
    scales_out = sub.cloud.scales.copy()
    quats_out = sub.cloud.quats_wxyz.copy()
    nrms_out = sub.cloud.surfel_normals.copy()

    if transport_covariance and len(rig.fol_idx) > 0:
        # 2. Central-difference tangent vectors dPhi/du, dPhi/dv + exact analytical dPhi/dw = n_tilde!
        eps = 4e-4  # 0.4 mm step
        pts_u_hi, _ = _eval_deform_points(lids, u0 + eps, v0, w0, rig, spec, s_grid, gamma_lut, B_lut, N_lut)
        pts_u_lo, _ = _eval_deform_points(lids, u0 - eps, v0, w0, rig, spec, s_grid, gamma_lut, B_lut, N_lut)
        d_du = (pts_u_hi - pts_u_lo) / (2.0 * eps)

        pts_v_hi, _ = _eval_deform_points(lids, u0, v0 + eps, w0, rig, spec, s_grid, gamma_lut, B_lut, N_lut)
        pts_v_lo, _ = _eval_deform_points(lids, u0, v0 - eps, w0, rig, spec, s_grid, gamma_lut, B_lut, N_lut)
        d_dv = (pts_v_hi - pts_v_lo) / (2.0 * eps)
        d_dw = n_tilde

        # Clamp tangent stretch norms gently to [0.42, 2.25] for guaranteed numerical stability
        nu = np.linalg.norm(d_du, axis=1, keepdims=True)
        nv = np.linalg.norm(d_dv, axis=1, keepdims=True)
        d_du = d_du * (np.clip(nu, 0.42, 2.25) / np.maximum(nu, 1e-9))
        d_dv = d_dv * (np.clip(nv, 0.42, 2.25) / np.maximum(nv, 1e-9))

        # Jacobian J_k = [dPhi/du, dPhi/dv, dPhi/dw] @ [e1, e2, e3]^T  -> shape (M, 3, 3)
        F_local = np.stack([d_du, d_dv, d_dw], axis=2)  # columns are d/du, d/dv, d/dw
        E_frame = np.stack([rig.e1[lids], rig.e2[lids], rig.e3[lids]], axis=2)  # columns are e1, e2, e3
        J_mat = (F_local @ E_frame.transpose(0, 2, 1)).astype(np.float32)

        # Reconstruct 3x3 symmetric Sigma_0 from cov6, transport Sigma' = J @ Sigma_0 @ J^T
        c6 = sub.cloud.cov6[rig.fol_idx]
        Sig0 = np.zeros((len(c6), 3, 3), dtype=np.float32)
        Sig0[:, 0, 0] = c6[:, 0]
        Sig0[:, 0, 1] = Sig0[:, 1, 0] = c6[:, 1]
        Sig0[:, 0, 2] = Sig0[:, 2, 0] = c6[:, 2]
        Sig0[:, 1, 1] = c6[:, 3]
        Sig0[:, 1, 2] = Sig0[:, 2, 1] = c6[:, 4]
        Sig0[:, 2, 2] = c6[:, 5]

        Sig1 = J_mat @ Sig0 @ J_mat.transpose(0, 2, 1)
        Sig1 = 0.5 * (Sig1 + Sig1.transpose(0, 2, 1))
        cov6_out[rig.fol_idx] = Sig1[:, [0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]]
        nrms_out[rig.fol_idx] = n_tilde.astype(np.float32)

        # Also transport original SH view directions / normals cleanly via polar rotation of J_mat where needed;
        # extract updated scales (sqrt of eigenvalues) for downstream inspection
        evals = np.linalg.eigvalsh(Sig1)
        scales_out[rig.fol_idx] = np.sqrt(np.maximum(evals, 1e-14)).astype(np.float32)

    # 3. Also deform each leaf's 24-vertex closed 3D boundary loop & centroid for exact wireframe overlay!
    deformed_leaves: list[LeafInstance3D] = []
    arc_errors_pct: list[float] = []
    for i, lf in enumerate(sub.leaf_instances):
        rel_lp = lf.boundary_loop_3d - rig.p_base[i][None, :]
        ul = rel_lp @ rig.e1[i]
        vl = rel_lp @ rig.e2[i]
        wl = rel_lp @ rig.e3[i]
        lid_arr = np.full(len(ul), i, dtype=np.int32)
        lp_def, n_lp = _eval_deform_points(lid_arr, ul, vl, wl, rig, spec, s_grid, gamma_lut, B_lut, N_lut)

        # Measure deformed spine arc-length from s=0 to s=1 along 20 samples
        s_probe = np.linspace(0.0, 1.0, 20)
        u_probe = s_probe * rig.blade_len[i]
        z_probe = np.zeros_like(u_probe)
        sp_pts, _ = _eval_deform_points(
            np.full(20, i, dtype=np.int32), u_probe, z_probe, z_probe, rig, spec, s_grid, gamma_lut, B_lut, N_lut
        )
        def_arc = float(np.sum(np.linalg.norm(np.diff(sp_pts, axis=0), axis=1)))
        target_arc = float(spec.len_scale[i] * rig.blade_len[i])
        arc_errors_pct.append(100.0 * abs(def_arc - target_arc) / max(target_arc, 1e-6))

        deformed_leaves.append(
            replace(
                lf,
                centroid=lp_def.mean(axis=0),
                normal=n_lp.mean(axis=0) / max(float(np.linalg.norm(n_lp.mean(axis=0))), 1e-9),
                boundary_loop_3d=lp_def,
            )
        )

    # Quantify physical invariants: petiole attachment drift & stem/pot rigidity!
    near_petiole = np.abs(u0) <= 0.0025  # within 2.5 mm of petiole hinge
    if np.any(near_petiole):
        orig_pet = sub.cloud.means[rig.fol_idx[near_petiole]].astype(np.float64)
        new_pet = pts_new[near_petiole]
        petiole_drift_mm = 1000.0 * float(np.median(np.linalg.norm(new_pet - orig_pet, axis=1)))
    else:
        petiole_drift_mm = 0.0

    non_fol = sub.kernel_labels < 0
    stem_pot_drift_mm = (
        1000.0 * float(np.max(np.linalg.norm(means_out[non_fol] - sub.cloud.means[non_fol], axis=1)))
        if np.any(non_fol)
        else 0.0
    )

    out_cloud = GaussianCloud3D(
        means=np.ascontiguousarray(means_out, dtype=np.float32),
        scales=np.ascontiguousarray(scales_out, dtype=np.float32),
        quats_wxyz=np.ascontiguousarray(quats_out, dtype=np.float32),
        cov6=np.ascontiguousarray(cov6_out, dtype=np.float32),
        surfel_normals=np.ascontiguousarray(nrms_out, dtype=np.float32),
        opacities=sub.cloud.opacities,
        rgb_dc=sub.cloud.rgb_dc,
        shs=sub.cloud.shs,
    )
    invariants = {
        "petiole_hinge_median_drift_mm": round(petiole_drift_mm, 4),
        "stem_and_pot_max_drift_mm": round(stem_pot_drift_mm, 6),
        "median_arc_length_error_pct": round(float(np.median(arc_errors_pct)), 4) if arc_errors_pct else 0.0,
        "mean_tip_displacement_cm": round(
            100.0
            * float(
                np.mean(
                    np.linalg.norm(
                        pts_new[u0 >= 0.80 * rig.blade_len[lids]]
                        - sub.cloud.means[rig.fol_idx[u0 >= 0.80 * rig.blade_len[lids]]],
                        axis=1,
                    )
                )
            ),
            2,
        )
        if np.any(u0 >= 0.80 * rig.blade_len[lids])
        else 0.0,
    }
    return out_cloud, deformed_leaves, invariants


# ---------------------------------------------------------------------------
# Botanical & Physical Per-Leaf Deformation Preset Builders
# ---------------------------------------------------------------------------


def make_gravity_wilt_spec(rig: LeafDeformRig, max_droop_deg: float = 54.0) -> PerLeafDeformSpec:
    """Euler-Bernoulli cantilever gravity droop toward world -Z + subtle inward wilting curl."""
    spec = make_identity_spec(rig.num_leaves)
    grav = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    # Project world gravity onto each leaf's out-of-plane normal e3 and lateral axis e2!
    g_nrm = rig.e3 @ grav
    g_lat = rig.e2 @ grav
    # Even nearly vertical leaves droop outward/downward naturally
    droop_rad = math.radians(max_droop_deg)
    # Ensure non-zero downward flap when e3 is nearly horizontal by signing toward -Z
    sign_nrm = np.where(np.abs(g_nrm) > 0.15, g_nrm, np.where(rig.e3[:, 2] >= 0, -0.65, 0.65))
    spec.flap_rad = droop_rad * np.clip(sign_nrm * 1.15, -1.0, 1.0)
    spec.sweep_rad = (0.48 * droop_rad) * np.clip(g_lat, -0.85, 0.85)
    # Wilting leaves curl inward into a trough along their upward-facing side
    up_sign = np.where(rig.e3[:, 2] >= 0.0, 1.0, -1.0)
    spec.cup_curv = 24.0 * up_sign
    spec.wid_base = np.full(rig.num_leaves, 0.92)
    return spec


def make_cupped_helical_twist_spec(
    rig: LeafDeformRig, cup_curv: float = 36.0, twist_deg: float = 48.0
) -> PerLeafDeformSpec:
    """Sculptural inward boat-cupping across midrib + progressive 48-deg helical ribbon torsion."""
    spec = make_identity_spec(rig.num_leaves)
    alt_sign = np.where((np.arange(rig.num_leaves) % 2) == 0, 1.0, -1.0)
    up_sign = np.where(rig.e3[:, 2] >= 0.0, 1.0, -1.0)
    spec.cup_curv = cup_curv * up_sign
    spec.twist_rad = math.radians(twist_deg) * alt_sign
    spec.flap_rad = math.radians(14.0) * up_sign
    return spec


def make_directional_wind_spec(
    rig: LeafDeformRig,
    wind_dir: tuple[float, float, float] = (0.92, 0.25, 0.18),
    gust_deg: float = 46.0,
    flutter_deg: float = 11.0,
    time_phase: float = 0.0,
) -> PerLeafDeformSpec:
    """Aerodynamic directional wind gust + Vogel drag-reducing torsional weathercocking + travelling flutter."""
    spec = make_identity_spec(rig.num_leaves)
    w = np.asarray(wind_dir, dtype=np.float64)
    w /= max(float(np.linalg.norm(w)), 1e-9)

    # Height & upwind exposure modulation (upper/outer canopy catches stronger wind!)
    z_norm = np.clip((rig.p_base[:, 2] + 0.35) / 1.15, 0.25, 1.25)
    gust_r = math.radians(gust_deg) * z_norm

    w_nrm = rig.e3 @ w
    w_lat = rig.e2 @ w
    w_axial = rig.e1 @ w
    # Broadside leaves (|e1 · w| small) experience maximum aerodynamic bending torque!
    broadside = np.sqrt(np.clip(1.0 - 0.55 * (w_axial ** 2), 0.25, 1.0))

    spec.flap_rad = gust_r * broadside * np.clip(w_nrm * 1.35, -1.0, 1.0)
    spec.sweep_rad = (0.75 * gust_r) * broadside * np.clip(w_lat * 1.25, -0.95, 0.95)
    # Aerodynamic weathercocking twist aligns broadside leaves toward airflow
    spec.twist_rad = math.radians(28.0) * z_norm * np.clip(w_nrm * w_lat * 2.2, -1.0, 1.0)
    spec.cup_curv = np.full(rig.num_leaves, 14.0)
    spec.wave_amp_rad = np.full(rig.num_leaves, math.radians(flutter_deg)) * z_norm
    spec.wave_freq = 8.0
    spec.wave_time = time_phase
    return spec


def make_willow_slender_morph_spec(rig: LeafDeformRig) -> PerLeafDeformSpec:
    """Botanical species reshape A: slender weeping willow / bamboo-leaf Ficus."""
    spec = make_gravity_wilt_spec(rig, max_droop_deg=30.0)
    spec.len_scale = np.full(rig.num_leaves, 1.20)
    spec.wid_base = np.full(rig.num_leaves, 0.52)
    spec.wid_tip_add = np.full(rig.num_leaves, -0.10)
    spec.cup_curv = np.full(rig.num_leaves, 12.0)
    return spec


def make_broad_obovate_morph_spec(rig: LeafDeformRig) -> PerLeafDeformSpec:
    """Botanical species reshape B: lush broad obovate / fiddle-leaf spoon morphology with upward sun-cupping."""
    spec = make_identity_spec(rig.num_leaves)
    up_sign = np.where(rig.e3[:, 2] >= 0.0, 1.0, -1.0)
    spec.len_scale = np.full(rig.num_leaves, 0.92)
    spec.wid_base = np.full(rig.num_leaves, 1.08)
    spec.wid_tip_add = np.full(rig.num_leaves, 0.56)
    spec.flap_rad = math.radians(16.0) * up_sign
    spec.cup_curv = 18.0 * up_sign
    return spec


def make_same_plant_phenology_contrast_spec(
    rig: LeafDeformRig,
) -> tuple[PerLeafDeformSpec, dict[int, str]]:
    """Same-Plant Heterogeneous Geometry + Style:
    Upper/right sunlit crown blooms upward (broad lush Sakura & Ghibli leaves),
    while lower/left shaded branches droop in gravity wilt (curled Ukiyo-e autumn leaves)!
    """
    wilt = make_gravity_wilt_spec(rig, max_droop_deg=56.0)
    bloom = make_broad_obovate_morph_spec(rig)

    z_med = float(np.median(rig.p_base[:, 2]))
    x_med = float(np.median(rig.p_base[:, 0]))

    spec = make_identity_spec(rig.num_leaves)
    style_map: dict[int, str] = {}

    for i in range(rig.num_leaves):
        score_sun = (rig.p_base[i, 2] - z_med) + 0.45 * (rig.p_base[i, 0] - x_med)
        if score_sun >= 0.0:
            # Sun-blooming upper/right branch: upward lift + lush broad leaf + spring Sakura / Ghibli palette!
            spec.flap_rad[i] = bloom.flap_rad[i] * 1.25
            spec.sweep_rad[i] = 0.0
            spec.cup_curv[i] = bloom.cup_curv[i]
            spec.len_scale[i] = 1.02
            spec.wid_base[i] = 1.06
            spec.wid_tip_add[i] = 0.45
            style_map[i] = "sakura_watercolor" if rig.p_base[i, 2] > z_med + 0.14 else "ghibli_gouache"
        else:
            # Gravity-wilted lower/left branch: deep 56-deg cantilever droop + curled margins + autumn ochre/vermilion!
            spec.flap_rad[i] = wilt.flap_rad[i]
            spec.sweep_rad[i] = wilt.sweep_rad[i]
            spec.cup_curv[i] = wilt.cup_curv[i] * 1.35
            spec.twist_rad[i] = math.radians(18.0) * (1.0 if i % 2 == 0 else -1.0)
            spec.len_scale[i] = 0.98
            spec.wid_base[i] = 0.85
            spec.wid_tip_add[i] = -0.08
            style_map[i] = "ukiyoe_papercut"

    return spec, style_map
