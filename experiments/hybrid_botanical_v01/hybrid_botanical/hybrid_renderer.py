"""Dual-Mode Hybrid Renderer: Native 3DGS Splatting + Infinite-Resolution Analytical Dual-Arc Spline Super-Zoom."""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np
import torch
from diff_gaussian_rasterization import GaussianRasterizationSettings, GaussianRasterizer
from scipy.interpolate import BSpline

from .schema_and_io import (
    LABEL_POT_BASE,
    LABEL_WOOD_SKELETON,
    CalibratedSceneView,
    DualArcTrimmedLeafPatch,
    GaussianCloudBank,
    HybridBotanicalPrimitive,
    clamped_cubic_knots,
    eval_clamped_bspline,
)


def make_pinhole_settings(
    w2c: np.ndarray,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    width: int,
    height: int,
    cam_center: np.ndarray,
    device: torch.device,
    sh_degree: int = 0,
    bg_val: float = 1.0,
    scale_modifier: float = 1.0,
) -> GaussianRasterizationSettings:
    E = w2c.astype(np.float32)
    P = np.zeros((4, 4), dtype=np.float32)
    near, far = 0.2, 100.0
    P[0, 0] = 2.0 * fx / width
    P[1, 1] = 2.0 * fy / height
    P[0, 2] = (2.0 * cx + 1.0 - width) / width
    P[1, 2] = (2.0 * cy + 1.0 - height) / height
    P[2, 2] = far / (far - near)
    P[2, 3] = -far * near / (far - near)
    P[3, 2] = 1.0

    return GaussianRasterizationSettings(
        image_height=height,
        image_width=width,
        tanfovx=float(width / (2.0 * fx)),
        tanfovy=float(height / (2.0 * fy)),
        bg=torch.full((3,), bg_val, dtype=torch.float32, device=device),
        scale_modifier=float(scale_modifier),
        viewmatrix=torch.tensor(E.T, dtype=torch.float32, device=device).contiguous(),
        projmatrix=torch.tensor((P @ E).T, dtype=torch.float32, device=device).contiguous(),
        sh_degree=sh_degree,
        campos=torch.tensor(cam_center, dtype=torch.float32, device=device).contiguous(),
        prefiltered=False,
        debug=False,
    )


def zoomed_camera_intrinsics(
    view: CalibratedSceneView,
    roi_box: tuple[int, int, int, int] | None,
    out_w: int,
    out_h: int,
) -> tuple[float, float, float, float]:
    """Compute exact optical-zoom pinhole intrinsics (fx', fy', cx', cy') for a sub-window roi_box."""
    if roi_box is None:
        sx = out_w / float(view.width)
        sy = out_h / float(view.height)
        return view.fx * sx, view.fy * sy, (view.cx + 0.5) * sx - 0.5, (view.cy + 0.5) * sy - 0.5

    x0, y0, x1, y1 = roi_box
    sx = out_w / float(x1 - x0)
    sy = out_h / float(y1 - y0)
    fx_z = view.fx * sx
    fy_z = view.fy * sy
    cx_z = (view.cx - x0 + 0.5) * sx - 0.5
    cy_z = (view.cy - y0 + 0.5) * sy - 0.5
    return fx_z, fy_z, cx_z, cy_z


