"""Multi-modal scene loader: C2L parents/rays/states + GPU 3DGS surface depth/RGB + C2L50 32-view edge DT."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from diff_gaussian_rasterization import GaussianRasterizationSettings, GaussianRasterizer
from PIL import Image
from plyfile import PlyData
from scipy.ndimage import distance_transform_edt, gaussian_filter, minimum_filter
from scipy.special import expit
from scipy.spatial.transform import Rotation
from skimage.morphology import skeletonize

from .schema import resolve_safe_path


@dataclass
class MultiModalView:
    """Calibrated camera view with C2L50 2D edge DT/tangent fields, visual-hull mask, and 3DGS surface depth."""

    view_name: str
    split: str  # "train" or "test"
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    w2c: np.ndarray  # (4, 4) float64
    c2w: np.ndarray  # (4, 4) float64
    cam_center: np.ndarray  # (3,) float64
    alpha: np.ndarray  # (H, W) float32 in [0, 1]
    outside_hull_dt: np.ndarray  # (H, W) float32, 0 inside silhouette (alpha>=0.05), >0 px distance outside
    edge_strength: np.ndarray  # (H, W) float32 in [0, 1]
    edge_mask: np.ndarray  # (H, W) bool
    edge_dt: np.ndarray  # (H, W) float32, Euclidean pixel distance to nearest 2D edge
    edge_tangent_2d: np.ndarray  # (H, W, 2) float32, unit 2D tangent at nearest edge pixel
    skeleton: np.ndarray | None = None  # (H, W) bool 1-px centerline skeleton
    rgb: np.ndarray | None = None  # (H, W, 3) float32
    depth: np.ndarray | None = None  # (H, W) float32 surface camera_z
    front_depth: np.ndarray | None = None  # (H, W) float32 foreground-locked camera_z
    depth_jump: np.ndarray | None = None  # (H, W) float32 relative depth discontinuity
    normal_map: np.ndarray | None = None  # (H, W, 3) float32 camera-space surface normal
    is_original_c2l_build: bool = False


@dataclass
class ParentFragmentChain:
    """Single C2L or complementary multi-view polyline with full ray provenance and per-node depth state."""

    parent_id: int
    source_view: str
    cam_center: np.ndarray  # (3,) float64
    uv: np.ndarray  # (L, 2) float64 [u=col, v=row]
    rays: np.ndarray  # (L, 3) float64 world ray per unit camera_z: x(z) = cam_center + z * ray
    fitted_z: np.ndarray  # (L,) float64
    raw_z: np.ndarray  # (L,) float64
    second_z: np.ndarray  # (L,) float64
    state: np.ndarray  # (L,) uint8: 1=trusted local surface, 2=rim/untrusted center, 0=unknown
    node_pixel: np.ndarray  # (L,) float64 world size of 1 pixel at node depth
    points_3d: np.ndarray  # (L, 3) float64
    is_complementary_seed: bool = False


@dataclass
class MultiModalSceneBundle:
    """Complete multi-modal input bundle for any C2L or 3DGS scene."""

    scene_name: str
    train_views: list[MultiModalView]
    eval_views: list[MultiModalView]
    parents: list[ParentFragmentChain]
    canonical_gaussians_path: Path | None
    median_pixel_scale: float
    surface_ply_path: Path | None = None
    has_silhouette_mask: bool = True
    bg_val: float = 1.0


def _compute_edge_dt_and_tangent(edge_strength: np.ndarray, edge_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute 2D Euclidean distance transform to edge_mask and propagate unit 2D edge tangents."""
    h, w = edge_strength.shape
    if not np.any(edge_mask):
        return (
            np.full((h, w), 50.0, dtype=np.float32),
            np.zeros((h, w, 2), dtype=np.float32),
        )

    smooth = gaussian_filter(edge_strength.astype(np.float32), sigma=1.0)
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    tx = -gy
    ty = gx
    nrm = np.hypot(tx, ty)
    valid = nrm > 1e-6
    tx_u = np.where(valid, tx / np.maximum(nrm, 1e-6), 1.0).astype(np.float32)
    ty_u = np.where(valid, ty / np.maximum(nrm, 1e-6), 0.0).astype(np.float32)

    dt, nearest_idx = distance_transform_edt(~edge_mask, return_indices=True)
    rr, cc = nearest_idx[0], nearest_idx[1]
    tang = np.stack([tx_u[rr, cc], ty_u[rr, cc]], axis=-1)
    return dt.astype(np.float32), tang.astype(np.float32)


