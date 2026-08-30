"""Phase 1b — THE SPREAD CONTROL. EVAL/ANALYSIS ONLY.

The paired test showed triangulation does NOT improve per-point accuracy onto GT creases
(median distance 0.0223 -> 0.0287, closer for only 45% of points) yet the aggregate cloud
recall rose (0.536 -> 0.590). Both can be true if the gain comes from the cloud being more
SPREAD IN DEPTH rather than better placed: the single-view cloud lies on one 2D surface, and
scattering points off it covers more of a 3D crease set at a fixed radius regardless of
whether any individual point got better.

CTRL_JITTER isolates exactly that. Take the single-view cloud and displace each point ALONG
ITS OWN VIEWING RAY by a multiplicative factor drawn from the triangulation's OWN observed
displacement distribution -- the same factors, randomly permuted across points. Marginal
depth-displacement distribution: identical. Correspondence between pixel and displacement:
destroyed. It is the direct analogue of Phase 0's ctrl_shufz.

If ctrl_jitter reproduces the recall gain, the gain is spread, not localization.
"""
import os
import sys
import json

import numpy as np
import torch
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out")

from src import common, render, view_split, visibility, tri_edges as T
from dexprimary_p0 import gt_labels
from dexprimary_p1b import score_cloud, TAUS

scene = "chair"
cfg = json.load(open(os.path.join(OUT, f"dexprimary_p1b_{scene}.json")))
refs, A = cfg["refs"], cfg["args"]
dex = os.path.join(OUT, f"dexined_edges_{scene}")
rng = np.random.default_rng(0)

cams, _ = common.load_cameras(scene)
g = common.load_gaussians(scene)
kg = render.defloat_mask(g["mu"], g["opacity"])

P_sv, P_tri, ratio, sup_a, res_a, dirs, zs, Cs = [], [], [], [], [], [], [], []
dts = {}
for r in refs:
    nbrs = T.neighbor_views(cams, r, A["K"], view_split.TRAIN)
    for n in nbrs:
        if n not in dts:
            _, dt = T.edge_dt(dex, n, A["thr"], A["key"])
            dts[n] = torch.tensor(dt, dtype=torch.float32, device="cuda")
    gb = render.render_gbuffer(g, kg, cams[r], with_median_depth=True)
    dmed = gb["depth_median"].cpu().numpy().astype(np.float64)
    m, _ = T.edge_dt(dex, r, A["thr"], A["key"])
    vv, uu = np.nonzero(m)
    zc = dmed[vv, uu]
    ok = np.isfinite(zc) & (zc > 1e-6)
    vv, uu, zc = vv[ok], uu[ok], zc[ok]
    uv = np.stack([uu, vv], 1).astype(np.float64)
    hp, cam = A["halfpix"], cams[r]
    f, cx, cy = cam.f, cam.K[0, 2], cam.K[1, 2]
    dcam = np.stack([(uu + hp - cx) / f, (vv + hp - cy) / f, np.ones(len(uu))], 1)
    dir_w = dcam @ cam.w2c[:3, :3]                      # R^T dcam
    C = cam.center
    P_sv.append(C[None] + zc[:, None] * dir_w)
    rr = T.triangulate_view(cams, r, nbrs, dts, zc, uv, halfpix=hp, rho=A["rho"], tau=A["tau"])
    P_tri.append(rr["P"]); sup_a.append(rr["support"]); res_a.append(rr["resid"])
    ratio.append(rr["z"] / zc)
    dirs.append(dir_w); zs.append(zc); Cs.append(np.repeat(C[None], len(zc), 0))
    del gb
    torch.cuda.empty_cache()
for k in list(dts):
    del dts[k]
torch.cuda.empty_cache()

P_sv = np.concatenate(P_sv); P_tri = np.concatenate(P_tri)
ratio = np.concatenate(ratio); sup = np.concatenate(sup_a); resid = np.concatenate(res_a)
dirs = np.concatenate(dirs); zs = np.concatenate(zs); Cs = np.concatenate(Cs)
perm = rng.permutation(len(ratio))
P_jit = Cs + (zs * ratio[perm])[:, None] * dirs         # same displacement law, shuffled
print(f"seeds {len(P_sv)}  |log ratio| median {np.median(np.abs(np.log(ratio))):.5f}")

keep = (sup >= 2) & (resid <= A["resid_max"])
kp, _, _ = T.surface_cull(P_tri, cams, sorted(set(refs)), {}, {}) if False else (keep, 0, 0)

# ---- score everything with the identical Phase-0/1b measurement
views = view_split.TEST
crease_pts, gt, bbox_diag = gt_labels(scene, views)
X_pool = g["mu"][kg]
covered = {t: {} for t in TAUS}; miss2d = {t: {} for t in TAUS}
depth_np, depth_t = {}, {}
for v in views:
    gb = render.render_gbuffer(g, kg, cams[v], with_median_depth=True)
    depth_np[v] = gb["depth"].cpu().numpy(); depth_t[v] = gb["depth"].clone()
    idx, uvq = gt[v]
    vis, uvg, _ = visibility.visible_mask(X_pool, cams[v], gb["depth"])
    d_pool = cKDTree(uvg[vis]).query(uvq, k=1)[0]
    for t in TAUS:
        covered[t][v] = d_pool <= t; miss2d[t][v] = ~covered[t][v]
    del gb
    torch.cuda.empty_cache()
seen = np.zeros(len(crease_pts), bool); cov_any = np.zeros(len(crease_pts), bool)
for v in views:
    idx, _ = gt[v]; seen[idx] = True; cov_any[idx] |= covered[1.5][v]
miss3d = seen & ~cov_any; seen_idx = np.where(seen)[0]
radii = cfg["radii"]; tree_gt3 = cKDTree(crease_pts)

clouds = {"p0_singleview": P_sv[keep], "tri (no surface cull)": P_tri[keep],
          "CTRL_JITTER (spread-matched)": P_jit[keep]}
print(f"\n{'cloud':30s} {'n':>8s} | {'rec2D':>7s} {'lift':>5s} | {'rec3D':>7s} {'Rm3D':>7s} {'pr3D':>7s}")
res = {}
for k, P in clouds.items():
    a = score_cloud(k, P, cams, views, gt, covered, miss2d, miss3d, seen_idx, crease_pts,
                    tree_gt3, depth_t, depth_np, radii)
    res[k] = a
    print(f"{k:30s} {a['n_total']:8d} | {a['recall_2D']:7.4f} {a['lift']:5.2f} | "
          f"{a['recall_3D_px1.5_equiv']:7.4f} {a['R_miss_3D_px1.5_equiv']:7.4f} "
          f"{a['precision_3D_px1.5_equiv']:7.4f}")
json.dump(res, open(os.path.join(OUT, "dexprimary_p1b_spread.json"), "w"), indent=2)
print("\nwrote out/dexprimary_p1b_spread.json")
