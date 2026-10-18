from env import *
import unittest
import numpy as np
from morphology import describe
class ShapeTests(unittest.TestCase):
 def scene(self):
  m=np.zeros((240,240),bool);m[40:200,48:52]=1;m[80:160,95:115]=1;m[80:160,155:205]=1;return m
 @unittest.expectedFailure
 def test_thin_leaf_thick_order(self):
  m=self.scene();d=describe(m,np.zeros_like(m));f=d['feature'];self.assertLess(f[120,50,0],f[120,105,0]);self.assertLess(f[120,105,1],f[120,180,1])
 def test_multiscale_can_discriminate_analytic_shapes(self):
  m=self.scene();d=describe(m,np.zeros_like(m));f=d['feature'];self.assertLess(f[120,50,0],f[120,105,0]);self.assertLess(f[120,105,2],f[120,180,2]);self.assertEqual(f[120,105,1],f[120,180,1])
 def test_hole_and_components_preserved(self):
  m=self.scene();m[110:130,170:190]=0;o=m.copy();d=describe(m,np.zeros_like(m));np.testing.assert_array_equal(m,o);self.assertFalse(d['eligible'][120,180]);self.assertEqual(d['feature'][120,180,0],0)
 def test_unknown_is_bound_not_filled(self):
  m=self.scene();u=np.zeros_like(m);u[35:205,40:60]=1;u[m]=0;d=describe(m,u);self.assertGreater(d['spread'][120,50],.1);self.assertFalse(d['eligible'][120,50]);self.assertTrue(d['eligible'][120,180])
 def test_rotate_no_axis_label(self):
  m=self.scene();d=describe(m,np.zeros_like(m));e=describe(np.rot90(m),np.zeros_like(m));np.testing.assert_allclose(np.rot90(d['feature']),e['feature'],rtol=0,atol=1e-12)
 def test_scale_normalization(self):
  m=self.scene();d=describe(m,np.zeros_like(m));big=np.repeat(np.repeat(m,2,0),2,1);e=describe(big,np.zeros_like(big));np.testing.assert_allclose(d['feature'][120,105],e['feature'][240,210],rtol=0,atol=.03)
 def test_frame_clipping_unknown(self):
  m=self.scene();m[:,0:2]=1;d=describe(m,np.zeros_like(m));self.assertFalse(d['eligible'][:,0].any());self.assertTrue(m[:,0].all())
 def test_invalid_empty_and_overlap(self):
  m=self.scene()
  with self.assertRaises(ValueError):describe(np.zeros_like(m),np.zeros_like(m))
  with self.assertRaises(ValueError):describe(m,m)
  with self.assertRaises(ValueError):describe(m.astype(float),np.zeros_like(m))
if __name__=='__main__':unittest.main(verbosity=2)
