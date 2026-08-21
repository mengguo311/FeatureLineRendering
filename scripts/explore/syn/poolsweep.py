"""Joint sweep over POOL construction x evidence ranking, over ALL de-floatered gaussians.
The canonical K=8 pool is only one choice; the pool agent showed pool choice is worth
+18pp base precision.  Here the pool and the ranker are optimised together.
"""
import os, sys, time, numpy as np, cv2
from scipy.stats import rankdata
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness, structure_tensor, nms_along_e1
from fastgate import FastGate
from src import visibility
import score_view as SV
from sharp import photo_edges, EDGE

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
NV = 25
scene = sys.argv[1] if len(sys.argv) > 1 else "chair"


def evidence_all(h, cache):
    if os.path.exists(cache):
        z = np.load(cache); return {k: z[k] for k in z}
    P = h.X; M = len(P)
    views = np.unique(np.round(np.linspace(0, len(h.cams) - 1, NV)).astype(int))
    D = {k: np.zeros((len(views), M), np.float32) for k in ("sparse", "ridge45")}
    VIS = np.zeros((len(views), M), bool)
    t0 = time.time()
    for vi, v in enumerate(views):
        cam = h.cams[v]
        Amap, Rmap, Fmap, nms, fgm, dep_t = SV._view_maps(h, cam, SV.DP)
        vism, uv, _ = visibility.visible_mask(P, cam, dep_t)
        u = np.round(uv[:, 0]).astype(np.int64); w = np.round(uv[:, 1]).astype(np.int64)
        VIS[vi] = vism & (u >= 0) & (u < 800) & (w >= 0) & (w < 800)
        uu = np.clip(uv[:, 0], 0, 799); ww = np.clip(uv[:, 1], 0, 799)
        d = cv2.distanceTransform((~photo_edges(h.rgb_paths[v], EDGE["sparse"])).astype(np.uint8),
                                  cv2.DIST_L2, 5)
        D["sparse"][vi] = map_coordinates(d, [ww, uu], order=1, mode="nearest")
        gate = nms & fgm & (Rmap < SV.TAU_RESID) & (Fmap >= 0.999) & (Amap >= 45.0)
        dd = cv2.distanceTransform((~gate).astype(np.uint8), cv2.DIST_L2, 5)
        D["ridge45"][vi] = map_coordinates(dd, [ww, uu], order=1, mode="nearest")
        del Amap, Rmap, Fmap, nms, fgm, dep_t
        if vi % 10 == 0: print(f"  view {vi} {time.time()-t0:.0f}s", flush=True)
    out = dict(D); out["vis"] = VIS
    np.savez_compressed(cache, **out)
    return out


h = Harness(scene)
X, N, opa = h.X, h.N, h.opa
M = len(X)
print(f"[{scene}] {M} de-floatered gaussians", flush=True)
E = evidence_all(h, os.path.join(OUT, f"evid_all_{scene}.npz"))
vis = E["vis"]
nv = np.maximum(vis.sum(0), 1)
s_dt = -np.where(vis, E["sparse"], 0).sum(0) / nv
s_ridge = np.where(vis, np.exp(-E["ridge45"] / 16.0), 0).sum(0) / nv
s_dt[vis.sum(0) == 0] = -1e9
print("evidence ready", flush=True)

# ---- pool features (pure geometry, mesh-free) ----
tree = cKDTree(X)
dist, knn = tree.query(X, k=33, workers=-1); knn = knn[:, 1:]
nbp = X[knn[:, :32]]
dd = nbp - nbp.mean(1, keepdims=True)
C = np.einsum("nkc,nkd->ncd", dd, dd) / 32
npca = np.linalg.eigh(C)[1][:, :, 0]
npca /= np.linalg.norm(npca, axis=1, keepdims=True) + 1e-12
dens = -dist[:, 1:33].mean(1)


def st_on(nrm, k):
    nb = knn[:, :k]
    nj = nrm[nb]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, nrm)); sg[sg == 0] = 1.0
    nj = nj * sg[..., None]
    dn = nj - nj.mean(1, keepdims=True)
    w = np.linalg.eigvalsh(np.einsum("nkc,nkd->ncd", dn, dn) / k)
    return w[:, 2], w[:, 2] - w[:, 1]


l1_pca, scr_pca = st_on(npca, 16)
Rk = lambda v: rankdata(v) / len(v)
pool_score = Rk(dens) + Rk(l1_pca) + Rk(opa)

# ---- candidate pools ----
st8 = structure_tensor(X, N, 8)
cand = np.where(st8["s_crease"] > 0.05)[0]
canon = nms_along_e1(X, cand, st8["s_crease"], st8["e1"], st8["knn"])
pools = {"canonical": canon}
for q in (0.30, 0.40, 0.50, 0.60):
    pools[f"poolq{q}"] = np.where(pool_score > np.quantile(pool_score, q))[0]
for q in (0.30, 0.40, 0.50):
    idx = np.where(pool_score > np.quantile(pool_score, q))[0]
    pools[f"poolq{q}+nms"] = nms_along_e1(X, idx, scr_pca, st8["e1"], knn[:, :8])
for t in (0.5, 0.6, 0.7):
    pools[f"opa{t}"] = np.where(opa > t)[0]
pools["all"] = np.arange(M)

FG = {}
print(f"\n{'pool':16s} {'n':>7s} {'base p/r':>13s}   best(p,r,f) @rec>=0.72 with rank score")
RANKS = {}
for name, idx in pools.items():
    fg = FastGate(h, idx)
    n = len(idx)
    p0, r0, _ = fg(np.ones(n, bool))
    sd = Rk(s_dt[idx]); sr = Rk(s_ridge[idx]); sp = Rk(pool_score[idx])
    cands = {"dt": sd, "dt+.5rid": sd + 0.5 * sr, "dt+.5rid+.25pool": sd + 0.5 * sr + 0.25 * sp,
             "ridge": sr, "pool": sp}
    line = f"{name:16s} {n:7d} {p0:.3f}/{r0:.3f}   "
    outs = []
    for cn, s in cands.items():
        o = np.argsort(-s, kind="stable"); b = None
        for f in np.arange(0.1, 1.01, 0.02):
            k = np.zeros(n, bool); k[o[:int(round(f * n))]] = True
            p, r, _ = fg(k)
            if r >= 0.72 and (b is None or p > b[0]): b = (p, r, f)
        outs.append(f"{cn}:{b[0]:.3f}/{b[1]:.3f}@{b[2]:.2f}" if b else f"{cn}:-")
    print(line + "  ".join(outs), flush=True)
