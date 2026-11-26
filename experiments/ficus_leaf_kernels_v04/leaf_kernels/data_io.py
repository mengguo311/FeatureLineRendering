"""Read-only multi-modal Ficus 3DGS + 32-view loader with strict write-boundary isolation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image
from plyfile import PlyData
from scipy.ndimage import distance_transform_edt, minimum_filter
from scipy.spatial.transform import Rotation
from scipy.special import expit
import cv2

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

READ_ALLOWED_ROOTS: tuple[Path, ...] = (
    _PACKAGE_ROOT,
    Path("/mnt/hdd1/u00134/radegs_paper_reproduction_v01").resolve(),
    Path("/home/u00134/cglib/data/full").resolve(),
    Path("/home/u00134/3dgs_line").resolve(),
    Path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01").resolve(),
    Path("/home/u00134/.gemini/antigravity/scratch/ficus_leaf_kernels_v01").resolve(),
    Path("/home/u00134/.gemini/antigravity/brain/a6b84014-7b95-40ac-98ee-e4217c453e3d").resolve(),
    Path("/home/u00134/.gemini/antigravity/brain/48eb7555-77d2-4416-a9b8-173755682d02").resolve(),
)

# STRICT WRITE ISOLATION: never allow writes to vec_spline3d_v01 or parent brain directory!
WRITE_ALLOWED_ROOTS: tuple[Path, ...] = (
    _PACKAGE_ROOT,
    Path("/home/u00134/.gemini/antigravity/scratch/ficus_leaf_kernels_v01").resolve(),
    Path("/home/u00134/.gemini/antigravity/brain/a6b84014-7b95-40ac-98ee-e4217c453e3d").resolve(),
    Path("/home/u00134/.gemini/antigravity/brain/48eb7555-77d2-4416-a9b8-173755682d02").resolve(),
)


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
    raise PermissionError(f"Write path '{resolved}' blocked to prevent workspace conflict!")


@dataclass
class GaussianCloud3D:
    """Full 284,835-kernel Ficus 3DGS model preserving exact PLY vertex order."""

    means: np.ndarray          # (N, 3) float32
    scales: np.ndarray         # (N, 3) float32 linear exp(scale)
    quats_wxyz: np.ndarray     # (N, 4) float32 normalized
    cov6: np.ndarray           # (N, 6) float32 upper-triangular 3D covariance for GaussianRasterizer
    surfel_normals: np.ndarray # (N, 3) float32 shortest-scale unit normal
    opacities: np.ndarray      # (N,) float32 in (0, 1)
    rgb_dc: np.ndarray         # (N, 3) float32 base albedo in [0, 1]
    shs: np.ndarray            # (N, 16, 3) float32 full degree-3 SH coefficients


@dataclass
class CalibratedLeafView:
    """Single calibrated training or held-out test view with RGB, alpha, foreground depth, and C2L50 edges."""

    view_name: str
    split: str  # "train" or "test"
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    w2c: np.ndarray         # (4, 4) float64
    c2w: np.ndarray         # (4, 4) float64
    cam_center: np.ndarray  # (3,) float64
    rgb: np.ndarray         # (H, W, 3) float32
    alpha: np.ndarray       # (H, W) float32
    depth: np.ndarray       # (H, W) float32
    front_depth: np.ndarray # (H, W) float32 3x3 foreground-locked depth
    depth_jump: np.ndarray  # (H, W) float32 relative depth step
    darkness: np.ndarray    # (H, W) float32 C2L50 edge darkness in [0, 1]
    skeleton: np.ndarray    # (H, W) bool 1-px C2L50 skeleton
    is_original_c2l: bool


@dataclass
class PriorVectorGeometry:
    """Read-only 3D leaf-rim points/tangents & wooden trunk spines from ficus_full_v04."""

    rim_points: np.ndarray      # (M, 3) float64 dense samples along 3D leaf-rim curves
    rim_tangents: np.ndarray    # (M, 3) float64 unit tangents
    trunk_points: np.ndarray    # (T, 3) float64 dense samples along wooden trunk spines
    trunk_radii: np.ndarray     # (T,) float64 local trunk radii
    pot_axis_origin: np.ndarray # (3,) float64
    pot_axis_dir: np.ndarray    # (3,) float64
    pot_h_max: float
    ink_gaussians: dict[str, np.ndarray] | None
    median_pixel_scale: float


def _compute_front_depth_and_jump(depth: np.ndarray, alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    valid_fg = (alpha > 0.55) & np.isfinite(depth) & (depth > 0.15)
    sentinel = np.where(valid_fg, depth, 1e6).astype(np.float32)
    min_3 = minimum_filter(sentinel, size=3)
    min_5 = minimum_filter(sentinel, size=5)
    front_d = np.where(min_3 < 9e5, min_3, np.where(min_5 < 9e5, min_5, depth)).astype(np.float32)

    z = np.where((alpha > 0.3) & np.isfinite(depth) & (depth > 0.1), depth, 0.0).astype(np.float32)
    dz_dx = cv2.Sobel(z, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    dz_dy = cv2.Sobel(z, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    rel_jump = np.where(alpha > 0.3, np.hypot(dz_dx, dz_dy) / np.maximum(z, 0.25), 0.0).astype(np.float32)
    return front_d, rel_jump


def load_ficus_3dgs_cloud(
    ply_path: str | Path = "/home/u00134/3dgs_line/tier1/out/multiscene_foundation/training/ficus/seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply",
) -> GaussianCloud3D:
    """Load all 284,835 Ficus 3DGS kernels in exact PLY order (read-only)."""
    safe_ply = resolve_read_path(ply_path)
    vdata = PlyData.read(safe_ply)["vertex"].data
    get_cols = lambda names: np.stack([vdata[n] for n in names], axis=-1).astype(np.float32)

    means = get_cols(["x", "y", "z"])
    scales = np.exp(get_cols(["scale_0", "scale_1", "scale_2"]))
    quat = get_cols(["rot_0", "rot_1", "rot_2", "rot_3"])
    quat /= np.maximum(np.linalg.norm(quat, axis=1, keepdims=True), 1e-12)

    R_mat = Rotation.from_quat(quat[:, [1, 2, 3, 0]]).as_matrix().astype(np.float32)
    cov3 = (R_mat * (scales[:, None, :] ** 2)) @ R_mat.transpose(0, 2, 1)
    cov6 = np.ascontiguousarray(cov3[:, [0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]])

    min_ax = np.argmin(scales, axis=1)
    surfel_normals = np.ascontiguousarray(R_mat[np.arange(len(means)), :, min_ax])

    opacities = expit(vdata["opacity"].astype(np.float32))
    dc = get_cols(["f_dc_0", "f_dc_1", "f_dc_2"])
    rgb_dc = np.clip(dc * 0.28209479177387814 + 0.5, 0.0, 1.0).astype(np.float32)
    rest = get_cols([f"f_rest_{i}" for i in range(45)]).reshape(-1, 3, 15)
    shs = np.ascontiguousarray(np.concatenate([dc[:, :, None], rest], axis=-1).transpose(0, 2, 1))

    return GaussianCloud3D(
        means=means,
        scales=scales,
        quats_wxyz=quat,
        cov6=cov6,
        surfel_normals=surfel_normals,
        opacities=opacities,
        rgb_dc=rgb_dc,
        shs=shs,
    )


def load_ficus_views_and_v04_priors(
    c2l_root: str | Path = "/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_multiview05_v01",
    cglib_ficus_root: str | Path = "/home/u00134/cglib/data/full/ficus",
    cameras_json_path: str | Path = "/home/u00134/3dgs_line/ficus_fragment_faces_v07/v07/cameras.json",
    extra_cache_dir: str | Path = "/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/cache_ficus_c2l_views",
    v04_dir: str | Path = "/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/ficus_full_v04",
) -> tuple[list[CalibratedLeafView], list[CalibratedLeafView], PriorVectorGeometry]:
    """Load 32 full-sphere train views, 5 held-out test views, and read-only v04 3D curve/trunk priors."""
    c2l = resolve_read_path(c2l_root)
    cglib = resolve_read_path(cglib_ficus_root)
    cam_file = resolve_read_path(cameras_json_path)
    cache_p = resolve_read_path(extra_cache_dir)
    v04_p = resolve_read_path(v04_dir)

    seed_cams_path = resolve_read_path(
        "/home/u00134/3dgs_line/tier1/out/multiscene_foundation/training/ficus/seed_1729/checkpoints/cameras.json"
    )
    cam_lookup: dict[str, dict[str, Any]] = {}
    if seed_cams_path.is_file():
        for c in json.loads(seed_cams_path.read_text(encoding="utf-8")):
            split_tag = "test" if int(c["id"]) < 16 else "train"
            vname = f"{split_tag}_{c['img_name']}"
            c2w_s = np.eye(4, dtype=np.float64)
            c2w_s[:3, :3] = np.asarray(c["rotation"], dtype=np.float64)
            c2w_s[:3, 3] = np.asarray(c["position"], dtype=np.float64)
            w2c_s = np.linalg.inv(c2w_s)
            cam_lookup[vname] = {
                "view": vname,
                "split": split_tag,
                "width": int(c["width"]),
                "height": int(c["height"]),
                "fx": float(c["fx"]),
                "fy": float(c["fy"]),
                "cx": 0.5 * float(c["width"]) - 0.5,
                "cy": 0.5 * float(c["height"]) - 0.5,
                "extrinsic": w2c_s.tolist(),
            }

    for c in json.loads(cam_file.read_text(encoding="utf-8"))["cameras"]:
        cam_lookup[c["view"]] = c

    gl_flip = np.diag([1.0, -1.0, -1.0, 1.0])
    for split_name, tf_file in (("train", "transforms_train.json"), ("test", "transforms_val.json")):
        tf_doc = json.loads(resolve_read_path(cglib / tf_file).read_text(encoding="utf-8"))
        fov_x = float(tf_doc["camera_angle_x"])
        w = h = 800
        fx = fy = 0.5 * w / math.tan(0.5 * fov_x)
        for frame in tf_doc["frames"]:
            stem = Path(frame["file_path"]).name
            vname = f"{split_name}_{stem}"
            c2w = np.asarray(frame["transform_matrix"], dtype=np.float64) @ gl_flip
            w2c = np.linalg.inv(c2w)
            cam_lookup.setdefault(
                vname,
                {
                    "view": vname,
                    "split": split_name,
                    "width": w,
                    "height": h,
                    "fx": fx,
                    "fy": fy,
                    "cx": 399.5,
                    "cy": 399.5,
                    "extrinsic": w2c.tolist(),
                    "file_path": str(cglib / f"{frame['file_path']}.png"),
                },
            )
            if "file_path" not in cam_lookup[vname]:
                cam_lookup[vname]["file_path"] = str(cglib / f"{frame['file_path']}.png")

    train_views: list[CalibratedLeafView] = []
    eval_views: list[CalibratedLeafView] = []
    loaded_names: set[str] = set()

    inp_dir = c2l / "scenes/ficus/inputs"
    det_dir = c2l / "scenes/ficus/detector"
    for npz_file in sorted(inp_dir.glob("*.npz")):
        vname = npz_file.stem
        meta = cam_lookup[vname]
        w2c = np.asarray(meta["extrinsic"], dtype=np.float64)
        c2w = np.linalg.inv(w2c)
        with np.load(npz_file, allow_pickle=False) as z_in, np.load(det_dir / f"{vname}.npz", allow_pickle=False) as z_det:
            rgb = np.array(z_in["rgb"], dtype=np.float32)
            alpha = np.array(z_in["alpha"], dtype=np.float32)
            depth = np.array(z_in["median_camera_z"], dtype=np.float32)
            darkness = np.clip(np.array(z_det["darkness"], dtype=np.float32), 0.0, 1.0)
            skeleton = np.array(z_det["skeleton"], dtype=bool)
        front_d, d_jump = _compute_front_depth_and_jump(depth, alpha)
        is_tr = vname.startswith("train_")
        vw = CalibratedLeafView(
            view_name=vname,
            split="train" if is_tr else "test",
            width=int(meta["width"]),
            height=int(meta["height"]),
            fx=float(meta["fx"]),
            fy=float(meta["fy"]),
            cx=float(meta["cx"]),
            cy=float(meta["cy"]),
            w2c=w2c,
            c2w=c2w,
            cam_center=c2w[:3, 3].copy(),
            rgb=rgb,
            alpha=alpha,
            depth=depth,
            front_depth=front_d,
            depth_jump=d_jump,
            darkness=darkness,
            skeleton=skeleton,
            is_original_c2l=is_tr,
        )
        if is_tr:
            train_views.append(vw)
            loaded_names.add(vname)
        else:
            eval_views.append(vw)

    if cache_p.is_dir():
        for cfile in sorted(cache_p.glob("train_*_c2l_3dgs.npz")):
            vname = cfile.name.replace("_c2l_3dgs.npz", "")
            if vname in loaded_names or vname not in cam_lookup:
                continue
            meta = cam_lookup[vname]
            w2c = np.asarray(meta["extrinsic"], dtype=np.float64)
            c2w = np.linalg.inv(w2c)
            with np.load(cfile, allow_pickle=False) as zc:
                rgb = np.array(zc["rgb"], dtype=np.float32)
                alpha = np.array(zc["alpha"], dtype=np.float32)
                depth = np.array(zc["depth"], dtype=np.float32)
                darkness = np.clip(np.array(zc["darkness"], dtype=np.float32), 0.0, 1.0)
                skeleton = np.array(zc["skeleton"], dtype=bool)
            if "file_path" in meta and Path(meta["file_path"]).is_file():
                gt_rgba = np.asarray(Image.open(resolve_read_path(meta["file_path"])).convert("RGBA"), dtype=np.uint8)
                alpha = np.minimum(alpha, gt_rgba[..., 3].astype(np.float32) / 255.0)
            front_d, d_jump = _compute_front_depth_and_jump(depth, alpha)
            train_views.append(
                CalibratedLeafView(
                    view_name=vname,
                    split="train",
                    width=int(meta["width"]),
                    height=int(meta["height"]),
                    fx=float(meta["fx"]),
                    fy=float(meta["fy"]),
                    cx=float(meta["cx"]),
                    cy=float(meta["cy"]),
                    w2c=w2c,
                    c2w=c2w,
                    cam_center=c2w[:3, 3].copy(),
                    rgb=rgb,
                    alpha=alpha,
                    depth=depth,
                    front_depth=front_d,
                    depth_jump=d_jump,
                    darkness=darkness,
                    skeleton=skeleton,
                    is_original_c2l=False,
                )
            )

    # Read-only load of v04 3D boundary curves, coaxial pot specs, and swept wooden trunk tubes
    rim_pts_list: list[np.ndarray] = []
    rim_tng_list: list[np.ndarray] = []
    trunk_pts_list: list[np.ndarray] = []
    trunk_rad_list: list[np.ndarray] = []
    pot_o = np.array([-0.02236, 0.01663, -0.0001], dtype=np.float64)
    pot_a = np.array([-0.00227, 0.00283, 0.99999], dtype=np.float64)
    pot_h_max = -0.504
    ink_gs = None

    if (v04_p / "curve_network.json").is_file() and (v04_p / "curve_controls.npz").is_file():
        net_doc = json.loads((v04_p / "curve_network.json").read_text(encoding="utf-8"))
        with np.load(v04_p / "curve_controls.npz", allow_pickle=False) as ctrl_z:
            all_ctrl = np.array(ctrl_z["control_points"], dtype=np.float64)

        if net_doc.get("coaxial_families"):
            cf = net_doc["coaxial_families"][0]
            pot_o = np.asarray(cf["axis_origin"], dtype=np.float64)
            pot_a = np.asarray(cf["axis_dir"], dtype=np.float64)
            pot_h_max = float(cf["h_range"][1]) + 0.008

        for cg in net_doc.get("contour_generators", []):
            if cg.get("generator_type") == "SWEPT_TUBE_ENVELOPE_3D":
                sp_ctrl = np.asarray(cg["spine_control_points"], dtype=np.float64)
                r_ctrl = np.asarray(cg["control_radii"], dtype=np.float64)
                # Sample dense piecewise linear interpolation along control polygon
                u_dense = np.linspace(0.0, len(sp_ctrl) - 1, 64)
                i0 = np.clip(np.floor(u_dense).astype(int), 0, len(sp_ctrl) - 2)
                w = u_dense - i0
                p_d = (1.0 - w)[:, None] * sp_ctrl[i0] + w[:, None] * sp_ctrl[i0 + 1]
                r_d = (1.0 - w) * r_ctrl[i0] + w * r_ctrl[i0 + 1]
                trunk_pts_list.append(p_d)
                trunk_rad_list.append(r_d)

        # Sample dense 3D points along canopy leaf-rim curves (z >= pot_h_max)
        for c_entry in net_doc.get("curves", []):
            if c_entry.get("role") == "COAXIAL_RING":
                continue
            s0, s1 = c_entry["ctrl_slice"]
            c_pts = all_ctrl[s0:s1]
            if len(c_pts) < 2 or float(c_pts[:, 2].max()) < pot_h_max:
                continue
            # Subdivide control polygon / 3-pt arc into dense samples for 3D barrier & 2D projection
            if c_entry["primitive_type"] == "ARC_3D" and len(c_pts) == 3 and "arc_geometry" in c_entry:
                ag = c_entry["arc_geometry"]
                ctr = np.asarray(ag["center"], dtype=np.float64)
                nrm = np.asarray(ag["normal"], dtype=np.float64)
                rad = float(ag["radius"])
                sw = math.radians(float(ag["sweep_deg"]))
                e1 = (c_pts[0] - ctr) / max(rad, 1e-8)
                e2 = np.cross(nrm, e1)
                th = np.linspace(0.0, sw, max(8, int(round(rad * sw / 0.0025))))
                pts_s = ctr[None, :] + rad * (np.cos(th)[:, None] * e1[None, :] + np.sin(th)[:, None] * e2[None, :])
            else:
                u_s = np.linspace(0.0, len(c_pts) - 1, max(6, len(c_pts) * 6))
                k0 = np.clip(np.floor(u_s).astype(int), 0, len(c_pts) - 2)
                wk = u_s - k0
                pts_s = (1.0 - wk)[:, None] * c_pts[k0] + wk[:, None] * c_pts[k0 + 1]
            tng_s = np.gradient(pts_s, axis=0)
            tng_s /= np.maximum(np.linalg.norm(tng_s, axis=1, keepdims=True), 1e-9)
            rim_pts_list.append(pts_s)
            rim_tng_list.append(tng_s)

        if (v04_p / "resampled_ink_gaussians.npz").is_file():
            with np.load(v04_p / "resampled_ink_gaussians.npz", allow_pickle=False) as z_ink:
                ink_gs = {k: np.array(z_ink[k], copy=True) for k in ("means", "covariance", "opacity", "colors")}

    with np.load(c2l / "arms/C/scenes/ficus/full/SHARED_CONTROL_AND_SAMPLING.npz", allow_pickle=False) as scs:
        med_p = float(np.median(scs["node_pixel"]))

    priors = PriorVectorGeometry(
        rim_points=np.concatenate(rim_pts_list, axis=0) if rim_pts_list else np.zeros((0, 3)),
        rim_tangents=np.concatenate(rim_tng_list, axis=0) if rim_tng_list else np.zeros((0, 3)),
        trunk_points=np.concatenate(trunk_pts_list, axis=0) if trunk_pts_list else np.zeros((0, 3)),
        trunk_radii=np.concatenate(trunk_rad_list, axis=0) if trunk_rad_list else np.zeros((0,)),
        pot_axis_origin=pot_o,
        pot_axis_dir=pot_a / max(float(np.linalg.norm(pot_a)), 1e-9),
        pot_h_max=pot_h_max,
        ink_gaussians=ink_gs,
        median_pixel_scale=med_p,
    )
    return train_views, eval_views, priors
