import unittest
from env import np
from upright import infer_up
class UprightTests(unittest.TestCase):
 def cameras(self):
  t=np.linspace(0,2*np.pi,8,endpoint=False);return np.c_[np.cos(t),np.sin(t),np.zeros(8)],np.tile([0,0,1.],(8,1))
 def test_rig_axis(self):
  r,u=self.cameras();m=infer_up(r,u);self.assertTrue(m['qualified']);np.testing.assert_allclose(m['up'],[0,0,1],atol=1e-12)
 def test_roll_inconsistent_unknown(self):
  r=np.eye(3);m=infer_up(r,r);self.assertFalse(m['qualified'])
 def test_single_direction_degenerate(self):
  m=infer_up(np.tile([1.,0,0],(8,1)),np.tile([0,0,1.],(8,1)));self.assertFalse(m['qualified'])
 def test_rotation_equivariant(self):
  r,u=self.cameras();q=np.array([[1,0,0],[0,.6,-.8],[0,.8,.6]]);m=infer_up(r@q.T,u@q.T);np.testing.assert_allclose(m['up'],q@np.array([0,0,1]),atol=1e-12)
if __name__=='__main__':unittest.main()
