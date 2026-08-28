"""FINAL M1a SEED RECIPE -- self-contained, MESH-FREE.

Two variants, both operating on ALL de-floatered gaussians (the C_N structure-tensor
pool is NOT used -- measured: it costs precision because it burns the recall headroom):

  seeds_puregeom(...)  inputs: gaussian params + rendered G-buffers        (no photographs)
  seeds_overall(...)   inputs: the above + the training RGB photographs

Nothing here imports mesh_oracle or reads the GT mesh.
"""
import os

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

# ------------------------------------------------------------------ edge-source switch
# The M1a photometric channel is a distance transform of a 2D edge map.  Which DETECTOR
# produces that edge map is now a flag; everything downstream (the DT, the SIGMA=16 soft
# aggregate, the score, the local competition, f) is untouched.  Default is "canny", so
# importing this module reproduces the published recipe bit-for-bit.
EDGE_SOURCE = "canny"                                    # see SOURCES below
CANNY_CFGS = EDGE_CFGS                                   # which Canny config "canny" means
TEED_CACHE = os.path.expanduser("~/3dgs_line/tier1/out/teed_edges_chair")
TEED_KEY = "native"                                      # "native" | "ms"
TEED_THR = 0.90                                          # raw-sigmoid threshold
TEED_NMS = True                                          # thin before thresholding

# ---- TRACK M (rankability mechanism ablation) knobs.  All default to OFF, so every
# ---- pre-existing source ("canny"/"teed"/"union") is bit-identical to before.
TEED_CC_MINLEN = 0        # M2: drop TEED components with < this many (thinned) px
MASK_DILATE = 2           # M3: px dilation of TEED support before masking Canny
MASK_SHIFT = 0            # M3 CONTROL: translate the TEED support by this many px before
                          # masking.  Keeps the mask's area, shape and spatial statistics
                          # IDENTICAL and destroys only its registration to the image, so a
                          # lift that survives the shift was density reduction, not
                          # selectivity.
# M1: quantisation levels of the CONTINUOUS confidence field.  dt_eff(x) =
# min_y [ d(x,y) + SIGMA * ln(p_ref/p(y)) ], i.e. evidence exp(-dt/SIGMA) becomes
# (p/p_ref)*exp(-d/SIGMA) -- a confidence-WEIGHTED soft distance rather than a step.
SOFT_LEVELS = (0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70,
               0.80, 0.90, 0.95, 0.99)
SOFT_GAMMA = 1.0          # evidence ~ (p/p_ref)^gamma.  1.0 = literal confidence
                          # weighting; ->0 recovers "every NMS ridge px counts equally".
SOURCES = ("canny", "teed", "union",          # published
           "teed_soft",                       # M1  continuous confidence
           "teed_cc",                         # M2  connected-component length filter
           "cannymask",                       # M3  TEED support as a MASK on Canny
           "teed_epi")                        # NG-MEC S1  epipolar-consensus selectivity


def set_edge_source(source="canny", cache=None, key=None, thr=None, nms=None, cfgs=None,
                    cc_minlen=None, mask_dilate=None, soft_gamma=None,
                    mask_shift=None):
    """Set the photometric edge detector used by photo_edge_map/photo_edge_dt.

    `cfgs` re-tunes the CANNY arm itself.  That is the control the TEED claim lives or dies
    on: TRACK A measured that an unblurred permissive Canny recovers 90% of the pixels the
    M1a Canny misses, so "a learned detector was needed" has to be demonstrated against a
    RE-TUNED Canny, not only against the published blurred one.
    """
    global EDGE_SOURCE, TEED_CACHE, TEED_KEY, TEED_THR, TEED_NMS, CANNY_CFGS
    global TEED_CC_MINLEN, MASK_DILATE, SOFT_GAMMA, MASK_SHIFT
    assert source in SOURCES, source
    EDGE_SOURCE = source
    CANNY_CFGS = tuple(cfgs) if cfgs is not None else EDGE_CFGS
    if cache is not None:
        TEED_CACHE = cache
    if key is not None:
        TEED_KEY = key
    if thr is not None:
        TEED_THR = float(thr)
    if nms is not None:
        TEED_NMS = bool(nms)
    # the two TRACK-M knobs are RESET on every call unless explicitly given, so a stale
    # cc_minlen from a previous arm can never silently contaminate the next one.
    TEED_CC_MINLEN = int(cc_minlen) if cc_minlen is not None else 0
    MASK_DILATE = int(mask_dilate) if mask_dilate is not None else 2
    SOFT_GAMMA = float(soft_gamma) if soft_gamma is not None else 1.0
    MASK_SHIFT = int(mask_shift) if mask_shift is not None else 0
    return dict(source=EDGE_SOURCE, cache=TEED_CACHE, key=TEED_KEY,
                thr=TEED_THR, nms=TEED_NMS, cfgs=CANNY_CFGS,
                cc_minlen=TEED_CC_MINLEN, mask_dilate=MASK_DILATE,
                soft_gamma=SOFT_GAMMA, mask_shift=MASK_SHIFT)


