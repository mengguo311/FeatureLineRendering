import unittest
from env import *
from display_layout import native_canvas
class Layout(unittest.TestCase):
 def test_mixed_native_sizes_are_padded_not_scaled(self):
  a=np.arange(3*5*3).reshape(3,5,3)/50.;b=np.ones((8,8,3));c=native_canvas(a,8,8);self.assertEqual(c.shape,b.shape);self.assertTrue(np.array_equal(c[2:5,1:6],a));self.assertTrue(np.all(c[:2]==1));self.assertTrue(np.array_equal(native_canvas(b,8,8),b))
if __name__=='__main__':unittest.main(verbosity=2)
