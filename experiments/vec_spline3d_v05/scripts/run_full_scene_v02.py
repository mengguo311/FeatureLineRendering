#!/usr/bin/env python3
"""v02 Full-Scene Reconstruction: 32-View Blind-Spot Seeding + ARC_3D / Co-Circular Ring Consolidation."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vec_spline3d.multimodal_data import load_ficus_multimodal_bundle
from vec_spline3d.multiview_seed import extract_complementary_multiview_seeds
from vec_spline3d.render_eval import (
    draw_vector_junctions_overlay,
    evaluate_line_bank_vs_views,
    render_gaussian_bank,
    save_comparison_panel,
)
from vec_spline3d.schema import resolve_safe_path
from vec_spline3d.stage1_ray_clean import run_stage1_ray_clean
from vec_spline3d.stage2_scms_consolidate import run_stage2_scms_consolidate
from vec_spline3d.stage3_spline_topology import run_stage3_spline_topology
from vec_spline3d.stage4_diff_refine import run_stage4_diff_refine


def save_v01_vs_v02_evolution_panel(
    out_path: Path,
    view,
    raw_gs: dict[str, np.ndarray],
    v01_ink_gs: dict[str, np.ndarray] | None,
    net_v02,
    device: torch.device,
    crop_box: tuple[int, int, int, int] | None = None,
) -> None:
    """Save 5-column visual progression: [RGB | Raw C2L | v01 (8-view Spline) | v02 Ink (32-view + ARC_3D) | v02 Colored Primitives (Gold=ARC_3D)]."""
    dest = resolve_safe_path(out_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    rgb_u8 = (np.clip(view.rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    raw_u8 = (render_gaussian_bank(raw_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)

    v02_ink_gs = net_v02.to_line_gaussians(color_mode="ink")
    v02_col_gs = net_v02.to_line_gaussians(color_mode="primitive")
    v02_ink_u8 = (render_gaussian_bank(v02_ink_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)
    v02_col_u8 = draw_vector_junctions_overlay(render_gaussian_bank(v02_col_gs, view, device=device, bg_val=1.0), net_v02, view)

    panels = [rgb_u8, raw_u8]
    titles = [f"{view.view_name} RGB", "Raw C2L (11.5k, 8-view)"]

    if v01_ink_gs is not None:
        v01_u8 = (render_gaussian_bank(v01_ink_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)
        panels.append(v01_u8)
        titles.append("v01 (8-view Line+BSpline)")

    panels.extend([v02_ink_u8, v02_col_u8])
    n_arcs = sum(1 for c in net_v02.curves.values() if c.primitive_type == "ARC_3D")
    titles.extend([
        f"v02 Ink (32-view + {n_arcs} ARC_3D)",
        "v02 Primitives (Gold=ARC_3D, Red=Bridge)",
    ])

    if crop_box is not None:
        x0, y0, x1, y1 = crop_box
        panels = [cv2.resize(p[y0:y1, x0:x1], (360, 360), interpolation=cv2.INTER_NEAREST) for p in panels]

    ph, pw = panels[0].shape[:2]
    header_h = 34
    grid = Image.new("RGB", (pw * len(panels), ph + header_h), color=(248, 248, 250))
    draw = ImageDraw.Draw(grid)
    for i, (pan, title) in enumerate(zip(panels, titles)):
        grid.paste(Image.fromarray(pan), (i * pw, header_h))
        draw.text((i * pw + 8, 9), title, fill=(20, 20, 25))
    grid.save(dest)


def main() -> None:
    t0 = time.time()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    out_dir = PROJECT_ROOT / "outputs/ficus_full_v02"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[v02 Full] Step 0: Loading 32 full-3DGS+C2L50 train views (8 original + 24 GPU-rendered) & 5 held-out test views...", flush=True)
    t_load = time.time()
    bundle = load_ficus_multimodal_bundle(num_extra_train_views=24)
    print(f"  Loaded {len(bundle.train_views)} train views + {len(bundle.eval_views)} eval views in {time.time() - t_load:.1f}s", flush=True)

    with np.load(bundle.canonical_gaussians_path, allow_pickle=False) as raw_z:
        raw_gs = {k: np.array(raw_z[k], copy=True) for k in ("means", "covariance", "opacity", "colors")}

    v01_npz = PROJECT_ROOT / "outputs/ficus_full_v01/resampled_ink_gaussians.npz"
    v01_ink_gs = None
    if v01_npz.is_file():
        with np.load(v01_npz, allow_pickle=False) as z1:
            v01_ink_gs = {k: np.array(z1[k], copy=True) for k in ("means", "covariance", "opacity", "colors")}

    print("[v02 Full] Stage 1A: Ray-cleaning base 8-view C2L fragments...", flush=True)
    t_s1 = time.time()
    base_segs, s1_base_stats = run_stage1_ray_clean(bundle, device=device, roi_bounds=None, num_ray_samples=96)
    print("  Stage 1A base done:", json.dumps(s1_base_stats), flush=True)

    print("[v02 Full] Stage 1B: Complementary 24-view blind-spot 2D skeleton seeding & foreground-depth ray lifting...", flush=True)
    t_seed = time.time()
    comp_segs, seed_stats = extract_complementary_multiview_seeds(
        bundle, base_segs, device=device, roi_bounds=None, min_uncovered_ratio=0.55, min_mv_corroboration=4
    )
    seed_stats["wall_seconds"] = round(time.time() - t_seed, 2)
    print("  Stage 1B complementary seeds:", json.dumps({k: v for k, v in seed_stats.items() if k != "seed_stage1_stats"}), flush=True)

    all_clean_segs = base_segs + comp_segs

    print("[v02 Full] Stage 2: Ray-anisotropic SCMS lateral consolidation across 32-view combined chains...", flush=True)
    t_s2 = time.time()
    ridges, s2_stats = run_stage2_scms_consolidate(all_clean_segs, bundle.median_pixel_scale, num_scms_iters=5)
    s2_stats["wall_seconds"] = round(time.time() - t_s2, 2)
    print("  Stage 2 done:", json.dumps(s2_stats), flush=True)

    print("[v02 Full] Stage 3: Co-circular ring consolidation + (LINE_3D / ARC_3D / CUBIC_BSPLINE_3D) + MILP topology...", flush=True)
    t_s3 = time.time()
    net_s3, s3_stats = run_stage3_spline_topology(ridges, bundle, device=device, enable_cocircular_consolidation=True)
    s3_stats["wall_seconds"] = round(time.time() - t_s3, 2)
    print("  Stage 3 cocircular:", json.dumps(s3_stats["cocircular_consolidation"]), flush=True)
    print("  Stage 3 summary:", json.dumps(s3_stats["post_topology_summary"]), flush=True)

    print("[v02 Full] Stage 4: Differentiable Line/Arc/BSpline refinement & dynamic topology cleanup...", flush=True)
    t_s4 = time.time()
    net_final, s4_stats = run_stage4_diff_refine(net_s3, bundle, device=device, num_steps=80, lr=2.5e-4)
    s4_stats["wall_seconds"] = round(time.time() - t_s4, 2)
    print("  Stage 4 summary:", json.dumps(s4_stats["final_summary"]), flush=True)

    net_final.metadata = {
        "mode": "full_scene_v02_32view_arc3d",
        "num_train_views": len(bundle.train_views),
        "num_eval_views": len(bundle.eval_views),
        "stage1_base": s1_base_stats,
        "stage1_complementary_seeding": seed_stats,
        "stage2": s2_stats,
        "stage3": s3_stats,
        "stage4": s4_stats,
        "total_wall_seconds": round(time.time() - t0, 2),
    }
    saved_paths = net_final.save_package(out_dir)

    print("[v02 Full] Evaluating Raw C2L vs v01 vs v02 on 8 original build views & 5 held-out test views...", flush=True)
    orig_build_views = [v for v in bundle.train_views if v.is_original_c2l_build]
    final_ink_gs = net_final.to_line_gaussians(color_mode="ink")

    eval_report = {
        "raw_c2l_baseline": {
            "num_primitives": len(bundle.parents),
            "train_build_8views": evaluate_line_bank_vs_views(
                raw_gs, orig_build_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
            "heldout_test_5views": evaluate_line_bank_vs_views(
                raw_gs, bundle.eval_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
        },
        "v01_8view_line_bspline": (
            json.loads((PROJECT_ROOT / "outputs/ficus_full_v01/EVALUATION_REPORT.json").read_text(encoding="utf-8"))["stage4_vec_spline3d_final"]
            if (PROJECT_ROOT / "outputs/ficus_full_v01/EVALUATION_REPORT.json").is_file()
            else None
        ),
        "v02_32view_seed_and_arc3d": {
            "summary": net_final.summary_stats(),
            "train_build_8views": evaluate_line_bank_vs_views(
                final_ink_gs, orig_build_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
            "heldout_test_5views": evaluate_line_bank_vs_views(
                final_ink_gs, bundle.eval_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
        },
        "saved_files": saved_paths,
        "stages": {
            "stage1_base": s1_base_stats,
            "stage1_complementary_seeding": seed_stats,
            "stage2": s2_stats,
            "stage3": s3_stats,
            "stage4": s4_stats,
        },
    }
    report_path = out_dir / "EVALUATION_REPORT_V02.json"
    report_path.write_text(json.dumps(eval_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Render rich progression panels: Full, Inner Canopy Zoom, and Pot Ribs + Stems Zoom!
    target_views = [v for v in (orig_build_views + bundle.eval_views) if v.view_name in ("test_r_14", "test_r_79", "test_r_1", "train_r_7")]
    for pv in target_views:
        save_comparison_panel(
            out_dir / f"v02_full_{pv.view_name}.png", view=pv, raw_gs=raw_gs, net=net_final, device=device
        )
        save_v01_vs_v02_evolution_panel(
            out_dir / f"evo_canopy_{pv.view_name}.png",
            view=pv, raw_gs=raw_gs, v01_ink_gs=v01_ink_gs, net_v02=net_final, device=device,
            crop_box=(240, 130, 560, 450),
        )
        save_v01_vs_v02_evolution_panel(
            out_dir / f"evo_pot_ribs_{pv.view_name}.png",
            view=pv, raw_gs=raw_gs, v01_ink_gs=v01_ink_gs, net_v02=net_final, device=device,
            crop_box=(230, 450, 550, 770),
        )

    print(f"[v02 Full] ALL COMPLETE in {time.time() - t0:.1f}s -> {report_path}", flush=True)


if __name__ == "__main__":
    main()
