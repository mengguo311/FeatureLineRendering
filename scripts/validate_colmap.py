"""Cheap projection-sanity check for the COLMAP loader (NO training, NO metric claim).

Loads the COLMAP model, projects the sparse SfM points into a handful of cameras
using EXACTLY the shipped Camera.full_proj_transform, and reports the fraction that
land in front of the camera and inside the image. A correct intrinsic+extrinsic
chain puts the large majority of a camera's own visible SfM points on-screen.

This validates ONLY that the ingestion math matches gs_io's raster convention. It
makes no claim about stroke counts, precision, or the crown thesis.
"""
import sys

import numpy as np
import torch

sys.path.insert(0, ".")
from scripts.colmap_loader import load_colmap  # noqa: E402


def project(pts_xyz, cam):
    N = pts_xyz.shape[0]
    homo = np.concatenate([pts_xyz, np.ones((N, 1))], axis=1)
    fp = cam.full_proj_transform.cpu().numpy()          # [4,4], row-vector convention
    clip = homo @ fp
    w = clip[:, 3:4]
    in_front = (w[:, 0] > 1e-6)
    ndc = clip[:, :3] / np.where(w == 0, 1e-9, w)
    x_px = (ndc[:, 0] + 1) * 0.5 * cam.image_width
    y_px = (ndc[:, 1] + 1) * 0.5 * cam.image_height
    on = in_front & (x_px >= 0) & (x_px < cam.image_width) & \
        (y_px >= 0) & (y_px < cam.image_height)
    return in_front, on


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data/realcap/tandt/truck"
    ds = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    print(f"[validate] loading COLMAP model at {data_dir} (downscale={ds})")
    cams, xyz, rgb = load_colmap(data_dir, downscale=ds)
    print(f"[validate] {len(cams)} cameras, {xyz.shape[0]} SfM points")
    print(f"[validate] first cam: {cams[0].name}  H={cams[0].image_height} "
          f"W={cams[0].image_width}  FoVx={np.degrees(cams[0].FoVx):.2f}deg "
          f"FoVy={np.degrees(cams[0].FoVy):.2f}deg")
    # camera-center spread (sanity: real capture -> nonzero baseline)
    centers = torch.stack([c.camera_center for c in cams]).cpu().numpy()
    extent = np.linalg.norm(centers - centers.mean(0), axis=1).max()
    print(f"[validate] camera-center extent radius = {extent:.3f}")

    fracs = []
    for i in np.linspace(0, len(cams) - 1, 6).astype(int):
        cam = cams[i]
        in_front, on = project(xyz, cam)
        frac_front = in_front.mean()
        frac_on = on.mean()
        fracs.append(frac_on)
        print(f"[validate] cam[{i:3d}] {cam.name:>12}: "
              f"in_front={frac_front*100:5.1f}%  on_screen={frac_on*100:5.1f}%")
    med = float(np.median(fracs))
    print(f"[validate] median on-screen fraction across sampled cams = {med*100:.1f}%")
    # A globally-consistent SfM cloud: each camera sees a SUBSET on-screen; median
    # on-screen of the FULL cloud is typically 15-45% (the rest is behind/outside
    # this view). The hard failure signature of a broken chain is ~0% on-screen or
    # ~0% in front. Report, do not gate a thesis on it.
    ok = med > 0.05 and all(project(xyz, cams[i])[0].mean() > 0.30
                            for i in np.linspace(0, len(cams) - 1, 6).astype(int))
    print(f"[validate] PROJECTION CHAIN {'PLAUSIBLE' if ok else 'SUSPECT'} "
          f"(heuristic, not a thesis gate)")


if __name__ == "__main__":
    main()