def _compute_foreground_depth(depth: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Compute a 3x3 foreground-masked minimum depth so anti-aliased leaf rims lock onto foreground leaf depth."""
    valid_fg = (alpha > 0.55) & np.isfinite(depth) & (depth > 0.15)
    sentinel = np.where(valid_fg, depth, 1e6).astype(np.float32)
    min_3x3 = minimum_filter(sentinel, size=3)
    min_5x5 = minimum_filter(sentinel, size=5)
    out = np.where(min_3x3 < 9e5, min_3x3, np.where(min_5x5 < 9e5, min_5x5, depth))
    return out.astype(np.float32)


def _compute_depth_normals_and_jumps(
    depth: np.ndarray, alpha: np.ndarray, fx: float, fy: float, cx: float, cy: float
) -> tuple[np.ndarray, np.ndarray]:
    """Derive camera-space surface normals and relative depth-jump map from 3DGS surface depth."""
    h, w = depth.shape
    z = np.where((alpha > 0.3) & np.isfinite(depth) & (depth > 0.1), depth, 0.0).astype(np.float32)
    dz_dx = cv2.Sobel(z, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    dz_dy = cv2.Sobel(z, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    rel_jump = np.hypot(dz_dx, dz_dy) / np.maximum(z, 0.25)
    rel_jump = np.where(alpha > 0.3, rel_jump, 0.0).astype(np.float32)

    uu, vv = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    X = (uu - float(cx)) * z / float(fx)
    Y = (vv - float(cy)) * z / float(fy)
    pts = np.stack([X, Y, z], axis=-1)
    dx = np.zeros_like(pts)
    dy = np.zeros_like(pts)
    dx[:, 1:-1] = 0.5 * (pts[:, 2:] - pts[:, :-2])
    dy[1:-1, :] = 0.5 * (pts[2:, :] - pts[:-2, :])
    normals = np.cross(dx, dy)
    n_len = np.linalg.norm(normals, axis=-1, keepdims=True)
    normals = np.where((n_len > 1e-8) & (alpha[..., None] > 0.3), normals / np.maximum(n_len, 1e-8), 0.0)
    flip = normals[..., 2] > 0
    normals[flip] *= -1.0
    return normals.astype(np.float32), rel_jump


class Surface3DGSRendererAndDetector:
    """Fast GPU renderer for source Ficus 3DGS PLY + exact C2L50 multi-scale edge & skeleton detector."""

    def __init__(
        self,
        ply_path: Path,
        c2l_code_dir: Path,
        device: torch.device,
    ) -> None:
        self.device = device
        ply_safe = resolve_safe_path(ply_path)
        code_safe = resolve_safe_path(c2l_code_dir)
        if str(code_safe) not in sys.path:
            sys.path.insert(0, str(code_safe))
        import boundary  # type: ignore
        self._boundary = boundary

        vdata = PlyData.read(ply_safe)["vertex"].data
        get_v = lambda names: np.stack([vdata[n] for n in names], -1).astype(np.float32)
        means = get_v(["x", "y", "z"])
        sc = np.exp(get_v([f"scale_{i}" for i in range(3)]))
        quat = get_v([f"rot_{i}" for i in range(4)])
        quat /= np.maximum(np.linalg.norm(quat, axis=1, keepdims=True), 1e-12)
        raw_op = vdata["opacity"].astype(np.float32)
        op_sig = np.where(
            np.isposinf(raw_op),
            1.0,
            np.where(np.isneginf(raw_op), 0.0, expit(np.clip(raw_op, -40.0, 40.0))),
        ).astype(np.float32)
        if "filter_3D" in (vdata.dtype.names or ()):
            f3d = vdata["filter_3D"].astype(np.float32)[:, None]
            sf_sq = sc * sc + f3d * f3d
            scales_act = np.sqrt(np.maximum(sf_sq, 1e-18)).astype(np.float32)
            op = (op_sig * np.sqrt(np.prod((sc * sc) / np.maximum(sf_sq, 1e-12), axis=1)))[:, None].astype(np.float32)
        else:
            scales_act = sc.astype(np.float32)
            op = op_sig[:, None].astype(np.float32)
        dc = get_v([f"f_dc_{i}" for i in range(3)])
        rest = get_v([f"f_rest_{i}" for i in range(45)]).reshape(-1, 3, 15)
        shs = np.ascontiguousarray(np.concatenate([dc[:, :, None], rest], -1).transpose(0, 2, 1))

        if device.type == "cuda":
            torch.cuda.set_device(device)
        self.means_t = torch.tensor(means, device=device).contiguous()
        self.scales_t = torch.tensor(scales_act, device=device).contiguous()
        self.rots_t = torch.tensor(quat, device=device).contiguous()
        self.op_t = torch.tensor(op, device=device).contiguous()
        self.shs_t = torch.tensor(shs, device=device).contiguous()
        self.m2d_t = torch.zeros_like(self.means_t)

    @torch.no_grad()
    def render_and_detect(
        self, w2c: np.ndarray, fx: float, fy: float, cx: float, cy: float, w: int, h: int, bg_val: float = 1.0
    ) -> dict[str, np.ndarray]:
        if self.device.type == "cuda":
            torch.cuda.set_device(self.device)
        E = w2c.astype(np.float32)
        P = np.zeros((4, 4), dtype=np.float32)
        near, far = 0.01, 100.0
        P[0, 0] = 2.0 * fx / w
        P[1, 1] = 2.0 * fy / h
        P[0, 2] = (2.0 * cx + 1.0 - w) / w
        P[1, 2] = (2.0 * cy + 1.0 - h) / h
        P[2, 2] = far / (far - near)
        P[2, 3] = -far * near / (far - near)
        P[3, 2] = 1.0
        campos = -E[:3, :3].T @ E[:3, 3]

        viewmat = torch.tensor(E.T, device=self.device).contiguous()
        projmat = torch.tensor((P @ E).T, device=self.device).contiguous()
        campos_t = torch.tensor(campos, device=self.device).contiguous()

        s_rgb = GaussianRasterizationSettings(
            image_height=h, image_width=w, tanfovx=float(w / (2.0 * fx)), tanfovy=float(h / (2.0 * fy)),
            bg=torch.full((3,), float(bg_val), dtype=torch.float32, device=self.device), scale_modifier=1.0,
            viewmatrix=viewmat, projmatrix=projmat, sh_degree=3, campos=campos_t, prefiltered=False, debug=False,
        )

        rast_out = GaussianRasterizer(s_rgb)(
            means3D=self.means_t,
            means2D=self.m2d_t,
            shs=self.shs_t,
            opacities=self.op_t,
            scales=self.scales_t,
            rotations=self.rots_t,
        )
        rgb = rast_out[0].permute(1, 2, 0).clamp(0.0, 1.0).cpu().numpy().astype(np.float32)
        # Native RaDe-GS CUDA rasterizer returns (color, radii, depth, middepth, alpha, normal, distortion)
        mid_z_raw = rast_out[3][0].cpu().numpy().astype(np.float32)
        alpha = np.clip(rast_out[4][0].cpu().numpy(), 0.0, 1.0).astype(np.float32)
        front_z = np.where((alpha > 1e-4) & (mid_z_raw > 0.0), mid_z_raw, 0.0).astype(np.float32)

        # Exact C2L50 multi-scale detector
        f_det = self._boundary.analyze(rgb, dict(scales=[1.4, 2.8, 5.6]))
        soft = np.maximum(f_det["structural"], 0.5 * f_det["detail"])
        darkness = np.clip(1.0 - self._boundary.ink(soft, gain=1, sigma=0.5)[..., 0], 0.0, 1.0).astype(np.float32)
        marked = darkness > 0.2
        skel = skeletonize(marked)
        return {
            "rgb": rgb,
            "alpha": alpha,
            "depth": front_z,
            "darkness": darkness,
            "marked": marked,
            "skeleton": skel,
        }


def load_ficus_multimodal_bundle(
    num_extra_train_views: int = 24,
    cache_dir: str | Path | None = "/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/cache_ficus_c2l_views",
    c2l_root: str | Path = "/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_multiview05_v01",
    cglib_ficus_root: str | Path = "/home/u00134/cglib/data/full/ficus",
    cameras_json_path: str | Path = "/home/u00134/3dgs_line/ficus_fragment_faces_v07/v07/cameras.json",
    surface_ply_path: str | Path = "/home/u00134/3dgs_line/tier1/out/multiscene_foundation/training/ficus/seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply",
    c2l_code_dir: str | Path = "/home/u00134/3dgs_line/gaer_rade_depth_lift_v01/reproduction/radegs_c2l50_multiview05_v01",
) -> MultiModalSceneBundle:
    """Load Ficus multi-modal bundle with 8 original + up to 24 GPU-rendered 3DGS+C2L50 views + 5 held-out eval views."""
    c2l = resolve_safe_path(c2l_root)
    cglib = resolve_safe_path(cglib_ficus_root)
    cam_file = resolve_safe_path(cameras_json_path)
    cache_path = resolve_safe_path(cache_dir) if cache_dir is not None else None
    if cache_path is not None:
        cache_path.mkdir(parents=True, exist_ok=True)

    full_dir = c2l / "arms/C/scenes/ficus/full"
    inp_dir = c2l / "scenes/ficus/inputs"
    det_dir = c2l / "scenes/ficus/detector"

    cam_lookup: dict[str, dict[str, Any]] = {}
    raw_cams = json.loads(cam_file.read_text(encoding="utf-8"))["cameras"]
    for c in raw_cams:
        cam_lookup[c["view"]] = c

    gl_flip = np.diag([1.0, -1.0, -1.0, 1.0])
    for split_name in ("train", "test"):
        tf_path = resolve_safe_path(cglib / f"transforms_{split_name}.json")
        tf_doc = json.load(tf_path.open("r", encoding="utf-8"))
        fov_x = float(tf_doc["camera_angle_x"])
        w = h = 800
        fx = fy = 0.5 * w / math.tan(0.5 * fov_x)
        for frame in tf_doc["frames"]:
            stem = Path(frame["file_path"]).name
            vname = f"{split_name}_{stem}"
            c2w_gl = np.asarray(frame["transform_matrix"], dtype=np.float64)
            c2w = c2w_gl @ gl_flip
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

    train_views: list[MultiModalView] = []
    eval_views: list[MultiModalView] = []
    loaded_train_names: set[str] = set()

    # 1. Load all 13 rich C2L views (8 train BUILD + 5 test EVAL)
    for npz_file in sorted(inp_dir.glob("*.npz")):
        vname = npz_file.stem
        det_file = det_dir / f"{vname}.npz"
        meta = cam_lookup[vname]
        w2c = np.asarray(meta["extrinsic"], dtype=np.float64)
        c2w = np.linalg.inv(w2c)
        with np.load(npz_file, allow_pickle=False) as z_in, np.load(det_file, allow_pickle=False) as z_det:
            rgb = np.array(z_in["rgb"], dtype=np.float32)
            alpha = np.array(z_in["alpha"], dtype=np.float32)
            depth = np.array(z_in["median_camera_z"], dtype=np.float32)
            darkness = np.array(z_det["darkness"], dtype=np.float32)
            marked = np.array(z_det["marked"], dtype=bool)
            skeleton = np.array(z_det["skeleton"], dtype=bool)

        edge_mask = skeleton | (marked & (darkness > 0.22))
        edge_dt, edge_tang = _compute_edge_dt_and_tangent(darkness, edge_mask)
        outside_dt = distance_transform_edt(alpha < 0.05).astype(np.float32)
        front_d = _compute_foreground_depth(depth, alpha)
        normals, depth_jump = _compute_depth_normals_and_jumps(
            depth, alpha, float(meta["fx"]), float(meta["fy"]), float(meta["cx"]), float(meta["cy"])
        )

        is_train = vname.startswith("train_")
        mv = MultiModalView(
            view_name=vname,
            split="train" if is_train else "test",
            width=int(meta["width"]),
            height=int(meta["height"]),
            fx=float(meta["fx"]),
            fy=float(meta["fy"]),
            cx=float(meta["cx"]),
            cy=float(meta["cy"]),
            w2c=w2c,
            c2w=c2w,
            cam_center=c2w[:3, 3].copy(),
            alpha=alpha,
            outside_hull_dt=outside_dt,
            edge_strength=np.clip(darkness, 0.0, 1.0),
            edge_mask=edge_mask,
            edge_dt=edge_dt,
            edge_tangent_2d=edge_tang,
            skeleton=skeleton,
            rgb=rgb,
            depth=depth,
            front_depth=front_d,
            depth_jump=depth_jump,
            normal_map=normals,
            is_original_c2l_build=is_train,
        )
        if is_train:
            train_views.append(mv)
            loaded_train_names.add(vname)
        else:
            eval_views.append(mv)

    # 2. Farthest-point sample extra full-sphere training views & render exact 3DGS depth + C2L50 edges
    if num_extra_train_views > 0:
        cand_names = sorted(
            k for k, v in cam_lookup.items()
            if v.get("split") == "train" and k not in loaded_train_names
        )
        selected_centers = [v.cam_center for v in train_views]
        chosen_extra: list[str] = []
        remaining = list(cand_names)
        while remaining and len(chosen_extra) < num_extra_train_views:
            best_name = None
            best_min_d = -1.0
            for cname in remaining:
                c_w2c = np.asarray(cam_lookup[cname]["extrinsic"], dtype=np.float64)
                c_pos = np.linalg.inv(c_w2c)[:3, 3]
                min_d = min(float(np.linalg.norm(c_pos - sc)) for sc in selected_centers)
                if min_d > best_min_d:
                    best_min_d = min_d
                    best_name = cname
            assert best_name is not None
            chosen_extra.append(best_name)
            remaining.remove(best_name)
            selected_centers.append(np.linalg.inv(np.asarray(cam_lookup[best_name]["extrinsic"], dtype=np.float64))[:3, 3])

        renderer_det: Surface3DGSRendererAndDetector | None = None
        dev = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        for vname in chosen_extra:
            meta = cam_lookup[vname]
            w2c = np.asarray(meta["extrinsic"], dtype=np.float64)
            c2w = np.linalg.inv(w2c)
            cfile = cache_path / f"{vname}_c2l_3dgs.npz" if cache_path is not None else None

            if cfile is not None and cfile.is_file():
                with np.load(cfile, allow_pickle=False) as zc_cache:
                    rgb = np.array(zc_cache["rgb"], dtype=np.float32)
                    alpha = np.array(zc_cache["alpha"], dtype=np.float32)
                    depth = np.array(zc_cache["depth"], dtype=np.float32)
                    darkness = np.array(zc_cache["darkness"], dtype=np.float32)
                    marked = np.array(zc_cache["marked"], dtype=bool)
                    skeleton = np.array(zc_cache["skeleton"], dtype=bool)
            else:
                if renderer_det is None:
                    renderer_det = Surface3DGSRendererAndDetector(
                        Path(surface_ply_path), Path(c2l_code_dir), device=dev
                    )
                rendered = renderer_det.render_and_detect(
                    w2c,
                    float(meta["fx"]),
                    float(meta["fy"]),
                    float(meta["cx"]),
                    float(meta["cy"]),
                    int(meta["width"]),
                    int(meta["height"]),
                )
                rgb = rendered["rgb"]
                alpha = rendered["alpha"]
                depth = rendered["depth"]
                darkness = rendered["darkness"]
                marked = rendered["marked"]
                skeleton = rendered["skeleton"]
                if cfile is not None:
                    np.savez_compressed(
                        cfile,
                        rgb=rgb,
                        alpha=alpha,
                        depth=depth,
                        darkness=darkness,
                        marked=marked,
                        skeleton=skeleton,
                    )

            # Use ground-truth PNG alpha if available for ultra-crisp silhouette hull, intersected with 3DGS alpha
            if "file_path" in meta and Path(meta["file_path"]).is_file():
                gt_rgba = np.asarray(Image.open(resolve_safe_path(meta["file_path"])).convert("RGBA"), dtype=np.uint8)
                gt_alpha = gt_rgba[..., 3].astype(np.float32) / 255.0
                hull_alpha = np.minimum(alpha, np.maximum(gt_alpha, 0.0))
            else:
                hull_alpha = alpha

            edge_mask = skeleton | (marked & (darkness > 0.22))
            edge_dt, edge_tang = _compute_edge_dt_and_tangent(darkness, edge_mask)
            outside_dt = distance_transform_edt(hull_alpha < 0.05).astype(np.float32)
            front_d = _compute_foreground_depth(depth, alpha)
            normals, depth_jump = _compute_depth_normals_and_jumps(
                depth, alpha, float(meta["fx"]), float(meta["fy"]), float(meta["cx"]), float(meta["cy"])
            )

            train_views.append(
                MultiModalView(
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
                    alpha=hull_alpha,
                    outside_hull_dt=outside_dt,
                    edge_strength=darkness,
                    edge_mask=edge_mask,
                    edge_dt=edge_dt,
                    edge_tangent_2d=edge_tang,
                    skeleton=skeleton,
                    rgb=rgb,
                    depth=depth,
                    front_depth=front_d,
                    depth_jump=depth_jump,
                    normal_map=normals,
                    is_original_c2l_build=False,
                )
            )

    # 3. Load C2L parents, rays, and per-view depth_graph state ledgers
    node_depth_cache: dict[str, dict[str, np.ndarray]] = {}
    for nd_path in sorted((full_dir / "depth_graph").glob("*_NODE_DEPTH.npz")):
        vprefix = nd_path.name.replace("_NODE_DEPTH.npz", "")
        with np.load(nd_path, allow_pickle=False) as z_nd:
            node_depth_cache[vprefix] = {
                "state": np.array(z_nd["state"], dtype=np.uint8),
                "raw_z": np.array(z_nd["raw_z"], dtype=np.float64),
                "second_z": np.array(z_nd["second_z"], dtype=np.float64),
            }

    with np.load(full_dir / "SHARED_CONTROL_AND_SAMPLING.npz", allow_pickle=False) as scs:
        scs_control = np.array(scs["control"], dtype=np.float64)
        scs_rays = np.array(scs["rays"], dtype=np.float64)
        scs_node_px = np.array(scs["node_pixel"], dtype=np.float64)
        scs_offsets = np.array(scs["parent_control_offsets"], dtype=np.int64)

    parents_raw = json.loads((full_dir / "parents.json").read_text(encoding="utf-8"))
    parent_chains: list[ParentFragmentChain] = []

    for pid, prow in enumerate(parents_raw):
        lo, hi = int(scs_offsets[pid, 0]), int(scs_offsets[pid, 1])
        vname = str(prow["view"])
        w2c = np.asarray(cam_lookup[vname]["extrinsic"], dtype=np.float64)
        cam_center = np.linalg.inv(w2c)[:3, 3]

        pts = scs_control[lo:hi].copy()
        rays = scs_rays[lo:hi].copy()
        node_px = scs_node_px[lo:hi].copy()
        uv = np.asarray(prow["uv"], dtype=np.float64)

        ray_sq = np.sum(rays * rays, axis=1)
        z_cam = np.sum((pts - cam_center[None, :]) * rays, axis=1) / np.maximum(ray_sq, 1e-12)

        node_ids = np.asarray(prow["node_ids"], dtype=np.int64)
        nd_info = node_depth_cache.get(vname)
        if nd_info is not None and len(node_ids) == len(pts):
            st = nd_info["state"][node_ids]
            raw_z = nd_info["raw_z"][node_ids]
            sec_z = nd_info["second_z"][node_ids]
        else:
            st = np.ones(len(pts), dtype=np.uint8)
            raw_z = z_cam.copy()
            sec_z = np.full(len(pts), np.nan, dtype=np.float64)

        parent_chains.append(
            ParentFragmentChain(
                parent_id=pid,
                source_view=vname,
                cam_center=cam_center,
                uv=uv,
                rays=rays,
                fitted_z=z_cam,
                raw_z=raw_z,
                second_z=sec_z,
                state=st,
                node_pixel=node_px,
                points_3d=pts,
                is_complementary_seed=False,
            )
        )

    med_p = float(np.median(scs_node_px))
    return MultiModalSceneBundle(
        scene_name="ficus",
        train_views=train_views,
        eval_views=eval_views,
        parents=parent_chains,
        canonical_gaussians_path=full_dir / "gaussians.npz",
        median_pixel_scale=med_p,
        surface_ply_path=resolve_safe_path(surface_ply_path),
        has_silhouette_mask=True,
        bg_val=1.0,
    )


def load_c2l_registry_scene_bundle(
    scene_name: str,
    num_extra_train_views: int = 16,
    device: torch.device | None = None,
    c2l_root: str | Path = "/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_multiview05_v01",
    c2l_code_dir: str | Path = "/home/u00134/3dgs_line/gaer_rade_depth_lift_v01/reproduction/radegs_c2l50_multiview05_v01",
    cache_root: str | Path = "/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs",
) -> MultiModalSceneBundle:
    """Load any scene registered in C2L50 REGISTRY.json (e.g., DTU 'scan24', 'scan65', or 'ficus')."""
    c2l = resolve_safe_path(c2l_root)
    reg_all = json.loads((c2l / "REGISTRY.json").read_text(encoding="utf-8"))["scenes"]
    if scene_name not in reg_all:
        raise ValueError(f"Unknown C2L registry scene: {scene_name}")
    reg = reg_all[scene_name]

    dev = device if device is not None else torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    ply_path = resolve_safe_path(reg["model"])
    bg_val = 1.0 if (scene_name == "ficus" or bool(reg.get("white_background", False))) else 0.0

    cache_dir = resolve_safe_path(Path(cache_root) / f"cache_{scene_name}_c2l_views")
    cache_dir.mkdir(parents=True, exist_ok=True)

    full_dir = c2l / f"arms/C/scenes/{scene_name}/full"
    inp_dir = c2l / f"scenes/{scene_name}/inputs"
    det_dir = c2l / f"scenes/{scene_name}/detector"

    cam_lookup = {str(c["view"]): c for c in reg["cameras"]}
    build_set = set(str(v) for v in reg["build_views"])
    eval_set = set(str(v) for v in reg["eval_views"])
    gs_ho = reg.get("GS_holdout", [])
    holdout_set = eval_set | (set(str(v) for v in gs_ho) if isinstance(gs_ho, (list, tuple, set)) else set())

    train_views: list[MultiModalView] = []
    eval_views: list[MultiModalView] = []
    loaded_train_names: set[str] = set()

    for npz_file in sorted(inp_dir.glob("*.npz")):
        vname = npz_file.stem
        if vname not in cam_lookup:
            continue
        det_file = det_dir / f"{vname}.npz"
        meta = cam_lookup[vname]
        w2c = np.asarray(meta["extrinsic"], dtype=np.float64)
        c2w = np.linalg.inv(w2c)
        with np.load(npz_file, allow_pickle=False) as z_in, np.load(det_file, allow_pickle=False) as z_det:
            rgb = np.clip(np.array(z_in["rgb"], dtype=np.float32), 0.0, 1.0)
            alpha = np.clip(np.array(z_in["alpha"], dtype=np.float32), 0.0, 1.0)
            depth = np.array(z_in["median_camera_z"], dtype=np.float32)
            darkness = np.clip(np.array(z_det["darkness"], dtype=np.float32), 0.0, 1.0)
            marked = np.array(z_det["marked"], dtype=bool)
            skeleton = np.array(z_det["skeleton"], dtype=bool)

        edge_mask = skeleton | (marked & (darkness > 0.22))
        edge_dt, edge_tang = _compute_edge_dt_and_tangent(darkness, edge_mask)
        has_bg = bool(np.mean(alpha < 0.05) > 0.01)
        outside_dt = distance_transform_edt(alpha < 0.05).astype(np.float32) if has_bg else np.zeros_like(alpha, dtype=np.float32)
        front_d = _compute_foreground_depth(depth, alpha)
        normals, depth_jump = _compute_depth_normals_and_jumps(
            depth, alpha, float(meta["fx"]), float(meta["fy"]), float(meta["cx"]), float(meta["cy"])
        )

        is_build = vname in build_set
        is_eval = vname in eval_set
        if not (is_build or is_eval):
            continue

        mv = MultiModalView(
            view_name=vname,
            split="train" if is_build else "test",
            width=int(meta["width"]),
            height=int(meta["height"]),
            fx=float(meta["fx"]),
            fy=float(meta["fy"]),
            cx=float(meta["cx"]),
            cy=float(meta["cy"]),
            w2c=w2c,
            c2w=c2w,
            cam_center=c2w[:3, 3].copy(),
            alpha=alpha,
            outside_hull_dt=outside_dt,
            edge_strength=darkness,
            edge_mask=edge_mask,
            edge_dt=edge_dt,
            edge_tangent_2d=edge_tang,
            skeleton=skeleton,
            rgb=rgb,
            depth=depth,
            front_depth=front_d,
            depth_jump=depth_jump,
            normal_map=normals,
            is_original_c2l_build=is_build,
        )
        if is_build:
            train_views.append(mv)
            loaded_train_names.add(vname)
        elif is_eval:
            eval_views.append(mv)

    # Farthest-point sample extra non-holdout views & render RaDe-GS / 3DGS surface depth + C2L50 edges
    if num_extra_train_views > 0:
        cand_names = sorted(k for k in cam_lookup.keys() if k not in loaded_train_names and k not in holdout_set)
        selected_centers = [v.cam_center for v in train_views]
        chosen_extra: list[str] = []
        remaining = list(cand_names)
        while remaining and len(chosen_extra) < num_extra_train_views:
            best_name = None
            best_min_d = -1.0
            for cname in remaining:
                c_pos = np.linalg.inv(np.asarray(cam_lookup[cname]["extrinsic"], dtype=np.float64))[:3, 3]
                min_d = min(float(np.linalg.norm(c_pos - sc)) for sc in selected_centers) if selected_centers else 1.0
                if min_d > best_min_d:
                    best_min_d = min_d
                    best_name = cname
            assert best_name is not None
            chosen_extra.append(best_name)
            remaining.remove(best_name)
            selected_centers.append(np.linalg.inv(np.asarray(cam_lookup[best_name]["extrinsic"], dtype=np.float64))[:3, 3])

        renderer_det: Surface3DGSRendererAndDetector | None = None
        for vname in chosen_extra:
            meta = cam_lookup[vname]
            w2c = np.asarray(meta["extrinsic"], dtype=np.float64)
            c2w = np.linalg.inv(w2c)
            cfile = cache_dir / f"{vname}_c2l_3dgs.npz"
            if cfile.is_file():
                with np.load(cfile, allow_pickle=False) as zc_cache:
                    rgb = np.array(zc_cache["rgb"], dtype=np.float32)
                    alpha = np.array(zc_cache["alpha"], dtype=np.float32)
                    depth = np.array(zc_cache["depth"], dtype=np.float32)
                    darkness = np.array(zc_cache["darkness"], dtype=np.float32)
                    marked = np.array(zc_cache["marked"], dtype=bool)
                    skeleton = np.array(zc_cache["skeleton"], dtype=bool)
            else:
                if renderer_det is None:
                    renderer_det = Surface3DGSRendererAndDetector(ply_path, Path(c2l_code_dir), device=dev)
                rendered = renderer_det.render_and_detect(
                    w2c, float(meta["fx"]), float(meta["fy"]), float(meta["cx"]), float(meta["cy"]),
                    int(meta["width"]), int(meta["height"]), bg_val=bg_val,
                )
                rgb, alpha, depth = rendered["rgb"], rendered["alpha"], rendered["depth"]
                darkness, marked, skeleton = rendered["darkness"], rendered["marked"], rendered["skeleton"]
                np.savez_compressed(cfile, rgb=rgb, alpha=alpha, depth=depth, darkness=darkness, marked=marked, skeleton=skeleton)

            edge_mask = skeleton | (marked & (darkness > 0.22))
            edge_dt, edge_tang = _compute_edge_dt_and_tangent(darkness, edge_mask)
            has_bg = bool(np.mean(alpha < 0.05) > 0.01)
            outside_dt = distance_transform_edt(alpha < 0.05).astype(np.float32) if has_bg else np.zeros_like(alpha, dtype=np.float32)
            front_d = _compute_foreground_depth(depth, alpha)
            normals, depth_jump = _compute_depth_normals_and_jumps(
                depth, alpha, float(meta["fx"]), float(meta["fy"]), float(meta["cx"]), float(meta["cy"])
            )
            train_views.append(
                MultiModalView(
                    view_name=vname, split="train",
                    width=int(meta["width"]), height=int(meta["height"]),
                    fx=float(meta["fx"]), fy=float(meta["fy"]), cx=float(meta["cx"]), cy=float(meta["cy"]),
                    w2c=w2c, c2w=c2w, cam_center=c2w[:3, 3].copy(),
                    alpha=alpha, outside_hull_dt=outside_dt, edge_strength=darkness,
                    edge_mask=edge_mask, edge_dt=edge_dt, edge_tangent_2d=edge_tang, skeleton=skeleton,
                    rgb=rgb, depth=depth, front_depth=front_d, depth_jump=depth_jump, normal_map=normals,
                    is_original_c2l_build=False,
                )
            )

    # Load C2L parents & ray provenance
    node_depth_cache: dict[str, dict[str, np.ndarray]] = {}
    for nd_path in sorted((full_dir / "depth_graph").glob("*_NODE_DEPTH.npz")):
        vprefix = nd_path.name.replace("_NODE_DEPTH.npz", "")
        with np.load(nd_path, allow_pickle=False) as z_nd:
            node_depth_cache[vprefix] = {
                "state": np.array(z_nd["state"], dtype=np.uint8),
                "raw_z": np.array(z_nd["raw_z"], dtype=np.float64),
                "second_z": np.array(z_nd["second_z"], dtype=np.float64),
            }

    with np.load(full_dir / "SHARED_CONTROL_AND_SAMPLING.npz", allow_pickle=False) as scs:
        scs_control = np.array(scs["control"], dtype=np.float64)
        scs_rays = np.array(scs["rays"], dtype=np.float64)
        scs_node_px = np.array(scs["node_pixel"], dtype=np.float64)
        scs_offsets = np.array(scs["parent_control_offsets"], dtype=np.int64)

    parents_raw = json.loads((full_dir / "parents.json").read_text(encoding="utf-8"))
    parent_chains: list[ParentFragmentChain] = []
    for pid, prow in enumerate(parents_raw):
        lo, hi = int(scs_offsets[pid, 0]), int(scs_offsets[pid, 1])
        vname = str(prow["view"])
        w2c = np.asarray(cam_lookup[vname]["extrinsic"], dtype=np.float64)
        cam_center = np.linalg.inv(w2c)[:3, 3]
        pts = scs_control[lo:hi].copy()
        rays = scs_rays[lo:hi].copy()
        node_px = scs_node_px[lo:hi].copy()
        uv = np.asarray(prow["uv"], dtype=np.float64)
        ray_sq = np.sum(rays * rays, axis=1)
        z_cam = np.sum((pts - cam_center[None, :]) * rays, axis=1) / np.maximum(ray_sq, 1e-12)

        node_ids = np.asarray(prow["node_ids"], dtype=np.int64)
        nd_info = node_depth_cache.get(vname)
        if nd_info is not None and len(node_ids) == len(pts):
            st = nd_info["state"][node_ids]
            raw_z = nd_info["raw_z"][node_ids]
            sec_z = nd_info["second_z"][node_ids]
        else:
            st = np.ones(len(pts), dtype=np.uint8)
            raw_z = z_cam.copy()
            sec_z = np.full(len(pts), np.nan, dtype=np.float64)

        parent_chains.append(
            ParentFragmentChain(
                parent_id=pid, source_view=vname, cam_center=cam_center,
                uv=uv, rays=rays, fitted_z=z_cam, raw_z=raw_z, second_z=sec_z,
                state=st, node_pixel=node_px, points_3d=pts, is_complementary_seed=False,
            )
        )

    has_sil = bool(np.median([np.mean(v.alpha < 0.05) for v in train_views]) > 0.02)
    return MultiModalSceneBundle(
        scene_name=scene_name,
        train_views=train_views,
        eval_views=eval_views,
        parents=parent_chains,
        canonical_gaussians_path=full_dir / "gaussians.npz",
        median_pixel_scale=float(np.median(scs_node_px)),
        surface_ply_path=ply_path,
        has_silhouette_mask=has_sil,
        bg_val=bg_val,
    )


def load_synthetic_3dgs_scene_bundle(
    scene_name: str,
    num_base_views: int = 8,
    num_extra_views: int = 16,
    device: torch.device | None = None,
    foundation_root: str | Path = "/home/u00134/3dgs_line/tier1/out/multiscene_foundation/training",
    cglib_root: str | Path = "/home/u00134/cglib/data/full",
    c2l_code_dir: str | Path = "/home/u00134/3dgs_line/gaer_rade_depth_lift_v01/reproduction/radegs_c2l50_multiview05_v01",
    cache_root: str | Path = "/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs",
) -> tuple[MultiModalSceneBundle, dict[str, np.ndarray]]:
    """End-to-end loader for NeRF Synthetic 3DGS models ('drums', 'chair', 'lego') without pre-existing C2L assets."""
    from .multiview_seed import _trace_2d_skeleton_chains

    dev = device if device is not None else torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    ply_path = resolve_safe_path(
        Path(foundation_root) / f"{scene_name}/seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply"
    )
    scene_data_dir = resolve_safe_path(Path(cglib_root) / scene_name)
    cache_dir = resolve_safe_path(Path(cache_root) / f"cache_{scene_name}_c2l_views")
    cache_dir.mkdir(parents=True, exist_ok=True)

    gl_flip = np.diag([1.0, -1.0, -1.0, 1.0])
    cam_lookup: dict[str, dict[str, Any]] = {}
    for split_name in ("train", "test"):
        tf_doc = json.loads(resolve_safe_path(scene_data_dir / f"transforms_{split_name}.json").read_text(encoding="utf-8"))
        fov_x = float(tf_doc["camera_angle_x"])
        w = h = 800
        fx = fy = 0.5 * w / math.tan(0.5 * fov_x)
        for frame in tf_doc["frames"]:
            stem = Path(frame["file_path"]).name
            vname = f"{split_name}_{stem}"
            c2w_gl = np.asarray(frame["transform_matrix"], dtype=np.float64)
            c2w = c2w_gl @ gl_flip
            w2c = np.linalg.inv(c2w)
            cam_lookup[vname] = {
                "view": vname, "split": split_name, "width": w, "height": h,
                "fx": fx, "fy": fy, "cx": 399.5, "cy": 399.5,
                "extrinsic": w2c, "c2w": c2w, "cam_center": c2w[:3, 3].copy(),
                "file_path": str(scene_data_dir / f"{frame['file_path']}.png"),
            }

    # Farthest-point sample (num_base_views + num_extra_views) training cameras starting from train_r_0
    train_cands = sorted(k for k, v in cam_lookup.items() if v["split"] == "train")
    chosen_train = [train_cands[0]]
    rem_train = train_cands[1:]
    tot_train_needed = num_base_views + num_extra_views
    while rem_train and len(chosen_train) < tot_train_needed:
        best_k = max(
            rem_train,
            key=lambda k: min(float(np.linalg.norm(cam_lookup[k]["cam_center"] - cam_lookup[s]["cam_center"])) for s in chosen_train),
        )
        chosen_train.append(best_k)
        rem_train.remove(best_k)

    eval_names = [k for k in ("test_r_1", "test_r_7", "test_r_14", "test_r_79", "test_r_99") if k in cam_lookup]
    renderer_det: Surface3DGSRendererAndDetector | None = None

    def _load_or_render_view(vname: str, is_train: bool, is_base: bool) -> MultiModalView:
        nonlocal renderer_det
        meta = cam_lookup[vname]
        w2c, c2w = meta["extrinsic"], meta["c2w"]
        cfile = cache_dir / f"{vname}_c2l_3dgs.npz"
        if cfile.is_file():
            with np.load(cfile, allow_pickle=False) as zc_cache:
                rgb = np.array(zc_cache["rgb"], dtype=np.float32)
                alpha = np.array(zc_cache["alpha"], dtype=np.float32)
                depth = np.array(zc_cache["depth"], dtype=np.float32)
                darkness = np.array(zc_cache["darkness"], dtype=np.float32)
                marked = np.array(zc_cache["marked"], dtype=bool)
                skeleton = np.array(zc_cache["skeleton"], dtype=bool)
        else:
            if renderer_det is None:
                renderer_det = Surface3DGSRendererAndDetector(ply_path, Path(c2l_code_dir), device=dev)
            rendered = renderer_det.render_and_detect(
                w2c, float(meta["fx"]), float(meta["fy"]), float(meta["cx"]), float(meta["cy"]),
                int(meta["width"]), int(meta["height"]), bg_val=1.0,
            )
            rgb, alpha, depth = rendered["rgb"], rendered["alpha"], rendered["depth"]
            darkness, marked, skeleton = rendered["darkness"], rendered["marked"], rendered["skeleton"]
            np.savez_compressed(cfile, rgb=rgb, alpha=alpha, depth=depth, darkness=darkness, marked=marked, skeleton=skeleton)

        if is_train and Path(meta["file_path"]).is_file():
            gt_rgba = np.asarray(Image.open(resolve_safe_path(meta["file_path"])).convert("RGBA"), dtype=np.uint8)
            gt_alpha = gt_rgba[..., 3].astype(np.float32) / 255.0
            hull_alpha = np.minimum(alpha, gt_alpha)
        elif (not is_train) and Path(meta["file_path"]).is_file():
            # For test views, use GT RGB display & GT silhouette mask for fair evaluation!
            gt_rgba = np.asarray(Image.open(resolve_safe_path(meta["file_path"])).convert("RGBA"), dtype=np.uint8)
            gt_a = gt_rgba[..., 3:4].astype(np.float32) / 255.0
            rgb = (gt_rgba[..., :3].astype(np.float32) / 255.0) * gt_a + (1.0 - gt_a)
            hull_alpha = gt_a[..., 0]
        else:
            hull_alpha = alpha

        edge_mask = skeleton | (marked & (darkness > 0.22))
        edge_dt, edge_tang = _compute_edge_dt_and_tangent(darkness, edge_mask)
        outside_dt = distance_transform_edt(hull_alpha < 0.05).astype(np.float32)
        front_d = _compute_foreground_depth(depth, alpha)
        normals, depth_jump = _compute_depth_normals_and_jumps(
            depth, alpha, float(meta["fx"]), float(meta["fy"]), float(meta["cx"]), float(meta["cy"])
        )
        return MultiModalView(
            view_name=vname, split="train" if is_train else "test",
            width=int(meta["width"]), height=int(meta["height"]),
            fx=float(meta["fx"]), fy=float(meta["fy"]), cx=float(meta["cx"]), cy=float(meta["cy"]),
            w2c=w2c, c2w=c2w, cam_center=meta["cam_center"].copy(),
            alpha=hull_alpha, outside_hull_dt=outside_dt, edge_strength=darkness,
            edge_mask=edge_mask, edge_dt=edge_dt, edge_tangent_2d=edge_tang, skeleton=skeleton,
            rgb=rgb, depth=depth, front_depth=front_d, depth_jump=depth_jump, normal_map=normals,
            is_original_c2l_build=is_base,
        )

    train_views = [_load_or_render_view(vn, True, idx < num_base_views) for idx, vn in enumerate(chosen_train)]
    eval_views = [_load_or_render_view(vn, False, False) for vn in eval_names]

    # Lift initial single-view 2D skeleton chains from the 8 base views to create both `parents` and Raw 8-View Baseline!
    parents: list[ParentFragmentChain] = []
    raw_means, raw_covs, raw_opacs, raw_cols = [], [], [], []
    eye3 = np.eye(3, dtype=np.float64)
    pid = 0
    all_node_px: list[np.ndarray] = []

    for vw in train_views[:num_base_views]:
        assert vw.skeleton is not None and vw.front_depth is not None and vw.depth is not None
        alpha_dil = cv2.dilate((vw.alpha > 0.20).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        cand_skel = vw.skeleton & (vw.edge_strength > 0.22) & alpha_dil
        chains_2d = _trace_2d_skeleton_chains(cand_skel, min_pixels=6)
        R_c2w = vw.c2w[:3, :3]
        fx, fy, cx, cy = vw.fx, vw.fy, vw.cx, vw.cy
        fg_mask = (vw.alpha > 0.45) & (vw.front_depth > 0.2)

        for uv_full in chains_2d:
            idx_sub = list(range(0, len(uv_full) - 1, 2)) + [len(uv_full) - 1]
            uv_sub = uv_full[idx_sub].astype(np.float64)
            z_init = np.zeros(len(uv_sub), dtype=np.float64)
            states = np.ones(len(uv_sub), dtype=np.uint8)
            valid_n = np.ones(len(uv_sub), dtype=bool)

            for k_i, (u_val, v_val) in enumerate(uv_sub):
                ci, ri = int(round(u_val)), int(round(v_val))
                patch_fg = fg_mask[max(0, ri - 2) : min(vw.height, ri + 3), max(0, ci - 2) : min(vw.width, ci + 3)]
                if int(patch_fg.sum()) < 1:
                    # Uncalibrated rim extrapolation (simulating raw single-view C2L depth jump!)
                    patch_any = vw.depth[max(0, ri - 4) : min(vw.height, ri + 5), max(0, ci - 4) : min(vw.width, ci + 5)]
                    pos_z = patch_any[patch_any > 0.2]
                    if len(pos_z) == 0:
                        valid_n[k_i] = False
                        continue
                    z_init[k_i] = float(np.median(pos_z))
                    states[k_i] = 2
                else:
                    patch_z = vw.depth[max(0, ri - 2) : min(vw.height, ri + 3), max(0, ci - 2) : min(vw.width, ci + 3)][patch_fg]
                    z0 = float(np.median(patch_z))
                    z_init[k_i] = z0
                    p_loc = z0 / math.sqrt(fx * fy)
                    if vw.alpha[ri, ci] < 0.80 or float(patch_z.max() - patch_z.min()) > 3.5 * p_loc:
                        states[k_i] = 2

            if int(valid_n.sum()) < 3:
                continue
            uv_sub, z_init, states = uv_sub[valid_n], z_init[valid_n], states[valid_n]
            cam_dirs = np.stack([(uv_sub[:, 0] - cx) / fx, (uv_sub[:, 1] - cy) / fy, np.ones(len(uv_sub))], axis=1)
            rays_w = cam_dirs @ R_c2w.T
            pts_3d = vw.cam_center[None, :] + z_init[:, None] * rays_w
            node_px = z_init / math.sqrt(fx * fy)
            all_node_px.append(node_px)

            parents.append(
                ParentFragmentChain(
                    parent_id=pid, source_view=vw.view_name, cam_center=vw.cam_center.copy(),
                    uv=uv_sub, rays=rays_w, fitted_z=z_init, raw_z=z_init.copy(),
                    second_z=np.full(len(uv_sub), np.nan), state=states, node_pixel=node_px,
                    points_3d=pts_3d, is_complementary_seed=False,
                )
            )
            pid += 1

            # Populate Raw 8-View Single-View Lifted Line-Gaussian Bank for baseline comparison
            p_c = float(np.median(node_px))
            seg_v = pts_3d[1:] - pts_3d[:-1]
            seg_l = np.linalg.norm(seg_v, axis=1)
            for s_i in range(len(seg_v)):
                n_g = max(1, min(16, int(math.ceil(seg_l[s_i] / max(0.35 * p_c, 1e-4)))))
                t_dir = seg_v[s_i] / max(seg_l[s_i], 1e-9)
                us = (np.arange(n_g, dtype=np.float64) + 0.5) / n_g
                mids = pts_3d[s_i][None, :] + us[:, None] * seg_v[s_i][None, :]
                sp = max(0.75 * p_c, 0.65 * (seg_l[s_i] / n_g))
                sw = 0.38 * p_c
                tt = np.outer(t_dir, t_dir)
                cov = (sp ** 2) * tt + (sw ** 2) * (eye3 - tt)
                raw_means.append(mids)
                raw_covs.append(np.repeat(cov[None, :, :], n_g, axis=0))
                raw_opacs.append(np.full(n_g, 0.125, dtype=np.float64))
                raw_cols.append(np.zeros((n_g, 3), dtype=np.float64))

    med_p = float(np.median(np.concatenate(all_node_px))) if all_node_px else 0.0035
    raw_gs = {
        "means": np.concatenate(raw_means, axis=0) if raw_means else np.zeros((0, 3)),
        "covariance": np.concatenate(raw_covs, axis=0) if raw_covs else np.zeros((0, 3, 3)),
        "opacity": np.concatenate(raw_opacs, axis=0) if raw_opacs else np.zeros((0,)),
        "colors": np.concatenate(raw_cols, axis=0) if raw_cols else np.zeros((0, 3)),
    }
    bundle = MultiModalSceneBundle(
        scene_name=scene_name,
        train_views=train_views,
        eval_views=eval_views,
        parents=parents,
        canonical_gaussians_path=None,
        median_pixel_scale=med_p,
        surface_ply_path=ply_path,
        has_silhouette_mask=True,
        bg_val=1.0,
    )
    return bundle, raw_gs
