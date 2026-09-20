"""Preregistered tests written before density_ridge_lines implementation."""
import unittest
import numpy as np
from scipy.ndimage import gaussian_filter
from src.density_ridge_lines import (
    adaptive_kde, axial_tensor, ridge_response, pooled_select, clean_mask, mask_metrics,
)


class DensityRidgeTests(unittest.TestCase):
    def test_kde_preserves_mass_and_constant_attributes(self):
        rng = np.random.default_rng(1729)
        xy = rng.uniform(24, 104, (300, 2))
        values = np.tile([0.25, 0.8], (len(xy), 1))
        kde = adaptive_kde(xy, values, (128, 128))
        self.assertAlmostEqual(kde['density'].sum(), len(xy), places=9)
        ok = kde['density'] > 1e-12
        np.testing.assert_allclose(kde['normalized'][ok], values[:1].repeat(ok.sum(), axis=0), atol=1e-12)
        np.testing.assert_allclose(kde['numerator'].sum(axis=(0, 1)), values.sum(axis=0), atol=1e-9)
        self.assertTrue(np.all(np.isin(kde['bandwidth'], [1, np.sqrt(2), 2, np.sqrt(8), 4])))

    def test_axial_tensor_kde_is_independently_sign_invariant(self):
        rng = np.random.default_rng(18)
        n = rng.normal(size=(80, 3)); n /= np.linalg.norm(n, axis=1)[:, None]
        signs = rng.choice([-1, 1], (80, 1))
        np.testing.assert_array_equal(axial_tensor(n), axial_tensor(n * signs))
        xy = rng.uniform(20, 44, (80, 2))
        a = adaptive_kde(xy, axial_tensor(n).reshape(-1, 9), (64, 64))
        b = adaptive_kde(xy, axial_tensor(n * signs).reshape(-1, 9), (64, 64))
        np.testing.assert_array_equal(a['normalized'], b['normalized'])
        valid = a['density'] > 1e-8
        t = a['normalized'][valid].reshape(-1, 3, 3)
        np.testing.assert_allclose(np.trace(t, axis1=1, axis2=2), 1, atol=1e-12)
        self.assertGreaterEqual(np.linalg.eigvalsh(t).min(), -1e-12)

    def test_hessian_prefers_broad_curve_to_blob_and_noise(self):
        y, x = np.mgrid[:160, :160]
        center = 80 + 12 * np.sin(x / 30)
        curve = np.exp(-0.5 * ((y-center)/3)**2)
        blob = np.exp(-0.5 * (((x-80)/3)**2 + ((y-80)/3)**2))
        noise = gaussian_filter(np.random.default_rng(1729).normal(0, .08, (160, 160)), 1)
        r = ridge_response(curve)
        rb = ridge_response(blob)['response']
        rn = ridge_response(noise)['response']
        middle = (x > 15) & (x < 145) & (np.abs(y-center) < 1)
        self.assertGreater(np.median(r['response'][middle]), 0.15)
        self.assertLess(rb[80, 80], 1e-8)
        self.assertGreater(np.median(r['response'][middle]), 5 * np.quantile(rn, .99))
        self.assertGreater(np.count_nonzero(r['seed_score'][middle]), 80)
        inverted = ridge_response(-curve)['response']
        self.assertLess(np.median(inverted[middle]), 1e-8)

    def test_pooled_selection_exact_deterministic_and_global(self):
        scores = [np.array([[4., 4., 1.], [0., 0., 2.]]), np.array([[4., 3., 2.]])]
        support = [np.ones_like(a, dtype=bool) for a in scores]
        masks, meta = pooled_select(scores, support, 4)
        self.assertEqual(sum(m.sum() for m in masks), 4)
        np.testing.assert_array_equal(masks[0], [[1, 1, 0], [0, 0, 0]])
        np.testing.assert_array_equal(masks[1], [[1, 1, 0]])
        again, _ = pooled_select(scores, support, 4)
        for a, b in zip(masks, again): np.testing.assert_array_equal(a, b)
        self.assertEqual(meta['threshold'], 3.)
        ties, _ = pooled_select(scores, support, 2)
        self.assertEqual(ties[0].sum(), 2)
        self.assertEqual(ties[1].sum(), 0)
        empty, _ = pooled_select(scores, support, 0)
        self.assertEqual(sum(m.sum() for m in empty), 0)
        # Baseline can differ in shape/ranking, but exact pooled visible area matches.
        matched, _ = pooled_select([a[::-1] for a in scores], support, sum(m.sum() for m in masks))
        self.assertEqual(sum(m.sum() for m in matched), 4)

    def test_cleanup_preserves_broad_curves_and_removes_specks(self):
        y, x = np.mgrid[:128, :128]
        curve = (np.abs(y-(64+8*np.sin(x/20))) <= 1.5) & (x > 10) & (x < 118)
        dirty = curve.copy(); dirty[5:7, 5:7] = True; dirty[110, 110] = True
        clean = clean_mask(dirty)
        np.testing.assert_array_equal(clean, curve)
        metrics = mask_metrics(clean, np.ones_like(clean))
        self.assertEqual(metrics['components'], 1)
        self.assertEqual(metrics['fragments'], 0)
        self.assertEqual(metrics['long_component_fraction'], 1.)
        self.assertGreater(metrics['median_width_px'], 2.)


if __name__ == '__main__':
    unittest.main()
