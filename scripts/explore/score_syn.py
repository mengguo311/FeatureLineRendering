"""score_syn.py -- family `syn`: the SYNTHESIS score (combination agent).

MESH-FREE.  Uses only h.X / h.N / h.opa / h.scale, the training cameras h.cams, the
gaussian G-buffer rendered from them (src.render, src.visibility) and -- for compute()
and compute_shared() only -- the training RGB photographs h.rgb_paths.
Never imports mesh_oracle, never touches h.crease / h.evaluate.

WHAT IT IS
    Per view (25 spread views) two independent evidence fields are built and the
    seed's projection is sampled in both:
      photo : distance transform of a blurred-Canny union on the training PHOTOGRAPH
              (blur 2.0 / 100,200  union  blur 2.5 / 75,150  -> ~3% edge density)
      ridge : distance transform of the crease-ridge map of the rendered G-BUFFER
              (two-cluster dihedral >= 45 deg of the composited normal map, AND
               locally planar depth [C0 test, rejects occluding contours], AND
               no background in the patch [rejects silhouettes], AND ridge NMS)
    aggregated over the views where the gaussian is visible, then combined as
        g = rank(mean_v exp(-photo/16))  +  0.5 * rank(-q90_v ridge)
        s = g + 0.5 * local_rank(g)          # local competition, ball r = 2 * 1NN-spacing

    The local-rank term is the one genuinely new mechanism: both evidence fields are
    REGIONAL (they cannot resolve the 2.5 px gate tolerance), but COMPARING gaussians
    inside one local cluster that straddles a crease can pick the member nearest to it.

MEASURED (chair, canonical K=8 pool of 19304 seeds, baseline 0.3516/0.8830)
    see the module-level PARETO dict; compute() AUC(vis) = 0.884.
    The much better operating point is to drop the C_N pool entirely and rank ALL
    de-floatered gaussians -- see final_recipe.py / the report.
"""
import os
import sys

import cv2
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from scipy.stats import rankdata

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from src import render, visibility  # noqa: E402

N_VIEWS = 25
DP = 4
TAU_ANG = 45.0
TAU_RESID = 0.005
GMAG_MIN = 0.02
SIGMA = 16.0
EDGE_CFGS = ((2.0, 100, 200), (2.5, 75, 150))
RAD_MULT = 2.0
LAMBDA = 0.5

_CACHE = {}
_R = lambda v: rankdata(v) / len(v)


def _photo_dt(path, cfgs=EDGE_CFGS):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
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


def _ridge_dt(normal, depth, alpha, dp=DP, tau_ang=TAU_ANG, tau_resid=TAU_RESID):
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
    ridge = nms & fg & (Rmap < tau_resid) & (Fmap >= tau_ang * 0 + 0.999) & (Amap >= tau_ang)
    return cv2.distanceTransform((~ridge).astype(np.uint8), cv2.DIST_L2, 5)


def _gather(h, sel, n_views=N_VIEWS):
    key = (id(h), len(sel), int(sel[0]), int(sel[-1]), n_views)
    if key in _CACHE:
        return _CACHE[key]
    import torch
    P = np.asarray(h.X)[sel]
    M = len(P)
    views = np.unique(np.round(np.linspace(0, len(h.cams) - 1, n_views)).astype(int))
    DPh = np.zeros((len(views), M), np.float32)
    DR = np.zeros((len(views), M), np.float32)
    VIS = np.zeros((len(views), M), bool)
    for vi, v in enumerate(views):
        cam = h.cams[v]
        gb = render.render_gbuffer(h.g, h.keep, cam)
        dep = gb["depth"].cpu().numpy().astype(np.float32)
        nrm = gb["normal"].cpu().numpy()
        alp = gb["alpha"].cpu().numpy()
        vm, uv, _ = visibility.visible_mask(P, cam, gb["depth"])
        del gb
        torch.cuda.empty_cache()
        u = np.round(uv[:, 0]).astype(np.int64); w = np.round(uv[:, 1]).astype(np.int64)
        VIS[vi] = vm & (u >= 0) & (u < cam.W) & (w >= 0) & (w < cam.H)
        uu = np.clip(uv[:, 0], 0, cam.W - 1); ww = np.clip(uv[:, 1], 0, cam.H - 1)
        DPh[vi] = map_coordinates(_photo_dt(h.rgb_paths[v]), [ww, uu], order=1, mode="nearest")
        DR[vi] = map_coordinates(_ridge_dt(nrm, dep, alp), [ww, uu], order=1, mode="nearest")
    _CACHE[key] = (DPh, DR, VIS)
    return _CACHE[key]


