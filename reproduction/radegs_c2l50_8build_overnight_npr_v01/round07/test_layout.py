from env import *
import unittest
from deliver_repair import pad_native
class LayoutTests(unittest.TestCase):
 def test_mixed_sizes_no_resample(self):
  a=np.arange(18).reshape(2,3,3)/18;b=np.zeros((4,5,3));x=pad_native([('a',a),('b',b)]);np.testing.assert_array_equal(x[0][1][:2,:3],a);self.assertEqual(x[0][1].shape,(4,5,3));self.assertTrue((x[0][1][2:]==1).all())
 def test_equal_size_values_exact(self):
  a=np.random.default_rng(17).random((5,7,3));x=pad_native([('a',a),('b',a)]);np.testing.assert_array_equal(x[0][1],a)
 def test_no_bad_channels(self):
  with self.assertRaises(ValueError):pad_native([('a',np.zeros((3,5)))])
if __name__=='__main__':unittest.main(verbosity=2)
