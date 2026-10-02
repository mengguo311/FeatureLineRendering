"""CPU contracts for one same-traversal export and frozen three-arm readout."""
import copy
import unittest

import numpy as np


def synthetic_raw():
    """Physical blend with omitted top-4 mass and original, noncompact IDs."""
    h, w = 16, 20
    mask = np.zeros((h, w), bool)
    mask[3:13, 3:17] = True
    alpha = mask.astype(np.float32) * .8
    rgb = np.ones((h, w, 3), np.float32)
    color = np.full_like(rgb, .2)
    color[:, 10:] = .7
    rgb[mask] = (color * alpha[..., None] + 1 - alpha[..., None])[mask]
    ids = np.full((h, w, 4), -1, np.int32)
    ids[mask] = [71, 5, 99, 3]
    weights = np.zeros((h, w, 4), np.float32)
    weights[mask] = [.4, .2, .08, .04]
    depths = np.zeros_like(weights)
    depths[mask] = [1, 1.5, 2, 3]
    # Remaining .08 is genuinely outside top4, at z=2.5.
    depth = np.zeros((h, w), np.float32)
    depth[mask] = (np.array([.4, .2, .08, .04]) @ np.array([1, 1.5, 2, 3]) + .08 * 2.5) / .8
    moment2 = np.zeros_like(alpha)
    moment2[mask] = np.array([.4, .2, .08, .04]) @ np.array([1, 1.5, 2, 3]) ** 2 + .08 * 2.5 ** 2
    normal = np.zeros((h, w, 3), np.float32)
    normal[mask, 2] = 1
    top_normal = np.zeros((h, w, 4, 3), np.float32)
    top_normal[mask, :, 2] = 1
    median = np.zeros_like(alpha)
    median[mask] = 1.5
    return dict(rgb=rgb, alpha=alpha, depth=depth, median_depth=median,
                normal=normal, topk_id=ids, topk_w=weights,
                topk_depth=depths, topk_normal=top_normal,
                moment2=moment2, normal_len=alpha.copy(), source_id='synthetic-pass-1')


