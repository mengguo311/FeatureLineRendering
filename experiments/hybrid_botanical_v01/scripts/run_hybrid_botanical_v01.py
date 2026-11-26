#!/usr/bin/env python3
"""End-to-End Pipeline for Topic 2: 3-Tier Hybrid Vector-Gaussian Botanical Primitive (hybrid_botanical_v01)."""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hybrid_botanical.applications_v01 import (
    build_stylized_foliage_palette,
    run_app1_8x_vector_superzoom,
    run_app2_topological_bonsai_pruning,
    run_app3_4level_hierarchical_kinematics,
    run_app4_inverse_phyllotaxis_and_regrowth,
    save_panel_strip,
)
from hybrid_botanical.eigen_leaf_splines import (
    compute_anatomical_leaf_frames,
    fit_eigen_leaf_dual_arc_patches_and_complete,
)
from hybrid_botanical.hybrid_renderer import (
    draw_hybrid_skeleton_and_splines_wireframe,
    render_analytical_spline_trimmed_hybrid,
    render_cloud_bank,
)
from hybrid_botanical.schema_and_io import (
    HybridBotanicalPrimitive,
    atomic_write_text,
    eval_clamped_bspline,
    export_standard_3dgs_ply,
    load_upstream_ficus_inputs,
    resolve_write_path,
)
from hybrid_botanical.tree_arborizer import build_4level_botanical_tree_and_bind_wood


def _select_isolated_gpu() -> torch.device:
    if not torch.cuda.is_available():
        return torch.device("cpu")
    dev = torch.device("cuda:1" if torch.cuda.device_count() >= 2 else "cuda:0")
    torch.cuda.set_device(dev)
    return dev


def export_hybrid_cad_obj(path: Path, model: HybridBotanicalPrimitive) -> Path:
    """Export 3D CAD OBJ containing all 4-level B-spline branch polylines + all 472 closed pointed-tip Dual-Arc leaf loops."""
    lines = ["# hybrid_botanical_v01 3-Tier Parametric Skeleton & Dual-Arc Leaf Loops"]
    v_off = 1
    u_sp = np.linspace(0.0, 1.0, 16)
    for br in model.skeleton.branches:
        lines.append(f"g BRANCH_LVL{br.level}_{br.branch_id:04d}")
        pts, _ = eval_clamped_bspline(br.ctrl_points, u_sp)
        for p in pts:
            lines.append(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}")
        lines.append("l " + " ".join(str(v_off + k) for k in range(len(pts))))
        v_off += len(pts)

    for patch in model.leaves:
        lines.append(f"g DUAL_ARC_LEAF_{patch.leaf_id:04d}_{patch.visibility_tier}")
        pl, pr = patch.eval_3d_boundary_arcs(n_per_arc=16)
        loop = np.vstack([pl, pr[-2:0:-1]])
        for p in loop:
            lines.append(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}")
        lines.append("l " + " ".join(str(v_off + k) for k in range(len(loop))) + f" {v_off}")
        v_off += len(loop)

    return atomic_write_text(path, "\n".join(lines) + "\n")


