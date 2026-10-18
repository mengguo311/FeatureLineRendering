from env import *
import unittest
from protocol import authorize_fit,pack,calibrate
class ProtocolTests(unittest.TestCase):
 def test_reserved_cannot_fit(self):
  for s in SCENES:
   authorize_fit(s,[DEV[s],AUX[s]])
   with self.assertRaises(ValueError):authorize_fit(s,[DEV[s],RES[s][0]])
 def test_dtu_not_part_fit(self):
  with self.assertRaises(ValueError):authorize_fit('scan24',['0000','0024'],classes=3)
  authorize_fit('ficus',['train_r_80','train_r_7'],classes=3)
 def test_mask_exhaustive_unknown(self):
  m=np.array([[1,1],[0,0]],bool);u=np.array([[0,0],[1,0]],bool);a=pack(m,u,np.array([1,0],np.uint8),np.array([[.9,.1],[.5,.5]]));np.testing.assert_array_equal(a['unknown'],[[0,1],[1,0]]);self.assertEqual(a['labels'].sum(),1);self.assertEqual(a['probability'][~m].sum(),0)
 def test_source_uv_not_gs_id(self):
  m=np.array([[0,1],[1,0]],bool);a=pack(m,np.zeros_like(m),[1,2],np.eye(2));np.testing.assert_array_equal(a['source_uv'],[[1,0],[0,1]]);self.assertNotIn('source_index',a)
 def test_wrong_alpha_rejected(self):
  a=self.fake();ref=self.reference(a);a['alpha']=a['alpha']*.9
  with self.assertRaises(AssertionError):calibrate(a,ref,np.zeros((2,2,3)),np.ones((2,2))*2,np.ones((2,2)))
 def fake(self):return dict(rgb=np.zeros((2,2,3),np.float32),alpha=np.ones((2,2),np.float32),median_center_z=np.ones((2,2),np.float32)*2,expected_center_z=np.ones((2,2),np.float32)*2)
 def reference(self,a):return dict(source_rgb=a['rgb'].copy(),source_alpha=a['alpha'].copy(),source_center_z=a['median_center_z'].copy())
 def test_native_gate_unchanged(self):
  a=self.fake();ref=self.reference(a)
  with self.assertRaises(AssertionError):calibrate(a,ref,np.ones((2,2,3))*.03,np.ones((2,2))*2,np.ones((2,2)))
 def test_depth_comparison_not_equivalence(self):
  a=self.fake();r=calibrate(a,self.reference(a),np.zeros((2,2,3)),np.ones((2,2))*2.1,np.ones((2,2)));self.assertGreater(r['depth_relative_p95'],0);self.assertTrue(r['full_reference_exact'])
if __name__=='__main__':unittest.main(verbosity=2)
