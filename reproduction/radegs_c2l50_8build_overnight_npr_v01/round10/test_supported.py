from env import *
import unittest
from supported import describe_supported,shift_support
sys.path.append(str(CODE.parent/'round09'))
from texture import describe
class Supported(unittest.TestCase):
 def test_all_ones_original(self):
  x=np.random.default_rng(1).random((31,47,3));f,v,d=describe_supported(x,np.ones(x.shape[:2]),1);np.testing.assert_allclose(f,describe(x,1),atol=1e-10,rtol=0);assert v.all()
 def test_constant_foreground_no_false_edge(self):
  w=np.zeros((49,49));w[:,22:27]=1;x=np.ones((49,49,3));x[w>0]=.25;f,v,d=describe_supported(x,w,1);np.testing.assert_allclose(f[w>0],np.broadcast_to([.5,.5,0],f[w>0].shape),atol=1e-10,rtol=0)
 def test_thin_foreground_background_invariance(self):
  y,x=np.mgrid[:49,:49];w=np.zeros((49,49));w[:,22:27]=1;a=np.ones((49,49,3));a[w>0]=np.repeat((.2+.3*np.sin(y[w>0]/3)**2)[:,None],3,axis=1);b=a.copy();b[w==0]=np.random.default_rng(2).random(((w==0).sum(),3));f,v,d=describe_supported(a,w,1);g,q,e=describe_supported(b,w,1);np.testing.assert_array_equal(f,g);assert np.max(abs(describe(a,1)[w>0]-describe(b,1)[w>0]))>.01
 def test_empty_unknown(self):
  f,v,d=describe_supported(np.ones((16,21,3)),np.zeros((16,21)),1);assert not v.any();assert np.isfinite(f).all();np.testing.assert_array_equal(d,np.zeros_like(d))
 def test_uniform_weight_scale_invariant(self):
  x=np.random.default_rng(3).random((31,47,3));w=np.random.default_rng(4).random((31,47));f,v,d=describe_supported(x,w,1);g,q,e=describe_supported(x,.4*w,1);np.testing.assert_allclose(f,g,atol=1e-10,rtol=0);np.testing.assert_array_equal(v,q)
 def test_shift_exact_multiset(self):
  w=np.random.default_rng(5).random((23,31));s=shift_support(w,1);np.testing.assert_array_equal(s,np.roll(w,3,axis=1));np.testing.assert_array_equal(np.sort(w.ravel()),np.sort(s.ravel()))
 def test_no_mutation(self):
  x=np.random.default_rng(6).random((30,40,3));w=np.ones((30,40));a=x.copy();b=w.copy();describe_supported(x,w,1);np.testing.assert_array_equal(x,a);np.testing.assert_array_equal(w,b)
 def test_nan_rgb_refused(self):
  x=np.zeros((12,12,3));x[0]=np.nan
  with self.assertRaises(ValueError):describe_supported(x,np.ones((12,12)),1)
 def test_bad_weight_refused(self):
  with self.assertRaises(ValueError):describe_supported(np.zeros((12,12,3)),-np.ones((12,12)),1)
 def test_shape_refused(self):
  with self.assertRaises(ValueError):describe_supported(np.zeros((12,12,3)),np.ones((13,12)),1)
if __name__=='__main__':unittest.main()
