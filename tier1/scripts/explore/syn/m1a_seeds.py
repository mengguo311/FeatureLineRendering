"""M1a SEED EXTRACTION -- FINAL RECIPE, self-contained and MESH-FREE.

Depends only on src/{common,render,visibility}.py (never mesh_oracle).
Everything else (edge maps, crease-ridge maps, local competition) is inlined here so
it can be lifted straight into src/seeds.py.

INPUTS
  MODE "overall"   gaussian params + rendered G-buffers + training PHOTOGRAPHS
  MODE "puregeom"  gaussian params + rendered G-buffers          (no photographs)
  MODE "shared"    same as "overall"  (adds C_N saliency + opacity; the only variant
                                       that is not harmful on lego)

USAGE
  python m1a_seeds.py chair overall
"""
import os
import sys

import cv2
import numpy as np
import torch
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from scipy.stats import rankdata

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from src import common, render, visibility

# ----------------------------------------------------------------- tuned constants
N_VIEWS   = 25
DP        = 4            # px patch radius for the rendered dihedral / planarity test
TAU_ANG   = 45.0         # deg
TAU_RESID = 0.005        # plane-fit depth residual / z  (C0 test)
GMAG_MIN  = 0.02
SIGMA     = 16.0         # px, soft kernel for the photometric aggregate
EDGE_CFGS = ((2.0, 100, 200), (2.5, 75, 150))   # ~3% edge density
RAD_MULT  = 2.0          # local-competition ball, in median-1NN-spacing units
LAMBDA    = 0.5
KEEP_F    = {"overall": 0.22, "puregeom": 0.28, "shared": 0.42}

_R = lambda v: rankdata(v) / len(v)


