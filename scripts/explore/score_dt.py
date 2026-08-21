"""score_dt.py -- family `dt`: multi-view photometric Canny-DT consistency.

MESH-FREE.  Uses only: gaussian centres/opacity/scale (h.X, h.g, h.keep), the
training RGB images (h.rgb_paths), the gaussian z-buffer from src/render.py and
src/visibility.py.  Nothing here imports mesh_oracle or reads the GT mesh.
(The `h` object is the eval-side Harness, but compute() touches only the
mesh-free attributes listed above -- never h.crease / h.evaluate.)

IDEA
    A real 3D feature line projects onto a photometric edge in essentially every
    view it is visible in; a spurious seed sitting in a smooth region does not.
    So: for every seed, aggregate the distance-transform value of its projection
    over all views where the gaussian z-buffer says it is visible, and score it
    with the negated robust aggregate.

WHAT MATTERS (measured on chair, see the report):
    The *edge density* of the detector dominates everything else.  The cached
    dt_field Canny(50,150) fires on ~12.5% of the chair's object pixels (velvet
    texture) -> the DT saturates near 0 everywhere and separates poorly
    (AUC 0.698).  Pre-blurring and raising the hysteresis until the density is
    ~2-5% of object pixels lifts AUC to ~0.85.  Inside that band the exact
    (sigma, tau) barely matters, so the default is the union of two scales.

    The choice of aggregate (mean / trimmed mean / median / fraction-below-tau /
    soft exponential kernel) moves AUC by <0.01.  Plain mean is used.

MEASURED (scene chair, canonical K=8 pool, 19304 seeds, views 0+25)
    AUC vs "within 2.5px of a GT crease in >=1 eval view" = 0.8607 (over the
    16100 eval-visible seeds; 0.8071 over all 19304).  Pareto:
        f=1.0 0.352/0.883   f=0.8 0.427/0.869   f=0.6 0.546/0.828
        f=0.5 0.621/0.796   f=0.4 0.698/0.722   f=0.3 0.764/0.576
        f=0.2 0.800/0.482
    Best gate point f=0.40 -> precision 0.698, recall 0.722.  DOES NOT PASS the
    80/70 gate on its own (recall passes, precision is ~10 pts short).
    compute() takes 2.1s for 25 views.

NEGATIVES, all measured, do not re-try them
    * edge-tangent alignment (projected e3 vs image edge orientation): AUC 0.505
    * 3D spatial smoothing of the score over kNN: AUC unchanged (0.848-0.852)
    * region-adaptive normalisation vs. neighbouring non-seed gaussians: AUC 0.57
    * excluding alpha-silhouette-driven edges: AUC 0.851 -> 0.815 (hurts)
    * view-dependent contrast (std/mean of grad-mag across views): AUC 0.404
    * fusing with any geometric feature available here (s_crease, s_corner,
      scale anisotropy, opacity): every combination LOWERS AUC.
    * TRANSFER: on lego this score is at chance (AUC 0.457-0.462); no edge
      density tested there beats 0.63.  The good chair density band was picked
      with the chair oracle and is scene-specific.
"""
import os
import sys

import cv2
import numpy as np
from scipy.ndimage import map_coordinates

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from src import render, visibility  # noqa: E402  (method-path modules only)

# (gaussian pre-blur sigma, Canny low, Canny high).  Union of these two scales.
# Both land in the ~2-5%-of-object-pixels edge-density band that works.
EDGE_CFGS = ((2.0, 100, 200), (2.5, 75, 150))
N_VIEWS = 25          # AUC saturates by ~12-25 views; see the view sweep.
_CACHE = {}