class HybridRasterEvidenceTests(unittest.TestCase):
    def test_vertical_export_typed_evidence_provenance_and_background(self):
        from src.hybrid_raster_evidence import raw_fields, fit_normalization, compute_evidence, validate_raw
        raw = synthetic_raw()
        saved = copy.deepcopy(raw)
        validate_raw(raw, gaussian_count=100)
        fields = raw_fields(raw)
        self.assertAlmostEqual(float(fields['topk_mass'][5, 5]), .9, places=6)
        self.assertAlmostEqual(float(fields['normalized_topk_w'][5, 5, 0]), .4 / .72, places=6)
        self.assertGreater(float(fields['depth_variance'][5, 5]), 0)
        result = compute_evidence(raw, fit_normalization([fields]))
        a, b, c = [result['arrays'][name] for name in ('A', 'B', 'C')]
        self.assertEqual(a.shape, raw['alpha'].shape)
        self.assertGreater(float(a.sum()), 0)
        self.assertGreater(float(b.sum()), 0)
        np.testing.assert_allclose(c, 1 - (1 - a) * (1 - b), atol=1e-7)
        self.assertTrue(np.all(c[:2] == 0))
        np.testing.assert_array_equal(result['provenance']['shared'], (a > 0) & (b > 0))
        np.testing.assert_allclose(result['provenance']['overlap'], a * b)
        np.testing.assert_allclose(result['arrays']['author_absolute'], fields['S_L'])
        masses = [result['arrays'][name + '_matched'].sum(dtype=np.float64) for name in ('A', 'B', 'C')]
        np.testing.assert_allclose(masses, [min(a.sum(dtype=np.float64), b.sum(dtype=np.float64), c.sum(dtype=np.float64))] * 3, rtol=2e-6)
        for key, value in saved.items():
            if isinstance(value, np.ndarray):
                np.testing.assert_array_equal(raw[key], value)

    def test_empty_rays_produce_no_ink_and_keep_sentinels(self):
        from src.hybrid_raster_evidence import raw_fields, fit_normalization, compute_evidence
        raw = synthetic_raw()
        for key, value in raw.items():
            if isinstance(value, np.ndarray):
                value.fill(-1 if key == 'topk_id' else (1 if key == 'rgb' else 0))
        result = compute_evidence(raw, fit_normalization([raw_fields(raw)]))
        for name in ('A', 'B', 'C', 'A_matched', 'B_matched', 'C_matched', 'author_absolute'):
            self.assertEqual(float(result['arrays'][name].sum()), 0.)
        self.assertEqual(result['diagnostics']['raw']['top4_coverage']['count'], 0)
        self.assertTrue(np.all(result['provenance']['B_argmax'] == -1))
        self.assertTrue(np.all(raw['topk_id'] == -1))

    def test_rejects_nonfinite_raw_before_author_sanitization(self):
        from src.hybrid_raster_evidence import raw_fields
        for field in ('rgb', 'alpha', 'depth', 'median_depth', 'normal', 'topk_w', 'topk_depth', 'topk_normal', 'moment2', 'normal_len'):
            with self.subTest(field=field):
                raw = synthetic_raw()
                raw[field].flat[0] = np.nan
                with self.assertRaisesRegex(ValueError, 'nonfinite'):
                    raw_fields(raw)

    def test_rejects_shapes_source_mixing_and_nonphysical_weights(self):
        from src.hybrid_raster_evidence import validate_raw
        raw = synthetic_raw()
        raw['rgb'] = raw['rgb'][:-1]
        with self.assertRaisesRegex(ValueError, 'shape mismatch'):
            validate_raw(raw)
        raw = synthetic_raw()
        raw['channel_source_ids'] = {key: 'synthetic-pass-1' for key, value in raw.items() if isinstance(value, np.ndarray)}
        validate_raw(raw)
        raw['channel_source_ids']['depth'] = 'other-renderer-pass'
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            validate_raw(raw)
        raw = synthetic_raw()
        raw['topk_w'][5, 5] /= raw['topk_w'][5, 5].sum()
        with self.assertRaisesRegex(ValueError, 'must not be normalized'):
            validate_raw(raw)
        raw = synthetic_raw()
        raw['topk_w'][0, 0, 0] = .1
        with self.assertRaisesRegex(ValueError, 'empty original ID'):
            validate_raw(raw)
        raw = synthetic_raw()
        raw['topk_id'][5, 5, 0] = 100
        with self.assertRaisesRegex(ValueError, 'checkpoint range'):
            validate_raw(raw, gaussian_count=100)

    def test_original_id_global_bijection_does_not_change_typed_evidence(self):
        from src.hybrid_raster_evidence import raw_fields, fit_normalization, compute_evidence
        raw = synthetic_raw()
        # Add an actual source-support boundary; renaming must preserve it.
        raw['topk_id'][3:13, 10:17] = [70, 8, 98, 4]
        renamed = copy.deepcopy(raw)
        valid = renamed['topk_id'] >= 0
        renamed['topk_id'][valid] = 311 + 7 * renamed['topk_id'][valid]
        first, second = raw_fields(raw), raw_fields(renamed)
        self.assertGreater(float(first['delta_G'].max()), 0.)
        for key in first:
            np.testing.assert_array_equal(first[key], second[key], err_msg=key)
        normalization = fit_normalization([first])
        a = compute_evidence(raw, normalization)
        b = compute_evidence(renamed, normalization)
        for key in a['arrays']:
            np.testing.assert_array_equal(a['arrays'][key], b['arrays'][key], err_msg=key)

    def test_overlap_is_invariant_to_support_slot_permutation(self):
        from src.hao_mukai_source_2026 import _overlap
        raw = synthetic_raw()
        ids = raw['topk_id']
        weights = raw['topk_w'] / np.maximum(raw['topk_w'].sum(-1, keepdims=True), 1e-8)
        valid = raw['alpha'] > 0
        expected = _overlap(ids, weights, valid)
        # Slots differ between adjacent pixels, while ID/weight pairs stay linked.
        alternate_ids, alternate_weights = ids.copy(), weights.copy()
        alternate_ids[:, ::2] = alternate_ids[:, ::2, [2, 0, 3, 1]]
        alternate_weights[:, ::2] = alternate_weights[:, ::2, [2, 0, 3, 1]]
        np.testing.assert_allclose(_overlap(alternate_ids, alternate_weights, valid), expected, atol=1e-7)

    def test_complement_nulls_overlap_and_tiny_weak_structure(self):
        from src.hybrid_raster_evidence import fuse_channels
        a = np.array([[0, .3], [1, 0]], np.float32)
        b = np.array([[1e-9, .5], [.8, 0]], np.float32)
        np.testing.assert_array_equal(fuse_channels(a, np.zeros_like(a))[0], a)
        np.testing.assert_array_equal(fuse_channels(np.zeros_like(b), b)[0], b)
        c, provenance = fuse_channels(a, b)
        self.assertEqual(float(c[1, 0]), 1.)
        self.assertGreater(float(c[0, 0]), 0.)
        self.assertTrue(provenance['B_only'][0, 0])
        self.assertTrue(provenance['shared'][0, 1])
        self.assertAlmostEqual(float(c[0, 1]), .65, places=6)
        with self.assertRaisesRegex(ValueError, 'equal HxW'):
            fuse_channels(a, b[:1])

    def test_ink_matching_scales_whole_support_without_topk_deletion(self):
        from src.hybrid_raster_evidence import ink_matched
        arms = dict(A=np.array([[1, 0, 0], [0, 0, 0]], np.float32),
                    B=np.array([[.4, .4, .4], [.01, .2, 0]], np.float32))
        matched, summary = ink_matched(arms)
        for key in arms:
            np.testing.assert_array_equal(matched[key] > 0, arms[key] > 0)
            self.assertAlmostEqual(float(matched[key].sum()), 1, places=6)
            np.testing.assert_allclose(matched[key], arms[key] * summary['gains'][key])
        empty, summary = ink_matched(dict(A=arms['A'], B=np.zeros_like(arms['A'])))
        self.assertEqual(summary['target_mass'], 0)
        self.assertEqual(float(empty['A'].sum()), 0)

    def test_A_preserves_inherited_rgb_and_alpha_detector(self):
        from src.hybrid_raster_evidence import raw_fields, fit_normalization, compute_evidence
        from scripts.hybrid_dense_v1 import image_edges
        raw = synthetic_raw()
        expected_rgb, expected_alpha = image_edges(raw['rgb'], np.zeros_like(raw['alpha']), raw['alpha'])
        result = compute_evidence(raw, fit_normalization([raw_fields(raw)]))
        arrays, foreground = result['arrays'], result['provenance']['foreground']
        np.testing.assert_array_equal(np.maximum(arrays['A_rgb_fine'], arrays['A_rgb_coarse']), (expected_rgb > 0) & foreground)
        np.testing.assert_array_equal(arrays['A_alpha'], (expected_alpha > 0) & foreground)

    def test_depth_response_detects_native_step_and_masks_empty_rays(self):
        from src.hybrid_raster_evidence import depth_evidence
        depth = np.ones((24, 32), np.float32)
        depth[:, 16:] = 2
        alpha = np.ones_like(depth)
        result = depth_evidence(depth, alpha)
        self.assertEqual(result['ink'].shape, depth.shape)
        self.assertGreater(float(result['ink'][:, 14:18].sum()), 0)
        self.assertEqual(float(result['ink'][:, :8].sum()), 0)
        empty = depth_evidence(depth, np.zeros_like(alpha))
        self.assertEqual(float(empty['ink'].sum()), 0)

    def test_f_normalization_frozen_recipe_and_channel_provenance(self):
        from src.hybrid_raster_evidence import CHANNELS, raw_fields, fit_normalization, compute_evidence
        raw = synthetic_raw()
        fields = raw_fields(raw)
        normalization = fit_normalization([fields])
        saved = copy.deepcopy(normalization)
        output = compute_evidence(raw, normalization)
        self.assertEqual(normalization, saved)
        channels = np.stack([output['arrays']['B_' + name] for name in CHANNELS], -1)
        np.testing.assert_array_equal(channels.max(-1), output['arrays']['B'])
        bits = output['provenance']['B_channel_bits']
        for index in range(len(CHANNELS)):
            np.testing.assert_array_equal((bits & (1 << index)) > 0, channels[..., index] > 0)
        # q=0 retains the frozen .35 strength floor, not a hard reliability veto.
        raw['normal_len'].fill(0)
        weak = compute_evidence(raw, normalization)
        self.assertGreater(float(weak['arrays']['B'].sum()), 0.)
        self.assertLessEqual(float(weak['arrays']['B'].max()), .350001)
        normalization['recipe_hash'] = 'wrong-recipe'
        with self.assertRaisesRegex(ValueError, 'recipe hash mismatch'):
            compute_evidence(raw, normalization)


if __name__ == '__main__':
    unittest.main()
