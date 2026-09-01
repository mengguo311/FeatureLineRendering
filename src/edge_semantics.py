r"""tier1/src/edge_semantics.py — METHOD PATH. MESH-FREE.
Per-candidate crease-vs-texture FEATURES for the Phase 1c kill-test.

`grep -n "mesh\|trimesh" src/edge_semantics.py` finds nothing but this banner. Imports only
common / render / visibility / epipolar_consensus — none touch the GT mesh. Labels and AUC
live in scripts/dexprimary_p1c.py (EVAL); this module never sees them.

THREE FEATURE FAMILIES (so a failure is diagnostic, not just dead):

FAM-A photometric profile. A flat printed decal is an ALBEDO step: chromaticity changes,
    luminance may or may not. A shading crease is the same material on both sides: luminance
    steps, chromaticity is continuous (white light; holds in NeRF-synthetic). Sampled from the
    same white-composited photos DexiNed ran on, at +-1/2 px along the local edge normal
    (gradient of the blurred DexiNed prob map), median-aggregated over every reference view
    that sees the candidate. NOTE: the per-gaussian SH-DC albedo-step variant of this physics
    already died (AUC~0.5, lego); this is the image-space re-measurement at full resolution.

FAM-B geometric discontinuity — the KNOWN-DEAD NEGATIVE CONTROL on lego decals (expect ~0.5
    there; on chair it is a live hypothesis, carrier-AUC 0.854 precedent). Rendered-normal
    angle and relative depth curvature across the edge, from render_gbuffer. If lego FAM-B
    comes back >>0.5 the harness is leaking and every other number is suspect.

FAM-C learned semantic prior. Frozen zero-shot DINOv2 ViT-S/14 patch tokens on the same
    photos; per-candidate descriptor = visibility-weighted mean of the bilinearly-sampled
    patch token over its views (384-d, for a linear probe fit by the EVAL script on a
    disjoint split), plus two zero-shot scalars: the feature step across the edge at +-1
    patch (semantic boundary strength) and the cosine similarity of the two sides. Patch
    stride is 14 px, so this measures WHAT the edge lies on, not where it is — exactly the
    semantic prior being tested.

All families are aggregated per candidate over the SAME view set with the SAME visibility
mask, so family AUCs are comparable.
"""
import os

import cv2
import numpy as np
import torch

from . import common, render, visibility
from .epipolar_consensus import nms_thin  # noqa: F401  (kept for parity with p0/p1b tooling)

A_NAMES = ["luma_step", "chroma_step", "chroma_frac", "sat_step", "grad_col_ratio"]
B_NAMES = ["normal_angle", "depth_curv", "alpha_drop"]
C_SCALAR_NAMES = ["dino_step", "dino_side_cos"]


def composite_white(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        im = im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)
    return np.ascontiguousarray(im[:, :, ::-1].astype(np.float32) / 255.0)  # RGB [0,1]


def _bil(img, u, v_):
    """Bilinear sample img[H,W,(C)] at float pixel coords; clamps to border."""
    H, W = img.shape[:2]
    u = np.clip(u, 0, W - 1.001)
    v_ = np.clip(v_, 0, H - 1.001)
    x0 = np.floor(u).astype(np.int64); y0 = np.floor(v_).astype(np.int64)
    fx = (u - x0)[..., None] if img.ndim == 3 else (u - x0)
    fy = (v_ - y0)[..., None] if img.ndim == 3 else (v_ - y0)
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy)
            + c * (1 - fx) * fy + d * fx * fy)


