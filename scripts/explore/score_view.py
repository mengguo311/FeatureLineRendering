"""score_view.py -- family "view": view-dependent geometric consistency.

MESH-FREE. Uses only: gaussian centers/normals (h.X, h.N, h.g, h.keep), the training
cameras (h.cams) and the gaussian G-buffer rendered from them (src.render). It never
imports mesh_oracle and never touches h.crease.

IDEA
----
A gaussian flagged as a crease by the object-space normal-structure-tensor C_N may be
near a *rendered* normal discontinuity for two very different reasons:
  (a) it is a genuine crease  -> the surface is C0-continuous across the discontinuity
      and the discontinuity is anchored to the object, so it reappears in EVERY view;
  (b) it is on an occluding contour / silhouette -> the surface is C0-DIScontinuous
      there, and the contour slides over the object as the camera moves.
So per view we build a *crease-ridge map*: pixels where
    (1) the alpha-composited G-buffer normal map has a two-cluster dihedral >= TAU_ANG
        (measured exactly the way the oracle defines a crease: angle between the two
        face normals), AND
    (2) the depth is locally PLANAR (max residual of a weighted plane fit to the patch
        depth, relative to z, below TAU_RESID)  -> C0 test, kills depth steps, AND
    (3) the patch does not touch background     -> kills silhouettes,
    (4) after non-maximum suppression across the ridge (1-px thin).
Each seed is then scored by how close its projection lands to that map, aggregated over
all views in which the seed is visible.

Why the alpha-composited normal map and not the raw per-gaussian normals: the
per-gaussian normal (shortest covariance axis) is very noisy -- see
compute_dihedral3d() below, which implements the object-space version of the same
dihedral test and is close to useless on this scene (AUC 0.58).

compute()  -> the best single score (soft aggregation, TAU_ANG=45)
Other exposed scores: compute_negmed, compute_ensemble, compute_dihedral3d.
"""
import numpy as np
import cv2

import sys, os
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from src import render, visibility

# --- defaults (swept on scene "chair"; see module docstring of the report) -----------
DP = 4                 # patch radius in px for the dihedral / planarity estimate
TAU_ANG = 45.0         # dihedral threshold (deg) on the rendered normal map
TAU_RESID = 0.005      # max plane-fit depth residual / z  (C0 / depth-step test)
SIGMA = 16.0           # px, soft kernel for aggregating distance-to-ridge over views
GMAG_MIN = 0.02        # cheap pre-filter: only pixels with this much normal gradient
                       # can ever reach TAU_ANG (verified: no change in AUC).
PSTRIDE = 1            # patch sampling stride. 1 = full (2*DP+1)^2 taps, 65 s for 49
                       # views. Setting it to 2 halves the runtime (33 s) at a small
                       # cost (precision at f=0.3: 0.723 -> 0.704).
# Views used for the multi-view vote. Excludes the two M1a gate views (0, 25) so that
# the score is never evaluated on the same views it was computed from. A deployment
# may simply use range(len(h.cams)).
DEFAULT_VIEWS = [v for v in range(0, 100, 2) if v not in (0, 25)]

_CACHE = {}


