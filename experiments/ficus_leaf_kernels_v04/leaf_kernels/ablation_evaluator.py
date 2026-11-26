"""Quantitative 5-Arm Ablation Evaluator & 6-Column Visual Comparison Renderer on Held-Out Test Views."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

from .data_io import CalibratedLeafView, GaussianCloud3D, PriorVectorGeometry, resolve_write_path
from .kernel_partitioner import LeafInstance3D
from .multiview_leaf_cells import EnclosedLeaf2DViewMap
from .stylize_and_render import _make_settings, render_3dgs_cloud, render_stylized_with_occluded_ink
from diff_gaussian_rasterization import GaussianRasterizer


@dataclass
class ArmModelBundle:
    """Complete 3DGS model + leaf partition + stylized color banks for one ablation arm."""

    arm_id: str
    short_title: str
    cloud: GaussianCloud3D
    kernel_labels: np.ndarray
    leaf_instances: list[LeafInstance3D]
    color_banks: dict[str, np.ndarray]
    build_stats: dict[str, Any]
    wall_seconds: float


@torch.no_grad()
def render_alpha_mask(cloud: GaussianCloud3D, view: CalibratedLeafView, device: torch.device) -> np.ndarray:
    """Render accumulated 3DGS silhouette alpha on GPU."""
    with torch.cuda.device(device):
        settings = _make_settings(view, device=device, sh_degree=0, bg_val=0.0)
        means_t = torch.tensor(cloud.means, dtype=torch.float32, device=device).contiguous()
        cov6_t = torch.tensor(cloud.cov6, dtype=torch.float32, device=device).contiguous()
        op_t = torch.tensor(cloud.opacities[:, None], dtype=torch.float32, device=device).contiguous()
        ones_t = torch.ones_like(means_t)
        m2d_t = torch.zeros_like(means_t)
        out = GaussianRasterizer(settings)(
            means3D=means_t, means2D=m2d_t, colors_precomp=ones_t, opacities=op_t, cov3D_precomp=cov6_t
        )[0]
        torch.cuda.synchronize(device)
        return np.clip(out[0].cpu().numpy(), 0.0, 1.0).astype(np.float32)


def evaluate_arm_on_heldout_views(
    arm: ArmModelBundle,
    eval_views: list[CalibratedLeafView],
    eval_cmaps: dict[str, EnclosedLeaf2DViewMap],
    priors: PriorVectorGeometry,
    device: torch.device,
) -> dict[str, float]:
    """Evaluate an ablation arm across 5 orthogonal metrics on the 5 strictly held-out test views.

    Metrics:
      1. front_leaf_xray_transmittance_pct (lower is better): mean residual X-ray transmittance (1 - alpha_outer)
         through foreground OUTER_ENCLOSED leaves on multi-layer overlapping pixels (directly measures X-ray bleed).
      2. single_leaf_core_purity_pct (higher is better): % single-leaf chromatic concentration inside
         unseen 2D enclosed leaf cells on test views.
      3. inter_leaf_seam_sharpness (higher is better): mean spatial color gradient ||grad(I_flat)||_2
         evaluated on ground-truth C2L50 inter-leaf edges inside the foliage crown (scaled x100).
      4. pure_3dgs_c2l_boundary_recall_pct (higher is better): % of ground-truth C2L50 leaf boundaries
         captured by pure-3DGS stylized leaf rendering alone (without external ink).
      5. intra_leaf_venation_detail (higher is better): internal botanical contrast inside leaf blades (x100)
         + silhouette_iou_vs_gt_pct (higher is better) verifying zero leaf erosion.
    """
    kid = arm.kernel_labels
    outer_ids = [lf.leaf_id for lf in arm.leaf_instances if lf.visibility_tier == "OUTER_ENCLOSED"]
    mid_deep_ids = [lf.leaf_id for lf in arm.leaf_instances if lf.visibility_tier != "OUTER_ENCLOSED"]

    outer_mask_k = np.isin(kid, outer_ids)
    back_mask_k = np.isin(kid, mid_deep_ids)

    bleed_list: list[float] = []
    purity_list: list[float] = []
    seam_grad_list: list[float] = []
    bdr_rec_list: list[float] = []
    vein_detail_list: list[float] = []
    iou_list: list[float] = []

    for ev in eval_views:
        # 1. Silhouette IoU vs GT
        ren_alpha = render_alpha_mask(arm.cloud, ev, device=device)
        gt_fg = ev.alpha > 0.50
        pr_fg = ren_alpha > 0.50
        inter = int(np.sum(gt_fg & pr_fg))
        union = max(int(np.sum(gt_fg | pr_fg)), 1)
        iou_list.append(100.0 * inter / union)

        # 2. Direct Foreground-Leaf X-Ray Transmittance on Multi-Layer Overlap Pixels!
        with torch.cuda.device(device):
            s_blk = _make_settings(ev, device=device, sh_degree=0, bg_val=0.0)
            m_out = torch.tensor(arm.cloud.means[outer_mask_k], dtype=torch.float32, device=device).contiguous()
            c6_out = torch.tensor(arm.cloud.cov6[outer_mask_k], dtype=torch.float32, device=device).contiguous()
            op_out = torch.tensor(arm.cloud.opacities[outer_mask_k, None], dtype=torch.float32, device=device).contiguous()
            alpha_outer = (
                GaussianRasterizer(s_blk)(
                    means3D=m_out, means2D=torch.zeros_like(m_out), colors_precomp=torch.ones_like(m_out), opacities=op_out, cov3D_precomp=c6_out
                )[0][0]
                .cpu()
                .numpy()
            )
            m_bck = torch.tensor(arm.cloud.means[back_mask_k], dtype=torch.float32, device=device).contiguous()
            c6_bck = torch.tensor(arm.cloud.cov6[back_mask_k], dtype=torch.float32, device=device).contiguous()
            op_bck = torch.tensor(arm.cloud.opacities[back_mask_k, None], dtype=torch.float32, device=device).contiguous()
            alpha_back = (
                GaussianRasterizer(s_blk)(
                    means3D=m_bck, means2D=torch.zeros_like(m_bck), colors_precomp=torch.ones_like(m_bck), opacities=op_bck, cov3D_precomp=c6_bck
                )[0][0]
                .cpu()
                .numpy()
            )
        # Pixels where an outer leaf overlaps in front of a mid/deep leaf
        overlap_px = gt_fg & (alpha_outer >= 0.25) & (alpha_back >= 0.20)
        if int(overlap_px.sum()) > 10:
            # Residual transmittance (1 - alpha_outer) measures exact % of background leaf leaking through front leaf!
            bleed_list.append(100.0 * float(np.mean(np.clip(1.0 - alpha_outer[overlap_px], 0.0, 1.0))))

        # 3. Single-leaf core chromatic purity & Inter-leaf seam sharpness on flat instance palette
        ren_flat = render_3dgs_cloud(arm.cloud, ev, device=device, override_colors=arm.color_banks["flat_instance_palette"])
        cm = eval_cmaps[ev.view_name]
        for cid in range(1, cm.num_valid_cells + 1):
            mc = cm.cell_id_map == cid
            if int(mc.sum()) >= 40:
                med_c = np.median(ren_flat[mc], axis=0)
                mad = float(np.mean(np.abs(ren_flat[mc] - med_c[None, :])))
                purity_list.append(100.0 * float(np.clip(1.0 - mad / 0.20, 0.0, 1.0)))

        fol_fg = gt_fg & ((alpha_outer + alpha_back) > 0.25)
        gx = cv2.Sobel(ren_flat, cv2.CV_32F, 1, 0, ksize=3) / 8.0
        gy = cv2.Sobel(ren_flat, cv2.CV_32F, 0, 1, ksize=3) / 8.0
        grad_mag = np.sqrt(np.sum(gx * gx + gy * gy, axis=2))
        eroded_fg = cv2.erode(fol_fg.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        seam_pixels = ev.skeleton & eroded_fg
        if int(seam_pixels.sum()) >= 20:
            seam_grad_list.append(100.0 * float(np.mean(grad_mag[seam_pixels])))

        # 4. Pure-3DGS Botanical Stylized C2L Boundary Recall & Intra-Leaf Venation Contrast
        ren_sty = render_3dgs_cloud(arm.cloud, ev, device=device, override_colors=arm.color_banks["botanical_stylized"])
        sty_gray = 0.299 * ren_sty[..., 0] + 0.587 * ren_sty[..., 1] + 0.114 * ren_sty[..., 2]
        sgx = cv2.Sobel(sty_gray, cv2.CV_32F, 1, 0, ksize=3) / 8.0
        sgy = cv2.Sobel(sty_gray, cv2.CV_32F, 0, 1, ksize=3) / 8.0
        sty_g = np.hypot(sgx, sgy)
        pred_edge = (sty_g > 0.038) & fol_fg
        gt_edge = (ev.skeleton | (ev.darkness > 0.24)) & fol_fg
        if int(pred_edge.sum()) > 10 and int(gt_edge.sum()) > 10:
            dt_pr = distance_transform_edt(~pred_edge)
            bdr_rec_list.append(100.0 * float(np.mean(dt_pr[gt_edge] <= 1.8)))

        # Intra-leaf botanical venation contrast strictly inside 2D closed leaf interiors (eroded away from perimeter!)
        if cm.num_valid_cells > 0:
            cell_int = cv2.erode((cm.cell_id_map > 0).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
            if int(cell_int.sum()) >= 30:
                vein_detail_list.append(100.0 * float(np.mean(sty_g[cell_int])))

    return {
        "num_total_kernels": int(len(arm.cloud.means)),
        "front_leaf_xray_transmittance_pct": round(float(np.mean(bleed_list)), 2) if bleed_list else 0.0,
        "single_leaf_core_purity_pct": round(float(np.mean(purity_list)), 2) if purity_list else 0.0,
        "inter_leaf_seam_sharpness": round(float(np.mean(seam_grad_list)), 2) if seam_grad_list else 0.0,
        "pure_3dgs_c2l_boundary_recall_pct": round(float(np.mean(bdr_rec_list)), 2) if bdr_rec_list else 0.0,
        "intra_leaf_venation_detail": round(float(np.mean(vein_detail_list)), 2) if vein_detail_list else 0.0,
        "silhouette_iou_vs_gt_pct": round(float(np.mean(iou_list)), 2),
    }


def save_6col_ablation_comparison_panels(
    out_dir: str | Path,
    view: CalibratedLeafView,
    source_cloud: GaussianCloud3D,
    arms: list[ArmModelBundle],
    priors: PriorVectorGeometry,
    device: torch.device,
    crops: dict[str, tuple[int, int, int, int] | None],
) -> list[Path]:
    """Render 6-column comparison grids (Instance Segmentation & Botanical Stylization) across all 5 arms!"""
    out = resolve_write_path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    orig_u8 = (render_3dgs_cloud(source_cloud, view, device=device, override_colors=None) * 255.0 + 0.5).astype(np.uint8)

    inst_cols_u8 = [orig_u8]
    sty_cols_u8 = [orig_u8]
    sty_ink_cols_u8 = [orig_u8]

    inst_titles = [f"{view.view_name} Native 3DGS"]
    sty_titles = [f"{view.view_name} Native 3DGS"]
    sty_ink_titles = [f"{view.view_name} Native 3DGS"]

    for arm in arms:
        r_inst = render_3dgs_cloud(arm.cloud, view, device=device, override_colors=arm.color_banks["instance_palette"])
        inst_cols_u8.append((r_inst * 255.0 + 0.5).astype(np.uint8))
        inst_titles.append(f"{arm.short_title} (Inst)")

        r_sty = render_3dgs_cloud(arm.cloud, view, device=device, override_colors=arm.color_banks["botanical_stylized"])
        sty_cols_u8.append((r_sty * 255.0 + 0.5).astype(np.uint8))
        sty_titles.append(f"{arm.short_title} (Pure 3DGS)")

        r_sty_ink = render_stylized_with_occluded_ink(
            arm.cloud, arm.color_banks["botanical_stylized"], priors.ink_gaussians, view, device=device, ink_opacity_scale=0.62
        )
        sty_ink_cols_u8.append((r_sty_ink * 255.0 + 0.5).astype(np.uint8))
        sty_ink_titles.append(f"{arm.short_title} (+3D Ink)")

    saved_paths: list[Path] = []

    def _write_grid(dest: Path, imgs: list[np.ndarray], titles: list[str], box: tuple[int, int, int, int] | None) -> None:
        if box is not None:
            x0, y0, x1, y1 = box
            tiles = [cv2.resize(im[y0:y1, x0:x1], (340, 340), interpolation=cv2.INTER_NEAREST) for im in imgs]
        else:
            tiles = imgs
        th, tw = tiles[0].shape[:2]
        hh = 34
        canvas = Image.new("RGB", (tw * len(tiles), th + hh), color=(248, 248, 250))
        draw = ImageDraw.Draw(canvas)
        for idx_t, (tile, ttl) in enumerate(zip(tiles, titles)):
            canvas.paste(Image.fromarray(tile), (idx_t * tw, hh))
            draw.text((idx_t * tw + 8, 9), ttl, fill=(20, 20, 25))
        canvas.save(resolve_write_path(dest))
        saved_paths.append(dest)

    for tag, box in crops.items():
        _write_grid(out / f"ablation_inst_{tag}_{view.view_name}.png", inst_cols_u8, inst_titles, box)
        _write_grid(out / f"ablation_pure_stylized_{tag}_{view.view_name}.png", sty_cols_u8, sty_titles, box)
        _write_grid(out / f"ablation_ink_stylized_{tag}_{view.view_name}.png", sty_ink_cols_u8, sty_ink_titles, box)

    return saved_paths
