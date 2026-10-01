import unittest
from types import SimpleNamespace
import numpy as np
from src.rade_state_calibration import render_rade_frozen, camera_matrices

class FoundationTest(unittest.TestCase):
    def setUp(self):
        self.cam=SimpleNamespace(H=64,W=64,w2c=np.eye(4),K=np.array([[64.,0,32.],[0,64.,32.],[0,0,1.]]),center=np.zeros(3))
        self.g={'mu':np.array([[0.,0.,3.]]),'quat':np.array([[1.,0.,0.,0.]]),
                'scale':np.array([[.15,.15,.15]]),'opacity':np.array([.9]),'albedo':np.array([[1.,0.,0.]])}
    def test_camera_projection_origin_center(self):
        view,proj=camera_matrices(self.cam)
        p=np.array([0.,0.,3.,1.])@proj
        self.assertAlmostEqual(float(p[0]/p[3]),0,places=5)
        self.assertAlmostEqual(float(p[1]/p[3]),0,places=5)
    def test_official_rade_kernel_on_isotropic_splat(self):
        f=render_rade_frozen(self.g,self.cam)
        self.assertEqual(set(f),{'rgb','alpha','expected_depth','median_depth','normal','radii'})
        self.assertEqual(f['alpha'].shape,(64,64))
        self.assertGreater(f['alpha'][32,32],.1)
        self.assertTrue(np.isfinite(f['expected_depth']).all())
        self.assertTrue(np.isfinite(f['normal']).all())
        self.assertGreater(f['expected_depth'][32,32],2.0)
        self.assertLess(f['expected_depth'][32,32],4.0)
        self.assertAlmostEqual(np.linalg.norm(f['normal'][32,32]),1,places=3)

if __name__=='__main__':unittest.main()
