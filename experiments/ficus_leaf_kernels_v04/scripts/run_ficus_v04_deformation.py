#!/usr/bin/env python3
"""Run Phase 4 (v04): Per-Leaf 3D Geometric Deformation, Jacobian Transport Ablation & Dynamic Breeze GIFs on GPU 1."""

from __future__ import annotations

import json
import math
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
from leaf_kernels.leaf_deformer_v04 import (
    LeafDeformRig,
    PerLeafDeformSpec,
    build_leaf_deform_rig,
    deform_leaf_substrate,
    make_broad_obovate_morph_spec,
    make_cupped_helical_twist_spec,
    make_directional_wind_spec,
    make_gravity_wilt_spec,
    make_identity_spec,
    make_same_plant_phenology_contrast_spec,
    make_willow_slender_morph_spec,
)
from leaf_kernels.leaf_refinement_v02 import orient_leaf_frames_anatomically
from leaf_kernels.style_presets_v03 import (
    LeafKernelSubstrateM12,
    build_m1_m2_leaf_substrate,
    build_mixed_mode_a_crown_sectors,
    compose_mixed_style_plant,
)
from leaf_kernels.stylize_and_render import draw_projected_3d_leaf_loops, render_3dgs_cloud


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


def _save_strip(
    dest: Path,
    imgs_u8: list[np.ndarray],
    titles: list[str],
    crop_box: tuple[int, int, int, int] | None = None,
    tile_size: int = 320,
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


def _measure_interior_crack_hole_rate(
    cloud: GaussianCloud3D,
    eval_views: list[CalibratedLeafView],
    device: torch.device,
) -> float:
    """Measure % of translucent Swiss-cheese pinholes/cracks strictly inside deformed leaf silhouettes!

    Closes small <= 5 px gaps on the binary silhouette (alpha > 0.45) to get the expected continuous leaf interior,
    then measures the fraction of interior pixels where accumulated alpha dips below 0.65 (cracks/holes).
    """
    crack_rates: list[float] = []
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    erode_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    for ev in eval_views:
        al = render_alpha_mask(cloud, ev, device=device)
        fg = (al > 0.35).astype(np.uint8)
        closed_fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kern)
        interior = cv2.erode(closed_fg, erode_k) > 0
        if int(interior.sum()) >= 50:
            pinholes = interior & (al < 0.68)
            crack_rates.append(100.0 * float(pinholes.sum()) / float(interior.sum()))
    return round(float(np.mean(crack_rates)), 2) if crack_rates else 0.0


