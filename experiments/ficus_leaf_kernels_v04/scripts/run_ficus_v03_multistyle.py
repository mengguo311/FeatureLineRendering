#!/usr/bin/env python3
"""Run Phase 3 (v03): M1+M2 Per-Leaf Kernel Multi-Style Presets & Same-Plant Mixed-Leaf Showcase on GPU 1."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from leaf_kernels.ablation_evaluator import render_alpha_mask
from leaf_kernels.data_io import (
    CalibratedLeafView,
    GaussianCloud3D,
    PriorVectorGeometry,
    load_ficus_3dgs_cloud,
    load_ficus_views_and_v04_priors,
    resolve_read_path,
    resolve_write_path,
)
from leaf_kernels.kernel_partitioner import (
    LeafInstance3D,
    _build_closed_leaf_contour_3d,
    run_ficus_leaf_kernel_partitioning,
)
from leaf_kernels.leaf_refinement_v02 import (
    build_v02_uv_venation_color_banks,
    orient_leaf_frames_anatomically,
)
from leaf_kernels.multiview_leaf_cells import EnclosedLeaf2DViewMap, detect_2d_enclosed_leaves_for_view
from leaf_kernels.style_presets_v03 import (
    PRESET_ORDER,
    PRESET_TITLES,
    LeafKernelSubstrateM12,
    build_m1_m2_leaf_substrate,
    build_mixed_mode_a_crown_sectors,
    build_mixed_mode_b_rosette_mosaic,
    build_mixed_mode_c_sumie_hero_bloom,
    compose_mixed_style_plant,
)
from leaf_kernels.stylize_and_render import render_3dgs_cloud, render_stylized_with_occluded_ink


def _select_isolated_gpu() -> torch.device:
    if not torch.cuda.is_available():
        return torch.device("cpu")
    dev = torch.device("cuda:1" if torch.cuda.device_count() >= 2 else "cuda:0")
    torch.cuda.set_device(dev)
    return dev


def _load_or_compute_v01_partition(
    cloud: GaussianCloud3D,
    train_views: list[Any],
    priors: PriorVectorGeometry,
    device: torch.device,
) -> tuple[np.ndarray, list[LeafInstance3D]]:
    v01_dir = PROJECT_ROOT / "outputs/ficus_leaf_baseline_v01"
    npz_p = v01_dir / "leaf_partitioned_kernels.npz"
    json_p = v01_dir / "leaf_instances.json"
    if npz_p.is_file() and json_p.is_file():
        with np.load(resolve_read_path(npz_p), allow_pickle=False) as zp:
            kernel_labels = np.array(zp["kernel_leaf_id"], dtype=np.int32)
        meta_leaves = json.loads(resolve_read_path(json_p).read_text(encoding="utf-8"))["leaves"]
        leaves: list[LeafInstance3D] = []
        for entry in meta_leaves:
            lid = int(entry["leaf_id"])
            k_idxs = np.where(kernel_labels == lid)[0].astype(np.int32)
            act_k = k_idxs[cloud.opacities[k_idxs] >= 0.025]
            ref_k = act_k if len(act_k) >= 4 else k_idxs
            ctr, elen, ewid, enrm, lw, ww, tw, aw, loop3d = _build_closed_leaf_contour_3d(
                cloud.means[ref_k].astype(np.float64), cloud.scales[ref_k].astype(np.float64)
            )
            leaves.append(
                LeafInstance3D(
                    leaf_id=lid,
                    kernel_indices=k_idxs,
                    active_kernel_count=int(len(act_k)),
                    centroid=ctr,
                    axis_length=elen,
                    axis_width=ewid,
                    normal=enrm,
                    length_world=lw,
                    width_world=ww,
                    thickness_world=tw,
                    area_world=aw,
                    mean_vis_views=float(entry["mean_unoccluded_views"]),
                    closure_confidence=float(entry["closure_confidence"]),
                    visibility_tier=str(entry["visibility_tier"]),
                    boundary_loop_3d=loop3d,
                    mean_rgb=cloud.rgb_dc[ref_k].mean(axis=0).astype(np.float64),
                )
            )
        return kernel_labels, orient_leaf_frames_anatomically(cloud, kernel_labels, leaves, priors)

    kernel_labels, leaves, _, _ = run_ficus_leaf_kernel_partitioning(cloud, train_views, priors, device=device)
    return kernel_labels, orient_leaf_frames_anatomically(cloud, kernel_labels, leaves, priors)


def _save_horizontal_strip(
    dest: Path,
    imgs_u8: list[np.ndarray],
    titles: list[str],
    crop_box: tuple[int, int, int, int] | None = None,
    tile_size: int = 340,
) -> Path:
    safe_dest = resolve_write_path(dest)
    safe_dest.parent.mkdir(parents=True, exist_ok=True)
    if crop_box is not None:
        x0, y0, x1, y1 = crop_box
        tiles = [cv2.resize(im[y0:y1, x0:x1], (tile_size, tile_size), interpolation=cv2.INTER_NEAREST) for im in imgs_u8]
    else:
        tiles = imgs_u8
    th, tw = tiles[0].shape[:2]
    hh = 34
    canvas = Image.new("RGB", (tw * len(tiles), th + hh), color=(248, 248, 250))
    draw = ImageDraw.Draw(canvas)
    for i, (tile, ttl) in enumerate(zip(tiles, titles)):
        canvas.paste(Image.fromarray(tile), (i * tw, hh))
        draw.text((i * tw + 8, 9), ttl, fill=(20, 20, 25))
    canvas.save(safe_dest)
    return safe_dest


def _evaluate_model_metrics(
    styled_cloud: GaussianCloud3D,
    styled_rgb: np.ndarray,
    eval_views: list[CalibratedLeafView],
    eval_cmaps: dict[str, EnclosedLeaf2DViewMap],
    device: torch.device,
) -> dict[str, float]:
    """Measure silhouette IoU, render FPS, and within-2D-leaf chromatic/style coherence on 5 held-out test views."""
    ious: list[float] = []
    within_cell_mad: list[float] = []

    # Warmup & timed FPS benchmark
    _ = render_3dgs_cloud(styled_cloud, eval_views[0], device=device, override_colors=styled_rgb)
    t_fps0 = time.time()
    for ev in eval_views:
        ren = render_3dgs_cloud(styled_cloud, ev, device=device, override_colors=styled_rgb)
        cm = eval_cmaps[ev.view_name]
        for cid in range(1, cm.num_valid_cells + 1):
            mc = cm.cell_id_map == cid
            if int(mc.sum()) >= 40:
                med_c = np.median(ren[mc], axis=0)
                within_cell_mad.append(float(np.mean(np.abs(ren[mc] - med_c[None, :]))))
    fps = len(eval_views) / max(time.time() - t_fps0, 1e-5)

    for ev in eval_views:
        al = render_alpha_mask(styled_cloud, ev, device=device)
        gt_fg = ev.alpha > 0.50
        pr_fg = al > 0.50
        ious.append(100.0 * float(np.sum(gt_fg & pr_fg)) / max(int(np.sum(gt_fg | pr_fg)), 1))

    return {
        "silhouette_iou_vs_gt_pct": round(float(np.mean(ious)), 2),
        "within_leaf_chromatic_mad": round(float(np.mean(within_cell_mad)), 4) if within_cell_mad else 0.0,
        "render_fps_800x800": round(float(fps), 1),
    }


def _evaluate_mosaic_style_isolation(
    sub: LeafKernelSubstrateM12,
    mosaic_map: dict[int, str],
    eval_views: list[CalibratedLeafView],
    eval_cmaps: dict[str, EnclosedLeaf2DViewMap],
    device: torch.device,
) -> dict[str, float]:
    """Quantify style isolation when adjacent leaflets in the SAME rosette have DIFFERENT styles!

    Assigns each of the 6 style presets a pure orthogonal/distinct indicator color and checks what % of each
    unseen 2D closed leaf cell is purely dominated by a single preset indicator without neighbor-preset bleed.
    """
    style_indicator_lut = {
        "ghibli_gouache": np.array([0.95, 0.10, 0.10], dtype=np.float32),
        "sumie_ink_wash": np.array([0.10, 0.90, 0.15], dtype=np.float32),
        "ukiyoe_papercut": np.array([0.15, 0.25, 0.95], dtype=np.float32),
        "pointillist_stipple": np.array([0.95, 0.85, 0.10], dtype=np.float32),
        "sakura_watercolor": np.array([0.92, 0.15, 0.88], dtype=np.float32),
        "cyanotype_celadon": np.array([0.10, 0.88, 0.92], dtype=np.float32),
    }
    ind_colors = np.full((len(sub.kernel_labels), 3), 0.35, dtype=np.float32)
    for lf in sub.leaf_instances:
        st = mosaic_map[lf.leaf_id]
        ind_colors[sub.kernel_labels == lf.leaf_id] = style_indicator_lut[st]

    styled_c, _, _ = compose_mixed_style_plant(sub, mosaic_map)
    isolation_scores: list[float] = []
    for ev in eval_views:
        ren_ind = render_3dgs_cloud(styled_c, ev, device=device, override_colors=ind_colors)
        cm = eval_cmaps[ev.view_name]
        for cid in range(1, cm.num_valid_cells + 1):
            mc = cm.cell_id_map == cid
            if int(mc.sum()) >= 40:
                med_c = np.median(ren_ind[mc], axis=0)
                mad = float(np.mean(np.abs(ren_ind[mc] - med_c[None, :])))
                isolation_scores.append(100.0 * float(np.clip(1.0 - mad / 0.20, 0.0, 1.0)))

    return {
        "mosaic_neighbor_style_isolation_purity_pct": round(float(np.mean(isolation_scores)), 2)
        if isolation_scores
        else 0.0
    }


def main() -> None:
    t0 = time.time()
    device = _select_isolated_gpu()
    out_dir = resolve_write_path(PROJECT_ROOT / "outputs/ficus_multistyle_v03")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[MultiStyle v03] Running in isolated workspace={PROJECT_ROOT}, device={device}", flush=True)

    cloud_src = load_ficus_3dgs_cloud()
    train_views, eval_views, priors = load_ficus_views_and_v04_priors()
    base_labels, base_leaves = _load_or_compute_v01_partition(cloud_src, train_views, priors, device=device)

    print("[MultiStyle v03] Step 1: Building compact M1+M2 per-leaf Gaussian kernel substrate (M3 disabled)...", flush=True)
    t_sub = time.time()
    sub = build_m1_m2_leaf_substrate(cloud_src, base_labels, base_leaves, priors)
    sub_sec = round(time.time() - t_sub, 3)
    print(
        f"  M1+M2 substrate ready in {sub_sec}s: {len(sub.cloud.means)} total kernels, {len(sub.leaf_instances)} discrete 3D leaves.",
        flush=True,
    )

    # Export clean M1+M2 per-leaf kernel substrate NPZ!
    sub_npz = out_dir / "m1_m2_per_leaf_kernels.npz"
    inst_banks = build_v02_uv_venation_color_banks(sub.cloud, sub.kernel_labels, sub.leaf_instances, enable_m3_venation=False)
    np.savez_compressed(
        sub_npz,
        kernel_leaf_id=sub.kernel_labels.astype(np.int32),
        means=sub.cloud.means,
        scales=sub.cloud.scales,
        quats_wxyz=sub.cloud.quats_wxyz,
        opacities=sub.cloud.opacities,
        rgb_dc=sub.cloud.rgb_dc,
        instance_palette_rgb=inst_banks["instance_palette"],
    )

    eval_cmaps = {ev.view_name: detect_2d_enclosed_leaves_for_view(ev, priors) for ev in eval_views}

    # Step 2: Build all 6 uniform artistic style presets
    print("[MultiStyle v03] Step 2: Compiling 6 per-leaf artistic style presets...", flush=True)
    uniform_models: dict[str, tuple[GaussianCloud3D, np.ndarray]] = {}
    preset_metrics: dict[str, Any] = {}
    for pname in PRESET_ORDER:
        tr_theme = (
            "sumie_monochrome"
            if pname == "sumie_ink_wash"
            else ("cyanotype" if pname == "cyanotype_celadon" else "natural_warm")
        )
        c_sty, rgb_sty, _ = compose_mixed_style_plant(sub, pname, trunk_theme=tr_theme)
        uniform_models[pname] = (c_sty, rgb_sty)
        preset_metrics[pname] = {
            "title": PRESET_TITLES[pname],
            **_evaluate_model_metrics(c_sty, rgb_sty, eval_views, eval_cmaps, device=device),
        }
        print(f"  Preset {pname:20s} -> {preset_metrics[pname]}", flush=True)

    # Step 3: Build 3 Mixed-Style Same-Plant Showcases!
    print("[MultiStyle v03] Step 3: Composing 3 Mixed-Style Same-Plant Models (different leaf styles on ONE tree)...", flush=True)
    map_mode_a = build_mixed_mode_a_crown_sectors(sub)
    map_mode_b = build_mixed_mode_b_rosette_mosaic(sub)
    map_mode_c = build_mixed_mode_c_sumie_hero_bloom(sub)

    c_mix_a, rgb_mix_a, cnt_a = compose_mixed_style_plant(sub, map_mode_a, trunk_theme="natural_warm")
    c_mix_b, rgb_mix_b, cnt_b = compose_mixed_style_plant(sub, map_mode_b, trunk_theme="natural_warm")
    c_mix_c, rgb_mix_c, cnt_c = compose_mixed_style_plant(sub, map_mode_c, trunk_theme="sumie_monochrome")

    mosaic_iso = _evaluate_mosaic_style_isolation(sub, map_mode_b, eval_views, eval_cmaps, device=device)
    mixed_metrics = {
        "mode_a_crown_6zone_symphony": {
            "leaf_counts_by_style": cnt_a,
            **_evaluate_model_metrics(c_mix_a, rgb_mix_a, eval_views, eval_cmaps, device=device),
        },
        "mode_b_intra_rosette_mosaic": {
            "leaf_counts_by_style": cnt_b,
            **mosaic_iso,
            **_evaluate_model_metrics(c_mix_b, rgb_mix_b, eval_views, eval_cmaps, device=device),
        },
        "mode_c_sumie_hero_bloom": {
            "leaf_counts_by_style": cnt_c,
            **_evaluate_model_metrics(c_mix_c, rgb_mix_c, eval_views, eval_cmaps, device=device),
        },
    }
    print("  Mixed-plant metrics:", json.dumps(mixed_metrics, ensure_ascii=False), flush=True)

    # Export mixed-style plant presets & assignments NPZ/JSON
    np.savez_compressed(
        out_dir / "v03_mixed_style_color_banks.npz",
        kernel_leaf_id=sub.kernel_labels.astype(np.int32),
        mode_a_rgb=rgb_mix_a,
        mode_a_opacities=c_mix_a.opacities,
        mode_a_scales=c_mix_a.scales,
        mode_b_rgb=rgb_mix_b,
        mode_b_opacities=c_mix_b.opacities,
        mode_b_scales=c_mix_b.scales,
        mode_c_rgb=rgb_mix_c,
        mode_c_opacities=c_mix_c.opacities,
        mode_c_scales=c_mix_c.scales,
    )

    # Step 4: Render 7-Column Style Preset Galleries & 5-Column Mixed-Style Same-Plant Showcases on Held-Out Test Views!
    print("[MultiStyle v03] Step 4: Rendering held-out test view galleries & mixed-leaf showcases...", flush=True)
    saved_panels: list[str] = []
    crops = {
        "full": None,
        "canopy_zoom": (240, 120, 560, 440),
        "rosette_zoom": (330, 160, 610, 440),
    }

    for ev in eval_views:
        if ev.view_name not in ("test_r_79", "test_r_7", "test_r_1", "test_r_14"):
            continue
        orig_u8 = (render_3dgs_cloud(cloud_src, ev, device=device, override_colors=None) * 255.0 + 0.5).astype(np.uint8)
        inst_u8 = (
            render_3dgs_cloud(sub.cloud, ev, device=device, override_colors=inst_banks["instance_palette"]) * 255.0 + 0.5
        ).astype(np.uint8)

        # A) 7-Column Uniform Style Preset Gallery (on test_r_79, test_r_7, test_r_1)
        if ev.view_name in ("test_r_79", "test_r_7", "test_r_1"):
            gal_imgs = [orig_u8]
            gal_ink_imgs = [orig_u8]
            gal_titles = [f"{ev.view_name} Native 3DGS"]
            for pname in PRESET_ORDER:
                c_p, rgb_p = uniform_models[pname]
                r_pure = render_3dgs_cloud(c_p, ev, device=device, override_colors=rgb_p)
                r_ink = render_stylized_with_occluded_ink(
                    c_p, rgb_p, priors.ink_gaussians, ev, device=device, ink_opacity_scale=0.52
                )
                gal_imgs.append((r_pure * 255.0 + 0.5).astype(np.uint8))
                gal_ink_imgs.append((r_ink * 255.0 + 0.5).astype(np.uint8))
                gal_titles.append(PRESET_TITLES[pname])

            for tag, box in crops.items():
                p1 = _save_horizontal_strip(
                    out_dir / f"gallery_6presets_{tag}_{ev.view_name}.png", gal_imgs, gal_titles, crop_box=box, tile_size=300
                )
                p2 = _save_horizontal_strip(
                    out_dir / f"gallery_6presets_ink_{tag}_{ev.view_name}.png",
                    gal_ink_imgs,
                    gal_titles,
                    crop_box=box,
                    tile_size=300,
                )
                saved_panels.extend([str(p1), str(p2)])

        # B) 5-Column Same-Plant Multi-Style Leaf Showcase (Pure M1+M2 Kernels & +3D Ink)
        mix_pure_imgs = [
            orig_u8,
            inst_u8,
            (render_3dgs_cloud(c_mix_a, ev, device=device, override_colors=rgb_mix_a) * 255.0 + 0.5).astype(np.uint8),
            (render_3dgs_cloud(c_mix_b, ev, device=device, override_colors=rgb_mix_b) * 255.0 + 0.5).astype(np.uint8),
            (render_3dgs_cloud(c_mix_c, ev, device=device, override_colors=rgb_mix_c) * 255.0 + 0.5).astype(np.uint8),
        ]
        mix_ink_imgs = [
            orig_u8,
            inst_u8,
            (
                render_stylized_with_occluded_ink(c_mix_a, rgb_mix_a, priors.ink_gaussians, ev, device=device, ink_opacity_scale=0.50)
                * 255.0
                + 0.5
            ).astype(np.uint8),
            (
                render_stylized_with_occluded_ink(c_mix_b, rgb_mix_b, priors.ink_gaussians, ev, device=device, ink_opacity_scale=0.50)
                * 255.0
                + 0.5
            ).astype(np.uint8),
            (
                render_stylized_with_occluded_ink(c_mix_c, rgb_mix_c, priors.ink_gaussians, ev, device=device, ink_opacity_scale=0.50)
                * 255.0
                + 0.5
            ).astype(np.uint8),
        ]
        mix_titles = [
            f"{ev.view_name} Native 3DGS",
            f"M1+M2 Leaf Kernels ({len(sub.leaf_instances)})",
            "Mixed A: 6-Zone Crown Symphony",
            "Mixed B: Per-Leaflet Rosette Mosaic",
            "Mixed C: Sumi-e + Hero Rosettes",
        ]
        for tag, box in crops.items():
            if ev.view_name == "test_r_14" and tag != "full":
                continue
            m1 = _save_horizontal_strip(
                out_dir / f"mixed_same_plant_{tag}_{ev.view_name}.png", mix_pure_imgs, mix_titles, crop_box=box, tile_size=350
            )
            m2 = _save_horizontal_strip(
                out_dir / f"mixed_same_plant_ink_{tag}_{ev.view_name}.png", mix_ink_imgs, mix_titles, crop_box=box, tile_size=350
            )
            saved_panels.extend([str(m1), str(m2)])

    report = {
        "schema": "ficus_multistyle_leaves/v03",
        "substrate_method": "M1_OpacitySharpening + M2_SeamSplitting (M3_Dropped)",
        "num_total_kernels": int(len(sub.cloud.means)),
        "num_discrete_3d_leaves": int(len(sub.leaf_instances)),
        "substrate_build_seconds": sub_sec,
        "substrate_stats": sub.build_stats,
        "style_presets_evaluated_on_5_test_views": preset_metrics,
        "mixed_style_same_plant_modes": mixed_metrics,
        "saved_m1_m2_substrate_npz": str(sub_npz),
        "saved_panels": saved_panels,
        "total_wall_seconds": round(time.time() - t0, 2),
    }
    rep_path = out_dir / "MULTISTYLE_V03_REPORT.json"
    tmp_r = rep_path.with_name(f"{rep_path.name}.tmp-{os.getpid()}")
    tmp_r.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp_r, rep_path)
    print(f"[MultiStyle v03] COMPLETE in {time.time() - t0:.1f}s -> {rep_path}", flush=True)


if __name__ == "__main__":
    main()
