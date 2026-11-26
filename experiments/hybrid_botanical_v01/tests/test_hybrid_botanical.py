"""Unit tests for hybrid_botanical_v01: strict write isolation, 4-level pipe-model tree, and Dual-Arc pointed cusps."""

from __future__ import annotations

import unittest
from pathlib import Path
import numpy as np

from hybrid_botanical.schema_and_io import (
    LABEL_WOOD_SKELETON,
    DualArcTrimmedLeafPatch,
    LathePotPrimitive,
    build_cloud_bank,
    resolve_read_path,
    resolve_write_path,
)
from hybrid_botanical.tree_arborizer import build_4level_botanical_tree_and_bind_wood


class TestHybridBotanicalV01(unittest.TestCase):
    def test_strict_upstream_write_protection(self) -> None:
        # Must allow reading from both upstream dirs, but block writing to either!
        self.assertEqual(resolve_read_path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01").name, "vec_spline3d_v01")
        self.assertEqual(resolve_read_path("/home/u00134/.gemini/antigravity/scratch/ficus_leaf_kernels_v01").name, "ficus_leaf_kernels_v01")

        with self.assertRaises(PermissionError):
            resolve_write_path("/home/u00134/.gemini/antigravity/scratch/vec_spline3d_v01/outputs/bad.txt")
        with self.assertRaises(PermissionError):
            resolve_write_path("/home/u00134/.gemini/antigravity/scratch/ficus_leaf_kernels_v01/outputs/bad.txt")
        with self.assertRaises(ValueError):
            resolve_read_path("/etc/shadow")

        ok_w = resolve_write_path(Path(__file__).resolve().parents[1] / "outputs/ok.json")
        self.assertTrue(str(ok_w).endswith("outputs/ok.json"))

    def test_dual_arc_pointed_cusp_closure_and_4level_pipe_tree(self) -> None:
        patch = DualArcTrimmedLeafPatch(
            leaf_id=0, parent_branch_id=2, hub_id=0, visibility_tier="OUTER_ENCLOSED",
            p_base=np.array([0.0, 0.0, 0.2]),
            e1=np.array([1.0, 0.0, 0.0]),
            e2=np.array([0.0, 1.0, 0.0]),
            e3=np.array([0.0, 0.0, 1.0]),
            blade_length=0.10,
            v_left_ctrl=np.array([0.0, 0.015, 0.026, 0.022, 0.011, 0.0]),
            v_right_ctrl=np.array([0.0, -0.015, -0.026, -0.022, -0.011, 0.0]),
            camber_coef=np.array([0.0, 0.0, -0.4, 0.2]),
            eigen_pca_code=np.zeros(3),
            kernel_indices=np.array([0], dtype=np.int32),
            infilled_kernel_count=0,
            area_cm2=32.0,
        )
        pl, pr = patch.eval_3d_boundary_arcs(n_per_arc=24)
        # Exact C0 cusp closure at both petiole base (index 0) and distal pointed apex (index -1)!
        self.assertLess(float(np.linalg.norm(pl[0] - pr[0])), 1e-12)
        self.assertLess(float(np.linalg.norm(pl[-1] - pr[-1])), 1e-12)
        # Mid-blade width is strictly positive
        self.assertGreater(float(pl[12, 1] - pr[12, 1]), 0.03)

        # Synthetic 4-level tree test: 1 trunk + wood waypoints + 4 leaf petioles -> 100% reachability & pipe radii!
        w_pts = np.column_stack([np.zeros(20), np.linspace(0.0, 0.08, 20), np.linspace(0.0, 0.25, 20)]).astype(np.float32)
        cloud = build_cloud_bank(
            means=w_pts,
            scales=np.full((20, 3), 0.003, dtype=np.float32),
            quats_wxyz=np.tile(np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32), (20, 1)),
            opacities=np.full(20, 0.6, dtype=np.float32),
            rgb=np.full((20, 3), 0.35, dtype=np.float32),
            kernel_labels=np.full(20, LABEL_WOOD_SKELETON, dtype=np.int32),
        )
        leaf_bases = np.array([
            [0.01, 0.09, 0.26], [-0.01, 0.09, 0.26],
            [0.01, 0.10, 0.27], [-0.01, 0.10, 0.27],
        ], dtype=np.float64)
        pot = LathePotPrimitive(
            axis_origin=np.zeros(3), axis_dir=np.array([0.0, 0.0, 1.0]),
            profile_h=np.array([-0.3, -0.1]), profile_r=np.array([0.1, 0.12]), h_max=-0.1,
        )
        trunks = [{"spine_ctrl": np.array([[0.0, 0.0, -0.1], [0.0, 0.0, 0.22]]), "radii_ctrl": np.array([0.010, 0.006])}]
        tree, _, st = build_4level_botanical_tree_and_bind_wood(cloud, leaf_bases, trunks, pot, p_med=0.0035)
        self.assertEqual(st["leaf_to_root_reachability_pct"], 100.0)
        # Da Vinci pipe-model monotonicity: level-1 base radius > level-3 petiole base radius!
        r_lvl1 = [b.radius_base for b in tree.branches if b.level == 1][0]
        r_lvl3 = [b.radius_base for b in tree.branches if b.level == 3][0]
        self.assertGreater(r_lvl1, r_lvl3)


if __name__ == "__main__":
    unittest.main()