def edge_normal_field(prob, blur=1.5):
    ps = cv2.GaussianBlur(prob, (0, 0), blur)
    gx = cv2.Sobel(ps, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(ps, cv2.CV_32F, 0, 1, ksize=3)
    n = np.sqrt(gx * gx + gy * gy) + 1e-9
    return gx / n, gy / n


def fam_ab_view(P, cam, rgb, prob, gbuf, halfpix=0.5, offs=(1.0, 2.0)):
    """FAM-A + FAM-B features of candidates P[N,3] in ONE view.
    Returns (inb[N], A[N,5], B[N,3], en[N,2]) where en = the pixel-scale edge normal used,
    nan outside inb (fam_c_view reuses it so all families share one normal per view)."""
    vis, uv, z = visibility.visible_mask(P, cam, gbuf["depth"])
    u = uv[:, 0] - halfpix                    # photo-index coords
    v_ = uv[:, 1] - halfpix
    inb = vis & (u >= 3) & (u < cam.W - 4) & (v_ >= 3) & (v_ < cam.H - 4)
    N = len(P)
    A = np.full((N, len(A_NAMES)), np.nan, np.float32)
    B = np.full((N, len(B_NAMES)), np.nan, np.float32)
    en = np.full((N, 2), np.nan, np.float32)
    if not inb.any():
        return inb, A, B, en
    ui, vi = u[inb], v_[inb]
    gx, gy = edge_normal_field(prob)
    ndx = _bil(gx, ui, vi); ndy = _bil(gy, ui, vi)
    nn = np.sqrt(ndx ** 2 + ndy ** 2) + 1e-9
    ndx, ndy = ndx / nn, ndy / nn
    en[inb, 0] = ndx
    en[inb, 1] = ndy

    # ---- FAM-A: photometric profile across the edge
    luma_w = np.array([0.299, 0.587, 0.114], np.float32)
    best = None
    for s in offs:
        cp = _bil(rgb, ui + s * ndx, vi + s * ndy)          # [M,3]
        cm = _bil(rgb, ui - s * ndx, vi - s * ndy)
        Yp = cp @ luma_w; Ym = cm @ luma_w
        chp = cp / (cp.sum(1, keepdims=True) + 1e-6)        # rgb chromaticity
        chm = cm / (cm.sum(1, keepdims=True) + 1e-6)
        luma = np.abs(Yp - Ym)
        chroma = np.linalg.norm(chp - chm, axis=1)
        sat = np.abs(chp.max(1) - chp.min(1) - (chm.max(1) - chm.min(1)))
        cur = np.stack([luma, chroma, sat], 1)
        best = cur if best is None else np.maximum(best, cur)
    luma, chroma, sat = best[:, 0], best[:, 1], best[:, 2]
    Af = np.empty((int(inb.sum()), len(A_NAMES)), np.float32)
    Af[:, 0] = luma
    Af[:, 1] = chroma
    Af[:, 2] = chroma / (chroma + 4.0 * luma + 1e-6)        # decal-ness: chroma share
    Af[:, 3] = sat
    # colour-vs-gray gradient ratio at the pixel itself
    gray = rgb @ luma_w
    ggx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3); ggy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gmag = np.sqrt(ggx ** 2 + ggy ** 2)
    cmag = np.zeros_like(gmag)
    for ch in range(3):
        cx_ = cv2.Sobel(rgb[:, :, ch] - gray, cv2.CV_32F, 1, 0, ksize=3)
        cy_ = cv2.Sobel(rgb[:, :, ch] - gray, cv2.CV_32F, 0, 1, ksize=3)
        cmag += np.sqrt(cx_ ** 2 + cy_ ** 2)
    ratio = cmag / (cmag + 3.0 * gmag + 1e-6)
    Af[:, 4] = _bil(ratio, ui, vi)
    A[inb] = Af

    # ---- FAM-B: rendered normal / depth discontinuity (KNOWN-DEAD control on lego)
    nrm = gbuf["normal"].detach().cpu().numpy()
    dep = gbuf["depth"].detach().cpu().numpy()
    alp = gbuf["alpha"].detach().cpu().numpy()
    dep = np.where(np.isfinite(dep), dep, 0.0).astype(np.float32)
    s = 2.0
    npx = _bil(nrm, ui + s * ndx, vi + s * ndy)
    nmx = _bil(nrm, ui - s * ndx, vi - s * ndy)
    npx /= np.linalg.norm(npx, axis=1, keepdims=True) + 1e-9
    nmx /= np.linalg.norm(nmx, axis=1, keepdims=True) + 1e-9
    Bf = np.empty((int(inb.sum()), len(B_NAMES)), np.float32)
    Bf[:, 0] = np.arccos(np.clip((npx * nmx).sum(1), -1, 1))
    d0 = _bil(dep, ui, vi)
    dp = _bil(dep, ui + s * ndx, vi + s * ndy)
    dm = _bil(dep, ui - s * ndx, vi - s * ndy)
    Bf[:, 1] = np.abs(dp + dm - 2 * d0) / np.maximum(d0, 1e-3)
    ap = _bil(alp, ui + s * ndx, vi + s * ndy)
    am = _bil(alp, ui - s * ndx, vi - s * ndy)
    Bf[:, 2] = np.abs(ap - am)
    B[inb] = Bf
    return inb, A, B, en


