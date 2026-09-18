"""2DGS G-buffer renderer — the Plan #1 geometric foundation.

*** METHOD-SIDE MODULE. No mesh, no trimesh, no mesh_oracle import. ***

Renders depth / normal / alpha from a trained 2DGS (hbb1/2d-gaussian-splatting) model at
an arbitrary tier1 `common.Camera`, and returns them in EXACTLY the same convention as
`src/render.render_gbuffer` so the two can be swapped under an identical measurement.

TWO CONVENTION BRIDGES ARE NEEDED (both verified in scripts/explore/check_2dgs_align.py):

1. CAMERA MATRICES.  tier1 stores an OpenCV world->cam `w2c` [4,4]; 3DGS/2DGS store the
   TRANSPOSE (row-vector convention) as `world_view_transform`, and a separate OpenGL-style
   `projection_matrix`.  tier1's K has fx==fy and the principal point hard-wired to
   (W/2, H/2), which is exactly the pinhole `getProjectionMatrix` assumes, so
       FoVx = 2*atan(W / (2f)),  FoVy = 2*atan(H / (2f))
   is a loss-free description of tier1's K.

2. THE HALF-PIXEL SHIFT.  The two codebases disagree about which continuous image
   coordinate an integer pixel index denotes:
       tier1   (common.project):  u_t = f*X/Z + W/2                -> index i sits at u_t = i
       3DGS    (rasterizer):      u_g = ((x_ndc + 1)*W - 1) * 0.5  -> index j sits at u_t = j + 0.5
   so u_g = u_t - 0.5.  A buffer produced by the 2DGS rasterizer must therefore be resampled
   at (i - 0.5, j - 0.5) to be read with tier1 integer pixel coordinates.  Half a pixel is
   NOT negligible here: the bilateral ribbon samples at +-2..4 px, so an uncorrected buffer
   biases the two ribbon sides asymmetrically.  Set `half_pixel=False` to disable and measure
   the effect.

DEPTH SEMANTICS.  2DGS `surf_depth` is camera-axis z (see ext/2dgs/utils/point_utils.py:
`points = depthmap * rays_d` with rays_d having camera-space z == 1), matching
`render.render_gbuffer`'s `depth` (`common.project` returns campts[:,2]).  Both are z, not
ray distance, which is what makes the inverse-depth plane fit in the ribbon exact.
Empty pixels are returned as +inf, again matching render.py.

`depth_ratio` selects the 2DGS depth flavour: 1.0 = median depth (bounded objects, sharp at
creases), 0.0 = expected/mean depth.  It must match what the model was TRAINED with, which
is recorded in <model_path>/cfg_args and is read automatically by `load_2dgs`.
"""
import os
import sys
import math

import numpy as np
import torch

EXT2DGS = os.path.expanduser("~/3dgs_line/ext/2dgs")


def _ensure_path():
    if EXT2DGS not in sys.path:
        sys.path.insert(0, EXT2DGS)


class _Pipe:
    """Stand-in for 2DGS PipelineParams (only these three fields are read by render())."""

    def __init__(self, depth_ratio=1.0):
        self.convert_SHs_python = False
        self.compute_cov3D_python = False
        self.debug = False
        self.depth_ratio = float(depth_ratio)


class _Cam2DGS:
    """MiniCam-compatible view built from a tier1 `common.Camera`."""

    def __init__(self, cam, znear=0.01, zfar=100.0):
        _ensure_path()
        from utils.graphics_utils import getProjectionMatrix

        self.image_width = int(cam.W)
        self.image_height = int(cam.H)
        f = float(cam.f)
        self.FoVx = 2.0 * math.atan(cam.W / (2.0 * f))
        self.FoVy = 2.0 * math.atan(cam.H / (2.0 * f))
        self.znear, self.zfar = znear, zfar

        w2c = np.asarray(cam.w2c, np.float64)
        self.world_view_transform = torch.tensor(w2c, dtype=torch.float32).transpose(0, 1).cuda()
        self.projection_matrix = getProjectionMatrix(
            znear=znear, zfar=zfar, fovX=self.FoVx, fovY=self.FoVy
        ).transpose(0, 1).cuda()
        self.full_proj_transform = (
            self.world_view_transform.unsqueeze(0).bmm(self.projection_matrix.unsqueeze(0))
        ).squeeze(0)
        self.camera_center = self.world_view_transform.inverse()[3, :3]


def _read_cfg_args(model_path):
    """Recover the training config (we need white_background / depth_ratio) from cfg_args."""
    p = os.path.join(model_path, "cfg_args")
    if not os.path.exists(p):
        return {}
    from argparse import Namespace  # noqa: F401  (cfg_args is a Namespace repr)
    ns = eval(open(p).read())
    return vars(ns)


