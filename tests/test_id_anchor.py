import unittest
import numpy as np
from src.id_anchor import anchor_samples
from src.common import Camera

CFG=dict(layer_spacing=3.,layer_rel_tol=.01,min_layer_mass=.8,max_dominant_distance_spacing=4.,max_reprojection_px=3.)
class AnchorTest(unittest.TestCase):
 def setUp(self):
  self.cam=Camera([[100.,0,50],[0,120,50],[0,0,1]],np.eye(4),100,100)
 def test_centers_not_depth_backprojection(self):
  g=dict(mu=np.array([[.01,0,2],[.03,0,2]]));r=anchor_samples(g,self.cam,np.array([[50.,50.]]),np.array([[1.,0.]]),np.array([[0,1]]),np.array([[.5,.5]]),np.array([2.]),CFG,.02)
  self.assertTrue(r['valid'][0]);np.testing.assert_allclose(r['anchor'][0],[.02,0,2]);self.assertGreater(r['reprojection_error'][0],.9);self.assertLess(r['backprojection_error'][0],1e-8)
 def test_cross_layer_rejected(self):
  g=dict(mu=np.array([[0,0,2],[0,0,4]]));r=anchor_samples(g,self.cam,np.array([[50.,50.]]),np.array([[1.,0.]]),np.array([[0,1]]),np.array([[.5,.5]]),np.array([2.]),CFG,.01)
  self.assertFalse(r['valid'][0]);self.assertEqual(r['reason'][0],'cross_depth_layer')
 def test_full_K_plane_lift(self):
  g=dict(mu=np.array([[0,0,2.]]));r=anchor_samples(g,self.cam,np.array([[50.,50.]]),np.array([[0.,1.]]),np.array([[0]]),np.array([[1.]]),np.array([2.]),CFG,.01)
  self.assertAlmostEqual(abs(r['lift'][0,1]),1.);self.assertAlmostEqual(float(r['plane'][0]@r['lift'][0]),0.)
if __name__=='__main__':unittest.main()
