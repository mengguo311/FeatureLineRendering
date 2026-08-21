"""tier1/src/linelet.py — 3D LINELET representation + initialization (METHOD PATH).

HARD INVARIANT: gaussians + training RGBs + cameras only. This file must NEVER
import mesh_oracle or read the GT mesh.

A linelet is the M1b primitive that turns an M1a crease SEED (a bare 3D point, i.e.
a high-recall region proposal) into an orientable, renderable curve element:

    L_i = (p_i in R^3,  t_i in S^2 unit tangent,  l_i half-length)

with p_i initialised at the seed's gaussian centre p0_i. p0 is kept for the whole
optimisation because the M1b trust region (dt_pull.py, GUARD 1) is anchored on it:
the measured seed jitter radius is 5px, so a linelet that wants to move further than
that in any view is jumping to a DIFFERENT image feature, not correcting itself.

TANGENT INIT — local 3D PCA over neighbouring SEEDS, never C_N.
    The normal-structure-tensor C_N tangent is DEAD on vanilla 3DGS (measured in M1a:
    AUC 0.54 ~ chance, because a per-gaussian "normal" is the shortest covariance axis
    of a near-isotropic splat, which is noise). What does carry orientation is the
    SHAPE OF THE SEED CLOUD itself: seeds are a high-recall proposal that clusters
    along creases, so the first principal component of the seed positions inside a
    small ball is a usable crease direction. Anisotropy lam1/(lam1+lam2+lam3) is
    returned as a per-linelet confidence, so callers can freeze hopeless tangents.

LENGTH INIT — local splat scale: the median over the seed's kNN gaussians of that
gaussian's largest covariance axis exp(scale).max(). That is the radius at which the
3DGS reconstruction itself stops resolving detail, which is the natural scale for a
linelet: shorter carries no extra information, longer bridges across real structure.
"""
import numpy as np
from scipy.spatial import cKDTree

K_SCALE = 8            # kNN over gaussians used for the local splat scale
PCA_RADIUS_MULT = 3.0  # tangent PCA ball radius, in median-splat-scale units
MIN_PCA_NEIGH = 3      # fewer neighbours than this -> tangent is not trustworthy


def init_linelets(seed_pos, gauss_pos, gauss_scale, k_scale=K_SCALE,
                  pca_radius_mult=PCA_RADIUS_MULT, knn_graph=8):
    """Build the linelet set from M1a seeds. Mesh-free.

    seed_pos[S,3]    : seed gaussian centres (M1a OVERALL recipe, f=0.30)
    gauss_pos[N,3]   : ALL de-floatered gaussian centres (for the local splat scale)
    gauss_scale[N,3] : exp(scale) of those gaussians

    Returns dict:
      p0[S,3] float64  frozen seed position (trust-region anchor)
      p [S,3] float64  current position (== p0 at init)
      t [S,3] float64  unit tangent (local seed PCA, first principal component)
      l [S]   float64  half-length (local splat scale)
      aniso[S]         lam1/(lam1+lam2+lam3) of the seed-PCA, in [1/3,1] (confidence)
      n_pca[S]         number of seeds in the PCA ball (excluding self)
      t_valid[S] bool  enough neighbours for the PCA to mean anything
      knn[S,k] int64   seed-graph neighbours, used by the smoothness term
      splat[S]         the median local splat scale (also = l at init)
    """
    seed_pos = np.ascontiguousarray(seed_pos, np.float64)
    S = len(seed_pos)

    # ---- half-length: median largest-axis exp(scale) over the kNN gaussians -------
    gtree = cKDTree(gauss_pos)
    k = min(k_scale + 1, len(gauss_pos))
    _, gknn = gtree.query(seed_pos, k=k, workers=-1)
    smax = np.asarray(gauss_scale).max(1)
    splat = np.median(smax[gknn], axis=1)
    l = splat.copy()

    # ---- tangent: first principal component of the neighbouring SEED positions ----
    rad = pca_radius_mult * float(np.median(splat))
    stree = cKDTree(seed_pos)
    balls = stree.query_ball_point(seed_pos, r=rad, workers=-1)

    t = np.zeros((S, 3))
    aniso = np.zeros(S)
    n_pca = np.zeros(S, np.int64)
    for i, b in enumerate(balls):
        b = np.asarray(b)
        n_pca[i] = len(b) - 1                      # ball always contains self
        if len(b) < MIN_PCA_NEIGH + 1:
            continue
        Q = seed_pos[b] - seed_pos[b].mean(0)
        w, V = np.linalg.eigh(Q.T @ Q / len(b))
        t[i] = V[:, 2]
        s = w.sum()
        aniso[i] = w[2] / s if s > 1e-24 else 0.0

    t_valid = n_pca >= MIN_PCA_NEIGH
    # fallback for isolated seeds: point at the nearest seed (any direction beats 0)
    bad = ~t_valid | (np.linalg.norm(t, axis=1) < 1e-9)
    if bad.any():
        _, nb = stree.query(seed_pos[bad], k=min(2, S), workers=-1)
        nb = np.atleast_2d(nb)
        d = seed_pos[nb[:, -1]] - seed_pos[bad]
        n = np.linalg.norm(d, axis=1, keepdims=True)
        d = np.where(n > 1e-12, d / np.maximum(n, 1e-12), np.array([[1.0, 0.0, 0.0]]))
        t[bad] = d
        t_valid[bad] = False
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12

    kg = min(knn_graph + 1, S)
    _, knn = stree.query(seed_pos, k=kg, workers=-1)
    knn = np.atleast_2d(knn)[:, 1:]

    return {"p0": seed_pos.copy(), "p": seed_pos.copy(), "t": t, "l": l,
            "aniso": aniso, "n_pca": n_pca, "t_valid": t_valid,
            "knn": knn.astype(np.int64), "splat": splat}


def modulate_length(l, conf, thr=0.9, lo=0.25, hi=1.5):
    """Confidence-modulated half-length (measured: +0.059 segment precision at the same
    recall). A linelet is DRAWN, so its length is a precision/recall dial: a confident
    linelet should be extended to cover more of the crease, an unconfident one shortened
    towards a dot so it cannot spray pixels off the feature. `conf` is the mesh-free
    multi-view inlier ratio from linelet_prune.consensus_stats; the binary policy at
    thr=0.9 beat every smooth (linear/quadratic/cubic) mapping that was swept."""
    m = np.where(np.asarray(conf) >= thr, hi, lo)
    return np.asarray(l) * m


def endpoints(p, t, l):
    """(a,b) world-space endpoints of the linelets: p -+ l*t. Arrays [S,3]."""
    d = np.asarray(l)[:, None] * np.asarray(t)
    return np.asarray(p) - d, np.asarray(p) + d


def save(path, L):
    np.savez(path, **{k: v for k, v in L.items()})


def load(path):
    z = np.load(path)
    return {k: z[k] for k in z.files}
