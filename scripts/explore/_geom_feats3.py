"""Round-3 feature bank: DENOISED normal fields (position-PCA normals, opacity-weighted
smoothed gaussian normals) + curvature. All MESH-FREE, per-gaussian geometric.
Motivation: the raw 3DGS per-gaussian normal (shortest covariance axis) is noisy, so the
raw C_N variance may be dominated by noise rather than by real dihedral structure.
"""
import numpy as np
from scipy.spatial import cKDTree


def _align(nrm, ref):
    s = np.sign((nrm * ref).sum(1))
    s[s == 0] = 1.0
    return nrm * s[:, None]


def _cn(n, knn):
    nj = n[knn]
    sign = np.sign(np.einsum("nkc,nc->nk", nj, n))
    sign[sign == 0] = 1.0
    nj = nj * sign[..., None]
    nbar = nj.mean(1, keepdims=True)
    d = nj - nbar
    C = np.einsum("nkc,nkd->ncd", d, d) / knn.shape[1]
    w, V = np.linalg.eigh(C)
    return w, V, nj


def _dihedral(nj, e1, n):
    proj = np.einsum("nkc,nc->nk", nj - nj.mean(1, keepdims=True), e1)
    pos = proj > 0
    npos = pos.sum(1).astype(float)
    nneg = nj.shape[1] - npos
    mp = np.einsum("nkc,nk->nc", nj, pos.astype(float)) / np.maximum(npos, 1)[:, None]
    mn = np.einsum("nkc,nk->nc", nj, (~pos).astype(float)) / np.maximum(nneg, 1)[:, None]
    mp /= np.linalg.norm(mp, axis=1, keepdims=True) + 1e-12
    mn /= np.linalg.norm(mn, axis=1, keepdims=True) + 1e-12
    ang = np.degrees(np.arccos(np.clip((mp * mn).sum(1), -1, 1)))
    ang[(npos == 0) | (nneg == 0)] = 0.0
    return ang


def compute_denoised(h, st, ks_pca=(12, 20, 32), ks_cn=(8, 16, 24)):
    X, n0, opa = h.X, h.N, h.opa
    N = len(X)
    F = {}
    tree = cKDTree(X)
    kmax = max(max(ks_pca), max(ks_cn))
    d, knn = tree.query(X, k=kmax + 1)
    d, knn = d[:, 1:], knn[:, 1:]

    # ---------- position-PCA normals at several supports ----------
    npca = {}
    for kp in ks_pca:
        nb = knn[:, :kp]
        Q = X[nb] - X[nb].mean(1, keepdims=True)
        C = np.einsum("nkc,nkd->ncd", Q, Q) / kp
        w, V = np.linalg.eigh(C)
        nn = _align(V[:, :, 0], n0)
        npca[kp] = nn
        F[f"pca_flat_k{kp}"] = -(w[:, 0] / (w[:, 2] + 1e-16))
        F[f"pca_agree_k{kp}"] = np.abs((nn * n0).sum(1))
        # curvature proxy: local RMS deviation from the tangent plane / spacing
        r = np.einsum("nkc,nc->nk", X[nb] - X[:, None, :], nn)
        sp = d[:, :kp].mean(1) + 1e-12
        F[f"curv_k{kp}"] = np.sqrt((r ** 2).mean(1)) / sp

    # ---------- C_N recomputed on the DENOISED normal fields ----------
    for kp in ks_pca:
        nn = npca[kp]
        for kc in ks_cn:
            w, V, nj = _cn(nn, knn[:, :kc])
            tag = f"p{kp}c{kc}"
            F[f"scr_pca_{tag}"] = w[:, 2] - w[:, 1]
            F[f"lin_pca_{tag}"] = (w[:, 2] - w[:, 1]) / (w[:, 2] + 1e-12)
            F[f"dih_pca_{tag}"] = _dihedral(nj, V[:, :, 2], nn)

    # ---------- opacity-weighted smoothing of the RAW gaussian normals ----------
    for ks in (8, 16):
        nb = knn[:, :ks]
        nj = n0[nb]
        sgn = np.sign(np.einsum("nkc,nc->nk", nj, n0))
        sgn[sgn == 0] = 1.0
        wgt = opa[nb] * sgn
        sm = np.einsum("nkc,nk->nc", nj, wgt) + n0 * opa[:, None]
        sm /= np.linalg.norm(sm, axis=1, keepdims=True) + 1e-12
        for kc in (8, 16):
            w, V, njj = _cn(sm, knn[:, :kc])
            tag = f"s{ks}c{kc}"
            F[f"scr_sm_{tag}"] = w[:, 2] - w[:, 1]
            F[f"dih_sm_{tag}"] = _dihedral(njj, V[:, :, 2], sm)
        F[f"sm_agree_k{ks}"] = np.abs((sm * n0).sum(1))

    # ---------- max pairwise normal angle inside the neighbourhood (robust dihedral) ----------
    for kp in (12, 20):
        nn = npca[kp]
        nb = knn[:, :kp]
        nj = _align(nn[nb].reshape(-1, 3), np.repeat(nn, kp, 0)).reshape(N, kp, 3)
        cs = np.einsum("nkc,nc->nk", nj, nn)
        F[f"maxang_pca_k{kp}"] = np.degrees(np.arccos(np.clip(cs.min(1), -1, 1)))
        F[f"p90ang_pca_k{kp}"] = np.degrees(
            np.arccos(np.clip(np.percentile(cs, 10, axis=1), -1, 1)))
    return F
