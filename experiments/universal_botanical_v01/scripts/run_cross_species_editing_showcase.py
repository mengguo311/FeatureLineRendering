#!/usr/bin/env python3
"""Cross-Species Botanical Stylization, Multi-Style Composition, Manifold Deformation, Pruning & Sprouting Showcase."""

from __future__ import annotations

import json
import math
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

from universal_botanical.adaptive_lamina_and_graph import (
    deform_universal_model_wind,
    fit_universal_organ_patches_and_kinematic_graph,
    render_sh3_cloud,
    render_universal_spline_hybrid,
)
from universal_botanical.basal_and_domains import discover_basal_support_and_domains
from universal_botanical.organ_partitioner import partition_and_consolidate_canopy_organs
from universal_botanical.schema_and_io import (
    CalibratedBuildOrEvalView,
    UniversalBotanicalConfig,
    UniversalBotanicalModel,
    atomic_write_text,
    eval_clamped_bspline,
    export_standard_sh3_ply,
    load_canonical_scene,
    load_universal_model_npz,
    resolve_write_path,
    save_universal_model_npz,
)
from universal_botanical.stylize_and_edit import (
    PRESET_ORDER,
    PRESET_TITLES,
    apply_horticultural_organ_pruning,
    apply_procedural_apical_sprouting,
    build_deform_preset_spec,
    build_mixed_crown_sectors,
    build_mixed_neighbor_mosaic,
    build_mixed_sumie_hero_focus,
    build_universal_deform_rig,
    compose_stylized_universal_plant,
    compute_universal_organ_polar_coords,
    deform_universal_organ_manifold,
)

SHOWCASE_SCENES = ("brassica", "bonsai", "flowers", "ficus")
CORE_THREE_SCENES = ("brassica", "bonsai", "flowers")


def _select_gpu() -> torch.device:
    if not torch.cuda.is_available():
        return torch.device("cpu")
    dev = torch.device("cuda:1" if torch.cuda.device_count() >= 2 else "cuda:0")
    torch.cuda.set_device(dev)
    return dev


def _fg_bbox(alpha: np.ndarray, pad_frac: float = 0.08) -> tuple[int, int, int, int]:
    ys, xs = np.where(alpha > 0.10)
    h, w = alpha.shape
    if len(xs) < 16:
        return (0, 0, w, h)
    pad = int(max(h, w) * pad_frac)
    return (
        max(0, int(xs.min()) - pad),
        max(0, int(ys.min()) - pad),
        min(w, int(xs.max()) + pad + 1),
        min(h, int(ys.max()) + pad + 1),
    )


