"""Phase 1b — WHY is precision capped? EVAL/ANALYSIS ONLY.

84.9% of triangulated points reproject onto DexiNed edges in their neighbour views, yet only
16.9% lie within the 1.5px-equivalent radius of a GT dihedral crease. If the 83% that are NOT
near a crease are ALSO multi-view consistent, then they are real, correctly-triangulated 3D
structure that simply is not a crease -- i.e. the chair's printed fabric pattern. That would
mean the precision ceiling is a DETECTOR-SEMANTICS limit (DexiNed returns photometric edges,
the GT asks for dihedral creases), not a triangulation-accuracy limit.
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

from src import common, view_split, tri_edges as T
from dexprimary_p0 import gt_labels

scene = "chair"
z = np.load(os.path.join(OUT, f"dexprimary_p1b_cloud_{scene}.npz"))
cfg = json.load(open(os.path.join(OUT, f"dexprimary_p1b_{scene}.json")))
A, refs, rad = cfg["args"], cfg["refs"], cfg["radii"]["px1.5_equiv"]
dex = os.path.join(OUT, f"dexined_edges_{scene}")
cams, _ = common.load_cameras(scene)
crease_pts, _, _ = gt_labels(scene, view_split.TEST)

keep = (z["support"] >= 2) & z["surface_keep"] & (z["resid"] <= A["resid_max"])
P, ref = z["P"][keep], z["ref"][keep]
near = cKDTree(crease_pts).query(P, k=1)[0] <= rad
print(f"triangulated (sup>=2, culled): {len(P)}   near a GT crease: {near.mean():.4f}")

# per-point multi-view consistency: fraction of its neighbour views with edge-DT <= 1.5
cons = np.zeros(len(P)); seen = np.zeros(len(P))
for r in refs:
    sel = ref == r
    if not sel.any():
        continue
    for n in T.neighbor_views(cams, r, A["K"], view_split.TRAIN):
        _, dtn = T.edge_dt(dex, n, A["thr"], A["key"])
        uvn, zn = common.project(P[sel], cams[n])
        ok = (zn > 0) & (uvn[:, 0] >= 0) & (uvn[:, 0] < 800) & (uvn[:, 1] >= 0) & (uvn[:, 1] < 800)
        ui = np.clip(np.round(uvn[:, 0] - A["halfpix"]).astype(int), 0, 799)
        vi = np.clip(np.round(uvn[:, 1] - A["halfpix"]).astype(int), 0, 799)
        d = np.where(ok, dtn[vi, ui], 1e6)
        idx = np.where(sel)[0]
        cons[idx] += (d <= 1.5).astype(float)
        seen[idx] += ok.astype(float)
frac = cons / np.maximum(seen, 1)
print("\n=== multi-view consistency, split by whether the point is on a GT crease ===")
for lab, m in (("ON a GT crease   ", near), ("NOT on a crease  ", ~near)):
    print(f"  {lab} n={int(m.sum()):7d}  mean consistent-neighbour fraction {frac[m].mean():.4f}"
          f"   frac with >=80% consistency {np.mean(frac[m]>=0.8):.4f}")
print(f"\n  -> if the two rows are similar, the off-crease points are REAL triangulated 3D")
print(f"     structure (printed pattern / shading edges), not triangulation error.")
json.dump({"n": int(len(P)), "frac_near_crease": float(near.mean()),
           "consistency_on_crease": float(frac[near].mean()),
           "consistency_off_crease": float(frac[~near].mean()),
           "hi_consistency_on_crease": float(np.mean(frac[near] >= 0.8)),
           "hi_consistency_off_crease": float(np.mean(frac[~near] >= 0.8))},
          open(os.path.join(OUT, "dexprimary_p1b_texture.json"), "w"), indent=2)
print("\nwrote out/dexprimary_p1b_texture.json")
