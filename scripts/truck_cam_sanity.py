"""Experiment B — projection sanity for the Truck camera adapter (DRIVER-SIDE, de-risk).
Reads out/3dgs_truck/cameras.json (written by the frozen 3DGS training itself) and the
trained gaussian ply, builds common.Camera-style (K, w2c), reprojects the gaussian
centers, and reports the on-screen / in-front fraction. No method change, no tuning.

Convention derivation (graphdeco camera_to_JSON):
  position = camera center in world (c2w[:3,3]);  rotation = c2w[:3,:3], OpenCV/COLMAP
  world (+Y down, +Z forward). => w2c_R = rotation.T ; w2c_t = -rotation.T @ position.
  K = [[fx,0,W/2],[0,fy,H/2],[0,0,1]] (PINHOLE undistorted, cx/cy=center assumed).
project() convention (src/common.py): campts = w2c_R@X + w2c_t ; z=campts.z ; uv=K@campts.
"""
import json, numpy as np
from plyfile import PlyData

CJ = "out/3dgs_truck/cameras.json"
PLY = "out/3dgs_truck/point_cloud/iteration_30000/point_cloud.ply"

cams = json.load(open(CJ))
p = PlyData.read(PLY)["vertex"]
mu = np.stack([p["x"], p["y"], p["z"]], 1).astype(np.float64)
print(f"gaussians: {len(mu)}  cams: {len(cams)}")

frac_front, frac_screen = [], []
for c in cams:
    R = np.array(c["rotation"], np.float64)      # c2w rotation
    pos = np.array(c["position"], np.float64)    # camera center world
    W, H = c["width"], c["height"]
    fx, fy = c["fx"], c["fy"]
    K = np.array([[fx, 0, W/2], [0, fy, H/2], [0, 0, 1]], np.float64)
    w2c_R = R.T
    w2c_t = -R.T @ pos
    campts = (w2c_R @ mu.T).T + w2c_t
    z = campts[:, 2]
    uv = (K @ campts.T).T
    uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
    infront = z > 0
    onscreen = infront & (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
    frac_front.append(infront.mean())
    frac_screen.append(onscreen.mean())

frac_front = np.array(frac_front); frac_screen = np.array(frac_screen)
print(f"in-front  frac: median {np.median(frac_front):.3f}  min {frac_front.min():.3f}  max {frac_front.max():.3f}")
print(f"on-screen frac: median {np.median(frac_screen):.3f}  min {frac_screen.min():.3f}  max {frac_screen.max():.3f}")
# Sanity: a correct convention on a bounded object should put a large, spatially-coherent
# fraction on-screen for most cams. A TRANSPOSED/flipped convention collapses to ~0.
print("VERDICT:", "PLAUSIBLE" if np.median(frac_screen) > 0.5 else "SUSPECT (convention likely wrong)")