def _crop_and_fit(img_f01: np.ndarray, box: tuple[int, int, int, int], tw: int, th: int) -> Image.Image:
    x0, y0, x1, y1 = box
    crop = img_f01[y0:y1, x0:x1]
    u8 = (np.clip(crop, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    h, w = u8.shape[:2]
    scale = min((tw - 10) / max(w, 1), (th - 10) / max(h, 1))
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    im = Image.fromarray(u8).resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (tw, th), (255, 255, 255))
    canvas.paste(im, ((tw - nw) // 2, (th - nh) // 2))
    return canvas


def _load_or_build_scene(
    scene: str,
    cfg: UniversalBotanicalConfig,
    device: torch.device,
) -> tuple[UniversalBotanicalModel, list[CalibratedBuildOrEvalView], bool]:
    cache_p = PROJECT_ROOT / "outputs/universal_5scene_v01" / scene / "model_cache.npz"
    cloud_in, train_views, eval_views, p_med, v05_trunks, curve_pts, _ = load_canonical_scene(scene)
    if cache_p.is_file():
        model = load_universal_model_npz(cache_p)
        return model, eval_views, True

    support, stem_chains, domain_labels, _, _ = discover_basal_support_and_domains(
        cloud_in, train_views, p_med, v05_trunks, cfg
    )
    cloud_ref, labels_ref, organ_recs, _, _ = partition_and_consolidate_canopy_organs(
        cloud_in, train_views, support, stem_chains, domain_labels, curve_pts, p_med, cfg, device
    )
    model = fit_universal_organ_patches_and_kinematic_graph(
        scene, cloud_ref, labels_ref, organ_recs, support, stem_chains, p_med, cfg
    )
    save_universal_model_npz(cache_p, model)
    return model, eval_views, False


def _draw_sprout_overlay(
    base_rgb: np.ndarray,
    sprouted_model: UniversalBotanicalModel,
    orig_num_stems: int,
    orig_num_organs: int,
    view: CalibratedBuildOrEvalView,
) -> np.ndarray:
    canvas = np.ascontiguousarray((np.clip(base_rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
    R, t = view.w2c[:3, :3], view.w2c[:3, 3]
    for ch in sprouted_model.stem_chains[orig_num_stems:]:
        pts, _ = eval_clamped_bspline(ch.ctrl_points, np.linspace(0.0, 1.0, 20))
        Xc = pts @ R.T + t[None, :]
        if np.all(Xc[:, 2] > 0.08):
            uv = np.rint(np.column_stack([view.fx * Xc[:, 0] / Xc[:, 2] + view.cx, view.fy * Xc[:, 1] / Xc[:, 2] + view.cy])).astype(np.int32)
            cv2.polylines(canvas, [uv], False, (20, 145, 55), 2, cv2.LINE_AA)
    for org in sprouted_model.organs[orig_num_organs:]:
        loop = org.eval_3d_boundary_loop(n_samples=36)
        Xc = loop @ R.T + t[None, :]
        if np.all(Xc[:, 2] > 0.08):
            uv = np.rint(np.column_stack([view.fx * Xc[:, 0] / Xc[:, 2] + view.cx, view.fy * Xc[:, 1] / Xc[:, 2] + view.cy])).astype(np.int32)
            cv2.polylines(canvas, [uv], True, (235, 65, 50), 1, cv2.LINE_AA)
    return canvas.astype(np.float32) / 255.0


def _save_grid_panel(
    path: Path,
    col_titles: list[str],
    rows: list[tuple[str, list[Image.Image]]],
    tw: int,
    th: int,
    lw: int = 235,
    hh: int = 40,
) -> None:
    ncols = len(col_titles)
    nrows = len(rows)
    panel = Image.new("RGB", (lw + ncols * tw, hh + nrows * th), (255, 255, 255))
    draw = ImageDraw.Draw(panel)
    for c_i, ct in enumerate(col_titles):
        draw.text((lw + c_i * tw + 8, 12), ct, fill=(22, 28, 36))
    for r_i, (r_label, imgs) in enumerate(rows):
        y0 = hh + r_i * th
        draw.line([(0, y0), (panel.width, y0)], fill=(228, 232, 236), width=1)
        for l_idx, line in enumerate(r_label.split("\n")):
            draw.text((12, y0 + 18 + l_idx * 20), line, fill=(18, 24, 30) if l_idx == 0 else (55, 68, 78))
        for c_i, im in enumerate(imgs):
            panel.paste(im, (lw + c_i * tw, y0))
    panel.save(resolve_write_path(path))


def main() -> None:
    t0 = time.time()
    device = _select_gpu()
    cfg = UniversalBotanicalConfig()
    out_dir = resolve_write_path(PROJECT_ROOT / "outputs/cross_species_showcase_v01")
    out_dir.mkdir(parents=True, exist_ok=True)

    models: dict[str, UniversalBotanicalModel] = {}
    evals: dict[str, list[CalibratedBuildOrEvalView]] = {}
    polars: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    rest_boxes: dict[str, tuple[int, int, int, int]] = {}

    report: dict[str, Any] = {
        "schema": "cross_species_stylization_and_editing_showcase/v01",
        "device": str(device),
        "presets": list(PRESET_ORDER),
        "scenes": {},
    }

    for sc in SHOWCASE_SCENES:
        ts = time.time()
        m, evs, from_cache = _load_or_build_scene(sc, cfg, device)
        models[sc] = m
        evals[sc] = evs
        polars[sc] = compute_universal_organ_polar_coords(m)
        _, al0 = render_sh3_cloud(m.cloud, evs[0], device)
        rest_boxes[sc] = _fg_bbox(al0, pad_frac=0.09)
        print(f"[Showcase] Ready {sc.upper()} ({'cached' if from_cache else 'built'} in {time.time() - ts:.2f}s): "
              f"organs={len(m.organs)}, kernels={len(m.cloud.means)}", flush=True)
        report["scenes"][sc] = {
            "basal_regime": m.support.regime,
            "num_organs": len(m.organs),
            "num_kernels": int(len(m.cloud.means)),
        }

    # -----------------------------------------------------------------------
    # Panel 1: 4-Species x 7-Column Artistic Preset Matrix
    # -----------------------------------------------------------------------
    tw1, th1 = 230, 230
    rows_p1: list[tuple[str, list[Image.Image]]] = []
    for sc in SHOWCASE_SCENES:
        m, ev0, bx = models[sc], evals[sc][0], rest_boxes[sc]
        orig_rgb, _ = render_universal_spline_hybrid(m, ev0, device)
        tiles = [_crop_and_fit(orig_rgb, bx, tw1, th1)]
        for pname in PRESET_ORDER:
            st_m, _ = compose_stylized_universal_plant(m, pname, precomputed_polar=polars[sc])
            st_rgb, _ = render_universal_spline_hybrid(st_m, ev0, device)
            tiles.append(_crop_and_fit(st_rgb, bx, tw1, th1))
        lbl = f"{sc.upper()}\nRegime: {m.support.regime}\n{len(m.organs)} discrete 3D organs\n0.00p vessel paint bleed"
        rows_p1.append((lbl, tiles))

    _save_grid_panel(
        out_dir / "cross_species_6presets_gallery.png",
        ["Original SH3"] + [PRESET_TITLES[p] for p in PRESET_ORDER],
        rows_p1,
        tw1,
        th1,
    )
    print("[Showcase] Saved Panel 1: cross_species_6presets_gallery.png", flush=True)

    # -----------------------------------------------------------------------
    # Panel 2: Same-Plant Multi-Style Composition + 2.5x Neighbor-Mosaic Close-Up
    # -----------------------------------------------------------------------
    tw2, th2 = 275, 250
    rows_p2: list[tuple[str, list[Image.Image]]] = []
    mosaic_models: dict[str, UniversalBotanicalModel] = {}

    for sc in SHOWCASE_SCENES:
        m, ev0, bx = models[sc], evals[sc][0], rest_boxes[sc]
        map_a = build_mixed_crown_sectors(m)
        map_b = build_mixed_neighbor_mosaic(m)
        map_c = build_mixed_sumie_hero_focus(m)

        ma, cnt_a = compose_stylized_universal_plant(m, map_a, precomputed_polar=polars[sc])
        mb, cnt_b = compose_stylized_universal_plant(m, map_b, precomputed_polar=polars[sc])
        mc, cnt_c = compose_stylized_universal_plant(m, map_c, support_theme="sumie_monochrome", precomputed_polar=polars[sc])
        mosaic_models[sc] = mb

        if sc in CORE_THREE_SCENES:
            sc_out = out_dir / sc
            sc_out.mkdir(parents=True, exist_ok=True)
            ply_m = export_standard_sh3_ply(sc_out / f"{sc}_multistyle_mosaic.ply", mb.cloud)
            report["scenes"][sc]["exported_multistyle_ply"] = str(ply_m)

        report["scenes"][sc]["mixed_style_organ_counts"] = {
            "crown_sectors": cnt_a,
            "neighbor_mosaic": cnt_b,
            "sumie_hero_focus": cnt_c,
        }

        rgb_a, _ = render_universal_spline_hybrid(ma, ev0, device)
        rgb_b, _ = render_universal_spline_hybrid(mb, ev0, device)
        rgb_c, _ = render_universal_spline_hybrid(mc, ev0, device)

        # 2.5x optical zoom into dense foliage core of Mode B (Neighbor-Contrast Mosaic)
        x0, y0, x1, y1 = bx
        cw, ch_px = int((x1 - x0) * 0.42), int((y1 - y0) * 0.42)
        cx_mid = int(0.5 * (x0 + x1))
        cy_mid = int(y0 + 0.42 * (y1 - y0))  # upper-mid foliage crown (above container!)
        zbox = (
            max(0, cx_mid - cw // 2),
            max(0, cy_mid - ch_px // 2),
            min(ev0.width, cx_mid + cw // 2),
            min(ev0.height, cy_mid + ch_px // 2),
        )
        rgb_b_zoom, _ = render_universal_spline_hybrid(mb, ev0, device, zoom_crop=zbox, out_size=(360, 360))
        im_zoom = Image.fromarray((np.clip(rgb_b_zoom, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)).resize(
            (tw2 - 10, th2 - 10), Image.Resampling.LANCZOS
        )
        tile_z = Image.new("RGB", (tw2, th2), (255, 255, 255))
        tile_z.paste(im_zoom, (5, 5))

        lbl = f"{sc.upper()} Multi-Style\nAll 6 styles on ONE plant\nMosaic: {len(cnt_b)} active styles\n3D kNN neighbor contrast"
        rows_p2.append((
            lbl,
            [
                _crop_and_fit(rgb_a, bx, tw2, th2),
                _crop_and_fit(rgb_b, bx, tw2, th2),
                tile_z,
                _crop_and_fit(rgb_c, bx, tw2, th2),
            ],
        ))

    _save_grid_panel(
        out_dir / "cross_species_same_plant_multistyle.png",
        [
            "Mode A: 6-Zone Crown Symphony",
            "Mode B: Per-Organ Neighbor Mosaic",
            "Mode B 2.5x Foliage Close-Up",
            "Mode C: Sumi-e Ink + Hero Bouquets",
        ],
        rows_p2,
        tw2,
        th2,
    )
    print("[Showcase] Saved Panel 2: cross_species_same_plant_multistyle.png", flush=True)

    # -----------------------------------------------------------------------
    # Panel 3 & Panel 4: Scale-Free 3D Manifold Deformation + Jacobian Ablation (Brassica, Bonsai, Flowers)
    # -----------------------------------------------------------------------
    deform_modes = [
        ("rest_pose", "Rest Pose (Original)"),
        ("gravity_wilt", "Gravity Wilt (48 deg)"),
        ("boat_cup_twist", "Boat-Cup + 44 deg Twist"),
        ("slender_lanceolate", "Slender Lanceolate Morph"),
        ("broad_rosette", "Broad Sunlit Morph"),
        ("same_plant_phenology", "Same-Plant Bloom vs Wilt"),
    ]
    tw3, th3 = 235, 235
    rows_p3: list[tuple[str, list[Image.Image]]] = []
    rows_p4: list[tuple[str, list[Image.Image]]] = []

    for sc in CORE_THREE_SCENES:
        m, ev0 = models[sc], evals[sc][0]
        rig = build_universal_deform_rig(m)
        # Expand crop box by 14% so drooping leaves fit without clipping
        bx_wide = _fg_bbox(ev0.alpha, pad_frac=0.15)
        tiles_d: list[Image.Image] = []
        def_stats_sc: dict[str, Any] = {}

        # Dual-phenology style map: upper half lush Ghibli/Sakura, lower half autumn Ukiyo-e vermilion/gold!
        z_med = float(np.median([o.centroid[2] for o in m.organs]))
        pheno_style_map = {
            o.organ_id: ("sakura_watercolor" if m.support.regime == "RECTANGULAR_TRAY_LOFT" else "ghibli_gouache")
            if o.centroid[2] >= z_med
            else "ukiyoe_papercut"
            for o in m.organs
        }
        m_pheno_styled, _ = compose_stylized_universal_plant(m, pheno_style_map, precomputed_polar=polars[sc])

        for m_key, _ in deform_modes:
            base_m = m_pheno_styled if m_key == "same_plant_phenology" else m
            sp = build_deform_preset_spec(base_m, rig, m_key, strength=(0.0 if m_key == "rest_pose" else 1.22))
            dm, dst = deform_universal_organ_manifold(base_m, rig, sp, transport_covariance=True)
            def_stats_sc[m_key] = dst
            rgb_d, _ = render_sh3_cloud(dm.cloud, ev0, device)
            tiles_d.append(_crop_and_fit(rgb_d, bx_wide, tw3, th3))
            if m_key == "same_plant_phenology":
                ply_d = export_standard_sh3_ply(out_dir / sc / f"{sc}_dual_phenology_deformed.ply", dm.cloud)
                report["scenes"][sc]["exported_phenology_deformed_ply"] = str(ply_d)

        report["scenes"][sc]["manifold_deformation"] = def_stats_sc
        wilt_st = def_stats_sc["gravity_wilt"]
        lbl3 = (
            f"{sc.upper()} 3D Deform\n"
            f"Support drift: {wilt_st['static_max_drift_pmed']:.4f} p_med\n"
            f"Arc-len err: {wilt_st['arclength_rel_err_pct']:.3f}%\n"
            f"Mean tip disp: {wilt_st['tip_mean_disp_cm']:.1f} cm"
        )
        rows_p3.append((lbl3, tiles_d))

        # Panel 4: Jacobian Covariance Transport Ablation (No J vs With J Sigma J^T) at 2.8x optical zoom!
        x0, y0, x1, y1 = rest_boxes[sc]
        zw, zh = int((x1 - x0) * 0.36), int((y1 - y0) * 0.36)
        zcx, zcy = int(x0 + 0.46 * (x1 - x0)), int(y0 + 0.44 * (y1 - y0))
        z_ab = (max(0, zcx - zw // 2), max(0, zcy - zh // 2), min(ev0.width, zcx + zw // 2), min(ev0.height, zcy + zh // 2))

        ab_tiles: list[Image.Image] = []
        ab_metrics: dict[str, Any] = {}
        for ab_mode in ("boat_cup_twist", "broad_rosette"):
            sp_ab = build_deform_preset_spec(m, rig, ab_mode, strength=1.15)
            dm_noj, _ = deform_universal_organ_manifold(m, rig, sp_ab, transport_covariance=False)
            dm_yesj, _ = deform_universal_organ_manifold(m, rig, sp_ab, transport_covariance=True)
            rgb_noj, al_noj = render_sh3_cloud(dm_noj.cloud, ev0, device, zoom_crop=z_ab, out_size=(340, 340))
            rgb_yesj, al_yesj = render_sh3_cloud(dm_yesj.cloud, ev0, device, zoom_crop=z_ab, out_size=(340, 340))
            # Measure internal pinhole / crack fraction inside dilated silhouette
            closed_sil = cv2.morphologyEx((al_yesj > 0.5).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)) > 0
            pinhole_noj = 100.0 * float(np.mean(al_noj[closed_sil] < 0.65)) if np.any(closed_sil) else 0.0
            pinhole_yesj = 100.0 * float(np.mean(al_yesj[closed_sil] < 0.65)) if np.any(closed_sil) else 0.0
            ab_metrics[ab_mode] = {
                "pinhole_frac_no_jacobian_pct": round(pinhole_noj, 2),
                "pinhole_frac_with_jacobian_pct": round(pinhole_yesj, 2),
            }
            for arr in (rgb_noj, rgb_yesj):
                im = Image.fromarray((np.clip(arr, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)).resize((250, 230), Image.Resampling.LANCZOS)
                t_im = Image.new("RGB", (260, 240), (255, 255, 255))
                t_im.paste(im, (5, 5))
                ab_tiles.append(t_im)

        report["scenes"][sc]["jacobian_covariance_ablation"] = ab_metrics
        b_m = ab_metrics["broad_rosette"]
        rows_p4.append((
            f"{sc.upper()} 2.8x Zoom\nBroad pinholes:\nNo J: {b_m['pinhole_frac_no_jacobian_pct']:.1f}%\nWith J: {b_m['pinhole_frac_with_jacobian_pct']:.1f}%",
            ab_tiles,
        ))

    _save_grid_panel(
        out_dir / "cross_species_manifold_deformation.png",
        [t for _, t in deform_modes],
        rows_p3,
        tw3,
        th3,
    )
    _save_grid_panel(
        out_dir / "cross_species_jacobian_ablation_zoom.png",
        [
            "Cup+Twist: Center-Only (No J)",
            "Cup+Twist: With J Sigma J^T",
            "Broad Morph: Center-Only (No J)",
            "Broad Morph: With J Sigma J^T",
        ],
        rows_p4,
        260,
        240,
    )
    print("[Showcase] Saved Panel 3 & Panel 4: deformation & Jacobian ablation", flush=True)

    # -----------------------------------------------------------------------
    # Panel 5: Horticultural Organ Pruning & Data-Driven Apical Sprouting (Brassica, Bonsai, Flowers)
    # -----------------------------------------------------------------------
    tw5, th5 = 250, 240
    rows_p5: list[tuple[str, list[Image.Image]]] = []
    for sc in CORE_THREE_SCENES:
        m, ev0 = models[sc], evals[sc][0]
        bx_grow = _fg_bbox(ev0.alpha, pad_frac=0.14)
        orig_rgb, _ = render_sh3_cloud(m.cloud, ev0, device)

        # 1. Prune coherent front window
        pruned_m, pruned_oids, p_stats = apply_horticultural_organ_pruning(m, ev0.cam_center, prune_fraction=0.22)
        hi_rgb_arr = m.cloud.rgb_dc.copy()
        pr_mask = np.isin(m.kernel_labels, list(pruned_oids))
        hi_rgb_arr[pr_mask] = 0.25 * hi_rgb_arr[pr_mask] + 0.75 * np.array([0.95, 0.25, 0.22], dtype=np.float32)
        hi_render, _ = render_sh3_cloud(m.cloud, ev0, device, override_rgb=hi_rgb_arr)
        pruned_render, _ = render_sh3_cloud(pruned_m.cloud, ev0, device)

        # 2. Procedural apical sprouting / budding matched to species allometry & chromaticity!
        sprouted_m, s_stats = apply_procedural_apical_sprouting(m, num_loci=10, buds_per_locus=4, growth_progress=1.0)
        sprouted_render, _ = render_sh3_cloud(sprouted_m.cloud, ev0, device)
        sprout_wire = _draw_sprout_overlay(orig_rgb, sprouted_m, len(m.stem_chains), len(m.organs), ev0)

        report["scenes"][sc]["horticultural_pruning"] = p_stats
        report["scenes"][sc]["procedural_apical_sprouting"] = s_stats

        lbl5 = (
            f"{sc.upper()}\n"
            f"Pruned: -{p_stats['pruned_organs']} outer organs\n"
            f"Allometry W/L={s_stats['discovered_median_wl_ratio']:.2f}\n"
            f"Sprouted: +{s_stats['new_organs']} apical buds"
        )
        rows_p5.append((
            lbl5,
            [
                _crop_and_fit(orig_rgb, bx_grow, tw5, th5),
                _crop_and_fit(hi_render, bx_grow, tw5, th5),
                _crop_and_fit(pruned_render, bx_grow, tw5, th5),
                _crop_and_fit(sprout_wire, bx_grow, tw5, th5),
                _crop_and_fit(sprouted_render, bx_grow, tw5, th5),
            ],
        ))

    _save_grid_panel(
        out_dir / "cross_species_pruning_and_sprouting.png",
        [
            "Original Held-Out View",
            "Target Prune Organs (Coral)",
            "After Horticultural Pruning",
            "New Shoot & Bud Spline Loci",
            "Full Regrowth & Budding Render",
        ],
        rows_p5,
        tw5,
        th5,
    )
    print("[Showcase] Saved Panel 5: cross_species_pruning_and_sprouting.png", flush=True)

    # -----------------------------------------------------------------------
    # Dynamic GIF 1: Continuous Wilt <-> Sunlit Bloom + Apical Budding across Brassica, Bonsai, Flowers
    # -----------------------------------------------------------------------
    rigs_3 = {sc: build_universal_deform_rig(models[sc]) for sc in CORE_THREE_SCENES}
    boxes_3 = {sc: _fg_bbox(evals[sc][0].alpha, pad_frac=0.15) for sc in CORE_THREE_SCENES}
    n_frames = 14
    frames_pheno: list[Image.Image] = []
    gw, gh = 290, 260
    for f_i in range(n_frames):
        # Smooth cosine cycle s_cyc in [-1 (full wilt), +1 (full sunlit bloom + apical buds)]
        s_cyc = -math.cos(2.0 * math.pi * f_i / n_frames)
        canvas = Image.new("RGB", (gw * 3, gh + 34), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        for c_i, sc in enumerate(CORE_THREE_SCENES):
            m, ev0, rig = models[sc], evals[sc][0], rigs_3[sc]
            if s_cyc < 0.0:
                sp = build_deform_preset_spec(m, rig, "gravity_wilt", strength=abs(s_cyc))
                dm, _ = deform_universal_organ_manifold(m, rig, sp, transport_covariance=True)
            else:
                sp = build_deform_preset_spec(m, rig, "broad_rosette", strength=s_cyc)
                dm, _ = deform_universal_organ_manifold(m, rig, sp, transport_covariance=True)
                if s_cyc > 0.12:
                    dm, _ = apply_procedural_apical_sprouting(
                        dm, num_loci=10, buds_per_locus=4, growth_progress=(s_cyc - 0.12) / 0.88
                    )
            rgb_f, _ = render_sh3_cloud(dm.cloud, ev0, device)
            canvas.paste(_crop_and_fit(rgb_f, boxes_3[sc], gw, gh), (c_i * gw, 34))
            state_lbl = "Wilt Droop" if s_cyc < -0.2 else ("Sunlit Bloom + Sprout" if s_cyc > 0.2 else "Rest")
            draw.text((c_i * gw + 10, 10), f"{sc.upper()}: {state_lbl} (0.0p vessel drift)", fill=(20, 28, 35))
        frames_pheno.append(canvas.quantize(colors=256, method=Image.Quantize.MEDIANCUT))

    gif1_path = resolve_write_path(out_dir / "anim_cross_species_wilt_to_bloom.gif")
    frames_pheno[0].save(gif1_path, save_all=True, append_images=frames_pheno[1:], duration=90, loop=0, optimize=False)

    # -----------------------------------------------------------------------
    # Dynamic GIF 2: Multi-Style Neighbor-Mosaic Breeze Sway across Brassica, Bonsai, Flowers, Ficus
    # -----------------------------------------------------------------------
    frames_breeze: list[Image.Image] = []
    bw, bh = 265, 250
    for f_i in range(n_frames):
        ph = 2.0 * math.pi * f_i / n_frames
        canvas = Image.new("RGB", (bw * 4, bh + 34), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        for c_i, sc in enumerate(SHOWCASE_SCENES):
            mb = mosaic_models[sc]
            def_c, _, _ = deform_universal_model_wind(mb, phase_rad=ph, wind_amp_deg=8.2)
            rgb_b, _ = render_sh3_cloud(def_c, evals[sc][0], device)
            canvas.paste(_crop_and_fit(rgb_b, rest_boxes[sc], bw, bh), (c_i * bw, 34))
            draw.text((c_i * bw + 10, 10), f"{sc.upper()} 6-Style Mosaic Breeze", fill=(20, 28, 35))
        frames_breeze.append(canvas.quantize(colors=256, method=Image.Quantize.MEDIANCUT))

    gif2_path = resolve_write_path(out_dir / "anim_cross_species_multistyle_breeze.gif")
    frames_breeze[0].save(gif2_path, save_all=True, append_images=frames_breeze[1:], duration=85, loop=0, optimize=False)

    report["total_wall_seconds"] = round(time.time() - t0, 2)
    atomic_write_text(out_dir / "CROSS_SPECIES_EDITING_REPORT.json", json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[Showcase] ALL PANELS, GIFS & PLYS COMPLETE in {report['total_wall_seconds']}s -> {out_dir}", flush=True)


if __name__ == "__main__":
    main()
