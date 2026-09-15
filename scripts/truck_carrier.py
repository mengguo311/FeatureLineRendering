"""Experiment B — MESH-FREE Truck carrier build (driver-side; agent login-expired).

Replicates the SHIPPED chair M1b method path VERBATIM (run_m1b.py lines 245-296),
frozen recipe: --f 0.30, --edge sharp, --gate (theta20/tau0.015/dilate2), --steps 100,
--pull_split train, tau_in1.5/min_ratio0.50/max_med1.5. NO per-scene tune.

Only redirects common.load_cameras/load_gaussians to src/truck_ingest (camera+gaussian
adapter), reuses the saved M1a OVERALL per-gaussian score (out/truck_m1a_seeds.npz), and
uses view_split.split(251) so TRAIN is 80% of the 251 Truck cams (generic, n_views param).

STOPS before the mesh Harness (Truck has no GT mesh -> mesh-free only). Saves
out/linelets_truck_gal_test.npz in the exact schema m1b_stroke_temporal.build_chains reads.
"""
import os, sys, time
TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "src"))
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))
import numpy as np
import torch
from src import common, render, linelet, dt_pull, linelet_prune, view_split
import truck_ingest

OUT = os.path.join(TIER1, "out")

# --- redirect loaders to Truck (adapter only; method path untouched) ---
def _load_cameras(scene):
    return truck_ingest.load_truck_cameras()
def _load_gaussians(scene):
    return truck_ingest.load_truck_gaussians()
common.load_cameras = _load_cameras
common.load_gaussians = _load_gaussians

# FROZEN chair recipe
F = 0.30
EDGE = "sharp"
GATE = dict(theta=20.0, tau_depth=0.015, dilate_px=2, soft=False)
STEPS = 100

def main():
    t_all = time.time()
    cams, rgb_paths = common.load_cameras("truck")
    g = common.load_gaussians("truck")
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep_g]
    scale_g = g["scale"][keep_g]
    print(f"[truck] {len(X)} de-floatered gaussians  ({len(cams)} cams)", flush=True)

    # reuse the SHIPPED M1a OVERALL score (per de-floatered gaussian); select top-F
    z = np.load(os.path.join(OUT, "truck_m1a_seeds.npz"))
    score = z["score"]
    if len(score) != len(X):
        raise RuntimeError(f"score/gaussian mismatch {len(score)} vs {len(X)}")
    idx = np.argsort(-score, kind="stable")[:int(round(F * len(X)))]
    seeds_pos = X[idx]
    print(f"  [seeds] f={F} -> {len(idx)} seeds (reused OVERALL score)", flush=True)

    t0 = time.time()
    L = linelet.init_linelets(seeds_pos, X, scale_g)
    print(f"  [linelet] init {len(L['p0'])} linelets in {time.time()-t0:.1f}s  "
          f"median half-length {np.median(L['l']):.5f} world  "
          f"tangent valid {L['t_valid'].mean():.3f}", flush=True)

    # honest held-out: pull consumes TRAIN only, split generic over 251 cams
    sp = view_split.split(len(cams))
    views = sp["train"]
    print(f"  [split] {len(cams)} cams -> TRAIN {len(views)} / VAL {len(sp['val'])} / TEST {len(sp['test'])}", flush=True)

    t0 = time.time()
    field = dt_pull.build_field("truck", g, keep_g, cams, rgb_paths, views,
                                cfg_name=EDGE, device="cuda", gate=GATE)
    gs = getattr(field, "gate_stats", None)
    print(f"  [field] {field.V} views, edge='{EDGE}', gate=ON, build {time.time()-t0:.1f}s", flush=True)
    if gs:
        print(f"  [gate] edge px {gs['n_before']} -> {gs['n_after']} "
              f"({100.0*gs['n_after']/max(gs['n_before'],1):.1f}% survive)", flush=True)

    t0 = time.time()
    res = dt_pull.pull(field, L, steps=STEPS)
    print(f"  [pull] {time.time()-t0:.1f}s  moved median {np.median(res['move_px']):.2f}px "
          f"p90 {np.percentile(res['move_px'],90):.2f}  n_vis median {np.median(res['vis'].sum(0)):.0f}", flush=True)

    stat = linelet_prune.consensus_statistic(res["resid3"], res["vis"], knn=L["knn"])
    keep, st = linelet_prune.consensus_prune(
        res["resid"], res["vis"], tau_in=1.5, min_ratio=0.50, max_med=1.5,
        resid3=res["resid3"], use_resid3=False, keep_frac=None, stat=stat)
    nv = st["n_vis"]
    print(f"  [prune] keep {keep.sum()}/{len(keep)} ({keep.mean()*100:.1f}%)  "
          f"inlier_ratio median {np.median(st['inlier_ratio']):.3f}  "
          f"median_resid median {np.median(st['median_resid']):.2f}px", flush=True)

    outp = os.path.join(OUT, "linelets_truck_gal_test.npz")
    np.savez(outp,
             p0=L["p0"], p=res["p"], t=res["t"], l=res["l"], keep=keep,
             inlier_ratio=st["inlier_ratio"], median_resid=st["median_resid"],
             n_vis=nv, seed_idx=idx)
    print(f"  wrote {outp}  ({time.time()-t_all:.0f}s total)", flush=True)
    print(f"CARRIER_DONE keep={int(keep.sum())} strokes_input", flush=True)

if __name__ == "__main__":
    main()
