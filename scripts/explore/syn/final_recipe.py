"""FINAL M1a SEED RECIPE -- self-contained, MESH-FREE.

Two variants, both operating on ALL de-floatered gaussians (the C_N structure-tensor
pool is NOT used -- measured: it costs precision because it burns the recall headroom):

  seeds_puregeom(...)  inputs: gaussian params + rendered G-buffers        (no photographs)
  seeds_overall(...)   inputs: the above + the training RGB photographs

Nothing here imports mesh_oracle or reads the GT mesh.
"""
import numpy as np
import cv2
from scipy.stats import rankdata
from scipy.spatial import cKDTree

# ------------------------------------------------------------------ tuned constants
N_VIEWS   = 25          # spread views used to accumulate evidence
DP        = 4           # patch radius (px) for the rendered dihedral / planarity test
TAU_ANG   = 45.0        # deg, crease threshold on the composited normal map
TAU_RESID = 0.005       # max plane-fit depth residual / z  (C0 test: kills depth steps)
GMAG_MIN  = 0.02
SIGMA     = 16.0        # px, soft kernel for the photometric DT aggregate
EDGE_CFGS = ((2.0, 100, 200), (2.5, 75, 150))   # blurred-Canny union (~3% edge density)
RAD_MULT  = 2.0         # local-competition ball radius, in median-1NN-spacing units
LAMBDA    = 0.5         # weight of the local rank
F_OVERALL = 0.22        # keep-fraction, overall recipe
F_PUREGEOM = 0.28       # keep-fraction, pure-geometry recipe

_R = lambda v: rankdata(v) / len(v)