def main() -> None:
    t0 = time.time()
    device = _select_isolated_gpu()
    out_dir = resolve_write_path(PROJECT_ROOT / "outputs/ficus_hybrid_v01")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[HybridBotanical v01] Isolated workspace={PROJECT_ROOT}, device={device}", flush=True)

    print("[HybridBotanical v01] Step 1: Loading read-only upstream v05 curves + M1+M2 472-leaf kernels + 37 views...", flush=True)
    inp = load_upstream_ficus_inputs()
    untrimmed_m12_cloud = inp["cloud"]

    print("[HybridBotanical v01] Step 2: Extracting anatomical leaf frames & building 4-level B-spline branching tree...", flush=True)
    t_s2 = time.time()
    leaf_frames = compute_anatomical_leaf_frames(untrimmed_m12_cloud, inp["leaf_meta_list"])
    leaf_p_bases = np.array([lf["p_base"] for lf in leaf_frames], dtype=np.float64)
    skeleton_tree, wood_completed_cloud, tree_stats = build_4level_botanical_tree_and_bind_wood(
        untrimmed_m12_cloud, leaf_p_bases, inp["swept_trunks"], inp["pot_spec"], inp["median_pixel_scale"],
        train_views=inp["train_views"],
    )
    print(f"  4-Level Tree built in {time.time() - t_s2:.2f}s -> {json.dumps(tree_stats)}", flush=True)

    print("[HybridBotanical v01] Step 3: Learning Eigen-Leaf PCA prior, fitting Dual-Arc B-Splines & shadow completion...", flush=True)
    t_s3 = time.time()
    patches, eigen_prior, full_completed_cloud, trimmed_no_infill_cloud, leaf_stats = fit_eigen_leaf_dual_arc_patches_and_complete(
        wood_completed_cloud, skeleton_tree, leaf_frames, inp["rim_points"],
        inp["train_views"], inp["median_pixel_scale"], device=device,
    )
    print(f"  Eigen-Leaf Dual-Arc patches built in {time.time() - t_s3:.2f}s -> {json.dumps(leaf_stats)}", flush=True)

    model = HybridBotanicalPrimitive(
        scene_name="ficus",
        pot_base=inp["pot_spec"],
        skeleton=skeleton_tree,
        leaves=patches,
        eigen_prior=eigen_prior,
        cloud=full_completed_cloud,
        median_pixel_scale=inp["median_pixel_scale"],
    )

    # Evaluate novel-view fidelity on all 5 strictly held-out test views (verifying shadow completion preserves PSNR/IoU!)
    ious_before, ious_after, psnr_consistency = [], [], []
    for ev in inp["eval_views"]:
        rgb_bef, al_bef = render_cloud_bank(untrimmed_m12_cloud, ev, device)
        rgb_aft, al_aft = render_cloud_bank(model.cloud, ev, device)
        gt_fg = ev.alpha > 0.50
        ious_before.append(100.0 * float(np.sum(gt_fg & (al_bef > 0.50))) / max(int(np.sum(gt_fg | (al_bef > 0.50))), 1))
        ious_after.append(100.0 * float(np.sum(gt_fg & (al_aft > 0.50))) / max(int(np.sum(gt_fg | (al_aft > 0.50))), 1))
        mse = float(np.mean((rgb_bef - rgb_aft) ** 2))
        psnr_consistency.append(10.0 * math.log10(1.0 / max(mse, 1e-8)))

    recon_eval = {
        "heldout_5views_iou_before_completion_pct": round(float(np.mean(ious_before)), 2),
        "heldout_5views_iou_after_completion_pct": round(float(np.mean(ious_after)), 2),
        "shadow_infill_unpruned_consistency_psnr_db": round(float(np.mean(psnr_consistency)), 2),
    }
    print("  Held-out 5-view parity check:", json.dumps(recon_eval), flush=True)

    # Export Standard 3DGS .ply, 3D CAD Skeleton+DualArc .obj, and Unified Schema JSON!
    ply_out = export_standard_3dgs_ply(out_dir / "hybrid_botanical_completed.ply", model.cloud)
    obj_out = export_hybrid_cad_obj(out_dir / "hybrid_skeleton_and_dual_arc_leaves.obj", model)

    # Render Overview 5-Column Decomposition Panel on test_r_1 and test_r_79!
    sty_rgb = build_stylized_foliage_palette(model)
    overview_panels = []
    for vname in ("test_r_1", "test_r_79"):
        ev = next(v for v in inp["eval_views"] if v.view_name == vname)
        w_cad = draw_hybrid_skeleton_and_splines_wireframe(model, ev)
        r_ply, _ = render_cloud_bank(model.cloud, ev, device)
        r_hyb_nat = render_analytical_spline_trimmed_hybrid(model, ev, device, out_size=(800, 800), draw_vector_ink_rims=False)
        r_hyb_sty = render_analytical_spline_trimmed_hybrid(
            model, ev, device, override_rgb=sty_rgb, out_size=(800, 800), draw_vector_ink_rims=True
        )
        ov_tiles = [
            (ev.rgb * 255.0 + 0.5).astype(np.uint8),
            w_cad,
            (r_ply * 255.0 + 0.5).astype(np.uint8),
            (r_hyb_nat * 255.0 + 0.5).astype(np.uint8),
            (r_hyb_sty * 255.0 + 0.5).astype(np.uint8),
        ]
        ov_titles = [
            f"{vname} Source 3DGS",
            "3-Tier Vector Tree + Dual-Arcs",
            "Standard Exported .PLY Render",
            "Hybrid Spline-Trimmed Natural",
            "Hybrid Spline-Trimmed Stylized",
        ]
        p_ov = save_panel_strip(out_dir / f"overview_3tier_hybrid_{vname}.png", ov_tiles, ov_titles)
        overview_panels.append(str(p_ov))

    # Run All 4 Flagship Applications!
    print("[HybridBotanical v01] Step 4A: Running App 1 (8x Infinite Vector-Sharp Super-Zoom)...", flush=True)
    app1_res = run_app1_8x_vector_superzoom(model, untrimmed_m12_cloud, inp["eval_views"], out_dir, device)

    print("[HybridBotanical v01] Step 4B: Running App 2 (Topological Bonsai Pruning + Exposed Inner Canopy)...", flush=True)
    n_orig_k = len(untrimmed_m12_cloud.means)
    no_comp_cloud = trimmed_no_infill_cloud
    if len(trimmed_no_infill_cloud.means) > n_orig_k:
        from hybrid_botanical.schema_and_io import build_cloud_bank as _bcb
        no_comp_cloud = _bcb(
            trimmed_no_infill_cloud.means[:n_orig_k], trimmed_no_infill_cloud.scales[:n_orig_k],
            trimmed_no_infill_cloud.quats_wxyz[:n_orig_k], trimmed_no_infill_cloud.opacities[:n_orig_k],
            trimmed_no_infill_cloud.rgb[:n_orig_k], trimmed_no_infill_cloud.kernel_labels[:n_orig_k],
        )
    app2_res = run_app2_topological_bonsai_pruning(model, no_comp_cloud, inp["eval_views"], out_dir, device)

    print("[HybridBotanical v01] Step 4C: Running App 3 (4-Level Coupled Bonsai Kinematics & Sway GIF)...", flush=True)
    app3_res = run_app3_4level_hierarchical_kinematics(model, inp["eval_views"], out_dir, device)

    print("[HybridBotanical v01] Step 4D: Running App 4 (Inverse Phyllotaxis & Apical Shoot Regrowth)...", flush=True)
    app4_res = run_app4_inverse_phyllotaxis_and_regrowth(model, inp["eval_views"], out_dir, device)

    # Save Unified Hybrid Botanical Schema JSON + Benchmark Report JSON
    schema_doc = {
        "schema": "hybrid_botanical_primitive/v01",
        "scene": "ficus",
        "layer1_lathe_pot": {
            "axis_origin": model.pot_base.axis_origin.tolist(),
            "axis_dir": model.pot_base.axis_dir.tolist(),
            "h_max": model.pot_base.h_max,
        },
        "layer2_skeleton_summary": tree_stats,
        "layer3_eigen_leaf_summary": {
            **leaf_stats,
            "eigen_mean_norm_ctrl8": [round(float(x), 4) for x in eigen_prior.mean_norm_ctrl8],
        },
    }
    schema_json_path = atomic_write_text(
        out_dir / "hybrid_botanical_primitive.json", json.dumps(schema_doc, indent=2, ensure_ascii=False) + "\n"
    )

    report = {
        "schema": "hybrid_botanical_benchmark/v01",
        "workspace_root": str(PROJECT_ROOT),
        "device_used": str(device),
        "total_kernels_completed_cloud": int(len(model.cloud.means)),
        "layer2_4level_tree": tree_stats,
        "layer3_dual_arc_eigen_leaves": leaf_stats,
        "heldout_5views_reconstruction": recon_eval,
        "app1_8x_vector_superzoom": app1_res,
        "app2_topological_bonsai_pruning": app2_res,
        "app3_4level_hierarchical_kinematics": app3_res,
        "app4_inverse_phyllotaxis_and_regrowth": app4_res,
        "exported_assets": {
            "standard_3dgs_ply": str(ply_out),
            "cad_skeleton_and_splines_obj": str(obj_out),
            "unified_primitive_json": str(schema_json_path),
            "overview_panels": overview_panels,
        },
        "total_wall_seconds": round(time.time() - t0, 2),
    }
    rep_path = atomic_write_text(
        out_dir / "HYBRID_BOTANICAL_V01_REPORT.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    )
    print(f"[HybridBotanical v01] COMPLETE in {time.time() - t0:.1f}s -> {rep_path}", flush=True)


if __name__ == "__main__":
    main()
