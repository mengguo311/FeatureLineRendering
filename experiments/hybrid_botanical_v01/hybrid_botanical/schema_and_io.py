"""Scene-agnostic unified schema, clamped B-spline math, and strict read/write boundary isolation."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
from PIL import Image
from plyfile import PlyData, PlyElement
from scipy.interpolate import BSpline
from scipy.ndimage import minimum_filter
from scipy.spatial.transform import Rotation
from scipy.special import logit

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

READ_ALLOWED_ROOTS: tuple[Path, ...] = (
    _PACKAGE_ROOT,
    Path("/mnt/hdd1/u00134/radegs_paper_reproduction_v01").resolve(),
    Path("/home/u00134/cglib/data/full").resolve(),
    Path("/home/u00134/3dgs_line").resolve(),
    Path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01").resolve(),
    Path("/home/u00134/.gemini/antigravity/scratch/ficus_leaf_kernels_v01").resolve(),
    Path("/home/u00134/.gemini/antigravity/scratch/hybrid_botanical_v01").resolve(),
    Path("/home/u00134/.gemini/antigravity/brain/48eb7555-77d2-4416-a9b8-173755682d02").resolve(),
)

# STRICT WRITE ISOLATION: ONLY allow writes inside hybrid_botanical_v01 / package root and active conversation artifact dir!
WRITE_ALLOWED_ROOTS: tuple[Path, ...] = (
    _PACKAGE_ROOT,
    Path("/home/u00134/.gemini/antigravity/scratch/hybrid_botanical_v01").resolve(),
    Path("/home/u00134/.gemini/antigravity/brain/48eb7555-77d2-4416-a9b8-173755682d02").resolve(),
)

LABEL_POT_BASE = -1
LABEL_WOOD_SKELETON = -2


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
    raise PermissionError(f"Write path '{resolved}' blocked to protect upstream workspaces!")


def atomic_write_text(path: str | Path, content: str) -> Path:
    dest = resolve_write_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.tmp-{os.getpid()}")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, dest)
    return dest


# ---------------------------------------------------------------------------
# Clamped Cubic B-Spline Utilities (1D Profile & 3D Space Curves)
# ---------------------------------------------------------------------------


def clamped_cubic_knots(num_ctrl: int) -> np.ndarray:
    """Clamped uniform knot vector on [0, 1] for M >= 4 control points (degree 3) or M == 2..3."""
    deg = min(3, num_ctrl - 1)
    n_int = num_ctrl - deg - 1
    internal = np.linspace(0.0, 1.0, n_int + 2, dtype=np.float64)[1:-1] if n_int > 0 else np.empty(0, dtype=np.float64)
    return np.concatenate([np.zeros(deg + 1), internal, np.ones(deg + 1)])


def eval_clamped_bspline(ctrl: np.ndarray, u_query: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate clamped B-spline curve and first derivative at u_query in [0, 1]."""
    c = np.asarray(ctrl, dtype=np.float64)
    m = len(c)
    u = np.clip(np.asarray(u_query, dtype=np.float64), 0.0, 1.0)
    if m == 2:
        pts = (1.0 - u)[:, None] * c[0] + u[:, None] * c[1]
        d1 = np.repeat((c[1] - c[0])[None, :], len(u), axis=0)
        return pts, d1
    deg = min(3, m - 1)
    knots = clamped_cubic_knots(m)
    spl = BSpline(knots, c, deg, extrapolate=False)
    return spl(u), spl.derivative(1)(u)


