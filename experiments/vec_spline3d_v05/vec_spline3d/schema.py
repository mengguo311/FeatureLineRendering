"""Vectorized 3D parametric curve, Darboux ribbon, coaxial ring, and view-dependent occluding contour schema (v04)."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
from scipy.interpolate import BSpline

DEFAULT_ALLOWED_ROOTS: tuple[Path, ...] = (
    Path("/mnt/hdd1/u00134/radegs_paper_reproduction_v01").resolve(),
    Path("/home/u00134/cglib/data/full").resolve(),
    Path("/home/u00134/3dgs_line").resolve(),
    Path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01").resolve(),
    Path("/home/u00134/.gemini/antigravity/brain/879bd51a-3371-416f-9545-fc0432c7b4ee").resolve(),
)


def resolve_safe_path(path: str | Path, allowed_roots: Iterable[Path] = DEFAULT_ALLOWED_ROOTS) -> Path:
    """Resolve a path and enforce strict directory boundary containment."""
    resolved = Path(path).resolve()
    for root in allowed_roots:
        root_res = root.resolve()
        if resolved == root_res or resolved.is_relative_to(root_res):
            return resolved
    raise ValueError(f"Path '{resolved}' is outside allowed directory boundaries.")


def clamped_uniform_knots(num_ctrl: int, degree: int) -> np.ndarray:
    """Construct a clamped uniform knot vector on [0, 1] for M control points and degree p."""
    if num_ctrl < degree + 1:
        raise ValueError(f"num_ctrl ({num_ctrl}) must be >= degree + 1 ({degree + 1})")
    num_internal = num_ctrl - degree - 1
    if num_internal == 0:
        internal = np.empty(0, dtype=np.float64)
    else:
        internal = np.linspace(0.0, 1.0, num_internal + 2, dtype=np.float64)[1:-1]
    return np.concatenate([
        np.zeros(degree + 1, dtype=np.float64),
        internal,
        np.ones(degree + 1, dtype=np.float64),
    ])


def bspline_basis_matrices(
    num_ctrl: int,
    u_samples: np.ndarray,
    degree: int | None = None,
    knots: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    """Compute exact B-spline evaluation and 1st/2nd derivative matrices (S, M) on [0, 1]."""
    u = np.clip(np.asarray(u_samples, dtype=np.float64), 0.0, 1.0)
    if degree is None:
        degree = 1 if num_ctrl == 2 else min(3, num_ctrl - 1)
    if knots is None:
        knots = clamped_uniform_knots(num_ctrl, degree)
    else:
        knots = np.asarray(knots, dtype=np.float64)

    eye = np.eye(num_ctrl, dtype=np.float64)
    spl = BSpline(knots, eye, degree, extrapolate=False)
    B = spl(u)
    B_du = spl.derivative(1)(u) if degree >= 1 else np.zeros_like(B)
    B_d2u = spl.derivative(2)(u) if degree >= 2 else np.zeros_like(B)
    return B, B_du, B_d2u, knots, degree


def circular_arc_geometry_from_3pt(
    p0: np.ndarray, pm: np.ndarray, p1: np.ndarray
) -> dict[str, Any]:
    """Derive exact 3D circle (center, normal, e1, e2, radius, sweep_rad) passing through p0 -> pm -> p1."""
    p0 = np.asarray(p0, dtype=np.float64)
    pm = np.asarray(pm, dtype=np.float64)
    p1 = np.asarray(p1, dtype=np.float64)
    a = pm - p0
    b = p1 - p0
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    w = np.cross(a, b)
    nw = float(np.linalg.norm(w))

    if na < 1e-10 or nb < 1e-10 or nw / max(na * nb, 1e-15) < 1e-3:
        return {"is_collinear": True, "center": 0.5 * (p0 + p1), "normal": np.array([0.0, 0.0, 1.0]), "radius": np.inf, "sweep_rad": 0.0}

    center = p0 + np.cross((na * na) * b - (nb * nb) * a, w) / (2.0 * nw * nw)
    r0_vec = p0 - center
    rm_vec = pm - center
    r1_vec = p1 - center
    radius = float(np.linalg.norm(r0_vec))
    if radius < 1e-10 or radius > 1e5:
        return {"is_collinear": True, "center": 0.5 * (p0 + p1), "normal": np.array([0.0, 0.0, 1.0]), "radius": np.inf, "sweep_rad": 0.0}

    e1 = r0_vec / radius
    rm_u = rm_vec / max(float(np.linalg.norm(rm_vec)), 1e-12)
    r1_u = r1_vec / max(float(np.linalg.norm(r1_vec)), 1e-12)

    n_arc = np.cross(e1, rm_u)
    n_len = float(np.linalg.norm(n_arc))
    if n_len < 1e-8:
        return {"is_collinear": True, "center": 0.5 * (p0 + p1), "normal": np.array([0.0, 0.0, 1.0]), "radius": np.inf, "sweep_rad": 0.0}
    n_arc /= n_len
    e2 = np.cross(n_arc, e1)

    sweep = math.atan2(float(np.dot(r1_u, e2)), float(np.dot(r1_u, e1)))
    if sweep <= 0.0:
        sweep += 2.0 * math.pi
    return {
        "is_collinear": False,
        "center": center,
        "normal": n_arc,
        "e1": e1,
        "e2": e2,
        "radius": radius,
        "sweep_rad": float(sweep),
    }


def evaluate_circular_arc_3pt_numpy(
    ctrl_3x3: np.ndarray, u_samples: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate exact 3D circular arc (points, d1, d2) defined by (P0, Pmid, P1) at u in [0, 1]."""
    u = np.clip(np.asarray(u_samples, dtype=np.float64), 0.0, 1.0)
    p0, pm, p1 = ctrl_3x3[0], ctrl_3x3[1], ctrl_3x3[2]
    geom = circular_arc_geometry_from_3pt(p0, pm, p1)
    if geom["is_collinear"]:
        q1 = 2.0 * pm - 0.5 * (p0 + p1)
        omu = 1.0 - u
        pts = (omu ** 2)[:, None] * p0 + (2.0 * omu * u)[:, None] * q1 + (u ** 2)[:, None] * p1
        d1 = (2.0 * omu)[:, None] * (q1 - p0) + (2.0 * u)[:, None] * (p1 - q1)
        d2 = np.repeat((2.0 * (p0 - 2.0 * q1 + p1))[None, :], len(u), axis=0)
        return pts, d1, d2

    c = geom["center"]
    e1 = geom["e1"]
    e2 = geom["e2"]
    r = geom["radius"]
    sw = geom["sweep_rad"]
    theta = u * sw
    ct = np.cos(theta)[:, None]
    st = np.sin(theta)[:, None]
    pts = c[None, :] + r * (ct * e1[None, :] + st * e2[None, :])
    d1 = (r * sw) * (-st * e1[None, :] + ct * e2[None, :])
    d2 = -(r * sw * sw) * (ct * e1[None, :] + st * e2[None, :])
    return pts, d1, d2