# ------------------------------------------------------------------ per-view maps ---
def _view_maps(h, cam, dp=DP):
    """Render the G-buffer and return (crease-ridge inputs) for one camera.
    Returns Amap (deg), Rmap (plane residual / z), Fmap (patch fg fraction),
    nms (bool), fg (bool), depth tensor."""
    Hh, Wd = cam.H, cam.W
    gb = render.render_gbuffer(h.g, h.keep, cam)
    dep_t = gb["depth"]
    alpha = gb["alpha"].cpu().numpy()
    nrm = gb["normal"].cpu().numpy().astype(np.float32)
    dep = dep_t.cpu().numpy().astype(np.float32)
    fg = (alpha > 0.5) & np.isfinite(dep)
    dep0 = np.where(fg, dep, 0.0).astype(np.float32)

    gy, gx = np.gradient(nrm, axis=(0, 1))
    gmag = np.sqrt((gx ** 2).sum(-1) + (gy ** 2).sum(-1)).astype(np.float32)

    Amap = np.zeros((Hh, Wd), np.float32)
    Rmap = np.full((Hh, Wd), 1e9, np.float32)
    Fmap = np.zeros((Hh, Wd), np.float32)

    cy, cx = np.nonzero(fg & (gmag > GMAG_MIN))
    if len(cy):
        off = np.arange(-dp, dp + 1, PSTRIDE)
        ou, ov = np.meshgrid(off, off, indexing="xy")
        ou = ou.ravel().astype(np.float32)
        ov = ov.ravel().astype(np.float32)
        pu = np.clip(cx[:, None] + ou[None].astype(np.int64), 0, Wd - 1)
        pv = np.clip(cy[:, None] + ov[None].astype(np.int64), 0, Hh - 1)
        pn = nrm[pv, pu]
        pf = fg[pv, pu]
        pz = dep0[pv, pu]
        w = pf.astype(np.float32)
        cnt = np.maximum(w.sum(1), 1.0)
        du = np.broadcast_to(ou[None], pu.shape)
        dv = np.broadcast_to(ov[None], pu.shape)

        # weighted plane fit of depth over the patch -> max residual / z (C0 test)
        Sw = w.sum(1); Su = (w * du).sum(1); Sv = (w * dv).sum(1)
        Suu = (w * du * du).sum(1); Svv = (w * dv * dv).sum(1); Suv = (w * du * dv).sum(1)
        bz = (w * pz).sum(1); buz = (w * du * pz).sum(1); bvz = (w * dv * pz).sum(1)
        Fmap[cy, cx] = w.mean(1)
        # a patch with too few foreground taps is a silhouette: leave Rmap = 1e9
        ok = Sw >= 6
        if ok.any():
            Mm = np.empty((int(ok.sum()), 3, 3), np.float64)
            Mm[:, 0, 0] = Sw[ok]; Mm[:, 0, 1] = Su[ok]; Mm[:, 0, 2] = Sv[ok]
            Mm[:, 1, 0] = Su[ok]; Mm[:, 1, 1] = Suu[ok]; Mm[:, 1, 2] = Suv[ok]
            Mm[:, 2, 0] = Sv[ok]; Mm[:, 2, 1] = Suv[ok]; Mm[:, 2, 2] = Svv[ok]
            Mm[:, 0, 0] += 1e-3; Mm[:, 1, 1] += 1e-3; Mm[:, 2, 2] += 1e-3
            abc = np.linalg.solve(Mm, np.stack([bz[ok], buz[ok], bvz[ok]], 1)
                                  ).astype(np.float32)
            pred = abc[:, 0:1] + abc[:, 1:2] * du[ok] + abc[:, 2:3] * dv[ok]
            r = (np.abs(pz[ok] - pred) * w[ok]).max(1) / np.maximum(dep[cy[ok], cx[ok]], 1e-9)
            Rmap[cy[ok], cx[ok]] = r

        # two-cluster dihedral of the (camera-oriented) composited normals
        nb = np.matmul(w[:, None, :], pn)[:, 0] / cnt[:, None]
        dn = pn - nb[:, None]
        dnw = dn * w[..., None]
        C = np.matmul(dnw.transpose(0, 2, 1), dn) / cnt[:, None, None]
        _, V = np.linalg.eigh(C)
        e1 = V[:, :, 2]
        t = np.matmul(dn, e1[:, :, None])[:, :, 0]
        A_ = ((t > 0) & pf).astype(np.float32)
        B_ = ((t < 0) & pf).astype(np.float32)
        nA = A_.sum(1)
        nB = B_.sum(1)
        mA = np.matmul(A_[:, None, :], pn)[:, 0] / np.maximum(nA, 1)[:, None]
        mB = np.matmul(B_[:, None, :], pn)[:, 0] / np.maximum(nB, 1)[:, None]
        mA /= np.linalg.norm(mA, axis=1, keepdims=True) + 1e-12
        mB /= np.linalg.norm(mB, axis=1, keepdims=True) + 1e-12
        a = np.degrees(np.arccos(np.clip((mA * mB).sum(1), -1, 1)))
        a[(nA == 0) | (nB == 0)] = 0.0
        Amap[cy, cx] = a

    # NMS across the ridge (principal direction of the normal-gradient structure tensor)
    Jxx = (gx * gx).sum(-1); Jyy = (gy * gy).sum(-1); Jxy = (gx * gy).sum(-1)
    tr = Jxx + Jyy
    det = Jxx * Jyy - Jxy * Jxy
    lam = tr / 2 + np.sqrt(np.maximum(tr * tr / 4 - det, 0))
    dx = lam - Jyy; dy = Jxy
    nn = np.sqrt(dx * dx + dy * dy)
    flat = nn < 1e-12
    dx = np.where(flat, 1.0, dx / np.maximum(nn, 1e-12)).astype(np.float32)
    dy = np.where(flat, 0.0, dy / np.maximum(nn, 1e-12)).astype(np.float32)
    gxg, gyg = np.meshgrid(np.arange(Wd, dtype=np.float32),
                           np.arange(Hh, dtype=np.float32), indexing="xy")
    nms = np.ones((Hh, Wd), bool)
    for s in (1.0, -1.0):
        sx = np.clip(gxg + s * dx, 0, Wd - 1)
        sy = np.clip(gyg + s * dy, 0, Hh - 1)
        nms &= Amap >= cv2.remap(Amap, sx, sy, cv2.INTER_LINEAR) - 1e-6
    return Amap, Rmap, Fmap, nms, fg, dep_t


