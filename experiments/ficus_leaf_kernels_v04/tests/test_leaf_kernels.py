"""Unit tests for ficus_leaf_kernels_v01: workspace write-isolation, parallel stacked-leaf separation, and closed contours."""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from leaf_kernels.data_io import GaussianCloud3D, PriorVectorGeometry, resolve_read_path, resolve_write_path
from leaf_kernels.kernel_partitioner import LeafInstance3D, _build_closed_leaf_contour_3d
from leaf_kernels.leaf_refinement_v02 import (
    apply_m1_opacity_sharpening,
    apply_m2_straddling_kernel_splitting,
    build_cloud_from_arrays,
    build_v02_uv_venation_color_banks,
    orient_leaf_frames_anatomically,
)
from leaf_kernels.style_presets_v03 import (
    PRESET_ORDER,
    build_m1_m2_leaf_substrate,
    compose_mixed_style_plant,
)
from leaf_kernels.leaf_deformer_v04 import (
    build_leaf_deform_rig,
    deform_leaf_substrate,
    make_cupped_helical_twist_spec,
    make_gravity_wilt_spec,
    make_identity_spec,
)


class TestFicusLeafKernels(unittest.TestCase):
    def test_strict_workspace_write_isolation_blocks_other_agent_dirs(self) -> None:
        # Must allow reading from vec_spline3d_v01, but strictly FORBID writing to vec_spline3d_v01 or parent brain!
        r_ok = resolve_read_path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01")
        self.assertTrue(r_ok.name == "vec_spline3d_v01")

        with self.assertRaises(PermissionError):
            resolve_write_path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/conflict.txt")
        with self.assertRaises(PermissionError):
            resolve_write_path("/home/u00134/.gemini/antigravity/brain/879bd51a-3371-416f-9545-fc0432c7b4ee/walkthrough.md")
        with self.assertRaises(ValueError):
            resolve_read_path("/etc/passwd")

        w_ok = resolve_write_path(Path(__file__).resolve().parents[1] / "outputs/test.json")
        self.assertTrue(str(w_ok).endswith("outputs/test.json"))

    def test_closed_leaf_contour_pca_and_camber_fit(self) -> None:
        rng = np.random.default_rng(123)
        u = rng.uniform(-0.04, 0.04, size=120)
        v = rng.uniform(-0.015, 0.015, size=120) * np.sqrt(np.maximum(1.0 - (u / 0.042) ** 2, 0.05))
        w = -0.8 * (u ** 2)  # gentle natural leaf droop
        pts = np.column_stack([0.1 + u, -0.2 + v, 0.3 + w])
        scales = np.full((120, 3), 0.003)

        ctr, elen, ewid, enrm, l_w, w_w, t_w, area_w, loop_3d = _build_closed_leaf_contour_3d(pts, scales)
        self.assertEqual(loop_3d.shape, (24, 3))
        self.assertGreater(l_w, 0.07)
        self.assertLess(w_w, 0.045)
        self.assertLess(t_w, 0.01)
        self.assertGreater(area_w, 0.001)
        self.assertAlmostEqual(float(np.linalg.norm(enrm)), 1.0, places=6)
        self.assertAlmostEqual(float(np.dot(elen, enrm)), 0.0, places=6)

    def test_v02_m1_m2_m3_operators_on_two_adjacent_leaves(self) -> None:
        rng = np.random.default_rng(42)
        # Leaf 0 centered at x=-0.03, Leaf 1 centered at x=+0.03, plus 2 wide straddling kernels at x=-0.004
        pts0 = np.column_stack([rng.uniform(-0.055, -0.008, 40), rng.uniform(-0.015, 0.015, 40), np.zeros(40)])
        pts1 = np.column_stack([rng.uniform(0.008, 0.055, 40), rng.uniform(-0.015, 0.015, 40), np.zeros(40)])
        pts_straddle = np.array([[-0.003, 0.0, 0.0], [0.003, 0.002, 0.0]])
        pts_halo = np.array([[-0.03, 0.0, 0.012], [0.03, 0.0, -0.012]])
        means = np.vstack([pts0, pts1, pts_straddle, pts_halo]).astype(np.float32)
        n = len(means)

        scales = np.tile(np.array([[0.003, 0.0025, 0.0001]], dtype=np.float32), (n, 1))
        # Wide x-axis scale on the two straddling kernels so +/- 1.28*sigma crosses x=0 into neighbor leaf!
        scales[80:82] = np.array([[0.014, 0.003, 0.0001], [0.014, 0.003, 0.0001]], dtype=np.float32)
        quats = np.tile(np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32), (n, 1))
        opac = np.full(n, 0.14, dtype=np.float32)
        opac[82:] = 0.010  # faint halo kernels
        rgb = np.tile(np.array([[0.20, 0.55, 0.18]], dtype=np.float32), (n, 1))
        shs = np.zeros((n, 16, 3), dtype=np.float32)

        cloud = build_cloud_from_arrays(means, scales, quats, opac, rgb, shs)
        labels = np.array([0] * 40 + [1] * 40 + [0, 1, 0, 1], dtype=np.int32)

        priors = PriorVectorGeometry(
            rim_points=np.zeros((0, 3)),
            rim_tangents=np.zeros((0, 3)),
            trunk_points=np.array([[0.0, -0.05, 0.0]], dtype=np.float64),
            trunk_radii=np.array([0.006], dtype=np.float64),
            pot_axis_origin=np.zeros(3),
            pot_axis_dir=np.array([0.0, 0.0, 1.0]),
            pot_h_max=-0.5,
            ink_gaussians=None,
            median_pixel_scale=0.0035,
        )

        leaves: list[LeafInstance3D] = []
        for lid in (0, 1):
            k_idx = np.where(labels == lid)[0].astype(np.int32)
            ctr, elen, ewid, enrm, lw, ww, tw, aw, loop3d = _build_closed_leaf_contour_3d(
                means[k_idx].astype(np.float64), scales[k_idx].astype(np.float64)
            )
            leaves.append(
                LeafInstance3D(
                    leaf_id=lid,
                    kernel_indices=k_idx,
                    active_kernel_count=len(k_idx) - 1,
                    centroid=ctr,
                    axis_length=elen,
                    axis_width=ewid,
                    normal=enrm,
                    length_world=lw,
                    width_world=ww,
                    thickness_world=tw,
                    area_world=aw,
                    mean_vis_views=6.0,
                    closure_confidence=0.85,
                    visibility_tier="OUTER_ENCLOSED",
                    boundary_loop_3d=loop3d,
                    mean_rgb=np.array([0.2, 0.55, 0.18]),
                )
            )

        leaves = orient_leaf_frames_anatomically(cloud, labels, leaves, priors)

        # Test M1: Opacity sharpening boosts interior sheet kernels and suppresses faint halo kernels!
        c_m1, st_m1 = apply_m1_opacity_sharpening(cloud, labels, leaves)
        self.assertGreater(st_m1["median_active_leaf_opacity_after"], st_m1["median_active_leaf_opacity_before"] * 2.0)
        self.assertLess(float(c_m1.opacities[82]), 0.002)

        # Test M2: Straddling wide kernels split and reassign cross-seam child to neighbor leaf!
        c_m2, lbl_m2, leaves_m2, st_m2 = apply_m2_straddling_kernel_splitting(cloud, labels, leaves, priors, num_passes=1)
        self.assertGreater(len(c_m2.means), len(cloud.means))
        self.assertGreaterEqual(st_m2["total_parent_splits"], 2)
        self.assertGreaterEqual(st_m2["children_reassigned_across_seams"], 1)

        # Test M3: UV venation & watercolor rim bank produces valid bounded colors with non-trivial texture variance!
        banks_m3 = build_v02_uv_venation_color_banks(c_m2, lbl_m2, leaves_m2, enable_m3_venation=True)
        sty = banks_m3["botanical_stylized"]
        self.assertEqual(sty.shape, (len(c_m2.means), 3))
        self.assertTrue(np.all(np.isfinite(sty)) and float(sty.min()) >= 0.0 and float(sty.max()) <= 1.0)
        self.assertGreater(float(sty[lbl_m2 == 0].std()), 0.03)

        # Test v03: M1+M2 substrate + Mixed-Style Same-Plant composer (Leaf 0 = pointillist_stipple, Leaf 1 = ukiyoe_papercut)
        sub_m12 = build_m1_m2_leaf_substrate(cloud, labels, leaves, priors)
        mixed_cloud, mixed_rgb, counts = compose_mixed_style_plant(
            sub_m12, {0: "pointillist_stipple", 1: "ukiyoe_papercut"}
        )
        self.assertEqual(counts["pointillist_stipple"], 1)
        self.assertEqual(counts["ukiyoe_papercut"], 1)
        # Pointillist leaf 0 must have smaller median max-scale than Ukiyo-e cutout leaf 1!
        sc0 = float(np.median(mixed_cloud.scales[sub_m12.kernel_labels == 0].max(axis=1)))
        sc1 = float(np.median(mixed_cloud.scales[sub_m12.kernel_labels == 1].max(axis=1)))
        self.assertLess(sc0, sc1 * 0.72)
        self.assertEqual(len(PRESET_ORDER), 6)

        # Test v04: Petiole-hinged 3D leaf deformation & Jacobian covariance transport invariants!
        rig = build_leaf_deform_rig(sub_m12)
        c_id, _, inv_id = deform_leaf_substrate(sub_m12, rig, make_identity_spec(rig.num_leaves))
        self.assertLess(float(np.max(np.abs(c_id.means - sub_m12.cloud.means))), 1e-5)
        self.assertEqual(inv_id["stem_and_pot_max_drift_mm"], 0.0)

        # Under 55-deg gravity droop & 48-deg twist: petiole drift remains < 1.0 mm & arc-length error < 1.5%!
        sp_wilt = make_gravity_wilt_spec(rig, max_droop_deg=55.0)
        c_wilt, _, inv_wilt = deform_leaf_substrate(sub_m12, rig, sp_wilt, transport_covariance=True)
        self.assertLess(inv_wilt["petiole_hinge_median_drift_mm"], 1.0)
        self.assertLess(inv_wilt["median_arc_length_error_pct"], 1.5)
        self.assertGreater(inv_wilt["mean_tip_displacement_cm"], 1.0)
        self.assertTrue(np.all(np.isfinite(c_wilt.cov6)))

        sp_twist = make_cupped_helical_twist_spec(rig, cup_curv=35.0, twist_deg=48.0)
        c_tw, _, inv_tw = deform_leaf_substrate(sub_m12, rig, sp_twist, transport_covariance=True)
        self.assertLess(inv_tw["median_arc_length_error_pct"], 1.5)
        self.assertTrue(np.all(np.isfinite(c_tw.means)))


if __name__ == "__main__":
    unittest.main()
