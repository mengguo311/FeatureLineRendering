"""Analytic construction-view diagnostics; never imports scene images or mesh."""
import unittest
from types import SimpleNamespace
import numpy as np
from src.persistent_boundary.feasibility import fit_fixed_point


def camera(x):
    w2c = np.eye(4)
    w2c[0, 3] = -x
    return SimpleNamespace(K=np.array([[90., 0., 31.], [0., 80., 27.], [0., 0., 1.]]), w2c=w2c)


def pixel(cam, point):
    p = cam.w2c @ np.r_[point, 1.]
    q = cam.K @ p[:3]
    return q[:2] / q[2]


class FixedPointFeasibilityTest(unittest.TestCase):
    def test_two_views_recover_common_point_with_full_intrinsics(self):
        point = np.array([.2, .1, 4.])
        cameras = [camera(0.), camera(1.)]
        result = fit_fixed_point(cameras, [pixel(c, point) for c in cameras], tolerance_px=.5)
        self.assertEqual(result['status'], 'feasible')
        self.assertTrue(result['feasible'])
        self.assertEqual(result['rank'], 3)
        np.testing.assert_allclose(result['xyz'], point, atol=1e-7)
        self.assertLess(max(result['residuals_px']), 1e-6)


    def test_identical_camera_rays_are_underdetermined_not_inconsistent(self):
        point = np.array([.2, .1, 4.])
        cameras = [camera(0.), camera(0.)]
        result = fit_fixed_point(cameras, [pixel(c, point) for c in cameras], tolerance_px=.5)
        self.assertEqual(result['status'], 'underdetermined')
        self.assertFalse(result['feasible'])
        self.assertLess(result['rank'], 3)
        self.assertIsNone(result['xyz'])


    def test_behind_camera_intersection_is_not_a_feasible_asset_anchor(self):
        point = np.array([.2, .1, -3.])
        cameras = [camera(0.), camera(1.)]
        result = fit_fixed_point(cameras, [pixel(c, point) for c in cameras], tolerance_px=.5)
        self.assertEqual(result['status'], 'behind_camera')
        self.assertFalse(result['feasible'])
        self.assertLess(max(result['residuals_px']), 1e-6)
        self.assertTrue(all(z < 0 for z in result['depths']))


    def test_weak_baseline_exposes_conditioning_without_an_internal_gate(self):
        point = np.array([.2, .1, 4.])
        wide = [camera(0.), camera(1.)]
        narrow = [camera(0.), camera(.001)]
        strong = fit_fixed_point(wide, [pixel(c, point) for c in wide], tolerance_px=.5)
        weak = fit_fixed_point(narrow, [pixel(c, point) for c in narrow], tolerance_px=.5)
        self.assertTrue(weak['feasible'])
        self.assertGreater(weak['condition_number'], strong['condition_number'] * 1000)
        self.assertEqual(len(weak['singular_values']), 3)


    def test_rejects_mismatched_camera_and_observation_counts(self):
        cameras = [camera(0.), camera(1.)]
        with self.assertRaises(ValueError):
            fit_fixed_point(cameras, [np.array([31., 27.])], tolerance_px=.5)


    def test_negative_tolerance_is_invalid_not_a_scientific_rejection(self):
        point = np.array([.2, .1, 4.])
        cameras = [camera(0.), camera(1.)]
        with self.assertRaises(ValueError):
            fit_fixed_point(cameras, [pixel(c, point) for c in cameras], tolerance_px=-1.)


if __name__ == '__main__':
    unittest.main()
