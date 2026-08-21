"""tier1/src/evidence.py — multi-view seed evidence scoring (METHOD PATH, mesh-free).

Consumes ONLY the gaussians, the rendered G-buffer (render.py), the gaussian z-buffer
visibility (visibility.py) and — optionally — the training photographs via the Canny DT
cache (dt_field.py). It NEVER imports mesh_oracle and never touches the GT mesh.

WHY THIS MODULE EXISTS
    The object-space normal-structure-tensor C_N in seeds.py is, on vanilla 3DGS,
    close to chance at telling a real crease gaussian from any other gaussian
    (measured on chair: AUC 0.54; ranking every de-floatered gaussian at random gives
    33.9% seed precision, the full C_N pipeline gives 35.2%). The per-gaussian normal
    is the shortest covariance axis, which is noise-dominated for the near-isotropic
    splats that dominate a vanilla reconstruction.

    What DOES carry signal is multi-view consistency of *rendered* geometry: a real
    crease shows a normal discontinuity, from every viewpoint, across a surface that
    stays depth-continuous (C0). An occluding contour is depth-DIScontinuous and slides
    over the object as the camera moves; a texture edge has no normal discontinuity.

    Measured on chair (all de-floatered gaussians, views 0+25 gate):
        C_N seeds only ............ precision 0.352  recall 0.883
        + ridge evidence (geom) ... precision 0.693  recall 0.723
        + photometric DT (fused) .. precision 0.773  recall 0.727
    See scripts/verify_m1a.py --rank and the M1a report for the full analysis, and for
    why 0.80 is NOT reachable by ranking of any kind (the 2.5px tolerance is smaller
    than one gaussian splat, so it is a refinement problem, which M1b's DT pull owns).

CROSS-SCENE CAVEAT (measured, important)
    Neither evidence term transfers to lego: the photometric term is at chance there
    (AUC 0.46 — lego is texture-rich so the Canny density argument inverts) and the
    ridge term is mildly anti-predictive (AUC 0.44 — lego is so crease-dense that
    ~72% of all gaussians are already within tolerance, leaving nothing to rank).
    Ranking is therefore OFF by default; enable it deliberately per scene.
"""
import cv2
import numpy as np

from . import render, visibility

# defaults swept on chair; see the module docstring
DP = 4              # patch radius (px) for the dihedral / planarity estimate
TAU_ANG = 45.0      # dihedral threshold (deg) on the rendered normal map
TAU_RESID = 0.005   # max plane-fit depth residual / z  (C0 test: kills depth steps)
SIGMA = 16.0        # px, soft kernel for aggregating distance-to-ridge over views
GMAG_MIN = 0.02     # cheap pre-filter on normal-gradient magnitude


