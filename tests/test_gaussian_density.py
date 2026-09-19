"""Analytical checks for the density path; legacy field tests stay unchanged."""
import unittest

import numpy as np

from src.field_visualization import (
    density_pca_frame, evaluate_density_slice, gaussian_density_contributions,
    weighted_quantiles,
)


class GaussianDensityTests(unittest.TestCase):
    def test_weighted_quantiles_are_inverse_empirical_cdf(self):
        np.testing.assert_array_equal(
            weighted_quantiles([9, 1, 5, 100], [1, 1, 2, 0], [0, .25, .5, .75, 1]),
            [1, 1, 5, 5, 9])
        for weights in ([0, 0], [1, -1]):
            with self.assertRaises(ValueError):
                weighted_quantiles([1, 2], weights, [.5])

    def test_weighted_global_pca_has_deterministic_right_handed_axes(self):
        points = np.array([[3., 0, 0], [-3, 0, 0], [0, 2, 0],
                           [0, -2, 0], [0, 0, 1], [0, 0, -1]])
        center, basis, coords = density_pca_frame(points, np.ones(6))
        np.testing.assert_allclose(center, 0, atol=1e-15)
        np.testing.assert_allclose(basis, np.eye(3), atol=1e-15)
        np.testing.assert_allclose(coords, points, atol=1e-15)
        shifted = density_pca_frame(points + [4, 5, 6], np.ones(6))
        np.testing.assert_allclose(shifted[2], coords, atol=1e-14)
        self.assertAlmostEqual(np.linalg.det(basis), 1.)
        weighted = density_pca_frame(points, np.arange(1, 7))
        np.testing.assert_allclose(weighted[0], np.average(points, axis=0, weights=np.arange(1, 7)))

    def test_analytic_peak_determinant_and_unbounded_occupancy(self):
        means = np.zeros((2, 3)); logs = np.log([[2., 3., 4.], [2., 3., 4.]])
        q = np.tile([1., 0, 0, 0], (2, 1)); alpha = np.array([.8, .7])
        occ, pdf = gaussian_density_contributions([[0, 0, 0], [2, 0, 0]], means, logs, q, alpha)
        np.testing.assert_allclose(occ.sum(1), [1.5, 1.5*np.exp(-.5)])
        np.testing.assert_allclose(pdf, occ / ((2*np.pi)**1.5 * 24))

    def test_thin_rotated_kernel_is_not_pseudoinverse_regularized(self):
        q = [[np.cos(np.pi/8), 0, 0, np.sin(np.pi/8)]]
        # Local X is extremely thin; offset along that rotated axis is 2 sigma.
        x = 2e-9 / np.sqrt(2)
        occ, pdf = gaussian_density_contributions([[x, x, 0]], [[0, 0, 0]],
                                                   np.log([[1e-9, 2, 3]]), q, [.4])
        np.testing.assert_allclose(occ, [[.4*np.exp(-2)]], rtol=1e-12)
        np.testing.assert_allclose(pdf/occ, [[1/((2*np.pi)**1.5*6e-9)]])

    def test_distant_kernel_has_no_artificial_exponent_floor(self):
        occ, pdf = gaussian_density_contributions([[20., 0, 0]], [[0, 0, 0]],
                                                   np.zeros((1, 3)), [[1, 0, 0, 0]], [1])
        self.assertAlmostEqual(float(occ[0, 0] / np.exp(-200)), 1.)
        self.assertLess(float(pdf[0, 0]), 1e-80)

    def test_slice_matches_brute_force_rotated_anisotropic_kernels(self):
        rng = np.random.default_rng(1729)
        means = rng.normal(size=(30, 3))
        logs = rng.uniform(-2, .3, (30, 3)); q = rng.normal(size=(30, 4))
        alpha = rng.uniform(.01, .9, 30)
        _, frame, _ = density_pca_frame(means, alpha)
        basis = frame[:, :2]; origin = np.array([.2, -.1, .3])
        u = np.linspace(-3, 3, 31); v = np.linspace(-2, 2, 27)
        uu, vv = np.meshgrid(u, v)
        points = (origin + uu[..., None]*basis[:, 0] + vv[..., None]*basis[:, 1]).reshape(-1, 3)
        occ, pdf = gaussian_density_contributions(points, means, logs, q, alpha)
        # A small radius deliberately exercises tails, plane and footprint culling.
        keep = occ / alpha >= np.exp(-.5*3**2)
        result = evaluate_density_slice(means, logs, q, alpha, origin, basis, u, v, radius=3)
        np.testing.assert_allclose(result['occupancy'].ravel(), (occ*keep).sum(1), atol=2e-14)
        np.testing.assert_allclose(result['pdf'].ravel(), (pdf*keep).sum(1), atol=2e-14)
        for name, exact in [('occupancy', occ), ('pdf', pdf)]:
            error = exact.sum(1) - result[name].ravel()
            self.assertLessEqual(float(error.max()), result['tail_bounds'][name] + 1e-14)
        again = evaluate_density_slice(means, logs, q, alpha, origin, basis, u, v, radius=3)
        np.testing.assert_array_equal(again['pdf'], result['pdf'])

    def test_slice_plane_culling_and_grid_boundary(self):
        means = np.array([[0., 0, 0], [0, 0, 10], [100, 0, 0]])
        result = evaluate_density_slice(means, np.zeros((3, 3)),
                                        np.tile([1, 0, 0, 0], (3, 1)), np.ones(3),
                                        np.zeros(3), np.eye(3)[:, :2], [-3., 0, 3], [-1., 0, 1], radius=3)
        np.testing.assert_array_equal(result['plane_indices'], [0, 2])
        np.testing.assert_array_equal(result['grid_indices'], [0])
        self.assertAlmostEqual(result['occupancy'][1, 0], np.exp(-4.5))
        self.assertAlmostEqual(result['occupancy'][1, 1], 1.)

    def test_slice_retains_extremely_thin_rotated_support(self):
        u = np.linspace(-1, 1, 11)
        result = evaluate_density_slice([[0, 0, 0]], np.log([[1e-8, 2, 3]]),
                                        [[np.cos(np.pi/8), 0, 0, np.sin(np.pi/8)]], [.8],
                                        np.zeros(3), np.eye(3)[:, :2], u, u)
        uu, vv = np.meshgrid(u, u)
        occ, pdf = gaussian_density_contributions(np.c_[uu.ravel(), vv.ravel(), np.zeros(uu.size)],
                                                  [[0, 0, 0]], np.log([[1e-8, 2, 3]]),
                                                  [[np.cos(np.pi/8), 0, 0, np.sin(np.pi/8)]], [.8])
        np.testing.assert_allclose(result['occupancy'].ravel(), occ[:, 0], atol=1e-14)
        np.testing.assert_allclose(result['pdf'].ravel(), pdf[:, 0], rtol=1e-12, atol=1e-12)

    def test_empty_slice_and_invalid_parameters(self):
        args = (np.empty((0, 3)), np.empty((0, 3)), np.empty((0, 4)), np.empty(0),
                np.zeros(3), np.eye(3)[:, :2], [-1, 1], [-1, 1])
        result = evaluate_density_slice(*args)
        np.testing.assert_array_equal(result['pdf'], np.zeros((2, 2)))
        with self.assertRaises(ValueError):
            evaluate_density_slice(*args, radius=-1)
        bad_basis = list(args); bad_basis[5] = np.ones((3, 2))
        with self.assertRaises(ValueError):
            evaluate_density_slice(*bad_basis)


if __name__ == '__main__':
    unittest.main()
