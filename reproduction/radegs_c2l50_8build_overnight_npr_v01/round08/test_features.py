from env import *
import unittest
from features import transform
class Features(unittest.TestCase):
 def test_scalar_invariance(self):
  x=np.array([[.12,.3,.2],[.8,.2,.1]]);a,e=transform(x,'chromaticity');b,f=transform(x*.7,'chromaticity');np.testing.assert_allclose(a,b,atol=1e-15);assert e.all() and f.all()
 def test_grey_collision_negative(self):
  a,e=transform(np.array([[.1,.1,.1],[.9,.9,.9]]),'chromaticity');np.testing.assert_array_equal(a[0],a[1])
 def test_invalid_unknown(self):
  a,e=transform(np.array([[0,0,0],[.01,.01,.01],[np.nan,.2,.1],[-.1,.2,.1],[.02,0,0]]),'chromaticity');np.testing.assert_array_equal(e,[False,False,False,False,True]);assert np.isfinite(a).all();assert not a[~e].any()
 def test_no_mutation_and_sum(self):
  x=np.array([[.3,.2,.1],[.03,.01,0.]]);b=x.copy();a,e=transform(x,'chromaticity');np.testing.assert_array_equal(x,b);np.testing.assert_allclose(a.sum(1),1);assert (a>=0).all()
 def test_additive_highlight_not_invariant(self):
  x=np.array([[.3,.2,.1]]);a,_=transform(x,'chromaticity');b,_=transform(x+.2,'chromaticity');assert np.max(abs(a-b))>.05
 def test_matched_floor(self):
  x=np.array([[.001,.002,.003],[.4,.2,.1]]);a,e=transform(x,'rgb_floor');b,f=transform(x,'chromaticity');np.testing.assert_array_equal(e,f);np.testing.assert_array_equal(a[e],x[e])
 def test_raw_identity(self):
  x=np.array([[0.,0.,0.],[.1,.2,.3]]);a,e=transform(x,'raw_rgb');np.testing.assert_array_equal(a,x);assert e.all()
 def test_bad_arm(self):
  with self.assertRaises(ValueError):transform(np.ones((3,3)),'fake')
if __name__=='__main__':unittest.main()