def crease_ridge_map(gbuf, dp=DP, tau_ang=TAU_ANG, tau_resid=TAU_RESID,
                     gmag_min=GMAG_MIN, require_interior=True):
    """Per-view crease-ridge mask from a gaussian G-buffer. Returns bool [H,W].

    A pixel is on the ridge iff, over a (2*dp+1)^2 patch of the alpha-composited
    normal map: (1) the two-cluster dihedral angle >= tau_ang (the same quantity the
    GT oracle thresholds, but measured from gaussians), (2) the patch depth is
    locally planar (weighted plane-fit residual / z < tau_resid) so occluding
    contours and depth steps are rejected, (3) the patch contains no background, and
    (4) the angle survives non-maximum suppression across the ridge.
    """
    dep = gbuf["depth"].detach().cpu().numpy().astype(np.float32)
    nrm = gbuf["normal"].detach().cpu().numpy().astype(np.float32)
    alpha = gbuf["alpha"].detach().cpu().numpy().astype(np.float32)
    H, W = dep.shape
    fg = (alpha > 0.5) & np.isfinite(dep)
    dep0 = np.where(fg, dep, 0.0).astype(np.float32)

    gy, gx = np.gradient(nrm, axis=(0, 1))
    gmag = np.sqrt((gx ** 2).sum(-1) + (gy ** 2).sum(-1)).astype(np.float32)

    Amap = np.zeros((H, W), np.float32)
    Rmap = np.full((H, W), 1e9, np.float32)
    Fmap = np.zeros((H, W), np.float32)

    cy, cx = np.nonzero(fg & (gmag > gmag_min))
    if len(cy):
        off = np.arange(-dp, dp + 1)
        ou, ov = np.meshgrid(off, off, indexing="xy")
        ou = ou.ravel().astype(np.float32)
        ov = ov.ravel().astype(np.float32)
        pu = np.clip(cx[:, None] + ou[None].astype(np.int64), 0, W - 1)
        pv = np.clip(cy[:, None] + ov[None].astype(np.int64), 0, H - 1)
        pn = nrm[pv, pu]
        pf = fg[pv, pu]
        pz = dep0[pv, pu]
        w = pf.astype(np.float32)
        cnt = np.maximum(w.sum(1), 1.0)
        du = np.broadcast_to(ou[None], pu.shape)
        dv = np.broadcast_to(ov[None], pu.shape)
        Fmap[cy, cx] = w.mean(1)

        # weighted plane fit of patch depth -> max residual / z  (C0 test)
        Sw = w.sum(1); Su = (w * du).sum(1); Sv = (w * dv).sum(1)
        Suu = (w * du * du).sum(1); Svv = (w * dv * dv).sum(1); Suv = (w * du * dv).sum(1)
        bz = (w * pz).sum(1); buz = (w * du * pz).sum(1); bvz = (w * dv * pz).sum(1)
        ok = Sw >= 6
        if ok.any():
            M = np.empty((int(ok.sum()), 3, 3), np.float64)
            M[:, 0, 0] = Sw[ok]; M[:, 0, 1] = Su[ok]; M[:, 0, 2] = Sv[ok]
            M[:, 1, 0] = Su[ok]; M[:, 1, 1] = Suu[ok]; M[:, 1, 2] = Suv[ok]
            M[:, 2, 0] = Sv[ok]; M[:, 2, 1] = Suv[ok]; M[:, 2, 2] = Svv[ok]
            M[:, 0, 0] += 1e-3; M[:, 1, 1] += 1e-3; M[:, 2, 2] += 1e-3
            abc = np.linalg.solve(M, np.stack([bz[ok], buz[ok], bvz[ok]], 1)).astype(np.float32)
            pred = abc[:, 0:1] + abc[:, 1:2] * du[ok] + abc[:, 2:3] * dv[ok]
            Rmap[cy[ok], cx[ok]] = ((np.abs(pz[ok] - pred) * w[ok]).max(1)
                                    / np.maximum(dep[cy[ok], cx[ok]], 1e-9))

        # two-cluster dihedral of the camera-oriented composited normals
        nb = np.matmul(w[:, None, :], pn)[:, 0] / cnt[:, None]
        dn = pn - nb[:, None]
        dnw = dn * w[..., None]
        C = np.matmul(dnw.transpose(0, 2, 1), dn) / cnt[:, None, None]
        _, V = np.linalg.eigh(C)
        t = np.matmul(dn, V[:, :, 2][:, :, None])[:, :, 0]
        A_ = ((t > 0) & pf).astype(np.float32)
        B_ = ((t < 0) & pf).astype(np.float32)
        nA, nB = A_.sum(1), B_.sum(1)
        mA = np.matmul(A_[:, None, :], pn)[:, 0] / np.maximum(nA, 1)[:, None]
        mB = np.matmul(B_[:, None, :], pn)[:, 0] / np.maximum(nB, 1)[:, None]
        mA /= np.linalg.norm(mA, axis=1, keepdims=True) + 1e-12
        mB /= np.linalg.norm(mB, axis=1, keepdims=True) + 1e-12
        a = np.degrees(np.arccos(np.clip((mA * mB).sum(1), -1, 1)))
        a[(nA == 0) | (nB == 0)] = 0.0
        Amap[cy, cx] = a

    # NMS across the ridge, along the principal normal-gradient direction
    Jxx = (gx * gx).sum(-1); Jyy = (gy * gy).sum(-1); Jxy = (gx * gy).sum(-1)
    tr = Jxx + Jyy
    lam = tr / 2 + np.sqrt(np.maximum(tr * tr / 4 - (Jxx * Jyy - Jxy * Jxy), 0))
    dx, dy = lam - Jyy, Jxy
    nn = np.sqrt(dx * dx + dy * dy)
    flat = nn < 1e-12
    dx = np.where(flat, 1.0, dx / np.maximum(nn, 1e-12)).astype(np.float32)
    dy = np.where(flat, 0.0, dy / np.maximum(nn, 1e-12)).astype(np.float32)
    gxg, gyg = np.meshgrid(np.arange(W, dtype=np.float32),
                           np.arange(H, dtype=np.float32), indexing="xy")
    nms = np.ones((H, W), bool)
    for s in (1.0, -1.0):
        nms &= Amap >= cv2.remap(Amap, np.clip(gxg + s * dx, 0, W - 1),
                                 np.clip(gyg + s * dy, 0, H - 1),
                                 cv2.INTER_LINEAR) - 1e-6

    gate = nms & fg & (Rmap < tau_resid) & (Amap >= tau_ang)
    if require_interior:
        gate &= Fmap >= 0.999
    return gate


