import unittest
import env
import numpy as np
from output import pack
class OutputTests(unittest.TestCase):
 def data(self):
  m=np.array([[True,False],[True,True]]);return dict(mask=m,subject_unknown=np.array([[False,True],[False,False]]),seeds=np.zeros(3,np.uint8),uv=np.array([[0,0],[0,1],[1,1]]))
 def test_hole_not_filled(self):
  d=self.data();a=pack(np.tile([1.,0.],(3,1)),d);self.assertEqual(a['labels'][0,1],0);self.assertEqual(a['probability'][0,1].sum(),0)
 def test_source_uv_not_GS_ID(self):
  d=self.data();a=pack(np.array([[1.,0.],[0.,1.],[1.,0.]]),d);np.testing.assert_array_equal(a['source_uv'],d['uv']);np.testing.assert_array_equal(a['labels'],[[1,0],[2,1]])
 def test_ambiguous_stays_unknown(self):
  d=self.data();a=pack(np.tile([.5,.5],(3,1)),d);self.assertFalse(a['labels'].any());self.assertTrue(a['unknown'].all())
 def test_no_height_seed_added_to_target(self):
  d=self.data();a=pack(np.tile([1.,0.],(3,1)),d);self.assertFalse(a['seeds'].any())
if __name__=='__main__':unittest.main()
