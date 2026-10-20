import unittest
import numpy as np
from cpu_partfield_probe import normalize_full_cloud, fixed_source_subset


class PartfieldCpuTests(unittest.TestCase):
    def test_full_cloud_normalization_matches_official(self):
        p = np.array([[0., 0., -2.], [2., 4., 2.], [1., 2., 0.]], dtype='f4')
        n = normalize_full_cloud(p)
        np.testing.assert_allclose(n[0], [-.45, -.9, -.9], atol=1e-6)
        np.testing.assert_allclose(n[-1], [0., 0., 0.], atol=1e-6)

    def test_subset_keeps_unique_original_row_ids(self):
        first = fixed_source_subset(284835, 8192)
        second = fixed_source_subset(284835, 8192)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(first.size, 8192)
        self.assertEqual(np.unique(first).size, first.size)
        self.assertTrue(np.all(first[:-1] < first[1:]))
        self.assertGreaterEqual(first.min(), 0)
        self.assertLess(first.max(), 284835)


if __name__ == '__main__':
    unittest.main()