def fit_clamped_bspline_3d(points: np.ndarray, num_ctrl: int = 6, reg: float = 1e-4) -> np.ndarray:
    """Least-squares clamped cubic B-spline fit with exact pinned endpoints."""
    pts = np.asarray(points, dtype=np.float64)
    n = len(pts)
    if n <= 2 or num_ctrl <= 2:
        return np.vstack([pts[0], pts[-1]])
    m = min(num_ctrl, n)
    diffs = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(diffs)])
    total = float(cum[-1])
    if total < 1e-8:
        return np.repeat(pts[:1], m, axis=0)
    u = cum / total
    deg = min(3, m - 1)
    knots = clamped_cubic_knots(m)
    B = BSpline(knots, np.eye(m, dtype=np.float64), deg)(u)
    if m == 2:
        return np.vstack([pts[0], pts[-1]])

    # Pin ctrl[0] = pts[0] and ctrl[-1] = pts[-1]; solve interior control points cleanly
    rhs = pts - np.outer(B[:, 0], pts[0]) - np.outer(B[:, -1], pts[-1])
    B_in = B[:, 1:-1]
    D2 = np.eye(m - 2)
    c_in = np.linalg.lstsq(B_in.T @ B_in + reg * (D2.T @ D2), B_in.T @ rhs, rcond=None)[0]
    return np.vstack([pts[0:1], c_in, pts[-1:]])


# ---------------------------------------------------------------------------
# Unified 3-Tier Hybrid Botanical Primitive Schema
# ---------------------------------------------------------------------------


@dataclass
class GaussianCloudBank:
    """Full 3DGS Gaussian bank for fast CUDA splatting & standard .ply export."""

    means: np.ndarray          # (N, 3) float32
    scales: np.ndarray         # (N, 3) float32 linear scales
    quats_wxyz: np.ndarray     # (N, 4) float32 unit quaternions
    cov6: np.ndarray           # (N, 6) float32 upper-triangular 3D covariance
    surfel_normals: np.ndarray # (N, 3) float32 unit surfel normal
    opacities: np.ndarray      # (N,) float32 in (0, 1)
    rgb: np.ndarray            # (N, 3) float32 albedo/stylized RGB in [0, 1]
    kernel_labels: np.ndarray  # (N,) int32: -1=POT, -2=WOOD_SKELETON, >=0=leaf_id


@dataclass
class LathePotPrimitive:
    """Layer 1: Coaxial surface-of-revolution pot & soil base."""

    axis_origin: np.ndarray  # (3,) float64
    axis_dir: np.ndarray     # (3,) float64
    profile_h: np.ndarray    # (P,) float64 axial heights
    profile_r: np.ndarray    # (P,) float64 outer radii
    h_max: float


@dataclass
class BranchSplineNode:
    """Single 1D parametric B-spline branch/twig/stalk/petiole segment in the 4-level botanical tree."""

    branch_id: int
    level: int                 # 0=PRIMARY_TRUNK, 1=SECONDARY_BRANCH, 2=ROSETTE_STALK, 3=PETIOLE_LINK
    parent_branch_id: int      # -1 for root trunks, else parent branch_id
    parent_u_attach: float     # attachment parameter u in [0, 1] along parent branch
    ctrl_points: np.ndarray    # (M_b, 3) float64 clamped B-spline control points (u=0 proximal -> u=1 distal)
    radius_base: float         # proximal radius (m) obeying da Vinci pipe model
    radius_tip: float          # distal radius (m)
    child_branch_ids: list[int] = field(default_factory=list)
    attached_leaf_ids: list[int] = field(default_factory=list)


@dataclass
class BotanicalTreeGraph:
    """Layer 2: Connected 4-level 1D B-spline skeletal tree + bound wood Gaussian attachment table."""

    branches: list[BranchSplineNode]
    rosette_hub_positions: np.ndarray  # (H, 3) float64 palmate umbel hub centers
    leaf_to_hub_id: np.ndarray         # (L,) int32 hub index for each leaf
    leaf_to_petiole_branch: np.ndarray # (L,) int32 level-3 petiole branch_id for each leaf
    # Binding of every WOOD_SKELETON Gaussian (kernel_labels == -2) to its host branch spline:
    wood_kernel_indices: np.ndarray    # (W,) int32 indices into GaussianCloudBank
    wood_host_branch: np.ndarray       # (W,) int32 host branch_id
    wood_u_param: np.ndarray           # (W,) float32 u in [0, 1] along host branch
    wood_local_n1: np.ndarray          # (W,) float32 radial offset along Bishop normal N1
    wood_local_n2: np.ndarray          # (W,) float32 radial offset along Bishop binormal N2
    num_infilled_twig_kernels: int = 0


