import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from R5_TRI_STATE import classify_interval,distance_interval,aabb_pairs
class TriStateTests(unittest.TestCase):
 def test_published_straddling_interval_is_uncertain(self):self.assertEqual(classify_interval(.0199949668,.0200196488,.02)['state'],'uncertain')
 def test_spheres_bound_exact_near_and_far(self):
  for center,expected in [(1.5,'support_near'),(3.,'support_far')]:
   d=distance_interval(np.zeros(3),np.eye(3),np.array([center,0,0]),np.eye(3),k=1,epsilon=.02);self.assertEqual(d['state'],expected)
 def test_big_ellipsoid_survives_coarse_query(self):
  mu=np.array([[0,0,0],[4,0,0]]);L=np.array([np.eye(3),np.eye(3)*.5]);self.assertEqual(aabb_pairs(mu,L,np.array([1,2]),3,.02),[(0,1)])
 def test_near_noncontact_semantics_remain_distinct(self):self.assertEqual(classify_interval(.03,.03,.05)['state'],'support_near')
if __name__=='__main__':unittest.main()
