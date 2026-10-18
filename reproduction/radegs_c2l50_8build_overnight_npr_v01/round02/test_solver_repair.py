from env import *
from harmonic import solve
import unittest
class TestSolverRepair(unittest.TestCase):
 def test_long_weak_chain_exact_resistance(self):
  n=6101;i=np.arange(n-1);w=np.where(i%3==0,1e-5,1.);seeds=np.zeros(n,int);seeds[0]=1;seeds[-1]=2;q,m=solve(n,i,i+1,w,seeds);res=np.r_[0,np.cumsum(1/w)];truth=1-res/res[-1];np.testing.assert_allclose(q[:,0],truth,atol=1e-6);self.assertLessEqual(q.max(),1+1e-5)
if __name__=='__main__':unittest.main()
