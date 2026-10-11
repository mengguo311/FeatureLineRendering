import unittest
import numpy as np
from depth_checks import valid_depth, compare_cameras,paired_thumbnail
class Tests(unittest.TestCase):
 def test_contact_sheet_preserves_invalid_masks(self):
  a=np.ma.masked_where([[False,True]],[[1.,2.]])
  np.testing.assert_array_equal(np.ma.getmaskarray(paired_thumbnail(a,a)),[[False,True,False,True]])
 def test_raw_unchanged_and_exact_half_included(self):
  d=np.array([[2.,3.,np.nan,0.,-1.,np.inf]],np.float32);a=np.array([[.5,.4999,.9,1.,1.,1.]],np.float32);before=d.copy()
  np.testing.assert_array_equal(valid_depth(d,a),[[True,False,False,False,False,False]])
  np.testing.assert_array_equal(d,before)
 def test_alpha_nan_is_invalid(self):
  np.testing.assert_array_equal(valid_depth(np.ones((1,2),np.float32),np.array([[np.nan,.9]],np.float32)),[[False,True]])
 def test_shape_mismatch_rejected(self):
  with self.assertRaises(ValueError):valid_depth(np.ones((2,3)),np.ones((3,2)))
 def test_camera_same_checkpoint_independent(self):
  c={'view':'0000','width':777,'height':581,'fx':1000.,'fy':1000.,'extrinsic':np.eye(4).tolist(),'iteration':15000}
  compare_cameras([c],[dict(c,iteration=30000)])
  with self.assertRaises(ValueError):compare_cameras([c],[dict(c,fx=1001.)])
if __name__=='__main__':unittest.main(verbosity=2)
