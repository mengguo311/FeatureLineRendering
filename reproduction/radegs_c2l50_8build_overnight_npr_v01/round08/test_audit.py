from env import *
import unittest
from audit_metrics import compare,overlap
class Audit(unittest.TestCase):
 def test_unknown_not_improvement(self):
  a=np.array([1,1,2,2]);b=np.zeros(4,int);r=compare(a,b,np.ones(4,bool));assert r['known_to_unknown']==4 and r['known_changed']==0 and r['unknown_to_known']==0
 def test_outside_mask_not_counted(self):
  r=compare(np.array([1,2,1]),np.array([2,1,0]),np.array([1,0,0],bool));assert r['known_changed']==1 and r['masked_pixels']==1
 def test_identical_density_overlap_one(self):
  h=np.array([[.2,.8],[.2,.8]]);np.testing.assert_array_equal(overlap(h),np.ones((2,2)))
 def test_disjoint_density_overlap_zero(self):
  h=np.eye(2);np.testing.assert_array_equal(overlap(h),np.eye(2))
if __name__=='__main__':unittest.main()
