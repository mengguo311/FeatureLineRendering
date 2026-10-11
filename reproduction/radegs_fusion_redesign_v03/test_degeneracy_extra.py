"""Additional physical wide-splat negative control; frozen core tests unchanged."""
import unittest
import numpy as np
from common import core
import inverse_ink as inv
class ExtraDegeneracy(unittest.TestCase):
 def test_broad_actual_gaussian_is_penalized_off_line(self):
  c={'width':41,'height':41,'fx':40.,'fy':40.,'extrinsic':np.eye(4).tolist()}
  def asset(sigma):return {'means':np.array([[0.,0.,2.]]),'covariance':np.eye(3)[None]*sigma**2,'opacity':np.array([.8]),'colors':np.zeros((1,3))}
  fine=asset(.025);broad=asset(.4);target=1-core.render(fine,c)[...,0].ravel();region=np.ones_like(target,bool)
  good={'view':'one','G':inv.kernel_matrix(fine,c),'target':target,'region':region};bad=dict(good,G=inv.kernel_matrix(broad,c))
  f=inv.objective(np.array([.8]),[good],sparsity=0)[0];b=inv.objective(np.array([.8]),[bad],sparsity=0)[0]
  self.assertLess(f,1e-12);self.assertGreater(b,f+.01)
if __name__=='__main__':unittest.main()
