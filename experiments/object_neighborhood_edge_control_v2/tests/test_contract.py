import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from contracts import writable_path, validate_roles, angle_status, ls_certificate
import numpy as np
class ContractTests(unittest.TestCase):
    def test_readonly_boundary(self):
        with self.assertRaises(ValueError): writable_path('/home/u00134/3dgs_line/object_neighborhood_edge_control_v1/out/a')
    def test_roles_reject_transform_leak(self):
        frame={'id':'a','theta_deg':1,'transform_matrix':np.eye(4).tolist()}
        with self.assertRaises(ValueError): validate_roles({'train':[frame],'dev-in':[dict(frame,id='b')]})
    def test_reclassify_extra_supervision(self):
        self.assertEqual(angle_status(32,[-28,18,35])['status'],'interpolation')
        self.assertEqual(angle_status(38,[-28,18,35])['status'],'extrapolation')
    def test_dual_valid_arbitrary_y_and_normalization(self):
        rng=np.random.default_rng(7);A=rng.normal(size=(13,4));b=rng.normal(size=13);c=rng.uniform(size=4);y=rng.normal(size=13)
        z=ls_certificate(A@c-b,b,y,A.T@y,13,0)
        self.assertLessEqual(z['D'],z['P']+1e-12)
        self.assertAlmostEqual(z['mse_upper'],np.mean((A@c-b)**2))
if __name__=='__main__': unittest.main()