@dataclass
class DualArcTrimmedLeafPatch:
    """Layer 3: Single 2D Gaussian leaf patch coupled to & trimmed by a closed Dual-Arc Cubic B-Spline.

    Closed boundary parameterization on cambered blade surface w_l(u, v):
      - Petiole cusp at s = 0 (u = 0, v = 0) -> p_base
      - Pointed apex cusp at s = 1 (u = L_l, v = 0) -> p_apex
      - Left margin clamped cubic B-spline v_left(s) >= 0 with ctrl [0, q_L1, q_L2, q_L3, q_L4, 0] * L_l
      - Right margin clamped cubic B-spline v_right(s) <= 0 with ctrl [0, -q_R1, -q_R2, -q_R3, -q_R4, 0] * L_l
      Any surface point (u, v) is analytically INSIDE iff 0 <= u/L_l <= 1 and v_right(u/L_l) <= v <= v_left(u/L_l)!
    """

    leaf_id: int
    parent_branch_id: int         # level-3 petiole branch_id
    hub_id: int                   # palmate rosette hub_id
    visibility_tier: str          # "OUTER_ENCLOSED", "MID_PARTIAL_OCCLUDED", "DEEP_OCCLUDED"
    p_base: np.ndarray            # (3,) float64 petiole hinge anchor (s=0)
    e1: np.ndarray                # (3,) float64 anatomical midrib unit axis (petiole -> apex)
    e2: np.ndarray                # (3,) float64 bilateral width unit axis
    e3: np.ndarray                # (3,) float64 blade normal unit axis (e1 x e2 = e3)
    blade_length: float           # L_l (m)
    v_left_ctrl: np.ndarray       # (6,) float64 clamped cubic B-spline widths >= 0 (ends = 0.0)
    v_right_ctrl: np.ndarray      # (6,) float64 clamped cubic B-spline widths <= 0 (ends = 0.0)
    camber_coef: np.ndarray       # (4,) float64 w(u, v) = c0 + c1*u + c2*u^2 + c3*v^2
    eigen_pca_code: np.ndarray    # (3,) float64 coordinates in learned Eigen-Leaf shape space
    kernel_indices: np.ndarray    # (K_l,) int32 indices into GaussianCloudBank
    infilled_kernel_count: int    # count of amodal shadow-zone Gaussians added to complete occluded leaf
    area_cm2: float               # analytical integral int_0^L (v_left(u/L) - v_right(u/L)) du * 1e4

    def eval_3d_boundary_arcs(self, n_per_arc: int = 32) -> tuple[np.ndarray, np.ndarray]:
        """Evaluate 3D points along Left (base->apex) and Right (base->apex) cubic B-spline margins."""
        s = np.linspace(0.0, 1.0, n_per_arc, dtype=np.float64)
        u = s * self.blade_length
        vl, _ = eval_clamped_bspline(self.v_left_ctrl[:, None], s)
        vr, _ = eval_clamped_bspline(self.v_right_ctrl[:, None], s)
        vl = vl[:, 0]
        vr = vr[:, 0]
        c = self.camber_coef
        wl = c[0] + c[1] * u + c[2] * (u ** 2) + c[3] * (vl ** 2)
        wr = c[0] + c[1] * u + c[2] * (u ** 2) + c[3] * (vr ** 2)
        pts_l = self.p_base[None, :] + u[:, None] * self.e1 + vl[:, None] * self.e2 + wl[:, None] * self.e3
        pts_r = self.p_base[None, :] + u[:, None] * self.e1 + vr[:, None] * self.e2 + wr[:, None] * self.e3
        return pts_l, pts_r


@dataclass
class EigenLeafPriorModel:
    """Learned single-plant self-similarity leaf shape space from high-confidence OUTER_ENCLOSED leaves."""

    mean_norm_ctrl8: np.ndarray   # (8,) float64 [v_L1..4 / L, -v_R1..4 / L]
    pca_components: np.ndarray    # (3, 8) float64 top-3 Eigen-Leaf principal directions
    pca_std: np.ndarray           # (3,) float64 singular standard deviations
    median_length: float          # (m)
    median_width_ratio: float     # median max_width / length
    median_camber: np.ndarray     # (4,) float64


