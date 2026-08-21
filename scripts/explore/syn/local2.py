"""Hypothesis: globally, a DENSE edge map is too noisy (regional AUC 0.75 vs 0.86),
but LOCALLY -- comparing gaussians inside one cluster straddling the crease -- it has
the resolution the sparse map lacks.  So: global rank from the SPARSE map, local rank
from the DENSE/MID map."""
import os, sys, time, numpy as np, cv2
from scipy.stats import rankdata
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness
from fastgate import FastGate
from src import visibility
from sharp import photo_edges

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
NV = 25
CFG = {"dense": ((1.0, 50, 150),), "mid": ((1.5, 60, 160),)}

h = Harness(scene); X, opa = h.X, h.opa; M = len(X)
cache = os.path.join(OUT, f"evid_dense_{scene}.npz")
if os.path.exists(cache):
    Z = np.load(cache); D2 = {k: Z[k] for k in CFG}
else:
    views = np.unique(np.round(np.linspace(0, len(h.cams) - 1, NV)).astype(int))
    D2 = {k: np.zeros((len(views), M), np.float32) for k in CFG}
    E0 = np.load(os.path.join(OUT, f"evid_all_{scene}.npz"))
    t0 = time.time()
    for vi, v in enumerate(views):
        cam = h.cams[v]
        from src import render
        gb = render.render_gbuffer(h.g, h.keep, cam)
        _, uv, _ = visibility.visible_mask(X, cam, gb["depth"])
        del gb
        uu = np.clip(uv[:, 0], 0, 799); ww = np.clip(uv[:, 1], 0, 799)
        for k, cfgs in CFG.items():
            d = cv2.distanceTransform((~photo_edges(h.rgb_paths[v], cfgs)).astype(np.uint8),
                                      cv2.DIST_L2, 5)
            D2[k][vi] = map_coordinates(d, [ww, uu], order=1, mode="nearest")
        if vi % 10 == 0: print(f" view {vi} {time.time()-t0:.0f}s", flush=True)
    np.savez_compressed(cache, **D2)

E = np.load(os.path.join(OUT, f"evid_all_{scene}.npz"))
vis = E["vis"]; nv = np.maximum(vis.sum(0), 1); never = vis.sum(0) == 0
Rk = lambda v: rankdata(v) / len(v)


def agg(Dm, s=16.0):
    a = np.where(vis, np.exp(-Dm / s), 0).sum(0) / nv
    a[never] = -1.0
    return a


with np.errstate(all="ignore"):
    rq90 = -np.nan_to_num(np.nanpercentile(np.where(vis, E["ridge45"], np.nan), 90, axis=0), nan=1e9)
rq90[never] = rq90.min() - 1
F = {"sparse": agg(E["sparse"]), "ridge": agg(E["ridge45"], 16.0), "rq90": rq90,
     "dense2": agg(D2["dense"], 2.0), "dense4": agg(D2["dense"], 4.0),
     "mid2": agg(D2["mid"], 2.0), "mid4": agg(D2["mid"], 4.0),
     "mid8": agg(D2["mid"], 8.0), "ridge4": agg(E["ridge45"], 4.0),
     "opa": opa.astype(float)}
S_ALL = Rk(F["sparse"]) + 0.5 * Rk(F["rq90"])
S_GEO = Rk(F["rq90"]) + 0.5 * Rk(opa) + 0.25 * ((vis & (E["ridge45"] <= 8)).sum(0) / nv)

fg = FastGate(h, np.arange(M))
tree = cKDTree(X)
sp = np.median(tree.query(X, k=2)[0][:, 1])
FG = np.arange(0.05, 0.75, 0.01)


def best(s, rmin=0.72):
    o = np.argsort(-s, kind="stable"); b = None
    for f in FG:
        k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
        p, r, n = fg(k)
        if r >= rmin and (b is None or p > b[0]): b = (p, r, f, n)
    return b


BALL = {}
for rm in (1.5, 2, 3, 4):
    BALL[rm] = tree.query_ball_point(X, r=rm * sp, workers=-1)


def lrank(S, rm):
    return np.array([np.mean(S[np.asarray(l)] < S[i]) if len(l) > 1 else 1.0
                     for i, l in enumerate(BALL[rm])])


for label, S in (("OVERALL", S_ALL), ("PUREGEOM", S_GEO)):
    print(f"\n##### {label}  global-only: " +
          ("p=%.3f r=%.3f f=%.2f" % best(S)[:3]), flush=True)
    for lf in (["dense2", "dense4", "mid2", "mid4", "mid8", "sparse", "ridge4"]
               if label == "OVERALL" else ["ridge4", "ridge", "rq90"]):
        for rm in (1.5, 2, 3, 4):
            lr = lrank(F[lf], rm)
            for lam in (0.25, 0.5, 0.75, 1.0):
                b = best(S + lam * lr)
                if b and b[0] > 0.70:
                    print(f"  lrank({lf}) rad{rm}sp lam{lam}: p={b[0]:.3f} r={b[1]:.3f} "
                          f"f={b[2]:.2f} n={b[3]}", flush=True)
