import unittest
from env import *
from closure import closure_score,link_gate,visible_state,region_mask,independent_count,can_assign
class CoreTests(unittest.TestCase):
 def test_large_gap(self):self.assertLess(closure_score([8],100),closure_score([2,2,2,2],100))
 def test_scale(self):self.assertAlmostEqual(closure_score([2,5],100),closure_score([20,50],1000),places=14)
 def test_tangent(self):
  self.assertTrue(link_gate([0,0],[2,0],[1,0],[-1,0],1,1,.001,True,True)[0]);self.assertFalse(link_gate([0,0],[2,0],[-1,0],[1,0],1,1,.001,True,True)[0])
 def test_layer(self):self.assertFalse(link_gate([0,0],[2,0],[1,0],[-1,0],1,2,.001,True,True)[0])
 def test_unknown_endpoint(self):self.assertFalse(link_gate([0,0],[2,0],[1,0],[-1,0],1,1,.001,False,True)[0])
 def test_occlusion(self):
  x=visible_state(np.array([1.,1.2,.8,np.nan]),np.ones(4),np.ones(4),1000)
  np.testing.assert_array_equal(x,['visible','occluded','front_inconsistent','unknown'])
 def test_open_leaf(self):self.assertIsNone(closure_score([2],100,open_structure=True))
 def test_hole(self):
  a=np.array([[1,1],[18,1],[18,18],[1,18],[1,1]]);b=np.array([[6,6],[12,6],[12,12],[6,12],[6,6]]);m=region_mask([a,b],(20,20));self.assertTrue(m[3,3]);self.assertFalse(m[9,9])
 def test_duplicate_independence(self):self.assertEqual(independent_count([('v0',3),('v0',3),('v0',3),('v1',4)]),2)
 def test_no_forced_assignment(self):self.assertFalse(can_assign(False,.9,.9));self.assertFalse(can_assign(True,.9,.2));self.assertTrue(can_assign(True,.8,.8))
 def test_camera_projection(self):
  c=dict(fx=400.,fy=700.,cx=12.5,cy=29.,extrinsic=np.eye(4).tolist());X=np.array([[.2,.3,2.],[-1,2,3.] ]);u,z=projection(X,c);np.testing.assert_allclose(unproject(u,z,c),X,rtol=0,atol=1e-14)
if __name__=='__main__':unittest.main()