@dataclass
class HybridBotanicalPrimitive:
    """Complete 3-Tier Hybrid Vector-Gaussian Botanical Model."""

    scene_name: str
    pot_base: LathePotPrimitive
    skeleton: BotanicalTreeGraph
    leaves: list[DualArcTrimmedLeafPatch]
    eigen_prior: EigenLeafPriorModel
    cloud: GaussianCloudBank
    median_pixel_scale: float


@dataclass
class CalibratedSceneView:
    """Calibrated multi-view camera with RGB, alpha, front_depth, and C2L50 edge maps."""

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
    front_depth: np.ndarray
    darkness: np.ndarray
    skeleton: np.ndarray
    edge_dt: np.ndarray


def build_cloud_bank(
    means: np.ndarray,
    scales: np.ndarray,
    quats_wxyz: np.ndarray,
    opacities: np.ndarray,
    rgb: np.ndarray,
    kernel_labels: np.ndarray,
) -> GaussianCloudBank:
    """Construct GaussianCloudBank with freshly recomputed 3D covariance cov6 and surfel normals."""
    q = quats_wxyz.astype(np.float32, copy=True)
    q /= np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-12)
    sc = np.maximum(scales.astype(np.float32), 1e-7)
    R = Rotation.from_quat(q[:, [1, 2, 3, 0]]).as_matrix().astype(np.float32)
    cov3 = (R * (sc[:, None, :] ** 2)) @ R.transpose(0, 2, 1)
    cov6 = np.ascontiguousarray(cov3[:, [0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]])
    min_ax = np.argmin(sc, axis=1)
    nrms = np.ascontiguousarray(R[np.arange(len(means)), :, min_ax])
    return GaussianCloudBank(
        means=np.ascontiguousarray(means, dtype=np.float32),
        scales=np.ascontiguousarray(sc, dtype=np.float32),
        quats_wxyz=np.ascontiguousarray(q, dtype=np.float32),
        cov6=cov6,
        surfel_normals=nrms,
        opacities=np.ascontiguousarray(np.clip(opacities, 1e-4, 0.998), dtype=np.float32),
        rgb=np.ascontiguousarray(np.clip(rgb, 0.0, 1.0), dtype=np.float32),
        kernel_labels=np.ascontiguousarray(kernel_labels, dtype=np.int32),
    )


def export_standard_3dgs_ply(path: str | Path, cloud: GaussianCloudBank) -> Path:
    """Export GaussianCloudBank as a standard 3DGS .ply viewable in SuperSplat / SIBR / PlayCanvas."""
    dest = resolve_write_path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = len(cloud.means)
    dtype_fields = [
        ("x", "f4"), ("y", "f4"), ("z", "f4"),
        ("nx", "f4"), ("ny", "f4"), ("nz", "f4"),
        ("f_dc_0", "f4"), ("f_dc_1", "f4"), ("f_dc_2", "f4"),
        ("opacity", "f4"),
        ("scale_0", "f4"), ("scale_1", "f4"), ("scale_2", "f4"),
        ("rot_0", "f4"), ("rot_1", "f4"), ("rot_2", "f4"), ("rot_3", "f4"),
    ]
    arr = np.empty(n, dtype=dtype_fields)
    arr["x"], arr["y"], arr["z"] = cloud.means[:, 0], cloud.means[:, 1], cloud.means[:, 2]
    arr["nx"], arr["ny"], arr["nz"] = cloud.surfel_normals[:, 0], cloud.surfel_normals[:, 1], cloud.surfel_normals[:, 2]
    dc = (np.clip(cloud.rgb, 0.0, 1.0) - 0.5) / 0.28209479177387814
    arr["f_dc_0"], arr["f_dc_1"], arr["f_dc_2"] = dc[:, 0], dc[:, 1], dc[:, 2]
    arr["opacity"] = logit(np.clip(cloud.opacities, 1e-4, 0.999)).astype(np.float32)
    ls = np.log(np.maximum(cloud.scales, 1e-7))
    arr["scale_0"], arr["scale_1"], arr["scale_2"] = ls[:, 0], ls[:, 1], ls[:, 2]
    arr["rot_0"], arr["rot_1"], arr["rot_2"], arr["rot_3"] = (
        cloud.quats_wxyz[:, 0], cloud.quats_wxyz[:, 1], cloud.quats_wxyz[:, 2], cloud.quats_wxyz[:, 3]
    )
    tmp = dest.with_name(f"{dest.name}.tmp-{os.getpid()}")
    PlyData([PlyElement.describe(arr, "vertex")], text=False).write(str(tmp))
    os.replace(tmp, dest)
    return dest


