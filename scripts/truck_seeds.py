"""Experiment B — run the SHIPPED M1a seed recipe VERBATIM on Truck (real capture,
COLMAP-estimated poses). Option (a) from B_TRUCK_M1A_SPEC.md: run recipe as-is, accept
background edges, report honestly. NO method change: we only redirect common.load_cameras /
common.load_gaussians to the Truck ingestion adapter (src/truck_ingest.py). EDGE_CFGS,
N_VIEWS, KEEP_F, all constants FROZEN. Mesh-free.

Usage:  python truck_seeds.py smoke     # 1-view gbuffer smoke (blocker #4)
        python truck_seeds.py full      # full seed extraction, save carrier
"""
import os, sys, time
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/src"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
import numpy as np
from src import common, render, visibility
import truck_ingest

# --- redirect loaders to Truck (camera+gaussian adapter only; method untouched) ---
_tc = None
def _load_cameras(scene):
    cams, paths = truck_ingest.load_truck_cameras()
    global _tc; _tc = paths
    return cams, paths
def _load_gaussians(scene):
    return truck_ingest.load_truck_gaussians()
common.load_cameras = _load_cameras
common.load_gaussians = _load_gaussians

import m1a_seeds  # imports AFTER we know constants; it uses common.* at call time

def smoke():
    cams, paths = common.load_cameras("truck")
    g = common.load_gaussians("truck")
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    print(f"cams {len(cams)}  gaussians {len(g['mu'])}  defloat_keep {keep_g.sum()}")
    cam = cams[0]
    t0 = time.time()
    gb = render.render_gbuffer(g, keep_g, cam)
    dep = gb["depth"].cpu().numpy(); alp = gb["alpha"].cpu().numpy(); nrm = gb["normal"].cpu().numpy()
    print(f"gbuffer OK in {time.time()-t0:.1f}s  depth{dep.shape} alpha_fg_frac {(alp>0.5).mean():.3f} "
          f"depth_finite {np.isfinite(dep).mean():.3f}")
    # photo edge on real jpg (opaque -> else branch)
    import cv2
    de = m1a_seeds.photo_edge_dt(paths[0])
    e_density = (de < 1.0).mean()  # px on-edge
    print(f"photo_edge_dt OK  edge_px_frac {e_density:.4f} (synthetic recipe target ~0.03)")
    print("SMOKE OK")

def full():
    t0 = time.time()
    X_keep, s, keep, X = m1a_seeds.extract_seeds("truck", "overall")
    dt = time.time()-t0
    print(f"[truck/overall] {len(X)} gaussians -> {len(X_keep)} seeds  ({dt:.0f}s)")
    np.savez(os.path.expanduser("~/3dgs_line/tier1/out/truck_m1a_seeds.npz"),
             seeds=X_keep, keep=keep, score=s, X=X)
    print("saved out/truck_m1a_seeds.npz  seeds", len(X_keep))

if __name__ == "__main__":
    {"smoke": smoke, "full": full}[sys.argv[1] if len(sys.argv)>1 else "smoke"]()
