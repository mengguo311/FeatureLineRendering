#!/usr/bin/env python3
"""v05 Full-Scene Reconstruction on Ficus: Coaxial Rings + View-Dependent Envelopes + Planar Ortho + RIBBON_3D."""

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
from vec_spline3d.multiview_seed import extract_complementary_multiview_seeds
from vec_spline3d.render_eval import evaluate_network_vs_views
from vec_spline3d.stage1_ray_clean import run_stage1_ray_clean
from vec_spline3d.stage2_scms_consolidate import run_stage2_scms_consolidate
from vec_spline3d.stage3_spline_topology import run_stage3_spline_topology
from vec_spline3d.stage4_diff_refine import run_stage4_diff_refine


def main() -> None:
    t0 = time.time()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        torch.cuda.set_device(device)
    out_dir = PROJECT_ROOT / "outputs/ficus_full_v05"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[v05 Ficus] Step 0: Loading 32 full-3DGS+C2L50 train views & 5 held-out test views...", flush=True)
    t_load = time.time()
    bundle = load_ficus_multimodal_bundle(num_extra_train_views=24)
    print(
        f"  Loaded {len(bundle.train_views)} train views + {len(bundle.eval_views)} eval views in {time.time() - t_load:.1f}s",
        flush=True,
    )

    base_segs, s1_base_stats = run_stage1_ray_clean(bundle, device=device, roi_bounds=None, num_ray_samples=96)
    t_seed = time.time()
    comp_segs, seed_stats = extract_complementary_multiview_seeds(
        bundle, base_segs, device=device, roi_bounds=None, min_uncovered_ratio=0.55, min_mv_corroboration=4
    )
    seed_stats["wall_seconds"] = round(time.time() - t_seed, 2)
    all_clean_segs = base_segs + comp_segs

    t_s2 = time.time()
    ridges, s2_stats = run_stage2_scms_consolidate(all_clean_segs, bundle.median_pixel_scale, num_scms_iters=5)
    s2_stats["wall_seconds"] = round(time.time() - t_s2, 2)

    t_s3 = time.time()
    net_s3, s3_stats = run_stage3_spline_topology(
        ridges,
        bundle,
        device=device,
        enable_cocircular_consolidation=True,
        enable_coaxial_consolidation=True,
        enable_ribbon_annotation=True,
        enable_contour_generators=True,
        enable_planar_regularization=True,
    )
    s3_stats["wall_seconds"] = round(time.time() - t_s3, 2)

    t_s4 = time.time()
    net_final, s4_stats = run_stage4_diff_refine(net_s3, bundle, device=device, num_steps=80, lr=2.5e-4)
    s4_stats["wall_seconds"] = round(time.time() - t_s4, 2)
    print("[v05 Ficus] Stage 4 summary:", json.dumps(s4_stats["final_summary"]), flush=True)

    net_final.metadata = {
        "mode": "full_scene_v05_hybrid_primitives",
        "num_train_views": len(bundle.train_views),
        "num_eval_views": len(bundle.eval_views),
        "stage1_base": s1_base_stats,
        "stage1_complementary_seeding": {k: v for k, v in seed_stats.items() if k != "seed_stage1_stats"},
        "stage2": s2_stats,
        "stage3": s3_stats,
        "stage4": s4_stats,
        "total_wall_seconds": round(time.time() - t0, 2),
    }
    saved_paths = net_final.save_package(out_dir)

    orig_build_views = [v for v in bundle.train_views if v.is_original_c2l_build]
    v04_report_path = PROJECT_ROOT / "outputs/ficus_full_v04/EVALUATION_REPORT_V04.json"
    prev_doc = json.loads(v04_report_path.read_text(encoding="utf-8")) if v04_report_path.is_file() else {}

    eval_report = {
        "raw_c2l_baseline": prev_doc.get("raw_c2l_baseline"),
        "v04_occluding_contour_envelopes": prev_doc.get("v04_occluding_contour_envelopes"),
        "v05_arbitrary_coaxial_and_planar_ortho": {
            "summary": net_final.summary_stats(),
            "coaxial_families": [fam.to_dict() for fam in net_final.coaxial_families],
            "contour_generators": (
                [lg.to_dict() for lg in net_final.lathe_generators] + [tg.to_dict() for tg in net_final.tube_generators]
            ),
            "planar_patches": [
                {k: v for k, v in pp.items() if not k.startswith("_")} for pp in net_final.planar_patches
            ],
            "train_build_8views": evaluate_network_vs_views(
                net_final, orig_build_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
            "heldout_test_5views": evaluate_network_vs_views(
                net_final, bundle.eval_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
        },
        "stages": {
            "stage1_base": s1_base_stats,
            "stage1_complementary_seeding": {k: v for k, v in seed_stats.items() if k != "seed_stage1_stats"},
            "stage2": s2_stats,
            "stage3": s3_stats,
            "stage4": s4_stats,
        },
        "saved_files": saved_paths,
        "wall_seconds": round(time.time() - t0, 2),
    }
    out_json = out_dir / "EVALUATION_REPORT_V05.json"
    out_json.write_text(json.dumps(eval_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[v05 Ficus] COMPLETE in {time.time() - t0:.1f}s -> {out_json}", flush=True)


if __name__ == "__main__":
    main()
