"""Necessary nested stem-density and original-seed provenance contracts.

These are algorithm controls. Actual image change, coverage and readability
are separate unit009 application gates.
"""
import copy
import unittest

from common import OUT, np
from asset_cli import load_asset
from density_cli import select_stem


UNIT = OUT.parent / 'unit_009'


class StemDensityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, _, cls.mesh, cls.original, cls.cfg = load_asset(UNIT / 'inputs/asset.json')

    def assert_stroke_equal(self, actual, expected):
        self.assertEqual(set(actual), set(expected))
        for name in expected:
            if isinstance(expected[name], np.ndarray):
                self.assertEqual(actual[name].dtype, expected[name].dtype)
                self.assertEqual(actual[name].shape, expected[name].shape)
                self.assertEqual(actual[name].tobytes(), expected[name].tobytes())
            else:
                self.assertEqual(actual[name], expected[name])

    def test_density_one_is_no_edit_and_zero_keeps_other_parts(self):
        full, _ = select_stem(self.mesh, self.original, self.cfg, 1.)
        empty, _ = select_stem(self.mesh, self.original, self.cfg, 0.)
        by_id = {stroke['id']: stroke for stroke in self.original}
        self.assertEqual({stroke['id'] for stroke in full}, set(by_id))
        self.assertEqual({stroke['id'] for stroke in empty},
                         {stroke['id'] for stroke in self.original if stroke['part'] != 2})
        for stroke in full:
            self.assert_stroke_equal(stroke, by_id[stroke['id']])
        for stroke in empty:
            self.assert_stroke_equal(stroke, by_id[stroke['id']])

    def test_nested_half_density_preserves_retained_fields_and_input(self):
        supplied = copy.deepcopy(self.original)
        cfg = copy.deepcopy(self.cfg)
        quarter, _ = select_stem(self.mesh, supplied, cfg, .25)
        half, _ = select_stem(self.mesh, supplied, cfg, .5)
        small = {stroke['id'] for stroke in quarter if stroke['part'] == 2}
        large = {stroke['id'] for stroke in half if stroke['part'] == 2}
        self.assertEqual(len(small), 12)
        self.assertEqual(len(large), 24)
        self.assertLess(small, large)
        self.assertEqual({part: sum(stroke['part'] == part for stroke in half)
                          for part in (1, 2, 3)}, {1: 260, 2: 24, 3: 150})
        by_id = {stroke['id']: stroke for stroke in self.original}
        for stroke in half + quarter + supplied:
            self.assert_stroke_equal(stroke, by_id[stroke['id']])
        self.assertEqual(cfg, self.cfg)

    def test_input_order_independence_seed0000_first_and_count_rounding(self):
        forward, _ = select_stem(self.mesh, self.original, self.cfg, .5)
        reverse, _ = select_stem(self.mesh, self.original[::-1], self.cfg, .5)
        self.assertEqual({stroke['id'] for stroke in forward},
                         {stroke['id'] for stroke in reverse})
        first, _ = select_stem(self.mesh, self.original, self.cfg, 1. / 48.)
        self.assertEqual({stroke['id'] for stroke in first if stroke['part'] == 2},
                         {'p2:seed0000:layer0'})
        for density, expected in ((.49 / 48., 0), (.5 / 48., 1), (.51 / 48., 1)):
            with self.subTest(density=density):
                selected, _ = select_stem(self.mesh, self.original, self.cfg, density)
                self.assertEqual(sum(stroke['part'] == 2 for stroke in selected), expected)

    def test_invalid_density_rejected(self):
        for value in (-.01, 1.01, float('nan'), float('inf'), -float('inf'), True, False):
            with self.subTest(value=value), self.assertRaises(ValueError):
                select_stem(self.mesh, self.original, self.cfg, value)

    def test_missing_duplicate_and_corrupt_seed_rejected(self):
        stem = next(stroke for stroke in self.original if stroke['part'] == 2)
        missing = [stroke for stroke in self.original if stroke['id'] != stem['id']]
        duplicate = self.original + [copy.deepcopy(stem)]
        corrupt = copy.deepcopy(self.original)
        changed = next(stroke for stroke in corrupt if stroke['id'] == stem['id'])
        # Still finite, normalized barycentric coordinates; nevertheless these
        # vertex anchors no longer contain the known area-sampled seed.
        changed['bary'][:] = [1., 0., 0.]
        for name, strokes in (('missing', missing), ('duplicate', duplicate),
                              ('wrong_seed_anchor', corrupt)):
            with self.subTest(case=name), self.assertRaises(ValueError):
                select_stem(self.mesh, strokes, self.cfg, .5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
