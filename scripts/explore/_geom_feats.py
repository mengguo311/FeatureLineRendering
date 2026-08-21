"""Feature bank for the `geom` family (per-gaussian geometric / saliency scores).
MESH-FREE: uses only gaussian params (mu, normal, scale, opacity) + C_N.
Shared by the exploration script and score_geom.py.
"""
import numpy as np
from scipy.spatial import cKDTree


def _sorted_scales(scale):
    ss = np.sort(scale, axis=1)          # ascending: [smin, smid, smax]
    return ss[:, 0], ss[:, 1], ss[:, 2]


def _ct(X, n, knn):
    """C_N eigendecomposition given an explicit knn index array."""
    nj = n[knn]
    sign = np.sign(np.einsum("nkc,nc->nk", nj, n))
    sign[sign == 0] = 1.0
    nj = nj * sign[..., None]
    nbar = nj.mean(1, keepdims=True)
    dnj = nj - nbar
    C = np.einsum("nkc,nkd->ncd", dnj, dnj) / knn.shape[1]
    w, V = np.linalg.eigh(C)
    return w, V, nj, nbar


def compute_all(h, st, ks=(8, 16, 24)):
    """Returns dict name -> float array [N] over ALL gaussians in h.X."""
    X, n, scale, opa = h.X, h.N, h.scale, h.opa
    N = len(X)
    F = {}

    # ---------- C_N at the canonical k=8 (as given in st) ----------
    l1, l2, l3 = st["l1"], st["l2"], st["l3"]
    e1, knn = st["e1"], st["knn"]
    lsum = l1 + l2 + l3 + 1e-12
    F["s_crease"] = st["s_crease"]
    F["s_corner"] = st["s_corner"]
    F["l1"] = l1
    F["l2"] = l2
    F["l3"] = l3
    F["lsum"] = lsum
    F["cn_lin"] = (l1 - l2) / (l1 + 1e-12)          # normal-variation linearity
    F["cn_crease_frac"] = (l1 - l2) / lsum
    F["cn_l1_frac"] = l1 / lsum
    F["cn_sph"] = -(l3 / (l1 + 1e-12))              # sign so higher = better
    F["cn_resid"] = -((l2 + l3) / (l1 + 1e-12))     # off-e1 residual, higher = cleaner

    # ---------- bimodality / dihedral of the aligned neighbour normals ----------
    w, V, nj, nbar = _ct(X, n, knn)
    dn = nj - nbar                                   # [N,k,3]
    proj = np.einsum("nkc,nc->nk", dn, e1)           # coordinate along e1
    tot = proj.var(1) + 1e-16
    pos = proj > 0
    npos = pos.sum(1).astype(float)
    k = knn.shape[1]
    nneg = k - npos
    mpos = np.where(npos > 0, (proj * pos).sum(1) / np.maximum(npos, 1), 0.0)
    mneg = np.where(nneg > 0, (proj * (~pos)).sum(1) / np.maximum(nneg, 1), 0.0)
    within = ((proj - np.where(pos, mpos[:, None], mneg[:, None])) ** 2).mean(1)
    F["bimodal"] = 1.0 - within / tot                # 1 = two tight clusters
    F["balance"] = np.minimum(npos, nneg) / (k / 2.0)  # cluster balance 0..1

    # dihedral angle between the two normal clusters (mesh-free; oracle uses 30 deg)
    mu_p = np.zeros((N, 3))
    mu_n = np.zeros((N, 3))
    for c in range(3):
        mu_p[:, c] = np.where(npos > 0, (nj[:, :, c] * pos).sum(1) / np.maximum(npos, 1), 0.0)
        mu_n[:, c] = np.where(nneg > 0, (nj[:, :, c] * (~pos)).sum(1) / np.maximum(nneg, 1), 0.0)
    mp = mu_p / (np.linalg.norm(mu_p, axis=1, keepdims=True) + 1e-12)
    mn = mu_n / (np.linalg.norm(mu_n, axis=1, keepdims=True) + 1e-12)
    cosang = np.clip((mp * mn).sum(1), -1, 1)
    F["dihedral"] = np.degrees(np.arccos(cosang))
    ok = (npos > 0) & (nneg > 0)
    F["dihedral"][~ok] = 0.0

    # ---------- gaussian anisotropy / normal reliability ----------
    smin, smid, smax = _sorted_scales(scale)
    F["scale_min"] = -smin
    F["scale_max"] = -smax
    F["scale_mid"] = -smid
    F["flat_mid_min"] = smid / (smin + 1e-12)        # normal well-defined if >> 1
    F["flat_max_min"] = smax / (smin + 1e-12)
    F["iso"] = -(smin / (smax + 1e-12))              # higher = less isotropic
    F["discness"] = (smid - smin) / (smid + 1e-12)
    F["needle"] = -(smax / (smid + 1e-12))           # higher = more disc-like (not needle)
    F["log_flat"] = np.log(smid / (smin + 1e-12))
    F["vol"] = -(smin * smid * smax)

    # ---------- opacity ----------
    F["opa"] = opa

    # ---------- local density / spacing ----------
    tree = cKDTree(X)
    kmax = max(ks)
    dists, knn_big = tree.query(X, k=kmax + 1)
    dists, knn_big = dists[:, 1:], knn_big[:, 1:]
    d8 = dists[:, :8].mean(1)
    F["dens"] = -d8                                  # higher = denser
    F["spacing"] = d8
    F["rel_scale"] = smax / (d8 + 1e-12)
    F["rel_scale_min"] = -(smin / (d8 + 1e-12))

    # ---------- local POSITION pca (surface planarity) ----------
    kp = 16
    nb = knn_big[:, :kp]
    P = X[nb] - X[:, None, :]
    Cp = np.einsum("nkc,nkd->ncd", P, P) / kp
    wp, Vp = np.linalg.eigh(Cp)
    p1, p2, p3 = wp[:, 2], wp[:, 1], wp[:, 0]
    psum = p1 + p2 + p3 + 1e-16
    F["pos_planar"] = -(p3 / (p1 + 1e-16))           # higher = flatter patch
    F["pos_thick"] = p3 / psum                       # higher = thicker (crease bends -> thicker)
    F["pos_lin"] = (p1 - p2) / psum
    F["pos_scatter"] = p3 / (p2 + 1e-16)
    # agreement between the gaussian normal and the local position-PCA normal
    pn = Vp[:, :, 0]
    F["n_pca_agree"] = np.abs(np.einsum("nc,nc->n", pn, n))

    # ---------- neighbourhood-aggregated normal reliability ----------
    lf = np.log(smid / (smin + 1e-12))
    F["nb_flat_mean"] = lf[knn].mean(1)
    F["nb_flat_min"] = lf[knn].min(1)
    F["nb_flat_self_min"] = np.minimum(lf, lf[knn].min(1))
    F["nb_opa_mean"] = opa[knn].mean(1)

    # ---------- multi-scale C_N consistency ----------
    for kk in ks:
        if kk == 8:
            continue
        wk, Vk, _, _ = _ct(X, n, knn_big[:, :kk])
        F[f"s_crease_k{kk}"] = wk[:, 2] - wk[:, 1]
        F[f"cn_lin_k{kk}"] = (wk[:, 2] - wk[:, 1]) / (wk[:, 2] + 1e-12)
        # angle between e1 at k=8 and at kk (stable across scales -> real crease)
        e1k = Vk[:, :, 2]
        F[f"e1_stab_k{kk}"] = np.abs(np.einsum("nc,nc->n", e1k, e1))
    F["ms_crease"] = np.minimum(F["s_crease"] / (F["s_crease"].std() + 1e-12),
                                F["s_crease_k16"] / (F["s_crease_k16"].std() + 1e-12))
    return F
