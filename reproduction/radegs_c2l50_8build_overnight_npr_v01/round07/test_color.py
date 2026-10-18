from env import *
import unittest
from appearance import color_mode,source_only
class ColorTests(unittest.TestCase):
 def asset(self):
  sh=np.zeros((2,3,16));sh[:,:,0]=.4;sh[:,0,3]=.7
  return dict(means=np.array([[0.,0.,2.],[.1,0.,3.]]),covariance=np.repeat(np.eye(3)[None]*.01,2,0),opacity=np.array([.5,.8]),SH=sh)
 def cameras(self):
  a=dict(fx=80.,fy=100.,cx=23.4,cy=25.7,width=50,height=54,extrinsic=np.eye(4).tolist());b=dict(a);e=np.eye(4);e[0,3]=1;b['extrinsic']=e.tolist();return a,b
 def test_dc_analytic(self):
  a=self.asset();c,_=self.cameras();x=color_mode(a,c,'dc_only',c);np.testing.assert_allclose(x,.5+.28209479177387814*.4,rtol=0,atol=1e-15)
 def test_dc_view_independent(self):
  a=self.asset();c,d=self.cameras();np.testing.assert_array_equal(color_mode(a,c,'dc_only',c),color_mode(a,d,'dc_only',c))
 def test_full_view_dependent(self):
  a=self.asset();c,d=self.cameras();self.assertGreater(np.max(abs(color_mode(a,c,'full_sh',c)-color_mode(a,d,'full_sh',c))),.01)
 def test_anchor_exact_dev_fixed_elsewhere(self):
  a=self.asset();c,d=self.cameras();x=color_mode(a,c,'anchor_sh',c);np.testing.assert_array_equal(x,color_mode(a,c,'full_sh',c));np.testing.assert_array_equal(x,color_mode(a,d,'anchor_sh',c))
 def test_source_unchanged(self):
  a=self.asset();before={k:v.copy() for k,v in a.items()};c,d=self.cameras()
  for arm in ['full_sh','dc_only','anchor_sh']:color_mode(a,d,arm,c)
  for k in a:np.testing.assert_array_equal(a[k],before[k])
 def test_bad_arm_and_missing_anchor(self):
  a=self.asset();c,_=self.cameras()
  with self.assertRaises(ValueError):color_mode(a,c,'fake',c)
  with self.assertRaises(ValueError):color_mode(a,c,'anchor_sh',None)
 def test_exclude_ink_and_wrong_count(self):
  r=np.zeros(2,dtype=[('group_id','u1')]);self.assertIs(source_only(r,2),r);r['group_id'][1]=1
  with self.assertRaises(ValueError):source_only(r,2)
  with self.assertRaises(ValueError):source_only(r,1)
if __name__=='__main__':unittest.main(verbosity=2)
