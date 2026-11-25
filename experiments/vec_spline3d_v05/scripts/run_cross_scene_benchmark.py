#!/usr/bin/env python3
"""Cross-Scene Generalization Runner for vec_spline3d v04 across DTU MVS ('scan24', 'scan65') & NeRF Synthetic ('drums', 'chair')."""

from __future__ import annotations

import argparse
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

from vec_spline3d.multimodal_data import (
    load_c2l_registry_scene_bundle,
    load_synthetic_3dgs_scene_bundle,
)
from vec_spline3d.multiview_seed import extract_complementary_multiview_seeds
from vec_spline3d.render_eval import (
    draw_vector_junctions_overlay,
    evaluate_line_bank_vs_views,
    evaluate_network_vs_views,
    render_gaussian_bank,
)
from vec_spline3d.schema import resolve_safe_path
from vec_spline3d.stage1_ray_clean import run_stage1_ray_clean
from vec_spline3d.stage2_scms_consolidate import run_stage2_scms_consolidate
from vec_spline3d.stage3_spline_topology import run_stage3_spline_topology
from vec_spline3d.stage4_diff_refine import run_stage4_diff_refine


def save_cross_scene_panel(
    out_path: Path,
    view,
    raw_gs: dict[str, np.ndarray],
    net,
    device: torch.device,
    raw_label: str,
    crop_box: tuple[int, int, int, int] | None = None,
) -> None:
    """Save 4-column comparison: [Source RGB | Raw Baseline | vec_spline3d v04 Ink | v04 Primitives & Semantics]."""
    dest = resolve_safe_path(out_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    rgb_u8 = (np.clip(view.rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    raw_u8 = (render_gaussian_bank(raw_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)

    ink_gs = net.to_line_gaussians(color_mode="ink", use_ribbon_surflets=True, camera_center=view.cam_center)
    prim_gs = net.to_line_gaussians(color_mode="primitive", use_ribbon_surflets=True, camera_center=view.cam_center)
    sem_gs = net.to_line_gaussians(color_mode="edge_class", use_ribbon_surflets=True, camera_center=view.cam_center)

    ink_u8 = (render_gaussian_bank(ink_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)
    prim_u8 = draw_vector_junctions_overlay(render_gaussian_bank(prim_gs, view, device=device, bg_val=1.0), net, view)
    sem_u8 = draw_vector_junctions_overlay(render_gaussian_bank(sem_gs, view, device=device, bg_val=1.0), net, view)

    panels = [rgb_u8, raw_u8, ink_u8, prim_u8, sem_u8]
    n_env = len(net.lathe_generators) + len(net.tube_generators)
    n_coax = len(net.coaxial_families)
    n_pln = len(net.planar_patches)
    tags = []
    if n_coax > 0:
        tags.append(f"{n_coax}Coax")
    if n_env > 0:
        tags.append(f"{n_env}Env")
    if n_pln > 0:
        tags.append(f"{n_pln}Pln")
    tag_str = ("+" + "+".join(tags)) if tags else ""
    titles = [
        f"{net.scene_name} {view.view_name} ({view.split.upper()})",
        raw_label,
        f"vec_spline3d v05 ({len(net.curves)} curves{tag_str})",
        "Primitives (Blue=Line, Gold=Arc/Coax, Red=Bridge)",
        "RIBBON_3D Semantics (Grn=Sil, Blu=Crease, Org=Coax)",
    ]

    if crop_box is not None:
        x0, y0, x1, y1 = crop_box
        panels = [cv2.resize(p[y0:y1, x0:x1], (380, 380), interpolation=cv2.INTER_NEAREST) for p in panels]

    ph, pw = panels[0].shape[:2]
    header_h = 34
    grid = Image.new("RGB", (pw * len(panels), ph + header_h), color=(248, 248, 250))
    draw = ImageDraw.Draw(grid)
    for i, (pan, title) in enumerate(zip(panels, titles)):
        grid.paste(Image.fromarray(pan), (i * pw, header_h))
        draw.text((i * pw + 8, 9), title, fill=(20, 20, 25))
    grid.save(dest)


def run_single_scene(scene_name: str, device_str: str, extra_views: int) -> None:
    t0 = time.time()
    device = torch.device(device_str if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        torch.cuda.set_device(device)
    out_dir = PROJECT_ROOT / f"outputs/cross_scene_{scene_name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    is_c2l_reg = scene_name in ("scan24", "scan65", "ficus")
    print(f"[{scene_name}] Step 0: Loading multi-modal bundle on {device} (is_c2l_registry={is_c2l_reg})...", flush=True)
    t_load = time.time()
    if is_c2l_reg:
        bundle = load_c2l_registry_scene_bundle(scene_name, num_extra_train_views=extra_views, device=device)
        assert bundle.canonical_gaussians_path is not None
        with np.load(bundle.canonical_gaussians_path, allow_pickle=False) as raw_z:
            raw_gs = {k: np.array(raw_z[k], copy=True) for k in ("means", "covariance", "opacity", "colors")}
        raw_label = f"Raw C2L ({len(bundle.parents)} polylines)"
    else:
        bundle, raw_gs = load_synthetic_3dgs_scene_bundle(
            scene_name, num_base_views=8, num_extra_views=extra_views, device=device
        )
        raw_label = f"Raw 8-View Lifted ({len(bundle.parents)} chains)"

    print(
        f"[{scene_name}] Loaded {len(bundle.train_views)} train + {len(bundle.eval_views)} held-out eval views, "
        f"{len(bundle.parents)} base chains, p_med={bundle.median_pixel_scale:.6f} in {time.time() - t_load:.1f}s",
        flush=True,
    )

    print(f"[{scene_name}] Stage 1A: Multi-view space/depth carving & Viterbi ray re-triangulation...", flush=True)
    base_segs, s1_base_stats = run_stage1_ray_clean(bundle, device=device, roi_bounds=None, num_ray_samples=96)

    print(f"[{scene_name}] Stage 1B: Complementary 3D blind-spot seeding from {extra_views} extra views...", flush=True)
    t_seed = time.time()
    comp_segs, seed_stats = extract_complementary_multiview_seeds(
        bundle, base_segs, device=device, roi_bounds=None, min_uncovered_ratio=0.55, min_mv_corroboration=4
    )
    seed_stats["wall_seconds"] = round(time.time() - t_seed, 2)
    all_segs = base_segs + comp_segs

    print(f"[{scene_name}] Stage 2: Ray-anisotropic SCMS lateral consolidation ({len(all_segs)} segments)...", flush=True)
    t_s2 = time.time()
    ridges, s2_stats = run_stage2_scms_consolidate(all_segs, bundle.median_pixel_scale, num_scms_iters=5)
    s2_stats["wall_seconds"] = round(time.time() - t_s2, 2)

    print(f"[{scene_name}] Stage 3: Arbitrary-Axis Coaxial + Co-Circular + MILP + Planar Ortho + RIBBON_3D...", flush=True)
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

    print(f"[{scene_name}] Stage 4: Differentiable Multi-View Curve, Coaxial, Planar & Envelope Refinement...", flush=True)
    t_s4 = time.time()
    net_final, s4_stats = run_stage4_diff_refine(net_s3, bundle, device=device, num_steps=80, lr=2.5e-4)
    s4_stats["wall_seconds"] = round(time.time() - t_s4, 2)
    print(f"[{scene_name}] Stage 4 summary:", json.dumps(s4_stats["final_summary"]), flush=True)

    net_final.metadata = {
        "mode": "cross_scene_v05_arbitrary_coaxial_and_planar_ortho",
        "scene": scene_name,
        "has_silhouette_mask": bundle.has_silhouette_mask,
        "num_train_views": len(bundle.train_views),
        "num_eval_views": len(bundle.eval_views),
        "total_wall_seconds": round(time.time() - t0, 2),
    }
    saved_paths = net_final.save_package(out_dir)

    orig_build_views = [v for v in bundle.train_views if v.is_original_c2l_build]
    raw_build_metrics = evaluate_line_bank_vs_views(
        raw_gs, orig_build_views, bundle.train_views, bundle.median_pixel_scale, device
    )
    raw_eval_metrics = evaluate_line_bank_vs_views(
        raw_gs, bundle.eval_views, bundle.train_views, bundle.median_pixel_scale, device
    )
    v04_build_metrics = evaluate_network_vs_views(
        net_final, orig_build_views, bundle.train_views, bundle.median_pixel_scale, device
    )
    v04_eval_metrics = evaluate_network_vs_views(
        net_final, bundle.eval_views, bundle.train_views, bundle.median_pixel_scale, device
    )

    report = {
        "scene": scene_name,
        "domain": "DTU_RealWorld_MVS" if scene_name.startswith("scan") else "NeRF_Synthetic_3DGS",
        "has_silhouette_mask": bundle.has_silhouette_mask,
        "median_pixel_scale": bundle.median_pixel_scale,
        "raw_baseline": {
            "label": raw_label,
            "num_input_chains": len(bundle.parents),
            "num_input_nodes": int(sum(len(p.points_3d) for p in bundle.parents)),
            "train_build_8views": raw_build_metrics,
            "heldout_eval_views": raw_eval_metrics,
        },
        "vec_spline3d_v04": {
            "summary": net_final.summary_stats(),
            "coaxial_families": [f.to_dict() for f in net_final.coaxial_families],
            "contour_generators": (
                [g.to_dict() for g in net_final.lathe_generators] + [t.to_dict() for t in net_final.tube_generators]
            ),
            "planar_patches": [
                {k: v for k, v in pp.items() if not k.startswith("_")} for pp in net_final.planar_patches
            ],
            "train_build_8views": v04_build_metrics,
            "heldout_eval_views": v04_eval_metrics,
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
    rep_path = out_dir / "EVALUATION_REPORT.json"
    rep_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Render full + zoomed comparison panels on ALL held-out eval views (up to 3) + 1 build view!
    vis_views = list(bundle.eval_views[:3]) + list(orig_build_views[:1])
    for vw in vis_views:
        save_cross_scene_panel(
            out_dir / f"{scene_name}_full_{vw.view_name}.png",
            view=vw, raw_gs=raw_gs, net=net_final, device=device, raw_label=raw_label, crop_box=None,
        )
        cx0 = max(0, vw.width // 2 - 160)
        cy0 = max(0, vw.height // 2 - 160)
        save_cross_scene_panel(
            out_dir / f"{scene_name}_zoom_{vw.view_name}.png",
            view=vw, raw_gs=raw_gs, net=net_final, device=device, raw_label=raw_label,
            crop_box=(cx0, cy0, min(vw.width, cx0 + 320), min(vw.height, cy0 + 320)),
        )

    print(f"[{scene_name}] COMPLETE in {time.time() - t0:.1f}s -> {rep_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True, choices=["scan24", "scan65", "drums", "chair", "lego", "ficus"])
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--extra-views", type=int, default=16)
    args = parser.parse_args()
    run_single_scene(args.scene, args.device, args.extra_views)


if __name__ == "__main__":
    main()
