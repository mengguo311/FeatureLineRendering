"""Phase 1b — the PAIRED localization test + reprojection sanity. EVAL/ANALYSIS ONLY.

The 1b question is not "is the cloud good" but "does multi-view triangulation place the SAME
DexiNed edge pixel better than single-view 3DGS depth does". tri and p0_singleview are built
from the identical edge pixels of the identical reference views, so they can be compared
POINT BY POINT rather than only in aggregate -- a paired test, which removes the density
confound entirely.

Also runs the spec's pitfall check: a triangulated point must reproject onto the object in its
SUPPORTING views, not just in the reference view it came from (where it is exact by
construction).
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

from src import common, render, view_split, tri_edges as T
from dexprimary_p0 import gt_labels, lift_view

scene = "chair"
z = np.load(os.path.join(OUT, f"dexprimary_p1b_cloud_{scene}.npz"))
cfg = json.load(open(os.path.join(OUT, f"dexprimary_p1b_{scene}.json")))
rad = cfg["radii"]["px1.5_equiv"]
refs, A = cfg["refs"], cfg["args"]
dex = os.path.join(OUT, f"dexined_edges_{scene}")

crease_pts, gt, _ = gt_labels(scene, view_split.TEST)
tree_gt = cKDTree(crease_pts)
cams, _ = common.load_cameras(scene)
g = common.load_gaussians(scene)
kg = render.defloat_mask(g["mu"], g["opacity"])

# Rebuild BOTH clouds from an identical seed list so the comparison is exactly paired:
# same edge pixel, same initial z (the 3DGS median depth). The only difference between the
# two is whether multi-view consensus was allowed to move the point off that initialisation.
P_sv, P_tr, ref_all, sup_all, res_all = [], [], [], [], []
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
    ok = np.isfinite(zc) & (zc > 1e-6)                 # Phase 0's median-arm rule
    vv, uu, zc = vv[ok], uu[ok], zc[ok]
    uv = np.stack([uu, vv], 1).astype(np.float64)
    hp = A["halfpix"]
    f, cx, cy = cams[r].f, cams[r].K[0, 2], cams[r].K[1, 2]
    Xc = np.stack([zc * (uu + hp - cx) / f, zc * (vv + hp - cy) / f, zc], 1)
    R, t = cams[r].w2c[:3, :3], cams[r].w2c[:3, 3]
    P_sv.append((Xc - t) @ R)                          # single-view placement
    rr = T.triangulate_view(cams, r, nbrs, dts, zc, uv, halfpix=hp, rho=A["rho"],
                            tau=A["tau"])              # same seed, same init, refined
    P_tr.append(rr["P"]); sup_all.append(rr["support"]); res_all.append(rr["resid"])
    ref_all.append(np.full(len(uv), r))
    del gb
    torch.cuda.empty_cache()
P_sv = np.concatenate(P_sv); P_tri = np.concatenate(P_tr)
sup = np.concatenate(sup_all); resid = np.concatenate(res_all); ref_tri = np.concatenate(ref_all)
for k in list(dts):
    del dts[k]
torch.cuda.empty_cache()
print(f"paired seeds: {len(P_sv)}")

kp2, nv2, _ = T.surface_cull(P_tri, cams, sorted(set(refs)), {}, {}, device="cuda") \
    if False else (None, None, None)
d_sv = tree_gt.query(P_sv, k=1)[0]
d_tri = tree_gt.query(P_tri, k=1)[0]
keep = (sup >= 2) & (resid <= A["resid_max"])
print("\n=== PAIRED LOCALIZATION (distance from each seeded point to the nearest GT crease) ===")
for lab, mm in (("all seeds", np.ones(len(d_sv), bool)), ("kept (sup>=2 + resid)", keep)):
    a, b = d_sv[mm], d_tri[mm]
    print(f"\n{lab}  n={int(mm.sum())}")
    print(f"  single-view  median {np.median(a):.5f}  p25 {np.percentile(a,25):.5f}  "
          f"p75 {np.percentile(a,75):.5f}   frac<=1.5px-equiv {np.mean(a<=rad):.4f}")
    print(f"  triangulated median {np.median(b):.5f}  p25 {np.percentile(b,25):.5f}  "
          f"p75 {np.percentile(b,75):.5f}   frac<=1.5px-equiv {np.mean(b<=rad):.4f}")
    print(f"  -> triangulation is CLOSER for {np.mean(b < a):.4f} of the paired points; "
          f"median improvement {np.median(a-b):+.5f} ({np.median(a)/max(np.median(b),1e-9):.2f}x)")
    fixed = float(np.mean((a > rad) & (b <= rad)))
    broke = float(np.mean((a <= rad) & (b > rad)))
    print(f"  -> FIXED (was outside tol, now inside) {fixed:.4f} | "
          f"BROKE (was inside, now outside) {broke:.4f} | net {fixed-broke:+.4f}")
Pk = P_tri[keep]; rk = ref_tri[keep]

print("\n=== REPROJECTION SANITY: do triangulated points land on edges in SUPPORTING views? ===")
Pk = P_tri[keep]; rk = ref_tri[keep]
own, nbr = [], []
for r in refs:
    sel = rk == r
    if not sel.any():
        continue
    _, dtr = T.edge_dt(dex, r, A["thr"], A["key"])
    uv, _ = common.project(Pk[sel], cams[r])
    ui = np.clip(np.round(uv[:, 0] - A["halfpix"]).astype(int), 0, 799)
    vi = np.clip(np.round(uv[:, 1] - A["halfpix"]).astype(int), 0, 799)
    own.append(dtr[vi, ui])
    for n in T.neighbor_views(cams, r, A["K"], view_split.TRAIN):
        _, dtn = T.edge_dt(dex, n, A["thr"], A["key"])
        uvn, zn = common.project(Pk[sel], cams[n])
        ok = (zn > 0) & (uvn[:, 0] >= 0) & (uvn[:, 0] < 800) & (uvn[:, 1] >= 0) & (uvn[:, 1] < 800)
        ui = np.clip(np.round(uvn[ok, 0] - A["halfpix"]).astype(int), 0, 799)
        vi = np.clip(np.round(uvn[ok, 1] - A["halfpix"]).astype(int), 0, 799)
        nbr.append(dtn[vi, ui])
own = np.concatenate(own); nbr = np.concatenate(nbr)
print(f"  reference view  edge-DT: median {np.median(own):.4f} p95 {np.percentile(own,95):.4f}"
      f"  (0 by construction)")
print(f"  NEIGHBOUR views edge-DT: median {np.median(nbr):.4f} p95 {np.percentile(nbr,95):.4f}"
      f"  frac<=1.5px {np.mean(nbr<=1.5):.4f}  n={len(nbr)}")
svn = []
for r in refs:
    sel = rk == r
    if not sel.any():
        continue
    for n in T.neighbor_views(cams, r, A["K"], view_split.TRAIN):
        _, dtn = T.edge_dt(dex, n, A["thr"], A["key"])
        uvn, zn = common.project(P_sv[keep][sel], cams[n])
        ok = (zn > 0) & (uvn[:, 0] >= 0) & (uvn[:, 0] < 800) & (uvn[:, 1] >= 0) & (uvn[:, 1] < 800)
        ui = np.clip(np.round(uvn[ok, 0] - A["halfpix"]).astype(int), 0, 799)
        vi = np.clip(np.round(uvn[ok, 1] - A["halfpix"]).astype(int), 0, 799)
        svn.append(dtn[vi, ui])
svn = np.concatenate(svn)
print(f"  same points placed by SINGLE-VIEW depth: median {np.median(svn):.4f} "
      f"p95 {np.percentile(svn,95):.4f}  frac<=1.5px {np.mean(svn<=1.5):.4f}  <- the contrast")

json.dump({"radius": rad, "n_paired": int(len(d_sv)), "n_kept": int(keep.sum()),
           "neighbour_edge_dt_median_singleview": float(np.median(svn)),
           "neighbour_edge_dt_frac_le_1.5_singleview": float(np.mean(svn <= 1.5)),
           "median_d_singleview": float(np.median(d_sv[keep])),
           "median_d_triangulated": float(np.median(d_tri[keep])),
           "frac_closer_triangulated": float(np.mean(d_tri[keep] < d_sv[keep])),
           "frac_within_tol_singleview": float(np.mean(d_sv[keep] <= rad)),
           "frac_within_tol_triangulated": float(np.mean(d_tri[keep] <= rad)),
           "neighbour_edge_dt_median": float(np.median(nbr)),
           "neighbour_edge_dt_frac_le_1.5": float(np.mean(nbr <= 1.5))},
          open(os.path.join(OUT, "dexprimary_p1b_paired.json"), "w"), indent=2)
print("\nwrote out/dexprimary_p1b_paired.json")
