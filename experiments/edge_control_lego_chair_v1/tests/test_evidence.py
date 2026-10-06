"""CPU fixtures for fixed RGB/alpha evidence and boundary-normal widths."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evidence import build_evidence, profile_metrics, srgb_to_linear


def encode(linear):
    return np.where(linear <= 0.0031308, 12.92 * linear,
                    1.055 * np.maximum(linear, 0) ** (1 / 2.4) - 0.055)


def edge_fixture(shape=(160, 176), normal=(0.8, 0.6), k=1.25):
    yy, xx = np.indices(shape, dtype=np.float64)
    center = np.array([shape[1] / 2, shape[0] / 2])
    dist = (xx - center[0]) * normal[0] + (yy - center[1]) * normal[1]
    u = 1 / (1 + np.exp(-dist / k))
    linear = np.stack([0.08 + 0.65 * u, 0.12 + 0.45 * u,
                       0.15 + 0.30 * u], axis=-1)
    return encode(linear).astype(np.float32), center


def profile(center, normal=(0.8, 0.6)):
    return {"id": "analytic", "center": list(center), "normal": list(normal),
            "radius": 12.0, "samples": 97, "kind": "internal"}


class EvidenceTest(unittest.TestCase):
    def test_exact_srgb_conversion(self):
        values = np.array([0.0, 0.04045, 0.5, 1.0])
        np.testing.assert_allclose(srgb_to_linear(values),
                                   [0.0, 0.00313080495, 0.21404114048, 1.0], atol=1e-10)

    def test_oblique_width_is_in_linear_profile_encoding(self):
        rgb, center = edge_fixture()
        metric = profile_metrics(rgb, [profile(center)])[0]
        self.assertTrue(metric["valid"], metric)
        self.assertAlmostEqual(metric["width"], 2 * np.log(9) * 1.25, delta=0.25)
        self.assertEqual(metric["encoding"], "display_sRGB_to_linear_RGB")
        self.assertAlmostEqual(metric["contrast"], np.sqrt((0.65**2 + 0.45**2 + 0.30**2) / 3), delta=0.003)

    def test_circle_normals_and_width(self):
        shape = (192, 192)
        yy, xx = np.indices(shape, dtype=np.float64)
        dist = np.hypot(xx - 96, yy - 96) - 48
        u = 1 / (1 + np.exp(-dist / 1.0))
        rgb = encode(np.repeat((0.1 + 0.7 * u)[..., None], 3, axis=2))
        evidence = build_evidence(rgb.astype(np.float32), np.ones(shape, np.float32))
        self.assertGreaterEqual(len(evidence["profiles"]), 12)
        metrics = profile_metrics(rgb, evidence["profiles"])
        valid = [m for m in metrics if m["valid"]]
        self.assertGreaterEqual(len(valid), 12)
        self.assertAlmostEqual(np.median([m["width"] for m in valid]), 2 * np.log(9), delta=0.4)
        for p in evidence["profiles"]:
            radial = np.array(p["center"]) - 96
            radial /= np.linalg.norm(radial)
            self.assertGreater(abs(np.dot(radial, p["normal"])), 0.98)

    def test_low_contrast_is_null_not_zero_width(self):
        rgb, center = edge_fixture()
        rgb = np.full_like(rgb, 0.3) + (rgb - 0.3) * 0.005
        metric = profile_metrics(rgb, [profile(center)])[0]
        self.assertFalse(metric["valid"])
        self.assertIsNone(metric["width"])
        self.assertEqual(metric["reason"], "low_contrast")
        evidence = build_evidence(rgb, np.ones(rgb.shape[:2], np.float32))
        self.assertEqual(len(evidence["profiles"]), 0)
        self.assertEqual(np.count_nonzero(evidence["internal_band"]), 0)

    def test_texture_and_nonmonotonic_are_rejected(self):
        rgb, center = edge_fixture(normal=(1, 0))
        xx = np.arange(rgb.shape[1])[None, :]
        linear = srgb_to_linear(rgb)
        linear += 0.11 * np.exp(-((xx - center[0]) / 8)**2)[..., None] * np.sin((xx - center[0]) * 2)[..., None]
        metric = profile_metrics(encode(linear), [profile(center, (1, 0))])[0]
        self.assertFalse(metric["valid"])
        self.assertIsNone(metric["width"])
        self.assertIn(metric["reason"], {"nonmonotonic_texture", "off_axis_color_texture", "multiple_transitions"})

    def test_two_separated_monotone_transitions_are_not_one_width(self):
        yy, xx = np.indices((96, 112), dtype=np.float64)
        d = xx - 56
        u = 0.5 / (1 + np.exp(-(d + 4) / 0.6)) + 0.5 / (1 + np.exp(-(d - 4) / 0.6))
        rgb = encode(np.repeat((0.1 + 0.7 * u)[..., None], 3, axis=2))
        metric = profile_metrics(rgb, [profile([56, 48], (1, 0))])[0]
        self.assertFalse(metric["valid"])
        self.assertIsNone(metric["width"])
        self.assertEqual(metric["reason"], "multiple_transitions")

    def test_internal_rgb_and_alpha_outline_remain_distinct(self):
        shape = (128, 160)
        yy, xx = np.indices(shape, dtype=np.float64)
        alpha = np.clip((48 - np.hypot(xx - 80, yy - 64)) / 1.5 + 0.5, 0, 1)
        rgb = np.repeat((0.15 + 0.6 / (1 + np.exp(-(xx - 80) / 1.1)))[..., None], 3, axis=2)
        rgb = alpha[..., None] * rgb + (1 - alpha[..., None])
        evidence = build_evidence(rgb.astype(np.float32), alpha.astype(np.float32))
        self.assertGreater(evidence["internal_band"].sum(), 50)
        self.assertGreater(evidence["outline_band"].sum(), 100)
        self.assertEqual(np.count_nonzero((evidence["internal_band"] > 0) & (evidence["outline_band"] > 0.01)), 0)
        np.testing.assert_array_equal(evidence["foreground"], alpha.astype(np.float32))
        self.assertTrue(np.all(evidence["reliable"] == (alpha >= 0.995)))
        np.testing.assert_allclose(evidence["nonband"],
                                   1 - np.maximum(evidence["internal_band"], evidence["outline_band"]), atol=1e-7)

    def test_multichannel_normals_detect_isoluminant_edge(self):
        # Opposite R/G changes cancel the Rec.709 luminance exactly.
        yy, xx = np.indices((128, 144), dtype=np.float64)
        u = 1 / (1 + np.exp(-(xx - 72) / 1.2))
        rgb = np.stack([0.15 + 0.7 * u, 0.65 - 0.7 * (0.2126 / 0.7152) * u,
                        np.full_like(u, 0.25)], axis=-1)
        evidence = build_evidence(rgb.astype(np.float32), np.ones(u.shape, np.float32))
        self.assertGreater(evidence["internal_band"].sum(), 100)
        self.assertGreater(len(evidence["profiles"]), 0)

    def test_maps_are_fixed_balanced_and_inputs_unmodified(self):
        rgb, _ = edge_fixture()
        alpha = np.ones(rgb.shape[:2], np.float32)
        original_rgb, original_alpha = rgb.copy(), alpha.copy()
        first, second = build_evidence(rgb, alpha), build_evidence(rgb, alpha)
        np.testing.assert_array_equal(rgb, original_rgb)
        np.testing.assert_array_equal(alpha, original_alpha)
        self.assertEqual(first["profiles"], second["profiles"])
        self.assertLessEqual(len(first["profiles"]), 96)
        for key in ("internal_band", "outline_band", "foreground", "nonband"):
            self.assertEqual(first[key].shape, alpha.shape)
            self.assertEqual(first[key].dtype, np.float32)
            self.assertTrue(np.isfinite(first[key]).all())
            np.testing.assert_array_equal(first[key], second[key])
        self.assertEqual(len(first["balanced_maps"]), 3)
        for balanced in first["balanced_maps"]:
            self.assertAlmostEqual(float(balanced.sum()), 1.0, places=5)
        x0, y0, x1, y1 = first["roi"]
        self.assertTrue(0 <= x0 < x1 <= rgb.shape[1] and 0 <= y0 < y1 <= rgb.shape[0])

    def test_different_size_segments_have_equal_balanced_mass(self):
        yy, xx = np.indices((192, 256), dtype=np.float64)
        left = 1 / (1 + np.exp((np.hypot(xx - 60, yy - 96) - 18) / 1.1))
        right = 1 / (1 + np.exp((np.hypot(xx - 176, yy - 96) - 34) / 1.1))
        rgb = encode(np.repeat((0.1 + 0.7 * (left + right))[..., None], 3, axis=2))
        evidence = build_evidence(rgb.astype(np.float32), np.ones((192, 256), np.float32))
        for balanced in evidence["balanced_maps"]:
            # Two disconnected circle edges have unequal circumference; each
            # must have half the statistic's mass, rather than pixel-count mass.
            self.assertAlmostEqual(float(balanced[:, :112].sum()), 0.5, places=4)
            self.assertAlmostEqual(float(balanced[:, 112:].sum()), 0.5, places=4)


if __name__ == "__main__":
    unittest.main()
