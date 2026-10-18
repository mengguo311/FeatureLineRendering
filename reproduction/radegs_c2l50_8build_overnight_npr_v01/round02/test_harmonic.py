from env import *
import unittest
from harmonic import solve, labels, edge_weight
class TestHarmonic(unittest.TestCase):
 def test_seed_and_sum(self):
  q,meta=solve(5,np.arange(4),np.arange(1,5),np.ones(4),np.array([1,0,0,0,2]));np.testing.assert_allclose(q[:,0],[1,.75,.5,.25,0],atol=1e-7);np.testing.assert_allclose(q.sum(1),1,atol=1e-7);self.assertEqual(labels(q)[2],0)
 def test_unseeded_disconnected_unknown(self):
  q,_=solve(4,np.array([0,2]),np.array([1,3]),np.ones(2),np.array([1,0,0,0]));np.testing.assert_array_equal(q[2:],0);np.testing.assert_array_equal(labels(q),[1,1,0,0])
 def test_boundary_resistance(self):
  q,_=solve(4,np.array([0,1,2]),np.array([1,2,3]),np.array([1.,.001,1.]),np.array([1,0,0,2]));self.assertGreater(q[1,0],.99);self.assertGreater(q[2,1],.99)
 def test_soft_target_no_new_seed(self):
  q,_=solve(3,np.array([0,1]),np.array([1,2]),np.ones(2),np.zeros(3,int),np.array([1.,0,0]),np.array([[.8,.2,0],[0,0,0],[0,0,0]]));np.testing.assert_allclose(q,[[.8,.2,0]]*3,atol=1e-7)
 def test_permutation_and_no_cross(self):
  i=np.array([0,2,1]);j=np.array([1,3,2]);w=np.ones(3);seed=np.array([1,0,0,2]);q,_=solve(4,i,j,w,seed);p=np.array([2,0,3,1]);q2,_=solve(4,p[i],p[j],w,seed[np.argsort(p)]);np.testing.assert_allclose(q2[p],q,atol=1e-7);q0,_=solve(4,i[:2],j[:2],w[:2],seed);self.assertGreater(q0[1,0],q[1,0])
 def test_color_not_identity_and_gate(self):
  w=edge_weight(np.array([[0.,0,0],[0,0,0]]),np.array([[1.,1,1],[0,0,0]]),np.ones(2),True);self.assertLess(w[0],w[1]);self.assertTrue(np.isfinite(w).all())
if __name__=='__main__':unittest.main()
