#!/usr/bin/env python
"""URS-E2E — run the DENSIFIED lego carrier through the real pull+prune pipeline.

*** METHOD PATH — MESH-FREE. Imports common/render/dt_pull/linelet/linelet_prune/view_split
    and the URS builder. It never imports mesh_oracle. Evaluation is done separately by
    scripts/urs_e2e_verdict.py / tune_lib.Harness. ***

The densified carrier is the URS GO configuration exactly as scored in out/urs_verdict.json:
TRAIN source views only, TEED ridge threshold 0.5, K_MIN=1 (no consensus culling), budget
89748. Seeds are placed where the unprojected TEED ridges land in object space — NOT snapped
to gaussian centroids.

MATCHED-COUNT ARMS. run_m1b's f dial selects round(f*N) gaussians. URS has no ranking, so the
analogue is a spatially uniform subsample: the carrier is voxel-deduped (bisected voxel size,
never a quality score) down to the SAME seed count the frozen-carrier arm uses at that f. That
makes each densified/frozen pair a like-for-like comparison at equal seed budget. A
full-budget arm (the whole 89748) is also produced.

Everything downstream of seeds_pos is run_m1b's own code, called directly.
"""
import argparse, json, os, sys, time

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src import common, render, dt_pull, linelet, linelet_prune, view_split   # noqa: E402
import run_m1b as RM                                                          # noqa: E402
from urs_build import build, voxel_dedup                                      # noqa: E402

OUT = os.path.join(TIER1, "out")
# URS GO config, verbatim from out/urs_verdict.json / urs_build defaults
URS_THR, URS_KMIN, URS_BUDGET, URS_STRIDE = 0.5, 1, 89748, 4
# pipeline config, identical to the m1b_lego_tc_* family
BASE = dict(edge="sharp", gate=True, gate_theta=20.0, gate_tau=0.015, gate_dilate=2,
            steps=100, lr=0.35, delta_max=5.0, huber=2.0, lam_s=0.02, lam_t=0.02,
            tau_in=1.5, min_ratio=0.50, max_med=1.5, len_thr=0.9,
            len_lo=0.25, len_hi=1.5)


def subsample_to(P, n_target, seed=0):
    """Spatially uniform reduction to ~n_target points by bisecting the dedup voxel.
    NOT a ranking: no point is preferred over another by any quality score."""
    if len(P) <= n_target:
        return P
    lo, hi = 1e-4, 1e-4
    while len(voxel_dedup(P, hi)) > n_target and hi < 1.0:
        hi *= 2.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if len(voxel_dedup(P, mid)) > n_target:
            lo = mid
        else:
            hi = mid
    return voxel_dedup(P, hi)


def run_arm(scene, seeds_pos, tag, cams, rgb_paths, g, keep_g, X, scale_g, verbose=True):
    """run_m1b's own pipeline from seeds_pos onward. Returns (json_path, npz_path)."""
    L = linelet.init_linelets(seeds_pos, X, scale_g)
    views = list(view_split.TRAIN)
    gate = dict(theta=BASE["gate_theta"], tau_depth=BASE["gate_tau"],
                dilate_px=BASE["gate_dilate"], soft=False)
    field = dt_pull.build_field(scene, g, keep_g, cams, rgb_paths, views,
                                cfg_name=BASE["edge"], device="cuda", gate=gate)
    res = dt_pull.pull(field, L, steps=BASE["steps"], lr=BASE["lr"],
                       delta_max=BASE["delta_max"], huber_delta=BASE["huber"],
                       lam_s=BASE["lam_s"], lam_t=BASE["lam_t"],
                       opt_tangent=True, opt_length=False, rel_tol=0.02,
                       two_sided=True, require_fg=False, dir_weight=False,
                       view_chunk=25, vis_every=25, lam_a=0.0)
    stat = linelet_prune.consensus_statistic(res["resid3"], res["vis"], knn=L["knn"])
    keep, st = linelet_prune.consensus_prune(
        res["resid"], res["vis"], tau_in=BASE["tau_in"], min_ratio=BASE["min_ratio"],
        max_med=BASE["max_med"], resid3=res["resid3"], use_resid3=False,
        keep_frac=None, stat=stat)
    P0, P1, t1, l1 = L["p0"], res["p"], res["t"], res["l"]
    npz = os.path.join(OUT, f"linelets_{scene}_{tag}_test.npz")
    np.savez(npz, p0=P0, p=P1, t=t1, l=l1, keep=keep,
             inlier_ratio=st["inlier_ratio"], median_resid=st["median_resid"],
             n_vis=res["vis"].sum(1) if res["vis"].ndim == 2 else res["vis"],
             seed_idx=np.arange(len(P1)))
    if verbose:
        print(f"  [{tag}] {len(P1)} linelets, keep {int(keep.sum())} "
              f"({keep.mean()*100:.1f}%) -> {os.path.basename(npz)}", flush=True)
    return npz, dict(n_seeds=int(len(seeds_pos)), n_keep=int(keep.sum()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--fs", default="0.40", help="comma list of matched f values")
    ap.add_argument("--full_budget", action="store_true")
    ap.add_argument("--tag_prefix", default="urse2e")
    a = ap.parse_args()

    cams, rgb_paths = common.load_cameras(a.scene)
    g = common.load_gaussians(a.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X, scale_g = g["mu"][keep_g], g["scale"][keep_g]
    N = len(X)
    print(f"[urs-e2e] {a.scene}: {N} de-floatered gaussians", flush=True)

    TR = list(view_split.TRAIN)[::URS_STRIDE]
    print(f"[urs-e2e] building URS carrier (GO config: TRAIN {len(TR)} views, "
          f"thr {URS_THR}, K{URS_KMIN}, budget {URS_BUDGET})", flush=True)
    P, diag = build(a.scene, TR, URS_THR, URS_BUDGET, k_min=URS_KMIN)
    print(f"[urs-e2e] URS carrier: {len(P)} pts (budget {URS_BUDGET}, "
          f"within={len(P) <= URS_BUDGET})", flush=True)

    meta = {"urs_diag": diag, "n_urs_carrier": int(len(P)),
            "budget_cap": URS_BUDGET, "within_budget": bool(len(P) <= URS_BUDGET),
            "arms": {}}
    for fs in [x for x in a.fs.split(",") if x]:
        f = float(fs)
        n_target = int(round(f * N))
        S = subsample_to(P, n_target)
        tag = f"{a.tag_prefix}{int(round(f*100)):03d}"
        print(f"[urs-e2e] arm f={f:.2f}: matched seed count {n_target} -> {len(S)} URS pts",
              flush=True)
        npz, info = run_arm(a.scene, S, tag, cams, rgb_paths, g, keep_g, X, scale_g)
        meta["arms"][tag] = {"f": f, "n_target": n_target, **info, "npz": npz}
    if a.full_budget:
        tag = f"{a.tag_prefix}full"
        print(f"[urs-e2e] arm FULL budget: {len(P)} URS pts", flush=True)
        npz, info = run_arm(a.scene, P, tag, cams, rgb_paths, g, keep_g, X, scale_g)
        meta["arms"][tag] = {"f": None, "n_target": len(P), **info, "npz": npz}

    json.dump(meta, open(os.path.join(OUT, "urs_e2e_build.json"), "w"),
              indent=1, default=float)
    print("\nwrote out/urs_e2e_build.json")