def load_upstream_ficus_inputs(
    v05_dir: str | Path = "/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/ficus_full_v05",
    leaf_v03_npz: str | Path = "/home/u00134/.gemini/antigravity/scratch/ficus_leaf_kernels_v01/outputs/ficus_multistyle_v03/m1_m2_per_leaf_kernels.npz",
    leaf_v01_json: str | Path = "/home/u00134/.gemini/antigravity/scratch/ficus_leaf_kernels_v01/outputs/ficus_leaf_baseline_v01/leaf_instances.json",
    c2l_root: str | Path = "/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_multiview05_v01",
    cglib_ficus: str | Path = "/home/u00134/cglib/data/full/ficus",
    extra_cache: str | Path = "/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/cache_ficus_c2l_views",
) -> dict[str, Any]:
    """Read-only loader gathering v05 1D curves/trunks/pot + M1+M2 472-leaf Gaussians + 32 train & 5 test views."""
    from scipy.ndimage import distance_transform_edt

    v05_p = resolve_read_path(v05_dir)
    npz_p = resolve_read_path(leaf_v03_npz)
    js_p = resolve_read_path(leaf_v01_json)
    c2l = resolve_read_path(c2l_root)
    cglib = resolve_read_path(cglib_ficus)
    cache_p = resolve_read_path(extra_cache)

    # 1. Load M1+M2 297,343-kernel cloud & 472 leaf metadata
    with np.load(npz_p, allow_pickle=False) as zk:
        cloud = build_cloud_bank(
            means=zk["means"],
            scales=zk["scales"],
            quats_wxyz=zk["quats_wxyz"],
            opacities=zk["opacities"],
            rgb=zk["rgb_dc"],
            kernel_labels=zk["kernel_leaf_id"],
        )
    leaf_meta_list = json.loads(js_p.read_text(encoding="utf-8"))["leaves"]

    # 2. Load v05 Lathe pot, 5 SweptTube trunks, and 3D canopy leaf-rim curves
    net_doc = json.loads((v05_p / "curve_network.json").read_text(encoding="utf-8"))
    with np.load(v05_p / "curve_controls.npz", allow_pickle=False) as zc:
        all_ctrl = np.array(zc["control_points"], dtype=np.float64)

    pot_spec = LathePotPrimitive(
        axis_origin=np.array([-0.02236, 0.01663, -0.0001], dtype=np.float64),
        axis_dir=np.array([-0.00227, 0.00283, 0.99999], dtype=np.float64),
        profile_h=np.linspace(-0.82, -0.50, 16),
        profile_r=np.full(16, 0.16),
        h_max=-0.504,
    )
    swept_trunks: list[dict[str, Any]] = []
    for cg in net_doc.get("contour_generators", []):
        if cg.get("generator_type") == "LATHE_ENVELOPE_3D":
            ph = np.asarray(cg["profile_h"], dtype=np.float64)
            pr = np.asarray(cg["profile_r"], dtype=np.float64)
            pot_spec = LathePotPrimitive(
                axis_origin=np.asarray(cg["axis_origin"], dtype=np.float64),
                axis_dir=np.asarray(cg["axis_dir"], dtype=np.float64),
                profile_h=ph,
                profile_r=pr,
                h_max=float(ph.max()),
            )
        elif cg.get("generator_type") == "SWEPT_TUBE_ENVELOPE_3D":
            swept_trunks.append({
                "spine_ctrl": np.asarray(cg["spine_control_points"], dtype=np.float64),
                "radii_ctrl": np.asarray(cg["control_radii"], dtype=np.float64),
            })

    rim_pts_list: list[np.ndarray] = []
    rim_tng_list: list[np.ndarray] = []
    for ce in net_doc.get("curves", []):
        if ce.get("role") == "COAXIAL_RING":
            continue
        s0, s1 = ce["ctrl_slice"]
        c_pts = all_ctrl[s0:s1]
        if len(c_pts) < 2 or float(c_pts[:, 2].max()) < pot_spec.h_max:
            continue
        if ce["primitive_type"] == "ARC_3D" and len(c_pts) == 3 and "arc_geometry" in ce:
            ag = ce["arc_geometry"]
            ctr = np.asarray(ag["center"], dtype=np.float64)
            nrm = np.asarray(ag["normal"], dtype=np.float64)
            rad = float(ag["radius"])
            sw = math.radians(float(ag["sweep_deg"]))
            e1_a = (c_pts[0] - ctr) / max(rad, 1e-8)
            e2_a = np.cross(nrm, e1_a)
            th = np.linspace(0.0, sw, max(6, int(round(rad * sw / 0.0025))))
            pts_s = ctr[None, :] + rad * (np.cos(th)[:, None] * e1_a + np.sin(th)[:, None] * e2_a)
        else:
            u_s = np.linspace(0.0, len(c_pts) - 1, max(5, len(c_pts) * 5))
            k0 = np.clip(np.floor(u_s).astype(int), 0, len(c_pts) - 2)
            wk = u_s - k0
            pts_s = (1.0 - wk)[:, None] * c_pts[k0] + wk[:, None] * c_pts[k0 + 1]
        tng = np.gradient(pts_s, axis=0)
        tng /= np.maximum(np.linalg.norm(tng, axis=1, keepdims=True), 1e-9)
        rim_pts_list.append(pts_s)
        rim_tng_list.append(tng)

    with np.load(c2l / "arms/C/scenes/ficus/full/SHARED_CONTROL_AND_SAMPLING.npz", allow_pickle=False) as scs:
        p_med = float(np.median(scs["node_pixel"]))

    # 3. Load exact ground-truth calibrated cameras (seed_1729 + transforms_train/val)
    seed_cams = json.loads(
        resolve_read_path("/home/u00134/3dgs_line/tier1/out/multiscene_foundation/training/ficus/seed_1729/checkpoints/cameras.json").read_text(encoding="utf-8")
    )
    cam_lookup: dict[str, dict[str, Any]] = {}
    for c in seed_cams:
        sp = "test" if int(c["id"]) < 16 else "train"
        vn = f"{sp}_{c['img_name']}"
        c2w_m = np.eye(4, dtype=np.float64)
        c2w_m[:3, :3] = np.asarray(c["rotation"], dtype=np.float64)
        c2w_m[:3, 3] = np.asarray(c["position"], dtype=np.float64)
        cam_lookup[vn] = {
            "split": sp, "width": int(c["width"]), "height": int(c["height"]),
            "fx": float(c["fx"]), "fy": float(c["fy"]),
            "cx": 0.5 * float(c["width"]) - 0.5, "cy": 0.5 * float(c["height"]) - 0.5,
            "w2c": np.linalg.inv(c2w_m),
        }
    gl_flip = np.diag([1.0, -1.0, -1.0, 1.0])
    for sp, tf_name in (("train", "transforms_train.json"), ("test", "transforms_val.json")):
        tf_doc = json.loads(resolve_read_path(cglib / tf_name).read_text(encoding="utf-8"))
        fx_f = 0.5 * 800.0 / math.tan(0.5 * float(tf_doc["camera_angle_x"]))
        for fr in tf_doc["frames"]:
            vn = f"{sp}_{Path(fr['file_path']).name}"
            c2w_m = np.asarray(fr["transform_matrix"], dtype=np.float64) @ gl_flip
            cam_lookup.setdefault(vn, {
                "split": sp, "width": 800, "height": 800, "fx": fx_f, "fy": fx_f,
                "cx": 399.5, "cy": 399.5, "w2c": np.linalg.inv(c2w_m),
            })
            cam_lookup[vn]["file_path"] = str(cglib / f"{fr['file_path']}.png")

    def _mk_view(vname: str, rgb: np.ndarray, alpha: np.ndarray, depth: np.ndarray, dark: np.ndarray, skel: np.ndarray) -> CalibratedSceneView:
        m = cam_lookup[vname]
        w2c = m["w2c"]
        c2w = np.linalg.inv(w2c)
        valid_fg = (alpha > 0.55) & np.isfinite(depth) & (depth > 0.15)
        sent = np.where(valid_fg, depth, 1e6).astype(np.float32)
        m3 = minimum_filter(sent, size=3)
        m5 = minimum_filter(sent, size=5)
        fd = np.where(m3 < 9e5, m3, np.where(m5 < 9e5, m5, depth)).astype(np.float32)
        emask = skel | (dark > 0.22)
        edt = distance_transform_edt(~emask).astype(np.float32) if np.any(emask) else np.full_like(alpha, 50.0)
        return CalibratedSceneView(
            view_name=vname, split=m["split"], width=m["width"], height=m["height"],
            fx=m["fx"], fy=m["fy"], cx=m["cx"], cy=m["cy"], w2c=w2c, c2w=c2w,
            cam_center=c2w[:3, 3].copy(), rgb=rgb, alpha=alpha, front_depth=fd,
            darkness=dark, skeleton=skel, edge_dt=edt,
        )

    train_views: list[CalibratedSceneView] = []
    eval_views: list[CalibratedSceneView] = []
    loaded: set[str] = set()
    inp_dir = c2l / "scenes/ficus/inputs"
    det_dir = c2l / "scenes/ficus/detector"
    for f_npz in sorted(inp_dir.glob("*.npz")):
        vn = f_npz.stem
        with np.load(f_npz, allow_pickle=False) as zi, np.load(det_dir / f"{vn}.npz", allow_pickle=False) as zd:
            vw = _mk_view(
                vn, np.array(zi["rgb"], dtype=np.float32), np.array(zi["alpha"], dtype=np.float32),
                np.array(zi["median_camera_z"], dtype=np.float32),
                np.clip(np.array(zd["darkness"], dtype=np.float32), 0.0, 1.0),
                np.array(zd["skeleton"], dtype=bool),
            )
        if vw.split == "train":
            train_views.append(vw)
            loaded.add(vn)
        else:
            eval_views.append(vw)

    for cf in sorted(cache_p.glob("train_*_c2l_3dgs.npz")):
        vn = cf.name.replace("_c2l_3dgs.npz", "")
        if vn in loaded or vn not in cam_lookup:
            continue
        with np.load(cf, allow_pickle=False) as zc:
            al = np.array(zc["alpha"], dtype=np.float32)
            fp = cam_lookup[vn].get("file_path")
            if fp and Path(fp).is_file():
                gt_a = np.asarray(Image.open(resolve_read_path(fp)).convert("RGBA"), dtype=np.uint8)[..., 3].astype(np.float32) / 255.0
                al = np.minimum(al, gt_a)
            train_views.append(_mk_view(
                vn, np.array(zc["rgb"], dtype=np.float32), al,
                np.array(zc["depth"], dtype=np.float32),
                np.clip(np.array(zc["darkness"], dtype=np.float32), 0.0, 1.0),
                np.array(zc["skeleton"], dtype=bool),
            ))

    return {
        "cloud": cloud,
        "leaf_meta_list": leaf_meta_list,
        "pot_spec": pot_spec,
        "swept_trunks": swept_trunks,
        "rim_points": np.concatenate(rim_pts_list, axis=0) if rim_pts_list else np.zeros((0, 3)),
        "rim_tangents": np.concatenate(rim_tng_list, axis=0) if rim_tng_list else np.zeros((0, 3)),
        "median_pixel_scale": p_med,
        "train_views": train_views,
        "eval_views": eval_views,
    }
