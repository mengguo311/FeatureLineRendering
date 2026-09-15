"""COLMAP ingestion for the shipped VFSD-GS pipeline (experiment B: real capture).

Parses a COLMAP `sparse/0` model (cameras.bin, images.bin, points3D.bin) written
by the standard reconstruction and returns Camera objects that are BYTE-COMPATIBLE
with vfsdgs.gs_io.Camera (same world_view/full_proj convention as load_blender),
plus the sparse point cloud (xyz + rgb) for SfM-based init.

This is EVAL/INGESTION infra only. No method change, no per-scene tuning. Poses are
ESTIMATED (COLMAP), NOT perfect — that is the whole point of experiment B.

Binary format follows the canonical COLMAP read_write_model.py spec.

CONVENTION NOTE (validated by scripts/validate_colmap.py projection test):
COLMAP stores world->camera (R = qvec2rotmat(qvec), t = tvec), camera convention
+Y down / +Z forward. gs_io.Camera expects a c2w in OpenGL convention (+Y up /
+Z back) and internally flips cols 1:3 back to COLMAP. So we build c2w_colmap =
inv([R|t]), flip cols 1,2 to OpenGL, hand to Camera, which flips them back -> net
identity, correct w2c reproduced. fovx from fx; Camera derives fovy from fx and the
image aspect (assumes fx==fy up to pixels; T&T PINHOLE fx/fy differ <0.3%, noted).
"""
import collections
import os
import struct

import numpy as np
import torch

from vfsdgs.gs_io import Camera

CameraModel = collections.namedtuple("CameraModel", ["model_id", "model_name", "num_params"])
CAMERA_MODELS = {
    CameraModel(0, "SIMPLE_PINHOLE", 3),
    CameraModel(1, "PINHOLE", 4),
    CameraModel(2, "SIMPLE_RADIAL", 4),
    CameraModel(3, "RADIAL", 5),
    CameraModel(4, "OPENCV", 8),
    CameraModel(5, "OPENCV_FISHEYE", 8),
    CameraModel(6, "FULL_OPENCV", 12),
    CameraModel(7, "FOV", 5),
    CameraModel(8, "SIMPLE_RADIAL_FISHEYE", 4),
    CameraModel(9, "RADIAL_FISHEYE", 5),
    CameraModel(10, "THIN_PRISM_FISHEYE", 12),
}
CAMERA_MODEL_IDS = {m.model_id: m for m in CAMERA_MODELS}


def _read_next_bytes(fid, num_bytes, fmt, endian="<"):
    data = fid.read(num_bytes)
    return struct.unpack(endian + fmt, data)


def qvec2rotmat(q):
    w, x, y, z = q
    return np.array([
        [1 - 2 * y * y - 2 * z * z, 2 * x * y - 2 * z * w, 2 * x * z + 2 * y * w],
        [2 * x * y + 2 * z * w, 1 - 2 * x * x - 2 * z * z, 2 * y * z - 2 * x * w],
        [2 * x * z - 2 * y * w, 2 * y * z + 2 * x * w, 1 - 2 * x * x - 2 * y * y],
    ])


def read_cameras_binary(path):
    cams = {}
    with open(path, "rb") as fid:
        n = _read_next_bytes(fid, 8, "Q")[0]
        for _ in range(n):
            props = _read_next_bytes(fid, 24, "iiQQ")
            cam_id, model_id, width, height = props
            model = CAMERA_MODEL_IDS[model_id]
            params = _read_next_bytes(fid, 8 * model.num_params,
                                      "d" * model.num_params)
            cams[cam_id] = dict(model=model.model_name, width=width,
                                height=height, params=np.array(params))
    return cams


def read_images_binary(path):
    imgs = {}
    with open(path, "rb") as fid:
        n = _read_next_bytes(fid, 8, "Q")[0]
        for _ in range(n):
            p = _read_next_bytes(fid, 64, "idddddddi")
            image_id = p[0]
            qvec = np.array(p[1:5])
            tvec = np.array(p[5:8])
            cam_id = p[8]
            name = ""
            ch = _read_next_bytes(fid, 1, "c")[0]
            while ch != b"\x00":
                name += ch.decode("utf-8")
                ch = _read_next_bytes(fid, 1, "c")[0]
            num_pts = _read_next_bytes(fid, 8, "Q")[0]
            # skip 2D points (x,y,point3D_id) triples
            fid.read(24 * num_pts)
            imgs[image_id] = dict(qvec=qvec, tvec=tvec, cam_id=cam_id, name=name)
    return imgs


def read_points3d_binary(path):
    xyz, rgb = [], []
    with open(path, "rb") as fid:
        n = _read_next_bytes(fid, 8, "Q")[0]
        for _ in range(n):
            p = _read_next_bytes(fid, 43, "QdddBBBd")
            xyz.append(p[1:4])
            rgb.append(p[4:7])
            track_len = _read_next_bytes(fid, 8, "Q")[0]
            fid.read(8 * track_len)
    return np.array(xyz, dtype=np.float64), np.array(rgb, dtype=np.float64) / 255.0


def _fovx_of(cam):
    m, params, W = cam["model"], cam["params"], cam["width"]
    if m in ("SIMPLE_PINHOLE", "SIMPLE_RADIAL", "RADIAL"):
        fx = params[0]
    elif m in ("PINHOLE", "OPENCV", "FULL_OPENCV"):
        fx = params[0]
    else:
        raise ValueError(f"unsupported COLMAP model for fovx: {m}")
    return 2.0 * np.arctan(W / (2.0 * fx))


def load_colmap(data_dir, downscale=1, images_subdir="images"):
    """Return (cams, pts_xyz, pts_rgb). cams: list[gs_io.Camera] in name order.

    data_dir must contain sparse/0/{cameras,images,points3D}.bin and images/.
    Real photos: white_bg composite is N/A (no alpha) -> plain RGB.
    """
    from PIL import Image
    sp = os.path.join(data_dir, "sparse", "0")
    cams_meta = read_cameras_binary(os.path.join(sp, "cameras.bin"))
    imgs_meta = read_images_binary(os.path.join(sp, "images.bin"))
    pts_xyz, pts_rgb = read_points3d_binary(os.path.join(sp, "points3D.bin"))

    cams = []
    for image_id in sorted(imgs_meta, key=lambda k: imgs_meta[k]["name"]):
        meta = imgs_meta[image_id]
        cam = cams_meta[meta["cam_id"]]
        R = qvec2rotmat(meta["qvec"])            # world->cam
        t = meta["tvec"].reshape(3, 1)
        w2c = np.eye(4)
        w2c[:3, :3] = R
        w2c[:3, 3:4] = t
        c2w_colmap = np.linalg.inv(w2c)
        c2w_gl = c2w_colmap.copy()
        c2w_gl[:3, 1:3] *= -1                    # COLMAP -> OpenGL (Camera flips back)
        fovx = _fovx_of(cam)

        img_path = os.path.join(data_dir, images_subdir, meta["name"])
        if not os.path.exists(img_path):
            continue
        im = Image.open(img_path).convert("RGB")
        if downscale > 1:
            im = im.resize((im.width // downscale, im.height // downscale),
                           Image.LANCZOS)
        arr = np.array(im, dtype=np.float32) / 255.0
        image = torch.from_numpy(arr).permute(2, 0, 1).contiguous()
        cams.append(Camera(c2w_gl, fovx, image, name=meta["name"]))
    return cams, pts_xyz, pts_rgb
