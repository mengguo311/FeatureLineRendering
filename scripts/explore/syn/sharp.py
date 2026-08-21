"""Attack the diagnosed 2.5-6px near-miss failure mode: sharp multi-view localization.

Builds per-seed x per-view distance matrices for several evidence maps at several
sharpnesses, then sweeps aggregations / products / cascades against the gate.
EVAL-SIDE analysis script.
"""
import os, sys, time, itertools, numpy as np, cv2
from scipy.ndimage import map_coordinates
from scipy.stats import rankdata
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from cache_scores import build
from fastgate import FastGate
from src import render, visibility
import score_view as SV

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
NV = 25

EDGE = {
    "dense":  ((1.0, 50, 150),),
    "mid":    ((1.5, 60, 160),),
    "sparse": ((2.0, 100, 200), (2.5, 75, 150)),
}


def photo_edges(path, cfgs):
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
    return e > 0


def gather(scene, h, sel):
    cache = os.path.join(OUT, f"sharp_{scene}.npz")
    if os.path.exists(cache):
        z = np.load(cache)
        return {k: z[k] for k in z}
    P = h.X[sel]; M = len(P)
    views = np.unique(np.round(np.linspace(0, len(h.cams) - 1, NV)).astype(int))
    keys = list(EDGE) + ["ridge35", "ridge45", "ridge55"]
    D = {k: np.zeros((len(views), M), np.float32) for k in keys}
    VIS = np.zeros((len(views), M), bool)
    t0 = time.time()
    for vi, v in enumerate(views):
        cam = h.cams[v]
        Amap, Rmap, Fmap, nms, fg, dep_t = SV._view_maps(h, cam, SV.DP)
        vism, uv, _ = visibility.visible_mask(P, cam, dep_t)
        u = np.round(uv[:, 0]).astype(np.int64); w = np.round(uv[:, 1]).astype(np.int64)
        ok = vism & (u >= 0) & (u < 800) & (w >= 0) & (w < 800)
        VIS[vi] = ok
        uu = np.clip(uv[:, 0], 0, 799); ww = np.clip(uv[:, 1], 0, 799)
        for k, cfgs in EDGE.items():
            d = cv2.distanceTransform((~photo_edges(h.rgb_paths[v], cfgs)).astype(np.uint8),
                                      cv2.DIST_L2, 5)
            D[k][vi] = map_coordinates(d, [ww, uu], order=1, mode="nearest")
        gate = nms & fg & (Rmap < SV.TAU_RESID) & (Fmap >= 0.999)
        for ta, k in ((35.0, "ridge35"), (45.0, "ridge45"), (55.0, "ridge55")):
            cm = gate & (Amap >= ta)
            dd = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
            D[k][vi] = map_coordinates(dd, [ww, uu], order=1, mode="nearest")
        del Amap, Rmap, Fmap, nms, fg, dep_t
        if vi % 8 == 0:
            print(f"  view {vi}/{len(views)} {time.time()-t0:.0f}s", flush=True)
    out = {k: D[k] for k in D}; out["vis"] = VIS; out["views"] = views
    np.savez_compressed(cache, **out)
    return out


def aggs(Dm, vis):
    """dict of aggregation-name -> score (higher better)."""
    A = np.where(vis, Dm, np.nan)
    nv = vis.sum(0)
    o = {}
    with np.errstate(all="ignore"):
        o["mean"] = -np.nanmean(A, 0)
        for q in (25, 50, 75, 90):
            o[f"q{q}"] = -np.nanpercentile(A, q, axis=0)
        for tau in (1.5, 2.0, 3.0, 5.0, 8.0, 12.0):
            o[f"fr{tau}"] = (vis & (Dm <= tau)).sum(0) / np.maximum(nv, 1)
        for s in (2.0, 4.0, 8.0, 16.0):
            o[f"soft{s}"] = np.nansum(np.where(vis, np.exp(-Dm / s), 0.0), 0) / np.maximum(nv, 1)
    for k in o:
        o[k] = np.nan_to_num(np.asarray(o[k], np.float64), nan=-1e9, posinf=-1e9, neginf=-1e9)
    return o


if __name__ == "__main__":
    scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
    h, st, sel = build(scene)
    fg_ = FastGate(h, sel); M = len(sel)
    G = gather(scene, h, sel)
    vis = G["vis"]
    z = dict(np.load(os.path.join(OUT, f"scores_{scene}.npz")))
    pos, visany = z["lab_pos"], z["lab_vis"]

    def auc(s):
        r = rankdata(s[visany]); y = pos[visany]
        n1 = y.sum(); n0 = len(y) - n1
        return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

    FGRID = np.arange(0.15, 0.85, 0.01)

    def best(s, rmin=0.72):
        o = np.argsort(-s, kind="stable"); b = None
        for f in FGRID:
            k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
            p, r, n = fg_(k)
            if r >= rmin and (b is None or p > b[0]): b = (p, r, f)
        return b

    ALL = {}
    print(f"\n{'field/agg':22s} {'AUC':>6s}  best(p,r,f) @rec>=0.72")
    for k in ["dense", "mid", "sparse", "ridge35", "ridge45", "ridge55"]:
        for an, s in aggs(G[k], vis).items():
            ALL[f"{k}.{an}"] = s
            b = best(s)
            print(f"{k+'.'+an:22s} {auc(s):6.3f}  " +
                  (f"{b[0]:.3f}/{b[1]:.3f} f={b[2]:.2f}" if b else "-"), flush=True)
    np.savez_compressed(os.path.join(OUT, f"sharpaggs_{scene}.npz"), **ALL)