def evaluate_circular_arc_3pt_torch(
    p0: torch.Tensor, pm: torch.Tensor, p1: torch.Tensor, u_grid: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor]:
    """Batched differentiable PyTorch evaluation of A circular arcs (A,3) x S samples -> (A*S, 3) pts & tangents."""
    a = pm - p0
    b = p1 - p0
    na_sq = (a * a).sum(dim=-1, keepdim=True)
    nb_sq = (b * b).sum(dim=-1, keepdim=True)
    w = torch.linalg.cross(a, b, dim=-1)
    nw_sq = (w * w).sum(dim=-1, keepdim=True)
    sin_ang = torch.sqrt(nw_sq.clamp(min=1e-18)) / torch.sqrt((na_sq * nb_sq).clamp(min=1e-18))

    safe_denom = (2.0 * nw_sq).clamp(min=1e-12)
    center = p0 + torch.linalg.cross(na_sq * b - nb_sq * a, w, dim=-1) / safe_denom
    r0_vec = p0 - center
    rm_vec = pm - center
    r1_vec = p1 - center
    radius = torch.linalg.norm(r0_vec, dim=-1, keepdim=True).clamp(min=1e-6, max=1e3)

    e1 = r0_vec / radius
    rm_u = rm_vec / torch.linalg.norm(rm_vec, dim=-1, keepdim=True).clamp(min=1e-8)
    r1_u = r1_vec / torch.linalg.norm(r1_vec, dim=-1, keepdim=True).clamp(min=1e-8)

    n_raw = torch.linalg.cross(e1, rm_u, dim=-1)
    n_arc = n_raw / torch.linalg.norm(n_raw, dim=-1, keepdim=True).clamp(min=1e-8)
    e2 = torch.linalg.cross(n_arc, e1, dim=-1)

    y_arg = (r1_u * e2).sum(dim=-1, keepdim=True)
    x_arg = (r1_u * e1).sum(dim=-1, keepdim=True)
    sweep = torch.atan2(y_arg, x_arg)
    sweep = torch.where(sweep <= 0.0, sweep + 2.0 * math.pi, sweep)

    u = u_grid[None, :, None]
    theta = u * sweep[:, None, :]
    ct = torch.cos(theta)
    st = torch.sin(theta)

    pts_arc = center[:, None, :] + radius[:, None, :] * (ct * e1[:, None, :] + st * e2[:, None, :])
    d1_arc = (radius * sweep)[:, None, :] * (-st * e1[:, None, :] + ct * e2[:, None, :])

    q1 = 2.0 * pm - 0.5 * (p0 + p1)
    omu = 1.0 - u
    pts_quad = (omu ** 2) * p0[:, None, :] + (2.0 * omu * u) * q1[:, None, :] + (u ** 2) * p1[:, None, :]
    d1_quad = (2.0 * omu) * (q1 - p0)[:, None, :] + (2.0 * u) * (p1 - q1)[:, None, :]

    use_arc = (sin_ang[:, None, :] >= 0.015) & (radius[:, None, :] < 50.0)
    pts = torch.where(use_arc, pts_arc, pts_quad).reshape(-1, 3)
    d1 = torch.where(use_arc, d1_arc, d1_quad).reshape(-1, 3)
    return pts, d1


def fit_circular_arc_to_polyline(
    points: np.ndarray, pin_endpoints: bool = False
) -> tuple[np.ndarray, float, dict[str, Any]]:
    """Fit a 3D circular arc (P0, Pmid, P1) to an ordered 3D polyline via PCA plane + Kåsa algebraic fit."""
    pts = np.asarray(points, dtype=np.float64)
    n = len(pts)
    if n < 3:
        mid = 0.5 * (pts[0] + pts[-1])
        return np.vstack([pts[0], mid, pts[-1]]), 1e9, {"valid": False}

    centroid = pts.mean(axis=0)
    centered = pts - centroid
    _, s_vals, vt = np.linalg.svd(centered, full_matrices=False)
    if len(vt) < 3 or s_vals[1] < 1e-9:
        mid = 0.5 * (pts[0] + pts[-1])
        return np.vstack([pts[0], mid, pts[-1]]), 1e9, {"valid": False}

    u_ax, v_ax, n_ax = vt[0], vt[1], vt[2]
    plane_err = float(np.max(np.abs(centered @ n_ax)))

    xy = np.column_stack([centered @ u_ax, centered @ v_ax])
    A_kasa = np.column_stack([2.0 * xy[:, 0], 2.0 * xy[:, 1], np.ones(n, dtype=np.float64)])
    rhs_kasa = xy[:, 0] ** 2 + xy[:, 1] ** 2
    sol, _, rank, _ = np.linalg.lstsq(A_kasa, rhs_kasa, rcond=None)
    if rank < 3:
        mid = 0.5 * (pts[0] + pts[-1])
        return np.vstack([pts[0], mid, pts[-1]]), 1e9, {"valid": False}

    cx_2d, cy_2d, c0 = float(sol[0]), float(sol[1]), float(sol[2])
    r_sq = c0 + cx_2d * cx_2d + cy_2d * cy_2d
    if r_sq <= 1e-12 or r_sq > 1e4:
        mid = 0.5 * (pts[0] + pts[-1])
        return np.vstack([pts[0], mid, pts[-1]]), 1e9, {"valid": False}
    radius = math.sqrt(r_sq)

    for _ in range(2):
        dx = xy[:, 0] - cx_2d
        dy = xy[:, 1] - cy_2d
        dist = np.hypot(dx, dy)
        if np.any(dist < 1e-9):
            break
        res = dist - radius
        J = np.column_stack([-dx / dist, -dy / dist, -np.ones(n)])
        step, _, _, _ = np.linalg.lstsq(J, -res, rcond=None)
        cx_2d += float(step[0])
        cy_2d += float(step[1])
        radius = max(1e-6, radius + float(step[2]))

    ang = np.arctan2(xy[:, 1] - cy_2d, xy[:, 0] - cx_2d)
    ang_unwrapped = np.unwrap(ang)
    th0, th1 = float(ang_unwrapped[0]), float(ang_unwrapped[-1])
    sweep_signed = th1 - th0
    sweep_abs = abs(sweep_signed)

    if sweep_abs < math.radians(8.0) or sweep_abs > math.radians(352.0):
        mid = 0.5 * (pts[0] + pts[-1])
        return np.vstack([pts[0], mid, pts[-1]]), 1e9, {"valid": False}

    c_3d = centroid + cx_2d * u_ax + cy_2d * v_ax
    th_mid = 0.5 * (th0 + th1)

    def pt_at(th: float) -> np.ndarray:
        return c_3d + radius * (math.cos(th) * u_ax + math.sin(th) * v_ax)

    p0_fit = pts[0].copy() if pin_endpoints else pt_at(th0)
    pm_fit = pt_at(th_mid)
    p1_fit = pts[-1].copy() if pin_endpoints else pt_at(th1)
    ctrl_3x3 = np.vstack([p0_fit, pm_fit, p1_fit])

    geom_chk = circular_arc_geometry_from_3pt(p0_fit, pm_fit, p1_fit)
    if geom_chk["is_collinear"]:
        dense_arc, _, _ = evaluate_circular_arc_3pt_numpy(ctrl_3x3, np.linspace(0.0, 1.0, 64))
        dists_to_arc = np.min(np.linalg.norm(pts[:, None, :] - dense_arc[None, :, :], axis=-1), axis=1)
    else:
        rel_q = pts - geom_chk["center"][None, :]
        z_oop = rel_q @ geom_chk["normal"]
        x_ip = rel_q @ geom_chk["e1"]
        y_ip = rel_q @ geom_chk["e2"]
        rho = np.hypot(x_ip, y_ip)
        phi = np.mod(np.arctan2(y_ip, x_ip), 2.0 * math.pi)
        in_span = phi <= geom_chk["sweep_rad"] + 1e-9
        d_interior = np.hypot(rho - geom_chk["radius"], z_oop)
        d_ends = np.minimum(
            np.linalg.norm(pts - p0_fit[None, :], axis=1),
            np.linalg.norm(pts - p1_fit[None, :], axis=1),
        )
        dists_to_arc = np.where(in_span, d_interior, d_ends)
    max_err = float(np.max(dists_to_arc))

    orient_sign = 1.0 if sweep_signed >= 0 else -1.0
    return ctrl_3x3, max_err, {
        "valid": True,
        "center": c_3d,
        "normal": n_ax * orient_sign,
        "radius": float(radius),
        "sweep_rad": float(sweep_abs),
        "plane_err": plane_err,
    }


