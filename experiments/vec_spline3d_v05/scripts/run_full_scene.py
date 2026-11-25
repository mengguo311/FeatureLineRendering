#!/usr/bin/env python3
"""Full-Scene 3D Vectorized Parametric Curve Reconstruction & Ablation Evaluation on Ficus."""

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
from vec_spline3d.render_eval import evaluate_line_bank_vs_views, save_comparison_panel
from vec_spline3d.stage1_ray_clean import run_stage1_ray_clean
from vec_spline3d.stage2_scms_consolidate import run_stage2_scms_consolidate
from vec_spline3d.stage3_spline_topology import run_stage3_spline_topology
from vec_spline3d.stage4_diff_refine import run_stage4_diff_refine


def main() -> None:
    t0 = time.time()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    out_dir = PROJECT_ROOT / "outputs/ficus_full_v01"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[Full Scene] Loading Ficus multi-modal bundle (40 train views + 5 held-out test views)...", flush=True)
    bundle = load_ficus_multimodal_bundle(num_extra_train_views=32)

    with np.load(bundle.canonical_gaussians_path, allow_pickle=False) as raw_z:
        raw_gs = {k: np.array(raw_z[k], copy=True) for k in ("means", "covariance", "opacity", "colors")}

    print("[Full Scene] Stage 1: Multi-view visual-hull space carving & state=2 ray depth re-triangulation...", flush=True)
    t_s1 = time.time()
    clean_segs, s1_stats = run_stage1_ray_clean(bundle, device=device, roi_bounds=None, num_ray_samples=96)
    s1_stats["wall_seconds"] = round(time.time() - t_s1, 2)
    print("  Stage 1 done:", json.dumps(s1_stats), flush=True)

    print("[Full Scene] Stage 2: Ray-anisotropic SCMS lateral consolidation...", flush=True)
    t_s2 = time.time()
    ridges, s2_stats = run_stage2_scms_consolidate(clean_segs, bundle.median_pixel_scale, num_scms_iters=5)
    s2_stats["wall_seconds"] = round(time.time() - t_s2, 2)
    print("  Stage 2 done:", json.dumps(s2_stats), flush=True)

    print("[Full Scene] Stage 3: Adaptive Line/Cubic B-Spline fitting & global MILP topology...", flush=True)
    t_s3 = time.time()
    net_s3, s3_stats = run_stage3_spline_topology(ridges, bundle, device=device)
    s3_stats["wall_seconds"] = round(time.time() - t_s3, 2)
    print("  Stage 3 done:", json.dumps(s3_stats["post_topology_summary"]), flush=True)
    s3_ink_gs = net_s3.to_line_gaussians(color_mode="ink")

    print("[Full Scene] Stage 4: Multi-modal differentiable spline refinement & topology cleanup...", flush=True)
    t_s4 = time.time()
    net_final, s4_stats = run_stage4_diff_refine(net_s3, bundle, device=device, num_steps=80, lr=2.5e-4)
    s4_stats["wall_seconds"] = round(time.time() - t_s4, 2)
    print("  Stage 4 done:", json.dumps(s4_stats["final_summary"]), flush=True)

    net_final.metadata = {
        "mode": "full_scene",
        "num_train_views": len(bundle.train_views),
        "num_eval_views": len(bundle.eval_views),
        "stage1": s1_stats,
        "stage2": s2_stats,
        "stage3": s3_stats,
        "stage4": s4_stats,
        "total_wall_seconds": round(time.time() - t0, 2),
    }
    saved_paths = net_final.save_package(out_dir)

    print("[Full Scene] Running quantitative evaluation on 5 held-out test views & 8 build views...", flush=True)
    final_ink_gs = net_final.to_line_gaussians(color_mode="ink")
    build_views = [v for v in bundle.train_views if v.depth is not None]

    eval_report = {
        "raw_c2l_baseline": {
            "num_primitives": len(bundle.parents),
            "multiview_2plus_ratio": 1.0 / max(1, len(bundle.parents)),
            "median_arc_length": float(
                np.median([
                    np.linalg.norm(np.diff(p.points_3d, axis=0), axis=1).sum() for p in bundle.parents
                ])
            ),
            "train_build_8views": evaluate_line_bank_vs_views(
                raw_gs, build_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
            "heldout_test_5views": evaluate_line_bank_vs_views(
                raw_gs, bundle.eval_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
        },
        "stage3_pre_diff_refine": {
            "summary": s3_stats["post_topology_summary"],
            "heldout_test_5views": evaluate_line_bank_vs_views(
                s3_ink_gs, bundle.eval_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
        },
        "stage4_vec_spline3d_final": {
            "summary": net_final.summary_stats(),
            "train_build_8views": evaluate_line_bank_vs_views(
                final_ink_gs, build_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
            "heldout_test_5views": evaluate_line_bank_vs_views(
                final_ink_gs, bundle.eval_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
        },
        "saved_files": saved_paths,
        "stages": {
            "stage1": s1_stats,
            "stage2": s2_stats,
            "stage3": s3_stats,
            "stage4": s4_stats,
        },
    }

    report_path = out_dir / "EVALUATION_REPORT.json"
    report_path.write_text(json.dumps(eval_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Render full-frame and 2x zoom crop comparison panels across key train and test views
    panel_views = [v for v in (build_views[:2] + bundle.eval_views) if v.view_name in ("train_r_7", "test_r_1", "test_r_14", "test_r_79")]
    if not panel_views:
        panel_views = [build_views[0], bundle.eval_views[0]]

    for pv in panel_views:
        save_comparison_panel(
            out_dir / f"full_{pv.view_name}_comparison.png",
            view=pv,
            raw_gs=raw_gs,
            net=net_final,
            device=device,
            crop_box=None,
        )
        # Zoom crop on upper-right canopy spike zone & mid-left leaf rosette
        save_comparison_panel(
            out_dir / f"crop_canopy_{pv.view_name}_comparison.png",
            view=pv,
            raw_gs=raw_gs,
            net=net_final,
            device=device,
            crop_box=(260, 120, 560, 420),
        )
        save_comparison_panel(
            out_dir / f"crop_leaves_{pv.view_name}_comparison.png",
            view=pv,
            raw_gs=raw_gs,
            net=net_final,
            device=device,
            crop_box=(150, 320, 450, 620),
        )

    print(f"[Full Scene] ALL COMPLETE in {time.time() - t0:.1f}s -> {report_path}", flush=True)


if __name__ == "__main__":
    main()
