#!/usr/bin/env python3
"""12-Style Botanical NPR Grand Anthology: 6 Avant-Garde 3DGS-Native Styles + All 12 Styles Coexisting on One Plant."""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any

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
    export_standard_sh3_ply,
    load_canonical_scene,
    load_universal_model_npz,
    resolve_write_path,
    save_universal_model_npz,
)
from universal_botanical.stylize_and_edit import (
    PRESET_AVANT_GARDE_6,
    PRESET_ORDER,
    PRESET_TITLES,
    build_12style_height_spectrum,
    build_12style_museum_cabinet,
    build_12style_neighbor_kaleidoscope,
    build_12style_phyllotactic_spiral,
    compose_stylized_universal_plant,
    compute_universal_organ_polar_coords,
)

ALL_FIVE_SCENES = ("brassica", "bonsai", "flowers", "ficus", "garden")
MACRO_FOUR_SCENES = ("brassica", "bonsai", "flowers", "ficus")


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


def _load_or_build(scene: str, cfg: UniversalBotanicalConfig, device: torch.device) -> tuple[UniversalBotanicalModel, list[CalibratedBuildOrEvalView], bool]:
    cache_p = PROJECT_ROOT / "outputs/universal_5scene_v01" / scene / "model_cache.npz"
    cloud_in, train_views, eval_views, p_med, v05_trunks, curve_pts, _ = load_canonical_scene(scene)
    if cache_p.is_file():
        return load_universal_model_npz(cache_p), eval_views, True
    support, stem_chains, domain_labels, _, _ = discover_basal_support_and_domains(cloud_in, train_views, p_med, v05_trunks, cfg)
    cloud_ref, labels_ref, organ_recs, _, _ = partition_and_consolidate_canopy_organs(
        cloud_in, train_views, support, stem_chains, domain_labels, curve_pts, p_med, cfg, device
    )
    model = fit_universal_organ_patches_and_kinematic_graph(scene, cloud_ref, labels_ref, organ_recs, support, stem_chains, p_med, cfg)
    save_universal_model_npz(cache_p, model)
    return model, eval_views, False


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
    out_dir = resolve_write_path(PROJECT_ROOT / "outputs/npr_12style_anthology_v01")
    out_dir.mkdir(parents=True, exist_ok=True)

    models: dict[str, UniversalBotanicalModel] = {}
    evals: dict[str, list[CalibratedBuildOrEvalView]] = {}
    polars: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    boxes: dict[str, tuple[int, int, int, int]] = {}

    report: dict[str, Any] = {
        "schema": "npr_12style_botanical_anthology/v01",
        "device": str(device),
        "num_total_presets": len(PRESET_ORDER),
        "all_12_presets": list(PRESET_ORDER),
        "avant_garde_6_presets": list(PRESET_AVANT_GARDE_6),
        "scenes": {},
    }

    for sc in ALL_FIVE_SCENES:
        ts = time.time()
        m, evs, cached = _load_or_build(sc, cfg, device)
        models[sc] = m
        evals[sc] = evs
        polars[sc] = compute_universal_organ_polar_coords(m)
        _, al0 = render_sh3_cloud(m.cloud, evs[0], device)
        boxes[sc] = _fg_bbox(al0, pad_frac=0.08)
        print(f"[12-NPR] Ready {sc.upper()} ({'cached' if cached else 'built'} in {time.time() - ts:.2f}s): organs={len(m.organs)}", flush=True)
        report["scenes"][sc] = {
            "basal_regime": m.support.regime,
            "num_organs": len(m.organs),
            "num_kernels": int(len(m.cloud.means)),
        }

    # -----------------------------------------------------------------------
    # Panel 1: The 6 Bold New Avant-Garde 3DGS-Native NPR Presets Across All 5 Plant Species
    # -----------------------------------------------------------------------
    tw1, th1 = 230, 225
    rows_new6: list[tuple[str, list[Image.Image]]] = []
    for sc in ALL_FIVE_SCENES:
        m, ev0, bx = models[sc], evals[sc][0], boxes[sc]
        orig_rgb, _ = render_universal_spline_hybrid(m, ev0, device)
        tiles = [_crop_and_fit(orig_rgb, bx, tw1, th1)]
        for pname in PRESET_AVANT_GARDE_6:
            st_m, _ = compose_stylized_universal_plant(m, pname, precomputed_polar=polars[sc])
            # Use native SH3 renderer directly for X-Ray translucency & Maki-e SH3 iridescence fidelity!
            if pname in ("neon_venation_xray", "vangogh_impasto", "maki_e_gold_lacquer"):
                rgb_s, _ = render_sh3_cloud(st_m.cloud, ev0, device)
            else:
                rgb_s, _ = render_universal_spline_hybrid(st_m, ev0, device)
            tiles.append(_crop_and_fit(rgb_s, bx, tw1, th1))
        rows_new6.append((f"{sc.upper()}\n{m.support.regime}\n{len(m.organs)} 3D organs", tiles))

    _save_grid_panel(
        out_dir / "npr_12styles_new6_cross_species.png",
        ["Original SH3"] + [PRESET_TITLES[p] for p in PRESET_AVANT_GARDE_6],
        rows_new6,
        tw1,
        th1,
    )
    print("[12-NPR] Saved Panel 1: npr_12styles_new6_cross_species.png", flush=True)

    # -----------------------------------------------------------------------
    # Panel 2: All 12 NPR Styles Assembled on ONE Single Plant (4 Composition Modes x 5 Species!)
    # -----------------------------------------------------------------------
    tw2, th2 = 270, 240
    rows_12all: list[tuple[str, list[Image.Image]]] = []
    kaleid_models: dict[str, UniversalBotanicalModel] = {}
    cabinet_models: dict[str, UniversalBotanicalModel] = {}

    for sc in ALL_FIVE_SCENES:
        m, ev0, bx = models[sc], evals[sc][0], boxes[sc]
        m1_map = build_12style_neighbor_kaleidoscope(m)
        m2_map = build_12style_phyllotactic_spiral(m)
        m3_map = build_12style_museum_cabinet(m)
        m4_map = build_12style_height_spectrum(m)

        mod1, c1 = compose_stylized_universal_plant(m, m1_map, precomputed_polar=polars[sc])
        mod2, c2 = compose_stylized_universal_plant(m, m2_map, precomputed_polar=polars[sc])
        mod3, c3 = compose_stylized_universal_plant(m, m3_map, support_theme="sumie_monochrome", precomputed_polar=polars[sc])
        mod4, c4 = compose_stylized_universal_plant(m, m4_map, precomputed_polar=polars[sc])
        kaleid_models[sc] = mod1
        cabinet_models[sc] = mod3

        sc_dir = out_dir / sc
        sc_dir.mkdir(parents=True, exist_ok=True)
        ply_k = export_standard_sh3_ply(sc_dir / f"{sc}_12style_kaleidoscope.ply", mod1.cloud)

        report["scenes"][sc]["same_plant_12style_compositions"] = {
            "mode_1_kaleidoscope_active_styles": len(c1),
            "mode_1_counts": c1,
            "mode_2_spiral_active_styles": len(c2),
            "mode_2_counts": c2,
            "mode_3_cabinet_active_styles": len(c3),
            "mode_3_counts": c3,
            "mode_4_spectrum_active_styles": len(c4),
            "mode_4_counts": c4,
            "exported_12style_ply": str(ply_k),
        }

        r1, _ = render_sh3_cloud(mod1.cloud, ev0, device)
        r2, _ = render_sh3_cloud(mod2.cloud, ev0, device)
        r3, _ = render_sh3_cloud(mod3.cloud, ev0, device)
        r4, _ = render_sh3_cloud(mod4.cloud, ev0, device)

        lbl2 = (
            f"{sc.upper()} 12-in-1\n"
            f"Kaleidoscope: {len(c1)}/12 styles\n"
            f"Spiral: {len(c2)}/12 styles\n"
            f"0.00p vessel paint bleed"
        )
        rows_12all.append((
            lbl2,
            [
                _crop_and_fit(r1, bx, tw2, th2),
                _crop_and_fit(r2, bx, tw2, th2),
                _crop_and_fit(r3, bx, tw2, th2),
                _crop_and_fit(r4, bx, tw2, th2),
            ],
        ))

    _save_grid_panel(
        out_dir / "npr_12styles_all_on_one_plant_5scenes.png",
        [
            "Mode I: 12-Style Neighbor Kaleidoscope",
            "Mode II: 12-Bouquet Crown Spiral",
            "Mode III: Ink/Etch Cabinet + 10 Jewels",
            "Mode IV: 12-Stratum Height Spectrum",
        ],
        rows_12all,
        tw2,
        th2,
    )
    print("[12-NPR] Saved Panel 2: npr_12styles_all_on_one_plant_5scenes.png", flush=True)

    # -----------------------------------------------------------------------
    # Panel 3: 3.2x Optical Macro Leaf Close-Up (Inspecting Impasto, Hatching, Stained-Glass, X-Ray Veins on Touching Leaves!)
    # -----------------------------------------------------------------------
    tw3, th3 = 290, 270
    rows_macro: list[tuple[str, list[Image.Image]]] = []
    for sc in MACRO_FOUR_SCENES:
        ev0, ev1 = evals[sc][0], evals[sc][min(2, len(evals[sc]) - 1)]
        x0, y0, x1, y1 = boxes[sc]
        zw, zh = int((x1 - x0) * 0.34), int((y1 - y0) * 0.34)
        cx_a, cy_a = int(x0 + 0.46 * (x1 - x0)), int(y0 + 0.40 * (y1 - y0))
        zbox0 = (max(0, cx_a - zw // 2), max(0, cy_a - zh // 2), min(ev0.width, cx_a + zw // 2), min(ev0.height, cy_a + zh // 2))

        _, al1 = render_sh3_cloud(models[sc].cloud, ev1, device)
        bx1 = _fg_bbox(al1, pad_frac=0.08)
        zw1, zh1 = int((bx1[2] - bx1[0]) * 0.36), int((bx1[3] - bx1[1]) * 0.36)
        cx_b, cy_b = int(0.5 * (bx1[0] + bx1[2])), int(bx1[1] + 0.42 * (bx1[3] - bx1[1]))
        zbox1 = (max(0, cx_b - zw1 // 2), max(0, cy_b - zh1 // 2), min(ev1.width, cx_b + zw1 // 2), min(ev1.height, cy_b + zh1 // 2))

        z_src, _ = render_sh3_cloud(models[sc].cloud, ev0, device, zoom_crop=zbox0, out_size=(400, 400))
        z_kal0, _ = render_sh3_cloud(kaleid_models[sc].cloud, ev0, device, zoom_crop=zbox0, out_size=(400, 400))
        z_cab0, _ = render_sh3_cloud(cabinet_models[sc].cloud, ev0, device, zoom_crop=zbox0, out_size=(400, 400))
        z_kal1, _ = render_sh3_cloud(kaleid_models[sc].cloud, ev1, device, zoom_crop=zbox1, out_size=(400, 400))

        macro_tiles = []
        for arr in (z_src, z_kal0, z_cab0, z_kal1):
            im = Image.fromarray((np.clip(arr, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)).resize(
                (tw3 - 10, th3 - 10), Image.Resampling.LANCZOS
            )
            t_im = Image.new("RGB", (tw3, th3), (255, 255, 255))
            t_im.paste(im, (5, 5))
            macro_tiles.append(t_im)

        rows_macro.append((
            f"{sc.upper()} 3.2x Macro\nImpasto + Hatching +\nStained-Glass + X-Ray\non touching 3D organs",
            macro_tiles,
        ))

    _save_grid_panel(
        out_dir / "npr_12styles_macro_leaf_closeup.png",
        [
            "Held-Out #1 Source 3.2x Macro",
            "Held-Out #1 12-Style Kaleidoscope",
            "Held-Out #1 Ink Cabinet + Jewels",
            "Held-Out #3 12-Style Multi-View",
        ],
        rows_macro,
        tw3,
        th3,
    )
    print("[12-NPR] Saved Panel 3: npr_12styles_macro_leaf_closeup.png", flush=True)

    # -----------------------------------------------------------------------
    # Dynamic GIF: 12-Style Kaleidoscope Breeze & Maki-e SH3 Iridescence Shimmer (4 Species)
    # -----------------------------------------------------------------------
    n_frames = 14
    frames_gif: list[Image.Image] = []
    gw, gh = 265, 250
    for f_i in range(n_frames):
        ph = 2.0 * math.pi * f_i / n_frames
        canvas = Image.new("RGB", (gw * 4, gh + 34), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        for c_i, sc in enumerate(MACRO_FOUR_SCENES):
            mk = kaleid_models[sc]
            def_c, _, _ = deform_universal_model_wind(mk, phase_rad=ph, wind_amp_deg=8.5)
            rgb_f, _ = render_sh3_cloud(def_c, evals[sc][0], device)
            canvas.paste(_crop_and_fit(rgb_f, boxes[sc], gw, gh), (c_i * gw, 34))
            draw.text((c_i * gw + 8, 10), f"{sc.upper()}: 12 NPR Styles on 1 Plant", fill=(20, 28, 35))
        frames_gif.append(canvas.quantize(colors=256, method=Image.Quantize.MEDIANCUT))

    gif_p = resolve_write_path(out_dir / "anim_12style_kaleidoscope_breeze.gif")
    frames_gif[0].save(gif_p, save_all=True, append_images=frames_gif[1:], duration=85, loop=0, optimize=False)

    report["total_wall_seconds"] = round(time.time() - t0, 2)
    atomic_write_text(out_dir / "NPR_12STYLE_ANTHOLOGY_REPORT.json", json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[12-NPR] COMPLETE in {report['total_wall_seconds']}s -> {out_dir}", flush=True)


if __name__ == "__main__":
    main()
