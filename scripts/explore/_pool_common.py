"""Shared helpers for the seed-POOL sweep (eval-side exploration).
Mesh-free pool construction; the harness (eval-only) is used for scoring.
"""
import os
import sys
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from tune_lib import structure_tensor, nms_along_e1  # noqa: E402

KMAX = 32


def build_knn(X, kmax=KMAX):
    tree = cKDTree(X)
    _, knn = tree.query(X, k=kmax + 1, workers=-1)
    return knn[:, 1:].astype(np.int64)


def pca_normals(X, knn, k):
    """Smallest eigenvector of the local kNN position covariance (unoriented)."""
    nb = X[knn[:, :k]]                       # [N,k,3]
    mu = nb.mean(1, keepdims=True)
    d = nb - mu
    C = np.einsum("nkc,nkd->ncd", d, d) / k
    w, V = np.linalg.eigh(C)
    n = V[:, :, 0]
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return n


def smooth_normals(n, knn, k, iters=1):
    """Sign-aligned kNN average of normals, renormalised. Unoriented-safe."""
    out = n.copy()
    for _ in range(iters):
        nj = out[knn[:, :k]]
        s = np.sign(np.einsum("nkc,nc->nk", nj, out))
        s[s == 0] = 1.0
        nb = (nj * s[..., None]).mean(1)
        nb += out                             # include self
        nrm = np.linalg.norm(nb, axis=1, keepdims=True)
        out = nb / np.clip(nrm, 1e-12, None)
    return out


def make_pool(X, n, knn, k, tau, use_nms=True, cos_thr=0.7, elig=None,
              st=None, mode="crease", corner_ratio=None):
    """Return (sel indices into X, st dict). elig = bool[N] eligibility mask."""
    if st is None:
        st = structure_tensor(X, n, k, knn=knn[:, :k])
    s = st["s_crease"]
    if mode == "crease":
        score = s
    elif mode == "l1":
        score = st["l1"]
    elif mode == "corner":
        score = st["s_corner"]
    else:
        raise ValueError(mode)
    cand = np.where(score > tau)[0]
    if elig is not None:
        cand = cand[elig[cand]]
    if corner_ratio is not None:  # drop corner-like points
        cand = cand[st["s_corner"][cand] <= corner_ratio * s[cand]]
    if len(cand) == 0:
        return cand, st
    if use_nms:
        sel = nms_along_e1(X, cand, score, st["e1"], st["knn"], cos_thr=cos_thr)
    else:
        sel = cand
    return sel, st


def crease_label(h, X, sel, tau=2.5):
    """EVAL ONLY. True if the seed projects within tau px of a GT crease pixel in >=1 view
    (only counting views where the seed is visible)."""
    from src import visibility
    lab = np.zeros(len(sel), bool)
    seen = np.zeros(len(sel), bool)
    P = X[sel]
    for v in h.views:
        vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
        vv = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
        cdt = h.crease[v][2]
        d = cdt[vv, u]
        lab |= vis & (d <= tau)
        seen |= vis
    return lab, seen


def auc(score, label):
    from scipy.stats import rankdata
    label = np.asarray(label, bool)
    if label.all() or (~label).any() is False:
        return float("nan")
    r = rankdata(score)
    n1 = label.sum()
    n0 = len(label) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((r[label].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))
