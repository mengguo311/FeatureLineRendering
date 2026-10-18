import unittest
from env import *
from conditional import restrict_ray,weighted_quantile
class ConditionalTests(unittest.TestCase):
 def test_diagonal_analytic(self):
  m=np.array([[1.,2,3]]);C=np.array([np.diag([4.,9,16])]);r=np.array([[.2,.3,1.]])
  z,s,q,ok=restrict_ray(m,C,r);P=np.linalg.inv(C[0]);expected=r[0]@P@m[0]/(r[0]@P@r[0]);self.assertAlmostEqual(z[0],expected,places=12);self.assertAlmostEqual(s[0]**2,1/(r[0]@P@r[0]),places=12)
 def test_tilted_thin_ellipsoid_not_center_depth(self):
  t=np.array([1.,0,.5]);t/=np.linalg.norm(t);n=np.cross(t,[0,1.,0]);U=np.stack([t,[0,1,0],n],1);C=U@np.diag([1.,.1,1e-8])@U.T;x=np.linspace(-.2,.2,5);m=np.c_[x,0*x,2+.5*x];z,s,q,ok=restrict_ray(m,np.repeat(C[None],5,0),np.tile([0.,0,1],(5,1)));self.assertTrue(ok.all());self.assertLess(np.ptp(z),2e-6);self.assertGreater(np.ptp(m[:,2]),.19)
 def test_two_layers_not_collapsed(self):
  m=np.array([[0,0,2.],[0,0,2.2]]);C=np.tile(np.diag([1.,1.,1e-6]),(2,1,1));z,s,q,ok=restrict_ray(m,C,np.tile([0.,0,1],(2,1)));self.assertGreater(weighted_quantile(z,np.ones(2),.9)-weighted_quantile(z,np.ones(2),.1),.19)
 def test_far_center_large_kernel_covered(self):
  z,s,q,ok=restrict_ray(np.array([[5.,0,2]]),np.array([np.diag([100.,1.,.001])]),np.array([[0.,0,1]]));self.assertTrue(ok[0]);self.assertLess(q[0],1)
 def test_missing_and_non_spd_unknown(self):
  m=np.array([[0.,0,2],[np.nan,0,2],[0,0,.1]]);C=np.tile(np.eye(3),(3,1,1));C[0,0,0]=-1;z,s,q,ok=restrict_ray(m,C,np.tile([0.,0,1],(3,1)));self.assertFalse(ok.any())
 def test_mode_gradient_zero_and_covariance_full(self):
  C=np.array([[[.3,.04,.08],[.04,.2,.02],[.08,.02,.4]]]);m=np.array([[.3,-.2,2]]);r=np.array([[.1,.2,1.]])
  z,s,q,ok=restrict_ray(m,C,r);P=np.linalg.inv(C[0]);f=lambda t:((t*r[0]-m[0])@P@(t*r[0]-m[0]));self.assertLess(abs((f(z[0]+1e-5)-f(z[0]-1e-5))/2e-5),1e-8)
 def test_ray_depth_is_z_not_range(self):
  z,s,q,ok=restrict_ray(np.array([[1.,0,2]]),np.array([np.eye(3)]),np.array([[.5,0,1]]));self.assertAlmostEqual(z[0],2);self.assertNotAlmostEqual(z[0],np.sqrt(5))
 def test_rigid_rotation_and_scale(self):
  m=np.array([[.1,.2,2.]]);C=np.array([np.diag([.3,.1,.01])]);r=np.array([[.1,0.,1.]]);z,s,q,ok=restrict_ray(m,C,r);R=np.array([[0,-1,0],[1,0,0],[0,0,1.]]);a,b,c,d=restrict_ray(m@R.T*7,(R@C@R.T)*49,r@R.T);self.assertTrue(np.allclose(a,z*7,atol=1e-12));self.assertTrue(np.allclose(c,q,atol=1e-12))
if __name__=='__main__':unittest.main(verbosity=2)
