import json
import unittest
import numpy as np
from eigen_probe import OUT,rotation
from stable_eigen_candidate import geometry_eigh

class CandidateTests(unittest.TestCase):
    def test_actual_trained_covariance_inverse(self):
        a=np.array(json.loads((OUT/'real_covariance_eigen_audit.json').read_text())['15000']['worst_matrix'],np.float32)
        v,q=geometry_eigh(a);inv=(q/v[:,None,:])@q.transpose(0,2,1)
        residual=np.linalg.norm(inv[0].astype(np.float64)@a-np.eye(3))
        print('actual covariance inverse residual',residual,flush=True)
        self.assertLess(residual,.001)
    def test_orientation_invariant_to_common_covariance_scale(self):
        r=rotation(np.array([[.7,.2,-.3,.4]],np.float32))[0]
        base=r@np.diag([1.,40.,100.])@r.T
        ray=np.array([.01,-.02,1.])
        expected=np.linalg.solve(base,ray);expected/=np.linalg.norm(expected)
        for scale in [1e-7,1e-6,1e-4,1.,100.]:
            v,q=geometry_eigh(base*scale);inv=(q/v[:,None,:])@q.transpose(0,2,1)
            actual=inv[0]@ray;actual/=np.linalg.norm(actual)
            np.testing.assert_allclose(actual,expected,rtol=1e-4,atol=1e-5)

if __name__=='__main__':unittest.main(verbosity=2)
