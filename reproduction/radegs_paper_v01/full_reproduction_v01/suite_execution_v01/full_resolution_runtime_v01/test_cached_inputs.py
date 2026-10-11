import sys,unittest
from pathlib import Path
import numpy as np
sys.path.append(str(Path(__file__).resolve().parents[3]/'stage2'))
import gpu_stages

class CachedInput(unittest.TestCase):
 def test_camera_z_mask_alpha_and_dimensions(self):
  z=np.array([[2.,3.],[0.,9.]],dtype=np.float32);a=np.array([[.5,.49],[1.,1.]],dtype=np.float32);m=np.array([[1.,1.],[1.,0.]])
  got=gpu_stages.masked_camera_z(z,a,m,(2,2));np.testing.assert_array_equal(got,[[2,0],[0,0]])
  np.testing.assert_array_equal(z,[[2,3],[0,9]])
 def test_invalid_shape_or_nonfinite_fails(self):
  z=np.ones((2,2),np.float32)
  for d,a,m in [(z[:1],z,z),(z,z[:1],z),(z,z,z[:1]),(z*np.nan,z,z)]:
   with self.assertRaises(ValueError):gpu_stages.masked_camera_z(d,a,m,(2,2))
 def test_depthmax_not_rescaled_or_tuned(self):
  z=np.array([[.0001,7.99],[8.,9.]],np.float32);one=np.ones_like(z)
  np.testing.assert_array_equal(gpu_stages.masked_camera_z(z,one,one,(2,2)),z)
if __name__=='__main__':unittest.main(verbosity=2)
