"""Engineering RED legacy stencil -> GREEN polygon coverage, outside acceptance fixtures."""
import round010_common
import sys
import unittest
import numpy as np
from scipy import ndimage
import centered_coverage as candidate

LEGACY = '--legacy' in sys.argv
if LEGACY:
    sys.argv.remove('--legacy')


def coverage(p, size=32):
    if not LEGACY:
        return candidate.ribbon_mask(p, size)
    pre = np.zeros((size, size), bool)
    for a, b in zip(np.asarray(p)[:-1], np.asarray(p)[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b-a)/.45)))
        q = np.rint(a+(b-a)*np.linspace(0, 1, n+1)[:, None]).astype(int)
        pre[q[:, 1], q[:, 0]] = True
    return ndimage.maximum_filter(pre, size=2)


class CoverageTests(unittest.TestCase):
    def test_closed_axial_support(self):
        expected = np.zeros((32, 32), bool); expected[15:18, 10:23] = True
        np.testing.assert_array_equal(coverage([[10., 16.], [22., 16.]]), expected)

    def test_oblique_independent_scalar_distance(self):
        a = np.array([6., 8.]); b = np.array([24., 20.]); d = b-a
        expected = np.zeros((32, 32), bool)
        for y in range(32):
            for x in range(32):
                q = np.array([x, y])-a
                expected[y, x] = 0 <= q@d <= d@d and (d[0]*q[1]-d[1]*q[0])**2 <= d@d
        np.testing.assert_array_equal(coverage([a, b]), expected)

    def test_reverse_path(self):
        p = [[6.25, 8.5], [13., 13.], [24.5, 20.25]]
        np.testing.assert_array_equal(coverage(p), coverage(p[::-1]))

    def test_butt_caps(self):
        mask = coverage([[10., 16.], [22., 16.]])
        self.assertFalse(mask[:, :10].any()); self.assertFalse(mask[:, 23:].any())

    def test_collinear_segment_union(self):
        np.testing.assert_array_equal(coverage([[10., 16.], [22., 16.]]),
                                      coverage([[10., 16.], [16., 16.], [22., 16.]]))

    def test_invalid_inputs_rejected(self):
        for p in ([[1., 1.], [1., 1.]], [[np.nan, 0.], [1., 1.]]):
            with self.assertRaises(ValueError): candidate.ribbon_mask(p, 32)
        with self.assertRaises(ValueError): candidate.ribbon_mask([[0., 0.], [1., 1.]], 32, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
