"""Unit tests for vec_spline3d v02: B-splines, ARC_3D, co-circular ring consolidation, PyTorch arc grad, and SCMS."""

from __future__ import annotations

import math
import unittest
from pathlib import Path

import numpy as np
import torch

from vec_spline3d.co_circular_arcs import _circle_from_two_oriented_segments
from vec_spline3d.schema import (
    CoaxialRingFamilySpec,
    CurveNetwork3D,
    JunctionNode,
    LatheEnvelopeGenerator,
    ParametricCurvePrimitive,
    RibbonGeometry,
    SweptTubeGenerator,
    bspline_basis_matrices,
    circular_arc_geometry_from_3pt,
    clamped_uniform_knots,
    evaluate_circular_arc_3pt_numpy,
    evaluate_circular_arc_3pt_torch,
    fit_circular_arc_to_polyline,
    fit_clamped_bspline_to_polyline,
    resolve_safe_path,
)
from vec_spline3d.stage1_ray_clean import CleanedChainSegment
from vec_spline3d.stage2_scms_consolidate import run_stage2_scms_consolidate


class TestVecSpline3DPipeline(unittest.TestCase):
    def test_bspline_basis_partition_of_unity_and_derivatives(self) -> None:
        u = np.linspace(0.0, 1.0, 25)
        B, B_du, B_d2u, knots, deg = bspline_basis_matrices(6, u, degree=3)
        self.assertEqual(deg, 3)
        np.testing.assert_allclose(B.sum(axis=1), np.ones(25), atol=1e-12)
        greville = np.array([np.mean(knots[i + 1 : i + 4]) for i in range(6)])
        ctrl = np.stack([greville, np.zeros(6), np.zeros(6)], axis=1)
        np.testing.assert_allclose((B @ ctrl)[:, 0], u, atol=1e-10)
        np.testing.assert_allclose((B_du @ ctrl)[:, 0], np.ones(25), atol=1e-9)
        np.testing.assert_allclose((B_d2u @ ctrl)[:, 0], np.zeros(25), atol=1e-8)

    def test_circular_arc_minor_and_major_sweep_and_pytorch_grad(self) -> None:
        # Test a 240-degree major circular arc in a tilted 3D plane!
        center = np.array([0.1, -0.2, -0.6])
        r = 0.22
        thetas = np.linspace(0.2, 0.2 + math.radians(240.0), 40)
        pts_gt = center[None, :] + r * np.column_stack([np.cos(thetas), np.sin(thetas), np.zeros_like(thetas)])

        ctrl_3x3, max_err, meta = fit_circular_arc_to_polyline(pts_gt, pin_endpoints=False)
        self.assertTrue(meta["valid"])
        self.assertLess(max_err, 1e-6)
        self.assertAlmostEqual(meta["radius"], r, places=5)
        self.assertAlmostEqual(math.degrees(meta["sweep_rad"]), 240.0, places=3)

        geom = circular_arc_geometry_from_3pt(ctrl_3x3[0], ctrl_3x3[1], ctrl_3x3[2])
        self.assertFalse(geom["is_collinear"])
        self.assertAlmostEqual(geom["radius"], r, places=5)

        # Verify PyTorch evaluation matches NumPy and produces finite gradients
        u_np = np.linspace(0.0, 1.0, 17)
        pts_np, d1_np, _ = evaluate_circular_arc_3pt_numpy(ctrl_3x3, u_np)
        p0_t = torch.tensor(ctrl_3x3[0:1], dtype=torch.float32, requires_grad=True)
        pm_t = torch.tensor(ctrl_3x3[1:2], dtype=torch.float32, requires_grad=True)
        p1_t = torch.tensor(ctrl_3x3[2:3], dtype=torch.float32, requires_grad=True)
        pts_t, d1_t = evaluate_circular_arc_3pt_torch(p0_t, pm_t, p1_t, torch.tensor(u_np, dtype=torch.float32))
        np.testing.assert_allclose(pts_t.detach().numpy(), pts_np, atol=1e-5)
        np.testing.assert_allclose(d1_t.detach().numpy(), d1_np, atol=1e-4)
        loss = (pts_t ** 2).sum() + (d1_t ** 2).sum()
        loss.backward()
        self.assertTrue(torch.isfinite(pm_t.grad).all())

    def test_parent_zucker_cocircular_pair_detection(self) -> None:
        p = 0.0035
        r = 0.18  # pot radius
        th1, th2 = 0.3, 0.55
        p1 = np.array([r * math.cos(th1), r * math.sin(th1), -0.5])
        t1 = np.array([-math.sin(th1), math.cos(th1), 0.0])
        p2 = np.array([r * math.cos(th2), r * math.sin(th2), -0.5])
        t2 = np.array([-math.sin(th2), math.cos(th2), 0.0])
        circ = _circle_from_two_oriented_segments(p1, t1, p2, t2, p_scale=p)
        self.assertIsNotNone(circ)
        assert circ is not None
        self.assertAlmostEqual(circ["radius"], r, places=3)
        np.testing.assert_allclose(circ["center"], np.array([0.0, 0.0, -0.5]), atol=1e-3)

    def test_ray_anisotropic_scms_merges_parallel_double_tracks(self) -> None:
        p = 0.0035
        t_param = np.linspace(0.0, 0.08, 22)
        true_curve = np.stack([t_param, 0.015 * np.sin(30.0 * t_param), np.zeros_like(t_param)], axis=1)
        tang = np.gradient(true_curve, axis=0)
        tang /= np.linalg.norm(tang, axis=1, keepdims=True)

        ray_a = np.tile(np.array([[0.0, 0.1, 0.995]]), (22, 1))
        ray_b = np.tile(np.array([[0.0, -0.1, 0.995]]), (22, 1))
        seg_a = CleanedChainSegment(
            0, 10, "train_r_7", np.array([0.0, 0.0, -4.0]), true_curve + 1.1 * p * ray_a,
            tang, ray_a, np.full(22, p), np.full(22, 4, dtype=np.int32), np.zeros(22, dtype=bool), True,
        )
        seg_b = CleanedChainSegment(
            1, 11, "train_r_80", np.array([0.0, 0.5, -4.0]), true_curve - 1.1 * p * ray_b,
            tang, ray_b, np.full(22, p), np.full(22, 4, dtype=np.int32), np.zeros(22, dtype=bool), True,
        )
        ridges, _ = run_stage2_scms_consolidate([seg_a, seg_b], median_pixel_scale=p, num_scms_iters=6)
        self.assertEqual(len(ridges), 1)
        ctrl, _, deg, err = fit_clamped_bspline_to_polyline(ridges[0].points_3d, num_ctrl=6)
        self.assertEqual(deg, 3)
        self.assertLess(err, 0.5 * p)

    def test_curve_network_export_with_arc3d_and_safe_path(self) -> None:
        n0 = JunctionNode(0, np.array([0.1, 0.0, 0.0]))
        n1 = JunctionNode(1, np.array([0.0, 0.1, 0.0]))
        pm = np.array([0.1 * math.sqrt(0.5), 0.1 * math.sqrt(0.5), 0.0])
        arc = ParametricCurvePrimitive(
            curve_id=0,
            primitive_type="ARC_3D",
            control_points=np.vstack([n0.position, pm, n1.position]),
            knots=clamped_uniform_knots(3, 2),
            degree=2,
            start_node_id=0,
            end_node_id=1,
            role="COCIRCULAR_RING",
            supporting_views=["train_r_7", "train_r_80"],
        )
        net = CurveNetwork3D(scene_name="unit_test_v02", curves={0: arc}, nodes={0: n0, 1: n1})
        net.rebuild_node_incidence()
        gs = net.to_line_gaussians(color_mode="primitive")
        self.assertGreater(len(gs["means"]), 10)
        self.assertTrue(np.all(np.linalg.eigvalsh(gs["covariance"]) > 0.0))

        out_root = Path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/unit_test_tmp")
        files = net.save_package(out_root)
        self.assertTrue(Path(files["json"]).is_file())

        with self.assertRaises(ValueError):
            resolve_safe_path("/etc/passwd")

    def test_coaxial_ring_darboux_ribbon_and_triaxial_surflets(self) -> None:
        # Closed 360-degree coaxial ring built from two 180-degree ARC_3D halves with analytical lathe normals
        r = 0.25
        h = -0.72
        n0 = JunctionNode(0, np.array([r, 0.0, h]), kind="SMOOTH_CONTINUATION")
        n1 = JunctionNode(1, np.array([-r, 0.0, h]), kind="SMOOTH_CONTINUATION")
        rib_a = RibbonGeometry(
            edge_class="COAXIAL_RING",
            control_normals=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]]),
            half_width_px=0.44,
            thickness_px=0.22,
            coaxial_family_id=0,
            coaxial_ring_h=h,
            coaxial_ring_r=r,
        )
        rib_b = RibbonGeometry(
            edge_class="COAXIAL_RING",
            control_normals=np.array([[-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [1.0, 0.0, 0.0]]),
            half_width_px=0.44,
            thickness_px=0.22,
            coaxial_family_id=0,
            coaxial_ring_h=h,
            coaxial_ring_r=r,
        )
        c0 = ParametricCurvePrimitive(
            curve_id=0, primitive_type="ARC_3D",
            control_points=np.array([[r, 0.0, h], [0.0, r, h], [-r, 0.0, h]]),
            knots=clamped_uniform_knots(3, 2), degree=2, start_node_id=0, end_node_id=1,
            role="COAXIAL_RING", supporting_views=["train_r_7", "train_r_80"], ribbon=rib_a,
        )
        c1 = ParametricCurvePrimitive(
            curve_id=1, primitive_type="ARC_3D",
            control_points=np.array([[-r, 0.0, h], [0.0, -r, h], [r, 0.0, h]]),
            knots=clamped_uniform_knots(3, 2), degree=2, start_node_id=1, end_node_id=0,
            role="COAXIAL_RING", supporting_views=["train_r_7", "train_r_80"], ribbon=rib_b,
        )
        _, pts, T, B, N = c0.evaluate_darboux_frame(num_samples=25)
        np.testing.assert_allclose(np.linalg.norm(pts[:, :2], axis=1), np.full(25, r), atol=1e-12)
        np.testing.assert_allclose(np.sum(T * N, axis=1), np.zeros(25), atol=1e-12)
        np.testing.assert_allclose(np.sum(B * N, axis=1), np.zeros(25), atol=1e-12)
        np.testing.assert_allclose(np.linalg.norm(N, axis=1), np.ones(25), atol=1e-12)

        fam = CoaxialRingFamilySpec(
            family_id=0, axis_origin=np.zeros(3), axis_dir=np.array([0.0, 0.0, 1.0]),
            e1=np.array([1.0, 0.0, 0.0]), e2=np.array([0.0, 1.0, 0.0]),
            h_min=-1.0, h_max=-0.5, profile_h=np.array([-1.0, -0.5]), profile_r=np.array([r, r]),
            ring_heights=[h], ring_radii=[r], member_curve_ids=[0, 1],
        )
        net = CurveNetwork3D(scene_name="unit_test_v03", curves={0: c0, 1: c1}, nodes={0: n0, 1: n1}, coaxial_families=[fam])
        net.rebuild_node_incidence()
        self.assertEqual(net.summary_stats()["open_endpoint_ratio"], 0.0)

        gs = net.to_line_gaussians(color_mode="edge_class", use_ribbon_surflets=True)
        eigs = np.linalg.eigvalsh(gs["covariance"])
        # Verify strictly positive tri-axial eigenvalues: thick^2 < width^2 < para^2
        self.assertTrue(np.all(eigs[:, 0] > 0.0))
        self.assertTrue(np.all(eigs[:, 1] > eigs[:, 0] * 1.5))
        self.assertTrue(np.all(eigs[:, 2] > eigs[:, 1]))

        out_root = Path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/unit_test_tmp")
        files = net.save_package(out_root)
        self.assertTrue(Path(files["ribbons_obj"]).is_file())
        self.assertTrue(Path(files["semantic_gaussians_npz"]).is_file())

    def test_lathe_and_tube_perspective_horizon_tangency_and_mesh_export(self) -> None:
        # 1. Exact perspective horizon tangency N(X) · (O_cam - X) == 0 on a curved spherical/conical lathe
        hs = np.linspace(-1.0, -0.5, 41)
        rs = 0.25 - 0.8 * ((hs + 0.75) ** 2)
        dr_dh = np.gradient(rs, hs)
        lg = LatheEnvelopeGenerator(
            generator_id=0,
            axis_origin=np.zeros(3),
            axis_dir=np.array([0.0, 0.0, 1.0]),
            e1=np.array([1.0, 0.0, 0.0]),
            e2=np.array([0.0, 1.0, 0.0]),
            profile_h=hs,
            profile_r=rs,
        )
        cam = np.array([1.8, -1.2, 0.9])  # Steep perspective viewing angle!
        branches = lg.evaluate_horizon_curves(cam, num_samples=41)
        self.assertEqual(len(branches), 2)
        for pts, _, _, _ in branches:
            # True surface normal at pts: er - dr_dh * ez
            er = pts[:, :2] / np.linalg.norm(pts[:, :2], axis=1, keepdims=True)
            n_surf = np.column_stack([er[:, 0], er[:, 1], -dr_dh])
            n_surf /= np.linalg.norm(n_surf, axis=1, keepdims=True)
            view_vecs = cam[None, :] - pts
            view_vecs /= np.linalg.norm(view_vecs, axis=1, keepdims=True)
            # Horizon condition N_surf · view_vec == 0!
            np.testing.assert_allclose(np.sum(n_surf * view_vecs, axis=1), np.zeros(len(pts)), atol=1e-3)

        # 2. Swept cylindrical tube horizon tangency & dynamic Gaussian rendering
        spine = np.array([[0.0, 0.0, -0.5], [0.02, 0.01, -0.3], [0.05, 0.03, -0.1], [0.08, 0.05, 0.1]])
        tg = SweptTubeGenerator(
            generator_id=1,
            spine_control_points=spine,
            control_radii=np.array([0.014, 0.013, 0.012, 0.010]),
            knots=clamped_uniform_knots(4, 3),
            degree=3,
        )
        t_branches = tg.evaluate_horizon_curves(cam, num_samples=24, occluding_lathe=lg)
        self.assertGreaterEqual(len(t_branches), 2)

        net = CurveNetwork3D(scene_name="unit_test_v04", lathe_generators=[lg], tube_generators=[tg])
        gs_static = net.to_line_gaussians(camera_center=None)
        gs_view = net.to_line_gaussians(color_mode="edge_class", camera_center=cam)
        self.assertEqual(len(gs_static["means"]), 0)
        self.assertGreater(len(gs_view["means"]), 50)
        self.assertTrue(np.all(np.linalg.eigvalsh(gs_view["covariance"]) > 0.0))

        out_root = Path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/unit_test_tmp")
        files = net.save_package(out_root)
        self.assertTrue(Path(files["envelopes_obj"]).is_file())

    def test_arbitrary_axis_horizontal_cylinder_horizon_and_frame(self) -> None:
        from vec_spline3d.coaxial_rings import _make_axis_frame
        from vec_spline3d.contour_generators import evaluate_lathe_horizon_torch

        # Horizontal bass-drum-like cylinder axis (nearly 88 deg from vertical z!)
        a_dir, e1, e2 = _make_axis_frame(np.array([0.96, 0.27, 0.05]))
        self.assertAlmostEqual(float(np.linalg.norm(a_dir)), 1.0, places=9)
        self.assertAlmostEqual(float(np.dot(a_dir, e1)), 0.0, places=9)
        self.assertAlmostEqual(float(np.dot(e1, e2)), 0.0, places=9)

        hs = np.linspace(-0.22, 0.22, 32)
        rs = np.full_like(hs, 0.26)
        lg = LatheEnvelopeGenerator(
            generator_id=2,
            axis_origin=np.array([0.05, -0.10, 0.15]),
            axis_dir=a_dir,
            e1=e1,
            e2=e2,
            profile_h=hs,
            profile_r=rs,
        )
        cam = np.array([0.3, -2.4, 1.3])
        branches = lg.evaluate_horizon_curves(cam, num_samples=32)
        self.assertEqual(len(branches), 2)
        for pts, _, _, n_u in branches:
            v_vecs = cam[None, :] - pts
            v_vecs /= np.linalg.norm(v_vecs, axis=1, keepdims=True)
            np.testing.assert_allclose(np.sum(n_u * v_vecs, axis=1), np.zeros(len(pts)), atol=2e-3)

        dr_t = torch.zeros(len(hs), dtype=torch.float32, requires_grad=True)
        cam_t = torch.tensor(cam[None, :], dtype=torch.float32)
        pts_t, _, _ = evaluate_lathe_horizon_torch(lg, dr_t, cam_t, num_samples=20)
        (pts_t ** 2).sum().backward()
        self.assertTrue(torch.isfinite(dr_t.grad).all())

    def test_planar_wireframe_coplanarity_and_manhattan_regularization(self) -> None:
        from vec_spline3d.multimodal_data import MultiModalSceneBundle, MultiModalView
        from vec_spline3d.planar_wireframe_reg import discover_and_regularize_planar_wireframes
        from vec_spline3d.stage1_ray_clean import GPUViewFieldEvaluator

        # Build a tilted architectural wall plane with 12 noisy horizontal & vertical window-frame segments
        p = 0.002
        n_true = np.array([0.0, 0.258819, 0.965926], dtype=np.float64)  # 15 deg tilted plane
        d_true = 0.10
        u_horiz = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        u_vert = np.cross(n_true, u_horiz)
        origin_p = d_true * n_true

        nodes: dict[int, JunctionNode] = {}
        curves: dict[int, ParametricCurvePrimitive] = {}
        rng = np.random.default_rng(7)
        nid = 0
        cid = 0
        # 6 horizontal window sills/lintels + 6 vertical jambs with out-of-plane jitter & slight angle skew
        for row_i in range(6):
            y_v = (row_i - 2.5) * 0.03
            p0 = origin_p + (-0.08) * u_horiz + y_v * u_vert + rng.uniform(-0.9 * p, 0.9 * p) * n_true
            p1 = origin_p + (0.08) * u_horiz + (y_v + 0.0025) * u_vert + rng.uniform(-0.9 * p, 0.9 * p) * n_true
            nodes[nid] = JunctionNode(nid, p0)
            nodes[nid + 1] = JunctionNode(nid + 1, p1)
            if row_i == 0:
                # Make one lintel a shallow false ARC_3D to verify planar linearization!
                pm = 0.5 * (p0 + p1) + 0.35 * p * u_vert
                curves[cid] = ParametricCurvePrimitive(cid, "ARC_3D", np.vstack([p0, pm, p1]), clamped_uniform_knots(3, 2), 2, nid, nid + 1, pixel_scale=p)
            else:
                curves[cid] = ParametricCurvePrimitive(cid, "LINE_3D", np.vstack([p0, p1]), clamped_uniform_knots(2, 1), 1, nid, nid + 1, pixel_scale=p)
            nid += 2
            cid += 1

        for col_i in range(6):
            x_u = (col_i - 2.5) * 0.03
            p0 = origin_p + x_u * u_horiz + (-0.08) * u_vert + rng.uniform(-0.9 * p, 0.9 * p) * n_true
            p1 = origin_p + (x_u - 0.0025) * u_horiz + (0.08) * u_vert + rng.uniform(-0.9 * p, 0.9 * p) * n_true
            nodes[nid] = JunctionNode(nid, p0)
            nodes[nid + 1] = JunctionNode(nid + 1, p1)
            curves[cid] = ParametricCurvePrimitive(cid, "LINE_3D", np.vstack([p0, p1]), clamped_uniform_knots(2, 1), 1, nid, nid + 1, pixel_scale=p)
            nid += 2
            cid += 1

        # Add one shared 90-degree L-corner node so junction plane seed fires even without dense depth maps
        nodes[0].position = origin_p + (-0.08) * u_horiz + (-0.075) * u_vert + 0.8 * p * n_true
        curves[11].start_node_id = 0

        net = CurveNetwork3D(scene_name="unit_planar_test", curves=curves, nodes=nodes)
        net.rebuild_node_incidence()
        net.sync_endpoints_from_nodes()

        init_plane_err = float(np.mean([abs(float(np.dot(nd.position, n_true)) - d_true) for nd in net.nodes.values()]))

        dummy_view = MultiModalView(
            view_name="v0", split="train", width=64, height=64, fx=80.0, fy=80.0, cx=31.5, cy=31.5,
            w2c=np.eye(4), c2w=np.eye(4), cam_center=np.array([0.0, 0.0, -2.0]),
            alpha=np.ones((64, 64), dtype=np.float32),
            outside_hull_dt=np.zeros((64, 64), dtype=np.float32),
            edge_strength=np.zeros((64, 64), dtype=np.float32),
            edge_mask=np.zeros((64, 64), dtype=bool),
            edge_dt=np.ones((64, 64), dtype=np.float32),
            edge_tangent_2d=np.zeros((64, 64, 2), dtype=np.float32),
            skeleton=np.zeros((64, 64), dtype=bool),
        )
        bundle = MultiModalSceneBundle("unit_planar_test", [dummy_view], [], [], None, p, has_silhouette_mask=False)
        evaluator = GPUViewFieldEvaluator([dummy_view], device=torch.device("cpu"))
        st = discover_and_regularize_planar_wireframes(net, bundle, evaluator)

        self.assertEqual(st["detected_planes"], 1)
        self.assertEqual(st["manhattan_planes"], 1)
        self.assertEqual(net.curves[0].primitive_type, "LINE_3D")
        n_fit = np.asarray(net.planar_patches[0]["normal"], dtype=np.float64)
        d_fit = float(net.planar_patches[0]["offset_d"])
        fitted_plane_err = float(np.max([abs(float(np.dot(nd.position, n_fit)) - d_fit) for nd in net.nodes.values()]))
        self.assertLess(fitted_plane_err, 1e-5)
        final_plane_err = float(np.mean([abs(float(np.dot(nd.position, n_true)) - d_true) for nd in net.nodes.values()]))
        self.assertLess(final_plane_err, init_plane_err * 0.45)

    def test_tilted_disc_36sector_outer_boundary_circle_fit(self) -> None:
        from vec_spline3d.coaxial_rings import _fit_disc_outer_boundary_2d, _make_axis_frame

        p = 0.003
        rng = np.random.default_rng(42)
        # Uniformly filled circular cymbal disc (R = 0.24 = 80p) vs square architectural wall patch
        r_u = 0.24 * np.sqrt(rng.uniform(0.0, 1.0, size=2400))
        th_u = rng.uniform(-math.pi, math.pi, size=2400)
        xy_disc = np.column_stack([0.12 + r_u * np.cos(th_u), -0.07 + r_u * np.sin(th_u)])
        fit_d = _fit_disc_outer_boundary_2d(xy_disc, p)
        self.assertIsNotNone(fit_d)
        assert fit_d is not None
        c2, rad, p90_r, out_f, n_sec, octs = fit_d
        np.testing.assert_allclose(c2, np.array([0.12, -0.07]), atol=1.5 * p)
        self.assertAlmostEqual(rad, 0.24, delta=1.5 * p)
        self.assertLess(p90_r, 2.5 * p)
        self.assertLessEqual(out_f, 0.04)
        self.assertGreaterEqual(n_sec, 30)
        self.assertEqual(octs, 8)

        # Square patch [-0.24, 0.24]^2 must fail BOTH circular boundary residual (<=2.7p) AND outside-corner check (<=0.042)!
        xy_sq = rng.uniform(-0.24, 0.24, size=(2400, 2))
        fit_sq = _fit_disc_outer_boundary_2d(xy_sq, p)
        if fit_sq is not None:
            self.assertGreater(fit_sq[2], 8.0 * p)
            self.assertGreater(fit_sq[3], 0.05)

        # Tilted axis frame check (25 deg tilt)
        a_dir, e1, e2 = _make_axis_frame(np.array([-0.28, 0.32, 0.905]))
        self.assertAlmostEqual(float(np.dot(a_dir, np.cross(e1, e2))), 1.0, places=7)


if __name__ == "__main__":
    unittest.main()
