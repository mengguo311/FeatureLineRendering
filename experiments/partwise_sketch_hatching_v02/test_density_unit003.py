"""Necessary paired editing contracts on the actual inherited lamp paths."""
from common import *
from base_density import select_base_pairs
import unittest


class PairSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mesh, cls.strokes, cls.cfg = load_inputs()

    def test_pairs_nested_permutation_and_non_target_preservation(self):
        small, info = select_base_pairs(self.mesh, self.strokes, self.cfg, 75)
        large, larger = select_base_pairs(self.mesh, self.strokes, self.cfg, 100)
        reverse, again = select_base_pairs(self.mesh, self.strokes[::-1], self.cfg, 75)
        self.assertEqual(info['selected_pair_ids'], again['selected_pair_ids'])
        self.assertTrue(set(info['selected_pair_ids']) < set(larger['selected_pair_ids']))
        self.assertEqual(sum(s['part'] == 3 for s in small), 150)
        self.assertEqual(core.stroke_digest([s for s in small if s['part'] != 3]),
                         core.stroke_digest([s for s in self.strokes if s['part'] != 3]))
        self.assertEqual({s['id'] for s in small}, {s['id'] for s in reverse})
        for pair in info['selected_pair_ids']:
            self.assertEqual({s['id'] for s in small if s['id'].startswith(pair+':')},
                             {pair+':layer0', pair+':layer1'})

    def test_all_pairs_no_edit_and_empty_base(self):
        all_strokes, _ = select_base_pairs(self.mesh, self.strokes, self.cfg, 150)
        self.assertEqual(core.stroke_digest(all_strokes), core.stroke_digest(self.strokes))
        empty, _ = select_base_pairs(self.mesh, self.strokes, self.cfg, 0)
        self.assertTrue(all(s['part'] != 3 for s in empty))

    def test_missing_layer_and_invalid_count_rejected(self):
        broken = [s for s in self.strokes if s['id'] != 'p3:seed0000:layer1']
        with self.assertRaises(ValueError): select_base_pairs(self.mesh, broken, self.cfg, 75)
        for count in (-1, 151, 75.5, True):
            with self.assertRaises(ValueError): select_base_pairs(self.mesh, self.strokes, self.cfg, count)


if __name__ == '__main__': unittest.main(verbosity=2)