# ------------------------------------------------------------------ image evidence
def photo_edge_dt(rgb_path, cfgs=EDGE_CFGS):
    """Distance transform of a union of blurred-Canny edge maps. [H,W] float32."""
    im = cv2.imread(rgb_path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:                 # composite RGBA over white
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        bgr = (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    else:
        bgr = im[:, :, :3]
    g0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    e = np.zeros(g0.shape, np.uint8)
    for sig, lo, hi in cfgs:
        g = cv2.GaussianBlur(g0, (0, 0), sig) if sig > 0 else g0
        e |= cv2.Canny(g, lo, hi)
    return cv2.distanceTransform((e == 0).astype(np.uint8), cv2.DIST_L2, 5)


# ------------------------------------------------------------------ G-buffer evidence
def crease_ridge_dt(normal, depth, alpha, dp=DP, tau_ang=TAU_ANG, tau_resid=TAU_RESID):
    """Distance transform of the rendered crease-ridge map.

    A pixel is on the ridge iff (a) the two-cluster dihedral of the alpha-composited
    normal map over a (2dp+1)^2 patch is >= tau_ang, (b) the patch depth is locally
    PLANAR (C0 -- rejects occluding contours / depth steps), (c) the patch does not
    touch background (rejects silhouettes), (d) it survives NMS across the ridge.
    normal[H,W,3], depth[H,W] (inf where empty), alpha[H,W] -- all numpy.
    """
    Hh, Wd = depth.shape
    fg = (alpha > 0.5) & np.isfinite(depth)
    dep = np.where(fg, depth, 0.0).astype(np.float32)
    nrm = normal.astype(np.float32)

    gy, gx = np.gradient(nrm, axis=(0, 1))
    gmag = np.sqrt((gx ** 2).sum(-1) + (gy ** 2).sum(-1)).astype(np.float32)

    Amap = np.zeros((Hh, Wd), np.float32)
    Rmap = np.full((Hh, Wd), 1e9, np.float32)
    Fmap = np.zeros((Hh, Wd), np.float32)
    cy, cx = np.nonzero(fg & (gmag > GMAG_MIN))
    if len(cy):
        off = np.arange(-dp, dp + 1)
        ou, ov = np.meshgrid(off, off, indexing="xy")
        ou = ou.ravel().astype(np.float32); ov = ov.ravel().astype(np.float32)
        pu = np.clip(cx[:, None] + ou[None].astype(np.int64), 0, Wd - 1)
        pv = np.clip(cy[:, None] + ov[None].astype(np.int64), 0, Hh - 1)
        pn = nrm[pv, pu]; pf = fg[pv, pu]; pz = dep[pv, pu]
        w = pf.astype(np.float32); cnt = np.maximum(w.sum(1), 1.0)
        du = np.broadcast_to(ou[None], pu.shape); dv = np.broadcast_to(ov[None], pu.shape)

        Sw = w.sum(1); Su = (w * du).sum(1); Sv = (w * dv).sum(1)
        Suu = (w * du * du).sum(1); Svv = (w * dv * dv).sum(1); Suv = (w * du * dv).sum(1)
        bz = (w * pz).sum(1); buz = (w * du * pz).sum(1); bvz = (w * dv * pz).sum(1)
        Fmap[cy, cx] = w.mean(1)
        ok = Sw >= 6
        if ok.any():
            Mm = np.empty((int(ok.sum()), 3, 3), np.float64)
            Mm[:, 0, 0] = Sw[ok]; Mm[:, 0, 1] = Su[ok]; Mm[:, 0, 2] = Sv[ok]
            Mm[:, 1, 0] = Su[ok]; Mm[:, 1, 1] = Suu[ok]; Mm[:, 1, 2] = Suv[ok]
            Mm[:, 2, 0] = Sv[ok]; Mm[:, 2, 1] = Suv[ok]; Mm[:, 2, 2] = Svv[ok]
            Mm[:, 0, 0] += 1e-3; Mm[:, 1, 1] += 1e-3; Mm[:, 2, 2] += 1e-3
            abc = np.linalg.solve(Mm, np.stack([bz[ok], buz[ok], bvz[ok]], 1)).astype(np.float32)
            pred = abc[:, 0:1] + abc[:, 1:2] * du[ok] + abc[:, 2:3] * dv[ok]
            Rmap[cy[ok], cx[ok]] = ((np.abs(pz[ok] - pred) * w[ok]).max(1) /
                                    np.maximum(depth[cy[ok], cx[ok]], 1e-9))
        nb = np.matmul(w[:, None, :], pn)[:, 0] / cnt[:, None]
        dn = pn - nb[:, None]
        C = np.matmul((dn * w[..., None]).transpose(0, 2, 1), dn) / cnt[:, None, None]
        e1 = np.linalg.eigh(C)[1][:, :, 2]
        t = np.matmul(dn, e1[:, :, None])[:, :, 0]
        A_ = ((t > 0) & pf).astype(np.float32); B_ = ((t < 0) & pf).astype(np.float32)
        nA = A_.sum(1); nB = B_.sum(1)
        mA = np.matmul(A_[:, None, :], pn)[:, 0] / np.maximum(nA, 1)[:, None]
        mB = np.matmul(B_[:, None, :], pn)[:, 0] / np.maximum(nB, 1)[:, None]
        mA /= np.linalg.norm(mA, axis=1, keepdims=True) + 1e-12
        mB /= np.linalg.norm(mB, axis=1, keepdims=True) + 1e-12
        ang = np.degrees(np.arccos(np.clip((mA * mB).sum(1), -1, 1)))
        ang[(nA == 0) | (nB == 0)] = 0.0
        Amap[cy, cx] = ang

    Jxx = (gx * gx).sum(-1); Jyy = (gy * gy).sum(-1); Jxy = (gx * gy).sum(-1)
    tr = Jxx + Jyy; det = Jxx * Jyy - Jxy * Jxy
    lam = tr / 2 + np.sqrt(np.maximum(tr * tr / 4 - det, 0))
    dx = lam - Jyy; dy = Jxy
    nn = np.sqrt(dx * dx + dy * dy); flat = nn < 1e-12
    dx = np.where(flat, 1.0, dx / np.maximum(nn, 1e-12)).astype(np.float32)
    dy = np.where(flat, 0.0, dy / np.maximum(nn, 1e-12)).astype(np.float32)
    gxg, gyg = np.meshgrid(np.arange(Wd, dtype=np.float32),
                           np.arange(Hh, dtype=np.float32), indexing="xy")
    nms = np.ones((Hh, Wd), bool)
    for s in (1.0, -1.0):
        nms &= Amap >= cv2.remap(Amap, np.clip(gxg + s * dx, 0, Wd - 1),
                                 np.clip(gyg + s * dy, 0, Hh - 1),
                                 cv2.INTER_LINEAR) - 1e-6
    ridge = nms & fg & (Rmap < tau_resid) & (Fmap >= 0.999) & (Amap >= tau_ang)
    return cv2.distanceTransform((~ridge).astype(np.uint8), cv2.DIST_L2, 5)


# ------------------------------------------------------------------ local competition
def local_rank(X, s, rad_mult=RAD_MULT):
    """Fraction of gaussians in a ball of rad_mult * median-1NN-spacing that this
    gaussian beats.  The global evidence is REGIONAL (it cannot resolve 2.5 px);
    comparing members of one cluster that straddles the crease can."""
    tree = cKDTree(X)
    sp = np.median(tree.query(X, k=2)[0][:, 1])
    balls = tree.query_ball_point(X, r=rad_mult * sp, workers=-1)
    return np.array([np.mean(s[np.asarray(b)] < s[i]) if len(b) > 1 else 1.0
                     for i, b in enumerate(balls)])


# ------------------------------------------------------------------ the two recipes
def score_from_evidence(X, opa, dt_photo, dt_ridge, vis, mode="overall"):
    """dt_photo/dt_ridge [V,M] float, vis [V,M] bool -> per-gaussian score."""
    nv = np.maximum(vis.sum(0), 1)
    never = vis.sum(0) == 0
    if mode == "overall":
        soft = np.where(vis, np.exp(-dt_photo / SIGMA), 0.0).sum(0) / nv
        with np.errstate(all="ignore"):
            rq90 = -np.nan_to_num(np.nanpercentile(np.where(vis, dt_ridge, np.nan),
                                                   90, axis=0), nan=1e9)
        soft[never] = soft.min() - 1; rq90[never] = rq90.min() - 1
        g = _R(soft) + 0.5 * _R(rq90)
    else:                                              # pure geometry, no photographs
        with np.errstate(all="ignore"):
            rq90 = -np.nan_to_num(np.nanpercentile(np.where(vis, dt_ridge, np.nan),
                                                   90, axis=0), nan=1e9)
        rq90[never] = rq90.min() - 1
        fr8 = (vis & (dt_ridge <= 8)).sum(0) / nv
        g = _R(rq90) + 0.5 * _R(opa) + 0.25 * _R(fr8)
    if mode == "overall":
        g = g + LAMBDA * local_rank(X, g)
    return g
