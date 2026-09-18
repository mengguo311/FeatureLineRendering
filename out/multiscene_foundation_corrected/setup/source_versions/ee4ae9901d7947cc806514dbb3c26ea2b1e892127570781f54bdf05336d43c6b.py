"""tier1/src/linelet_prune.py — multi-view consensus pruning (METHOD PATH, mesh-free).

HARD INVARIANT: this file sees only DT residuals + the gaussian-z-buffer visibility
produced by dt_pull.py. It never imports mesh_oracle.

WHY A CONSENSUS TEST IS THE RIGHT SILHOUETTE KILLER
    After the pull, every linelet sits on SOME image edge. Three things produce image
    edges: (a) a real static 3D crease, (b) a texture edge painted on the surface, and
    (c) an OCCLUDING CONTOUR (silhouette), which is view-dependent — it slides across
    the surface as the camera moves. (a) and (b) are fixed to the object, so a single
    3D point can satisfy them from every viewpoint. (c) cannot: a linelet parked on the
    silhouette of view k projects into the interior of view k' and its DT residual there
    blows up. So "fraction of visible views in which the projection is still within
    tau_in px of an edge" separates static 3D structure from view-dependent contours,
    and it does so WITHOUT any mesh.

    A linelet whose seed was a genuine false positive (>5px from any real structure) is
    caught by the same test: the trust region forbids it from reaching a real feature,
    so it ends up on nothing and its inlier ratio collapses.

WHAT WAS MEASURED, AND WHERE THE SPEC RULE FALLS SHORT (chair, f=0.30, 50 statistics
scored by AUC against "ended within 1.5px of a GT crease"):
  * The spec rule (centre residual, tau_in=1.5, prune below 0.50) keeps 95.4% of
    linelets: it barely prunes, because on a texture-rich object almost every linelet
    lands on SOME edge in most views. Its statistic saturates at P@1.5 < 0.79 no matter
    how hard the threshold is driven.
  * Three changes, each measured, make the ranking strictly better at every keep
    fraction: use the 3-POINT residual (resid3, whole segment on the feature) instead of
    the centre alone; loosen tau_in to 2.0; and SMOOTH the ratio over the seed-graph kNN
    (worth +0.033 AUC alone) — a real crease is a contiguous curve, so its neighbours
    agree, while a linelet that found a lone texture edge is isolated.
  * Even so, no mesh-free statistic exceeds AUC ~0.70. That is the honest limit: an
    ORACLE prune ranked by true GT distance reaches P@1.5=0.856 / R@1.5=0.770 on the
    segment protocol at keep=0.44, so the information IS present in the pulled set — but
    it is not recoverable from the DT residual alone. Do not read the quantile dial as a
    tuned method: it is a frontier control, and the frontier it walks is reported.
  * Measured NON-signals, do not add them back: the rendered crease-ridge evidence at the
    final position (AUC <=0.563 — M1a already spent it during seeding), the projected
    tangent/edge agreement (AUC 0.44, anti-correlated), and silhouette proximity
    (AUC 0.37/0.42, ANTI-predictive — view-dependent contours are NOT what is failing).
"""
import warnings

import numpy as np


def consensus_stats(resid, vis, tau_in=1.5):
    """resid[V,S] DT (px) at the projected linelet, vis[V,S] bool.
    Returns dict(inlier_ratio[S], median_resid[S], n_vis[S])."""
    vis = np.asarray(vis, bool)
    resid = np.asarray(resid, np.float32)
    nv = vis.sum(0)
    inl = ((resid <= tau_in) & vis).sum(0) / np.maximum(nv, 1)
    r = np.where(vis, resid, np.nan)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)   # all-NaN = never visible
        med = np.nanmedian(r, axis=0)
    med = np.nan_to_num(med, nan=1e9)
    return {"inlier_ratio": inl.astype(np.float64),
            "median_resid": med.astype(np.float64),
            "n_vis": nv.astype(np.int64)}


def rank01(v):
    r = np.empty(len(v), np.float64)
    r[np.argsort(np.asarray(v), kind="stable")] = np.arange(len(v))
    return r / max(len(v) - 1, 1)


def consensus_statistic(resid3, vis, knn=None, tau_in=2.0, splat=None, w_splat=0.0):
    """The measured-best mesh-free ranking of linelet quality (see module docstring).

    3-point inlier ratio at tau_in, averaged with its seed-graph kNN neighbours. If
    w_splat>0 the (chair-specific, see below) local splat scale is blended in: smaller
    local gaussians predicted post-pull correctness better than the entire M1a score
    (AUC 0.669 vs 0.577), but it is a SEED-INTRINSIC property rather than a measure of
    how the pull went, so it is OFF by default and must be justified per scene."""
    vis = np.asarray(vis, bool)
    nv = np.maximum(vis.sum(0), 1)
    inl = ((np.asarray(resid3, np.float32) <= tau_in) & vis).sum(0) / nv
    if knn is not None:
        inl = 0.5 * inl + 0.5 * inl[np.asarray(knn)].mean(1)
    if w_splat > 0 and splat is not None:
        return (1.0 - w_splat) * rank01(inl) + w_splat * rank01(-np.asarray(splat))
    return inl


def consensus_prune(resid, vis, tau_in=1.5, min_ratio=0.50, max_med=1.5,
                    min_views=3, resid3=None, use_resid3=False,
                    keep_frac=None, stat=None):
    """Returns (keep[S] bool, stats dict).

    Prune if  (i) seen from fewer than min_views views (nothing to agree on),
             (ii) inlier ratio < min_ratio  — the spec's 0.50; true static creases
                  reach >=0.8 multi-view consensus, silhouettes do not, or
            (iii) post-optimisation median residual > max_med px.
    use_resid3 scores the 3-POINT segment mean instead of the centre alone, i.e. it
    demands the whole linelet — not just its midpoint — be on the feature.

    keep_frac (optional) additionally keeps only the top fraction of `stat` (default:
    consensus_statistic). This is the frontier dial: the fixed 0.50 threshold above is
    the spec's rule and is reported as such, while keep_frac walks the measured
    precision/recall frontier."""
    r = np.asarray(resid3 if (use_resid3 and resid3 is not None) else resid, np.float32)
    st = consensus_stats(r, vis, tau_in=tau_in)
    keep = ((st["n_vis"] >= min_views) & (st["inlier_ratio"] >= min_ratio) &
            (st["median_resid"] <= max_med))
    if keep_frac is not None and 0 < keep_frac < 1:
        v = np.asarray(stat) if stat is not None else consensus_statistic(
            resid3 if resid3 is not None else resid, vis)
        keep = keep & (v >= np.quantile(v, 1.0 - keep_frac))
        st["stat"] = v
    st["keep"] = keep
    return keep, st
