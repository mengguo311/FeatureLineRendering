"""Toy regressions frozen before the temporal audit implementation/evaluation."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '2'
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
import argparse
import unittest
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--backend', choices=['broken', 'new'], default='new')
args, rest = parser.parse_known_args()

if args.backend == 'new':
    import temporal_audit as impl
else:
    class Broken:
        @staticmethod
        def match_support(uv, pixels):
            # Simulates the forbidden coordinate-only metric and silent missing.
            return np.zeros(len(uv)), np.zeros_like(uv)
        @staticmethod
        def shift_image(a, dx, dy):
            return np.roll(a, (dy, dx), axis=(0, 1))
    impl = Broken()


class TemporalTests(unittest.TestCase):
    def test_drift_is_measured_from_actual_support(self):
        uv = np.array([[4., 4.], [4., 5.], [4., 6.]])
        d, offset = impl.match_support(uv, uv + [6., 0.])
        np.testing.assert_allclose(d, 6.)
        np.testing.assert_allclose(offset, np.tile([6., 0.], (3, 1)))

    def test_missing_same_id_not_replaced_by_other_ink(self):
        d, offset = impl.match_support(np.array([[4., 4.]]), np.empty((0, 2)))
        self.assertTrue(np.isinf(d[0]))
        self.assertTrue(np.isnan(offset).all())

    def test_injection_does_not_wrap(self):
        a = np.zeros((8, 8), dtype=np.uint8); a[1, 7] = 200
        self.assertEqual(int(impl.shift_image(a, 2, 0).sum()), 0)

    @unittest.skipIf(args.backend == 'broken', 'New instrumented raster primitive')
    def test_local_layer_matches_full_canvas(self):
        from PIL import Image
        from scipy import ndimage
        rng = np.random.default_rng(17)
        for q in (np.array([[0, 0], [127, 127], [40, 46]]),
                  rng.integers(24, 60, size=(40, 2)), np.empty((0, 2), int)):
            parts = np.ones((128, 128), int); parts[:, :2] = 0
            a = np.zeros((128, 128));
            if len(q): a[q[:, 1], q[:, 0]] = .731
            a = ndimage.maximum_filter(a, size=2); a[parts == 0] = 0
            expected = np.asarray(Image.fromarray(np.uint8(a * 255)).resize((64, 64), Image.Resampling.LANCZOS))
            x0, y0, crop, _ = impl.layer_crop(q, .731, parts, 2, 2)
            observed = np.zeros((64, 64), np.uint8)
            observed[y0:y0+crop.shape[0], x0:x0+crop.shape[1]] = crop
            np.testing.assert_array_equal(observed, expected)

    @unittest.skipIf(args.backend == 'broken', 'New independent analytic primitive')
    def test_exact_rays_front_back_and_inside(self):
        c = {'R':np.eye(3), 'eye':np.array([0., .5, -3.]),
             'center':np.array([0.,0.]), 'focal':1.}
        asset = {'profiles_ry':{'1': [[1, 0], [1, 1]]}}
        depth, part = impl.analytic_rays(asset, c, np.array([[0.,0.], [2.,0.]]))
        self.assertAlmostEqual(depth[0], 2.)
        self.assertEqual(part.tolist(), [1, 0])
        self.assertTrue(np.isinf(depth[1]))


if __name__ == '__main__':
    unittest.main(argv=['test_temporal_audit.py'] + rest, verbosity=2)
