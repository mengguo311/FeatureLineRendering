"""Run the final recipe end to end on a scene and evaluate with the REAL harness."""
import os, sys, time, numpy as np
from scipy.stats import rankdata
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness, structure_tensor, nms_along_e1
from src import render, visibility
import final_recipe as FR
import torch

scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
t0 = time.time()
h = Harness(scene)
X, opa = h.X, h.opa
M = len(X)
print(f"[{scene}] {M} de-floatered gaussians  ({time.time()-t0:.0f}s)", flush=True)

cache = os.path.join(OUT, f"final_evid_{scene}.npz")
if os.path.exists(cache):
    Z = np.load(cache); DP_, DR, VIS = Z["dp"], Z["dr"], Z["vis"]
else:
    views = np.unique(np.round(np.linspace(0, len(h.cams) - 1, FR.N_VIEWS)).astype(int))
    DP_ = np.zeros((len(views), M), np.float32)
    DR = np.zeros((len(views), M), np.float32)
    VIS = np.zeros((len(views), M), bool)
    from scipy.ndimage import map_coordinates
    for vi, v in enumerate(views):
        cam = h.cams[v]
        gb = render.render_gbuffer(h.g, h.keep, cam)
        dep = gb["depth"].cpu().numpy().astype(np.float32)
        nrm = gb["normal"].cpu().numpy()
        alp = gb["alpha"].cpu().numpy()
        vm, uv, _ = visibility.visible_mask(X, cam, gb["depth"])
        del gb; torch.cuda.empty_cache()
        u = np.round(uv[:, 0]).astype(np.int64); w = np.round(uv[:, 1]).astype(np.int64)
        VIS[vi] = vm & (u >= 0) & (u < cam.W) & (w >= 0) & (w < cam.H)
        uu = np.clip(uv[:, 0], 0, cam.W - 1); ww = np.clip(uv[:, 1], 0, cam.H - 1)
        DP_[vi] = map_coordinates(FR.photo_edge_dt(h.rgb_paths[v]), [ww, uu],
                                  order=1, mode="nearest")
        DR[vi] = map_coordinates(FR.crease_ridge_dt(nrm, dep, alp), [ww, uu],
                                 order=1, mode="nearest")
        if vi % 8 == 0: print(f"  view {vi}/{len(views)} {time.time()-t0:.0f}s", flush=True)
    np.savez_compressed(cache, dp=DP_, dr=DR, vis=VIS)
print(f"evidence ready {time.time()-t0:.0f}s", flush=True)

# canonical K=8 pool, for reference
st = structure_tensor(X, h.N, 8)
cand = np.where(st["s_crease"] > 0.05)[0]
sel = nms_along_e1(X, cand, st["s_crease"], st["e1"], st["knn"])
print("canonical pool %d  baseline %.3f/%.3f/%d" % ((len(sel),) + h.evaluate(X[sel])), flush=True)
print("all-gaussian pool %d  baseline %.3f/%.3f/%d" % ((M,) + h.evaluate(X)), flush=True)

FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.28, 0.25, 0.22, 0.2, 0.15, 0.1]
for mode, flock in (("overall", FR.F_OVERALL), ("puregeom", FR.F_PUREGEOM)):
    s = FR.score_from_evidence(X, opa, DP_, DR, VIS, mode=mode)
    np.save(os.path.join(OUT, f"finalscore_{mode}_{scene}.npy"), s)
    o = np.argsort(-s, kind="stable")
    print(f"\n===== {mode.upper()} =====", flush=True)
    for f in FS:
        k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
        p, r, n = h.evaluate(X, extra_mask=k)
        mark = "  <== LOCKED f" if abs(f - flock) < 1e-9 else ""
        print(f"  f={f:<5} p={p:.4f} r={r:.4f} n={n}{mark}", flush=True)
    k = np.zeros(M, bool); k[o[:int(round(flock * M))]] = True
    ps, rs, ns = h.evaluate(X, extra_mask=k, per_view=True)
    print(f"  PER-VIEW at f={flock}: " +
          "  ".join(f"v{v}: p={p:.4f} r={r:.4f} n={n}" for v, p, r, n in zip(h.views, ps, rs, ns)),
          flush=True)
print("total %.0fs" % (time.time() - t0))