def fit_clamped_bspline_to_polyline(
    points: np.ndarray,
    num_ctrl: int,
    reg_smooth: float = 1e-3,
    pin_endpoints: bool = True,
) -> tuple[np.ndarray, np.ndarray, int, float]:
    """Fit a clamped B-spline (or line if num_ctrl==2) to an ordered 3D point chain."""
    pts = np.asarray(points, dtype=np.float64)
    n = len(pts)
    if n < 2:
        raise ValueError("Need at least 2 points to fit a curve.")

    diffs = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(diffs)])
    total_len = float(cum[-1])
    if total_len < 1e-12:
        ctrl = np.repeat(pts[:1], 2, axis=0)
        knots = clamped_uniform_knots(2, 1)
        return ctrl, knots, 1, 0.0

    u = cum / total_len
    num_ctrl = max(2, min(num_ctrl, n))
    degree = 1 if num_ctrl == 2 else min(3, num_ctrl - 1)
    knots = clamped_uniform_knots(num_ctrl, degree)

    if num_ctrl == 2:
        ctrl = np.vstack([pts[0], pts[-1]])
        pred = (1.0 - u)[:, None] * ctrl[0] + u[:, None] * ctrl[1]
        max_err = float(np.linalg.norm(pred - pts, axis=1).max())
        return ctrl, knots, 1, max_err

    B, _, _, _, _ = bspline_basis_matrices(num_ctrl, u, degree=degree, knots=knots)
    D2 = np.diff(np.eye(num_ctrl, dtype=np.float64), n=2, axis=0)

    if pin_endpoints and num_ctrl > 2:
        p0, p1 = pts[0], pts[-1]
        rhs_pts = pts - B[:, :1] @ p0[None, :] - B[:, -1:] @ p1[None, :]
        B_in = B[:, 1:-1]
        D2_in = D2[:, 1:-1]
        D2_rhs = -(D2[:, :1] @ p0[None, :] + D2[:, -1:] @ p1[None, :])
        lhs = B_in.T @ B_in + reg_smooth * (D2_in.T @ D2_in) + 1e-9 * np.eye(num_ctrl - 2)
        rhs = B_in.T @ rhs_pts + reg_smooth * (D2_in.T @ D2_rhs)
        ctrl_in = np.linalg.solve(lhs, rhs)
        ctrl = np.vstack([p0[None, :], ctrl_in, p1[None, :]])
    else:
        lhs = B.T @ B + reg_smooth * (D2.T @ D2) + 1e-9 * np.eye(num_ctrl)
        rhs = B.T @ pts
        ctrl = np.linalg.solve(lhs, rhs)

    pred = B @ ctrl
    max_err = float(np.linalg.norm(pred - pts, axis=1).max())
    return ctrl, knots, degree, max_err


@dataclass
class CoaxialRingFamilySpec:
    """Explicit rotational symmetry prior & coaxial circle/arc family on a surface of revolution."""

    family_id: int
    axis_origin: np.ndarray
    axis_dir: np.ndarray
    e1: np.ndarray
    e2: np.ndarray
    h_min: float
    h_max: float
    profile_h: np.ndarray
    profile_r: np.ndarray
    ring_heights: list[float] = field(default_factory=list)
    ring_radii: list[float] = field(default_factory=list)
    member_curve_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": int(self.family_id),
            "axis_origin": [float(x) for x in self.axis_origin],
            "axis_dir": [float(x) for x in self.axis_dir],
            "h_range": [float(self.h_min), float(self.h_max)],
            "num_coaxial_rings": len(self.ring_heights),
            "ring_heights": [round(float(h), 5) for h in self.ring_heights],
            "ring_radii": [round(float(r), 5) for r in self.ring_radii],
            "member_curve_ids": [int(c) for c in self.member_curve_ids],
        }


@dataclass
class LatheEnvelopeGenerator:
    """Exact perspective occluding contour generator on a smooth 3D surface of revolution."""

    generator_id: int
    axis_origin: np.ndarray  # (3,)
    axis_dir: np.ndarray     # (3,) unit axis vector a
    e1: np.ndarray           # (3,)
    e2: np.ndarray           # (3,)
    profile_h: np.ndarray    # (P,) axial heights from foot to mouth
    profile_r: np.ndarray    # (P,) outer silhouette envelope radius rho(h)
    pixel_scale: float = 0.0035
    half_width_px: float = 0.40
    thickness_px: float = 0.30
    inward_shift_px: float = 0.28
    opacity: float = 0.145
    supporting_views: list[str] = field(default_factory=list)

    def evaluate_horizon_curves(
        self, camera_center: np.ndarray, num_samples: int = 64
    ) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Return exact perspective horizon branches [(pts, T_unit, B_unit, N_outward_unit)] for camera_center."""
        cam = np.asarray(camera_center, dtype=np.float64)
        rel_c = cam - self.axis_origin
        hc = float(np.dot(rel_c, self.axis_dir))
        cx = float(np.dot(rel_c, self.e1))
        cy = float(np.dot(rel_c, self.e2))
        dc = math.hypot(cx, cy)
        if dc <= float(np.max(self.profile_r)) * 1.02:
            return []
        phic = math.atan2(cy, cx)

        h_s = np.linspace(float(self.profile_h[0]), float(self.profile_h[-1]), max(8, num_samples), dtype=np.float64)
        r_s = np.interp(h_s, self.profile_h, self.profile_r)
        dr_dh = np.gradient(r_s, h_s)

        # Exact perspective horizon condition: N(h, theta) · (O_cam - X(h, theta)) = 0
        cos_arg = (r_s + dr_dh * (hc - h_s)) / dc
        valid = np.abs(cos_arg) <= 0.9995
        if int(valid.sum()) < 2:
            return []

        out_branches: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
        # Extract contiguous valid runs along h
        idx = 0
        n = len(h_s)
        while idx < n:
            if not valid[idx]:
                idx += 1
                continue
            r_start = idx
            while idx < n and valid[idx]:
                idx += 1
            if idx - r_start >= 2:
                sl = slice(r_start, idx)
                ang = np.arccos(np.clip(cos_arg[sl], -1.0, 1.0))
                for sgn in (1.0, -1.0):
                    th = phic + sgn * ang
                    er = np.cos(th)[:, None] * self.e1[None, :] + np.sin(th)[:, None] * self.e2[None, :]
                    pts = self.axis_origin[None, :] + h_s[sl, None] * self.axis_dir[None, :] + r_s[sl, None] * er
                    n_raw = er - dr_dh[sl, None] * self.axis_dir[None, :]
                    n_out = n_raw / np.maximum(np.linalg.norm(n_raw, axis=1, keepdims=True), 1e-9)

                    t_raw = np.gradient(pts, axis=0)
                    t_u = t_raw / np.maximum(np.linalg.norm(t_raw, axis=1, keepdims=True), 1e-9)
                    # Orthonormalize N against T and compute B = N x T
                    n_orth = n_out - np.sum(n_out * t_u, axis=1, keepdims=True) * t_u
                    n_u = n_orth / np.maximum(np.linalg.norm(n_orth, axis=1, keepdims=True), 1e-9)
                    b_u = np.cross(n_u, t_u)
                    b_u /= np.maximum(np.linalg.norm(b_u, axis=1, keepdims=True), 1e-9)
                    out_branches.append((pts, t_u, b_u, n_u))
        return out_branches

    def is_segment_occluded_by_solid(self, cam_center: np.ndarray, target_pts: np.ndarray) -> np.ndarray:
        """Test if rays from cam_center to target_pts pass through the opaque solid vessel interior."""
        t_steps = np.linspace(0.15, 0.94, 14, dtype=np.float64)[None, :, None]
        seg_pts = cam_center[None, None, :] + t_steps * (target_pts[:, None, :] - cam_center[None, None, :])
        rel = seg_pts - self.axis_origin[None, None, :]
        h = np.sum(rel * self.axis_dir[None, None, :], axis=-1)
        xp = np.sum(rel * self.e1[None, None, :], axis=-1)
        yp = np.sum(rel * self.e2[None, None, :], axis=-1)
        rho = np.hypot(xp, yp)
        h_lo = float(self.profile_h[0])
        h_hi = float(self.profile_h[-1]) - 1.5 * self.pixel_scale
        r_shell = np.interp(np.clip(h, h_lo, h_hi), self.profile_h, self.profile_r)
        hit = (h >= h_lo) & (h <= h_hi) & (rho < r_shell - 1.5 * self.pixel_scale)
        return np.any(hit, axis=1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generator_id": int(self.generator_id),
            "generator_type": "LATHE_ENVELOPE_3D",
            "axis_origin": [float(x) for x in self.axis_origin],
            "axis_dir": [float(x) for x in self.axis_dir],
            "profile_h": [round(float(x), 5) for x in self.profile_h],
            "profile_r": [round(float(x), 5) for x in self.profile_r],
            "half_width_px": round(float(self.half_width_px), 4),
            "inward_shift_px": round(float(self.inward_shift_px), 4),
            "num_supporting_views": len(self.supporting_views),
        }


@dataclass
class SweptTubeGenerator:
    """View-dependent occluding contour generator on a curved generalized cylinder (wooden trunk / main stem)."""

    generator_id: int
    spine_control_points: np.ndarray  # (M, 3) B-spline spine control points
    control_radii: np.ndarray         # (M,) B-spline cross-sectional radii
    knots: np.ndarray
    degree: int
    pixel_scale: float = 0.0035
    half_width_px: float = 0.38
    thickness_px: float = 0.28
    inward_shift_px: float = 0.22
    opacity: float = 0.135
    supporting_views: list[str] = field(default_factory=list)

    def evaluate_horizon_curves(
        self,
        camera_center: np.ndarray,
        num_samples: int = 32,
        occluding_lathe: LatheEnvelopeGenerator | None = None,
    ) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Return exact left & right perspective horizon branches [(pts, T_unit, B_unit, N_outward_unit)]."""
        cam = np.asarray(camera_center, dtype=np.float64)
        u = np.linspace(0.0, 1.0, max(6, num_samples), dtype=np.float64)
        B_mat, B_du, _, _, _ = bspline_basis_matrices(
            len(self.spine_control_points), u, degree=self.degree, knots=self.knots
        )
        sp_pts = B_mat @ self.spine_control_points
        sp_d1 = B_du @ self.spine_control_points
        T_s = sp_d1 / np.maximum(np.linalg.norm(sp_d1, axis=1, keepdims=True), 1e-9)
        r_s = np.maximum(B_mat @ self.control_radii, 1e-4)

        v_vec = cam[None, :] - sp_pts
        v_perp = v_vec - np.sum(v_vec * T_s, axis=1, keepdims=True) * T_s
        d_perp = np.linalg.norm(v_perp, axis=1, keepdims=True)
        if np.any(d_perp[:, 0] <= r_s * 1.05):
            return []
        v_hat = v_perp / np.maximum(d_perp, 1e-9)
        w_hat = np.cross(T_s, v_hat)
        w_hat /= np.maximum(np.linalg.norm(w_hat, axis=1, keepdims=True), 1e-9)

        cos_a = np.clip(r_s[:, None] / d_perp, 0.0, 0.99)
        sin_a = np.sqrt(np.maximum(1.0 - cos_a * cos_a, 1e-8))

        branches: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
        for sgn in (1.0, -1.0):
            n_out = cos_a * v_hat + sgn * sin_a * w_hat
            n_out /= np.maximum(np.linalg.norm(n_out, axis=1, keepdims=True), 1e-9)
            pts = sp_pts + r_s[:, None] * n_out

            if occluding_lathe is not None:
                occ = occluding_lathe.is_segment_occluded_by_solid(cam, pts)
                vis = ~occ
            else:
                vis = np.ones(len(pts), dtype=bool)

            idx = 0
            n = len(pts)
            while idx < n:
                if not vis[idx]:
                    idx += 1
                    continue
                r0 = idx
                while idx < n and vis[idx]:
                    idx += 1
                if idx - r0 >= 2:
                    sub_p = pts[r0:idx]
                    sub_n = n_out[r0:idx]
                    t_raw = np.gradient(sub_p, axis=0)
                    t_u = t_raw / np.maximum(np.linalg.norm(t_raw, axis=1, keepdims=True), 1e-9)
                    n_orth = sub_n - np.sum(sub_n * t_u, axis=1, keepdims=True) * t_u
                    n_u = n_orth / np.maximum(np.linalg.norm(n_orth, axis=1, keepdims=True), 1e-9)
                    b_u = np.cross(n_u, t_u)
                    b_u /= np.maximum(np.linalg.norm(b_u, axis=1, keepdims=True), 1e-9)
                    branches.append((sub_p, t_u, b_u, n_u))
        return branches

    def to_dict(self) -> dict[str, Any]:
        return {
            "generator_id": int(self.generator_id),
            "generator_type": "SWEPT_TUBE_ENVELOPE_3D",
            "degree": int(self.degree),
            "spine_control_points": [[round(float(v), 5) for v in pt] for pt in self.spine_control_points],
            "control_radii": [round(float(r), 5) for r in self.control_radii],
            "half_width_px": round(float(self.half_width_px), 4),
            "inward_shift_px": round(float(self.inward_shift_px), 4),
            "num_supporting_views": len(self.supporting_views),
        }


