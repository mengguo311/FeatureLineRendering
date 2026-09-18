"""tier1/src/common.py — shared METHOD-PATH utilities: cameras + gaussian ply loading.
HARD INVARIANT: no mesh, no trimesh, no mesh_oracle import anywhere in this file.
Camera convention (proven in bcr/align_check.py): blender c2w (OpenGL) -> opencv w2c
via right-multiply diag(1,-1,-1,1) then invert.
"""
import json
import os
import numpy as np
from plyfile import PlyData

CGLIB = os.path.expanduser("~/cglib")
W = H = 800


class Camera:
    def __init__(self, K, w2c, H, W, name=""):
        self.K = np.asarray(K, np.float64)
        self.w2c = np.asarray(w2c, np.float64)
        self.H, self.W = H, W
        self.name = name
        self.f = float(self.K[0, 0])
        c2w = np.linalg.inv(self.w2c)
        self.center = c2w[:3, 3].copy()  # camera center in world


def load_cameras(scene, root=CGLIB):
    """All train cameras for a scene. Returns (cams, rgb_paths)."""
    meta = json.load(open(f"{root}/data/full/{scene}/transforms_train.json"))
    f = 0.5 * W / np.tan(0.5 * meta["camera_angle_x"])
    K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]], np.float64)
    flip = np.diag([1.0, -1.0, -1.0, 1.0])
    cams, rgb_paths = [], []
    for fr in meta["frames"]:
        c2w = np.array(fr["transform_matrix"], np.float64) @ flip
        w2c = np.linalg.inv(c2w)
        name = os.path.basename(fr["file_path"])
        cams.append(Camera(K, w2c, H, W, name=name))
        rgb_paths.append(f"{root}/data/full/{scene}/train/{name}.png")
    return cams, rgb_paths


def quat_to_rotmat(q):
    """q: [N,4] w-first (3DGS rot_0..3). Returns R [N,3,3]; columns = principal axes."""
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((len(q), 3, 3), np.float64)
    R[:, 0, 0] = 1 - 2 * (y * y + z * z)
    R[:, 0, 1] = 2 * (x * y - w * z)
    R[:, 0, 2] = 2 * (x * z + w * y)
    R[:, 1, 0] = 2 * (x * y + w * z)
    R[:, 1, 1] = 1 - 2 * (x * x + z * z)
    R[:, 1, 2] = 2 * (y * z - w * x)
    R[:, 2, 0] = 2 * (x * z - w * y)
    R[:, 2, 1] = 2 * (y * z + w * x)
    R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


SH_C0 = 0.28209479177387814   # Y_00, the SH degree-0 basis value


def load_gaussians(scene, root=CGLIB):
    """Load vanilla 3DGS ply. Returns dict with:
    mu[N,3], opacity[N] (sigmoid applied), scale[N,3] (exp applied), quat[N,4],
    normal[N,3] (shortest-covariance axis, UNORIENTED sign), scale_max[N],
    f_dc[N,3] (raw SH degree-0 coefficients) and albedo[N,3].

    albedo = clip(0.5 + SH_C0 * f_dc, 0, 1) is the VIEW-INDEPENDENT diffuse base colour:
    the degree-0 term alone, with NO view-direction evaluation of the 45 f_rest
    coefficients. That is deliberate — it is the quantity that should be continuous
    across a geometric crease (same material both sides) and discontinuous across a
    printed pattern, which is exactly the hypothesis STEP 0.5 tests."""
    p = PlyData.read(f"{root}/outputs/{scene}_static/point_cloud.ply")["vertex"]
    mu = np.stack([p["x"], p["y"], p["z"]], 1).astype(np.float64)
    opacity = 1.0 / (1.0 + np.exp(-np.asarray(p["opacity"], np.float64)))
    scale = np.exp(np.stack([p["scale_0"], p["scale_1"], p["scale_2"]], 1).astype(np.float64))
    quat = np.stack([p["rot_0"], p["rot_1"], p["rot_2"], p["rot_3"]], 1).astype(np.float64)
    f_dc = np.stack([p["f_dc_0"], p["f_dc_1"], p["f_dc_2"]], 1).astype(np.float64)
    albedo = np.clip(0.5 + SH_C0 * f_dc, 0.0, 1.0)
    R = quat_to_rotmat(quat)
    amin = scale.argmin(1)
    normal = R[np.arange(len(mu)), :, amin]  # column of R with smallest scale
    normal /= np.linalg.norm(normal, axis=1, keepdims=True) + 1e-12
    return {
        "mu": mu, "opacity": opacity, "scale": scale, "quat": quat,
        "normal": normal, "scale_max": scale.max(1),
        "f_dc": f_dc, "albedo": albedo,
    }


def project(pts, cam):
    """pts[N,3] world -> (uv[N,2], z[N] camera depth)."""
    campts = (cam.w2c[:3, :3] @ pts.T).T + cam.w2c[:3, 3]
    z = campts[:, 2]
    uv = (cam.K @ campts.T).T
    uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
    return uv, z
