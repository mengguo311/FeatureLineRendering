import unittest
import numpy as np
from native_attributes import camera_record,camera_matrices,_local,ROOT
from representative_core import split_scales

class Engineering(unittest.TestCase):
 def test_world_projection_pixel_units(self):
  k=[[400,0,399.5],[0,400,399.5],[0,0,1]];m=np.eye(4);m[0,3]=-.1
  cam=dict(native_width=800,native_height=800,native_K=k,w2c=m.tolist());view,full=camera_matrices(cam)
  xyz=np.array([.1,0,2,1],np.float32);clip=xyz@full;ndc=clip[:2]/clip[3];pixel=((ndc+1)*800-1)/2
  np.testing.assert_allclose(pixel,[399.5,399.5],atol=1e-4)
  xyz[0]+=.1;clip=xyz@full;pixel=((clip[:2]/clip[3]+1)*800-1)/2
  self.assertAlmostEqual(float(pixel[0]),419.5,places=4)
 def test_reject_unqualified_principal_point(self):
  with self.assertRaises(ValueError):camera_record(dict(H=800,W=800,K=[[400,0,400],[0,400,400],[0,0,1]],w2c=np.eye(4)))
 def test_output_containment(self):
  self.assertEqual(_local(ROOT/'out/representative_edge_gaussians_three_v1/x'),ROOT/'out/representative_edge_gaussians_three_v1/x')
  with self.assertRaises(ValueError):_local(ROOT/'artifacts/gaussian_edge_attribution_v1/x')
 def test_nonpersistent_fine_not_deleted_near_other_major(self):
  x=np.zeros((3,20,20,3),np.float32);x[0,8,8,0]=1;x[1,8,6,0]=1;x[0,8,10,0]=.5
  major,detail=split_scales(x,.1,2)
  self.assertEqual(detail[8,10,0],.5)
 def test_outline_kept_separate(self):
  x=np.zeros((3,10,10,3),np.float32);x[0:2,5,5,2]=1
  major,detail=split_scales(x,.1,2)
  self.assertEqual(major[5,5,2],1);self.assertEqual(major[:,:,0].sum(),0);self.assertEqual(major[:,:,1].sum(),0)
if __name__=='__main__':unittest.main(verbosity=2)
