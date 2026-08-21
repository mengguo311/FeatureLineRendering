"""Sweep tau_seed / k for the M1a gate (chair). Reuses fixed G-buffers per view."""
import os, sys, itertools
import numpy as np, cv2, torch
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from src import common, render, seeds as seeds_mod, visibility
from src.mesh_oracle import MeshOracle

scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
views = [0, 25]
cams, _ = common.load_cameras(scene)
g = common.load_gaussians(scene)
keep = render.defloat_mask(g["mu"], g["opacity"])
gbufs = {vi: render.render_gbuffer(g, keep, cams[vi]) for vi in views}
oracle = MeshOracle(scene, angle_deg=30.0)
H = Wd = 800

crease = {}
for vi in views:
    uvq = oracle.visible_crease_uv(cams[vi], view_key=vi)
    cu = np.clip(np.round(uvq[:, 0]).astype(int), 0, Wd - 1)
    cv_ = np.clip(np.round(uvq[:, 1]).astype(int), 0, H - 1)
    m = np.zeros((H, Wd), bool); m[cv_, cu] = True
    crease[vi] = (cu, cv_, cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5))

for k, tau in itertools.product([16, 24, 32], [0.05, 0.10, 0.15, 0.20, 0.30]):
    sd = seeds_mod.compute_seeds(g["mu"][keep], g["normal"][keep], k=k, tau_seed=tau)
    if len(sd["pos"]) < 50:
        print(f"k={k} tau={tau}: too few seeds ({len(sd['pos'])})"); continue
    ps, rs = [], []
    for vi in views:
        vis, uv, _ = visibility.visible_mask(sd["pos"], cams[vi], gbufs[vi]["depth"])
        suv = uv[vis]
        inb = (suv[:, 0] >= 0) & (suv[:, 0] < Wd) & (suv[:, 1] >= 0) & (suv[:, 1] < H)
        suv = suv[inb]
        su = np.round(suv[:, 0]).astype(int); sv = np.round(suv[:, 1]).astype(int)
        cu, cv_, cdt = crease[vi]
        ps.append((cdt[sv, su] <= 2.5).mean() if len(suv) else 0.0)
        sm = np.zeros((H, Wd), bool); sm[sv, su] = True
        sdt = cv2.distanceTransform((~sm).astype(np.uint8), cv2.DIST_L2, 5)
        rs.append((sdt[cv_, cu] <= 3.0).mean())
    print(f"k={k:2d} tau={tau:.2f} seeds={len(sd['pos']):6d}  "
          f"prec={100*np.mean(ps):5.1f}% (v0 {100*ps[0]:.1f}/v25 {100*ps[1]:.1f})  "
          f"rec={100*np.mean(rs):5.1f}% (v0 {100*rs[0]:.1f}/v25 {100*rs[1]:.1f})")
