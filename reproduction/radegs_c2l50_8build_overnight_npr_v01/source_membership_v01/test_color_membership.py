import unittest
import numpy as np
from source_membership import color_reweight, effective_sampling_weight


class ColorMembershipTests(unittest.TestCase):
    def test_color_evidence_retains_visibility_mass_and_favors_nearer_source_color(self):
        weights = np.array([0.2, 0.3, 0.1])
        colors = np.array([[1., 0., 0.], [0., 0., 1.], [0., 0., 1.]])
        target = np.array([0.8, 0., 0.2])
        out = color_reweight(weights, colors, target, sigma=0.3)
        self.assertTrue(np.isclose(out.sum(), weights.sum()))
        self.assertGreater(out[0] / out[1], weights[0] / weights[1])
        self.assertTrue(np.isclose(out[1] / out[2], weights[1] / weights[2]))

    def test_color_evidence_preserves_identical_colors_and_zero_mass(self):
        colors = np.ones((2, 3)) * 0.4
        np.testing.assert_array_equal(color_reweight(np.array([0.2, 0.3]), colors, np.zeros(3), sigma=0.3), np.array([0.2, 0.3]))
        np.testing.assert_array_equal(color_reweight(np.zeros(2), colors, np.zeros(3), sigma=0.3), np.zeros(2))

    def test_color_evidence_rejects_invalid_sigma(self):
        with self.assertRaises(ValueError):
            color_reweight(np.array([0.2]), np.ones((1, 3)), np.ones(3), sigma=0.)

    def test_color_evidence_rejects_nonfinite_inputs(self):
        with self.assertRaises(ValueError):
            color_reweight(np.array([np.nan]), np.ones((1, 3)), np.ones(3), sigma=0.25)
        with self.assertRaises(ValueError):
            color_reweight(np.array([0.1]), np.ones((1, 3)) * np.inf, np.ones(3), sigma=0.25)

    def test_sampling_weight_normalization_is_replayable(self):
        self.assertAlmostEqual(effective_sampling_weight(1.6, 6144, 768), 0.2)
        with self.assertRaises(ValueError):
            effective_sampling_weight(1.6, 0, 768)


if __name__ == '__main__':
    unittest.main()