@torch.no_grad()
def render_cloud_bank(
    cloud: GaussianCloudBank,
    view: CalibratedSceneView,
    device: torch.device,
    override_rgb: np.ndarray | None = None,
    active_mask: np.ndarray | None = None,
    roi_box: tuple[int, int, int, int] | None = None,
    out_size: tuple[int, int] | None = None,
    bg_val: float = 1.0,
    scale_modifier: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Render GaussianCloudBank (RGB and accumulated alpha) at standard or optical-zoom resolution."""
    out_w, out_h = out_size if out_size is not None else (view.width, view.height)
    fx, fy, cx, cy = zoomed_camera_intrinsics(view, roi_box, out_w, out_h)

    rgb_arr = override_rgb if override_rgb is not None else cloud.rgb
    if active_mask is not None:
        means = cloud.means[active_mask]
        cov6 = cloud.cov6[active_mask]
        op = cloud.opacities[active_mask]
        rgb_arr = rgb_arr[active_mask]
    else:
        means, cov6, op = cloud.means, cloud.cov6, cloud.opacities

    if len(means) == 0:
        return np.full((out_h, out_w, 3), bg_val, dtype=np.float32), np.zeros((out_h, out_w), dtype=np.float32)

    with torch.cuda.device(device):
        s_rgb = make_pinhole_settings(
            view.w2c, fx, fy, cx, cy, out_w, out_h, view.cam_center, device, sh_degree=0, bg_val=bg_val, scale_modifier=scale_modifier
        )
        s_al = s_rgb._replace(bg=torch.zeros(3, dtype=torch.float32, device=device))

        m_t = torch.tensor(means, dtype=torch.float32, device=device).contiguous()
        c6_t = torch.tensor(cov6, dtype=torch.float32, device=device).contiguous()
        op_t = torch.tensor(op[:, None], dtype=torch.float32, device=device).contiguous()
        col_t = torch.tensor(rgb_arr, dtype=torch.float32, device=device).contiguous()
        m2d = torch.zeros_like(m_t)

        ren_rgb = GaussianRasterizer(s_rgb)(
            means3D=m_t, means2D=m2d, colors_precomp=col_t, opacities=op_t, cov3D_precomp=c6_t
        )[0].permute(1, 2, 0).clamp(0.0, 1.0).cpu().numpy()
        ren_al = GaussianRasterizer(s_al)(
            means3D=m_t, means2D=m2d, colors_precomp=torch.ones_like(m_t), opacities=op_t, cov3D_precomp=c6_t
        )[0][0].clamp(0.0, 1.0).cpu().numpy()
        torch.cuda.synchronize(device)
        return np.ascontiguousarray(ren_rgb, dtype=np.float32), np.ascontiguousarray(ren_al, dtype=np.float32)


@torch.no_grad()
def render_analytical_spline_trimmed_hybrid(
    model: HybridBotanicalPrimitive,
    view: CalibratedSceneView,
    device: torch.device,
    override_rgb: np.ndarray | None = None,
    active_leaf_ids: set[int] | None = None,
    roi_box: tuple[int, int, int, int] | None = None,
    out_size: tuple[int, int] = (720, 720),
    draw_vector_ink_rims: bool = False,
) -> np.ndarray:
    """Infinite-resolution Analytical Dual-Arc B-Spline Surface Ray-Casting + Normalized 3DGS Radiance Renderer!

    At 8x optical zoom (e.g., 100x100 px source ROI rendered at 800x800 px):
      1. Renders smooth wood/pot depth & radiance buffer.
      2. For each visible DualArcTrimmedLeafPatch overlapping the zoomed viewport:
         - Solves exact 3D camera-ray intersection with the cambered leaf surface w_l(u, v) on GPU;
         - Evaluates exact analytical Dual-Arc Cubic B-Spline signed boundary margin
           d_in(s, v) = min(u, L - u, v - v_right(s), v_left(s) - v) with 0.65-px analytical AA;
         - Evaluates partition-of-unity normalized Gaussian radiance inside the spline so interior leaf shading
           is 100% continuous & pinhole-free while leaf tips and margins are infinitely vector-sharp!
    """
    out_w, out_h = out_size
    fx, fy, cx, cy = zoomed_camera_intrinsics(view, roi_box, out_w, out_h)
    rgb_src = override_rgb if override_rgb is not None else model.cloud.rgb

    # 1. Render Wood & Pot base layer + camera-z depth buffer
    non_leaf_m = model.cloud.kernel_labels < 0
    bg_rgb, bg_al = render_cloud_bank(
        model.cloud, view, device, override_rgb=rgb_src, active_mask=non_leaf_m,
        roi_box=roi_box, out_size=out_size, bg_val=1.0, scale_modifier=1.05,
    )

    with torch.cuda.device(device):
        # Compute wood/pot depth buffer via soft-min z splatting
        R_w2c = torch.tensor(view.w2c[:3, :3], dtype=torch.float32, device=device)
        t_w2c = torch.tensor(view.w2c[:3, 3], dtype=torch.float32, device=device)
        cam_o = torch.tensor(view.cam_center, dtype=torch.float32, device=device)
        R_c2w = torch.tensor(view.c2w[:3, :3], dtype=torch.float32, device=device)

        z_buf = torch.full((out_h, out_w), 1e6, dtype=torch.float32, device=device)
        canvas = torch.tensor(bg_rgb, dtype=torch.float32, device=device)

        if np.any(non_leaf_m):
            m_nl = torch.tensor(model.cloud.means[non_leaf_m], dtype=torch.float32, device=device).contiguous()
            c6_nl = torch.tensor(model.cloud.cov6[non_leaf_m], dtype=torch.float32, device=device).contiguous()
            op_nl = torch.tensor(model.cloud.opacities[non_leaf_m, None], dtype=torch.float32, device=device).contiguous()
            z_nl = (m_nl @ R_w2c.T + t_w2c[None, :])[:, 2].clamp(0.1, 50.0)
            s_z = make_pinhole_settings(view.w2c, fx, fy, cx, cy, out_w, out_h, view.cam_center, device, bg_val=0.0, scale_modifier=1.05)
            z_aux = GaussianRasterizer(s_z)(
                means3D=m_nl, means2D=torch.zeros_like(m_nl),
                colors_precomp=torch.stack([torch.ones_like(z_nl), z_nl, z_nl], dim=-1),
                opacities=op_nl, cov3D_precomp=c6_nl,
            )[0]
            al_w = z_aux[0]
            z_wood = z_aux[1] / al_w.clamp(min=1e-4)
            z_buf = torch.where(al_w > 0.42, z_wood, z_buf)

        # Precompute pixel world ray directions D_world (out_h, out_w, 3)
        uu = torch.arange(out_w, dtype=torch.float32, device=device)
        vv = torch.arange(out_h, dtype=torch.float32, device=device)
        grid_v, grid_u = torch.meshgrid(vv, uu, indexing="ij")
        d_cam = torch.stack([(grid_u - float(cx)) / float(fx), (grid_v - float(cy)) / float(fy), torch.ones_like(grid_u)], dim=-1)
        d_world = d_cam @ R_c2w.T  # Note: d_cam[..., 2] == 1 so ray parameter t directly equals camera_z!!

        # Sort active leaves back-to-front (painter's algorithm with exact z-buffer occlusion test!)
        knots6 = clamped_cubic_knots(6)
        s_lut256 = np.linspace(0.0, 1.0, 256, dtype=np.float64)
        B_lut256 = BSpline(knots6, np.eye(6, dtype=np.float64), 3)(s_lut256)

        cand_leaves: list[tuple[float, DualArcTrimmedLeafPatch, tuple[int, int, int, int]]] = []
        for patch in model.leaves:
            if active_leaf_ids is not None and patch.leaf_id not in active_leaf_ids:
                continue
            pts_l, pts_r = patch.eval_3d_boundary_arcs(n_per_arc=16)
            b_pts = np.vstack([pts_l, pts_r])
            Xc = b_pts @ view.w2c[:3, :3].T + view.w2c[:3, 3]
            if np.all(Xc[:, 2] <= 0.2):
                continue
            zc = np.maximum(Xc[:, 2], 0.2)
            up = fx * (Xc[:, 0] / zc) + cx
            vp = fy * (Xc[:, 1] / zc) + cy
            c0 = max(0, int(math.floor(float(up.min()) - 4)))
            c1 = min(out_w, int(math.ceil(float(up.max()) + 5)))
            r0 = max(0, int(math.floor(float(vp.min()) - 4)))
            r1 = min(out_h, int(math.ceil(float(vp.max()) + 5)))
            if c1 <= c0 or r1 <= r0:
                continue
            cand_leaves.append((float(np.median(zc)), patch, (c0, r0, c1, r1)))

        # Sort back-to-front (largest z first) so closer leaves naturally paint over & update z_buf!
        cand_leaves.sort(key=lambda x: -x[0])

        for _, patch, (c0, r0, c1, r1) in cand_leaves:
            k_idx = patch.kernel_indices
            if len(k_idx) == 0:
                continue

            sub_d = d_world[r0:r1, c0:c1]  # (H_s, W_s, 3), camera_z = t_ray!
            p_b = torch.tensor(patch.p_base, dtype=torch.float32, device=device)
            e1 = torch.tensor(patch.e1, dtype=torch.float32, device=device)
            e2 = torch.tensor(patch.e2, dtype=torch.float32, device=device)
            e3 = torch.tensor(patch.e3, dtype=torch.float32, device=device)
            cam = patch.camber_coef

            # Ray-plane initial guess + 2 exact Newton steps on cambered surface w(u,v) = c0 + c1*u + c2*u^2 + c3*v^2
            denom = (sub_d * e3).sum(dim=-1)
            not_edge_on = torch.abs(denom) > 0.06
            if not torch.any(not_edge_on):
                continue

            safe_den = torch.where(not_edge_on, denom, torch.ones_like(denom))
            t_ray = float(((p_b - cam_o) * e3).sum().item()) / safe_den

            d_e1 = (sub_d * e1).sum(dim=-1)
            d_e2 = (sub_d * e2).sum(dim=-1)
            o_rel = cam_o - p_b
            o_e1 = float((o_rel * e1).sum().item())
            o_e2 = float((o_rel * e2).sum().item())
            o_e3 = float((o_rel * e3).sum().item())

            for _ in range(2):
                u_cur = o_e1 + t_ray * d_e1
                v_cur = o_e2 + t_ray * d_e2
                w_cur = o_e3 + t_ray * denom
                w_surf = float(cam[0]) + float(cam[1]) * u_cur + float(cam[2]) * (u_cur ** 2) + float(cam[3]) * (v_cur ** 2)
                f_val = w_cur - w_surf
                df_dt = denom - (float(cam[1]) + 2.0 * float(cam[2]) * u_cur) * d_e1 - (2.0 * float(cam[3]) * v_cur) * d_e2
                df_safe = torch.where(torch.abs(df_dt) > 0.05, df_dt, safe_den)
                t_ray = t_ray - f_val / df_safe

            u_hit = o_e1 + t_ray * d_e1
            v_hit = o_e2 + t_ray * d_e2
            L_b = float(patch.blade_length)
            s_hit = u_hit / L_b

            # Lookup exact Dual-Arc Cubic B-Spline widths v_left(s) and v_right(s)
            vl_lut = torch.tensor(B_lut256 @ patch.v_left_ctrl, dtype=torch.float32, device=device)
            vr_lut = torch.tensor(B_lut256 @ patch.v_right_ctrl, dtype=torch.float32, device=device)
            s_clamped = s_hit.clamp(0.0, 1.0) * 255.0
            i0 = s_clamped.long().clamp(0, 254)
            frac = s_clamped - i0.float()
            vl_s = (1.0 - frac) * vl_lut[i0] + frac * vl_lut[i0 + 1]
            vr_s = (1.0 - frac) * vr_lut[i0] + frac * vr_lut[i0 + 1]

            # Exact signed interior margin distance (m) -> screen pixels!
            # Near sharp tips (s->0 or s->1), width tapers smoothly to 0 so min(v - vr, vl - v) naturally forms the sharp C0 cusp!
            d_lat = torch.minimum(v_hit - vr_s, vl_s - v_hit)
            d_lon = torch.minimum(u_hit, L_b - u_hit)
            d_in_m = torch.minimum(d_lat, d_lon)
            d_px = d_in_m * (float(fx) / t_ray.clamp(min=0.2))

            valid_hit = not_edge_on & (t_ray > 0.2) & (d_px > -0.75) & (t_ray <= z_buf[r0:r1, c0:c1] + 0.0025)
            if not torch.any(valid_hit):
                continue

            # Analytical 0.7-pixel sub-pixel anti-aliased spline coverage!
            cov_alpha = torch.clamp(0.5 + d_px / 1.15, 0.0, 1.0) * valid_hit.float()

            # Smooth Partition-of-Unity Gaussian Radiance Interpolation over Leaf `l`'s Kernels!
            # Evaluates exact Nadaraya-Watson weighted color in (u, v) leaf plane so interior is 100% crack-free at any zoom!
            k_pts = torch.tensor(model.cloud.means[k_idx], dtype=torch.float32, device=device)
            k_rel = k_pts - p_b[None, :]
            ku = (k_rel * e1[None, :]).sum(dim=-1)
            kv = (k_rel * e2[None, :]).sum(dim=-1)
            k_op = torch.tensor(model.cloud.opacities[k_idx], dtype=torch.float32, device=device)
            k_col = torch.tensor(rgb_src[k_idx], dtype=torch.float32, device=device)
            sig_uv = max(float(np.median(model.cloud.scales[k_idx].max(axis=1))) * 1.15, 0.0042)

            hit_rc = torch.where(cov_alpha > 1e-3)
            uh_v = u_hit[hit_rc]  # (P,)
            vh_v = v_hit[hit_rc]  # (P,)

            # Chunked evaluation if P * K is large
            p_cnt = len(uh_v)
            col_interp = torch.zeros((p_cnt, 3), dtype=torch.float32, device=device)
            chunk = 4096
            inv_2s2 = 0.5 / (sig_uv * sig_uv)
            for p0 in range(0, p_cnt, chunk):
                p1 = min(p_cnt, p0 + chunk)
                du2 = (uh_v[p0:p1, None] - ku[None, :]) ** 2 + (vh_v[p0:p1, None] - kv[None, :]) ** 2
                wts = torch.exp((-du2 * inv_2s2).clamp(min=-25.0)) * k_op[None, :]
                w_sum = wts.sum(dim=1, keepdim=True).clamp(min=1e-6)
                col_interp[p0:p1] = (wts @ k_col) / w_sum

            if draw_vector_ink_rims:
                # Crisp 1.1-px analytical vector ink stroke right along the Dual-Arc Cubic B-Spline boundary!
                d_px_v = d_px[hit_rc]
                ink_w = torch.clamp(1.0 - torch.abs(d_px_v - 0.55) / 0.85, 0.0, 1.0)[:, None] * 0.78
                ink_c = torch.tensor([[0.10, 0.12, 0.10]], dtype=torch.float32, device=device)
                col_interp = (1.0 - ink_w) * col_interp + ink_w * ink_c

            a_v = cov_alpha[hit_rc][:, None]
            sub_can = canvas[r0:r1, c0:c1]
            sub_can[hit_rc] = (1.0 - a_v) * sub_can[hit_rc] + a_v * col_interp
            canvas[r0:r1, c0:c1] = sub_can

            # Update depth buffer where coverage is solid (>= 0.55)
            solid = cov_alpha >= 0.55
            sub_z = z_buf[r0:r1, c0:c1]
            z_buf[r0:r1, c0:c1] = torch.where(solid & (t_ray < sub_z), t_ray, sub_z)

        torch.cuda.synchronize(device)
        return np.ascontiguousarray(canvas.clamp(0.0, 1.0).cpu().numpy(), dtype=np.float32)


def draw_hybrid_skeleton_and_splines_wireframe(
    model: HybridBotanicalPrimitive,
    view: CalibratedSceneView,
    active_branch_ids: set[int] | None = None,
    active_leaf_ids: set[int] | None = None,
    roi_box: tuple[int, int, int, int] | None = None,
    out_size: tuple[int, int] = (800, 800),
) -> np.ndarray:
    """Render clean vector CAD diagram of Layer-1 Lathe + Layer-2 4-Level Branch Tree + Layer-3 Dual-Arc Leaf Splines."""
    out_w, out_h = out_size
    fx, fy, cx, cy = zoomed_camera_intrinsics(view, roi_box, out_w, out_h)
    canvas = np.full((out_h, out_w, 3), 252, dtype=np.uint8)
    R = view.w2c[:3, :3]
    t = view.w2c[:3, 3]

    def _proj(pts3d: np.ndarray) -> tuple[np.ndarray, bool]:
        Xc = pts3d @ R.T + t[None, :]
        if np.any(Xc[:, 2] <= 0.2):
            return np.zeros((0, 1, 2), dtype=np.int32), False
        us = np.round(fx * (Xc[:, 0] / Xc[:, 2]) + cx).astype(np.int32)
        vs = np.round(fy * (Xc[:, 1] / Xc[:, 2]) + cy).astype(np.int32)
        return np.column_stack([us, vs]).reshape(-1, 1, 2), True

    # 1. Draw Lathe Pot rings
    o_p = model.pot_base.axis_origin
    a_p = model.pot_base.axis_dir
    e1_p = np.array([1.0, 0.0, 0.0]) - a_p[0] * a_p
    e1_p /= max(float(np.linalg.norm(e1_p)), 1e-8)
    e2_p = np.cross(a_p, e1_p)
    th = np.linspace(0.0, 2.0 * math.pi, 48)
    for hk, rk in zip(model.pot_base.profile_h[::3], model.pot_base.profile_r[::3]):
        ring = o_p[None, :] + hk * a_p[None, :] + rk * (np.cos(th)[:, None] * e1_p + np.sin(th)[:, None] * e2_p)
        poly, ok = _proj(ring)
        if ok:
            cv2.polylines(canvas, [poly], isClosed=True, color=(120, 115, 110), thickness=1, lineType=cv2.LINE_AA)

    # 2. Draw 4-Level Parametric B-Spline Branching Tree (color-coded by botanical hierarchy level!)
    lvl_colors = {
        0: (95, 55, 25),    # Primary Trunks: deep walnut brown (thick)
        1: (155, 85, 30),   # Secondary Branches: warm sienna
        2: (195, 130, 35),  # Rosette Stalks: golden ochre
        3: (95, 155, 65),   # Petiole Links: olive petiole green
    }
    lvl_thick = {0: 3, 1: 2, 2: 1, 3: 1}
    u_sp = np.linspace(0.0, 1.0, 20)
    for br in model.skeleton.branches:
        if active_branch_ids is not None and br.branch_id not in active_branch_ids:
            continue
        pts_b, _ = eval_clamped_bspline(br.ctrl_points, u_sp)
        poly, ok = _proj(pts_b)
        if ok:
            cv2.polylines(
                canvas, [poly], isClosed=False, color=lvl_colors.get(br.level, (80, 80, 80)),
                thickness=lvl_thick.get(br.level, 1), lineType=cv2.LINE_AA,
            )

    # 3. Draw Closed Dual-Arc Pointed-Tip Cubic B-Splines + Midrib Spine per Leaf!
    for patch in model.leaves:
        if active_leaf_ids is not None and patch.leaf_id not in active_leaf_ids:
            continue
        pts_l, pts_r = patch.eval_3d_boundary_arcs(n_per_arc=20)
        col_l = (20, 145, 75) if patch.visibility_tier == "OUTER_ENCLOSED" else (45, 120, 185)
        p_l, ok1 = _proj(pts_l)
        p_r, ok2 = _proj(pts_r)
        if ok1 and ok2:
            cv2.polylines(canvas, [p_l], isClosed=False, color=col_l, thickness=1, lineType=cv2.LINE_AA)
            cv2.polylines(canvas, [p_r], isClosed=False, color=col_l, thickness=1, lineType=cv2.LINE_AA)
    return canvas