def nms_thin(p, blur=1.0):
    """Keep p only where it is a local max along its own gradient (canonical edge NMS).

    A thresholded learned-edge probability map is several px thick; Canny's output is 1 px
    by construction.  Without this the two detectors are not comparable at any fixed pixel
    budget, and the DT built from the thick map is systematically biased inward.
    """
    ps = cv2.GaussianBlur(p, (0, 0), blur) if blur > 0 else p
    gx = cv2.Sobel(ps, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(ps, cv2.CV_32F, 0, 1, ksize=3)
    n = np.sqrt(gx * gx + gy * gy)
    flat = n < 1e-9
    dx = np.where(flat, 1.0, gx / np.maximum(n, 1e-9)).astype(np.float32)
    dy = np.where(flat, 0.0, gy / np.maximum(n, 1e-9)).astype(np.float32)
    Hh, Wd = p.shape
    xs, ys = np.meshgrid(np.arange(Wd, dtype=np.float32),
                         np.arange(Hh, dtype=np.float32), indexing="xy")
    keep = np.ones((Hh, Wd), bool)
    for sgn in (1.0, -1.0):
        q = cv2.remap(p, np.clip(xs + sgn * dx, 0, Wd - 1),
                      np.clip(ys + sgn * dy, 0, Hh - 1), cv2.INTER_LINEAR)
        keep &= p >= q - 1e-6
    return np.where(keep, p, 0.0).astype(np.float32)


def teed_prob(rgb_path):
    """The cached raw-sigmoid TEED probability map, NMS-thinned iff TEED_NMS. [H,W] f32.

    The cache is keyed by the view index, recovered from the file name (`r_<v>.png`, and
    common.load_cameras is verified to enumerate frames in exactly that order)."""
    stem = os.path.splitext(os.path.basename(rgb_path))[0]
    v = int(stem.split("_")[-1])
    z = np.load(os.path.join(TEED_CACHE, f"v{v:03d}.npz"))
    p = z[TEED_KEY].astype(np.float32)
    if TEED_NMS:
        p = nms_thin(p)
    return p


def cc_length_filter(e, min_px):
    """M2: keep only 8-connected components with >= min_px pixels.

    After NMS the map is one px wide, so a component's pixel count IS its arc length in px
    to within the usual digital-curve constant.  This is the 'topological continuity'
    factor: short specks (texture) die, long strokes (contours) live."""
    if min_px <= 0:
        return e
    n, lab, stats, _ = cv2.connectedComponentsWithStats((e > 0).astype(np.uint8), 8)
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_px
    return (keep[lab].astype(np.uint8) * 255)


def teed_edge_map(rgb_path):
    """Binary TEED edge map (thresholded, optionally CC-length-filtered)."""
    p = teed_prob(rgb_path)
    e = ((p >= TEED_THR).astype(np.uint8) * 255)
    return cc_length_filter(e, TEED_CC_MINLEN)


def teed_soft_dt(rgb_path):
    """M1: distance field of the CONTINUOUS TEED confidence, not of a thresholded step.

    The M1a photometric evidence is exp(-dt/SIGMA) with dt = distance to the nearest edge
    PIXEL -- a pixel is either an edge or it is not.  Here the evidence becomes
        E(x) = max_y  (p(y)/p_ref) * exp(-|x-y|/SIGMA)
    so a faint detection contributes proportionally to its calibrated probability instead
    of being promoted to a full edge or discarded.  Returning dt_eff = -SIGMA*ln E keeps
    every downstream consumer (photo_edge_dt's caller, score_from_evidence) untouched.
    The max over y is evaluated by quantising p into SOFT_LEVELS and taking the lower
    envelope of the per-level distance transforms; the quantisation error is bounded by
    SIGMA*ln(t_{k+1}/t_k), <= 0.8 px over the dense part of the ladder."""
    p = teed_prob(rgb_path)
    p_ref = float(max(SOFT_LEVELS))
    out = None
    for t in SOFT_LEVELS:
        m = p >= t
        if not m.any():
            continue
        d = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
        v = d + SOFT_GAMMA * SIGMA * np.log(p_ref / t)
        out = v if out is None else np.minimum(out, v)
    if out is None:                       # degenerate: no pixel above the lowest level
        return np.full(p.shape, 1e6, np.float32)
    return out.astype(np.float32)
RAD_MULT  = 2.0         # local-competition ball radius, in median-1NN-spacing units
LAMBDA    = 0.5         # weight of the local rank
F_OVERALL = 0.22        # keep-fraction, overall recipe
F_PUREGEOM = 0.28       # keep-fraction, pure-geometry recipe

_R = lambda v: rankdata(v) / len(v)


# ------------------------------------------------------------------ image evidence
def canny_edge_map(rgb_path, cfgs=None):
    """Binary union of blurred-Canny edge maps, uint8 {0,255}. [H,W].  Bit-identical to
    the code that used to live inline in photo_edge_dt when EDGE_SOURCE == "canny"."""
    cfgs = CANNY_CFGS if cfgs is None else cfgs
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
    return e


def photo_edge_map(rgb_path, cfgs=None):
    """Binary photometric edge map for the current EDGE_SOURCE, uint8 {0,255}. [H,W].

    Factored out of photo_edge_dt so the recall diagnostics can intersect the raw edge SET
    (not its DT) with GT crease pixels."""
    if EDGE_SOURCE in ("teed", "teed_cc", "teed_epi"):
        # "teed_epi" is the epipolar-consensus arm.  src/epipolar_consensus.py writes its
        # surviving edges to a cache with the IDENTICAL file layout and key as the TEED cache
        # ("native", values in {0,1}), already NMS-thinned by construction because the arm is
        # a SUBSET of the thinned TEED map.  So it reads through the same path with nms=False
        # and thr=0.5, and no existing source's behaviour changes by a single pixel.
        return teed_edge_map(rgb_path)
    e = canny_edge_map(rgb_path, cfgs)
    if EDGE_SOURCE == "union":
        # ADDITIVE: every Canny edge is kept and the learned ones are ADDED.  Recall can
        # only go up relative to "canny", which is what "spend orthogonal information
        # additively, not subtractively" means at the level of the edge map.
        e = e | teed_edge_map(rgb_path)
    elif EDGE_SOURCE == "cannymask":
        # M3 -- SUBTRACTIVE: Canny keeps its own (1-px, sub-pixel-accurate) LOCALISATION,
        # but only where TEED says there is a contour.  If this recovers most of the TEED
        # lift, the operative property is SELECTIVITY, not where TEED puts its edges.
        sup = teed_prob(rgb_path) >= TEED_THR
        if MASK_SHIFT:
            sup = np.roll(sup, (MASK_SHIFT, MASK_SHIFT), axis=(0, 1))
        if MASK_DILATE > 0:
            sup = cv2.dilate(sup.astype(np.uint8),
                             np.ones((2 * MASK_DILATE + 1,) * 2, np.uint8)) > 0
        e = np.where(sup, e, 0).astype(np.uint8)
    elif EDGE_SOURCE == "teed_soft":
        # the soft arm has no binary map; expose the >= thr set for diagnostics only.
        return teed_edge_map(rgb_path)
    return e


def photo_edge_dt(rgb_path, cfgs=None):
    """Distance transform of the current photometric edge source. [H,W] float32."""
    if EDGE_SOURCE == "teed_soft":
        return teed_soft_dt(rgb_path)
    e = photo_edge_map(rgb_path, cfgs)
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
