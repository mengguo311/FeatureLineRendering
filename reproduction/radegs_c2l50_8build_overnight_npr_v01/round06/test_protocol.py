from env import *
import unittest
from protocol import authorize_fit,pack,fit_views
class ProtocolTests(unittest.TestCase):
 def test_fit_ficus_only(self):
  self.assertTrue(authorize_fit('ficus'))
  for s in ['scan24','scan65']:
   with self.assertRaises(ValueError):authorize_fit(s)
 def test_no_reserved_in_fit(self):
  self.assertEqual(fit_views('ficus'),['train_r_80','train_r_7']);self.assertFalse(set(fit_views('ficus'))&set(RES['ficus']))
 def test_holes_and_unassigned_survive(self):
  m=np.array([[1,0],[1,0]],bool);u=np.array([[0,1],[0,0]],bool);p=pack(m,u,np.array([1,0]),np.array([[1,0,0],[.4,.3,.3]]));np.testing.assert_array_equal(p['labels'],[[1,0],[0,0]]);np.testing.assert_array_equal(p['unknown'],[[0,1],[1,0]]);np.testing.assert_array_equal(p['inference_mask'],m)
 def test_camera_full_intrinsic(self):
  c=dict(fx=612.,fy=799.,cx=317.2,cy=201.6,extrinsic=np.eye(4).tolist());uv=np.array([[35.2,91.8],[602.,401.]]);z=np.array([2.,3.]);X=unproject(uv,z,c);v,d=project(X,c);np.testing.assert_allclose(v,uv,rtol=0,atol=1e-12);np.testing.assert_allclose(d,z,rtol=0,atol=1e-12)
 def test_no_inference_outside_mask(self):
  m=np.eye(3,dtype=bool);u=np.zeros_like(m);p=pack(m,u,np.array([1,2,3]),np.eye(3));self.assertFalse(p['labels'][~m].any());self.assertFalse(p['probability'][~m].any())
if __name__=='__main__':unittest.main(verbosity=2)