def _collect(h, sel, views=None, taus=(TAU_ANG,), dp=DP,
             tau_resid=TAU_RESID, need_fg=True):
    """Per-seed x per-view distance to the crease-ridge map, for each tau in taus.
    Returns (dist[len(taus), V, M] float32, vis[V, M] bool)."""
    views = list(DEFAULT_VIEWS if views is None else views)
    key = (id(h), tuple(sel[:8]), len(sel), tuple(views), tuple(taus), dp,
           tau_resid, need_fg)
    if key in _CACHE:
        return _CACHE[key]
    P = h.X[sel]
    M = len(P)
    dist = np.zeros((len(taus), len(views), M), np.float32)
    vis = np.zeros((len(views), M), bool)
    for vi, v in enumerate(views):
        cam = h.cams[v]
        Amap, Rmap, Fmap, nms, fg, dep_t = _view_maps(h, cam, dp)
        vism, uv, _ = visibility.visible_mask(P, cam, dep_t)
        vis[vi] = vism
        idx = np.where(vism)[0]
        if len(idx) == 0:
            continue
        su = np.clip(np.round(uv[idx, 0]).astype(np.int64), 0, cam.W - 1)
        sv = np.clip(np.round(uv[idx, 1]).astype(np.int64), 0, cam.H - 1)
        gate = nms & fg & (Rmap < tau_resid)
        if need_fg:
            gate &= Fmap >= 0.999
        for ti, ta in enumerate(taus):
            cm = gate & (Amap >= ta)
            dt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
            dist[ti, vi, idx] = dt[sv, su]
    _CACHE[key] = (dist, vis)
    return dist, vis


# ------------------------------------------------------------------------ scores ---
def compute(h, sel, st, views=None):
    """BEST SINGLE SCORE. Higher = more likely a true crease seed. Mesh-free.
    Soft multi-view aggregation of the distance to the depth-step-gated 45-degree
    crease ridge:  s_i = mean_over_visible_views exp(-d_iv / SIGMA)."""
    dist, vis = _collect(h, sel, views, taus=(TAU_ANG,))
    nv = np.maximum(vis.sum(0), 1).astype(np.float64)
    return (np.where(vis, np.exp(-dist[0] / SIGMA), 0.0).sum(0) / nv).astype(np.float64)


def compute_negmed(h, sel, st, views=None):
    """Negated median (over visible views) distance-to-ridge. Sharper, slightly worse."""
    dist, vis = _collect(h, sel, views, taus=(TAU_ANG,))
    d = np.where(vis, dist[0], np.nan)
    with np.errstate(all="ignore"):
        med = np.nanmedian(d, 0)
    return -np.nan_to_num(med, nan=99.0).astype(np.float64)


