from pilotio import *
from core import run_backend
import unittest
class IndependentBaseline(unittest.TestCase):
    def test_B0_keeps_two_collinear_fragments_independent(self):
        data=load_np(OUT/'synthetic/seed_0/clean/broken_collinear/input.npz')
        result=run_backend(data,'B0',0)
        self.assertEqual(result['stats']['eligible_fragments'],2)
        self.assertEqual(result['stats']['final_hypotheses'],2)
        self.assertEqual(result['stats']['assigned_samples'],len(data['xyz']))
        self.assertEqual(result['stats']['candidate_links'],0)
if __name__=='__main__':unittest.main(verbosity=2)