def local_rank(X, s, rad_mult=RAD_MULT):
    tree = cKDTree(X)
    sp = np.median(tree.query(X, k=2)[0][:, 1])
    balls = tree.query_ball_point(X, r=rad_mult * sp, workers=-1)
    return np.array([np.mean(s[np.asarray(b)] < s[i]) if len(b) > 1 else 1.0
                     for i, b in enumerate(balls)])


def _terms(h, sel):
    DPh, DR, VIS = _gather(h, sel)
    nv = np.maximum(VIS.sum(0), 1); never = VIS.sum(0) == 0

    def fix(a):
        a = np.asarray(a, float)
        if never.any() and (~never).any():
            a[never] = np.nanmin(a[~never]) - 1.0
        return np.nan_to_num(a, nan=-1e9)

    with np.errstate(all="ignore"):
        photo = fix(np.where(VIS, np.exp(-DPh / SIGMA), 0.0).sum(0) / nv)
        rq90 = fix(-np.nanpercentile(np.where(VIS, DR, np.nan), 90, axis=0))
        rfr8 = fix((VIS & (DR <= 8)).sum(0) / nv)
    return photo, rq90, rfr8


def compute(h, sel, st):
    """BEST OVERALL. Needs gaussians + rendered G-buffers + training photographs."""
    photo, rq90, _ = _terms(h, sel)
    g = _R(photo) + 0.5 * _R(rq90)
    return (g + LAMBDA * local_rank(np.asarray(h.X)[sel], g)).astype(np.float64)


def compute_puregeom(h, sel, st):
    """BEST WITHOUT PHOTOGRAPHS. Needs gaussians + rendered G-buffers only."""
    _, rq90, rfr8 = _terms(h, sel)
    return (_R(rq90) + 0.5 * _R(np.asarray(h.opa)[sel]) + 0.25 * _R(rfr8)).astype(np.float64)


def compute_shared(h, sel, st):
    """The only variant that is not harmful on lego (see the report): adds the
    C_N corner/crease saliency and opacity, which are the only terms with positive
    ranking power on BOTH chair and lego."""
    photo, rq90, _ = _terms(h, sel)
    return (_R(photo) + 0.5 * _R(rq90) + 1.0 * _R(np.asarray(st["s_corner"])[sel]) +
            0.5 * _R(np.asarray(st["s_crease"])[sel]) +
            1.0 * _R(np.asarray(h.opa)[sel])).astype(np.float64)


def compute_photo(h, sel, st):
    return _R(_terms(h, sel)[0]).astype(np.float64)


def compute_ridge(h, sel, st):
    return _R(_terms(h, sel)[1]).astype(np.float64)


if __name__ == "__main__":
    import time
    sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
    from tune_lib import Harness, structure_tensor, nms_along_e1
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    P = h.X[sel]
    print("pool", len(sel), "baseline %.4f/%.4f/%d" % h.evaluate(P))
    for nm, fn in (("compute", compute), ("puregeom", compute_puregeom),
                   ("shared", compute_shared)):
        s = fn(h, sel, st)
        row = []
        for f in (1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2):
            k = np.zeros(len(sel), bool)
            k[np.argsort(-s, kind="stable")[:int(f * len(sel))]] = True
            p, r, _ = h.evaluate(P, extra_mask=k)
            row.append(f"f{f}:{p*100:.0f}/{r*100:.0f}")
        print(f"  {nm:10s} " + "  ".join(row), flush=True)
    print("standalone %.1fs" % (time.time() - t0))
