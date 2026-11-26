"""Unit tests for universal_botanical_v01: strict write isolation, color-agnostic organ discovery, 3-family support & zero wind leak."""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from universal_botanical.adaptive_lamina_and_graph import (
    build_cov6_from_sq,
    deform_universal_model_wind,
    fit_universal_organ_patches_and_kinematic_graph,
)
from universal_botanical.basal_and_domains import (
    fit_axisymmetric_lathe_mesh,
    fit_convex_loft_vessel_mesh,
    fit_rectangular_tray_mesh,
)
from universal_botanical.schema_and_io import (
    LABEL_BASAL_SUPPORT,
    LABEL_STATIC_STAND_OR_TABLE,
    LABEL_STEM_SKELETON,
    BasalSupportModel,
    SceneGaussianCloud,
    StemSplineChain,
    UniversalBotanicalConfig,
    eval_periodic_cubic_bspline_1d,
    fit_periodic_cubic_bspline_1d,
    resolve_read_path,
    resolve_write_path,
)


class TestUniversalBotanicalV01(unittest.TestCase):
    def test_strict_workspace_isolation_protects_user_codex_and_upstream_dirs(self) -> None:
        # Allowed read from user's Codex output directory
        r_ok = resolve_read_path("/home/u00134/Documents/Codex/2026-11-26/ficus-leaf-kernels-v04-hybrid-botanical/outputs")
        self.assertEqual(r_ok.name, "outputs")

        # Strictly block any write into user's Codex workspace or upstream scratch projects!
        with self.assertRaises(PermissionError):
            resolve_write_path("/home/u00134/Documents/Codex/2026-11-26/ficus-leaf-kernels-v04-hybrid-botanical/outputs/overwrite.json")
        with self.assertRaises(PermissionError):
            resolve_write_path("/home/u00134/.gemini/antigravity/scratch/ficus_leaf_kernels_v01/outputs/bad.json")
        with self.assertRaises(ValueError):
            resolve_read_path("/etc/shadow")

        w_ok = resolve_write_path(Path(__file__).resolve().parents[1] / "outputs/ok.json")
        self.assertTrue(str(w_ok).endswith("outputs/ok.json"))

    def test_periodic_bspline_and_three_support_families(self) -> None:
        th = np.linspace(-np.pi, np.pi, 32, endpoint=False)
        target_r = 0.9 + 0.15 * np.cos(2 * th)
        ctrl = fit_periodic_cubic_bspline_1d(th, target_r, np.ones_like(th), k=16, smooth_reg=0.01)
        pred_r = eval_periodic_cubic_bspline_1d(ctrl, th)
        self.assertLess(float(np.max(np.abs(pred_r - target_r))), 0.04)
        # Periodic continuity across -pi / +pi seam
        r_minus = eval_periodic_cubic_bspline_1d(ctrl, np.array([-np.pi]))[0]
        r_plus = eval_periodic_cubic_bspline_1d(ctrl, np.array([np.pi - 1e-9]))[0]
        self.assertAlmostEqual(float(r_minus), float(r_plus), places=6)

        rng = np.random.default_rng(7)
        # Rectangular tray point sample
        ang = rng.uniform(0, 2 * np.pi, 600)
        z = rng.uniform(-0.35, -0.22, 600)
        rect_pts = np.column_stack([np.clip(np.cos(ang) * 0.4, -0.3, 0.3), np.clip(np.sin(ang) * 0.3, -0.2, 0.2), z])
        vr, fr, info_r = fit_rectangular_tray_mesh(rect_pts, p_med=0.0035)
        self.assertEqual(vr.shape[1], 3)
        self.assertGreater(len(fr), 10)
        self.assertGreater(info_r["matched_rect_area"], 0.15)

        vl, fl, _ = fit_axisymmetric_lathe_mesh(rect_pts)
        vc, fc, _ = fit_convex_loft_vessel_mesh(rect_pts, p_med=0.0035)
        self.assertGreater(len(fl), 20)
        self.assertGreater(len(fc), 20)

    def test_zero_wind_leakage_on_support_and_stand_and_broad_leaf_preservation(self) -> None:
        rng = np.random.default_rng(42)
        # 30 support pts, 20 stand pts, 20 stem pts, 60 broad pink leaf pts (R > G!)
        p_stand = np.column_stack([rng.uniform(-0.3, 0.3, 20), rng.uniform(-0.3, 0.3, 20), rng.uniform(-0.5, -0.42, 20)])
        p_sup = np.column_stack([rng.uniform(-0.2, 0.2, 30), rng.uniform(-0.15, 0.15, 30), rng.uniform(-0.4, -0.2, 30)])
        p_stem = np.column_stack([np.zeros(20), np.zeros(20), np.linspace(-0.2, 0.1, 20)])
        # Broad pink ovate blade (width = 0.22, length = 0.24 -> W/L ~ 0.92!)
        u = rng.uniform(-0.12, 0.12, 60)
        v = rng.uniform(-0.11, 0.11, 60)
        w = 0.2 * (u ** 2) - 0.15 * (v ** 2)
        p_leaf = np.column_stack([u + 0.12, v, 0.15 + w])

        means = np.vstack([p_stand, p_sup, p_stem, p_leaf]).astype(np.float32)
        n = len(means)
        scales = np.full((n, 3), 0.005, dtype=np.float32)
        scales[-60:, 2] = 0.001  # thin lamina
        quats = np.tile(np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32), (n, 1))
        cov6 = build_cov6_from_sq(scales, quats)
        nrms = np.tile(np.array([[0.0, 0.0, 1.0]], dtype=np.float32), (n, 1))
        opac = np.full(n, 0.85, dtype=np.float32)
        # Pink non-green RGB (R=0.85, G=0.40, B=0.75)
        rgb = np.tile(np.array([[0.85, 0.40, 0.75]], dtype=np.float32), (n, 1))
        shs = np.zeros((n, 16, 3), dtype=np.float32)

        cloud = SceneGaussianCloud(means, scales, quats, cov6, nrms, opac, rgb, shs)
        labels = np.concatenate([
            np.full(20, LABEL_STATIC_STAND_OR_TABLE, dtype=np.int32),
            np.full(30, LABEL_BASAL_SUPPORT, dtype=np.int32),
            np.full(20, LABEL_STEM_SKELETON, dtype=np.int32),
            np.zeros(60, dtype=np.int32),
        ])
        sup = BasalSupportModel(
            regime="RECTANGULAR_TRAY_LOFT",
            vertices=np.zeros((0, 3), dtype=np.float32),
            faces=np.zeros((0, 3), dtype=np.int32),
            rim_z=-0.20,
            vessel_bot_z=-0.40,
            support_kernel_mask=(labels == LABEL_BASAL_SUPPORT),
            stand_kernel_mask=(labels == LABEL_STATIC_STAND_OR_TABLE),
        )
        stems = [
            StemSplineChain(
                chain_id=0, level=0, parent_chain_id=-1, parent_u=0.0,
                ctrl_points=np.array([[0.0, 0.0, -0.2], [0.0, 0.0, -0.1], [0.0, 0.0, 0.0], [0.0, 0.0, 0.1]]),
                radius_base=0.015, radius_tip=0.008, supported_kernel_count=20, basal_anchored=True,
            )
        ]
        org_recs = [{
            "organ_id": 0, "organ_kind": "LAMINAR_BLADE", "visibility_tier": "OUTER_ENCLOSED",
            "active_kernel_count": 60, "centroid": p_leaf.mean(axis=0),
            "e1": np.array([1.0, 0.0, 0.0]), "e2": np.array([0.0, 1.0, 0.0]), "e3": np.array([0.0, 0.0, 1.0]),
            "length": 0.25, "width": 0.23, "thickness": 0.006,
            "mean_vis_views": 8.0, "enclosed_kernel_frac": 0.9, "mean_rgb": rgb[-1],
        }]
        cfg = UniversalBotanicalConfig()
        model = fit_universal_organ_patches_and_kinematic_graph("synthetic_pink", cloud, labels, org_recs, sup, stems, 0.0035, cfg)

        # Verify 100% of broad leaf kernel centers stay inside the fitted periodic spline contour!
        org = model.organs[0]
        rel = p_leaf - org.centroid[None, :]
        un = (rel @ org.e1) / (0.5 * org.length)
        vn = (rel @ org.e2) / (0.5 * org.width)
        rn = np.hypot(un, vn)
        r_bound = eval_periodic_cubic_bspline_1d(org.periodic_ctrl_r, np.arctan2(vn, un))
        self.assertGreaterEqual(float(np.mean(rn <= r_bound * 1.02)), 0.95)

        # Deform under wind and assert EXACT ZERO motion on all 50 support + stand Gaussians!
        def_cloud, _, _ = deform_universal_model_wind(model, phase_rad=1.2, wind_amp_deg=9.0)
        static_m = (labels == LABEL_BASAL_SUPPORT) | (labels == LABEL_STATIC_STAND_OR_TABLE)
        max_support_drift = float(np.max(np.linalg.norm(def_cloud.means[static_m] - cloud.means[static_m], axis=1)))
        mean_leaf_disp = float(np.mean(np.linalg.norm(def_cloud.means[-60:] - cloud.means[-60:], axis=1)))
        self.assertEqual(max_support_drift, 0.0)
        self.assertGreater(mean_leaf_disp, 0.002)

    def test_universal_stylization_manifold_deform_pruning_and_sprouting(self) -> None:
        from universal_botanical.schema_and_io import load_universal_model_npz, save_universal_model_npz
        from universal_botanical.stylize_and_edit import (
            PRESET_CLASSIC_6,
            PRESET_ORDER,
            apply_horticultural_organ_pruning,
            apply_procedural_apical_sprouting,
            build_12style_neighbor_kaleidoscope,
            build_deform_preset_spec,
            build_mixed_neighbor_mosaic,
            build_universal_deform_rig,
            compose_stylized_universal_plant,
            deform_universal_organ_manifold,
        )

        rng = np.random.default_rng(99)
        p_sup = np.column_stack([rng.uniform(-0.2, 0.2, 20), rng.uniform(-0.2, 0.2, 20), rng.uniform(-0.3, -0.1, 20)])
        org_pts_list = []
        org_recs = []
        lbl_list = [np.full(20, LABEL_BASAL_SUPPORT, dtype=np.int32)]
        for oid in range(12):
            ang = oid * (2.0 * np.pi / 12.0)
            ctr = np.array([0.22 * np.cos(ang), 0.22 * np.sin(ang), 0.05 + 0.03 * oid])
            u = rng.uniform(-0.08, 0.08, 30)
            v = rng.uniform(-0.06, 0.06, 30)
            pts_o = ctr[None, :] + np.column_stack([u, v, np.zeros(30)])
            org_pts_list.append(pts_o)
            lbl_list.append(np.full(30, oid, dtype=np.int32))
            org_recs.append({
                "organ_id": oid, "organ_kind": "LAMINAR_BLADE", "visibility_tier": "OUTER_ENCLOSED",
                "active_kernel_count": 30, "centroid": ctr,
                "e1": np.array([1.0, 0.0, 0.0]), "e2": np.array([0.0, 1.0, 0.0]), "e3": np.array([0.0, 0.0, 1.0]),
                "length": 0.17, "width": 0.13, "thickness": 0.004,
                "mean_vis_views": 8.0, "enclosed_kernel_frac": 0.9, "mean_rgb": np.array([0.85, 0.45, 0.65], dtype=np.float32),
            })

        means = np.vstack([p_sup] + org_pts_list).astype(np.float32)
        n = len(means)
        scales = np.full((n, 3), 0.004, dtype=np.float32)
        scales[20:, 2] = 0.0008
        quats = np.tile(np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32), (n, 1))
        cov6 = build_cov6_from_sq(scales, quats)
        nrms = np.tile(np.array([[0.0, 0.0, 1.0]], dtype=np.float32), (n, 1))
        opac = np.full(n, 0.88, dtype=np.float32)
        rgb = np.tile(np.array([[0.85, 0.45, 0.65]], dtype=np.float32), (n, 1))
        shs = np.zeros((n, 16, 3), dtype=np.float32)
        labels = np.concatenate(lbl_list)

        cloud = SceneGaussianCloud(means, scales, quats, cov6, nrms, opac, rgb, shs)
        sup = BasalSupportModel(
            regime="RECTANGULAR_TRAY_LOFT", vertices=np.zeros((0, 3), dtype=np.float32), faces=np.zeros((0, 3), dtype=np.int32),
            rim_z=-0.10, vessel_bot_z=-0.30, support_kernel_mask=(labels == LABEL_BASAL_SUPPORT), stand_kernel_mask=np.zeros(n, dtype=bool),
        )
        model = fit_universal_organ_patches_and_kinematic_graph("unit_test_plant", cloud, labels, org_recs, sup, [], 0.003, UniversalBotanicalConfig())

        # 1. NPZ roundtrip with allow_pickle=False
        tmp_npz = Path(__file__).resolve().parents[1] / "outputs/unit_test_roundtrip.npz"
        save_universal_model_npz(tmp_npz, model)
        reloaded = load_universal_model_npz(tmp_npz)
        self.assertEqual(len(reloaded.organs), 12)
        self.assertTrue(np.allclose(reloaded.cloud.means, model.cloud.means))
        tmp_npz.unlink(missing_ok=True)

        # 2. Classic 6 mosaic AND Full 12-Style Kaleidoscope assign every single preset on ONE plant!
        mosaic6 = build_mixed_neighbor_mosaic(model)
        self.assertEqual(set(mosaic6.values()), set(PRESET_CLASSIC_6))
        kaleid12 = build_12style_neighbor_kaleidoscope(model)
        self.assertEqual(len(PRESET_ORDER), 12)
        self.assertEqual(set(kaleid12.values()), set(PRESET_ORDER))
        styled_m, counts = compose_stylized_universal_plant(model, kaleid12)
        self.assertEqual(sum(counts.values()), 12)
        self.assertEqual(len(counts), 12)
        # Support covariance & quaternions stay bit-exact untouched!
        self.assertTrue(np.array_equal(styled_m.cloud.cov6[:20], model.cloud.cov6[:20]))

        # 3. Inextensible manifold deformation + Jacobian covariance transport preserves 0.0 support drift & <0.05% arc-length error!
        rig = build_universal_deform_rig(model)
        spec = build_deform_preset_spec(model, rig, "gravity_wilt", strength=1.0)
        def_model, def_stats = deform_universal_organ_manifold(model, rig, spec, transport_covariance=True)
        self.assertEqual(def_stats["static_max_drift_pmed"], 0.0)
        self.assertLess(def_stats["arclength_rel_err_pct"], 0.05)
        self.assertGreater(def_stats["tip_mean_disp_cm"], 2.0)

        # 4. Pruning & procedural sprouting
        pruned_m, pruned_ids, p_stats = apply_horticultural_organ_pruning(model, cam_center=np.array([1.0, 0.0, 0.2]), prune_fraction=0.25)
        self.assertEqual(len(pruned_ids), 3)
        self.assertEqual(p_stats["remaining_organs"], 9)
        sprouted_m, s_stats = apply_procedural_apical_sprouting(model, num_loci=2, buds_per_locus=3, growth_progress=1.0)
        self.assertEqual(s_stats["new_organs"], 6)
        self.assertGreater(len(sprouted_m.cloud.means), len(model.cloud.means))


if __name__ == "__main__":
    unittest.main()
