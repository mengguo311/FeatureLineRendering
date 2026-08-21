"""Round-2 feature bank for the `geom` family: features that live on the SEED SUBSET
(seed-graph coherence) plus gaussian-axis / tangent alignment and 2-plane position fits.
All MESH-FREE.
"""
import numpy as np
from scipy.spatial import cKDTree

import sys, os
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from src import common


def compute_seedlevel(h, sel, st, ks=(6, 12, 24)):
    """Features defined on the seed subset only. Returns dict name -> [len(sel)]."""
    X = h.X
    P = X[sel]
    e3 = st["e3"][sel]      # crease tangent
    e1 = st["e1"][sel]      # across-crease
    n = h.N[sel]
    F = {}

    # ---------- gaussian principal axes ----------
    quat = h.g["quat"][h.keep][sel]
    R = common.quat_to_rotmat(quat)              # columns = principal axes
    sc = h.scale[sel]
    amax = sc.argmax(1)
    amid = np.argsort(sc, 1)[:, 1]
    a_max = R[np.arange(len(sel)), :, amax]
    a_mid = R[np.arange(len(sel)), :, amid]
    a_max /= np.linalg.norm(a_max, axis=1, keepdims=True) + 1e-12
    a_mid /= np.linalg.norm(a_mid, axis=1, keepdims=True) + 1e-12
    ss = np.sort(sc, 1)
    elong = np.log((ss[:, 2] + 1e-12) / (ss[:, 1] + 1e-12))

    F["align_tan"] = np.abs((a_max * e3).sum(1))
    F["align_tan_w"] = np.abs((a_max * e3).sum(1)) * elong
    F["align_e1_mid"] = np.abs((a_mid * e1).sum(1))
    F["n_perp_e1"] = -np.abs((n * e1).sum(1))
    F["elong"] = elong

    # ---------- seed-graph coherence (does this seed lie on a 1D chain of seeds?) ----------
    tree = cKDTree(P)
    kmax = max(ks)
    d, idx = tree.query(P, k=kmax + 1)
    d, idx = d[:, 1:], idx[:, 1:]
    off = P[idx] - P[:, None, :]                        # [M,k,3]
    offn = off / (np.linalg.norm(off, axis=2, keepdims=True) + 1e-12)
    for k in ks:
        o, ii, dd = offn[:, :k], idx[:, :k], d[:, :k]
        # (a) do the neighbour seeds lie ALONG my tangent?
        col = np.abs(np.einsum("mkc,mc->mk", o, e3))
        F[f"chain_col_k{k}"] = col.mean(1)
        F[f"chain_colmax_k{k}"] = np.sort(col, 1)[:, -2:].mean(1)
        # (b) do neighbour tangents agree with mine?
        F[f"chain_tan_k{k}"] = np.abs(np.einsum("mkc,mc->mk", e3[ii], e3)).mean(1)
        # (c) do neighbour across-crease dirs agree?
        F[f"chain_e1_k{k}"] = np.abs(np.einsum("mkc,mc->mk", e1[ii], e1)).mean(1)
        # (d) combined: collinear AND tangent-consistent
        F[f"chain_both_k{k}"] = (col * np.abs(np.einsum("mkc,mc->mk", e3[ii], e3))).mean(1)
        # (e) local seed density (seeds cluster on creases)
        F[f"seed_dens_k{k}"] = -dd.mean(1)
        # (f) planarity of the seed cloud itself: real creases are 1D curves
        Pl = off[:, :k]
        C = np.einsum("mkc,mkd->mcd", Pl, Pl) / k
        w, V = np.linalg.eigh(C)
        F[f"seed_lin_k{k}"] = (w[:, 2] - w[:, 1]) / (w.sum(1) + 1e-16)
        F[f"seed_flat_k{k}"] = -(w[:, 0] / (w[:, 2] + 1e-16))
        # (g) alignment of the seed-cloud principal direction with my tangent
        F[f"seed_pcatan_k{k}"] = np.abs(np.einsum("mc,mc->m", V[:, :, 2], e3))

    # ---------- 2-plane fit residual on neighbour POSITIONS (gaussian kNN) ----------
    knn = st["knn"][sel]
    Q = X[knn] - P[:, None, :]                          # [M,k,3]
    kq = knn.shape[1]
    Cq = np.einsum("mkc,mkd->mcd", Q, Q) / kq
    wq, Vq = np.linalg.eigh(Cq)
    nrm_pca = Vq[:, :, 0]
    r1 = np.einsum("mkc,mc->mk", Q, nrm_pca)            # 1-plane residual
    rms1 = np.sqrt((r1 ** 2).mean(1)) + 1e-12
    # split neighbours by the side of the crease (sign of their normal's e1 coord) and
    # fit a plane to each half -> residual ratio
    nj = h.N[knn]
    sgn = np.sign(np.einsum("mkc,mc->mk", nj, n))
    sgn[sgn == 0] = 1.0
    nj = nj * sgn[..., None]
    side = np.einsum("mkc,mc->mk", nj - nj.mean(1, keepdims=True), e1) > 0
    res2 = np.zeros(len(sel))
    for s in (True, False):
        m = side == s
        cnt = m.sum(1).astype(float)
        Qm = Q * m[..., None]
        mean = Qm.sum(1) / np.maximum(cnt, 1)[:, None]
        D = (Q - mean[:, None, :]) * m[..., None]
        Cm = np.einsum("mkc,mkd->mcd", D, D) / np.maximum(cnt, 1)[:, None, None]
        wm, Vm = np.linalg.eigh(Cm)
        rr = np.einsum("mkc,mc->mk", Q - mean[:, None, :], Vm[:, :, 0]) * m
        res2 += (rr ** 2).sum(1)
    rms2 = np.sqrt(res2 / kq) + 1e-12
    F["plane2_gain"] = np.log(rms1 / rms2)
    F["plane1_res"] = rms1 / (np.sqrt(wq[:, 2]) + 1e-12)   # normalised 1-plane thickness
    return F