@dataclass
class RibbonGeometry:
    """Oriented Darboux frame & physical multi-modal edge signature turning a 3D curve into a RIBBON_3D primitive."""

    edge_class: str  # "COAXIAL_RING", "SILHOUETTE_CONTOUR", "DIHEDRAL_CREASE", "SURFACE_STRIPE", "TOPOLOGY_BRIDGE"
    control_normals: np.ndarray
    half_width_px: float = 0.40
    thickness_px: float = 0.27
    inward_shift_px: float = 0.0
    inward_sign: float = 1.0
    dihedral_deg: float = 0.0
    depth_jump_rel: float = 0.0
    albedo_contrast: float = 0.0
    coaxial_family_id: int = -1
    coaxial_ring_h: float = 0.0
    coaxial_ring_r: float = 0.0


@dataclass
class JunctionNode:
    """Topological vertex connecting 1 (free endpoint), 2 (corner/continuation), or 3+ (T/Y) curves."""

    node_id: int
    position: np.ndarray
    incident: list[tuple[int, int]] = field(default_factory=list)
    kind: str = "ENDPOINT"

    @property
    def degree(self) -> int:
        return len(self.incident)


@dataclass
class ParametricCurvePrimitive:
    """First-class 3D vectorized parametric curve & oriented ribbon primitive."""

    curve_id: int
    primitive_type: str  # "LINE_3D", "ARC_3D", or "CUBIC_BSPLINE_3D"
    control_points: np.ndarray
    knots: np.ndarray
    degree: int
    start_node_id: int = -1
    end_node_id: int = -1
    pixel_scale: float = 0.0035
    width_px: float = 0.38
    opacity: float = 0.125
    role: str = "FEATURE_CURVE"
    supporting_views: list[str] = field(default_factory=list)
    source_parent_ids: list[int] = field(default_factory=list)
    confidence: float = 1.0
    ribbon: RibbonGeometry | None = None

    def evaluate(self, num_samples: int = 32) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return (u, points, first_deriv, second_deriv) each of shape (S, 3)."""
        u = np.linspace(0.0, 1.0, max(2, num_samples), dtype=np.float64)
        if self.primitive_type == "ARC_3D" and len(self.control_points) == 3:
            pts, d1, d2 = evaluate_circular_arc_3pt_numpy(self.control_points, u)
            return u, pts, d1, d2

        B, B_du, B_d2u, _, _ = bspline_basis_matrices(
            len(self.control_points), u, degree=self.degree, knots=self.knots
        )
        pts = B @ self.control_points
        d1 = B_du @ self.control_points
        d2 = B_d2u @ self.control_points
        return u, pts, d1, d2

    def evaluate_darboux_frame(
        self, num_samples: int = 32
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Evaluate orthonormal Darboux ribbon frame (u, pts, T_unit, B_ribbon, N_surface) along [0, 1]."""
        u, pts, d1, _ = self.evaluate(num_samples=num_samples)
        d1_len = np.linalg.norm(d1, axis=1, keepdims=True)
        T = np.where(d1_len > 1e-12, d1 / np.maximum(d1_len, 1e-12), np.array([1.0, 0.0, 0.0]))

        m = len(self.control_points)
        if self.ribbon is not None and len(self.ribbon.control_normals) == m:
            cn = np.asarray(self.ribbon.control_normals, dtype=np.float64)
            if self.primitive_type == "ARC_3D" and m == 3:
                l0 = (1.0 - u) * (1.0 - 2.0 * u)
                l1 = 4.0 * u * (1.0 - u)
                l2 = u * (2.0 * u - 1.0)
                n_raw = l0[:, None] * cn[0] + l1[:, None] * cn[1] + l2[:, None] * cn[2]
            else:
                B_mat, _, _, _, _ = bspline_basis_matrices(m, u, degree=self.degree, knots=self.knots)
                n_raw = B_mat @ cn
        else:
            n_raw = np.tile(np.array([[0.0, 0.0, 1.0]], dtype=np.float64), (len(u), 1))

        n_orth = n_raw - np.sum(n_raw * T, axis=1, keepdims=True) * T
        n_len = np.linalg.norm(n_orth, axis=1, keepdims=True)
        deg_mask = n_len[:, 0] < 1e-6
        if np.any(deg_mask):
            alt = np.where(np.abs(T[deg_mask, 2:3]) < 0.85, np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]))
            n_alt = np.cross(T[deg_mask], alt)
            n_orth[deg_mask] = n_alt / np.maximum(np.linalg.norm(n_alt, axis=1, keepdims=True), 1e-9)
            n_len = np.linalg.norm(n_orth, axis=1, keepdims=True)

        N = n_orth / np.maximum(n_len, 1e-9)
        B = np.cross(N, T)
        b_len = np.linalg.norm(B, axis=1, keepdims=True)
        B = B / np.maximum(b_len, 1e-9)
        return u, pts, T, B, N

    def endpoint_tangent(self, end_idx: int) -> np.ndarray:
        """Outward-pointing unit tangent at end_idx=0 (u=0) or end_idx=1 (u=1)."""
        if self.primitive_type == "ARC_3D" and len(self.control_points) == 3:
            _, _, d1, _ = self.evaluate(num_samples=3)
            vec = -d1[0] if end_idx == 0 else d1[-1]
            nrm = float(np.linalg.norm(vec))
            return vec / nrm if nrm > 1e-12 else np.array([1.0, 0.0, 0.0], dtype=np.float64)

        ctrl = self.control_points
        vec = (ctrl[0] - ctrl[1]) if end_idx == 0 else (ctrl[-1] - ctrl[-2])
        nrm = float(np.linalg.norm(vec))
        return vec / nrm if nrm > 1e-12 else np.array([1.0, 0.0, 0.0], dtype=np.float64)

    def mean_surface_normal(self) -> np.ndarray | None:
        if self.ribbon is None or len(self.ribbon.control_normals) == 0:
            return None
        nm = np.mean(self.ribbon.control_normals, axis=0)
        ln = float(np.linalg.norm(nm))
        return nm / ln if ln > 1e-8 else None

    def arc_length(self, num_samples: int = 64) -> float:
        _, pts, _, _ = self.evaluate(num_samples=num_samples)
        return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())

    def bending_energy(self, num_samples: int = 48) -> float:
        r"""Approximate integrated squared curvature \int \kappa(s)^2 ds."""
        u, _, d1, d2 = self.evaluate(num_samples=num_samples)
        du = 1.0 / max(1, len(u) - 1)
        speed = np.linalg.norm(d1, axis=1)
        valid = speed > 1e-9
        if not np.any(valid):
            return 0.0
        cross = np.linalg.norm(np.cross(d1[valid], d2[valid]), axis=1)
        kappa = cross / np.maximum(speed[valid] ** 3, 1e-18)
        return float(np.sum((kappa ** 2) * speed[valid]) * du)


