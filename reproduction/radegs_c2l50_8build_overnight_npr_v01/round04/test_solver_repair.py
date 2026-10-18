from env import *
import unittest
from scipy import sparse
from solver_repair import repair

class RepairTests(unittest.TestCase):
 def matrix(self,K=2):
  W=np.array([[0,1,0],[1,0,1],[0,1,0.]],float);g=np.array([.3,.05,.2]);A=np.diag(W.sum(1)+g)-W;p=np.eye(K)[np.array([0,1,K-1])];return sparse.csr_matrix(A),g[:,None]*p
 def test_same_linear_system_no_tolerance_relax(self):
  A,b=self.matrix();x,meta=repair(A,b,np.array([[-.01,1.02],[.6,.3],[1.01,-.01]]));np.testing.assert_allclose(x,np.linalg.solve(A.toarray(),b),atol=2e-7);self.assertLessEqual(max(meta['relative_residual']),1.01e-8);self.assertTrue((x>=0).all() and (x<=1).all())
 def test_three_classes_partition(self):
  A,b=self.matrix(3);x,_=repair(A,b,np.zeros_like(b));np.testing.assert_allclose(x.sum(1),1,atol=1e-12);np.testing.assert_allclose(x,np.linalg.solve(A.toarray(),b),atol=2e-7)
 def test_non_partition_rhs_rejected(self):
  A,b=self.matrix()
  with self.assertRaises(AssertionError):repair(A,b*2,np.zeros_like(b))
 def test_unconverged_is_invalid_not_clipped_success(self):
  A,b=self.matrix()
  with self.assertRaises(RuntimeError):repair(A,b,np.zeros_like(b),maxiter=1)
 def test_node_order_invariance(self):
  A,b=self.matrix();x,_=repair(A,b,np.zeros_like(b));p=np.array([2,0,1]);y,_=repair(A[p][:,p],b[p],np.zeros_like(b));np.testing.assert_allclose(y,x[p],atol=1e-12)
if __name__=='__main__':unittest.main()