@torch.no_grad()
def dino_tokens(model, rgb, device="cuda", size=798):
    """rgb float [H,W,3] in [0,1] -> patch token grid [g,g,384] float16 (g=size/14)."""
    x = torch.tensor(rgb, dtype=torch.float32, device=device).permute(2, 0, 1)[None]
    x = torch.nn.functional.interpolate(x, size=(size, size), mode="bilinear",
                                        align_corners=False)
    mean = torch.tensor([0.485, 0.456, 0.406], device=device)[None, :, None, None]
    std = torch.tensor([0.229, 0.224, 0.225], device=device)[None, :, None, None]
    out = model.forward_features((x - mean) / std)
    t = out["x_norm_patchtokens"][0]                      # [g*g, C]
    grid = int(np.sqrt(t.shape[0]))
    return t.reshape(grid, grid, -1).half().cpu().numpy(), grid


def fam_c_view(P, cam, tokens, grid, gbuf, halfpix=0.5, img_size=800, dino_size=798):
    """FAM-C in one view: (vis[N], desc[N,C] fp32, scal[N,2]).
    desc = the patch token AT the candidate; scal = [feature step across edge at +-1 patch,
    cosine similarity of the two sides]."""
    vis, uv, _ = visibility.visible_mask(P, cam, gbuf["depth"])
    u = (uv[:, 0] - halfpix) * (dino_size / img_size) / 14.0 - 0.5   # patch-grid coords
    v_ = (uv[:, 1] - halfpix) * (dino_size / img_size) / 14.0 - 0.5
    inb = vis & (u >= 1) & (u < grid - 2) & (v_ >= 1) & (v_ < grid - 2)
    N, C = len(P), tokens.shape[2]
    desc = np.full((N, C), np.nan, np.float32)
    scal = np.full((N, 2), np.nan, np.float32)
    if not inb.any():
        return inb, desc, scal
    ui, vi = u[inb], v_[inb]
    tok = tokens.astype(np.float32)
    f0 = _bil(tok, ui, vi)
    # edge normal at patch scale from the token-magnitude field is unstable; use the photo
    # edge normal passed via gbuf["edge_nx"], gbuf["edge_ny"] sampled at pixel res
    ndx = gbuf["edge_nx"][inb]; ndy = gbuf["edge_ny"][inb]
    fp = _bil(tok, ui + ndx, vi + ndy)                    # +-1 patch across the edge
    fm = _bil(tok, ui - ndx, vi - ndy)
    step = np.linalg.norm(fp - fm, axis=1) / (np.linalg.norm(f0, axis=1) + 1e-6)
    cos = (fp * fm).sum(1) / (np.linalg.norm(fp, axis=1) * np.linalg.norm(fm, axis=1) + 1e-9)
    desc[inb] = f0
    scal[inb, 0] = step
    scal[inb, 1] = cos
    return inb, desc, scal


