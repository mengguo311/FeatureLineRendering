"""Frozen threshold-only experiment tests, written before implementation."""
import unittest
from pathlib import Path

import numpy as np

from src.density_ridge_lines import CHANNELS, clean_mask
from src.density_ridge_threshold_sweep import BUDGETS, SCENES, select_sweep, assert_nested


class ThresholdSweepTests(unittest.TestCase):
    def test_exact_pooled_budget_and_stable_scene_row_major_ties(self):
        scores = [np.ones((10, 10)) for _ in SCENES]
        supports = [np.ones((10, 10), bool) for _ in SCENES]
        supports[0][0, 0] = False
        raw, clean, meta = select_sweep(scores, supports)
        valid = np.concatenate([s.ravel() for s in supports])
        for b, budget in enumerate(BUDGETS):
            expected = np.zeros(400, bool)
            count = int(budget * 399)
            expected[np.flatnonzero(valid)[:count]] = True
            np.testing.assert_array_equal(np.concatenate([m[b].ravel() for m in raw]), expected)
            self.assertEqual(meta[b]['requested'], count)
            self.assertEqual(meta[b]['selected'], count)
            self.assertEqual(meta[b]['threshold'], 1.)
        for r, c in zip(raw, clean):
            assert_nested(r)
            assert_nested(c)

    def test_positive_candidates_cap_not_zero_score_fill(self):
        scores = [np.zeros((10, 10)) for _ in SCENES]
        scores[2][0, :3] = [3, 2, 1]
        supports = [np.ones((10, 10), bool) for _ in SCENES]
        raw, clean, meta = select_sweep(scores, supports)
        for b in range(4):
            self.assertEqual(meta[b]['selected'], 3)
            self.assertEqual(meta[b]['positive_candidates'], 3)
            self.assertEqual(sum(m[b].sum() for m in clean), 0)

    def test_stable_nesting_all_budgets_with_ties_and_masked_scores(self):
        rng = np.random.default_rng(1729)
        scores = [rng.integers(0, 8, (31, 43)).astype(float) for _ in SCENES]
        supports = [rng.random((31, 43)) > .2 for _ in SCENES]
        first = select_sweep(scores, supports)
        second = select_sweep(scores, supports)
        for stage in (0, 1):
            for a, b in zip(first[stage], second[stage]):
                np.testing.assert_array_equal(a, b)
                assert_nested(a)
        for r, c, s in zip(first[0], first[1], supports):
            self.assertFalse((c & ~r).any())
            self.assertFalse((r & ~s).any())

    def test_cleanup_8_connected_boundary_and_monotonic_merges(self):
        a = np.zeros((30, 30), bool)
        a[np.arange(12), np.arange(12)] = True  # diagonal area 12 survives
        a[20, :11] = True  # area 11 removed
        b = a.copy(); b[20, 11] = True  # grows to area 12
        c = b.copy(); c[12:20, 11] = True  # joins components
        np.testing.assert_array_equal(clean_mask(a)[:12, :12], a[:12, :12])
        self.assertEqual(clean_mask(a).sum(), 12)
        self.assertEqual(clean_mask(b).sum(), 24)
        assert_nested(np.stack([clean_mask(m) for m in (a, b, c)]))

    def test_nesting_violation_fails(self):
        with self.assertRaises(AssertionError):
            assert_nested(np.array([[[True, False]], [[False, True]]]))

    def test_saved_six_percent_reproduction_before_baseline_matching(self):
        root = Path('out/density_ridge_lines')
        if not all((root / f'{s}_ridge_grids.npz').exists() for s in SCENES):
            self.skipTest('Verified source grids are required for integration reproduction')
        arrays = []
        for s in SCENES:
            with np.load(root / f'{s}_ridge_grids.npz', allow_pickle=False) as a:
                arrays.append({k: a[k] for k in ('support', 'ridge_scores', 'ridge_raw',
                                               'ridge_cleaned_unmatched')})
        for ch in range(len(CHANNELS)):
            raw, clean, meta = select_sweep([a['ridge_scores'][ch] for a in arrays],
                                             [a['support'] for a in arrays])
            self.assertEqual(meta[0]['selected'], meta[0]['requested'])
            for a, r, c in zip(arrays, raw, clean):
                np.testing.assert_array_equal(r[0], a['ridge_raw'][ch])
                np.testing.assert_array_equal(c[0], a['ridge_cleaned_unmatched'][ch])


if __name__ == '__main__':
    unittest.main()
