#!/usr/bin/env python3
"""v04 Full-Scene Reconstruction: Coaxial Lathe Rings + Darboux RIBBON_3D + View-Dependent Occluding Contour Envelopes."""

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
    evaluate_network_vs_views,
    render_gaussian_bank,
    save_comparison_panel,
)
from vec_spline3d.schema import resolve_safe_path
from vec_spline3d.stage1_ray_clean import run_stage1_ray_clean
from vec_spline3d.stage2_scms_consolidate import run_stage2_scms_consolidate
from vec_spline3d.stage3_spline_topology import run_stage3_spline_topology
from vec_spline3d.stage4_diff_refine import run_stage4_diff_refine


def save_v04_evolution_panel(
    out_path: Path,
    view,
    raw_gs: dict[str, np.ndarray],
    v03_ink_gs: dict[str, np.ndarray] | None,
    net_v04,
    device: torch.device,
    crop_box: tuple[int, int, int, int] | None = None,
) -> None:
    """Save 5-column progression: [RGB | Raw C2L | v03 (Static Coaxial+Ribbon) | v04 Ink (+View Contours) | v04 Semantic Contours]."""
    dest = resolve_safe_path(out_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    rgb_u8 = (np.clip(view.rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    raw_u8 = (render_gaussian_bank(raw_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)

    v04_ink_gs = net_v04.to_line_gaussians(color_mode="ink", use_ribbon_surflets=True, camera_center=view.cam_center)
    v04_sem_gs = net_v04.to_line_gaussians(color_mode="edge_class", use_ribbon_surflets=True, camera_center=view.cam_center)
    v04_ink_u8 = (render_gaussian_bank(v04_ink_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)
    v04_sem_u8 = draw_vector_junctions_overlay(render_gaussian_bank(v04_sem_gs, view, device=device, bg_val=1.0), net_v04, view)

    panels = [rgb_u8, raw_u8]
    titles = [f"{view.view_name} RGB", "Raw C2L (11.5k)"]

    if v03_ink_gs is not None:
        v03_u8 = (render_gaussian_bank(v03_ink_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)
        panels.append(v03_u8)
        titles.append("v03 (Coaxial + Static Ribbon)")

    n_env = len(net_v04.lathe_generators) + len(net_v04.tube_generators)
    panels.extend([v04_ink_u8, v04_sem_u8])
    titles.extend([
        f"v04 Ink (+{n_env} View Contour Envelopes)",
        "v04 Semantics (Cyan=ViewContour, Gold=Ring)",
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
    out_dir = PROJECT_ROOT / "outputs/ficus_full_v04"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[v04 Full] Step 0: Loading 32 full-3DGS+C2L50 train views & 5 held-out test views...", flush=True)
    t_load = time.time()
    bundle = load_ficus_multimodal_bundle(num_extra_train_views=24)
    print(f"  Loaded {len(bundle.train_views)} train views + {len(bundle.eval_views)} eval views in {time.time() - t_load:.1f}s", flush=True)

    with np.load(bundle.canonical_gaussians_path, allow_pickle=False) as raw_z:
        raw_gs = {k: np.array(raw_z[k], copy=True) for k in ("means", "covariance", "opacity", "colors")}

    v03_npz = PROJECT_ROOT / "outputs/ficus_full_v03/resampled_ink_gaussians.npz"
    v03_ink_gs = None
    if v03_npz.is_file():
        with np.load(v03_npz, allow_pickle=False) as z3:
            v03_ink_gs = {k: np.array(z3[k], copy=True) for k in ("means", "covariance", "opacity", "colors")}

    print("[v04 Full] Stage 1A: Ray-cleaning base 8-view C2L fragments...", flush=True)
    base_segs, s1_base_stats = run_stage1_ray_clean(bundle, device=device, roi_bounds=None, num_ray_samples=96)

    print("[v04 Full] Stage 1B: Complementary 24-view 3D blind-spot skeleton seeding...", flush=True)
    t_seed = time.time()
    comp_segs, seed_stats = extract_complementary_multiview_seeds(
        bundle, base_segs, device=device, roi_bounds=None, min_uncovered_ratio=0.55, min_mv_corroboration=4
    )
    seed_stats["wall_seconds"] = round(time.time() - t_seed, 2)
    all_clean_segs = base_segs + comp_segs

    print("[v04 Full] Stage 2: Ray-anisotropic SCMS lateral consolidation...", flush=True)
    t_s2 = time.time()
    ridges, s2_stats = run_stage2_scms_consolidate(all_clean_segs, bundle.median_pixel_scale, num_scms_iters=5)
    s2_stats["wall_seconds"] = round(time.time() - t_s2, 2)

    print("[v04 Full] Stage 3: Coaxial Rings + Smooth Contour Envelopes (Lathe & Tubes) + MILP + RIBBON_3D...", flush=True)
    t_s3 = time.time()
    net_s3, s3_stats = run_stage3_spline_topology(
        ridges,
        bundle,
        device=device,
        enable_cocircular_consolidation=True,
        enable_coaxial_consolidation=True,
        enable_ribbon_annotation=True,
        enable_contour_generators=True,
    )
    s3_stats["wall_seconds"] = round(time.time() - t_s3, 2)
    print("  Stage 3 coaxial rings:", json.dumps(s3_stats["coaxial_ring_consolidation"]), flush=True)
    print("  Stage 3 contour generators:", json.dumps(s3_stats["contour_generators"]), flush=True)
    print("  Stage 3 summary:", json.dumps(s3_stats["post_topology_summary"]), flush=True)

    print("[v04 Full] Stage 4: Differentiable Envelope Horizon, Coaxial-Manifold & Darboux Ribbon Refinement...", flush=True)
    t_s4 = time.time()
    net_final, s4_stats = run_stage4_diff_refine(net_s3, bundle, device=device, num_steps=80, lr=2.5e-4)
    s4_stats["wall_seconds"] = round(time.time() - t_s4, 2)
    print("  Stage 4 summary:", json.dumps(s4_stats["final_summary"]), flush=True)

    net_final.metadata = {
        "mode": "full_scene_v04_contour_envelopes",
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

    print("[v04 Full] Evaluating Raw C2L vs v01 vs v02 vs v03 vs v04 on 8 build views & 5 held-out test views...", flush=True)
    orig_build_views = [v for v in bundle.train_views if v.is_original_c2l_build]

    v03_report_path = PROJECT_ROOT / "outputs/ficus_full_v03/EVALUATION_REPORT_V03.json"
    prev_doc = json.loads(v03_report_path.read_text(encoding="utf-8")) if v03_report_path.is_file() else {}

    eval_report = {
        "raw_c2l_baseline": prev_doc.get("raw_c2l_baseline"),
        "v01_8view_line_bspline": prev_doc.get("v01_8view_line_bspline"),
        "v02_32view_seed_and_arc3d": prev_doc.get("v02_32view_seed_and_arc3d"),
        "v03_coaxial_rings_and_ribbon3d": prev_doc.get("v03_coaxial_rings_and_ribbon3d"),
        "v04_occluding_contour_envelopes": {
            "summary": net_final.summary_stats(),
            "coaxial_families": [fam.to_dict() for fam in net_final.coaxial_families],
            "contour_generators": (
                [lg.to_dict() for lg in net_final.lathe_generators] + [tg.to_dict() for tg in net_final.tube_generators]
            ),
            "train_build_8views": evaluate_network_vs_views(
                net_final, orig_build_views, bundle.train_views, bundle.median_pixel_scale, device
            ),
            "heldout_test_5views": evaluate_network_vs_views(
                net_final, bundle.eval_views, bundle.train_views, bundle.median_pixel_scale, device
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
    report_path = out_dir / "EVALUATION_REPORT_V04.json"
    report_path.write_text(json.dumps(eval_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    target_views = [v for v in (orig_build_views + bundle.eval_views) if v.view_name in ("test_r_14", "test_r_79", "test_r_1", "train_r_7")]
    for pv in target_views:
        save_comparison_panel(
            out_dir / f"v04_full_{pv.view_name}.png", view=pv, raw_gs=raw_gs, net=net_final, device=device
        )
        save_v04_evolution_panel(
            out_dir / f"v04_evo_pot_{pv.view_name}.png",
            view=pv, raw_gs=raw_gs, v03_ink_gs=v03_ink_gs, net_v04=net_final, device=device,
            crop_box=(230, 450, 550, 770),
        )
        save_v04_evolution_panel(
            out_dir / f"v04_evo_stems_{pv.view_name}.png",
            view=pv, raw_gs=raw_gs, v03_ink_gs=v03_ink_gs, net_v04=net_final, device=device,
            crop_box=(250, 310, 550, 610),
        )
        save_v04_evolution_panel(
            out_dir / f"v04_evo_full_{pv.view_name}.png",
            view=pv, raw_gs=raw_gs, v03_ink_gs=v03_ink_gs, net_v04=net_final, device=device,
            crop_box=None,
        )

    print(f"[v04 Full] ALL COMPLETE in {time.time() - t0:.1f}s -> {report_path}", flush=True)


if __name__ == "__main__":
    main()
