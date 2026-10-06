"""Independent contracts before the selection implementation (RED then GREEN)."""
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from selection import silhouette, sparse_sample, compare_sides, normalize_scores, select_ids

class SparseContracts(unittest.TestCase):
    def test_normal_and_endpoints(self):
        a=np.zeros((31,31)); a[:, :15]=1
        edge, p, n, sdf=silhouette(a, .5)
        q=np.abs(p[:,1]-14)<.1
        np.testing.assert_allclose(np.abs(n[q,1]),1,atol=1e-6)
        for delta in (1,2,4):
            np.testing.assert_allclose(np.linalg.norm((p+delta*n)-(p-delta*n),axis=1),2*delta)
        self.assertEqual(len(p),31)

    def test_bilinear_original_id_union_not_slot(self):
        ids=np.array([[[7,3],[3,7]],[[7,9],[9,7]]],np.int32)
        w=np.array([[[.4,.2],[.5,.1]],[[.6,.1],[.3,.2]]],np.float32)
        got,res=sparse_sample(ids,w,np.array([[.5,.5]]),np.ones((2,2)))
        self.assertEqual(set(got[0]),{3,7,9})
        self.assertAlmostEqual(got[0][7],.325,places=6)
        self.assertAlmostEqual(got[0][3],.175,places=6)
        self.assertAlmostEqual(got[0][9],.1,places=6)
        self.assertAlmostEqual(res[0],.4,places=6)

    def test_background_zero_truncation_unknown_and_L1_bound(self):
        ids=np.array([[[0],[1]]],np.int32); w=np.array([[[.4],[.5]]],np.float32)
        # Independent full distributions: (0:.4,2:.2), (1:.5,2:.1)
        obs,raw,participation,bound=compare_sides(ids,w,np.array([[.6,.6]]),
              np.array([[0.,0.]]),np.array([[0.,1.]]),3)
        self.assertAlmostEqual(obs[0],.9,places=6)
        self.assertAlmostEqual(bound[0],.3,places=6)
        self.assertLessEqual(abs(1.-obs[0]),bound[0])
        maps,res=sparse_sample(ids,w,np.array([[-1.,0.]]),np.array([[.6,.6]]))
        self.assertEqual(maps,[{}]); self.assertEqual(res[0],0.)
        self.assertGreater(bound[0],0.)

    def test_full_mass_floor_refusal_and_no_padding(self):
        score=normalize_scores(np.array([1.,1.,0.]),np.array([100.,.001,5.]),.25,1e-6)
        self.assertAlmostEqual(score[0],.01,places=6); self.assertEqual(score[1],0.)
        self.assertEqual(len(select_ids(score,np.array([1.,1.,0.]),np.array([100.,.001,5.]),
            ratio_floor=.02,raw_floor=.01,min_mass=.25)),0)

if __name__=='__main__': unittest.main(verbosity=2)
