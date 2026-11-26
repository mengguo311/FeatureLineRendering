"""Stage 5: Native CUDA 3DGS per-leaf instance rendering, botanical stylization, occlusion diagnostics & exporters."""

from __future__ import annotations

import colorsys
import json
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from diff_gaussian_rasterization import GaussianRasterizationSettings, GaussianRasterizer
from PIL import Image, ImageDraw

from .data_io import CalibratedLeafView, GaussianCloud3D, PriorVectorGeometry, resolve_write_path
from .kernel_partitioner import LeafInstance3D
from .multiview_leaf_cells import EnclosedLeaf2DViewMap, LABEL_POT_OR_SOIL, LABEL_WOOD_STEM


def _make_settings(view: CalibratedLeafView, device: torch.device, sh_degree: int = 0, bg_val: float = 1.0) -> GaussianRasterizationSettings:
    w, h = view.width, view.height
    E = view.w2c.astype(np.float32)
    P = np.zeros((4, 4), dtype=np.float32)
    near, far = 0.2, 100.0
    P[0, 0] = 2.0 * view.fx / w
    P[1, 1] = 2.0 * view.fy / h
    P[0, 2] = (2.0 * view.cx + 1.0 - w) / w
    P[1, 2] = (2.0 * view.cy + 1.0 - h) / h
    P[2, 2] = far / (far - near)
    P[2, 3] = -far * near / (far - near)
    P[3, 2] = 1.0

    return GaussianRasterizationSettings(
        image_height=h,
        image_width=w,
        tanfovx=float(w / (2.0 * view.fx)),
        tanfovy=float(h / (2.0 * view.fy)),
        bg=torch.full((3,), bg_val, dtype=torch.float32, device=device),
        scale_modifier=1.0,
        viewmatrix=torch.tensor(E.T, dtype=torch.float32, device=device).contiguous(),
        projmatrix=torch.tensor((P @ E).T, dtype=torch.float32, device=device).contiguous(),
        sh_degree=sh_degree,
        campos=torch.tensor(view.cam_center, dtype=torch.float32, device=device).contiguous(),
        prefiltered=False,
        debug=False,
    )


@torch.no_grad()
def render_3dgs_cloud(
    cloud: GaussianCloud3D,
    view: CalibratedLeafView,
    device: torch.device,
    override_colors: np.ndarray | None = None,
    scale_modifier: float = 1.0,
) -> np.ndarray:
    """Render full 284,835-kernel 3DGS model with either native SH3 colors or per-kernel stylized RGB colors."""
    use_sh = override_colors is None
    with torch.cuda.device(device):
        settings = _make_settings(view, device=device, sh_degree=3 if use_sh else 0, bg_val=1.0)
        if scale_modifier != 1.0:
            settings = settings._replace(scale_modifier=float(scale_modifier))

        means_t = torch.tensor(cloud.means, dtype=torch.float32, device=device).contiguous()
        cov6_t = torch.tensor(cloud.cov6, dtype=torch.float32, device=device).contiguous()
        op_t = torch.tensor(cloud.opacities[:, None], dtype=torch.float32, device=device).contiguous()
        m2d_t = torch.zeros_like(means_t)

        if use_sh:
            shs_t = torch.tensor(cloud.shs, dtype=torch.float32, device=device).contiguous()
            img = GaussianRasterizer(settings)(
                means3D=means_t, means2D=m2d_t, shs=shs_t, opacities=op_t, cov3D_precomp=cov6_t
            )[0]
        else:
            cols_t = torch.tensor(override_colors, dtype=torch.float32, device=device).contiguous()
            img = GaussianRasterizer(settings)(
                means3D=means_t, means2D=m2d_t, colors_precomp=cols_t, opacities=op_t, cov3D_precomp=cov6_t
            )[0]

        torch.cuda.synchronize(device)
        return np.clip(img.permute(1, 2, 0).cpu().numpy(), 0.0, 1.0).astype(np.float32)