def score_seeds(g, keep_mask, cams, P, views, dt_maps=None, sigma=SIGMA,
                device="cuda", **ridge_kw):
    """Multi-view evidence score for seed points P[M,3]. Mesh-free.

    Returns dict with 'ridge' [M] (soft distance-to-crease-ridge evidence),
    'photo' [M] or None (negated mean Canny-DT over visible views), 'n_vis' [M].
    Both are aggregated only over views where the gaussian z-buffer says P is visible.
    """
    M = len(P)
    ridge = np.zeros(M)
    photo = np.zeros(M) if dt_maps is not None else None
    nvis = np.zeros(M)
    for v in views:
        cam = cams[v]
        gbuf = render.render_gbuffer(g, keep_mask, cam, device=device)
        gate = crease_ridge_map(gbuf, **ridge_kw)
        dt = cv2.distanceTransform((~gate).astype(np.uint8), cv2.DIST_L2, 5)
        vis, uv, _ = visibility.visible_mask(P, cam, gbuf["depth"])
        idx = np.where(vis)[0]
        if not len(idx):
            continue
        u = np.clip(np.round(uv[idx, 0]).astype(np.int64), 0, cam.W - 1)
        w_ = np.clip(np.round(uv[idx, 1]).astype(np.int64), 0, cam.H - 1)
        ridge[idx] += np.exp(-dt[w_, u] / sigma)
        if photo is not None:
            photo[idx] -= dt_maps[v].astype(np.float32)[w_, u]
        nvis[idx] += 1
    n = np.maximum(nvis, 1)
    out = {"ridge": ridge / n, "n_vis": nvis}
    out["photo"] = (photo / n) if photo is not None else None
    return out


def rank01(s):
    """Map a score to its normalised rank in [0,1] (robust to scale/outliers)."""
    r = np.empty(len(s), np.float64)
    r[np.argsort(s)] = np.arange(len(s))
    return r / max(len(s) - 1, 1)


def local_competition(P, s, tree=None, radius_mult=2.0):
    """Fraction of gaussians within `radius_mult` x median-1NN-spacing that this
    gaussian outscores. The evidence fields are regional and cannot resolve the
    per-splat tolerance, but a CLUSTER of gaussians straddling a crease can still be
    ranked internally, which recovers some localization. Worth ~+2pp precision on
    chair as an additive term; useless as a standalone score."""
    from scipy.spatial import cKDTree
    tree = tree or cKDTree(P)
    d1, _ = tree.query(P, k=2)
    rad = radius_mult * np.median(d1[:, 1])
    out = np.zeros(len(P))
    for i, nb in enumerate(tree.query_ball_point(P, rad)):
        if len(nb) > 1:
            out[i] = (s[np.asarray(nb)] < s[i]).mean()
    return out
