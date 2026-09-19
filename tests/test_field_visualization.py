import unittest
import numpy as np
from src.field_visualization import (
    quaternion_to_matrix, gaussian_candidate_normals,
    axial_rgb, local_surface_metrics, evaluate_gaussian_slice,
)


class FieldVisualizationTests(unittest.TestCase):
    def test_identity_quaternion_uses_smallest_scale_axis(self):
        q = np.array([[1.0, 0.0, 0.0, 0.0]])  # Graphdeco wxyz
        log_s = np.log(np.array([[3.0, 2.0, 0.25]]))
        n, scales = gaussian_candidate_normals(log_s, q)
        np.testing.assert_allclose(scales, [[3.0, 2.0, 0.25]], rtol=1e-7)
        np.testing.assert_allclose(np.abs(n), [[0.0, 0.0, 1.0]], atol=1e-7)

    def test_quaternion_rotation_is_orthonormal(self):
        q = np.array([[2.0, 1.0, -3.0, 0.5]])
        R = quaternion_to_matrix(q)[0]
        np.testing.assert_allclose(R.T @ R, np.eye(3), atol=1e-7)
        self.assertGreater(np.linalg.det(R), 0.999999)

    def test_axial_rgb_is_sign_invariant(self):
        n = np.array([[1.0, -2.0, 2.0]])
        np.testing.assert_allclose(axial_rgb(n), axial_rgb(-n), atol=0)
        np.testing.assert_allclose(axial_rgb(n), [[1/3, 2/3, 2/3]], atol=1e-7)

    def test_planar_neighborhood_has_high_planarity_and_agreement(self):
        xs, ys = np.meshgrid(np.linspace(-1, 1, 7), np.linspace(-1, 1, 7))
        p = np.c_[xs.ravel(), ys.ravel(), np.zeros(xs.size)]
        n = np.tile([0.0, 0.0, 1.0], (len(p), 1))
        idx = np.arange(len(p))
        # All 49 points form an isotropic square plane, so global-neighborhood
        # PCA has two equal tangent eigenvalues and one zero normal eigenvalue.
        m = local_surface_metrics(p, n, idx, k=49)
        self.assertGreater(np.median(m['planarity']), 0.99)
        self.assertGreater(np.median(m['axis_agreement']), 0.99)

    def test_slice_field_peaks_at_gaussian_center(self):
        means = np.array([[0.0, 0.0, 0.0]])
        cov = np.array([np.diag([0.1, 0.2, 0.3]) ** 2])
        weights = np.array([0.8])
        u = np.linspace(-0.5, 0.5, 41)
        v = np.linspace(-0.5, 0.5, 41)
        field = evaluate_gaussian_slice(means, cov, weights, np.zeros(3), np.eye(3)[:, :2], u, v)
        peak = np.unravel_index(np.argmax(field), field.shape)
        self.assertEqual(peak, (20, 20))
        self.assertAlmostEqual(field[peak], 0.8, places=6)


if __name__ == '__main__':
    unittest.main()
