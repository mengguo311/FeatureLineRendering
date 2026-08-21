"""tier1/src/lines_image.py — image-space line BASELINE (flicker control condition).
METHOD PATH: consumes only the gaussian G-buffer. NO mesh.

I_depth  : Sobel gradient magnitude of normalized inverse depth > tau_d
I_normal : ||Laplacian(N)|| ridge (normal crease) > tau_n
I_line   = (I_depth OR I_normal) AND (alpha > 0.5)
"""
import cv2
import numpy as np
import torch


def extract_lines(gbuf, tau_d=0.20, tau_n=1.0):
    """gbuf: dict from render.render_gbuffer. Returns bool [H,W] numpy."""
    depth = gbuf["depth"].detach().cpu().numpy().astype(np.float32)
    normal = gbuf["normal"].detach().cpu().numpy().astype(np.float32)
    alpha = gbuf["alpha"].detach().cpu().numpy().astype(np.float32)

    fg = alpha > 0.5
    inv = np.zeros_like(depth)
    finite = np.isfinite(depth) & (depth > 1e-6)
    inv[finite] = 1.0 / depth[finite]
    # normalize inverse depth to [0,1] over the foreground (robust to outliers)
    if fg.any():
        lo, hi = np.percentile(inv[fg], [1, 99])
        inv = np.clip((inv - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    gx = cv2.Sobel(inv, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(inv, cv2.CV_32F, 0, 1, ksize=3)
    gmag = np.sqrt(gx * gx + gy * gy)
    I_depth = gmag > tau_d

    lap = np.stack([cv2.Laplacian(normal[..., c], cv2.CV_32F, ksize=3)
                    for c in range(3)], -1)
    kappa = np.linalg.norm(lap, axis=-1)
    I_normal = kappa > tau_n

    return (I_depth | I_normal) & fg
