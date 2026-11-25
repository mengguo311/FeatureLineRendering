#!/usr/bin/env python3
"""v03 Full-Scene Reconstruction: Coaxial Lathe Ring Family + Oriented Darboux RIBBON_3D & Semantic Decoupling."""

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


def save_v03_evolution_panel(
    out_path: Path,
    view,
    raw_gs: dict[str, np.ndarray],
    v02_ink_gs: dict[str, np.ndarray] | None,
    v03_ink_gs: dict[str, np.ndarray],
    v03_sem_gs: dict[str, np.ndarray],
    net_v03,
    device: torch.device,
    crop_box: tuple[int, int, int, int] | None = None,
) -> None:
    """Save 5-column progression: [RGB | Raw C2L | v02 Ink (Unconstrained Arcs) | v03 Ink (Coaxial + RIBBON_3D) | v03 Semantic Ribbons]."""
    dest = resolve_safe_path(out_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    rgb_u8 = (np.clip(view.rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    raw_u8 = (render_gaussian_bank(raw_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)

    v03_ink_u8 = (render_gaussian_bank(v03_ink_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)
    v03_sem_u8 = draw_vector_junctions_overlay(render_gaussian_bank(v03_sem_gs, view, device=device, bg_val=1.0), net_v03, view)

    panels = [rgb_u8, raw_u8]
    titles = [f"{view.view_name} RGB", "Raw C2L (11.5k)"]

    if v02_ink_gs is not None:
        v02_u8 = (render_gaussian_bank(v02_ink_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)
        panels.append(v02_u8)
        titles.append("v02 (32-view + ARC_3D)")

    n_rings = len(net_v03.coaxial_families[0].ring_heights) if net_v03.coaxial_families else 0
    panels.extend([v03_ink_u8, v03_sem_u8])
    titles.extend([
        f"v03 Ink ({n_rings} Coaxial Rings + RIBBON_3D)",
        "v03 Semantics (Gold=Ring, Grn=Sil, Blu=Crease)",
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
    out_dir = PROJECT_ROOT / "outputs/ficus_full_v03"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[v03 Full] Step 0: Loading 32 full-3DGS+C2L50 train views & 5 held-out test views...", flush=True)
    t_load = time.time()
    bundle = load_ficus_multimodal_bundle(num_extra_train_views=24)
    print(f"  Loaded {len(bundle.train_views)} train views + {len(bundle.eval_views)} eval views in {time.time() - t_load:.1f}s", flush=True)

    with np.load(bundle.canonical_gaussians_path, allow_pickle=False) as raw_z:
        raw_gs = {k: np.array(raw_z[k], copy=True) for k in ("means", "covariance", "opacity", "colors")}

    v02_npz = PROJECT_ROOT / "outputs/ficus_full_v02/resampled_ink_gaussians.npz"
    v02_ink_gs = None
    if v02_npz.is_file():
        with np.load(v02_npz, allow_pickle=False) as z2:
            v02_ink_gs = {k: np.array(z2[k], copy=True) for k in ("means", "covariance", "opacity", "colors")}

    print("[v03 Full] Stage 1A: Ray-cleaning base 8-view C2L fragments...", flush=True)
    base_segs, s1_base_stats = run_stage1_ray_clean(bundle, device=device, roi_bounds=None, num_ray_samples=96)

    print("[v03 Full] Stage 1B: Complementary 24-view 3D blind-spot skeleton seeding...", flush=True)
    t_seed = time.time()
    comp_segs, seed_stats = extract_complementary_multiview_seeds(
        bundle, base_segs, device=device, roi_bounds=None, min_uncovered_ratio=0.55, min_mv_corroboration=4
    )
    seed_stats["wall_seconds"] = round(time.time() - t_seed, 2)
    all_clean_segs = base_segs + comp_segs

    print("[v03 Full] Stage 2: Ray-anisotropic SCMS lateral consolidation...", flush=True)
    t_s2 = time.time()
    ridges, s2_stats = run_stage2_scms_consolidate(all_clean_segs, bundle.median_pixel_scale, num_scms_iters=5)
    s2_stats["wall_seconds"] = round(time.time() - t_s2, 2)

    print("[v03 Full] Stage 3: Coaxial Ring Family + Co-Circular Arcs + MILP Topology + Darboux RIBBON_3D...", flush=True)
    t_s3 = time.time()
    net_s3, s3_stats = run_stage3_spline_topology(
        ridges,
        bundle,
        device=device,
        enable_cocircular_consolidation=True,
        enable_coaxial_consolidation=True,
        enable_ribbon_annotation=True,
    )
    s3_stats["wall_seconds"] = round(time.time() - t_s3, 2)
    print("  Stage 3 coaxial rings:", json.dumps(s3_stats["coaxial_ring_consolidation"]), flush=True)
    print("  Stage 3 ribbon semantics:", json.dumps(s3_stats["ribbon_3d_annotation"]), flush=True)
    print("  Stage 3 summary:", json.dumps(s3_stats["post_topology_summary"]), flush=True)

    print("[v03 Full] Stage 4: Differentiable Coaxial-Manifold & Tri-Axial Darboux Ribbon Refinement...", flush=True)
    t_s4 = time.time()
    net_final, s4_stats = run_stage4_diff_refine(net_s3, bundle, device=device, num_steps=80, lr=2.5e-4)
    s4_stats["wall_seconds"] = round(time.time() - t_s4, 2)
    print("  Stage 4 summary:", json.dumps(s4_stats["final_summary"]), flush=True)

    net_final.metadata = {
        "mode": "full_scene_v03_coaxial_ribbon3d",
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

    print("[v03 Full] Evaluating Raw C2L vs v01 vs v02 vs v03 on 8 build views & 5 held-out test views...", flush=True)
    orig_build_views = [v for v in bundle.train_views if v.is_original_c2l_build]
    final_ink_gs = net_final.to_line_gaussians(color_mode="ink", use_ribbon_surflets=True)

    v02_report_path = PROJECT_ROOT / "outputs/ficus_full_v02/EVALUATION_REPORT_V02.json"
    prev_doc = json.loads(v02_report_path.read_text(encoding="utf-8")) if v02_report_path.is_file() else {}

    eval_report = {
        "raw_c2l_baseline": prev_doc.get("raw_c2l_baseline"),
        "v01_8view_line_bspline": prev_doc.get("v01_8view_line_bspline"),
        "v02_32view_seed_and_arc3d": prev_doc.get("v02_32view_seed_and_arc3d"),
        "v03_coaxial_rings_and_ribbon3d": {
            "summary": net_final.summary_stats(),
            "coaxial_families": [fam.to_dict() for fam in net_final.coaxial_families],
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
            "stage1_complementary_seeding": {k: v for k, v in seed_stats.items() if k != "seed_stage1_stats"},
            "stage2": s2_stats,
            "stage3": s3_stats,
            "stage4": s4_stats,
        },
    }
    report_path = out_dir / "EVALUATION_REPORT_V03.json"
    report_path.write_text(json.dumps(eval_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    final_sem_gs = net_final.to_line_gaussians(color_mode="edge_class", use_ribbon_surflets=True)
    target_views = [v for v in (orig_build_views + bundle.eval_views) if v.view_name in ("test_r_14", "test_r_79", "test_r_1", "train_r_7")]
    for pv in target_views:
        save_comparison_panel(
            out_dir / f"v03_full_{pv.view_name}.png", view=pv, raw_gs=raw_gs, net=net_final, device=device
        )
        save_v03_evolution_panel(
            out_dir / f"v03_evo_pot_{pv.view_name}.png",
            view=pv, raw_gs=raw_gs, v02_ink_gs=v02_ink_gs, v03_ink_gs=final_ink_gs, v03_sem_gs=final_sem_gs, net_v03=net_final, device=device,
            crop_box=(230, 450, 550, 770),
        )
        save_v03_evolution_panel(
            out_dir / f"v03_evo_canopy_{pv.view_name}.png",
            view=pv, raw_gs=raw_gs, v02_ink_gs=v02_ink_gs, v03_ink_gs=final_ink_gs, v03_sem_gs=final_sem_gs, net_v03=net_final, device=device,
            crop_box=(240, 130, 560, 450),
        )
        save_v03_evolution_panel(
            out_dir / f"v03_evo_full_{pv.view_name}.png",
            view=pv, raw_gs=raw_gs, v02_ink_gs=v02_ink_gs, v03_ink_gs=final_ink_gs, v03_sem_gs=final_sem_gs, net_v03=net_final, device=device,
            crop_box=None,
        )

    print(f"[v03 Full] ALL COMPLETE in {time.time() - t0:.1f}s -> {report_path}", flush=True)


if __name__ == "__main__":
    main()
