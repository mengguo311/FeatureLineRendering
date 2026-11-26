"""Scene-agnostic unified schema, periodic & clamped B-spline math, and strict boundary-isolated I/O."""

from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from plyfile import PlyData, PlyElement
from scipy.interpolate import BSpline
from scipy.ndimage import distance_transform_edt

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

READ_ALLOWED_ROOTS: tuple[Path, ...] = (
    _PACKAGE_ROOT,
    Path("/mnt/hdd1/u00134/radegs_paper_reproduction_v01").resolve(),
    Path("/home/u00134/cglib/data/full").resolve(),
    Path("/home/u00134/3dgs_line").resolve(),
    Path("/home/u00134/.gemini/antigravity/scratch").resolve(),
    Path("/home/u00134/Documents/Codex/2026-11-26/ficus-leaf-kernels-v04-hybrid-botanical").resolve(),
    Path("/home/u00134/.gemini/antigravity/brain/48eb7555-77d2-4416-a9b8-173755682d02").resolve(),
)

# STRICT WRITE ISOLATION: never write outside universal_botanical_v01 or active conversation artifact dir!
WRITE_ALLOWED_ROOTS: tuple[Path, ...] = (
    _PACKAGE_ROOT,
    Path("/home/u00134/.gemini/antigravity/brain/48eb7555-77d2-4416-a9b8-173755682d02").resolve(),
)

LABEL_STATIC_STAND_OR_TABLE = -4
LABEL_UNASSIGNED_CANOPY = -3
LABEL_STEM_SKELETON = -2
LABEL_BASAL_SUPPORT = -1


def resolve_read_path(path: str | Path, allowed_roots: Iterable[Path] = READ_ALLOWED_ROOTS) -> Path:
    resolved = Path(path).resolve()
    for root in allowed_roots:
        r = root.resolve()
        if resolved == r or resolved.is_relative_to(r):
            return resolved
    raise ValueError(f"Read path '{resolved}' is outside allowed boundaries.")


def resolve_write_path(path: str | Path, allowed_roots: Iterable[Path] = WRITE_ALLOWED_ROOTS) -> Path:
    resolved = Path(path).resolve()
    for root in allowed_roots:
        r = root.resolve()
        if resolved == r or resolved.is_relative_to(r):
            return resolved
    raise PermissionError(f"Write path '{resolved}' blocked to protect upstream & user workspaces!")


def atomic_write_text(path: str | Path, content: str) -> Path:
    dest = resolve_write_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.tmp-{os.getpid()}")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, dest)
    return dest


@dataclass(frozen=True)
class UniversalBotanicalConfig:
    """Single frozen scene-agnostic configuration used identically across all plant species & containers."""

    active_opacity_min: float = 0.030
    open_ground_width_over_height_min: float = 1.35
    smooth_shell_djump_max: float = 0.0185
    smooth_shell_alpha_min: float = 0.90
    rect_tray_fill_min: float = 0.90
    lathe_aspect_max: float = 1.16
    min_cell_area_px: int = 24
    max_cell_area_frac: float = 0.28
    detrended_depth_iqr_mult: float = 4.8
    coplanar_normal_deg: float = 33.0
    coplanar_step_mult: float = 1.75
    seam_merge_normal_deg: float = 52.0
    seam_merge_step_mult: float = 2.80
    seam_merge_djump_mult: float = 2.80
    laminar_thickness_ratio_max: float = 0.24
    min_laminar_active_kernels: int = 22
    num_periodic_ctrl: int = 24


@dataclass
class SceneGaussianCloud:
    """Canonical 3DGS model preserving exact vertex order and full degree-3 SH coefficients."""

    means: np.ndarray          # (N, 3) float32
    scales: np.ndarray         # (N, 3) float32 linear exp(scale)
    quats_wxyz: np.ndarray     # (N, 4) float32 normalized
    cov6: np.ndarray           # (N, 6) float32 upper-triangular 3D covariance
    surfel_normals: np.ndarray # (N, 3) float32 shortest-axis unit normal
    opacities: np.ndarray      # (N,) float32 in (0, 1)
    rgb_dc: np.ndarray         # (N, 3) float32 base color in [0, 1]
    shs: np.ndarray            # (N, 16, 3) float32 degree-3 spherical harmonics


@dataclass
class CalibratedBuildOrEvalView:
    """Single calibrated build or held-out view."""

    view_name: str
    split: str
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    w2c: np.ndarray
    c2w: np.ndarray
    cam_center: np.ndarray
    rgb: np.ndarray
    alpha: np.ndarray
    depth: np.ndarray
    front_depth: np.ndarray
    depth_jump: np.ndarray
    darkness: np.ndarray
    skeleton: np.ndarray
    edge_dt: np.ndarray


