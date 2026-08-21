"""score_geom.py -- family `geom`: per-gaussian GEOMETRIC / SALIENCY seed scores.

MESH-FREE by construction: every quantity below is a function of the gaussian
parameters only (centers mu, per-gaussian normals n, scales, opacity) plus the
C_N structure tensor `st`.  No mesh, no images, no rendering, no G-buffer.

Headline empirical findings on chair (see the report / explore_geom*.py):
  * The stated "near-isotropic gaussians have arbitrary normals -> false seeds"
    hypothesis is REFUTED, and in fact runs BACKWARDS: near-crease seeds sit on
    LESS flat gaussians than false seeds (flat_mid_min AUC 0.469, flat_max_min
    0.415).  The useful direction of that axis is therefore `-flatness`.
  * The raw C_N crease saliency itself is nearly uninformative for ranking
    (s_crease AUC 0.551) -- the raw 3DGS normals are noise-dominated.
    Recomputing the normal field from local position-PCA lifts the normal-based
    signal to AUC 0.71 (`compute_dihedral`).
  * The strongest single geometric quantities are RECONSTRUCTION-DENSITY proxies,
    not crease geometry: seed density (AUC 0.760) and neighbourhood mean opacity
    (0.748).
  * Best combination reaches AUC 0.806-0.823 -> precision 0.570 at recall 0.715
    (f=0.45).  The gate (0.80 / 0.70) is NOT reachable from this family alone.

compute() returns the best single score (highest precision at recall >= 0.70).
"""
import numpy as np
from scipy.spatial import cKDTree

__all__ = ["compute", "compute_auc_best", "compute_dihedral", "compute_seed_density",
           "compute_nb_opacity", "compute_flatness"]

# ---------------------------------------------------------------- primitives


def _rank01(x):
    """rank-normalise to (0,1); ties broken arbitrarily but stably."""
    return (np.argsort(np.argsort(x, kind="mergesort"), kind="mergesort") + 0.5) / len(x)


def _knn(X, k):
    d, i = cKDTree(X).query(X, k=k + 1)
    return d[:, 1:], i[:, 1:]


def _pca_normals(X, knn_idx):
    """Local position-PCA normal (smallest eigenvector of the kNN scatter)."""
    k = knn_idx.shape[1]
    Q = X[knn_idx] - X[knn_idx].mean(1, keepdims=True)
    C = np.einsum("nkc,nkd->ncd", Q, Q) / k
    _, V = np.linalg.eigh(C)
    return V[:, :, 0]


# ---------------------------------------------------------------- features


def _nb_opacity(h, st):
    """mean opacity of the C_N kNN (k=8). AUC_vis 0.748 on chair."""
    return h.opa[st["knn"]].mean(1)


def _density(h, k=8):
    """-mean kNN distance (higher = denser reconstruction). AUC_vis 0.695."""
    d, _ = _knn(h.X, k)
    return -d.mean(1)


def _nb_flatness(h, st):
    """mean over the C_N kNN of log(scale_mid/scale_min) = normal-definedness.
    NOTE the sign used downstream is NEGATIVE: flatter neighbourhoods are LESS
    likely to be creases (the assigned hypothesis is inverted). AUC_vis 0.424."""
    ss = np.sort(h.scale, axis=1)
    lf = np.log((ss[:, 1] + 1e-12) / (ss[:, 0] + 1e-12))
    return lf[st["knn"]].mean(1)


def _p90_angle_pca(h, kp=20, pct=10):
    """Robust local dihedral estimate on a DENOISED normal field: build normals by
    local position-PCA over kNN(kp), then take the 10th-percentile cosine between
    the centre normal and its neighbours -> degrees. AUC_vis 0.716."""
    _, idx = _knn(h.X, kp)
    nn = _pca_normals(h.X, idx)
    s = np.sign((nn * h.N).sum(1))
    s[s == 0] = 1.0
    nn = nn * s[:, None]                       # consistent sign vs the gaussian normal
    nj = nn[idx]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, nn))
    sg[sg == 0] = 1.0
    cs = np.einsum("nkc,nc->nk", nj * sg[..., None], nn)
    return np.degrees(np.arccos(np.clip(np.percentile(cs, pct, axis=1), -1.0, 1.0)))


def _seed_density(h, sel, k=24):
    """-mean distance to the k nearest OTHER SEEDS. Best single geom feature,
    AUC_vis 0.760, but its Pareto is poor (it is spatially clustered, so it
    deletes whole crease regions and recall collapses)."""
    P = h.X[sel]
    d, _ = cKDTree(P).query(P, k=k + 1)
    return -d[:, 1:].mean(1)


