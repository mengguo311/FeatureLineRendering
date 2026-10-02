"""Native export contract; these tests require the isolated CUDA builds."""
import unittest

import numpy as np

from src.hybrid_raster_native import (
    camera_matrices, compare_calibration, render_native, validate_raw,
)


def camera(h=33, w=33):
    return dict(native_height=h, native_width=w,
                native_K=[[32., 0., (w-1)/2], [0., 32., (h-1)/2], [0., 0., 1.]],
                w2c=np.eye(4).tolist())


def fixture(depths=(3.5, 3.), opacities=(.8, .12)):
    # ID zero stays offscreen; IDs 1,2 must survive without local remapping.
    n = len(depths)+1
    return dict(mu=np.array([[100., 0., 3.]]+[[0., 0., z] for z in depths]),
                scale=np.full((n, 3), .22), quat=np.tile([1., 0., 0., 0.], (n, 1)),
                opacity=np.array([.9]+list(opacities)),
                albedo=np.array([[.2, .3, .5]]+[[i%2, (i+1)%2, .25] for i in range(n-1)]))


class NativeContractTest(unittest.TestCase):
    def test_01_vertical_export_and_unpatched_calibration(self):
        g, cam = fixture(), camera()
        raw = render_native(g, cam)
        validate_raw(raw, len(g['mu']), (33, 33))
        y = x = 16
        np.testing.assert_array_equal(raw['topk_id'][y, x], [1, 2, -1, -1])
        # Front ID2 contributes .12; back ID1 contributes .8*(1-.12).
        np.testing.assert_allclose(raw['topk_w'][y, x], [.704, .12, 0, 0], atol=3e-6)
        self.assertAlmostEqual(float(raw['alpha'][y, x]), .824, places=5)
        np.testing.assert_allclose(raw['topk_depth'][y, x, :2], [3.5, 3.], atol=3e-5)
        expected_rgb = .704*g['albedo'][1]+.12*g['albedo'][2]+(1-.824)
        np.testing.assert_allclose(raw['rgb'][y, x], expected_rgb, atol=3e-6)
        self.assertAlmostEqual(float(raw['moment2'][y, x]), .704*3.5**2+.12*3.**2, places=4)
        self.assertAlmostEqual(float(raw['depth'][y, x]), (.704*3.5+.12*3.)/.824, places=5)
        self.assertTrue(np.all(raw['topk_id'][0, 0] == -1))
        self.assertEqual(float(raw['alpha'][0, 0]), 0.)
        np.testing.assert_array_equal(raw['rgb'][0, 0], np.ones(3))
        self.assertEqual(compare_calibration(raw, render_native(g, cam, patched=False))['status'], 'PASS')

    def test_02_more_than_four_contributors_keeps_full_moment(self):
        depths = np.arange(3., 4.5, .25)
        g, cam = fixture(depths, [.15]*len(depths)), camera()
        raw = render_native(g, cam)
        validate_raw(raw, len(g['mu']), (33, 33))
        weights = .15*.85**np.arange(len(depths))
        y = x = 16
        self.assertLess(raw['topk_w'][y, x].sum(), raw['alpha'][y, x]-.05)
        self.assertAlmostEqual(float(raw['moment2'][y, x]), float(np.dot(weights, depths**2)), places=4)
        self.assertAlmostEqual(float(raw['alpha'][y, x]), float(weights.sum()), places=5)

    def test_03_empty_rays_and_dimensions(self):
        g = fixture()
        g['mu'][:, 0] = 100.
        raw = render_native(g, camera(31, 47))
        validate_raw(raw, len(g['mu']), (31, 47))
        for key in ('alpha', 'depth', 'median_depth', 'normal', 'topk_w', 'moment2', 'normal_len'):
            self.assertTrue(np.all(raw[key] == 0), key)
        self.assertTrue(np.all(raw['topk_id'] == -1))
        self.assertTrue(np.all(raw['rgb'] == 1))

    def test_04_exact_native_principal_point(self):
        cam = camera(800, 800)
        _, proj = camera_matrices(cam)
        projected = np.array([0., 0., 3., 1.]) @ proj
        ndc = projected[:2] / projected[3]
        np.testing.assert_allclose(((ndc+1)*800-1)/2, [399.5, 399.5], atol=1e-6)
        cam['native_K'][0][2] = 400.
        with self.assertRaises(ValueError):
            camera_matrices(cam)

    def test_05_calibration_rejects_changed_or_nonfinite_buffers(self):
        reference = {k: np.ones((3, 3), np.float32)
                     for k in ('rgb', 'alpha', 'depth', 'normal', 'median_depth')}
        changed = {k: value.copy() for k, value in reference.items()}
        changed['normal'][1, 1] += .01
        self.assertEqual(compare_calibration(changed, reference)['status'], 'ENGINEERING_INVALID')
        changed['normal'][1, 1] = np.nan
        with self.assertRaises(ValueError):
            compare_calibration(changed, reference)

    def test_06_export_validation_rejects_wrong_id_shape_and_mass(self):
        raw = dict(rgb=np.ones((2, 3, 3), np.float32), alpha=np.zeros((2, 3), np.float32),
                   depth=np.zeros((2, 3), np.float32), median_depth=np.zeros((2, 3), np.float32),
                   normal=np.zeros((2, 3, 3), np.float32), radii=np.zeros(2, np.int32),
                   topk_id=np.full((2, 3, 4), -1, np.int32), topk_w=np.zeros((2, 3, 4), np.float32),
                   topk_depth=np.zeros((2, 3, 4), np.float32),
                   topk_normal=np.zeros((2, 3, 4, 3), np.float32),
                   moment2=np.zeros((2, 3), np.float32), normal_len=np.zeros((2, 3), np.float32))
        self.assertTrue(validate_raw(raw, 2, (2, 3)))
        raw['topk_id'][0, 0, 0] = 2
        with self.assertRaises(ValueError):
            validate_raw(raw, 2, (2, 3))
        raw['topk_id'][0, 0, 0] = 1
        raw['topk_w'][0, 0, 0] = .1
        with self.assertRaises(ValueError):
            validate_raw(raw, 2, (2, 3))
        with self.assertRaises(ValueError):
            validate_raw(raw, 2, (3, 2))


if __name__ == '__main__':
    unittest.main()
