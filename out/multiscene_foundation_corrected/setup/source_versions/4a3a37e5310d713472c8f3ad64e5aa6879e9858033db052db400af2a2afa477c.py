"""tier1/src/geom_gate.py — GEOMETRY-GATED edge field (METHOD PATH, texture-blind).

HARD INVARIANT: consumes ONLY the rendered G-buffer (depth + normal + alpha) and the
training RGB. It never imports mesh_oracle and never reads the GT mesh.

WHAT IT IS FOR
    The DT that both the M1a seed recipe and the M1b pull descend is built on RGB-Canny
    edges, where a printed fabric pattern and a 30-degree dihedral crease are
    photometrically identical. This module keeps only those Canny pixels that have
    GEOMETRIC support in the G-buffer, so the DT valley survives at real creases and
    disappears at flat prints:

        DT_pull_k = distanceTransform( Canny_k  AND  dilate(M_geom_k, 2px) )

    The mask only SELECTS which Canny pixels survive. It never moves them, so the
    sub-pixel locus the pull descends to is unchanged and the measured 0.27% temporal
    flicker floor is preserved by construction.

*** READ THIS BEFORE TRUSTING THE GATE (STEP 0 falsification, chair, 8 views) ***
    The premise "at a flat print the G-buffer stays flat" is FALSE on vanilla 3DGS.
    Labelling Canny pixels by the GT mesh and measuring the bilateral-ribbon dihedral:
        FABRIC print  theta p50 28.8 deg, p95 79.3 deg     (dd/d p95 2.01%)
        TRUE crease   theta p05  4.9 deg, p50 23.4 deg     (dd/d p05 0.01%)
    i.e. fabric is MORE dihedral than crease and the distributions overlap almost
    completely (spec separation criterion: -74.4 deg against a required +6 deg).
    A control run of the identical estimator on GT-MESH depth separates the classes
    (AUC 0.72-0.77) while gaussian depth is at chance (AUC 0.42-0.51), so the estimator
    is sound: vanilla-3DGS geometry is ALBEDO-CONTAMINATED — the reconstruction embosses
    the fabric print into the depth field, because that is where the colour variation is.
    Multi-view rescue attempts (Plan B) are no better: across-view dihedral variance
    AUC 0.577, world-normal consensus 0.596, multi-view depth step 0.538, and the best
    of any candidate (shading-vs-albedo view-contrast variance) only 0.638, itself mostly
    explained by edge contrast (control AUC 0.619).

    So this module is retained as a MEASURED, WIRED, DEFAULT-OFF component with an honest
    end-to-end number attached, not as a fix. Enable it deliberately and re-measure.
"""
import cv2
import numpy as np

# spec's frozen operating points
THETA_PULL, TAU_DEPTH_PULL = 20.0, 0.015
THETA_SEED, TAU_DEPTH_SEED = 12.0, 0.008
DP = 4
GMAG_MIN = 0.02


def dihedral_map(normal, depth, alpha, dp=DP, gmag_min=GMAG_MIN):
    """Two-cluster dihedral (deg) of the alpha-composited normal map over a
    (2dp+1)^2 patch. This is the raw angle, WITHOUT the planarity/NMS gating that
    final_recipe.crease_ridge_dt applies, because the gate wants a graded geometric
    support map rather than a thinned ridge."""
    H, W = depth.shape
    fg = (alpha > 0.5) & np.isfinite(depth)
    nrm = normal.astype(np.float32)
    gy, gx = np.gradient(nrm, axis=(0, 1))
    gmag = np.sqrt((gx ** 2).sum(-1) + (gy ** 2).sum(-1)).astype(np.float32)
    A = np.zeros((H, W), np.float32)
    cy, cx = np.nonzero(fg & (gmag > gmag_min))
    if not len(cy):
        return A
    off = np.arange(-dp, dp + 1)
    ou, ov = np.meshgrid(off, off, indexing="xy")
    ou = ou.ravel(); ov = ov.ravel()
    pu = np.clip(cx[:, None] + ou[None], 0, W - 1)
    pv = np.clip(cy[:, None] + ov[None], 0, H - 1)
    pn = nrm[pv, pu]
    pf = fg[pv, pu].astype(np.float32)
    cnt = np.maximum(pf.sum(1), 1.0)
    nb = np.matmul(pf[:, None, :], pn)[:, 0] / cnt[:, None]
    dn = pn - nb[:, None]
    C = np.matmul((dn * pf[..., None]).transpose(0, 2, 1), dn) / cnt[:, None, None]
    e1 = np.linalg.eigh(C)[1][:, :, 2]
    t = np.matmul(dn, e1[:, :, None])[:, :, 0]
    A_ = ((t > 0) & (pf > 0)).astype(np.float32)
    B_ = ((t < 0) & (pf > 0)).astype(np.float32)
    nA, nB = A_.sum(1), B_.sum(1)
    mA = np.matmul(A_[:, None, :], pn)[:, 0] / np.maximum(nA, 1)[:, None]
    mB = np.matmul(B_[:, None, :], pn)[:, 0] / np.maximum(nB, 1)[:, None]
    mA /= np.linalg.norm(mA, axis=1, keepdims=True) + 1e-12
    mB /= np.linalg.norm(mB, axis=1, keepdims=True) + 1e-12
    ang = np.degrees(np.arccos(np.clip((mA * mB).sum(1), -1, 1)))
    ang[(nA == 0) | (nB == 0)] = 0.0
    A[cy, cx] = ang
    return A


