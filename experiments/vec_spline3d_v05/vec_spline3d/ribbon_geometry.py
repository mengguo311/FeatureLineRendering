"""Oriented Darboux ribbon geometry (RIBBON_3D) & physical edge semantics from 3DGS surfels + multi-view steps."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from plyfile import PlyData
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from scipy.special import expit

from .multimodal_data import MultiModalSceneBundle
from .schema import CurveNetwork3D, RibbonGeometry, resolve_safe_path
from .stage1_ray_clean import GPUViewFieldEvaluator


class SurfaceRibbonEstimator:
    """Extracts oriented 3DGS surfel normals, two-sided dihedral angles, and silhouette/albedo edge classes."""

    def __init__(
        self,
        bundle: MultiModalSceneBundle,
        evaluator: GPUViewFieldEvaluator,
        device: torch.device,
        surface_ply_path: str | Path | None = None,
    ) -> None:
        self.bundle = bundle
        self.evaluator = evaluator
        self.device = device
        self.p_med = bundle.median_pixel_scale

        self.surfel_pts: np.ndarray | None = None
        self.surfel_normals: np.ndarray | None = None
        self.surfel_tree: cKDTree | None = None
        self.cams_t = torch.tensor(
            np.stack([v.cam_center for v in bundle.train_views], axis=0), dtype=torch.float32, device=device
        )

        eff_ply = Path(surface_ply_path) if surface_ply_path is not None else bundle.surface_ply_path
        if eff_ply is not None and eff_ply.exists():
            ply_safe = resolve_safe_path(eff_ply)
            vdata = PlyData.read(ply_safe)["vertex"].data
            xyz = np.stack([vdata["x"], vdata["y"], vdata["z"]], axis=-1).astype(np.float64)
            opac = expit(np.clip(vdata["opacity"].astype(np.float64), -40.0, 40.0))
            keep = opac > 0.15
            xyz = xyz[keep]
            sc = np.exp(np.stack([vdata["scale_0"][keep], vdata["scale_1"][keep], vdata["scale_2"][keep]], axis=-1))
            quat = np.stack(
                [vdata["rot_0"][keep], vdata["rot_1"][keep], vdata["rot_2"][keep], vdata["rot_3"][keep]], axis=-1
            ).astype(np.float64)
            quat /= np.maximum(np.linalg.norm(quat, axis=1, keepdims=True), 1e-12)
            R_mat = Rotation.from_quat(quat[:, [1, 2, 3, 0]]).as_matrix()
            min_ax = np.argmin(sc, axis=1)
            normals = R_mat[np.arange(len(xyz)), :, min_ax]

            # Orient surfel normals outward toward visible training cameras on GPU
            normals = self._orient_surfel_normals_outward(xyz, normals)
            self.surfel_pts = xyz
            self.surfel_normals = normals
            self.surfel_tree = cKDTree(xyz)

        # Pack RGB maps of training views (V, 3, H, W) on GPU for fast two-sided photometric contrast queries
        rgb_list = []
        has_rgb = []
        for vw in bundle.train_views:
            if vw.rgb is not None:
                rgb_list.append(vw.rgb.transpose(2, 0, 1))
                has_rgb.append(True)
            else:
                rgb_list.append(np.zeros((3, evaluator.h, evaluator.w), dtype=np.float32))
                has_rgb.append(False)
        self.rgb_maps = torch.tensor(np.stack(rgb_list, axis=0), dtype=torch.float32, device=device)
        self.has_rgb = torch.tensor(has_rgb, dtype=torch.bool, device=device)

    @torch.no_grad()
    def _orient_surfel_normals_outward(self, xyz: np.ndarray, normals: np.ndarray) -> np.ndarray:
        out_n = normals.copy()
        ev = self.evaluator
        chunk = 24000
        for s in range(0, len(xyz), chunk):
            e = min(len(xyz), s + chunk)
            X_t = torch.tensor(xyz[s:e], dtype=torch.float32, device=self.device)
            Xc = torch.einsum("vij,nj->vni", ev.R, X_t) + ev.t[:, None, :]
            z = Xc[:, :, 2].clamp(min=1e-3)
            u = ev.fx[:, None] * (Xc[:, :, 0] / z) + ev.cx[:, None]
            v = ev.fy[:, None] * (Xc[:, :, 1] / z) + ev.cy[:, None]
            in_f = (Xc[:, :, 2] > 0.2) & (u >= 0.0) & (u <= ev.w - 1.0) & (v >= 0.0) & (v <= ev.h - 1.0)
            gx = 2.0 * (u / (ev.w - 1.0)) - 1.0
            gy = 2.0 * (v / (ev.h - 1.0)) - 1.0
            grid = torch.stack([gx, gy], dim=-1).unsqueeze(2)
            smp_d = F.grid_sample(
                ev.maps[:, 4:5, :, :], grid, mode="nearest", padding_mode="border", align_corners=True
            ).squeeze(-1)
            vis = in_f & ((~ev.has_depth[:, None]) | (z <= smp_d[:, 0, :] + 5.0 * self.p_med))
            v_dirs = F.normalize(self.cams_t[:, None, :] - X_t[None, :, :], dim=-1, eps=1e-8)
            mean_v = (v_dirs * vis.unsqueeze(-1).float()).sum(dim=0).cpu().numpy()
            dots = np.sum(out_n[s:e] * mean_v, axis=1)
            flip = dots < 0.0
            out_n[s:e][flip] *= -1.0
        return out_n

    def _estimate_control_normals_and_dihedral(
        self, ctrl_pts: np.ndarray, sample_pts: np.ndarray, sample_tangs: np.ndarray
    ) -> tuple[np.ndarray, float]:
        """Estimate smooth outward normals at control points and two-sided 3D surfel dihedral angle along the curve."""
        m = len(ctrl_pts)
        if self.surfel_tree is None or self.surfel_normals is None or self.surfel_pts is None:
            fallback = np.tile(np.array([[0.0, 0.0, 1.0]], dtype=np.float64), (m, 1))
            return fallback, 0.0

        dists_c, idxs_c = self.surfel_tree.query(ctrl_pts, k=12, distance_upper_bound=6.0 * self.p_med)
        ctrl_nrms = np.zeros((m, 3), dtype=np.float64)
        for i in range(m):
            ok = np.isfinite(dists_c[i]) & (idxs_c[i] < len(self.surfel_pts))
            if np.any(ok):
                nb_n = self.surfel_normals[idxs_c[i][ok]]
                w = np.exp(-0.5 * (dists_c[i][ok] / (2.2 * self.p_med)) ** 2)[:, None]
                # Align signs to dominant normal before averaging
                ref = nb_n[0]
                aligned = np.where((nb_n @ ref)[:, None] >= 0.0, nb_n, -nb_n)
                avg = (w * aligned).sum(axis=0)
                # Ensure outward consistency with majority of raw oriented normals
                if float(np.dot(avg, (w * nb_n).sum(axis=0))) < 0.0:
                    avg = -avg
                ln = float(np.linalg.norm(avg))
                ctrl_nrms[i] = avg / ln if ln > 1e-8 else np.array([0.0, 0.0, 1.0])
            else:
                ctrl_nrms[i] = np.array([0.0, 0.0, 1.0])

        # Enforce consistent normal propagation along control polygon
        for i in range(1, m):
            if float(np.dot(ctrl_nrms[i], ctrl_nrms[i - 1])) < -0.2:
                ctrl_nrms[i] = -ctrl_nrms[i]

        # Measure two-sided 3D dihedral angle across the binormal plane at interior sample points
        dists_s, idxs_s = self.surfel_tree.query(sample_pts, k=16, distance_upper_bound=5.0 * self.p_med)
        dihedrals: list[float] = []
        mean_n = ctrl_nrms.mean(axis=0)
        mean_n /= max(float(np.linalg.norm(mean_n)), 1e-9)

        for s_i in range(len(sample_pts)):
            ok = np.isfinite(dists_s[s_i]) & (idxs_s[s_i] < len(self.surfel_pts))
            if int(ok.sum()) < 6:
                continue
            nb_pts = self.surfel_pts[idxs_s[s_i][ok]]
            nb_nrm = self.surfel_normals[idxs_s[s_i][ok]]
            b_dir = np.cross(mean_n, sample_tangs[s_i])
            bn = float(np.linalg.norm(b_dir))
            if bn < 1e-6:
                continue
            b_dir /= bn
            side = (nb_pts - sample_pts[s_i][None, :]) @ b_dir
            pos_m = side > 0.4 * self.p_med
            neg_m = side < -0.4 * self.p_med
            if int(pos_m.sum()) >= 2 and int(neg_m.sum()) >= 2:
                n_pos = nb_nrm[pos_m].mean(axis=0)
                n_neg = nb_nrm[neg_m].mean(axis=0)
                lp, ln = float(np.linalg.norm(n_pos)), float(np.linalg.norm(n_neg))
                if lp > 1e-6 and ln > 1e-6:
                    cos_d = float(np.clip(np.dot(n_pos / lp, n_neg / ln), -1.0, 1.0))
                    dihedrals.append(math.degrees(math.acos(cos_d)))

        dihedral_deg = float(np.percentile(dihedrals, 75.0)) if dihedrals else 0.0
        return ctrl_nrms, dihedral_deg

    @torch.no_grad()
    def annotate_network_ribbons(self, net: CurveNetwork3D) -> dict[str, Any]:
        """Compute Darboux ribbon geometry, stroke widths, inward silhouette offsets, and edge classes for all curves."""
        if not net.curves:
            return {"annotated_curves": 0}

        cids = sorted(net.curves.keys())
        S = 9
        sample_pts_all: list[np.ndarray] = []
        sample_tng_all: list[np.ndarray] = []
        ctrl_nrm_map: dict[int, np.ndarray] = {}
        dihedral_map: dict[int, float] = {}

        for cid in cids:
            c = net.curves[cid]
            _, pts, d1, _ = c.evaluate(num_samples=S)
            d1_n = np.linalg.norm(d1, axis=1, keepdims=True)
            tng = np.where(d1_n > 1e-12, d1 / np.maximum(d1_n, 1e-12), np.array([1.0, 0.0, 0.0]))
            sample_pts_all.append(pts)
            sample_tng_all.append(tng)

            if c.ribbon is not None and c.role == "COAXIAL_RING":
                ctrl_nrm_map[cid] = c.ribbon.control_normals
                dihedral_map[cid] = c.ribbon.dihedral_deg
            else:
                cn, dih = self._estimate_control_normals_and_dihedral(c.control_points, pts, tng)
                ctrl_nrm_map[cid] = cn
                dihedral_map[cid] = dih

        pts_cat = np.concatenate(sample_pts_all, axis=0)
        tng_cat = np.concatenate(sample_tng_all, axis=0)

        # Batched GPU query of two-sided cross-edge silhouette, depth jump, albedo contrast, and stroke width!
        ev = self.evaluator
        N_tot = len(pts_cat)
        sil_frac_arr = np.zeros(N_tot, dtype=np.float32)
        djump_arr = np.zeros(N_tot, dtype=np.float32)
        albedo_arr = np.zeros(N_tot, dtype=np.float32)
        width_arr = np.full(N_tot, 0.40, dtype=np.float32)

        chunk = 14000
        for s in range(0, N_tot, chunk):
            e = min(N_tot, s + chunk)
            X_t = torch.tensor(pts_cat[s:e], dtype=torch.float32, device=self.device)
            T_t = torch.tensor(tng_cat[s:e], dtype=torch.float32, device=self.device)

            Xc = torch.einsum("vij,nj->vni", ev.R, X_t) + ev.t[:, None, :]
            z = Xc[:, :, 2].clamp(min=1e-3)
            u = ev.fx[:, None] * (Xc[:, :, 0] / z) + ev.cx[:, None]
            v = ev.fy[:, None] * (Xc[:, :, 1] / z) + ev.cy[:, None]

            Tc = torch.einsum("vij,nj->vni", ev.R, T_t)
            du = ev.fx[:, None] * (Tc[:, :, 0] / z - Xc[:, :, 0] * Tc[:, :, 2] / (z * z))
            dv = ev.fy[:, None] * (Tc[:, :, 1] / z - Xc[:, :, 1] * Tc[:, :, 2] / (z * z))
            t2d = F.normalize(torch.stack([du, dv], dim=-1), dim=-1, eps=1e-6)
            n2d_u = -t2d[:, :, 1]
            n2d_v = t2d[:, :, 0]

            def to_grid(uu: torch.Tensor, vv: torch.Tensor) -> torch.Tensor:
                gx = 2.0 * (uu / (ev.w - 1.0)) - 1.0
                gy = 2.0 * (vv / (ev.h - 1.0)) - 1.0
                return torch.stack([gx, gy], dim=-1).unsqueeze(2)

            g0 = to_grid(u, v)
            gp = to_grid(u + 2.2 * n2d_u, v + 2.2 * n2d_v)
            gm = to_grid(u - 2.2 * n2d_u, v - 2.2 * n2d_v)
            gp1 = to_grid(u + 1.2 * n2d_u, v + 1.2 * n2d_v)
            gm1 = to_grid(u - 1.2 * n2d_u, v - 1.2 * n2d_v)

            s0 = F.grid_sample(ev.maps[:, [0, 3, 4], :, :], g0, mode="bilinear", padding_mode="border", align_corners=True).squeeze(-1)
            sp = F.grid_sample(ev.maps[:, [0, 3, 4], :, :], gp, mode="nearest", padding_mode="border", align_corners=True).squeeze(-1)
            sm = F.grid_sample(ev.maps[:, [0, 3, 4], :, :], gm, mode="nearest", padding_mode="border", align_corners=True).squeeze(-1)
            sp1 = F.grid_sample(ev.maps[:, 3:4, :, :], gp1, mode="bilinear", padding_mode="border", align_corners=True).squeeze(-1)
            sm1 = F.grid_sample(ev.maps[:, 3:4, :, :], gm1, mode="bilinear", padding_mode="border", align_corners=True).squeeze(-1)

            in_f = (Xc[:, :, 2] > 0.2) & (u >= 3.0) & (u <= ev.w - 4.0) & (v >= 3.0) & (v <= ev.h - 4.0)
            vis = in_f & ((~ev.has_depth[:, None]) | (s0[:, 0, :] < 0.95) | (z <= s0[:, 2, :] + 5.5 * self.p_med))
            vis_f = vis.float()
            v_denom = vis_f.sum(dim=0).clamp(min=1.0)

            # Silhouette / occlusion jump across +- 2.2 px
            alpha_drop = torch.minimum(sp[:, 0, :], sm[:, 0, :]) < 0.28
            both_fg = ev.has_depth[:, None] & (sp[:, 0, :] > 0.75) & (sm[:, 0, :] > 0.75) & (sp[:, 2, :] > 0.2) & (sm[:, 2, :] > 0.2)
            rel_dz = torch.where(both_fg, torch.abs(sp[:, 2, :] - sm[:, 2, :]) / z, torch.zeros_like(z))
            is_sil = vis & (alpha_drop | (rel_dz > 0.018))
            sil_frac_arr[s:e] = (is_sil.float().sum(dim=0) / v_denom).cpu().numpy()
            djump_arr[s:e] = ((rel_dz * vis_f).sum(dim=0) / v_denom).cpu().numpy()

            # Two-sided RGB contrast on continuous foreground views
            rgb_p = F.grid_sample(self.rgb_maps, gp, mode="bilinear", padding_mode="border", align_corners=True).squeeze(-1)
            rgb_m = F.grid_sample(self.rgb_maps, gm, mode="bilinear", padding_mode="border", align_corners=True).squeeze(-1)
            c_diff = torch.linalg.norm(rgb_p - rgb_m, dim=1)
            rgb_vis = (vis & self.has_rgb[:, None] & (~alpha_drop)).float()
            albedo_arr[s:e] = ((c_diff * rgb_vis).sum(dim=0) / rgb_vis.sum(dim=0).clamp(min=1.0)).cpu().numpy()

            # Multi-view stroke profile width from darkness decay at +- 1.2 px vs center
            e_center = s0[:, 1, :].clamp(min=1e-3)
            e_side = 0.5 * (sp1[:, 0, :] + sm1[:, 0, :])
            ratio_w = (e_side / e_center).clamp(0.0, 1.2)
            est_w = 0.34 + 0.16 * ((ratio_w * vis_f).sum(dim=0) / v_denom)
            width_arr[s:e] = est_w.clamp(0.34, 0.50).cpu().numpy()

        # Assign RibbonGeometry to all curves and calibrate exact inward_sign for SILHOUETTE_CONTOUR curves
        sil_cids: list[int] = []
        sil_plus_pts: list[np.ndarray] = []
        sil_minus_pts: list[np.ndarray] = []

        for idx, cid in enumerate(cids):
            c = net.curves[cid]
            sl = slice(idx * S, (idx + 1) * S)
            sil_score = float(np.median(sil_frac_arr[sl]))
            dj_val = float(np.median(djump_arr[sl]))
            alb_val = float(np.median(albedo_arr[sl]))
            hw_px = float(np.median(width_arr[sl]))
            dih_deg = dihedral_map[cid]

            if c.role == "COAXIAL_RING" and c.ribbon is not None:
                c.ribbon.half_width_px = float(np.clip(hw_px, 0.36, 0.46))
                c.ribbon.albedo_contrast = max(c.ribbon.albedo_contrast, alb_val)
                continue

            if c.role == "BRIDGE":
                edge_cls = "TOPOLOGY_BRIDGE"
            elif sil_score >= 0.32 or dj_val >= 0.018 or c.role == "SILHOUETTE_DEPTH_JUMP":
                edge_cls = "SILHOUETTE_CONTOUR"
            elif dih_deg >= 26.0:
                edge_cls = "DIHEDRAL_CREASE"
            else:
                edge_cls = "SURFACE_STRIPE"

            c.ribbon = RibbonGeometry(
                edge_class=edge_cls,
                control_normals=ctrl_nrm_map[cid],
                half_width_px=hw_px,
                thickness_px=round(0.65 * hw_px, 4),
                inward_shift_px=0.24 if edge_cls == "SILHOUETTE_CONTOUR" else 0.0,
                inward_sign=1.0,
                dihedral_deg=dih_deg,
                depth_jump_rel=dj_val,
                albedo_contrast=alb_val,
            )
            c.width_px = hw_px

            if edge_cls == "SILHOUETTE_CONTOUR":
                _, pts_f, _, B_f, _ = c.evaluate_darboux_frame(num_samples=5)
                mid_p = pts_f[2]
                mid_b = B_f[2]
                step_in = 1.6 * c.pixel_scale
                sil_cids.append(cid)
                sil_plus_pts.append(mid_p + step_in * mid_b)
                sil_minus_pts.append(mid_p - step_in * mid_b)

        if sil_cids:
            q_plus = ev.query_points(np.stack(sil_plus_pts, axis=0), pixel_scale=self.p_med)
            q_minus = ev.query_points(np.stack(sil_minus_pts, axis=0), pixel_scale=self.p_med)
            for k_i, cid in enumerate(sil_cids):
                rib = net.curves[cid].ribbon
                assert rib is not None
                cost_p = float(q_plus["outside_dt_mean"][k_i]) + 20.0 * float(q_plus["hull_viol_rate"][k_i])
                cost_m = float(q_minus["outside_dt_mean"][k_i]) + 20.0 * float(q_minus["hull_viol_rate"][k_i])
                if abs(cost_p - cost_m) < 0.05:
                    # Interior stem/leaf overlap where both sides lie inside visual hull: no asymmetric shift needed
                    rib.inward_shift_px = 0.0
                else:
                    rib.inward_sign = 1.0 if cost_p < cost_m else -1.0

        counts: dict[str, int] = {}
        for c in net.curves.values():
            if c.ribbon is not None:
                counts[c.ribbon.edge_class] = counts.get(c.ribbon.edge_class, 0) + 1
        return {
            "annotated_ribbon_curves": len(net.curves),
            "edge_class_breakdown": counts,
            "mean_ribbon_half_width_px": round(
                float(np.mean([c.ribbon.half_width_px for c in net.curves.values() if c.ribbon is not None])), 4
            ),
            "mean_dihedral_crease_deg": round(
                float(
                    np.mean([
                        c.ribbon.dihedral_deg
                        for c in net.curves.values()
                        if c.ribbon is not None and c.ribbon.edge_class == "DIHEDRAL_CREASE"
                    ] or [0.0])
                ),
                2,
            ),
        }
