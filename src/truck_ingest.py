"""Experiment B — Truck (real capture, COLMAP-estimated poses) camera ingestion.

Alternate camera SOURCE for the SHIPPED M1b pipeline. NOT a method change: the feature-line
method consumes common.Camera (K + w2c) and is convention-agnostic; this is the ingestion
analogue of readColmapSceneInfo vs readNerfSyntheticInfo in the 3DGS trainer. Poses are
ESTIMATED (COLMAP SfM), NOT perfect — that is the object of experiment B.

Camera source = out/3dgs_truck/cameras.json, written by the FROZEN 3DGS training itself, so
the feature-line eval uses byte-identical cameras to the model it renders. Convention
(graphdeco camera_to_JSON): position = camera center in world (c2w[:3,3]); rotation = c2w
rotation, OpenCV world (+Y down, +Z fwd). => w2c_R = R.T ; w2c_t = -R.T @ position.
Validated numerically (scripts/truck_cam_ab.py): convention A on-screen median 0.324 vs
transposed B 0.169; 404k dense splatted px at cam0; 66.7% in-front on 2.58M gaussians
(incl. courtyard background). Consistent with 72.2% on-screen for the 136k on-surface SfM pts.
"""
import json
import os
import cv2
import numpy as np
from plyfile import PlyData

from common import Camera, SH_C0

TRUCK_ROOT = os.path.expanduser("~/3dgs_line/tier1")
CAMS_JSON = f"{TRUCK_ROOT}/out/3dgs_truck/cameras.json"
PLY_30K = f"{TRUCK_ROOT}/out/3dgs_truck/point_cloud/iteration_30000/point_cloud.ply"
IMG_DIR = f"{TRUCK_ROOT}/data/realcap/tandt/truck/images"


def load_truck_cameras(cams_json=CAMS_JSON, img_dir=IMG_DIR):
    """Return (cams, rgb_paths) mirroring common.load_cameras, from COLMAP-estimated poses."""
    meta = json.load(open(cams_json))
    cams, rgb_paths = [], []
    for c in meta:
        R = np.array(c["rotation"], np.float64)      # c2w rotation, OpenCV world
        pos = np.array(c["position"], np.float64)    # camera center in world
        W, H = int(c["width"]), int(c["height"])
        fx, fy = float(c["fx"]), float(c["fy"])
        name = c["img_name"]
        # T&T ships HALF-RESOLUTION images while COLMAP intrinsics are full-res.
        # The gbuffer renders at cam W/H and photo_edge_dt reads the on-disk jpg, so the
        # two must agree. Rescale K + W/H to the ACTUAL image size (pose/method untouched;
        # this is the standard 3DGS resolution-downscale, applied consistently to both paths).
        _ip = f"{img_dir}/{name}.jpg"
        _im = cv2.imread(_ip)
        if _im is not None:
            aH, aW = _im.shape[:2]
            if (aW, aH) != (W, H):
                sx, sy = aW / float(W), aH / float(H)
                fx, fy = fx * sx, fy * sy
                W, H = aW, aH
        K = np.array([[fx, 0, W / 2.0], [0, fy, H / 2.0], [0, 0, 1]], np.float64)
        w2c = np.eye(4)
        w2c[:3, :3] = R.T
        w2c[:3, 3] = -R.T @ pos
        cams.append(Camera(K, w2c, H, W, name=name))
        rgb_paths.append(f"{img_dir}/{name}.jpg")
    return cams, rgb_paths


def load_truck_gaussians(ply=PLY_30K):
    """Load the FROZEN vanilla-3DGS Truck ply into the same dict schema as common.load_gaussians.
    Byte-identical field parsing (scale_0..2, rot_0..3, f_dc_0..2) — same load_gaussians path."""
    from common import quat_to_rotmat
    p = PlyData.read(ply)["vertex"]
    mu = np.stack([p["x"], p["y"], p["z"]], 1).astype(np.float64)
    opacity = 1.0 / (1.0 + np.exp(-np.asarray(p["opacity"], np.float64)))
    scale = np.exp(np.stack([p["scale_0"], p["scale_1"], p["scale_2"]], 1).astype(np.float64))
    quat = np.stack([p["rot_0"], p["rot_1"], p["rot_2"], p["rot_3"]], 1).astype(np.float64)
    f_dc = np.stack([p["f_dc_0"], p["f_dc_1"], p["f_dc_2"]], 1).astype(np.float64)
    albedo = np.clip(0.5 + SH_C0 * f_dc, 0.0, 1.0)
    R = quat_to_rotmat(quat)
    amin = scale.argmin(1)
    normal = R[np.arange(len(mu)), :, amin]
    normal /= np.linalg.norm(normal, axis=1, keepdims=True) + 1e-12
    return {"mu": mu, "opacity": opacity, "scale": scale, "quat": quat,
            "normal": normal, "scale_max": scale.max(1), "f_dc": f_dc, "albedo": albedo}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(TRUCK_ROOT, "src"))
    from common import project
    cams, paths = load_truck_cameras()
    g = load_truck_gaussians()
    print(f"cams {len(cams)}  gaussians {len(g['mu'])}  imgs exist:",
          sum(os.path.exists(p) for p in paths[:5]), "/5 sampled")
    # smoke: project through the SHIPPED common.project on the first cam
    uv, z = project(g["mu"], cams[0])
    on = (z > 0) & (uv[:, 0] >= 0) & (uv[:, 0] < cams[0].W) & (uv[:, 1] >= 0) & (uv[:, 1] < cams[0].H)
    print(f"cam0 via common.project: on-screen frac {on.mean():.3f}  center {cams[0].center}")
    print("SMOKE OK" if on.mean() > 0.25 else "SMOKE SUSPECT")
