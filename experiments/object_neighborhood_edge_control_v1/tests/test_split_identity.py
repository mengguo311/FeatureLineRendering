import unittest
import numpy as np
from stable_ids import Identity

class IdentityTests(unittest.TestCase):
    def test_reorder_and_split(self):
        s=Identity([31,17],[1,2],[[0,1,2],[3,4,5]])
        s=s.reorder([1,0]); s=s.split([31],2)
        self.assertEqual(s.uid.tolist(),[17,32,33])
        self.assertEqual(s.parent_uid.tolist(),[-1,31,31])
        self.assertEqual(s.label.tolist(),[2,1,1])
        np.testing.assert_equal(s.anchor[1], [0,1,2])
        self.assertEqual(s.continuity_field().tolist(),s.reorder([2,0,1]).continuity_field()[[1,2,0]].tolist())
    def test_no_reuse_after_split(self):
        s=Identity([3],[1],[[0,0,0]])
        s=s.split([3],2).split([4],2)
        self.assertEqual(len(set(s.uid)),3)
        self.assertGreater(min(s.uid[-2:]),5)
