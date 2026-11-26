#!/usr/bin/env python3
"""Run 5-Arm Controlled Ablation & Combined Optimization Evaluation for Ficus 3DGS Leaf Stylization (v02).

Compares on 5 strictly held-out test views (test_r_1, test_r_7, test_r_14, test_r_79, test_r_99):
  - Arm 0 (v01_baseline):   Original 284,835 kernels, 472 3D leaves, linear tip-base shading.
  - Arm 1 (m1_opacity):     +M1 Beer-Lambert sheet opacity sharpening & faint halo tail suppression.
  - Arm 2 (m2_seam_split):  +M2 2-pass boundary-straddling wide Gaussian splitting & seam reassignment.
  - Arm 3 (m3_uv_venation): +M3 Anatomical petiole->apex UV frame, texel subdivision & 3D midrib/vein/rim mapping.
  - Arm 4 (v02_full_m123):  M1 + M2 + M3 combined joint optimization.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from leaf_kernels.ablation_evaluator import (
    ArmModelBundle,
    evaluate_arm_on_heldout_views,
    save_6col_ablation_comparison_panels,
)
from leaf_kernels.data_io import (
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
    apply_m1_opacity_sharpening,
    apply_m2_straddling_kernel_splitting,
    build_v02_uv_venation_color_banks,
    orient_leaf_frames_anatomically,
    subdivide_interior_leaf_texels_3d,
)
from leaf_kernels.multiview_leaf_cells import detect_2d_enclosed_leaves_for_view


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
    """Fast-reload cached v01 472-leaf partition if present, otherwise compute from scratch."""
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


def main() -> None:
    t0 = time.time()
    device = _select_isolated_gpu()
    out_dir = resolve_write_path(PROJECT_ROOT / "outputs/ficus_leaf_ablation_v02")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[LeafAblation v02] Isolated workspace={PROJECT_ROOT}, device={device}", flush=True)

    cloud_src = load_ficus_3dgs_cloud()
    train_views, eval_views, priors = load_ficus_views_and_v04_priors()
    base_labels, base_leaves = _load_or_compute_v01_partition(cloud_src, train_views, priors, device=device)
    print(f"  Loaded base Ficus cloud ({len(cloud_src.means)} kernels, {len(base_leaves)} oriented 3D leaves).", flush=True)

    eval_cmaps = {ev.view_name: detect_2d_enclosed_leaves_for_view(ev, priors) for ev in eval_views}

    arms: list[ArmModelBundle] = []

    # --- Arm 0: Baseline (v01) ---
    ta = time.time()
    banks_v01 = build_v02_uv_venation_color_banks(cloud_src, base_labels, base_leaves, enable_m3_venation=False)
    arms.append(
        ArmModelBundle(
            arm_id="0_v01_baseline",
            short_title="v01 Baseline",
            cloud=cloud_src,
            kernel_labels=base_labels,
            leaf_instances=base_leaves,
            color_banks=banks_v01,
            build_stats={"num_leaves": len(base_leaves)},
            wall_seconds=round(time.time() - ta, 3),
        )
    )

    # --- Arm 1: +M1 Opacity Sharpening & Halo Suppression (Isolated) ---
    ta = time.time()
    c_m1, st_m1 = apply_m1_opacity_sharpening(cloud_src, base_labels, base_leaves)
    banks_m1 = build_v02_uv_venation_color_banks(c_m1, base_labels, base_leaves, enable_m3_venation=False)
    arms.append(
        ArmModelBundle(
            arm_id="1_m1_opacity_sharpening",
            short_title="+M1 Opacity Sharp",
            cloud=c_m1,
            kernel_labels=base_labels,
            leaf_instances=base_leaves,
            color_banks=banks_m1,
            build_stats=st_m1,
            wall_seconds=round(time.time() - ta, 3),
        )
    )

    # --- Arm 2: +M2 Boundary-Straddling Wide Gaussian Splitting (Isolated) ---
    ta = time.time()
    c_m2, lbl_m2, leaves_m2, st_m2 = apply_m2_straddling_kernel_splitting(
        cloud_src, base_labels, base_leaves, priors, num_passes=2, min_split_px=1.65
    )
    banks_m2 = build_v02_uv_venation_color_banks(c_m2, lbl_m2, leaves_m2, enable_m3_venation=False)
    arms.append(
        ArmModelBundle(
            arm_id="2_m2_seam_splitting",
            short_title="+M2 Seam Split",
            cloud=c_m2,
            kernel_labels=lbl_m2,
            leaf_instances=leaves_m2,
            color_banks=banks_m2,
            build_stats=st_m2,
            wall_seconds=round(time.time() - ta, 3),
        )
    )

    # --- Arm 3: +M3 Anatomical UV Texel Venation & Watercolor Rim (Isolated) ---
    ta = time.time()
    c_m3, lbl_m3, leaves_m3, st_m3 = subdivide_interior_leaf_texels_3d(
        cloud_src, base_labels, base_leaves, priors, num_passes=2, texel_scale_px=1.55
    )
    banks_m3 = build_v02_uv_venation_color_banks(c_m3, lbl_m3, leaves_m3, enable_m3_venation=True)
    arms.append(
        ArmModelBundle(
            arm_id="3_m3_uv_venation",
            short_title="+M3 UV Venation",
            cloud=c_m3,
            kernel_labels=lbl_m3,
            leaf_instances=leaves_m3,
            color_banks=banks_m3,
            build_stats=st_m3,
            wall_seconds=round(time.time() - ta, 3),
        )
    )

    # --- Arm 4: M1 + M2 + M3 Full Combined (v02) ---
    ta = time.time()
    c_123_a, lbl_123_a, leaves_123_a, st_123_split = apply_m2_straddling_kernel_splitting(
        cloud_src, base_labels, base_leaves, priors, num_passes=2, min_split_px=1.65
    )
    c_123_b, lbl_123_b, leaves_123_b, st_123_tex = subdivide_interior_leaf_texels_3d(
        c_123_a, lbl_123_a, leaves_123_a, priors, num_passes=2, texel_scale_px=1.55
    )
    c_123, st_123_op = apply_m1_opacity_sharpening(
        c_123_b, lbl_123_b, leaves_123_b, core_gamma_outer=4.8, core_gamma_mid=3.6
    )
    banks_123 = build_v02_uv_venation_color_banks(c_123, lbl_123_b, leaves_123_b, enable_m3_venation=True)
    arms.append(
        ArmModelBundle(
            arm_id="4_v02_combined_m123",
            short_title="v02 Full (M1+M2+M3)",
            cloud=c_123,
            kernel_labels=lbl_123_b,
            leaf_instances=leaves_123_b,
            color_banks=banks_123,
            build_stats={"m2_split": st_123_split, "m3_texel": st_123_tex, "m1_opacity": st_123_op},
            wall_seconds=round(time.time() - ta, 3),
        )
    )

    # Evaluate all 5 arms across all 5 strictly held-out test views!
    print("[LeafAblation v02] Evaluating all 5 arms on 5 held-out test views...", flush=True)
    eval_table: dict[str, dict[str, Any]] = {}
    for arm in arms:
        metrics = evaluate_arm_on_heldout_views(arm, eval_views, eval_cmaps, priors, device=device)
        eval_table[arm.arm_id] = {
            "short_title": arm.short_title,
            "wall_seconds": arm.wall_seconds,
            "build_stats": arm.build_stats,
            "heldout_5views_metrics": metrics,
        }
        print(f"  {arm.arm_id:24s} -> {json.dumps(metrics)}", flush=True)

    # Compute marginal delta vs Baseline & normalized composite effectiveness score [0..100]
    base_m = eval_table["0_v01_baseline"]["heldout_5views_metrics"]
    for aid, row in eval_table.items():
        m = row["heldout_5views_metrics"]
        d_bleed_red = round(base_m["front_leaf_xray_transmittance_pct"] - m["front_leaf_xray_transmittance_pct"], 2)
        d_purity = round(m["single_leaf_core_purity_pct"] - base_m["single_leaf_core_purity_pct"], 2)
        d_seam = round(m["inter_leaf_seam_sharpness"] - base_m["inter_leaf_seam_sharpness"], 2)
        d_bdr_rec = round(m["pure_3dgs_c2l_boundary_recall_pct"] - base_m["pure_3dgs_c2l_boundary_recall_pct"], 2)
        d_vein = round(m["intra_leaf_venation_detail"] - base_m["intra_leaf_venation_detail"], 2)
        d_iou = round(m["silhouette_iou_vs_gt_pct"] - base_m["silhouette_iou_vs_gt_pct"], 2)

        # Balanced composite stylization effectiveness score across:
        # 1) Occlusion X-Ray Suppression (30%), 2) Single-Leaf Purity (25%),
        # 3) Inter-Leaf Seam Sharpness (15%), 4) Pure-3DGS Boundary Recall & Venation Detail (20%),
        # 5) Silhouette Preservation IoU (10%)
        comp_score = (
            0.30 * (100.0 - m["front_leaf_xray_transmittance_pct"])
            + 0.25 * m["single_leaf_core_purity_pct"]
            + 0.15 * min(100.0, m["inter_leaf_seam_sharpness"] * 3.5)
            + 0.12 * m["pure_3dgs_c2l_boundary_recall_pct"]
            + 0.08 * min(100.0, m["intra_leaf_venation_detail"] * 12.0)
            + 0.10 * m["silhouette_iou_vs_gt_pct"]
        )
        row["delta_vs_baseline"] = {
            "xray_transmittance_reduction_pp": d_bleed_red,
            "single_leaf_purity_gain_pp": d_purity,
            "inter_leaf_seam_sharpness_gain": d_seam,
            "pure_3dgs_c2l_boundary_recall_gain_pp": d_bdr_rec,
            "intra_leaf_venation_detail_gain": d_vein,
            "silhouette_iou_delta_pp": d_iou,
        }
        row["composite_effectiveness_score"] = round(float(comp_score), 2)

    # Export v02 combined refined Gaussian cloud & per-kernel stylized colors
    v02_npz = out_dir / "v02_refined_leaf_kernels.npz"
    np.savez_compressed(
        v02_npz,
        kernel_leaf_id=lbl_123_b.astype(np.int32),
        means=c_123.means,
        scales=c_123.scales,
        quats_wxyz=c_123.quats_wxyz,
        opacities=c_123.opacities,
        instance_palette_rgb=banks_123["instance_palette"],
        botanical_stylized_rgb=banks_123["botanical_stylized"],
    )

    # Render 6-column comparison panels on held-out test_r_79, test_r_7, and test_r_1
    print("[LeafAblation v02] Rendering 6-column side-by-side ablation panels on held-out test views...", flush=True)
    panel_files: list[str] = []
    for ev in eval_views:
        if ev.view_name in ("test_r_79", "test_r_7", "test_r_1"):
            saved = save_6col_ablation_comparison_panels(
                out_dir,
                ev,
                cloud_src,
                arms,
                priors,
                device=device,
                crops={
                    "full": None,
                    "canopy_zoom": (240, 120, 560, 440),
                    "rosette_zoom": (330, 160, 610, 440),
                },
            )
            panel_files.extend(str(p) for p in saved)

    # Determine single best individual method & overall winner
    single_ids = ["1_m1_opacity_sharpening", "2_m2_seam_splitting", "3_m3_uv_venation"]
    best_single = max(single_ids, key=lambda k: eval_table[k]["composite_effectiveness_score"])
    best_overall = max(eval_table.keys(), key=lambda k: eval_table[k]["composite_effectiveness_score"])

    report = {
        "schema": "ficus_leaf_ablation/v02",
        "workspace_root": str(PROJECT_ROOT),
        "device_used": str(device),
        "num_heldout_eval_views": len(eval_views),
        "best_single_optimization_method": best_single,
        "best_overall_configuration": best_overall,
        "arms": eval_table,
        "saved_v02_refined_npz": str(v02_npz),
        "saved_panels": panel_files,
        "total_wall_seconds": round(time.time() - t0, 2),
    }
    rep_path = out_dir / "ABLATION_V02_REPORT.json"
    tmp_r = rep_path.with_name(f"{rep_path.name}.tmp-{os.getpid()}")
    tmp_r.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp_r, rep_path)
    print(
        f"[LeafAblation v02] COMPLETE in {time.time() - t0:.1f}s | Best single={best_single} | Best overall={best_overall}",
        flush=True,
    )


if __name__ == "__main__":
    main()
