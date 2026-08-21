"""tier1/src/dt_field.py — multi-view 2D edge + distance-transform cache.
METHOD PATH: consumes only the train RGBs. NO mesh.

Per view: composite RGBA over white -> gray -> Canny(50,150) ->
cv2.distanceTransform on the edge complement (DIST_L2, 5) + Sobel grads of the DT
(for later autograd-based DT pull). Cached to disk as float16 .npz per scene.
"""
import os
import cv2
import numpy as np

CACHE_DIR = os.path.expanduser("~/3dgs_line/tier1/cache")


def _edge_dt(img_path, tau_low=50, tau_high=150, scales=None):
    """Canny edge distance transform for one view.

    `scales` optionally overrides the single (blur_sigma, tau_low, tau_high) detector
    with a list of them, whose edge maps are unioned. This matters: the spec default
    Canny(50,150) fires on ~12.5% of the chair's object pixels (the velvet upholstery
    texture saturates the DT to ~0 everywhere). Blurring first and raising the
    hysteresis until the edge density is ~2-5% of object pixels makes the DT a far
    better feature-line prior; inside that band the exact values barely matter.
    """
    im = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(img_path)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        rgb = im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)  # over white
        rgb = rgb.astype(np.uint8)
    else:
        rgb = im[:, :, :3] if im.ndim == 3 else cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
    if scales is None:
        edge = cv2.Canny(gray, tau_low, tau_high)
    else:
        edge = np.zeros_like(gray)
        for sigma, lo, hi in scales:
            g = cv2.GaussianBlur(gray, (0, 0), sigma) if sigma > 0 else gray
            edge = np.maximum(edge, cv2.Canny(g, lo, hi))
    dt = cv2.distanceTransform((edge == 0).astype(np.uint8), cv2.DIST_L2, 5)
    gx = cv2.Sobel(dt, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(dt, cv2.CV_32F, 0, 1, ksize=3)
    return dt, np.stack([gx, gy], 0)


# sparser two-scale detector: use for feature-line evidence, not for the spec baseline
SPARSE_SCALES = [(2.0, 100, 200), (2.5, 75, 150)]


def build_dt_cache(scene, rgb_paths, force=False, cache_dir=CACHE_DIR,
                   scales=None, tag=""):
    """Build (or load) the DT cache for all views of a scene.
    Returns dict {"dt": [V,H,W] float16, "grad": [V,2,H,W] float16}.
    Pass scales=SPARSE_SCALES (with a distinct tag) for the sparse-edge variant."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"dt_{scene}{tag}.npz")
    if os.path.exists(path) and not force:
        z = np.load(path)
        return {"dt": z["dt"], "grad": z["grad"]}
    dts, grads = [], []
    for p in rgb_paths:
        dt, g = _edge_dt(p, scales=scales)
        dts.append(dt.astype(np.float16))
        grads.append(g.astype(np.float16))
    out = {"dt": np.stack(dts), "grad": np.stack(grads)}
    np.savez(path, **out)
    return out
