"""tier1/src/visibility.py — METHOD-PATH occlusion cull.
Uses ONLY the gaussian z-buffer from render.render_gbuffer. NO mesh, ever.

Visible iff z_P <= zbuf_3x3min(round(u), round(v)) + 0.02 * z_P.
"""
import numpy as np
import torch
import torch.nn.functional as F


def visible_mask(P, cam, depth, rel_tol=0.02):
    """P[M,3] world points; cam: common.Camera; depth: torch [H,W] gaussian z-buffer
    (inf where empty). Returns (vis[M] bool numpy, uv[M,2] numpy, z[M] numpy)."""
    H, Wd = cam.H, cam.W
    campts = (cam.w2c[:3, :3] @ P.T).T + cam.w2c[:3, 3]
    z = campts[:, 2]
    uv = (cam.K @ campts.T).T
    uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
    u = np.round(uv[:, 0]).astype(np.int64)
    v = np.round(uv[:, 1]).astype(np.int64)
    inb = (z > 0) & (u >= 0) & (u < Wd) & (v >= 0) & (v < H)

    # 3x3 min window on the z-buffer (avoids single-pixel dropout at depth steps)
    d = torch.nan_to_num(depth, posinf=1e9).float()[None, None]
    zmin = -F.max_pool2d(-d, 3, stride=1, padding=1)[0, 0]
    zmin_np = zmin.detach().cpu().numpy()

    vis = np.zeros(len(P), bool)
    idx = np.where(inb)[0]
    zb = zmin_np[v[idx], u[idx]]
    vis[idx] = z[idx] <= zb + rel_tol * z[idx]
    return vis, uv, z
