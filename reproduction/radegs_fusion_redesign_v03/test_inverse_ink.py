import unittest
import numpy as np
from scipy.sparse import csr_matrix
import inverse_ink as inv
from common import core
class InverseInkTests(unittest.TestCase):
 def test_product_not_addition(self):
  G=csr_matrix([[1.,1.],[.5,.2]])
  np.testing.assert_allclose(inv.forward(np.array([.4,.5]),G),[.7,1-.8*.9],rtol=0,atol=1e-14)
 def test_gradient_finite_difference(self):
  G=csr_matrix([[1.,.1],[.2,.7],[.4,0.]])
  obs=[{'view':'a','G':G,'target':np.array([.7,.01,.15]),'region':np.ones(3,bool)}];a=np.array([.3,.4]);f,g=inv.objective(a,obs)
  fd=np.array([(inv.objective(a+np.eye(2)[k]*1e-6,obs)[0]-inv.objective(a-np.eye(2)[k]*1e-6,obs)[0])/2e-6 for k in range(2)])
  np.testing.assert_allclose(g,fd,rtol=0,atol=1e-8)
 def test_repeated_observations_do_not_increase_ink(self):
  o={'view':'same_camera','G':csr_matrix([[1.],[.2]]),'target':np.array([.7,0.]),'region':np.ones(2,bool)}
  base=inv.objective(np.array([.4]),[o])
  for n in [3,12,47]:
   f,g=inv.objective(np.array([.4]),[o]*n);np.testing.assert_allclose([f,*g],[base[0],*base[1]],rtol=0,atol=1e-14)
 def test_transparent_and_black_sheet_negative_controls(self):
  o={'view':'a','G':csr_matrix(np.eye(2)),'target':np.array([.8,0.]),'region':np.ones(2,bool)}
  good=inv.objective(np.array([.8,0.]),[o])[0]
  self.assertGreater(inv.objective(np.zeros(2),[o])[0],good+.5)
  self.assertGreater(inv.objective(np.full(2,.95),[o])[0],good+.8)
 def test_hidden_not_negative(self):
  o={'view':'hidden','G':csr_matrix((3,1)),'target':np.zeros(3),'region':np.ones(3,bool)}
  f,g=inv.objective(np.array([.8]),[o],sparsity=0);self.assertEqual(f,0);np.testing.assert_array_equal(g,[0])
 def test_unknown_depth_not_negative(self):
  o={'view':'unknown','G':csr_matrix([[1.]]),'target':np.zeros(1),'region':np.ones(1,bool),'negative_known':np.zeros(1,bool)}
  f,g=inv.objective(np.array([.8]),[o],sparsity=0);self.assertEqual(f,0);np.testing.assert_array_equal(g,[0])
 def test_conflicting_visible_edge_has_nonzero_optimum(self):
  obs=[{'view':str(i),'G':csr_matrix([[1.]]),'target':np.array([float(i)]),'region':np.ones(1,bool)} for i in [0,1]]
  self.assertAlmostEqual(inv.objective(np.array([.5]),obs,sparsity=0)[0],.25)
  self.assertGreater(inv.objective(np.array([0.]),obs,sparsity=0)[0],.25)
  self.assertGreater(inv.objective(np.array([.95]),obs,sparsity=0)[0],.25)
 def test_near_layers_not_transitively_joined(self):
  g=core.group_samples(np.array([[0.,0,2],[0,0,2.03],[0,0,2.06]]),np.arange(3),np.full(3,.01),np.tile([1.,0,0],(3,1)),np.ones(3));self.assertEqual(len(g),3)
 def test_sparse_kernel_matches_native(self):
  a={'means':np.array([[0.,0.,2.],[.02,.03,2.1]]),'covariance':np.eye(3)[None]*np.array([.05,.07])[:,None,None]**2,'opacity':np.array([.7,.5]),'colors':np.zeros((2,3))}
  c={'width':21,'height':19,'fx':25.,'fy':24.,'extrinsic':np.eye(4).tolist()};d=np.full((19,21),2.05);al=np.ones_like(d)
  G=inv.kernel_matrix(a,c,d,al)
  p=inv.forward(a['opacity'],G).reshape(19,21);r=1-core.render(a,c,d,al)[...,0]
  np.testing.assert_allclose(p,r,rtol=0,atol=2e-6)
if __name__=='__main__':unittest.main()
