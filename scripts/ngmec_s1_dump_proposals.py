"""Dump a non-TEED proposal set into the TEED cache layout, so the epipolar gate can be
tested on a detector that has NO selectivity prior of its own.

*** METHOD PATH. MESH-FREE. ***  TRACK M measured that a selectivity mask applied to an
ALREADY-selective detector buys ~nothing (+0.004, carried 0.08) and applied to a permissive
one buys +0.2408.  TEED is already selective, so gating TEED is structurally the first case.
This dumps the permissive un-blurred Canny so the second case can be measured too.
"""
import os
import sys
import argparse

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))
from src import common, view_split
import final_recipe as FR

OUT = os.path.join(TIER1, "out")

ap = argparse.ArgumentParser()
ap.add_argument("--scene", required=True)
ap.add_argument("--name", default="cannysharplow")
ap.add_argument("--cfgs", type=float, nargs="+", default=[0, 20, 60])
args = ap.parse_args()

cams, rgb_paths = common.load_cameras(args.scene)
ev = np.unique(np.round(np.linspace(0, len(cams) - 1, FR.N_VIEWS)).astype(int)).tolist()
views = sorted(set(ev) | set(view_split.TRAIN) | set(view_split.VAL) | set(view_split.TEST))
cfgs = (tuple(args.cfgs),)
d = os.path.join(OUT, f"prop_edges_{args.scene}_{args.name}")
os.makedirs(d, exist_ok=True)
FR.set_edge_source("canny", cfgs=cfgs)
n = []
for v in views:
    e = FR.photo_edge_map(rgb_paths[v]) > 0
    np.savez_compressed(os.path.join(d, f"v{v:03d}.npz"), native=e.astype(np.float16))
    n.append(int(e.sum()))
FR.set_edge_source("canny")
print(f"[dump] {args.scene}/{args.name} cfgs={cfgs}: {len(views)} views, "
      f"{np.mean(n):.0f} px/view -> {d}")