COLOR_PALETTE = np.array([
    [0.14, 0.62, 0.24],
    [0.58, 0.34, 0.78],
    [0.06, 0.68, 0.76],
    [0.82, 0.36, 0.68],
], dtype=np.float64)

EDGE_CLASS_COLORS: dict[str, np.ndarray] = {
    "COAXIAL_RING": np.array([0.94, 0.62, 0.02], dtype=np.float64),           # Gold/Amber: Coaxial Lathe Rings
    "VIEW_CONTOUR_GENERATOR": np.array([0.00, 0.72, 0.86], dtype=np.float64), # Vivid Cyan: View-Dependent Envelopes!
    "SILHOUETTE_CONTOUR": np.array([0.08, 0.66, 0.34], dtype=np.float64),     # Emerald Green: Occluding Leaf Rims
    "DIHEDRAL_CREASE": np.array([0.12, 0.44, 0.88], dtype=np.float64),        # Royal Blue: 3D Normal Creases
    "SURFACE_STRIPE": np.array([0.68, 0.26, 0.78], dtype=np.float64),         # Amethyst: Veins & Surface Markings
    "TOPOLOGY_BRIDGE": np.array([0.92, 0.18, 0.14], dtype=np.float64),        # Crimson: Bridges
}


def _resample_horizon_branch_to_surflets(
    pts: np.ndarray,
    n_out: np.ndarray,
    pixel_scale: float,
    spacing_px: float,
    longitudinal_sigma_px: float,
    half_width_px: float,
    thickness_px: float,
    inward_shift_px: float,
    opacity: float,
    color_rgb: np.ndarray,
    prim_id: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    """Convert an ordered 3D horizon polyline + outward surface normals into inward-tucked tri-axial surflets."""
    if len(pts) < 2:
        return None
    p = max(float(pixel_scale), 1e-5)
    diffs = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(diffs)])
    tot_len = float(cum[-1])
    if tot_len < 0.5 * p:
        return None

    step = max(spacing_px * p, 1e-5)
    n_seg = max(1, int(math.ceil(tot_len / step)))
    s_grid = np.linspace(0.0, tot_len, n_seg + 1, dtype=np.float64)
    pts_r = np.column_stack([np.interp(s_grid, cum, pts[:, k]) for k in range(3)])
    nrm_r = np.column_stack([np.interp(s_grid, cum, n_out[:, k]) for k in range(3)])

    seg_vecs = pts_r[1:] - pts_r[:-1]
    seg_mids = 0.5 * (pts_r[1:] + pts_r[:-1])
    seg_lens = np.linalg.norm(seg_vecs, axis=1)
    tangents = np.zeros_like(seg_vecs)
    ok = seg_lens > 1e-12
    tangents[ok] = seg_vecs[ok] / seg_lens[ok, None]
    tangents[~ok] = np.array([0.0, 0.0, 1.0], dtype=np.float64)

    n_mid = 0.5 * (nrm_r[1:] + nrm_r[:-1])
    n_mid = n_mid - np.sum(n_mid * tangents, axis=1, keepdims=True) * tangents
    n_len = np.linalg.norm(n_mid, axis=1, keepdims=True)
    N_seg = n_mid / np.maximum(n_len, 1e-9)
    B_seg = np.cross(N_seg, tangents)
    B_seg /= np.maximum(np.linalg.norm(B_seg, axis=1, keepdims=True), 1e-9)

    # At a smooth horizon (N · view == 0), N_seg points outward into empty sky in screen space!
    # Shift by -inward_shift_px * p * N_seg strictly into the foreground vessel/trunk interior!
    seg_mids = seg_mids - (inward_shift_px * p) * N_seg

    sig_para = np.maximum(longitudinal_sigma_px * p, 0.65 * seg_lens)
    sig_n_screen = max(half_width_px * p, 1e-5)
    sig_b_ray = max(thickness_px * p, 1e-5)

    tt = tangents[:, :, None] * tangents[:, None, :]
    nn = N_seg[:, :, None] * N_seg[:, None, :]
    bb = B_seg[:, :, None] * B_seg[:, None, :]
    cov = (sig_para[:, None, None] ** 2) * tt + (sig_n_screen ** 2) * nn + (sig_b_ray ** 2) * bb

    m = len(seg_mids)
    return (
        seg_mids,
        cov,
        np.full(m, np.clip(opacity, 0.01, 0.99), dtype=np.float64),
        np.repeat(color_rgb[None, :], m, axis=0),
        np.full(m, prim_id, dtype=np.int32),
    )