@torch.no_grad()
def render_stylized_with_occluded_ink(
    cloud: GaussianCloud3D,
    stylized_colors: np.ndarray,
    ink_gs: dict[str, np.ndarray] | None,
    view: CalibratedLeafView,
    device: torch.device,
    ink_opacity_scale: float = 0.68,
) -> np.ndarray:
    """Joint 3D depth-sorted Gaussian splatting of stylized leaf/stem/pot kernels + 3D vector ink contours (zero X-ray bleed)."""
    if ink_gs is None or len(ink_gs["means"]) == 0:
        return render_3dgs_cloud(cloud, view, device=device, override_colors=stylized_colors)

    with torch.cuda.device(device):
        settings = _make_settings(view, device=device, sh_degree=0, bg_val=1.0)
        ink_xyz = ink_gs["means"].astype(np.float32)
        # Nudge 3D ink contours 2.2 mm toward camera so front leaf-margin strokes sit cleanly on top of their own leaf,
        # while back-canopy ink strokes remain genuinely occluded behind foreground stylized leaves!
        ray_to_cam = view.cam_center.astype(np.float32)[None, :] - ink_xyz
        ray_to_cam /= np.maximum(np.linalg.norm(ray_to_cam, axis=1, keepdims=True), 1e-6)
        ink_xyz_biased = ink_xyz + 0.0022 * ray_to_cam

        cov_ink = ink_gs["covariance"].astype(np.float32)
        if cov_ink.ndim == 3:
            cov_ink = cov_ink[:, [0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]]
        op_ink = np.clip(ink_gs["opacity"].astype(np.float32) * ink_opacity_scale, 0.0, 0.92)[:, None]
        col_ink = np.broadcast_to(np.array([[0.11, 0.13, 0.10]], dtype=np.float32), (len(ink_xyz), 3)).copy()

        means_all = torch.tensor(np.concatenate([cloud.means, ink_xyz_biased], axis=0), dtype=torch.float32, device=device).contiguous()
        cov6_all = torch.tensor(np.concatenate([cloud.cov6, cov_ink], axis=0), dtype=torch.float32, device=device).contiguous()
        op_all = torch.tensor(np.concatenate([cloud.opacities[:, None], op_ink], axis=0), dtype=torch.float32, device=device).contiguous()
        col_all = torch.tensor(np.concatenate([stylized_colors, col_ink], axis=0), dtype=torch.float32, device=device).contiguous()
        m2d_all = torch.zeros_like(means_all)

        img = GaussianRasterizer(settings)(
            means3D=means_all, means2D=m2d_all, colors_precomp=col_all, opacities=op_all, cov3D_precomp=cov6_all
        )[0]
        torch.cuda.synchronize(device)
        return np.clip(img.permute(1, 2, 0).cpu().numpy(), 0.0, 1.0).astype(np.float32)


