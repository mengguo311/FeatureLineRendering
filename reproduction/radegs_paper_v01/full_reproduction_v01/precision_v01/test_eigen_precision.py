import unittest
import numpy as np
from eigen_probe import legacy_eigh,rotation


class EigenPrecisionTests(unittest.TestCase):
    def test_small_positive_covariance_reconstructs_its_inverse(self):
        r=rotation(np.array([[.7,.2,-.3,.4]],np.float32))[0]
        a=r@np.diag([1e-7,4e-6,1e-5])@r.T
        v,q=legacy_eigh(a)
        inverse=(q/v[:,None,:])@q.transpose(0,2,1)
        residual=float(np.linalg.norm(inverse[0]@a-np.eye(3)))
        print('C24 GLM inverse residual',residual,flush=True)
        self.assertLess(residual,1e-3)


if __name__=='__main__':unittest.main(verbosity=2)