@dataclass
class CurveNetwork3D:
    """Hybrid 3D geometric primitive network: static curves/ribbons + coaxial rings + planar frames + contour envelopes."""

    scene_name: str
    curves: dict[int, ParametricCurvePrimitive] = field(default_factory=dict)
    nodes: dict[int, JunctionNode] = field(default_factory=dict)
    coaxial_families: list[CoaxialRingFamilySpec] = field(default_factory=list)
    lathe_generators: list[LatheEnvelopeGenerator] = field(default_factory=list)
    tube_generators: list[SweptTubeGenerator] = field(default_factory=list)
    planar_patches: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def sync_endpoints_from_nodes(self) -> None:
        """Enforce exact C0 continuity by copying shared JunctionNode coordinates into curve endpoints."""
        for curve in self.curves.values():
            if curve.start_node_id in self.nodes:
                curve.control_points[0] = self.nodes[curve.start_node_id].position.copy()
            if curve.end_node_id in self.nodes:
                curve.control_points[-1] = self.nodes[curve.end_node_id].position.copy()

    def rebuild_node_incidence(self) -> None:
        for node in self.nodes.values():
            node.incident.clear()
        for cid, curve in self.curves.items():
            if curve.start_node_id in self.nodes:
                self.nodes[curve.start_node_id].incident.append((cid, 0))
            if curve.end_node_id in self.nodes:
                self.nodes[curve.end_node_id].incident.append((cid, 1))
        orphan_ids = [nid for nid, node in self.nodes.items() if len(node.incident) == 0]
        for nid in orphan_ids:
            del self.nodes[nid]

    def summary_stats(self) -> dict[str, Any]:
        lengths = np.array([c.arc_length() for c in self.curves.values()], dtype=np.float64)
        n_curves = len(self.curves)
        n_lines = sum(1 for c in self.curves.values() if c.primitive_type == "LINE_3D")
        n_arcs = sum(1 for c in self.curves.values() if c.primitive_type == "ARC_3D")
        n_splines = sum(1 for c in self.curves.values() if c.primitive_type == "CUBIC_BSPLINE_3D")
        n_cocirc = sum(1 for c in self.curves.values() if c.role == "COCIRCULAR_RING")
        n_coaxial = sum(1 for c in self.curves.values() if c.role == "COAXIAL_RING")
        n_bridges = sum(1 for c in self.curves.values() if c.role == "BRIDGE")
        n_ribbons = sum(1 for c in self.curves.values() if c.ribbon is not None)
        mv_supported = sum(1 for c in self.curves.values() if len(c.supporting_views) >= 2)
        total_ctrl = sum(len(c.control_points) for c in self.curves.values())
        gen_ctrl = sum(len(g.profile_h) for g in self.lathe_generators) + sum(
            len(t.spine_control_points) for t in self.tube_generators
        )

        edge_class_counts: dict[str, int] = {}
        for c in self.curves.values():
            if c.ribbon is not None:
                ec = c.ribbon.edge_class
                edge_class_counts[ec] = edge_class_counts.get(ec, 0) + 1
        if self.lathe_generators or self.tube_generators:
            edge_class_counts["VIEW_CONTOUR_GENERATOR"] = len(self.lathe_generators) + len(self.tube_generators)

        deg_counts: dict[str, int] = {"deg1_open": 0, "deg2_cont": 0, "deg3plus_junction": 0}
        for node in self.nodes.values():
            if node.degree == 1:
                deg_counts["deg1_open"] += 1
            elif node.degree == 2:
                deg_counts["deg2_cont"] += 1
            elif node.degree >= 3:
                deg_counts["deg3plus_junction"] += 1

        return {
            "scene": self.scene_name,
            "num_curves": n_curves,
            "num_line_3d": n_lines,
            "num_arc_3d": n_arcs,
            "num_cubic_bspline_3d": n_splines,
            "num_coaxial_families": len(self.coaxial_families),
            "num_coaxial_ring_arcs": n_coaxial,
            "num_cocircular_merged_arcs": n_cocirc,
            "num_bridges": n_bridges,
            "num_ribbon_3d_primitives": n_ribbons,
            "num_lathe_contour_generators": len(self.lathe_generators),
            "num_swept_tube_generators": len(self.tube_generators),
            "total_contour_generators": len(self.lathe_generators) + len(self.tube_generators),
            "num_planar_patches": len(self.planar_patches),
            "edge_class_counts": edge_class_counts,
            "total_control_points": total_ctrl,
            "generator_control_nodes": gen_ctrl,
            "num_nodes": len(self.nodes),
            "node_degrees": deg_counts,
            "open_endpoint_ratio": float(deg_counts["deg1_open"] / max(1, 2 * n_curves)),
            "multiview_2plus_curve_count": mv_supported,
            "multiview_2plus_curve_ratio": float(mv_supported / max(1, n_curves)),
            "total_arc_length": float(lengths.sum()) if n_curves else 0.0,
            "median_arc_length": float(np.median(lengths)) if n_curves else 0.0,
            "mean_arc_length": float(lengths.mean()) if n_curves else 0.0,
            "p90_arc_length": float(np.percentile(lengths, 90)) if n_curves else 0.0,
        }

    def to_line_gaussians(
        self,
        spacing_px: float = 0.35,
        longitudinal_sigma_px: float = 0.75,
        color_mode: str = "ink",
        use_ribbon_surflets: bool = True,
        camera_center: np.ndarray | None = None,
    ) -> dict[str, np.ndarray]:
        """Sample static curves/ribbons + optional view-dependent horizon contours for `camera_center`."""
        means_list: list[np.ndarray] = []
        cov_list: list[np.ndarray] = []
        opac_list: list[np.ndarray] = []
        color_list: list[np.ndarray] = []
        prim_ids: list[np.ndarray] = []

        eye3 = np.eye(3, dtype=np.float64)
        for idx, cid in enumerate(sorted(self.curves.keys())):
            curve = self.curves[cid]
            p = max(float(curve.pixel_scale), 1e-5)
            length = curve.arc_length(num_samples=48)
            step = max(spacing_px * p, 1e-5)
            n_seg = max(1, int(np.ceil(length / step)))

            if use_ribbon_surflets and curve.ribbon is not None:
                _, pts, _, B_frame, N_frame = curve.evaluate_darboux_frame(num_samples=n_seg + 1)
                seg_vecs = pts[1:] - pts[:-1]
                seg_mids = 0.5 * (pts[1:] + pts[:-1])
                seg_lens = np.linalg.norm(seg_vecs, axis=1)
                tangents = np.zeros_like(seg_vecs)
                valid = seg_lens > 1e-12
                tangents[valid] = seg_vecs[valid] / seg_lens[valid, None]
                tangents[~valid] = np.array([1.0, 0.0, 0.0], dtype=np.float64)

                n_mid = 0.5 * (N_frame[1:] + N_frame[:-1])
                n_mid = n_mid - np.sum(n_mid * tangents, axis=1, keepdims=True) * tangents
                n_len = np.linalg.norm(n_mid, axis=1, keepdims=True)
                bad_n = n_len[:, 0] < 1e-6
                if np.any(bad_n):
                    b_fallback = 0.5 * (B_frame[1:] + B_frame[:-1])
                    n_mid[bad_n] = np.cross(tangents[bad_n], b_fallback[bad_n])
                    n_len = np.linalg.norm(n_mid, axis=1, keepdims=True)
                N_seg = n_mid / np.maximum(n_len, 1e-9)
                B_seg = np.cross(N_seg, tangents)
                B_seg /= np.maximum(np.linalg.norm(B_seg, axis=1, keepdims=True), 1e-9)

                if abs(curve.ribbon.inward_shift_px) > 1e-6:
                    seg_mids = seg_mids + (curve.ribbon.inward_shift_px * curve.ribbon.inward_sign * p) * B_seg

                sig_para = np.maximum(longitudinal_sigma_px * p, 0.65 * seg_lens)
                sig_width = max(curve.ribbon.half_width_px * p, 1e-5)
                sig_thick = max(curve.ribbon.thickness_px * p, 1e-5)

                tt = tangents[:, :, None] * tangents[:, None, :]
                bb = B_seg[:, :, None] * B_seg[:, None, :]
                nn = N_seg[:, :, None] * N_seg[:, None, :]
                cov = (sig_para[:, None, None] ** 2) * tt + (sig_width ** 2) * bb + (sig_thick ** 2) * nn
            else:
                _, pts, _, _ = curve.evaluate(num_samples=n_seg + 1)
                seg_vecs = pts[1:] - pts[:-1]
                seg_mids = 0.5 * (pts[1:] + pts[:-1])
                seg_lens = np.linalg.norm(seg_vecs, axis=1)
                tangents = np.zeros_like(seg_vecs)
                valid = seg_lens > 1e-12
                tangents[valid] = seg_vecs[valid] / seg_lens[valid, None]
                tangents[~valid] = np.array([1.0, 0.0, 0.0], dtype=np.float64)

                sigma_perp = max(curve.width_px * p, 1e-5)
                sigma_para = np.maximum(longitudinal_sigma_px * p, 0.65 * seg_lens)
                tt = tangents[:, :, None] * tangents[:, None, :]
                cov = (sigma_para[:, None, None] ** 2) * tt + (sigma_perp ** 2) * (eye3[None, :, :] - tt)

            m = len(seg_mids)
            means_list.append(seg_mids)
            cov_list.append(cov)
            opac_list.append(np.full(m, np.clip(curve.opacity, 0.01, 0.99), dtype=np.float64))
            prim_ids.append(np.full(m, cid, dtype=np.int32))

            if color_mode == "ink":
                color_list.append(np.zeros((m, 3), dtype=np.float64))
            elif color_mode == "edge_class" and curve.ribbon is not None:
                col = EDGE_CLASS_COLORS.get(curve.ribbon.edge_class, np.array([0.2, 0.2, 0.2], dtype=np.float64))
                color_list.append(np.repeat(col[None, :], m, axis=0))
            else:
                if curve.role == "COAXIAL_RING":
                    col = np.array([0.96, 0.52, 0.0], dtype=np.float64)
                elif curve.role == "BRIDGE":
                    col = np.array([0.95, 0.20, 0.10], dtype=np.float64)
                elif curve.primitive_type == "ARC_3D":
                    col = np.array([0.88, 0.68, 0.06], dtype=np.float64)
                elif curve.primitive_type == "LINE_3D":
                    col = np.array([0.12, 0.45, 0.86], dtype=np.float64)
                else:
                    col = COLOR_PALETTE[idx % len(COLOR_PALETTE)]
                color_list.append(np.repeat(col[None, :], m, axis=0))

        # Dynamically append exact view-dependent occluding contour surflets when camera_center is supplied!
        if camera_center is not None and (self.lathe_generators or self.tube_generators):
            gen_col = (
                np.zeros(3, dtype=np.float64)
                if color_mode == "ink"
                else EDGE_CLASS_COLORS["VIEW_CONTOUR_GENERATOR"]
            )
            occ_lathe = self.lathe_generators[0] if self.lathe_generators else None

            for lg in self.lathe_generators:
                for h_pts, _, _, h_nrm in lg.evaluate_horizon_curves(camera_center, num_samples=64):
                    res = _resample_horizon_branch_to_surflets(
                        h_pts, h_nrm, lg.pixel_scale, spacing_px, longitudinal_sigma_px,
                        lg.half_width_px, lg.thickness_px, lg.inward_shift_px, lg.opacity, gen_col, -100 - lg.generator_id,
                    )
                    if res is not None:
                        means_list.append(res[0])
                        cov_list.append(res[1])
                        opac_list.append(res[2])
                        color_list.append(res[3])
                        prim_ids.append(res[4])

            for tg in self.tube_generators:
                for h_pts, _, _, h_nrm in tg.evaluate_horizon_curves(camera_center, num_samples=32, occluding_lathe=occ_lathe):
                    res = _resample_horizon_branch_to_surflets(
                        h_pts, h_nrm, tg.pixel_scale, spacing_px, longitudinal_sigma_px,
                        tg.half_width_px, tg.thickness_px, tg.inward_shift_px, tg.opacity, gen_col, -200 - tg.generator_id,
                    )
                    if res is not None:
                        means_list.append(res[0])
                        cov_list.append(res[1])
                        opac_list.append(res[2])
                        color_list.append(res[3])
                        prim_ids.append(res[4])

        if not means_list:
            return {
                "means": np.zeros((0, 3), dtype=np.float64),
                "covariance": np.zeros((0, 3, 3), dtype=np.float64),
                "opacity": np.zeros((0,), dtype=np.float64),
                "colors": np.zeros((0, 3), dtype=np.float64),
                "primitive_id": np.zeros((0,), dtype=np.int32),
            }

        return {
            "means": np.concatenate(means_list, axis=0),
            "covariance": np.concatenate(cov_list, axis=0),
            "opacity": np.concatenate(opac_list, axis=0),
            "colors": np.concatenate(color_list, axis=0),
            "primitive_id": np.concatenate(prim_ids, axis=0),
        }

    def export_obj(self, path: str | Path, samples_per_curve: int = 24) -> Path:
        out_path = resolve_safe_path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines_out: list[str] = [f"# vec_spline3d_v04 CurveNetwork3D scene={self.scene_name}"]
        v_offset = 1
        for cid in sorted(self.curves.keys()):
            curve = self.curves[cid]
            n_s = 2 if curve.primitive_type == "LINE_3D" else max(12, samples_per_curve)
            _, pts, _, _ = curve.evaluate(num_samples=n_s)
            for p in pts:
                lines_out.append(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}")
            idx_str = " ".join(str(v_offset + k) for k in range(len(pts)))
            lines_out.append(f"l {idx_str}")
            v_offset += len(pts)
        tmp = out_path.with_name(f"{out_path.name}.tmp-{os.getpid()}")
        tmp.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
        os.replace(tmp, out_path)
        return out_path

    def export_ribbon_obj(self, path: str | Path, samples_per_curve: int = 20) -> Path:
        """Export oriented 3D Darboux ribbon triangle-strip meshes grouped by physical edge class."""
        out_path = resolve_safe_path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines_out: list[str] = [f"# vec_spline3d_v04 RIBBON_3D Oriented Surface Strips scene={self.scene_name}"]

        by_group: dict[str, list[int]] = {}
        for cid in sorted(self.curves.keys()):
            ec = self.curves[cid].ribbon.edge_class if self.curves[cid].ribbon is not None else "UNCLASSIFIED"
            by_group.setdefault(ec, []).append(cid)

        v_off = 1
        for grp_name, cid_list in sorted(by_group.items()):
            lines_out.append(f"g {grp_name}")
            for cid in cid_list:
                c = self.curves[cid]
                n_s = 4 if c.primitive_type == "LINE_3D" else max(12, samples_per_curve)
                _, pts, _, B_vec, N_vec = c.evaluate_darboux_frame(num_samples=n_s)
                hw_px = c.ribbon.half_width_px if c.ribbon is not None else c.width_px
                hw_world = max(hw_px * c.pixel_scale, 1e-5)
                in_shift = (
                    c.ribbon.inward_shift_px * c.ribbon.inward_sign * c.pixel_scale
                    if c.ribbon is not None
                    else 0.0
                )
                center_pts = pts + in_shift * B_vec
                left_pts = center_pts - hw_world * B_vec
                right_pts = center_pts + hw_world * B_vec

                for k in range(n_s):
                    lp = left_pts[k]
                    rp = right_pts[k]
                    nv = N_vec[k]
                    lines_out.append(f"v {lp[0]:.6f} {lp[1]:.6f} {lp[2]:.6f}")
                    lines_out.append(f"vn {nv[0]:.5f} {nv[1]:.5f} {nv[2]:.5f}")
                    lines_out.append(f"v {rp[0]:.6f} {rp[1]:.6f} {rp[2]:.6f}")
                    lines_out.append(f"vn {nv[0]:.5f} {nv[1]:.5f} {nv[2]:.5f}")

                for k in range(n_s - 1):
                    i0 = v_off + 2 * k
                    i1 = i0 + 1
                    i2 = i0 + 2
                    i3 = i0 + 3
                    lines_out.append(f"f {i0}//{i0} {i1}//{i1} {i3}//{i3}")
                    lines_out.append(f"f {i0}//{i0} {i3}//{i3} {i2}//{i2}")
                v_off += 2 * n_s

        tmp = out_path.with_name(f"{out_path.name}.tmp-{os.getpid()}")
        tmp.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
        os.replace(tmp, out_path)
        return out_path

    def export_envelopes_obj(self, path: str | Path) -> Path:
        """Export smooth 3D surface-of-revolution and swept-tube envelope meshes supporting view-dependent contours."""
        out_path = resolve_safe_path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines_out: list[str] = [f"# vec_spline3d_v04 Occluding Contour Envelope Surfaces scene={self.scene_name}"]
        v_off = 1

        for lg in self.lathe_generators:
            lines_out.append(f"g LATHE_ENVELOPE_{lg.generator_id}")
            n_h = len(lg.profile_h)
            n_th = 64
            thetas = np.linspace(0.0, 2.0 * math.pi, n_th, endpoint=False)
            dr_dh = np.gradient(lg.profile_r, lg.profile_h)
            for i_h in range(n_h):
                hk = float(lg.profile_h[i_h])
                rk = float(lg.profile_r[i_h])
                slk = float(dr_dh[i_h])
                for th in thetas:
                    er = math.cos(th) * lg.e1 + math.sin(th) * lg.e2
                    pt = lg.axis_origin + hk * lg.axis_dir + rk * er
                    nv = er - slk * lg.axis_dir
                    nv /= max(float(np.linalg.norm(nv)), 1e-9)
                    lines_out.append(f"v {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f}")
                    lines_out.append(f"vn {nv[0]:.5f} {nv[1]:.5f} {nv[2]:.5f}")
            for i_h in range(n_h - 1):
                for j in range(n_th):
                    jn = (j + 1) % n_th
                    a = v_off + i_h * n_th + j
                    b = v_off + i_h * n_th + jn
                    c = v_off + (i_h + 1) * n_th + jn
                    d = v_off + (i_h + 1) * n_th + j
                    lines_out.append(f"f {a}//{a} {b}//{b} {c}//{c}")
                    lines_out.append(f"f {a}//{a} {c}//{c} {d}//{d}")
            v_off += n_h * n_th

        for tg in self.tube_generators:
            lines_out.append(f"g SWEPT_TUBE_{tg.generator_id}")
            n_s = 28
            n_th = 20
            u = np.linspace(0.0, 1.0, n_s)
            thetas = np.linspace(0.0, 2.0 * math.pi, n_th, endpoint=False)
            B_m, B_du, _, _, _ = bspline_basis_matrices(len(tg.spine_control_points), u, degree=tg.degree, knots=tg.knots)
            sp_p = B_m @ tg.spine_control_points
            sp_d1 = B_du @ tg.spine_control_points
            T_s = sp_d1 / np.maximum(np.linalg.norm(sp_d1, axis=1, keepdims=True), 1e-9)
            r_s = np.maximum(B_m @ tg.control_radii, 1e-4)

            for i_s in range(n_s):
                ts = T_s[i_s]
                ref = np.array([1.0, 0.0, 0.0]) if abs(ts[0]) < 0.85 else np.array([0.0, 1.0, 0.0])
                u1 = np.cross(ts, ref)
                u1 /= max(float(np.linalg.norm(u1)), 1e-9)
                u2 = np.cross(ts, u1)
                for th in thetas:
                    nv = math.cos(th) * u1 + math.sin(th) * u2
                    pt = sp_p[i_s] + r_s[i_s] * nv
                    lines_out.append(f"v {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f}")
                    lines_out.append(f"vn {nv[0]:.5f} {nv[1]:.5f} {nv[2]:.5f}")
            for i_s in range(n_s - 1):
                for j in range(n_th):
                    jn = (j + 1) % n_th
                    a = v_off + i_s * n_th + j
                    b = v_off + i_s * n_th + jn
                    c = v_off + (i_s + 1) * n_th + jn
                    d = v_off + (i_s + 1) * n_th + j
                    lines_out.append(f"f {a}//{a} {b}//{b} {c}//{c}")
                    lines_out.append(f"f {a}//{a} {c}//{c} {d}//{d}")
            v_off += n_s * n_th

        tmp = out_path.with_name(f"{out_path.name}.tmp-{os.getpid()}")
        tmp.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
        os.replace(tmp, out_path)
        return out_path

    def save_package(self, out_dir: str | Path) -> dict[str, str]:
        out = resolve_safe_path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        self.sync_endpoints_from_nodes()

        all_ctrl: list[np.ndarray] = []
        all_ctrl_nrm: list[np.ndarray] = []
        all_knots: list[np.ndarray] = []
        ctrl_offsets: list[tuple[int, int]] = []
        knot_offsets: list[tuple[int, int]] = []
        curves_doc: list[dict[str, Any]] = []

        c_off = 0
        k_off = 0
        for cid in sorted(self.curves.keys()):
            c = self.curves[cid]
            m = len(c.control_points)
            km = len(c.knots)
            all_ctrl.append(c.control_points)
            if c.ribbon is not None and len(c.ribbon.control_normals) == m:
                all_ctrl_nrm.append(c.ribbon.control_normals)
            else:
                all_ctrl_nrm.append(np.zeros((m, 3), dtype=np.float64))
            all_knots.append(c.knots)
            ctrl_offsets.append((c_off, c_off + m))
            knot_offsets.append((k_off, k_off + km))
            c_off += m
            k_off += km

            entry: dict[str, Any] = {
                "curve_id": int(cid),
                "primitive_type": c.primitive_type,
                "degree": int(c.degree),
                "num_control_points": int(m),
                "ctrl_slice": [ctrl_offsets[-1][0], ctrl_offsets[-1][1]],
                "knot_slice": [knot_offsets[-1][0], knot_offsets[-1][1]],
                "start_node_id": int(c.start_node_id),
                "end_node_id": int(c.end_node_id),
                "pixel_scale": float(c.pixel_scale),
                "width_px": float(c.width_px),
                "opacity": float(c.opacity),
                "role": c.role,
                "supporting_views": list(c.supporting_views),
                "source_parent_ids": [int(x) for x in c.source_parent_ids],
                "confidence": float(c.confidence),
            }
            if c.primitive_type == "ARC_3D" and m == 3:
                ag = circular_arc_geometry_from_3pt(c.control_points[0], c.control_points[1], c.control_points[2])
                if not ag["is_collinear"]:
                    entry["arc_geometry"] = {
                        "center": [float(x) for x in ag["center"]],
                        "normal": [float(x) for x in ag["normal"]],
                        "radius": float(ag["radius"]),
                        "sweep_deg": round(math.degrees(ag["sweep_rad"]), 3),
                    }
            if c.ribbon is not None:
                entry["ribbon_3d"] = {
                    "edge_class": c.ribbon.edge_class,
                    "half_width_px": round(float(c.ribbon.half_width_px), 4),
                    "thickness_px": round(float(c.ribbon.thickness_px), 4),
                    "inward_shift_px": round(float(c.ribbon.inward_shift_px), 4),
                    "inward_sign": float(c.ribbon.inward_sign),
                    "dihedral_deg": round(float(c.ribbon.dihedral_deg), 2),
                    "depth_jump_rel": round(float(c.ribbon.depth_jump_rel), 5),
                    "albedo_contrast": round(float(c.ribbon.albedo_contrast), 4),
                    "coaxial_family_id": int(c.ribbon.coaxial_family_id),
                }
            curves_doc.append(entry)

        nodes_doc = [
            {
                "node_id": int(nid),
                "position": [float(x) for x in self.nodes[nid].position],
                "degree": int(self.nodes[nid].degree),
                "kind": self.nodes[nid].kind,
                "incident": [[int(a), int(b)] for a, b in self.nodes[nid].incident],
            }
            for nid in sorted(self.nodes.keys())
        ]

        summary = self.summary_stats()
        json_path = out / "curve_network.json"
        doc = {
            "schema": "vec_spline3d/v05",
            "scene": self.scene_name,
            "summary": summary,
            "coaxial_families": [fam.to_dict() for fam in self.coaxial_families],
            "contour_generators": (
                [lg.to_dict() for lg in self.lathe_generators] + [tg.to_dict() for tg in self.tube_generators]
            ),
            "planar_patches": [
                {k: v for k, v in pp.items() if not k.startswith("_")} for pp in self.planar_patches
            ],
            "metadata": self.metadata,
            "nodes": nodes_doc,
            "curves": curves_doc,
        }
        tmp_json = json_path.with_name(f"{json_path.name}.tmp-{os.getpid()}")
        tmp_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp_json, json_path)

        npz_path = out / "curve_controls.npz"
        np.savez_compressed(
            npz_path,
            control_points=np.concatenate(all_ctrl, axis=0) if all_ctrl else np.zeros((0, 3)),
            control_normals=np.concatenate(all_ctrl_nrm, axis=0) if all_ctrl_nrm else np.zeros((0, 3)),
            knots=np.concatenate(all_knots, axis=0) if all_knots else np.zeros((0,)),
            ctrl_offsets=np.array(ctrl_offsets, dtype=np.int32),
            knot_offsets=np.array(knot_offsets, dtype=np.int32),
        )

        obj_path = self.export_obj(out / "curves_wireframe.obj")
        ribbon_obj_path = self.export_ribbon_obj(out / "ribbons_mesh.obj")
        ink_gs = self.to_line_gaussians(color_mode="ink")
        col_gs = self.to_line_gaussians(color_mode="primitive")
        sem_gs = self.to_line_gaussians(color_mode="edge_class")
        ink_path = out / "resampled_ink_gaussians.npz"
        col_path = out / "resampled_colored_gaussians.npz"
        sem_path = out / "resampled_semantic_gaussians.npz"
        np.savez_compressed(ink_path, **ink_gs)
        np.savez_compressed(col_path, **col_gs)
        np.savez_compressed(sem_path, **sem_gs)

        result = {
            "json": str(json_path),
            "controls_npz": str(npz_path),
            "obj": str(obj_path),
            "ribbons_obj": str(ribbon_obj_path),
            "ink_gaussians_npz": str(ink_path),
            "colored_gaussians_npz": str(col_path),
            "semantic_gaussians_npz": str(sem_path),
        }
        if self.lathe_generators or self.tube_generators:
            env_path = self.export_envelopes_obj(out / "contour_envelopes_mesh.obj")
            result["envelopes_obj"] = str(env_path)
        return result