def build_stylized_kernel_colors(
    cloud: GaussianCloud3D,
    kernel_labels: np.ndarray,
    leaf_instances: list[LeafInstance3D],
) -> dict[str, np.ndarray]:
    """Generate 3 per-kernel color banks (N, 3): instance_palette, autumn_stylized, and occlusion_tier."""
    n = len(cloud.means)
    base_rgb = cloud.rgb_dc.copy()
    lum = (0.299 * base_rgb[:, 0] + 0.587 * base_rgb[:, 1] + 0.114 * base_rgb[:, 2])[:, None]

    # Neutral natural tones for Pot (-1) and Wood Stems (-2)
    pot_mask = kernel_labels == LABEL_POT_OR_SOIL
    wood_mask = kernel_labels == LABEL_WOOD_STEM

    inst_colors = base_rgb.copy()
    autumn_colors = base_rgb.copy()
    occ_colors = base_rgb.copy()

    inst_colors[pot_mask] = 0.22 + 0.35 * base_rgb[pot_mask]
    inst_colors[wood_mask] = np.array([0.48, 0.38, 0.28], dtype=np.float32) * (0.65 + 0.6 * lum[wood_mask])
    occ_colors[pot_mask] = 0.78 * np.ones((int(pot_mask.sum()), 3), dtype=np.float32)
    occ_colors[wood_mask] = np.array([0.55, 0.48, 0.42], dtype=np.float32)

    # Golden-ratio hue sequence so spatially adjacent leaf IDs receive maximally distinct colors!
    golden_conj = 0.618033988749895
    z_all_leaves = np.array([lf.centroid[2] for lf in leaf_instances], dtype=np.float64)
    z_lo = float(np.percentile(z_all_leaves, 5.0)) if len(z_all_leaves) else -0.3
    z_hi = float(np.percentile(z_all_leaves, 95.0)) if len(z_all_leaves) else 0.9

    for lf in leaf_instances:
        k_idx = lf.kernel_indices
        if len(k_idx) == 0:
            continue

        # 1. Distinct Instance Palette (modulated gently by natural kernel shading so 3D leaf relief remains crisp!)
        hue = (lf.leaf_id * golden_conj) % 1.0
        sat = 0.68 + 0.20 * ((lf.leaf_id * 0.37) % 1.0)
        val = 0.88
        c_inst = np.array(colorsys.hsv_to_rgb(hue, sat, val), dtype=np.float32)
        shade = np.clip(0.68 + 0.55 * lum[k_idx], 0.55, 1.12)
        inst_colors[k_idx] = np.clip(c_inst[None, :] * shade, 0.0, 1.0)

        # 2. Per-Leaf Coherent Autumn / Botanical Watercolor Stylization!
        # Upper/outer sunlit leaves warm into golden-amber & coral; lower/shaded leaves stay rich jade/sage;
        # PLUS smooth tip-to-base gradient along each leaf's own major axis e_len!
        sun_t = float(np.clip((lf.centroid[2] - z_lo) / max(z_hi - z_lo, 1e-4), 0.0, 1.0))
        leaf_rand = ((lf.leaf_id * 1103515245 + 12345) & 0x7FFFFFFF) / float(0x7FFFFFFF)
        warmth = np.clip(0.65 * sun_t + 0.35 * leaf_rand, 0.0, 1.0)
        # Interpolate hue from rich sage-emerald (h=0.30) through gold (h=0.12) to autumn coral-crimson (h=0.03)
        h_aut = 0.30 * (1.0 - warmth) + 0.035 * warmth
        s_aut = 0.62 + 0.22 * warmth
        v_aut = 0.78 + 0.16 * warmth
        c_base_aut = np.array(colorsys.hsv_to_rgb(h_aut, s_aut, v_aut), dtype=np.float32)
        c_tip_aut = np.array(colorsys.hsv_to_rgb(max(0.01, h_aut - 0.05), min(0.92, s_aut + 0.10), min(0.98, v_aut + 0.08)), dtype=np.float32)

        rel_u = ((cloud.means[k_idx].astype(np.float64) - lf.centroid[None, :]) @ lf.axis_length) / max(0.5 * lf.length_world, 1e-4)
        u_01 = np.clip(0.5 * (rel_u + 1.0), 0.0, 1.0).astype(np.float32)[:, None]
        grad_col = (1.0 - u_01) * c_base_aut[None, :] + u_01 * c_tip_aut[None, :]
        # Quantized cel-like luminance band per kernel for painterly botanical illustration look
        cel_shade = np.where(lum[k_idx] > 0.52, 1.06, np.where(lum[k_idx] > 0.34, 0.92, 0.76)).astype(np.float32)
        autumn_colors[k_idx] = np.clip(grad_col * cel_shade, 0.0, 1.0)

        # 3. Occlusion Tier Diagnostic Color
        if lf.visibility_tier == "OUTER_ENCLOSED":
            c_occ = np.array([0.10, 0.74, 0.40], dtype=np.float32)   # Emerald Green: Unoccluded Closed Leaf
        elif lf.visibility_tier == "MID_PARTIAL_OCCLUDED":
            c_occ = np.array([0.94, 0.62, 0.08], dtype=np.float32)   # Warm Amber: Partially Occluded Mid-Canopy
        else:
            c_occ = np.array([0.36, 0.30, 0.78], dtype=np.float32)   # Indigo/Violet: Deeply Occluded Inner Core
        occ_colors[k_idx] = np.clip(c_occ[None, :] * (0.70 + 0.45 * lum[k_idx]), 0.0, 1.0)

    return {
        "instance_palette": inst_colors,
        "autumn_stylized": autumn_colors,
        "occlusion_tier": occ_colors,
    }