def chain_candidates(P, r=0.005, k=8, cos_min=0.6, min_size=10):
    """3D proximity + direction-coherence chaining (mesh-free). Returns labels[N] (-1 = none).

    Edges = kNN pairs within r whose displacement aligns with BOTH endpoints' local PCA
    tangents; chains = connected components; components < min_size get label -1."""
    from scipy.spatial import cKDTree
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    N = len(P)
    tree = cKDTree(P)
    d, idx = tree.query(P, k=k + 1)
    d, idx = d[:, 1:], idx[:, 1:]
    # local tangent by PCA of neighbours
    nb = P[idx] - P[:, None, :]
    cov = np.einsum("nkc,nkd->ncd", nb, nb)
    w, V = np.linalg.eigh(cov)
    tang = V[:, :, 2]
    ii = np.repeat(np.arange(N), k)
    jj = idx.reshape(-1)
    dd = d.reshape(-1)
    disp = P[jj] - P[ii]
    dn = np.linalg.norm(disp, axis=1) + 1e-12
    ci = np.abs((disp * tang[ii]).sum(1)) / dn
    cj = np.abs((disp * tang[jj]).sum(1)) / dn
    ok = (dd < r) & (ci >= cos_min) & (cj >= cos_min)
    m = coo_matrix((np.ones(ok.sum()), (ii[ok], jj[ok])), shape=(N, N))
    n_comp, lab = connected_components(m + m.T, directed=False)
    cnt = np.bincount(lab, minlength=n_comp)
    lab = np.where(cnt[lab] >= min_size, lab, -1)
    return lab


# ---------------------------------------------------------------- Phase 1d: pseudo-labels
# MESH-FREE supervision sources. These functions see ONLY method-path features (FAM-A/B/C
# arrays + DINO descriptors). They never see mesh labels — that is the whole point of the
# Phase 1d falsification, and it is what the AST check verifies.
#
# Every threshold below is FROZEN A PRIORI from physics, not tuned on any mesh AUC:
# a geometric crease is (i) a rendered-normal discontinuity, (ii) a rendered-depth
# curvature, (iii) a shading-contrast (luminance) step. The vote V is the mean PERCENTILE
# of those three cues (scale-free, sign fixed toward "crease" by the physics, never by
# measured AUC — alpha_drop is deliberately excluded because its sign is not decidable
# a priori).

def _pct(x):
    """Percentile-rank transform in [0,1]; NaN stays NaN."""
    out = np.full(len(x), np.nan, np.float32)
    m = np.isfinite(x)
    r = np.argsort(np.argsort(x[m]))
    out[m] = r / max(len(r) - 1, 1)
    return out


def crease_vote(FA, FB):
    """V in [0,1]: mean percentile of (normal_angle, depth_curv, luma_step)."""
    v = np.stack([_pct(FB[:, B_NAMES.index("normal_angle")]),
                  _pct(FB[:, B_NAMES.index("depth_curv")]),
                  _pct(FA[:, A_NAMES.index("luma_step")])], 1)
    return np.nanmean(v, 1)


def pseudo_labels_votes(FA, FB, q_pos=0.85, q_neg=0.50):
    """PL-VOTE: pseudo-positive = vote above the q_pos quantile, pseudo-negative = below
    q_neg, middle band unlabeled (-1). Quantiles frozen a priori (~15% positives, matching
    no measured class prior — just 'creases are the sparse class')."""
    V = crease_vote(FA, FB)
    y = np.full(len(V), -1, np.int8)
    m = np.isfinite(V)
    hi = np.nanquantile(V[m], q_pos)
    lo = np.nanquantile(V[m], q_neg)
    y[m & (V >= hi)] = 1
    y[m & (V <= lo)] = 0
    return y, V


def pseudo_labels_cluster(DD, FA, FB, k=8, seed=0, max_fit=60000):
    """PL-CLUSTER (self-supervised): k-means the DINO descriptors, then orient each cluster
    by the mesh-free crease vote — a cluster is pseudo-positive iff its mean vote exceeds
    the global mean vote. Labels every finite-descriptor point (no band)."""
    from sklearn.cluster import KMeans
    V = crease_vote(FA, FB)
    ok = np.isfinite(DD[:, 0]) & np.isfinite(V)
    X = DD[ok].astype(np.float32)
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    rng = np.random.default_rng(seed)
    sub = rng.choice(len(X), min(max_fit, len(X)), replace=False)
    km = KMeans(n_clusters=k, n_init=4, random_state=seed).fit(X[sub])
    cl = km.predict(X)
    gmean = float(np.mean(V[ok]))
    cmean = np.array([V[ok][cl == c].mean() if (cl == c).any() else -1 for c in range(k)])
    y = np.full(len(DD), -1, np.int8)
    y[ok] = (cmean[cl] > gmean).astype(np.int8)
    return y, cl, cmean