def load_2dgs(model_path, iteration=None, sh_degree=3):
    """Load a trained 2DGS model. Returns (gaussians, pipe, meta)."""
    _ensure_path()
    from scene.gaussian_model import GaussianModel

    pc_root = os.path.join(model_path, "point_cloud")
    if iteration is None:
        its = [int(d.split("_")[-1]) for d in os.listdir(pc_root) if d.startswith("iteration_")]
        iteration = max(its)
    ply = os.path.join(pc_root, f"iteration_{iteration}", "point_cloud.ply")
    g = GaussianModel(sh_degree)
    g.load_ply(ply)

    cfg = _read_cfg_args(model_path)
    pipe = _Pipe(depth_ratio=cfg.get("depth_ratio", 1.0))
    meta = {
        "model_path": model_path,
        "iteration": int(iteration),
        "ply": ply,
        "n_gauss": int(g.get_xyz.shape[0]),
        "depth_ratio": pipe.depth_ratio,
        "white_background": bool(cfg.get("white_background", True)),
        "lambda_normal": cfg.get("lambda_normal", None),
        "lambda_dist": cfg.get("lambda_dist", None),
    }
    return g, pipe, meta


def _shift_half_pixel(t):
    """Resample a [H,W] or [H,W,C] tensor from 3DGS pixel indices to tier1 pixel indices.

    tier1 index i corresponds to 3DGS continuous coordinate i-0.5, so we sample the 3DGS
    buffer at (i-0.5, j-0.5). grid_sample with align_corners=True maps normalized -1..1 to
    3DGS indices 0..W-1, hence x_norm = 2*(i-0.5)/(W-1) - 1.
    """
    squeeze = t.dim() == 2
    if squeeze:
        t = t[..., None]
    H, W, C = t.shape
    ii = torch.arange(W, device=t.device, dtype=torch.float32) - 0.5
    jj = torch.arange(H, device=t.device, dtype=torch.float32) - 0.5
    gx = (2.0 * ii / (W - 1) - 1.0).view(1, 1, W).expand(1, H, W)
    gy = (2.0 * jj / (H - 1) - 1.0).view(1, H, 1).expand(1, H, W)
    grid = torch.stack([gx, gy], dim=-1)                       # [1,H,W,2]
    src = t.permute(2, 0, 1)[None].contiguous()                # [1,C,H,W]
    out = torch.nn.functional.grid_sample(
        src, grid, mode="bilinear", padding_mode="border", align_corners=True
    )[0].permute(1, 2, 0)
    return out[..., 0] if squeeze else out


@torch.no_grad()
def render_gbuffer_2dgs(gaussians, pipe, cam, bg_white=True, half_pixel=True,
                        alpha_eps=1e-6, with_rgb=False):
    """2DGS G-buffer at a tier1 camera, in tier1 convention.

    Returns dict with the same keys/semantics as render.render_gbuffer:
        depth  [H,W] float32  camera-axis z, +inf where nothing was hit
        normal [H,W,3]        world-space, alpha-composited, renormalised, flipped
                              toward the camera (render.py:45 does the same)
        alpha  [H,W]
      plus 2DGS-specific extras:
        surf_normal [H,W,3]   the depth-derived pseudo-normal 2DGS regularises against
        dist   [H,W]          the depth-distortion map
        rgb    [H,W,3]        only when with_rgb=True
    """
    _ensure_path()
    from gaussian_renderer import render as gs_render

    bg = torch.tensor([1.0, 1.0, 1.0] if bg_white else [0.0, 0.0, 0.0],
                      dtype=torch.float32, device="cuda")
    v = _Cam2DGS(cam)
    pkg = gs_render(v, gaussians, pipe, bg)

    alpha = pkg["rend_alpha"][0]                                # [H,W]
    depth = pkg["surf_depth"][0]                                # [H,W] camera-axis z
    normal = pkg["rend_normal"].permute(1, 2, 0)                # [H,W,3] world space
    snormal = pkg["surf_normal"].permute(1, 2, 0)
    dist = pkg["rend_dist"][0]
    rgb = pkg["render"].permute(1, 2, 0) if with_rgb else None

    if half_pixel:
        alpha = _shift_half_pixel(alpha)
        depth = _shift_half_pixel(depth)
        normal = _shift_half_pixel(normal)
        snormal = _shift_half_pixel(snormal)
        dist = _shift_half_pixel(dist)
        if rgb is not None:
            rgb = _shift_half_pixel(rgb)

    # 2DGS returns depth 0 where nothing was hit; render.py's contract is +inf.
    empty = (alpha <= alpha_eps) | ~torch.isfinite(depth) | (depth <= 1e-6)
    depth = torch.where(empty, torch.full_like(depth, float("inf")), depth)

    # rend_normal is alpha-weighted (unnormalised); renormalise and orient toward the camera,
    # matching render.render_gbuffer (render.py:45,143-144).
    n = normal / normal.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    cc = torch.as_tensor(np.asarray(cam.center, np.float32), device=n.device)
    # view ray direction per pixel is not needed to fix the sign: the camera looks down +z in
    # camera space, so a normal pointing away from the camera has positive dot with the
    # camera-space view direction. Do the test in camera space.
    R = torch.as_tensor(np.asarray(cam.w2c[:3, :3], np.float32), device=n.device)
    n_cam = n @ R.T                                             # world -> camera
    flip = (n_cam[..., 2] > 0)[..., None]
    n = torch.where(flip, -n, n)
    _ = cc

    out = {"depth": depth.float(), "normal": n.float(), "alpha": alpha.float(),
           "surf_normal": snormal.float(), "dist": dist.float()}
    if rgb is not None:
        out["rgb"] = rgb.float()
    return out