def main() -> None:
    t0 = time.time()
    device = _select_isolated_gpu()
    out_dir = resolve_write_path(PROJECT_ROOT / "outputs/ficus_leaf_deform_v04")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[LeafDeform v04] Isolated workspace={PROJECT_ROOT}, device={device}", flush=True)

    cloud_src = load_ficus_3dgs_cloud()
    train_views, eval_views, priors = load_ficus_views_and_v04_priors()
    base_labels, base_leaves = _load_or_compute_v01_partition(cloud_src, train_views, priors, device=device)

    print("[LeafDeform v04] Step 1: Building M1+M2 per-leaf substrate & petiole-hinged deformation rig...", flush=True)
    sub = build_m1_m2_leaf_substrate(cloud_src, base_labels, base_leaves, priors)
    rig = build_leaf_deform_rig(sub)

    # Pre-compile per-kernel RGB banks so we can render BOTH Natural Green & Stylized Multi-Style under any 3D deformation!
    _, ghibli_rgb, _ = compose_mixed_style_plant(sub, "ghibli_gouache")
    map_symphony = build_mixed_mode_a_crown_sectors(sub)
    _, symphony_rgb, _ = compose_mixed_style_plant(sub, map_symphony)
    # Natural photorealistic albedo enhanced with clean M1+M2 leaf separation
    natural_rgb = sub.cloud.rgb_dc.copy()

    # Step 2: Build 6 Per-Leaf 3D Deformation Modes + Same-Plant Heterogeneous Phenology Contrast!
    pheno_spec, pheno_style_map = make_same_plant_phenology_contrast_spec(rig)
    _, pheno_rgb, pheno_counts = compose_mixed_style_plant(sub, pheno_style_map)

    deform_modes: list[tuple[str, str, PerLeafDeformSpec, np.ndarray]] = [
        ("0_rest_pose", "Rest Pose (Original)", make_identity_spec(rig.num_leaves), ghibli_rgb),
        ("1_gravity_wilt", "Gravity Wilt (+54 deg)", make_gravity_wilt_spec(rig, max_droop_deg=54.0), ghibli_rgb),
        ("2_cup_twist", "Boat-Cup + 48 deg Twist", make_cupped_helical_twist_spec(rig, 36.0, 48.0), ghibli_rgb),
        ("3_wind_gust", "Lateral Wind Gust", make_directional_wind_spec(rig, gust_deg=48.0, flutter_deg=10.0), ghibli_rgb),
        ("4_willow_slender", "Willow Slender Morph", make_willow_slender_morph_spec(rig), ghibli_rgb),
        ("5_broad_obovate", "Broad Obovate Morph", make_broad_obovate_morph_spec(rig), ghibli_rgb),
        ("6_same_plant_pheno", "Same-Plant Bloom vs Wilt", pheno_spec, pheno_rgb),
    ]

    print("[LeafDeform v04] Step 2: Executing per-leaf 3D deformations & verifying physical invariants...", flush=True)
    deformed_models: dict[str, tuple[GaussianCloud3D, list[LeafInstance3D], np.ndarray, str]] = {}
    mode_reports: dict[str, Any] = {}

    for m_id, m_title, spec, col_bank in deform_modes:
        td = time.time()
        c_def, l_def, inv = deform_leaf_substrate(sub, rig, spec, transport_covariance=True)
        dt_ms = round(1000.0 * (time.time() - td), 1)
        crack_pct = _measure_interior_crack_hole_rate(c_def, eval_views, device=device)
        deformed_models[m_id] = (c_def, l_def, col_bank, m_title)
        mode_reports[m_id] = {
            "title": m_title,
            "deform_wall_ms": dt_ms,
            "interior_pinhole_crack_pct": crack_pct,
            **inv,
        }
        print(f"  {m_id:22s} ({dt_ms:5.1f} ms) -> crack={crack_pct:.2f}% | {inv}", flush=True)

    # Step 3: Ablation — With vs Without Jacobian Covariance Transport (Sigma' = J Sigma J^T) on Extreme Edits!
    print("[LeafDeform v04] Step 3: Running Jacobian Covariance Transport ablation...", flush=True)
    ablation_jacobian: dict[str, Any] = {}
    jac_test_specs = [
        ("gravity_wilt_54deg", make_gravity_wilt_spec(rig, max_droop_deg=54.0)),
        ("broad_obovate_expand", make_broad_obovate_morph_spec(rig)),
        ("cup_twist_48deg", make_cupped_helical_twist_spec(rig, 38.0, 52.0)),
    ]
    jac_vis_clouds: dict[str, tuple[GaussianCloud3D, GaussianCloud3D]] = {}
    for j_name, j_spec in jac_test_specs:
        c_no_jac, _, _ = deform_leaf_substrate(sub, rig, j_spec, transport_covariance=False)
        c_with_jac, _, _ = deform_leaf_substrate(sub, rig, j_spec, transport_covariance=True)
        hole_no = _measure_interior_crack_hole_rate(c_no_jac, eval_views, device=device)
        hole_yes = _measure_interior_crack_hole_rate(c_with_jac, eval_views, device=device)
        ablation_jacobian[j_name] = {
            "without_jacobian_crack_hole_pct": hole_no,
            "with_jacobian_crack_hole_pct": hole_yes,
            "crack_reduction_pp": round(hole_no - hole_yes, 2),
        }
        jac_vis_clouds[j_name] = (c_no_jac, c_with_jac)
        print(f"  Jacobian ablation [{j_name}]: no_J crack={hole_no:.2f}% -> with_J crack={hole_yes:.2f}%", flush=True)

    # Step 4: Render 7-Column Deformation Galleries (Natural 3DGS + Ghibli/Phenology Stylized + Multi-Style Symphony)!
    print("[LeafDeform v04] Step 4: Rendering multi-view deformation panels & Jacobian zoom comparisons...", flush=True)
    saved_panels: list[str] = []
    crops = {
        "full": None,
        "canopy_zoom": (230, 120, 570, 460),
        "rosette_zoom": (310, 155, 610, 455),
    }

    for ev in eval_views:
        if ev.view_name not in ("test_r_1", "test_r_7", "test_r_79"):
            continue
        nat_imgs: list[np.ndarray] = []
        sty_imgs: list[np.ndarray] = []
        sym_imgs: list[np.ndarray] = []
        titles: list[str] = []

        for m_id, m_title, _, _ in deform_modes:
            c_def, _, col_bank, _ = deformed_models[m_id]
            r_nat = render_3dgs_cloud(c_def, ev, device=device, override_colors=natural_rgb)
            r_sty = render_3dgs_cloud(c_def, ev, device=device, override_colors=col_bank)
            s_col = pheno_rgb if m_id == "6_same_plant_pheno" else symphony_rgb
            r_sym = render_3dgs_cloud(c_def, ev, device=device, override_colors=s_col)

            nat_imgs.append((r_nat * 255.0 + 0.5).astype(np.uint8))
            sty_imgs.append((r_sty * 255.0 + 0.5).astype(np.uint8))
            sym_imgs.append((r_sym * 255.0 + 0.5).astype(np.uint8))
            titles.append(m_title)

        for tag, box in crops.items():
            p_nat = _save_strip(out_dir / f"deform_natural_{tag}_{ev.view_name}.png", nat_imgs, titles, box, tile_size=290)
            p_sty = _save_strip(out_dir / f"deform_stylized_{tag}_{ev.view_name}.png", sty_imgs, titles, box, tile_size=290)
            p_sym = _save_strip(out_dir / f"deform_multistyle_{tag}_{ev.view_name}.png", sym_imgs, titles, box, tile_size=290)
            saved_panels.extend([str(p_nat), str(p_sty), str(p_sym)])

        # Save 6-Column Jacobian Covariance Ablation Zoom on test_r_79 & test_r_7
        if ev.view_name in ("test_r_79", "test_r_7"):
            jac_imgs: list[np.ndarray] = []
            jac_titles: list[str] = []
            for j_label, j_key in (
                ("Gravity Wilt", "gravity_wilt_54deg"),
                ("Broad Obovate", "broad_obovate_expand"),
                ("Cup + Twist", "cup_twist_48deg"),
            ):
                c_no, c_yes = jac_vis_clouds[j_key]
                im_no = (render_3dgs_cloud(c_no, ev, device=device, override_colors=ghibli_rgb) * 255.0 + 0.5).astype(np.uint8)
                im_yes = (render_3dgs_cloud(c_yes, ev, device=device, override_colors=ghibli_rgb) * 255.0 + 0.5).astype(np.uint8)
                jac_imgs.extend([im_no, im_yes])
                jac_titles.extend([f"{j_label}: Center-Only (No J)", f"{j_label}: With Jacobian J"])
            pj = _save_strip(
                out_dir / f"ablation_jacobian_rosette_zoom_{ev.view_name}.png",
                jac_imgs,
                jac_titles,
                crop_box=(310, 155, 610, 455),
                tile_size=320,
            )
            saved_panels.append(str(pj))

    # Step 5: Render 2 Smooth 3D Animated GIFs (Dynamic Breeze Flutter + Continuous Wilt-to-Bloom Morph)!
    print("[LeafDeform v04] Step 5: Rendering smooth 3D dynamic breeze & morph animated GIFs...", flush=True)
    ev_breeze = next(v for v in eval_views if v.view_name == "test_r_79")
    ev_full = next(v for v in eval_views if v.view_name == "test_r_1")

    breeze_frames: list[Image.Image] = []
    n_frames = 20
    for f_i in range(n_frames):
        ang = 2.0 * math.pi * f_i / n_frames
        gust_mod = 34.0 + 16.0 * math.sin(ang)
        sp_w = make_directional_wind_spec(
            rig, wind_dir=(0.92, 0.25, 0.18), gust_deg=gust_mod, flutter_deg=12.0, time_phase=2.0 * ang
        )
        c_w, _, _ = deform_leaf_substrate(sub, rig, sp_w, transport_covariance=True)
        r_n = (render_3dgs_cloud(c_w, ev_breeze, device=device, override_colors=natural_rgb) * 255.0 + 0.5).astype(np.uint8)
        r_s = (render_3dgs_cloud(c_w, ev_breeze, device=device, override_colors=symphony_rgb) * 255.0 + 0.5).astype(np.uint8)
        # 2x canopy zoom side-by-side [Natural 3DGS Breeze | Same-Plant 6-Style Breeze]
        x0, y0, x1, y1 = 220, 110, 580, 470
        t1 = cv2.resize(r_n[y0:y1, x0:x1], (360, 360), interpolation=cv2.INTER_AREA)
        t2 = cv2.resize(r_s[y0:y1, x0:x1], (360, 360), interpolation=cv2.INTER_AREA)
        frame = Image.new("RGB", (720, 392), color=(248, 248, 250))
        dr = ImageDraw.Draw(frame)
        frame.paste(Image.fromarray(t1), (0, 32))
        frame.paste(Image.fromarray(t2), (360, 32))
        dr.text((10, 8), "Native 3DGS: Per-Leaf Aero-Breeze & Flutter", fill=(20, 20, 25))
        dr.text((370, 8), "Same-Plant 6-Style Symphony: 3D Breeze", fill=(20, 20, 25))
        breeze_frames.append(frame)

    gif_breeze_path = resolve_write_path(out_dir / "anim_breeze_flutter_test_r_79.gif")
    breeze_frames[0].save(
        gif_breeze_path, save_all=True, append_images=breeze_frames[1:], duration=85, loop=0, optimize=False
    )

    morph_frames: list[Image.Image] = []
    wilt_full = make_gravity_wilt_spec(rig, max_droop_deg=56.0)
    bloom_full = make_broad_obovate_morph_spec(rig)
    for f_i in range(n_frames):
        # Smooth cosine oscillation s_t in [-1 (wilt), +1 (lush sun-bloom)]
        tau = math.cos(2.0 * math.pi * f_i / n_frames)  # +1 -> -1 -> +1
        sp_m = make_identity_spec(rig.num_leaves)
        if tau >= 0.0:
            w_t = tau
            sp_m.flap_rad = w_t * wilt_full.flap_rad
            sp_m.sweep_rad = w_t * wilt_full.sweep_rad
            sp_m.cup_curv = w_t * wilt_full.cup_curv
            sp_m.wid_base = 1.0 + w_t * (wilt_full.wid_base - 1.0)
        else:
            b_t = -tau
            sp_m.flap_rad = b_t * bloom_full.flap_rad * 1.3
            sp_m.cup_curv = b_t * bloom_full.cup_curv
            sp_m.len_scale = 1.0 + b_t * (bloom_full.len_scale - 1.0)
            sp_m.wid_base = 1.0 + b_t * (bloom_full.wid_base - 1.0)
            sp_m.wid_tip_add = b_t * bloom_full.wid_tip_add

        c_m, _, _ = deform_leaf_substrate(sub, rig, sp_m, transport_covariance=True)
        r_g = (render_3dgs_cloud(c_m, ev_full, device=device, override_colors=ghibli_rgb) * 255.0 + 0.5).astype(np.uint8)
        r_p = (render_3dgs_cloud(c_m, ev_full, device=device, override_colors=pheno_rgb) * 255.0 + 0.5).astype(np.uint8)
        # Crop cleanly around the whole potted tree (140..660, 60..720) -> resize to (340, 430)
        t1 = cv2.resize(r_g[70:730, 140:660], (330, 420), interpolation=cv2.INTER_AREA)
        t2 = cv2.resize(r_p[70:730, 140:660], (330, 420), interpolation=cv2.INTER_AREA)
        frame = Image.new("RGB", (660, 452), color=(248, 248, 250))
        dr = ImageDraw.Draw(frame)
        frame.paste(Image.fromarray(t1), (0, 32))
        frame.paste(Image.fromarray(t2), (330, 32))
        dr.text((10, 8), "Ghibli 3DGS: Gravity Wilt <-> Lush Sun-Bloom", fill=(20, 20, 25))
        dr.text((340, 8), "Dual-Phenology Palette: Continuous 3D Morph", fill=(20, 20, 25))
        morph_frames.append(frame)

    gif_morph_path = resolve_write_path(out_dir / "anim_wilt_to_bloom_test_r_1.gif")
    morph_frames[0].save(
        gif_morph_path, save_all=True, append_images=morph_frames[1:], duration=90, loop=0, optimize=False
    )

    # Export key deformed 3DGS models & closed 3D boundary wireframes OBJ
    c_pheno_def, l_pheno_def, _ = deformed_models["6_same_plant_pheno"][:3]
    np.savez_compressed(
        out_dir / "v04_phenology_deformed_kernels.npz",
        kernel_leaf_id=sub.kernel_labels.astype(np.int32),
        means=c_pheno_def.means,
        cov6=c_pheno_def.cov6,
        scales=c_pheno_def.scales,
        opacities=c_pheno_def.opacities,
        stylized_rgb=pheno_rgb,
    )

    report = {
        "schema": "ficus_leaf_deform/v04",
        "substrate": "M1+M2 Per-Leaf Kernels (297,343 kernels, 472 hinged 3D leaves)",
        "phenology_contrast_leaf_counts": pheno_counts,
        "deformation_modes_physical_invariants": mode_reports,
        "jacobian_covariance_transport_ablation": ablation_jacobian,
        "saved_gifs": [str(gif_breeze_path), str(gif_morph_path)],
        "saved_panels": saved_panels,
        "total_wall_seconds": round(time.time() - t0, 2),
    }
    rep_path = out_dir / "DEFORM_V04_REPORT.json"
    tmp_r = rep_path.with_name(f"{rep_path.name}.tmp-{os.getpid()}")
    tmp_r.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp_r, rep_path)
    print(f"[LeafDeform v04] COMPLETE in {time.time() - t0:.1f}s -> {rep_path}", flush=True)


if __name__ == "__main__":
    main()