def render_2d_cells_overlay(view: CalibratedLeafView, cmap: EnclosedLeaf2DViewMap) -> np.ndarray:
    """Visualize detected 2D enclosed leaf cells on top of the view's RGB image."""
    rgb_u8 = (np.clip(view.rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    cid = cmap.cell_id_map
    out = rgb_u8.copy()
    if cmap.num_valid_cells > 0:
        golden = 0.61803398875
        lut = np.zeros((cmap.num_valid_cells + 1, 3), dtype=np.uint8)
        for k in range(1, cmap.num_valid_cells + 1):
            r, g, b = colorsys.hsv_to_rgb((k * golden) % 1.0, 0.78, 0.95)
            lut[k] = [int(r * 255), int(g * 255), int(b * 255)]
        colored = lut[cid]
        has_c = cid > 0
        out[has_c] = (0.35 * rgb_u8[has_c] + 0.65 * colored[has_c]).astype(np.uint8)

        # Crisp dark cell boundaries
        gx = cv2.Sobel(cid.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(cid.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
        bdr = (np.hypot(gx, gy) > 0.1) & has_c
        out[bdr] = [20, 25, 20]
    return out


def draw_projected_3d_leaf_loops(
    base_img: np.ndarray,
    leaf_instances: list[LeafInstance3D],
    view: CalibratedLeafView,
) -> np.ndarray:
    """Overlay closed 3D leaf boundary loops of front-visible OUTER_ENCLOSED leaves onto an image."""
    canvas = (np.clip(base_img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).copy()
    R = view.w2c[:3, :3]
    t = view.w2c[:3, 3]
    for lf in leaf_instances:
        if lf.visibility_tier == "DEEP_OCCLUDED":
            continue
        ctr_c = R @ lf.centroid + t
        if ctr_c[2] <= 0.2:
            continue
        uc = int(round(view.fx * (ctr_c[0] / ctr_c[2]) + view.cx))
        vc = int(round(view.fy * (ctr_c[1] / ctr_c[2]) + view.cy))
        if not (0 <= uc < view.width and 0 <= vc < view.height):
            continue
        if ctr_c[2] > float(view.front_depth[vc, uc]) + 0.016:
            continue

        pts_c = lf.boundary_loop_3d @ R.T + t[None, :]
        if np.any(pts_c[:, 2] <= 0.2):
            continue
        us = np.round(view.fx * (pts_c[:, 0] / pts_c[:, 2]) + view.cx).astype(np.int32)
        vs = np.round(view.fy * (pts_c[:, 1] / pts_c[:, 2]) + view.cy).astype(np.int32)
        in_img = (us >= 0) & (us < view.width) & (vs >= 0) & (vs < view.height)
        if not np.all(in_img):
            continue
        vis_verts = pts_c[:, 2] <= (view.front_depth[vs, us] + 0.016)
        if float(np.mean(vis_verts)) < 0.65:
            continue
        poly = np.column_stack([us, vs]).reshape(-1, 1, 2)
        cv2.polylines(canvas, [poly], isClosed=True, color=(15, 20, 15), thickness=1, lineType=cv2.LINE_AA)
    return canvas


def save_5col_leaf_stylization_panels(
    out_paths_and_crops: list[tuple[str | Path, tuple[int, int, int, int] | None]],
    view: CalibratedLeafView,
    cmap_2d: EnclosedLeaf2DViewMap,
    cloud: GaussianCloud3D,
    color_banks: dict[str, np.ndarray],
    leaf_instances: list[LeafInstance3D],
    priors: PriorVectorGeometry,
    device: torch.device,
) -> list[Path]:
    """Render 5 base images once for a view and save full-frame + cropped 5-column visual panels."""
    orig_rgb = render_3dgs_cloud(cloud, view, device=device, override_colors=None)
    orig_u8 = (orig_rgb * 255.0 + 0.5).astype(np.uint8)
    cells_2d_u8 = render_2d_cells_overlay(view, cmap_2d)

    inst_rgb = render_3dgs_cloud(cloud, view, device=device, override_colors=color_banks["instance_palette"])
    inst_u8 = draw_projected_3d_leaf_loops(inst_rgb, leaf_instances, view)

    aut_ink_rgb = render_stylized_with_occluded_ink(
        cloud, color_banks["autumn_stylized"], priors.ink_gaussians, view, device=device, ink_opacity_scale=0.68
    )
    aut_u8 = (aut_ink_rgb * 255.0 + 0.5).astype(np.uint8)

    occ_rgb = render_3dgs_cloud(cloud, view, device=device, override_colors=color_banks["occlusion_tier"])
    occ_u8 = (occ_rgb * 255.0 + 0.5).astype(np.uint8)

    base_panels = [orig_u8, cells_2d_u8, inst_u8, aut_u8, occ_u8]
    titles = [
        f"{view.view_name} Native 3DGS",
        f"2D Closed Cells ({cmap_2d.num_valid_cells})",
        f"3DGS Leaf Kernels ({len(leaf_instances)} leaves)",
        "Botanical Stylized 3DGS + Ink",
        "Occlusion Tier (Grn=Open, Amb=Mid, Pur=Deep)",
    ]

    saved: list[Path] = []
    for out_path, crop_box in out_paths_and_crops:
        dest = resolve_write_path(out_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if crop_box is not None:
            x0, y0, x1, y1 = crop_box
            panels = [cv2.resize(p[y0:y1, x0:x1], (360, 360), interpolation=cv2.INTER_NEAREST) for p in base_panels]
        else:
            panels = base_panels
        ph, pw = panels[0].shape[:2]
        header_h = 34
        grid = Image.new("RGB", (pw * len(panels), ph + header_h), color=(248, 248, 250))
        draw = ImageDraw.Draw(grid)
        for i, (pan, title) in enumerate(zip(panels, titles)):
            grid.paste(Image.fromarray(pan), (i * pw, header_h))
            draw.text((i * pw + 8, 9), title, fill=(20, 20, 25))
        grid.save(dest)
        saved.append(dest)
    return saved


def export_leaf_kernel_assets(
    out_dir: str | Path,
    cloud: GaussianCloud3D,
    kernel_labels: np.ndarray,
    leaf_instances: list[LeafInstance3D],
    color_banks: dict[str, np.ndarray],
    stats: dict[str, Any],
) -> dict[str, str]:
    """Export per-kernel leaf_id NPZ, leaf_instances JSON, closed 3D boundary loops OBJ, and cambered leaf patch meshes OBJ."""
    out = resolve_write_path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    npz_path = out / "leaf_partitioned_kernels.npz"
    np.savez_compressed(
        npz_path,
        kernel_leaf_id=kernel_labels.astype(np.int32),
        means=cloud.means,
        opacities=cloud.opacities,
        instance_palette_rgb=color_banks["instance_palette"],
        autumn_stylized_rgb=color_banks["autumn_stylized"],
        occlusion_tier_rgb=color_banks["occlusion_tier"],
    )

    # Export closed 3D leaf boundary wireframes OBJ
    loops_obj = out / "leaf_closed_boundaries.obj"
    loop_lines = ["# ficus_leaf_kernels_v01 Closed 3D Leaf Boundary Loops"]
    v_off = 1
    for lf in leaf_instances:
        loop_lines.append(f"g LEAF_{lf.leaf_id:04d}_{lf.visibility_tier}")
        for p in lf.boundary_loop_3d:
            loop_lines.append(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}")
        n_v = len(lf.boundary_loop_3d)
        idx_str = " ".join(str(v_off + k) for k in range(n_v)) + f" {v_off}"
        loop_lines.append(f"l {idx_str}")
        v_off += n_v
    tmp_l = loops_obj.with_name(f"{loops_obj.name}.tmp-{os.getpid()}")
    tmp_l.write_text("\n".join(loop_lines) + "\n", encoding="utf-8")
    os.replace(tmp_l, loops_obj)

    # Export triangulated 3D cambered leaf patch meshes OBJ (fan from leaf centroid to closed 24-pt loop)
    mesh_obj = out / "leaf_patches_mesh.obj"
    mesh_lines = ["# ficus_leaf_kernels_v01 Cambered 3D Leaf Surface Patches"]
    v_off_m = 1
    for lf in leaf_instances:
        mesh_lines.append(f"g LEAF_PATCH_{lf.leaf_id:04d}_{lf.visibility_tier}")
        nv = lf.normal
        c = lf.centroid
        mesh_lines.append(f"v {c[0]:.6f} {c[1]:.6f} {c[2]:.6f}")
        mesh_lines.append(f"vn {nv[0]:.5f} {nv[1]:.5f} {nv[2]:.5f}")
        for p in lf.boundary_loop_3d:
            mesh_lines.append(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}")
            mesh_lines.append(f"vn {nv[0]:.5f} {nv[1]:.5f} {nv[2]:.5f}")
        n_b = len(lf.boundary_loop_3d)
        c_idx = v_off_m
        for k in range(n_b):
            b0 = v_off_m + 1 + k
            b1 = v_off_m + 1 + ((k + 1) % n_b)
            mesh_lines.append(f"f {c_idx}//{c_idx} {b0}//{b0} {b1}//{b1}")
        v_off_m += 1 + n_b
    tmp_m = mesh_obj.with_name(f"{mesh_obj.name}.tmp-{os.getpid()}")
    tmp_m.write_text("\n".join(mesh_lines) + "\n", encoding="utf-8")
    os.replace(tmp_m, mesh_obj)

    doc = {
        "schema": "ficus_leaf_kernels/v01",
        "summary": stats,
        "leaves": [
            {
                "leaf_id": int(lf.leaf_id),
                "total_kernels": int(len(lf.kernel_indices)),
                "active_kernels": int(lf.active_kernel_count),
                "visibility_tier": lf.visibility_tier,
                "mean_unoccluded_views": round(float(lf.mean_vis_views), 2),
                "closure_confidence": round(float(lf.closure_confidence), 3),
                "centroid": [round(float(x), 5) for x in lf.centroid],
                "normal": [round(float(x), 5) for x in lf.normal],
                "length_world": round(float(lf.length_world), 5),
                "width_world": round(float(lf.width_world), 5),
                "thickness_world": round(float(lf.thickness_world), 5),
                "area_world": round(float(lf.area_world), 6),
            }
            for lf in leaf_instances
        ],
    }
    json_path = out / "leaf_instances.json"
    tmp_j = json_path.with_name(f"{json_path.name}.tmp-{os.getpid()}")
    tmp_j.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp_j, json_path)

    return {
        "kernels_npz": str(npz_path),
        "instances_json": str(json_path),
        "closed_boundaries_obj": str(loops_obj),
        "leaf_patches_mesh_obj": str(mesh_obj),
    }