# ---------------------------------------------------------------- edge maps
def edge_map(rgb_path, cfgs=EDGE_CFGS):
    """Union of blurred-Canny edge maps for one training image. Returns bool [H,W]."""
    im = cv2.imread(rgb_path, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(rgb_path)
    if im.ndim == 3 and im.shape[2] == 4:                      # composite over white
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        bgr = (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    else:
        bgr = im[:, :, :3]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    e = np.zeros(gray.shape, np.uint8)
    for sig, lo, hi in cfgs:
        g = cv2.GaussianBlur(gray, (0, 0), sig) if sig > 0 else gray
        e |= cv2.Canny(g, lo, hi)
    return e > 0


def _depth(h, v):
    """Gaussian z-buffer for view v (reuses h.gbufs when present). No mesh."""
    if getattr(h, "gbufs", None) and v in h.gbufs:
        return h.gbufs[v]["depth"]
    import time

    import torch
    for _ in range(30):                     # GPU is shared; back off on OOM
        try:
            gb = render.render_gbuffer(h.g, h.keep, h.cams[v])
            d = gb["depth"]
            del gb
            torch.cuda.empty_cache()
            return d
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            time.sleep(2.0)
    return render.render_gbuffer(h.g, h.keep, h.cams[v], device="cpu")["depth"]


def view_indices(n_total, n_views):
    return np.unique(np.round(np.linspace(0, n_total - 1, min(n_views, n_total))).astype(int))


def gather(h, sel, n_views=N_VIEWS, cfgs=EDGE_CFGS):
    """Per-seed / per-view DT sampling.

    Returns (dt[M,V] float32, vis[M,V] bool, views[V]).  dt is the bilinearly
    sampled distance (px) from the seed's projection to the nearest edge pixel;
    entries where the seed is not visible / out of frame are 0 and masked by vis.
    """
    key = (id(h), tuple(sel[:8]), len(sel), n_views, cfgs)
    if key in _CACHE:
        return _CACHE[key]
    P = np.asarray(h.X)[sel]
    views = view_indices(len(h.cams), n_views)
    dt = np.zeros((len(P), len(views)), np.float32)
    vis = np.zeros((len(P), len(views)), bool)
    for j, v in enumerate(views):
        vm, uv, _ = visibility.visible_mask(P, h.cams[v], _depth(h, v))
        u = np.round(uv[:, 0]).astype(np.int64)
        w = np.round(uv[:, 1]).astype(np.int64)
        ok = vm & (u >= 0) & (u < 800) & (w >= 0) & (w < 800)
        d = cv2.distanceTransform((~edge_map(h.rgb_paths[v], cfgs)).astype(np.uint8),
                                  cv2.DIST_L2, 5)
        dt[ok, j] = map_coordinates(d, [uv[ok, 1], uv[ok, 0]], order=1, mode="nearest")
        vis[:, j] = ok
    _CACHE[key] = (dt, vis, views)
    return dt, vis, views


# ---------------------------------------------------------------- scores
def _wmean(dt, vis):
    w = vis.astype(np.float32)
    return (dt * w).sum(1) / np.maximum(w.sum(1), 1.0)


def compute(h, sel, st, n_views=N_VIEWS):
    """Best single score: negated mean DT over the views where the seed is visible.
    Higher = more likely a true crease seed.  Mesh-free."""
    dt, vis, _ = gather(h, sel, n_views)
    s = -_wmean(dt, vis)
    s[vis.sum(1) == 0] = -1e18          # never seen -> no photometric evidence
    return s.astype(np.float64)


def compute_trimmed(h, sel, st, n_views=N_VIEWS, lo=10, hi=90):
    """Negated 10-90% trimmed mean DT.  Marginally better AUC, slightly better recall."""
    dt, vis, _ = gather(h, sel, n_views)
    A = np.where(vis, dt, np.nan)
    with np.errstate(all="ignore"):
        qlo = np.nanpercentile(A, lo, axis=1, keepdims=True)
        qhi = np.nanpercentile(A, hi, axis=1, keepdims=True)
        s = -np.nanmean(np.where((A >= qlo) & (A <= qhi), A, np.nan), 1)
    return np.nan_to_num(s, nan=-1e18)


def compute_median(h, sel, st, n_views=N_VIEWS):
    """Negated median DT over visible views."""
    dt, vis, _ = gather(h, sel, n_views)
    with np.errstate(all="ignore"):
        s = -np.nanmedian(np.where(vis, dt, np.nan), 1)
    return np.nan_to_num(s, nan=-1e18)


def compute_frac(h, sel, st, tau=8.0, n_views=N_VIEWS):
    """Fraction of visible views whose DT <= tau.  Equivalent power to the mean."""
    dt, vis, _ = gather(h, sel, n_views)
    return (vis & (dt <= tau)).sum(1) / np.maximum(vis.sum(1), 1)


def compute_soft(h, sel, st, tau=8.0, n_views=N_VIEWS):
    """Mean over visible views of exp(-DT/tau): soft edge-support."""
    dt, vis, _ = gather(h, sel, n_views)
    return _wmean(-np.exp(-dt / tau), vis) * -1.0


def advisory_median_dt(h, sel, n_views=N_VIEWS):
    """The M1a spec's advisory metric, on the ORIGINAL cached Canny(50,150) DT:
    median over seeds of the per-seed median distance to the nearest 2D edge."""
    from src import dt_field
    DT = dt_field.build_dt_cache("chair" if "chair" in h.rgb_paths[0] else h.scene,
                                 h.rgb_paths)["dt"]
    P = np.asarray(h.X)[sel]
    views = view_indices(len(h.cams), n_views)
    vals = np.full((len(P), len(views)), np.nan, np.float32)
    for j, v in enumerate(views):
        vm, uv, _ = visibility.visible_mask(P, h.cams[v], _depth(h, v))
        u = np.round(uv[:, 0]).astype(np.int64)
        w = np.round(uv[:, 1]).astype(np.int64)
        ok = vm & (u >= 0) & (u < 800) & (w >= 0) & (w < 800)
        vals[ok, j] = DT[v].astype(np.float32)[w[ok], u[ok]]
    with np.errstate(all="ignore"):
        return float(np.nanmedian(np.nanmedian(vals, 1)))


if __name__ == "__main__":
    import time
    sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
    from tune_lib import Harness, structure_tensor, nms_along_e1
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    P = h.X[sel]
    t1 = time.time()
    s = compute(h, sel, st)
    print("compute(): %.1fs for %d seeds, %d views" % (time.time() - t1, len(sel), N_VIEWS))
    order = np.argsort(-s)
    print("f     prec   rec    n_vis")
    for f in [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]:
        k = np.zeros(len(sel), bool)
        k[order[:int(f * len(sel))]] = True
        p, r, n = h.evaluate(P, extra_mask=k)
        print("%.1f  %.3f  %.3f  %d" % (f, p, r, n))
    print("advisory median-of-median DT (cached Canny 50/150): %.3f px"
          % advisory_median_dt(h, sel))
    print("total %.1fs" % (time.time() - t0))
