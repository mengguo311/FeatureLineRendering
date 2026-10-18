from env import *
import unittest
from experiment import seed_labels, combine_priors
class TestSeeds(unittest.TestCase):
 def test_only_central_interiors(self):
  m=dict(height_lo=0.,height_hi=32.,cuts=[8,16],bins=32);h=np.arange(33.);q=seed_labels(h,np.ones(len(h))*3,m,100);self.assertEqual(q[0],0);self.assertEqual(q[8],0);self.assertEqual(q[4],1);self.assertEqual(q[12],2);self.assertEqual(q[24],3)
 def test_holes_edges_and_budget(self):
  m=dict(height_lo=0.,height_hi=32.,cuts=[8,16],bins=32);h=np.full(100,4.);d=np.ones(100)*3;d[:10]=1;q=seed_labels(h,d,m,5);self.assertEqual((q>0).sum(),5);self.assertFalse(q[:10].any())
 def test_unobserved_target_unknown(self):
  g,p=combine_priors(5,np.array([],int),np.zeros((0,3)),np.array([]));np.testing.assert_array_equal(g,0);np.testing.assert_array_equal(p,0)
 def test_no_hard_source_single_label(self):
  g,p=combine_priors(2,np.array([0,0]),np.array([[.8,.2,0],[.6,.4,0]]),np.array([1.,1.]));np.testing.assert_allclose(p[0],[.7,.3,0]);self.assertEqual(g[1],0)
if __name__=='__main__':unittest.main()
