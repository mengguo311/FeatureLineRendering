#!/usr/bin/env python3
"""Run Ficus 3DGS Closed-Leaf Region Detection, Gaussian Kernel Partitioning & Stylization Baseline (Isolated GPU 1)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from leaf_kernels.data_io import load_ficus_3dgs_cloud, load_ficus_views_and_v04_priors, resolve_write_path
from leaf_kernels.kernel_partitioner import run_ficus_leaf_kernel_partitioning
from leaf_kernels.multiview_leaf_cells import detect_2d_enclosed_leaves_for_view
from leaf_kernels.stylize_and_render import (
    build_stylized_kernel_colors,
    export_leaf_kernel_assets,
    render_3dgs_cloud,
    save_5col_leaf_stylization_panels,
)


def _select_isolated_gpu() -> torch.device:
    """Prefer GPU 1 (second RTX A6000) to avoid any VRAM/compute contention with parallel agent on GPU 0."""
    if not torch.cuda.is_available():
        return torch.device("cpu")
    dev = torch.device("cuda:1" if torch.cuda.device_count() >= 2 else "cuda:0")
    torch.cuda.set_device(dev)
    return dev


def main() -> None:
    t0 = time.time()
    device = _select_isolated_gpu()
    out_dir = resolve_write_path(PROJECT_ROOT / "outputs/ficus_leaf_baseline_v01")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[LeafKernels v01] Running in isolated workspace {PROJECT_ROOT} on device={device}", flush=True)

    print("[LeafKernels v01] Step 1: Loading 284,835 Ficus 3DGS kernels + 32 train views + 5 held-out test views...", flush=True)
    cloud = load_ficus_3dgs_cloud()
    train_views, eval_views, priors = load_ficus_views_and_v04_priors()
    print(f"  Loaded {len(cloud.means)} 3DGS kernels, {len(train_views)} train views, {len(eval_views)} test views.", flush=True)

    print("[LeafKernels v01] Step 2 & 3: Running 32-view closed-cell detection & occlusion-gated 3D leaf kernel partitioning...", flush=True)
    t_part = time.time()
    kernel_labels, leaf_instances, train_cmaps, part_stats = run_ficus_leaf_kernel_partitioning(
        cloud, train_views, priors, device=device
    )
    part_stats["partition_wall_seconds"] = round(time.time() - t_part, 2)
    print("  Partition stats:", json.dumps(part_stats, ensure_ascii=False), flush=True)

    print("[LeafKernels v01] Step 4: Building stylized per-leaf 3DGS color banks & exporting 3D leaf assets...", flush=True)
    color_banks = build_stylized_kernel_colors(cloud, kernel_labels, leaf_instances)
    saved_assets = export_leaf_kernel_assets(out_dir, cloud, kernel_labels, leaf_instances, color_banks, part_stats)

    # Quantitative cross-view consistency & occlusion evaluation on the 5 strictly held-out test views!
    print("[LeafKernels v01] Step 5: Evaluating multi-view leaf coherence & rendering held-out test views...", flush=True)
    eval_cmaps = {vw.view_name: detect_2d_enclosed_leaves_for_view(vw, priors) for vw in eval_views}
    train_cmap_dict = {vw.view_name: cm for vw, cm in zip(train_views, train_cmaps)}

    # Measure 2D-3D Leaf Homogeneity on held-out test views:
    # Render dominant leaf_id per pixel or check color coherence inside unseen 2D enclosed leaf cells!
    test_coherence_scores: list[float] = []
    for ev_v in eval_views:
        inst_ren = render_3dgs_cloud(cloud, ev_v, device=device, override_colors=color_banks["instance_palette"])
        cm_ev = eval_cmaps[ev_v.view_name]
        if cm_ev.num_valid_cells > 0:
            # Measure within-cell chromatic std (low std = single clean 3D leaf kernel group fills the unseen 2D leaf cell!)
            stds = []
            for cid in range(1, cm_ev.num_valid_cells + 1):
                m_c = cm_ev.cell_id_map == cid
                if int(m_c.sum()) >= 40:
                    stds.append(float(inst_ren[m_c].std(axis=0).mean()))
            if stds:
                # Convert std in [0, 0.35] to homogeneity score in [0, 100]%
                test_coherence_scores.append(100.0 * float(np.mean(np.clip(1.0 - np.array(stds) / 0.25, 0.0, 1.0))))

    report = {
        "device_used": str(device),
        "workspace_root": str(PROJECT_ROOT),
        "partition_summary": part_stats,
        "heldout_test_5views_evaluation": {
            "num_eval_views": len(eval_views),
            "mean_2d_enclosed_cells_on_test_views": round(
                float(np.mean([cm.num_valid_cells for cm in eval_cmaps.values()])), 1
            ),
            "within_2d_leaf_3d_instance_homogeneity_pct": round(float(np.mean(test_coherence_scores)), 2)
            if test_coherence_scores
            else 0.0,
        },
        "saved_files": saved_assets,
        "total_wall_seconds": round(time.time() - t0, 2),
    }
    report_path = out_dir / "LEAF_PARTITION_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Save full-frame and 2x canopy zoom panels on held-out test_r_79, test_r_7, test_r_1, test_r_14, and train_r_7
    all_target = [
        v for v in (train_views + eval_views)
        if v.view_name in ("test_r_79", "test_r_7", "test_r_1", "test_r_14", "train_r_7")
    ]
    for tv in all_target:
        cm = eval_cmaps[tv.view_name] if tv.view_name in eval_cmaps else train_cmap_dict[tv.view_name]
        save_5col_leaf_stylization_panels(
            [
                (out_dir / f"leaf_full_{tv.view_name}.png", None),
                (out_dir / f"leaf_canopy_zoom_{tv.view_name}.png", (240, 120, 560, 440)),
                (out_dir / f"leaf_rosette_zoom_{tv.view_name}.png", (330, 160, 610, 440)),
            ],
            tv, cm, cloud, color_banks, leaf_instances, priors, device=device,
        )

    print(f"[LeafKernels v01] COMPLETE in {time.time() - t0:.1f}s -> {report_path}", flush=True)


if __name__ == "__main__":
    main()
