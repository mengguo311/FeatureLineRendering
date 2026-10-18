import unittest
from env import np
from upright import fit_support,plane_labels
class SupportTests(unittest.TestCase):
 def fixture(self):
  rng=np.random.default_rng(1729);n=300
  ground=np.c_[rng.uniform(-2,2,n),rng.uniform(-2,2,n),np.zeros(n)];wall=np.c_[np.zeros(n*2),rng.uniform(-2,2,n*2),rng.uniform(.1,2,n*2)];body=np.c_[rng.uniform(-.2,.2,80),rng.uniform(-.2,.2,80),np.ones(80)]
  X=np.r_[ground,wall,body];v=np.arange(len(X))%2;per=np.arange(len(X))<3*n;cen=~per;return X,np.full(len(X),.01),v,per,cen
 def test_same_color_dominant_wall_not_support_plane(self):
  a=self.fixture();m=fit_support(*a,np.array([0,0,1.]));self.assertIsNotNone(m);self.assertGreater(abs(m['normal'][2]),.999);self.assertLess(abs(m['offset']),1e-10)
 def test_supported_plane_band_unknown_body_kept(self):
  m=dict(normal=[0,0,1],offset=0,sign=1);l=plane_labels(np.array([[0,0,0],[0,0,.1],[0,0,-.1]]),np.full(3,.01),m);np.testing.assert_array_equal(l,[-1,1,0])
 def test_scale_invariance(self):
  X,p,v,a,b=self.fixture();m=fit_support(X,p,v,a,b,np.array([0,0,1.]));q=fit_support(X*7,p*7,v,a,b,np.array([0,0,1.]));np.testing.assert_allclose(q['normal'],m['normal'],atol=1e-9);np.testing.assert_allclose(q['offset'],m['offset']*7,atol=1e-9)
 def test_no_ground_refuses_wall(self):
  X,p,v,a,b=self.fixture();X=X[300:];self.assertIsNone(fit_support(X,p[300:],v[300:],a[300:],b[300:],np.array([0,0,1.])))
if __name__=='__main__':unittest.main()
