"""Native CUDA 3DGS rendering, static & view-dependent network evaluation on held-out views, and comparison panels."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from diff_gaussian_rasterization import GaussianRasterizer
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

from .multimodal_data import MultiModalView
from .schema import CurveNetwork3D, resolve_safe_path
from .stage1_ray_clean import GPUViewFieldEvaluator
from .stage4_diff_refine import _make_raster_settings


@torch.no_grad()
def render_gaussian_bank(
    gs_bank: dict[str, np.ndarray],
    view: MultiModalView,
    device: torch.device,
    bg_val: float = 1.0,
) -> np.ndarray:
    """Render a line-Gaussian bank (means, covariance, opacity, colors) using installed native CUDA rasterizer."""
    if len(gs_bank["means"]) == 0:
        return np.full((view.height, view.width, 3), bg_val, dtype=np.float32)

    settings = _make_raster_settings(view, device=device, bg_val=bg_val)
    means = torch.tensor(gs_bank["means"], dtype=torch.float32, device=device).contiguous()
    cov = gs_bank["covariance"]
    if cov.ndim == 3:
        cov = cov[:, [0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]]
    cov_t = torch.tensor(cov, dtype=torch.float32, device=device).contiguous()
    opac = torch.tensor(gs_bank["opacity"].reshape(-1, 1), dtype=torch.float32, device=device).contiguous()
    cols = torch.tensor(gs_bank["colors"], dtype=torch.float32, device=device).contiguous()
    means2d = torch.zeros_like(means)

    rast_out = GaussianRasterizer(settings)(
        means3D=means,
        means2D=means2d,
        opacities=opac,
        colors_precomp=cols,
        cov3D_precomp=cov_t,
    )
    img_t = rast_out[0]
    torch.cuda.synchronize(device)
    img = img_t.permute(1, 2, 0).cpu().numpy()
    return np.clip(img, 0.0, 1.0).astype(np.float32)


def draw_vector_junctions_overlay(
    base_rgb: np.ndarray,
    net: CurveNetwork3D,
    view: MultiModalView,
) -> np.ndarray:
    """Draw explicit topological JunctionNodes (green=G1/deg2, red=T/Y deg>=3) onto rendered colored curve image."""
    canvas = (np.clip(base_rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).copy()
    R = view.w2c[:3, :3]
    t = view.w2c[:3, 3]
    for node in net.nodes.values():
        if node.degree < 2:
            continue
        xc = R @ node.position + t
        if xc[2] <= 0.2:
            continue
        u = int(round(view.fx * (xc[0] / xc[2]) + view.cx))
        v = int(round(view.fy * (xc[1] / xc[2]) + view.cy))
        if 0 <= u < view.width and 0 <= v < view.height:
            if node.degree >= 3:
                cv2.circle(canvas, (u, v), 2, (220, 25, 25), -1, lineType=cv2.LINE_AA)
            elif node.kind == "CORNER":
                cv2.circle(canvas, (u, v), 1, (20, 145, 40), -1, lineType=cv2.LINE_AA)
    return canvas


def evaluate_line_bank_vs_views(
    gs_bank: dict[str, np.ndarray],
    views: list[MultiModalView],
    train_views_for_hull: list[MultiModalView],
    pixel_scale: float,
    device: torch.device,
) -> dict[str, float]:
    """Compute multi-view visual-hull violation rate & 2D rendered edge precision/recall/Chamfer on target views."""
    pts = gs_bank["means"]
    if len(pts) == 0:
        return {
            "num_gaussians": 0,
            "hull_violation_node_pct": 0.0,
            "free_space_violation_node_pct": 0.0,
            "mean_bg_sky_leak_pixels": 0.0,
            "precision_2_5px_pct": 0.0,
            "recall_2_5px_pct": 0.0,
            "bidirectional_chamfer_2d_px": 99.0,
        }

    hull_eval = GPUViewFieldEvaluator(train_views_for_hull, device=device)
    q = hull_eval.query_points(pts, pixel_scale=pixel_scale)
    hull_bad_pct = 100.0 * float(np.mean(q["hull_viol_rate"] > 0.075))
    fsv_bad_pct = 100.0 * float(np.mean(q["free_space_viol"] > 0))

    prec_list, rec_list, cham_list, leak_list = [], [], [], []
    for v in views:
        ren = render_gaussian_bank(gs_bank, v, device=device, bg_val=1.0)
        ink = 1.0 - ren.mean(axis=2)
        pred_mask = ink > 0.08
        gt_mask = v.edge_mask

        bg_mask = v.outside_hull_dt > 2.5
        leak_px = int(np.sum(pred_mask & bg_mask))
        leak_list.append(leak_px)

        if np.any(pred_mask) and np.any(gt_mask):
            d_pred_to_gt = v.edge_dt[pred_mask]
            dt_pred = distance_transform_edt(~pred_mask)
            d_gt_to_pred = dt_pred[gt_mask]

            prec = 100.0 * float(np.mean(d_pred_to_gt <= 2.5))
            rec = 100.0 * float(np.mean(d_gt_to_pred <= 2.5))
            cham = 0.5 * (float(np.mean(np.minimum(d_pred_to_gt, 15.0))) + float(np.mean(np.minimum(d_gt_to_pred, 15.0))))
            prec_list.append(prec)
            rec_list.append(rec)
            cham_list.append(cham)

    return {
        "num_gaussians": int(len(pts)),
        "hull_violation_node_pct": hull_bad_pct,
        "free_space_violation_node_pct": fsv_bad_pct,
        "mean_bg_sky_leak_pixels": float(np.mean(leak_list)) if leak_list else 0.0,
        "precision_2_5px_pct": float(np.mean(prec_list)) if prec_list else 0.0,
        "recall_2_5px_pct": float(np.mean(rec_list)) if rec_list else 0.0,
        "bidirectional_chamfer_2d_px": float(np.mean(cham_list)) if cham_list else 99.0,
    }


def evaluate_network_vs_views(
    net: CurveNetwork3D,
    views: list[MultiModalView],
    train_views_for_hull: list[MultiModalView],
    pixel_scale: float,
    device: torch.device,
) -> dict[str, float]:
    """Evaluate a hybrid CurveNetwork3D (including view-dependent occluding contour generators using ONLY v.cam_center)."""
    base_gs = net.to_line_gaussians(color_mode="ink", use_ribbon_surflets=True, camera_center=None)
    if not net.lathe_generators and not net.tube_generators:
        return evaluate_line_bank_vs_views(base_gs, views, train_views_for_hull, pixel_scale, device)

    hull_eval = GPUViewFieldEvaluator(train_views_for_hull, device=device)
    prec_list, rec_list, cham_list, leak_list, gs_counts, hull_viols, fsv_viols = [], [], [], [], [], [], []

    for v in views:
        gs_v = net.to_line_gaussians(color_mode="ink", use_ribbon_surflets=True, camera_center=v.cam_center)
        gs_counts.append(len(gs_v["means"]))
        q = hull_eval.query_points(gs_v["means"], pixel_scale=pixel_scale)
        hull_viols.append(100.0 * float(np.mean(q["hull_viol_rate"] > 0.075)))
        fsv_viols.append(100.0 * float(np.mean(q["free_space_viol"] > 0)))

        ren = render_gaussian_bank(gs_v, v, device=device, bg_val=1.0)
        ink = 1.0 - ren.mean(axis=2)
        pred_mask = ink > 0.08
        gt_mask = v.edge_mask

        bg_mask = v.outside_hull_dt > 2.5
        leak_list.append(int(np.sum(pred_mask & bg_mask)))

        if np.any(pred_mask) and np.any(gt_mask):
            d_pred_to_gt = v.edge_dt[pred_mask]
            dt_pred = distance_transform_edt(~pred_mask)
            d_gt_to_pred = dt_pred[gt_mask]

            prec_list.append(100.0 * float(np.mean(d_pred_to_gt <= 2.5)))
            rec_list.append(100.0 * float(np.mean(d_gt_to_pred <= 2.5)))
            cham_list.append(
                0.5 * (float(np.mean(np.minimum(d_pred_to_gt, 15.0))) + float(np.mean(np.minimum(d_gt_to_pred, 15.0))))
            )

    return {
        "num_gaussians": int(round(float(np.mean(gs_counts)))) if gs_counts else 0,
        "hull_violation_node_pct": float(np.mean(hull_viols)) if hull_viols else 0.0,
        "free_space_violation_node_pct": float(np.mean(fsv_viols)) if fsv_viols else 0.0,
        "mean_bg_sky_leak_pixels": float(np.mean(leak_list)) if leak_list else 0.0,
        "precision_2_5px_pct": float(np.mean(prec_list)) if prec_list else 0.0,
        "recall_2_5px_pct": float(np.mean(rec_list)) if rec_list else 0.0,
        "bidirectional_chamfer_2d_px": float(np.mean(cham_list)) if cham_list else 99.0,
    }


def save_comparison_panel(
    out_path: str | Path,
    view: MultiModalView,
    raw_gs: dict[str, np.ndarray],
    net: CurveNetwork3D,
    device: torch.device,
    crop_box: tuple[int, int, int, int] | None = None,
) -> Path:
    """Save a 4-column comparison image: [RGB Source | Raw C2L Fragments | Reconstructed Ink | Colored Primitives + Junctions]."""
    dest = resolve_safe_path(out_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    rgb_vis = view.rgb if view.rgb is not None else np.repeat(view.alpha[..., None], 3, axis=2)
    rgb_u8 = (np.clip(rgb_vis, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    raw_ren = (render_gaussian_bank(raw_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)

    ink_gs = net.to_line_gaussians(color_mode="ink", camera_center=view.cam_center)
    col_gs = net.to_line_gaussians(color_mode="edge_class" if (net.lathe_generators or net.tube_generators) else "primitive", camera_center=view.cam_center)
    ink_ren = (render_gaussian_bank(ink_gs, view, device=device, bg_val=1.0) * 255.0 + 0.5).astype(np.uint8)
    col_ren_f = render_gaussian_bank(col_gs, view, device=device, bg_val=1.0)
    col_u8 = draw_vector_junctions_overlay(col_ren_f, net, view)

    n_gen = len(net.lathe_generators) + len(net.tube_generators)
    gen_tag = f" + {n_gen} Envelopes" if n_gen > 0 else ""
    panels = [rgb_u8, raw_ren, ink_ren, col_u8]
    titles = [
        f"{view.view_name} RGB",
        "Raw C2L Fragments (11.5k)",
        f"VecSpline3D Ink ({len(net.curves)} curves{gen_tag})",
        "Primitives / Semantic Contours + T/Y Nodes",
    ]

    if crop_box is not None:
        x0, y0, x1, y1 = crop_box
        panels = [
            cv2.resize(p[y0:y1, x0:x1], (400, 400), interpolation=cv2.INTER_NEAREST)
            for p in panels
        ]

    ph, pw = panels[0].shape[:2]
    header_h = 34
    grid = Image.new("RGB", (pw * len(panels), ph + header_h), color=(248, 248, 250))
    draw = ImageDraw.Draw(grid)
    for i, (pan, title) in enumerate(zip(panels, titles)):
        grid.paste(Image.fromarray(pan), (i * pw, header_h))
        draw.text((i * pw + 10, 9), title, fill=(25, 25, 30))

    grid.save(dest)
    return dest