# ----------------------------------------------------------------- evidence fields
def photo_edge_dt(rgb_path, cfgs=EDGE_CFGS):
    """DT of a union of blurred-Canny edge maps of one training photograph."""
    im = cv2.imread(rgb_path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:                 # RGBA -> composite on white
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


def crease_ridge_dt(normal, depth, alpha):
    """DT of the crease-ridge map of one rendered G-buffer.

    ridge pixel  <=>  two-cluster dihedral of the composited normal map over a
    (2*DP+1)^2 patch >= TAU_ANG,  AND  patch depth locally planar (C0 -> rejects
    occluding contours),  AND  patch fully foreground (rejects silhouettes),
    AND  survives NMS across the ridge.
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
        off = np.arange(-DP, DP + 1)
        ou, ov = np.meshgrid(off, off, indexing="xy")
        ou = ou.ravel().astype(np.float32); ov = ov.ravel().astype(np.float32)
        pu = np.clip(cx[:, None] + ou[None].astype(np.int64), 0, Wd - 1)
        pv = np.clip(cy[:, None] + ov[None].astype(np.int64), 0, Hh - 1)
        pn = nrm[pv, pu]; pf = fg[pv, pu]; pz = dep[pv, pu]
        w = pf.astype(np.float32); cnt = np.maximum(w.sum(1), 1.0)
        du = np.broadcast_to(ou[None], pu.shape); dv = np.broadcast_to(ov[None], pu.shape)

        # --- C0 test: weighted plane fit of the patch depth, max residual / z
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

        # --- two-cluster dihedral of the composited (camera-oriented) normals
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

    # --- NMS across the ridge (principal dir of the normal-gradient structure tensor)
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
    ridge = nms & fg & (Rmap < TAU_RESID) & (Fmap >= 0.999) & (Amap >= TAU_ANG)
    return cv2.distanceTransform((~ridge).astype(np.uint8), cv2.DIST_L2, 5)


# ----------------------------------------------------------------- structure tensor
def structure_tensor_cn(X, n, k):
    tree = cKDTree(X)
    _, knn = tree.query(X, k=k + 1, workers=-1)
    knn = knn[:, 1:]
    nj = n[knn]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, n)); sg[sg == 0] = 1.0
    nj = nj * sg[..., None]
    dn = nj - nj.mean(1, keepdims=True)
    w = np.linalg.eigvalsh(np.einsum("nkc,nkd->ncd", dn, dn) / k)
    return w[:, 2] - w[:, 1], w[:, 1] - w[:, 0]          # s_crease, s_corner


def local_rank(X, s, rad_mult=RAD_MULT):
    """Fraction of gaussians within rad_mult * median-1NN-spacing that this one beats.
    The evidence fields are REGIONAL (they cannot resolve the 2.5 px gate tolerance);
    comparing members of one cluster that straddles a crease can."""
    tree = cKDTree(X)
    sp = np.median(tree.query(X, k=2, workers=-1)[0][:, 1])
    balls = tree.query_ball_point(X, r=rad_mult * sp, workers=-1)
    return np.array([np.mean(s[np.asarray(b)] < s[i]) if len(b) > 1 else 1.0
                     for i, b in enumerate(balls)])


# ----------------------------------------------------------------- the recipe
def extract_seeds(scene, mode="overall", keep_f=None, n_views=N_VIEWS):
    """Returns (seed_positions[K,3], score[M], keep[M], X[M,3])."""
    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)

    # POOL = ALL de-floatered gaussians.  The C_N structure-tensor pool is deliberately
    # NOT used: measured, it costs precision because it burns the recall headroom.
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep_g]
    Nn = g["normal"][keep_g]
    opa = g["opacity"][keep_g]
    M = len(X)

    views = np.unique(np.round(np.linspace(0, len(cams) - 1, n_views)).astype(int))
    DPh = np.zeros((len(views), M), np.float32)
    DR = np.zeros((len(views), M), np.float32)
    VIS = np.zeros((len(views), M), bool)
    need_photo = mode in ("overall", "shared")
    for vi, v in enumerate(views):
        cam = cams[v]
        gb = render.render_gbuffer(g, keep_g, cam)
        dep = gb["depth"].cpu().numpy().astype(np.float32)
        nrm = gb["normal"].cpu().numpy()
        alp = gb["alpha"].cpu().numpy()
        vm, uv, _ = visibility.visible_mask(X, cam, gb["depth"])
        del gb
        torch.cuda.empty_cache()
        u = np.round(uv[:, 0]).astype(np.int64); w = np.round(uv[:, 1]).astype(np.int64)
        VIS[vi] = vm & (u >= 0) & (u < cam.W) & (w >= 0) & (w < cam.H)
        uu = np.clip(uv[:, 0], 0, cam.W - 1); ww = np.clip(uv[:, 1], 0, cam.H - 1)
        if need_photo:
            DPh[vi] = map_coordinates(photo_edge_dt(rgb_paths[v]), [ww, uu],
                                      order=1, mode="nearest")
        DR[vi] = map_coordinates(crease_ridge_dt(nrm, dep, alp), [ww, uu],
                                 order=1, mode="nearest")

    nv = np.maximum(VIS.sum(0), 1)
    never = VIS.sum(0) == 0

    def fix(a):
        a = np.asarray(a, float)
        if never.any() and (~never).any():
            a[never] = np.nanmin(a[~never]) - 1.0
        return np.nan_to_num(a, nan=-1e9)

    with np.errstate(all="ignore"):
        photo = fix(np.where(VIS, np.exp(-DPh / SIGMA), 0.0).sum(0) / nv)
        rq90 = fix(-np.nanpercentile(np.where(VIS, DR, np.nan), 90, axis=0))
        rfr8 = fix((VIS & (DR <= 8)).sum(0) / nv)

    if mode == "overall":
        s = _R(photo) + 0.5 * _R(rq90)
        s = s + LAMBDA * local_rank(X, s)
    elif mode == "puregeom":
        s = _R(rq90) + 0.5 * _R(opa) + 0.25 * _R(rfr8)
    elif mode == "shared":
        s_cr, s_co = structure_tensor_cn(X, Nn, 8)
        s = (_R(photo) + 0.5 * _R(rq90) + 1.0 * _R(s_co) +
             0.5 * _R(s_cr) + 1.0 * _R(opa))
    else:
        raise ValueError(mode)

    f = KEEP_F[mode] if keep_f is None else keep_f
    keep = np.zeros(M, bool)
    keep[np.argsort(-s, kind="stable")[:int(round(f * M))]] = True
    return X[keep], s, keep, X


if __name__ == "__main__":
    scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
    mode = sys.argv[2] if len(sys.argv) > 2 else "overall"
    import time
    t0 = time.time()
    P, s, keep, X = extract_seeds(scene, mode)
    print(f"[{scene}/{mode}] {len(X)} gaussians -> {len(P)} seeds  ({time.time()-t0:.0f}s)")
    # ---- EVAL ONLY below this line ----
    sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
    from tune_lib import Harness
    h = Harness(scene)
    print("  gate: %.4f / %.4f / n=%d" % h.evaluate(X, extra_mask=keep))
    ps, rs, ns = h.evaluate(X, extra_mask=keep, per_view=True)
    print("  per-view: " + "  ".join(f"v{v}: p={a:.4f} r={b:.4f} n={c}"
                                     for v, a, b, c in zip(h.views, ps, rs, ns)))