@dataclass
class BasalSupportModel:
    """Automatically discovered basal support regime (enclosed pot/tray/vessel, open ground, or none)."""

    regime: str  # AXISYMMETRIC_LATHE | RECTANGULAR_TRAY_LOFT | CONVEX_SECTION_LOFT | OPEN_GROUND_BED | NO_ENCLOSED_SUPPORT
    vertices: np.ndarray         # (V, 3) float32 mesh vertices (empty if no enclosed vessel)
    faces: np.ndarray            # (F, 3) int32 mesh triangles
    rim_z: float                 # top height of enclosed support or ground bed
    vessel_bot_z: float          # bottom height of enclosed vessel (above any stand/table)
    support_kernel_mask: np.ndarray  # (N,) bool: static container or ground-bed Gaussians
    stand_kernel_mask: np.ndarray    # (N,) bool: static under-container stand/table Gaussians
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class StemSplineChain:
    """Evidence-backed 3D stem / trunk / stalk B-spline segment."""

    chain_id: int
    level: int                   # 0 = primary trunk/stalk, 1 = secondary branch, 2 = organ petiole/attachment
    parent_chain_id: int         # -1 if rooted at basal support / ground
    parent_u: float
    ctrl_points: np.ndarray      # (M, 3) float64 clamped cubic B-spline controls
    radius_base: float
    radius_tip: float
    supported_kernel_count: int
    basal_anchored: bool


