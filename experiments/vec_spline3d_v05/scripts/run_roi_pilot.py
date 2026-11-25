#!/usr/bin/env python3
"""Fast ROI Pilot on Ficus: tests the full 4-stage parametric curve reconstruction on a dense leaf+stem cluster."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vec_spline3d.multimodal_data import load_ficus_multimodal_bundle
from vec_spline3d.render_eval import save_comparison_panel
from vec_spline3d.stage1_ray_clean import run_stage1_ray_clean
from vec_spline3d.stage2_scms_consolidate import run_stage2_scms_consolidate
from vec_spline3d.stage3_spline_topology import run_stage3_spline_topology
from vec_spline3d.stage4_diff_refine import run_stage4_diff_refine


def main() -> None:
    t0 = time.time()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    out_dir = PROJECT_ROOT / "outputs/ficus_roi_pilot"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[ROI Pilot] Loading Ficus multi-modal bundle (24 train views + 5 eval views)...", flush=True)
    bundle = load_ficus_multimodal_bundle(num_extra_train_views=16)

    # Select a representative dense upper-mid canopy + stem-branch 3D ROI box
    roi_min = np.array([-0.32, -0.32, 0.05], dtype=np.float64)
    roi_max = np.array([0.32, 0.32, 0.65], dtype=np.float64)

    print("[ROI Pilot] Stage 1: Multi-view visual-hull carving & state=2 ray re-triangulation...", flush=True)
    clean_segs, s1_stats = run_stage1_ray_clean(bundle, device=device, roi_bounds=(roi_min, roi_max), num_ray_samples=80)
    print("  Stage 1 stats:", json.dumps(s1_stats), flush=True)

    print("[ROI Pilot] Stage 2: Ray-anisotropic SCMS lateral consolidation...", flush=True)
    ridges, s2_stats = run_stage2_scms_consolidate(clean_segs, bundle.median_pixel_scale, num_scms_iters=5)
    print("  Stage 2 stats:", json.dumps(s2_stats), flush=True)

    print("[ROI Pilot] Stage 3: Adaptive Line/Cubic B-Spline fitting & MILP topology...", flush=True)
    net, s3_stats = run_stage3_spline_topology(ridges, bundle, device=device)
    print("  Stage 3 summary:", json.dumps(s3_stats["post_topology_summary"]), flush=True)

    print("[ROI Pilot] Stage 4: Differentiable multi-modal spline refinement...", flush=True)
    net, s4_stats = run_stage4_diff_refine(net, bundle, device=device, num_steps=50, lr=2.5e-4)
    print("  Stage 4 summary:", json.dumps(s4_stats["final_summary"]), flush=True)

    net.metadata = {
        "mode": "roi_pilot",
        "roi_min": roi_min.tolist(),
        "roi_max": roi_max.tolist(),
        "stage1": s1_stats,
        "stage2": s2_stats,
        "stage3": s3_stats,
        "stage4": s4_stats,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    saved = net.save_package(out_dir)

    with np.load(bundle.canonical_gaussians_path, allow_pickle=False) as raw_z:
        raw_means = raw_z["means"]
        in_roi = np.all((raw_means >= roi_min[None, :]) & (raw_means <= roi_max[None, :]), axis=1)
        raw_roi_gs = {k: np.array(raw_z[k][in_roi], copy=True) for k in ("means", "covariance", "opacity", "colors")}

    for v in [bundle.train_views[0], bundle.eval_views[0]]:
        save_comparison_panel(
            out_dir / f"pilot_{v.view_name}_panel.png",
            view=v,
            raw_gs=raw_roi_gs,
            net=net,
            device=device,
        )

    print(f"[ROI Pilot] Completed in {time.time() - t0:.1f}s -> {saved['json']}", flush=True)


if __name__ == "__main__":
    main()
