"""score_pool.py -- family "pool": seed POOL CONSTRUCTION for M1a crease seeds.

MESH-FREE. Uses only gaussian centers / normals / opacity / scales (h.X, h.N, h.opa,
h.scale). Never touches h.crease, mesh_oracle, or any GT.

Headline findings of the pool sweep (scene chair, views 0+25, corrected harness):
  * The per-gaussian normal matters a lot. h.N (shortest COVARIANCE axis) is a poor
    surface normal for near-isotropic gaussians. Replacing it with the smallest
    eigenvector of the local kNN POSITION PCA (k~16-32) lifts the C_N structure-tensor
    AUC from 0.559 -> 0.703 and the gate precision at recall>=0.75 from 0.376 -> 0.450.
  * NMS along e1 does NOT help this gate (it only shrinks the pool); nms off >= nms 0.9
    > nms 0.7 >> nms 0.5 at matched tau.
  * The strongest single mesh-free feature is not the structure tensor at all: it is
    LOCAL POINT DENSITY (negative mean kNN distance, AUC 0.751 at k=32, 0.789 at k=96),
    because 3DGS densification piles gaussians onto geometric edges.
  * Opacity is a real but weaker lever (AUC 0.591); an opacity floor alone beats the
    whole C_N baseline.
  * The default score is the equal-weight rank sum of (density, normal-variation with
    PCA normals, opacity). No weights were fitted; see notes for the tuned variant.

compute() returns that rank sum for an arbitrary seed pool `sel`.
build_pool() returns the recommended POOL (best base precision at recall>=75%).
"""
import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import rankdata

KMAX = 32          # neighbourhood used for density + PCA normals
K_PCA = 32         # kNN for the local-PCA normal
K_ST = 16          # kNN for the normal structure tensor
_CACHE = {}


# ---------------------------------------------------------------- primitives
def _geom(h):
    """kNN graph, PCA normals, normal-structure-tensor l1 and density. Cached per harness."""
    key = id(h)
    if key in _CACHE:
        return _CACHE[key]
    X = np.asarray(h.X, np.float64)
    tree = cKDTree(X)
    _, knn = tree.query(X, k=KMAX + 1, workers=-1)
    knn = knn[:, 1:]

    # local-PCA normal: smallest eigenvector of the kNN position covariance
    nb = X[knn[:, :K_PCA]]
    d = nb - nb.mean(1, keepdims=True)
    C = np.einsum("nkc,nkd->ncd", d, d) / K_PCA
    _, V = np.linalg.eigh(C)
    npca = V[:, :, 0]
    npca /= np.linalg.norm(npca, axis=1, keepdims=True) + 1e-12

    # normal structure tensor C_N on those normals -> l1 = total normal variation
    nb2 = knn[:, :K_ST]
    nj = npca[nb2]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, npca))
    sg[sg == 0] = 1.0
    nj = nj * sg[..., None]
    dn = nj - nj.mean(1, keepdims=True)
    CN = np.einsum("nkc,nkd->ncd", dn, dn) / K_ST
    w = np.linalg.eigvalsh(CN)
    l1, l2 = w[:, 2], w[:, 1]

    dens = -np.linalg.norm(X[knn[:, :KMAX]] - X[:, None], axis=2).mean(1)
    out = {"knn": knn, "npca": npca, "l1": l1, "s_crease": l1 - l2, "dens": dens}
    _CACHE[key] = out
    return out


def _rank(v):
    return rankdata(v) / max(len(v), 1)


# ---------------------------------------------------------------- scores
def compute(h, sel, st):
    """Best single mesh-free per-seed score. Higher = more likely a true crease seed.

    Equal-weight rank sum of local density, PCA-normal structure-tensor l1, and opacity.
    Ranks are taken within `sel`, so the score is self-contained for the given pool.
    """
    g = _geom(h)
    sel = np.asarray(sel, np.int64)
    return (_rank(g["dens"][sel]) + _rank(g["l1"][sel])
            + _rank(np.asarray(h.opa)[sel])).astype(np.float64)


def compute_density(h, sel, st):
    """Local point density alone (-mean kNN-32 distance). Strongest single feature."""
    return _rank(_geom(h)["dens"][np.asarray(sel, np.int64)]).astype(np.float64)


def compute_l1_pca(h, sel, st):
    """Total normal variation l1 of C_N built on local-PCA normals (not h.N)."""
    return _rank(_geom(h)["l1"][np.asarray(sel, np.int64)]).astype(np.float64)


def compute_screase_pca(h, sel, st):
    """s_crease = l1 - l2 of C_N built on local-PCA normals (the baseline saliency,
    but with the better normal)."""
    return _rank(_geom(h)["s_crease"][np.asarray(sel, np.int64)]).astype(np.float64)


def compute_dens_l1(h, sel, st):
    """Density + normal variation, no opacity (highest AUC variant)."""
    g = _geom(h)
    sel = np.asarray(sel, np.int64)
    return (_rank(g["dens"][sel]) + _rank(g["l1"][sel])).astype(np.float64)


# ---------------------------------------------------------------- pool recipe
def build_pool(h, q=0.60, weights=(1.0, 1.0, 1.0)):
    """THE POOL RECIPE. Returns indices into h.X (no structure-tensor threshold, no NMS).

    Keep the top (1-q) fraction of de-floatered gaussians by the equal-weight rank sum of
    (local density, PCA-normal C_N l1, opacity). q=0.60 -> 22754 seeds,
    precision 0.528 / recall 0.757 on chair views 0+25 (baseline pool: 0.352 / 0.883).
    """
    g = _geom(h)
    wd, wl, wo = weights
    s = (wd * _rank(g["dens"]) + wl * _rank(g["l1"]) + wo * _rank(np.asarray(h.opa)))
    return np.where(s > np.quantile(s, q))[0]