@dataclass
class AdaptiveOrganPatch:
    """Universal botanical organ: either a 2D spline-trimmed curved lamina or a preserved 3D volumetric cluster."""

    organ_id: int
    organ_kind: str              # "LAMINAR_BLADE" or "VOLUMETRIC_CLUSTER"
    visibility_tier: str         # "OUTER_ENCLOSED", "MID_PARTIAL_OCCLUDED", or "DEEP_OCCLUDED"
    parent_chain_id: int
    p_base: np.ndarray           # (3,) float64 proximal attachment hinge
    centroid: np.ndarray         # (3,) float64 organ 3D centroid
    e1: np.ndarray               # (3,) float64 major lamina axis (base -> apex)
    e2: np.ndarray               # (3,) float64 transverse width axis
    e3: np.ndarray               # (3,) float64 surface normal axis
    length: float
    width: float
    thickness: float
    periodic_ctrl_r: np.ndarray  # (K,) float64 normalized polar radial spline controls in (u_norm, v_norm)
    apex_cusp_gamma: float       # [0, 1]: 0 = smooth rounded/lobed tip (Brassica), >0 = pointed acuminate tip (Ficus/Canna)
    camber_coef8: np.ndarray     # (8,) float64 cubic ruffled surface w(u, v)
    kernel_indices: np.ndarray   # (M_o,) int32 indices into refined cloud
    mean_rgb: np.ndarray         # (3,) float32

    def eval_camber(self, u: np.ndarray, v: np.ndarray) -> np.ndarray:
        c = self.camber_coef8
        return (
            c[0]
            + c[1] * u
            + c[2] * v
            + c[3] * (u ** 2)
            + c[4] * (u * v)
            + c[5] * (v ** 2)
            + c[6] * (u ** 3)
            + c[7] * (u * (v ** 2))
        )

    def eval_boundary_uv(self, thetas: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        r_env = eval_periodic_cubic_bspline_1d(self.periodic_ctrl_r, thetas)
        a_half = max(0.5 * self.length, 1e-4)
        b_half = max(0.5 * self.width, 1e-4)
        cos_t = np.cos(thetas)
        sin_t = np.sin(thetas)
        # Optional acute-cusp taper near theta=0 (apex) and theta=+-pi (cuneate base) ONLY when empirically supported
        if self.apex_cusp_gamma > 1e-3:
            cusp_mod = 1.0 - self.apex_cusp_gamma * (np.abs(cos_t) ** 3) * 0.28
            sin_eff = sin_t * cusp_mod
        else:
            sin_eff = sin_t
        u_rel = r_env * a_half * cos_t
        v_rel = r_env * b_half * sin_eff
        return u_rel, v_rel

    def eval_3d_boundary_loop(self, n_samples: int = 48) -> np.ndarray:
        th = np.linspace(-math.pi, math.pi, n_samples, endpoint=False)
        u_rel, v_rel = self.eval_boundary_uv(th)
        w_rel = self.eval_camber(u_rel, v_rel)
        return (
            self.centroid[None, :]
            + u_rel[:, None] * self.e1[None, :]
            + v_rel[:, None] * self.e2[None, :]
            + w_rel[:, None] * self.e3[None, :]
        )


@dataclass
class UniversalBotanicalModel:
    """Complete generalizable botanical 3DGS model for arbitrary plant species & support regimes."""

    scene_name: str
    p_med: float
    support: BasalSupportModel
    stem_chains: list[StemSplineChain]
    organs: list[AdaptiveOrganPatch]
    cloud: SceneGaussianCloud
    kernel_labels: np.ndarray    # (N,) int32: -4=stand, -2=stem, -1=support, >=0=organ_id
    stem_owner: np.ndarray       # (N,) int32: chain_id for stem kernels, -1 otherwise
    diagnostics: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Clamped & Periodic Cubic B-Spline Utilities
# ---------------------------------------------------------------------------


def clamped_cubic_knots(num_ctrl: int) -> np.ndarray:
    deg = min(3, num_ctrl - 1)
    n_int = max(0, num_ctrl - deg - 1)
    if n_int > 0:
        interior = np.linspace(0.0, 1.0, n_int + 2)[1:-1]
    else:
        interior = np.array([], dtype=np.float64)
    return np.concatenate([np.zeros(deg + 1), interior, np.ones(deg + 1)])


def eval_clamped_bspline(ctrl: np.ndarray, u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ctrl64 = np.asarray(ctrl, dtype=np.float64)
    m = len(ctrl64)
    u_clamped = np.clip(np.asarray(u, dtype=np.float64), 0.0, 1.0)
    if m == 1:
        pts = np.repeat(ctrl64, len(u_clamped), axis=0)
        return pts, np.zeros_like(pts)
    deg = min(3, m - 1)
    spl = BSpline(clamped_cubic_knots(m), ctrl64, deg)
    return spl(u_clamped), spl.derivative(1)(u_clamped)


def fit_clamped_bspline_3d(polyline: np.ndarray, num_ctrl: int = 5, reg: float = 1e-4) -> np.ndarray:
    pts = np.asarray(polyline, dtype=np.float64)
    if len(pts) <= 2 or num_ctrl <= 2:
        t = np.linspace(0.0, 1.0, max(2, num_ctrl))
        return (1.0 - t)[:, None] * pts[0][None, :] + t[:, None] * pts[-1][None, :]
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(cum[-1])
    if total < 1e-8:
        return np.repeat(pts[:1], num_ctrl, axis=0)
    u_pts = cum / total
    deg = min(3, num_ctrl - 1)
    knots = clamped_cubic_knots(num_ctrl)
    B = BSpline(knots, np.eye(num_ctrl, dtype=np.float64), deg)(u_pts)
    if num_ctrl <= 2:
        return np.vstack([pts[0], pts[-1]])
    rhs = pts - np.outer(B[:, 0], pts[0]) - np.outer(B[:, -1], pts[-1])
    B_in = B[:, 1:-1]
    n_in = num_ctrl - 2
    D2 = np.diff(np.eye(num_ctrl), n=2, axis=0)[:, 1:-1]
    reg_rhs = -(
        np.diff(np.eye(num_ctrl), n=2, axis=0)[:, 0:1] @ pts[0:1]
        + np.diff(np.eye(num_ctrl), n=2, axis=0)[:, -1:] @ pts[-1:]
    )
    lhs = B_in.T @ B_in + reg * (D2.T @ D2) + 1e-7 * np.eye(n_in)
    c_in = np.linalg.solve(lhs, B_in.T @ rhs + reg * (D2.T @ reg_rhs))
    return np.vstack([pts[0], c_in, pts[-1]])


def eval_periodic_cubic_bspline_1d(ctrl_r: np.ndarray, thetas: np.ndarray) -> np.ndarray:
    """Evaluate K-control periodic uniform cubic B-spline on [-pi, pi)."""
    c = np.asarray(ctrl_r, dtype=np.float64)
    k = len(c)
    # Map theta in [-pi, pi) -> s in [0, K)
    s = ((np.asarray(thetas, dtype=np.float64) + math.pi) / (2.0 * math.pi)) * k
    s = np.mod(s, float(k))
    idx0 = np.floor(s).astype(np.int64)
    t = s - idx0
    im1 = (idx0 - 1) % k
    i0 = idx0 % k
    ip1 = (idx0 + 1) % k
    ip2 = (idx0 + 2) % k
    b0 = ((1.0 - t) ** 3) / 6.0
    b1 = (3.0 * (t ** 3) - 6.0 * (t ** 2) + 4.0) / 6.0
    b2 = (-3.0 * (t ** 3) + 3.0 * (t ** 2) + 3.0 * t + 1.0) / 6.0
    b3 = (t ** 3) / 6.0
    return b0 * c[im1] + b1 * c[i0] + b2 * c[ip1] + b3 * c[ip2]


def fit_periodic_cubic_bspline_1d(thetas_obs: np.ndarray, r_obs: np.ndarray, weights: np.ndarray, k: int = 16, smooth_reg: float = 0.08) -> np.ndarray:
    """Fit K-control periodic uniform cubic B-spline to weighted polar envelope samples."""
    s = ((np.asarray(thetas_obs, dtype=np.float64) + math.pi) / (2.0 * math.pi)) * k
    s = np.mod(s, float(k))
    idx0 = np.floor(s).astype(np.int64)
    t = s - idx0
    n = len(s)
    B = np.zeros((n, k), dtype=np.float64)
    rows = np.arange(n)
    B[rows, (idx0 - 1) % k] += ((1.0 - t) ** 3) / 6.0
    B[rows, idx0 % k] += (3.0 * (t ** 3) - 6.0 * (t ** 2) + 4.0) / 6.0
    B[rows, (idx0 + 1) % k] += (-3.0 * (t ** 3) + 3.0 * (t ** 2) + 3.0 * t + 1.0) / 6.0
    B[rows, (idx0 + 2) % k] += (t ** 3) / 6.0

    w_sqrt = np.sqrt(np.maximum(weights, 1e-6))
    Bw = B * w_sqrt[:, None]
    rw = r_obs * w_sqrt

    # Periodic 2nd-difference laplacian regularizer
    L = np.zeros((k, k), dtype=np.float64)
    for j in range(k):
        L[j, (j - 1) % k] = 1.0
        L[j, j] = -2.0
        L[j, (j + 1) % k] = 1.0

    med_r = float(np.median(r_obs)) if len(r_obs) > 0 else 0.92
    lhs = Bw.T @ Bw + smooth_reg * (L.T @ L) + 0.015 * np.eye(k)
    rhs = Bw.T @ rw + 0.015 * med_r * np.ones(k)
    ctrl = np.linalg.solve(lhs, rhs)
    return np.clip(ctrl, 0.22, 1.45)


# ---------------------------------------------------------------------------
# Canonical 5-Scene Input Loader (Strictly Separating Build vs Quarantined Eval)
# ---------------------------------------------------------------------------


def load_v05_optional_curve_samples(v05_dir: Path | None) -> tuple[list[dict[str, Any]], np.ndarray]:
    """Optionally load 3D curve samples & swept tubes from v05 if available (never loads/trusts default lathe!)."""
    if v05_dir is None or not (v05_dir / "curve_network.json").is_file():
        return [], np.zeros((0, 3), dtype=np.float64)
    doc = json.loads(resolve_read_path(v05_dir / "curve_network.json").read_text(encoding="utf-8"))
    with np.load(resolve_read_path(v05_dir / "curve_controls.npz"), allow_pickle=False) as zp:
        ctrl_all = np.asarray(zp["control_points"], dtype=np.float64)
    trunks: list[dict[str, Any]] = []
    for g in doc.get("contour_generators", []):
        if g.get("generator_type") == "SWEPT_TUBE_ENVELOPE_3D":
            trunks.append({
                "spine_ctrl": np.asarray(g["spine_control_points"], dtype=np.float64),
                "radii_ctrl": np.asarray(g["control_radii"], dtype=np.float64),
            })
    samples = []
    for c in doc.get("curves", []):
        if c.get("role") == "COAXIAL_RING":
            continue
        s0, s1 = int(c["ctrl_slice"][0]), int(c["ctrl_slice"][1])
        pts = ctrl_all[s0:s1]
        if len(pts) < 2:
            continue
        t = np.linspace(0, len(pts) - 1, max(4, len(pts) * 4))
        samples.append(np.stack([np.interp(t, np.arange(len(pts)), col) for col in pts.T], axis=1))
    curve_pts = np.concatenate(samples, axis=0) if samples else np.zeros((0, 3), dtype=np.float64)
    return trunks, curve_pts


def load_canonical_scene(
    scene_name: str,
    codex_work_root: Path = Path("/home/u00134/Documents/Codex/2026-11-26/ficus-leaf-kernels-v04-hybrid-botanical/work"),
) -> tuple[SceneGaussianCloud, list[CalibratedBuildOrEvalView], list[CalibratedBuildOrEvalView], float, list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    """Load canonical cloud, 32 build views, 5 quarantined eval views, p_med, and optional v05 curves for any of the 5 scenes."""
    sc = scene_name.lower()
    if sc == "ficus":
        ficus_pkg = Path("/home/u00134/.gemini/antigravity/scratch/ficus_leaf_kernels_v01")
        if str(ficus_pkg) not in sys.path:
            sys.path.insert(0, str(ficus_pkg))
        from leaf_kernels.data_io import load_ficus_3dgs_cloud, load_ficus_views_and_v04_priors

        c_raw = load_ficus_3dgs_cloud()
        tr_raw, ev_raw, pr_raw = load_ficus_views_and_v04_priors()
        cloud = SceneGaussianCloud(
            means=c_raw.means,
            scales=c_raw.scales,
            quats_wxyz=c_raw.quats_wxyz,
            cov6=c_raw.cov6,
            surfel_normals=c_raw.surfel_normals,
            opacities=c_raw.opacities,
            rgb_dc=c_raw.rgb_dc,
            shs=c_raw.shs,
        )

        def _conv_view(vw: Any) -> CalibratedBuildOrEvalView:
            edt = distance_transform_edt(~(vw.skeleton | (vw.darkness > 0.22))).astype(np.float32)
            return CalibratedBuildOrEvalView(
                view_name=vw.view_name,
                split=vw.split,
                width=int(vw.width),
                height=int(vw.height),
                fx=float(vw.fx),
                fy=float(vw.fy),
                cx=float(vw.cx),
                cy=float(vw.cy),
                w2c=vw.w2c.astype(np.float64),
                c2w=vw.c2w.astype(np.float64),
                cam_center=vw.cam_center.astype(np.float64),
                rgb=vw.rgb.astype(np.float32),
                alpha=vw.alpha.astype(np.float32),
                depth=vw.front_depth.astype(np.float32),
                front_depth=vw.front_depth.astype(np.float32),
                depth_jump=vw.depth_jump.astype(np.float32),
                darkness=vw.darkness.astype(np.float32),
                skeleton=vw.skeleton.astype(bool),
                edge_dt=edt,
            )

        v05_dir = Path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/ficus_full_v05")
        trunks, curve_pts = load_v05_optional_curve_samples(v05_dir)
        return (
            cloud,
            [_conv_view(v) for v in tr_raw],
            [_conv_view(v) for v in ev_raw],
            float(pr_raw.median_pixel_scale),
            trunks,
            curve_pts,
            {"scene": "ficus", "p_med": float(pr_raw.median_pixel_scale)},
        )

    recon_root = resolve_read_path(codex_work_root / "full_reconstruction" / sc)
    inp_dir = recon_root / "input"
    manifest = json.loads(resolve_read_path(inp_dir / "manifest.json").read_text(encoding="utf-8"))
    with np.load(resolve_read_path(inp_dir / "cloud.npz"), allow_pickle=False) as cd:
        cloud = SceneGaussianCloud(
            means=cd["means"].astype(np.float32),
            scales=cd["scales"].astype(np.float32),
            quats_wxyz=cd["quats_wxyz"].astype(np.float32),
            cov6=cd["cov6"].astype(np.float32),
            surfel_normals=cd["surfel_normals"].astype(np.float32),
            opacities=cd["opacities"].astype(np.float32),
            rgb_dc=cd["rgb_dc"].astype(np.float32),
            shs=cd["shs"].astype(np.float32),
        )

    def _load_saved_view(vname: str, expected_split: str) -> CalibratedBuildOrEvalView:
        vp = resolve_read_path(inp_dir / "views" / f"{vname}.npz")
        with np.load(vp, allow_pickle=False) as vd:
            skel = vd["skeleton"].astype(bool)
            dark = vd["darkness"].astype(np.float32)
            edt = distance_transform_edt(~(skel | (dark > 0.22))).astype(np.float32)
            return CalibratedBuildOrEvalView(
                view_name=str(vname),
                split=expected_split,
                width=int(vd["width"]),
                height=int(vd["height"]),
                fx=float(vd["fx"]),
                fy=float(vd["fy"]),
                cx=float(vd["cx"]),
                cy=float(vd["cy"]),
                w2c=vd["w2c"].astype(np.float64),
                c2w=vd["c2w"].astype(np.float64),
                cam_center=vd["cam_center"].astype(np.float64),
                rgb=vd["rgb"].astype(np.float32),
                alpha=vd["alpha"].astype(np.float32),
                depth=vd["depth"].astype(np.float32),
                front_depth=vd["front_depth"].astype(np.float32),
                depth_jump=vd["depth_jump"].astype(np.float32),
                darkness=dark,
                skeleton=skel,
                edge_dt=edt,
            )

    train_views = [_load_saved_view(vn, "train") for vn in manifest["train_views"]]
    eval_views = [_load_saved_view(vn, "test") for vn in manifest["eval_views"]]
    assert not ({v.view_name for v in train_views} & {v.view_name for v in eval_views}), "Train/eval view leakage!"
    trunks, curve_pts = load_v05_optional_curve_samples(recon_root / "vector/v05")
    return cloud, train_views, eval_views, float(manifest["p_med"]), trunks, curve_pts, manifest


def export_standard_sh3_ply(path: str | Path, cloud: SceneGaussianCloud) -> Path:
    """Export standard 3DGS PLY preserving full degree-3 SH coefficients."""
    dest = resolve_write_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = len(cloud.means)
    c0 = 0.28209479177387814
    f_dc = ((cloud.rgb_dc - 0.5) / c0).astype(np.float32)
    f_rest = cloud.shs[:, 1:, :].transpose(0, 2, 1).reshape(n, 45).astype(np.float32)
    op_clamped = np.clip(cloud.opacities, 1e-5, 1.0 - 1e-5)
    raw_opac = np.log(op_clamped / (1.0 - op_clamped)).astype(np.float32)
    raw_scale = np.log(np.maximum(cloud.scales, 1e-7)).astype(np.float32)

    dtype_fields = [
        ("x", "f4"), ("y", "f4"), ("z", "f4"),
        ("nx", "f4"), ("ny", "f4"), ("nz", "f4"),
        ("f_dc_0", "f4"), ("f_dc_1", "f4"), ("f_dc_2", "f4"),
    ]
    for k in range(45):
        dtype_fields.append((f"f_rest_{k}", "f4"))
    dtype_fields.extend([
        ("opacity", "f4"),
        ("scale_0", "f4"), ("scale_1", "f4"), ("scale_2", "f4"),
        ("rot_0", "f4"), ("rot_1", "f4"), ("rot_2", "f4"), ("rot_3", "f4"),
    ])

    arr = np.empty(n, dtype=dtype_fields)
    arr["x"], arr["y"], arr["z"] = cloud.means[:, 0], cloud.means[:, 1], cloud.means[:, 2]
    arr["nx"], arr["ny"], arr["nz"] = cloud.surfel_normals[:, 0], cloud.surfel_normals[:, 1], cloud.surfel_normals[:, 2]
    arr["f_dc_0"], arr["f_dc_1"], arr["f_dc_2"] = f_dc[:, 0], f_dc[:, 1], f_dc[:, 2]
    for k in range(45):
        arr[f"f_rest_{k}"] = f_rest[:, k]
    arr["opacity"] = raw_opac
    arr["scale_0"], arr["scale_1"], arr["scale_2"] = raw_scale[:, 0], raw_scale[:, 1], raw_scale[:, 2]
    arr["rot_0"], arr["rot_1"], arr["rot_2"], arr["rot_3"] = (
        cloud.quats_wxyz[:, 0], cloud.quats_wxyz[:, 1], cloud.quats_wxyz[:, 2], cloud.quats_wxyz[:, 3]
    )

    tmp = dest.with_name(f"{dest.name}.tmp-{os.getpid()}")
    PlyData([PlyElement.describe(arr, "vertex")], text=False).write(str(tmp))
    os.replace(tmp, dest)
    return dest


_ORGAN_KIND_TO_INT = {"LAMINAR_BLADE": 0, "VOLUMETRIC_CLUSTER": 1}
_INT_TO_ORGAN_KIND = {0: "LAMINAR_BLADE", 1: "VOLUMETRIC_CLUSTER"}
_TIER_TO_INT = {"OUTER_ENCLOSED": 0, "MID_PARTIAL_OCCLUDED": 1, "DEEP_OCCLUDED": 2}
_INT_TO_TIER = {0: "OUTER_ENCLOSED", 1: "MID_PARTIAL_OCCLUDED", 2: "DEEP_OCCLUDED"}


def save_universal_model_npz(path: str | Path, model: UniversalBotanicalModel) -> Path:
    """Atomically serialize UniversalBotanicalModel using pure numeric arrays (zero pickle)."""
    dest = resolve_write_path(path)
    if dest.suffix != ".npz":
        dest = dest.with_suffix(".npz")
    dest.parent.mkdir(parents=True, exist_ok=True)

    n_org = len(model.organs)
    k_ctrl = len(model.organs[0].periodic_ctrl_r) if n_org > 0 else 24
    org_ids = np.array([o.organ_id for o in model.organs], dtype=np.int32)
    org_kinds = np.array([_ORGAN_KIND_TO_INT[o.organ_kind] for o in model.organs], dtype=np.int32)
    org_tiers = np.array([_TIER_TO_INT[o.visibility_tier] for o in model.organs], dtype=np.int32)
    org_parents = np.array([o.parent_chain_id for o in model.organs], dtype=np.int32)
    org_pbase = np.array([o.p_base for o in model.organs], dtype=np.float64).reshape(n_org, 3)
    org_ctr = np.array([o.centroid for o in model.organs], dtype=np.float64).reshape(n_org, 3)
    org_e1 = np.array([o.e1 for o in model.organs], dtype=np.float64).reshape(n_org, 3)
    org_e2 = np.array([o.e2 for o in model.organs], dtype=np.float64).reshape(n_org, 3)
    org_e3 = np.array([o.e3 for o in model.organs], dtype=np.float64).reshape(n_org, 3)
    org_lwt = np.array([[o.length, o.width, o.thickness, o.apex_cusp_gamma] for o in model.organs], dtype=np.float64).reshape(n_org, 4)
    org_ctrl = np.array([o.periodic_ctrl_r for o in model.organs], dtype=np.float64).reshape(n_org, k_ctrl)
    org_cam8 = np.array([o.camber_coef8 for o in model.organs], dtype=np.float64).reshape(n_org, 8)
    org_rgb = np.array([o.mean_rgb for o in model.organs], dtype=np.float32).reshape(n_org, 3)

    n_st = len(model.stem_chains)
    st_meta_i = np.array(
        [[s.chain_id, s.level, s.parent_chain_id, s.supported_kernel_count, int(s.basal_anchored)] for s in model.stem_chains],
        dtype=np.int32,
    ).reshape(n_st, 5)
    st_meta_f = np.array([[s.parent_u, s.radius_base, s.radius_tip] for s in model.stem_chains], dtype=np.float64).reshape(n_st, 3)
    st_counts = np.array([len(s.ctrl_points) for s in model.stem_chains], dtype=np.int32)
    st_ctrl_cat = np.vstack([s.ctrl_points for s in model.stem_chains]).astype(np.float64) if n_st > 0 else np.zeros((0, 3), dtype=np.float64)

    tmp = dest.with_name(f"{dest.stem}.tmp-{os.getpid()}.npz")
    np.savez_compressed(
        tmp,
        scene_utf8=np.frombuffer(model.scene_name.encode("utf-8"), dtype=np.uint8),
        p_med=np.float64(model.p_med),
        sup_regime_utf8=np.frombuffer(model.support.regime.encode("utf-8"), dtype=np.uint8),
        sup_verts=model.support.vertices.astype(np.float32),
        sup_faces=model.support.faces.astype(np.int32),
        sup_z=np.array([model.support.rim_z, model.support.vessel_bot_z], dtype=np.float64),
        sup_mask=model.support.support_kernel_mask.astype(bool),
        stand_mask=model.support.stand_kernel_mask.astype(bool),
        st_meta_i=st_meta_i,
        st_meta_f=st_meta_f,
        st_counts=st_counts,
        st_ctrl_cat=st_ctrl_cat,
        org_ids=org_ids,
        org_kinds=org_kinds,
        org_tiers=org_tiers,
        org_parents=org_parents,
        org_pbase=org_pbase,
        org_ctr=org_ctr,
        org_e1=org_e1,
        org_e2=org_e2,
        org_e3=org_e3,
        org_lwt=org_lwt,
        org_ctrl=org_ctrl,
        org_cam8=org_cam8,
        org_rgb=org_rgb,
        means=model.cloud.means.astype(np.float32),
        scales=model.cloud.scales.astype(np.float32),
        quats_wxyz=model.cloud.quats_wxyz.astype(np.float32),
        cov6=model.cloud.cov6.astype(np.float32),
        surfel_normals=model.cloud.surfel_normals.astype(np.float32),
        opacities=model.cloud.opacities.astype(np.float32),
        rgb_dc=model.cloud.rgb_dc.astype(np.float32),
        shs=model.cloud.shs.astype(np.float32),
        kernel_labels=model.kernel_labels.astype(np.int32),
        stem_owner=model.stem_owner.astype(np.int32),
    )
    os.replace(tmp, dest)
    return dest


def load_universal_model_npz(path: str | Path) -> UniversalBotanicalModel:
    """Deserialize UniversalBotanicalModel safely with allow_pickle=False."""
    src = resolve_read_path(path)
    with np.load(src, allow_pickle=False) as d:
        scene_name = bytes(d["scene_utf8"].tolist()).decode("utf-8")
        p_med = float(d["p_med"])
        sup_regime = bytes(d["sup_regime_utf8"].tolist()).decode("utf-8")
        sup_z = d["sup_z"].astype(np.float64)
        support = BasalSupportModel(
            regime=sup_regime,
            vertices=d["sup_verts"].astype(np.float32),
            faces=d["sup_faces"].astype(np.int32),
            rim_z=float(sup_z[0]),
            vessel_bot_z=float(sup_z[1]),
            support_kernel_mask=d["sup_mask"].astype(bool),
            stand_kernel_mask=d["stand_mask"].astype(bool),
        )
        cloud = SceneGaussianCloud(
            means=d["means"].astype(np.float32),
            scales=d["scales"].astype(np.float32),
            quats_wxyz=d["quats_wxyz"].astype(np.float32),
            cov6=d["cov6"].astype(np.float32),
            surfel_normals=d["surfel_normals"].astype(np.float32),
            opacities=d["opacities"].astype(np.float32),
            rgb_dc=d["rgb_dc"].astype(np.float32),
            shs=d["shs"].astype(np.float32),
        )
        kernel_labels = d["kernel_labels"].astype(np.int32)
        stem_owner = d["stem_owner"].astype(np.int32)

        st_meta_i = d["st_meta_i"]
        st_meta_f = d["st_meta_f"]
        st_counts = d["st_counts"]
        st_ctrl_cat = d["st_ctrl_cat"]
        stem_chains: list[StemSplineChain] = []
        off = 0
        for i in range(len(st_counts)):
            cnt = int(st_counts[i])
            stem_chains.append(
                StemSplineChain(
                    chain_id=int(st_meta_i[i, 0]),
                    level=int(st_meta_i[i, 1]),
                    parent_chain_id=int(st_meta_i[i, 2]),
                    parent_u=float(st_meta_f[i, 0]),
                    ctrl_points=st_ctrl_cat[off : off + cnt].astype(np.float64),
                    radius_base=float(st_meta_f[i, 1]),
                    radius_tip=float(st_meta_f[i, 2]),
                    supported_kernel_count=int(st_meta_i[i, 3]),
                    basal_anchored=bool(st_meta_i[i, 4]),
                )
            )
            off += cnt

        org_ids = d["org_ids"]
        org_kinds = d["org_kinds"]
        org_tiers = d["org_tiers"]
        org_parents = d["org_parents"]
        org_pbase = d["org_pbase"]
        org_ctr = d["org_ctr"]
        org_e1 = d["org_e1"]
        org_e2 = d["org_e2"]
        org_e3 = d["org_e3"]
        org_lwt = d["org_lwt"]
        org_ctrl = d["org_ctrl"]
        org_cam8 = d["org_cam8"]
        org_rgb = d["org_rgb"]

        organs: list[AdaptiveOrganPatch] = []
        for i in range(len(org_ids)):
            oid = int(org_ids[i])
            organs.append(
                AdaptiveOrganPatch(
                    organ_id=oid,
                    organ_kind=_INT_TO_ORGAN_KIND[int(org_kinds[i])],
                    visibility_tier=_INT_TO_TIER[int(org_tiers[i])],
                    parent_chain_id=int(org_parents[i]),
                    p_base=org_pbase[i].astype(np.float64),
                    centroid=org_ctr[i].astype(np.float64),
                    e1=org_e1[i].astype(np.float64),
                    e2=org_e2[i].astype(np.float64),
                    e3=org_e3[i].astype(np.float64),
                    length=float(org_lwt[i, 0]),
                    width=float(org_lwt[i, 1]),
                    thickness=float(org_lwt[i, 2]),
                    periodic_ctrl_r=org_ctrl[i].astype(np.float64),
                    apex_cusp_gamma=float(org_lwt[i, 3]),
                    camber_coef8=org_cam8[i].astype(np.float64),
                    kernel_indices=np.flatnonzero(kernel_labels == oid).astype(np.int32),
                    mean_rgb=org_rgb[i].astype(np.float32),
                )
            )

    return UniversalBotanicalModel(
        scene_name=scene_name,
        p_med=p_med,
        support=support,
        stem_chains=stem_chains,
        organs=organs,
        cloud=cloud,
        kernel_labels=kernel_labels,
        stem_owner=stem_owner,
    )