def _pos_thickness(h, k=16):
    """local position-PCA thickness l3/(l1+l2+l3): creases bend the patch.
    AUC_vis 0.658."""
    _, idx = _knn(h.X, k)
    Q = h.X[idx] - h.X[:, None, :]
    C = np.einsum("nkc,nkd->ncd", Q, Q) / k
    w, _ = np.linalg.eigh(C)
    return w[:, 0] / (w.sum(1) + 1e-16)


def _curv(h, kp=20):
    """RMS deviation from the local PCA tangent plane, normalised by spacing."""
    d, idx = _knn(h.X, kp)
    nn = _pca_normals(h.X, idx)
    r = np.einsum("nkc,nc->nk", h.X[idx] - h.X[:, None, :], nn)
    return np.sqrt((r ** 2).mean(1)) / (d.mean(1) + 1e-12)


# ---------------------------------------------------------------- scores


def compute(h, sel, st):
    """BEST geom score: equal-weight sum of 5 rank-normalised quantities.
    Selected as the subset (of 12 candidates, sizes 1..5) maximising precision
    subject to recall >= 0.70 on chair views 0/25 -- so the chair numbers carry
    a mild oracle-selection optimism (~+0.02 precision over the AUC-greedy pick).

    chair: AUC_vis 0.806; f=0.45 -> precision 0.570 / recall 0.715.
    """
    sc = (_rank01(_nb_opacity(h, st)[sel])
          + _rank01(_p90_angle_pca(h)[sel])
          + _rank01(_density(h)[sel])
          + _rank01(-_nb_flatness(h, st)[sel])     # NB: negative (hypothesis inverted)
          + _rank01(h.opa[sel]))
    return sc.astype(np.float64)


def compute_auc_best(h, sel, st):
    """Variant selected greedily for AUC rather than for the gate.
    chair: AUC_vis 0.823; f=0.50 -> 0.551 / 0.714, f=0.30 -> 0.629 / 0.553."""
    sc = (_rank01(_seed_density(h, sel))
          + _rank01(_nb_opacity(h, st)[sel])
          + _rank01(_p90_angle_pca(h)[sel])
          + _rank01(_density(h)[sel])
          + _rank01(_curv(h)[sel])
          + _rank01(-_nb_flatness(h, st)[sel])
          + _rank01(h.opa[sel]))
    return sc.astype(np.float64)


def compute_dihedral(h, sel, st):
    """Pure geometry, no density/opacity: robust dihedral on a denoised
    (position-PCA) normal field. chair AUC_vis 0.716 -- this is the honest
    ceiling of the *normal-structure* part of the family."""
    return _p90_angle_pca(h)[sel].astype(np.float64)


def compute_seed_density(h, sel, st):
    """Best SINGLE geom feature by AUC (0.760) but a bad Pareto."""
    return _seed_density(h, sel).astype(np.float64)


def compute_nb_opacity(h, sel, st):
    """Neighbourhood mean opacity, AUC_vis 0.748; best single feature by Pareto."""
    return _nb_opacity(h, st)[sel].astype(np.float64)


def compute_flatness(h, sel, st):
    """The ASSIGNED hypothesis, in its stated direction (flatter = better normal =
    more trustworthy seed). It is WRONG: AUC_vis 0.469 (i.e. anti-predictive)."""
    ss = np.sort(h.scale, axis=1)
    return (ss[:, 1] / (ss[:, 0] + 1e-12))[sel].astype(np.float64)


# ---------------------------------------------------------------- standalone


if __name__ == "__main__":
    import os
    import sys
    import time
    t0 = time.time()
    sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
    sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
    from tune_lib import Harness, structure_tensor, nms_along_e1

    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    P = h.X[sel]
    print("pool", len(sel), "baseline", h.evaluate(P)[:2])
    for name, fn in [("compute", compute), ("compute_auc_best", compute_auc_best),
                     ("compute_dihedral", compute_dihedral),
                     ("compute_seed_density", compute_seed_density),
                     ("compute_nb_opacity", compute_nb_opacity),
                     ("compute_flatness", compute_flatness)]:
        s = fn(h, sel, st)
        o = np.argsort(-s)
        line = []
        for f in [1.0, 0.8, 0.6, 0.5, 0.45, 0.4, 0.3, 0.2]:
            keep = np.zeros(len(sel), bool)
            keep[o[:int(round(f * len(sel)))]] = True
            p, r, _ = h.evaluate(P, extra_mask=keep)
            line.append(f"{f:.2f}:{p:.3f}/{r:.3f}")
        print(f"{name:22s} " + " ".join(line))
    print(f"[{time.time()-t0:.1f}s]")