def compute_ensemble(h, sel, st, views=None):
    """Rank-average over four dihedral thresholds (25/35/45/55 deg) of both the soft
    and the median aggregation. Less threshold-sensitive, ~same AUC as compute()."""
    taus = (25.0, 35.0, 45.0, 55.0)
    dist, vis = _collect(h, sel, views, taus=taus)
    nv = np.maximum(vis.sum(0), 1).astype(np.float64)

    def rk(s):
        o = np.argsort(s, kind="stable")
        r = np.empty(len(s), np.float64)
        r[o] = np.arange(len(s))
        return r / max(len(s) - 1, 1)

    out = np.zeros(len(sel), np.float64)
    for ti in range(len(taus)):
        out += rk(np.where(vis, np.exp(-dist[ti] / 8.0), 0.0).sum(0) / nv)
        d = np.where(vis, dist[ti], np.nan)
        with np.errstate(all="ignore"):
            med = np.nanmedian(d, 0)
        out += rk(-np.nan_to_num(med, nan=99.0))
    return out / (2 * len(taus))


def compute_dihedral3d(h, sel, st, k=32):
    """OBJECT-SPACE dihedral from the raw per-gaussian normals (the 'split the kNN into
    the two clusters implied by e1 and measure the angle between the two mean normals'
    idea), times the cluster balance.  NEGATIVE RESULT on chair: AUC 0.579 -- the
    per-gaussian normal (shortest covariance axis) is far too noisy, the median measured
    'dihedral' is 83 deg for ALL seeds, so the oracle's 30-deg definition cannot be
    applied in object space. Kept for the record / ablation."""
    from scipy.spatial import cKDTree
    X, Nrm = h.X, h.N
    tree = cKDTree(X)
    _, knn = tree.query(X[sel], k=k + 1)
    knn = knn[:, 1:]
    n0 = Nrm[sel]
    nj = Nrm[knn]
    sg = np.sign(np.einsum("mkc,mc->mk", nj, n0))
    sg[sg == 0] = 1.0
    nj = nj * sg[..., None]
    nbar = nj.mean(1, keepdims=True)
    dnj = nj - nbar
    C = np.einsum("mkc,mkd->mcd", dnj, dnj) / k
    _, V = np.linalg.eigh(C)
    e1 = V[:, :, 2]
    t = np.einsum("mkc,mc->mk", dnj, e1)
    A = t > 0
    B = ~A
    nA = A.sum(1).astype(np.float64)
    nB = B.sum(1).astype(np.float64)
    mA = (nj * A[..., None]).sum(1) / np.maximum(nA, 1)[:, None]
    mB = (nj * B[..., None]).sum(1) / np.maximum(nB, 1)[:, None]
    mA /= np.linalg.norm(mA, axis=1, keepdims=True) + 1e-12
    mB /= np.linalg.norm(mB, axis=1, keepdims=True) + 1e-12
    ang = np.degrees(np.arccos(np.clip((mA * mB).sum(1), -1, 1)))
    ang[(nA == 0) | (nB == 0)] = 0.0
    bal = np.minimum(nA, nB) / float(k)
    return (ang * bal).astype(np.float64)


if __name__ == "__main__":
    import time
    sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
    from tune_lib import Harness, structure_tensor, nms_along_e1
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    print("pool", len(sel), "setup %.1fs" % (time.time() - t0))
    t0 = time.time()
    s = compute(h, sel, st)
    print("compute(): %.1fs  score range %.4f..%.4f" % (time.time() - t0, s.min(), s.max()))
    P = h.X[sel]
    print("baseline", h.evaluate(P))
    o = np.argsort(-s, kind="stable")
    for f in (1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2):
        keep = np.zeros(len(sel), bool)
        keep[o[:int(f * len(sel))]] = True
        print("  f=%.2f  prec=%.4f  rec=%.4f  nvis=%d" % ((f,) + h.evaluate(P, extra_mask=keep)))