def depth_step_map(depth, alpha, rad=3):
    """Relative depth discontinuity: local depth range / depth, over a (2rad+1)^2 window.
    A slanted flat surface contributes only its slant across the window (small); a real
    depth step contributes the whole jump."""
    fg = (alpha > 0.5) & np.isfinite(depth)
    z = np.where(fg, depth, np.nan).astype(np.float32)
    zf = np.nan_to_num(z, nan=0.0)
    m = fg.astype(np.uint8)
    k = np.ones((2 * rad + 1, 2 * rad + 1), np.uint8)
    big = cv2.dilate(zf, k)
    small = -cv2.dilate(-np.where(fg, zf, 1e9).astype(np.float32), k)
    cnt = cv2.dilate(m, k)
    rng = np.where((cnt > 0) & fg, big - small, 0.0)
    return np.where(fg, rng / np.maximum(zf, 1e-6), 0.0).astype(np.float32)


def geom_support(gbuf, theta_thresh=THETA_PULL, tau_depth=TAU_DEPTH_PULL, dp=DP,
                 rad=3, soft=False, tau_soft=6.0):
    """Texture-blind geometric-crease support from one G-buffer.
    soft=True returns a logistic weight in [0,1] instead of a hard mask (anti-chatter:
    a hard threshold can flip a marginal crease in and out between adjacent trajectory
    frames, which would reintroduce exactly the flicker M1b exists to remove)."""
    dep = gbuf["depth"].detach().cpu().numpy().astype(np.float32) if hasattr(
        gbuf["depth"], "detach") else np.asarray(gbuf["depth"], np.float32)
    nrm = gbuf["normal"].detach().cpu().numpy() if hasattr(
        gbuf["normal"], "detach") else np.asarray(gbuf["normal"])
    alp = gbuf["alpha"].detach().cpu().numpy() if hasattr(
        gbuf["alpha"], "detach") else np.asarray(gbuf["alpha"])
    A = dihedral_map(nrm, dep, alp, dp=dp)
    D = depth_step_map(dep, alp, rad=rad)
    if soft:
        wa = 1.0 / (1.0 + np.exp(-(A - theta_thresh) / tau_soft))
        wd = 1.0 / (1.0 + np.exp(-(D - tau_depth) / max(tau_depth * 0.5, 1e-6)))
        return np.maximum(wa, wd).astype(np.float32)
    return ((A >= theta_thresh) | (D >= tau_depth))


def gate_edges(edge, support, dilate_px=2):
    """Keep only Canny pixels with geometric support nearby. Never moves a pixel."""
    m = (support > 0.5) if support.dtype != bool else support
    if dilate_px > 0:
        k = np.ones((2 * dilate_px + 1, 2 * dilate_px + 1), np.uint8)
        m = cv2.dilate(m.astype(np.uint8), k) > 0
    return edge & m


def gated_dt(edge, support, dilate_px=2):
    """DT of the gated edge set. Surviving Canny pixels keep DT == 0 exactly."""
    ge = gate_edges(edge, support, dilate_px)
    if not ge.any():
        return np.full(edge.shape, 1e3, np.float32), ge
    return cv2.distanceTransform((~ge).astype(np.uint8), cv2.DIST_L2, 5), ge
