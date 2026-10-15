from common import *
import unittest
from renderer import render,project_cov,colors,join
def cam():return dict(width=41,height=35,fx=20.,fy=27.,cx=19.,cy=16.,extrinsic=np.eye(4).tolist())
def blob(z=2,op=.5,col=(.8,.4,.2)):
 return dict(means=np.array([[0.,0.,z]]),covariance=np.eye(3)[None]*.04,opacity=np.array([op]),colors=np.array([col]))
class RendererTests(unittest.TestCase):
 def test_center_analytic_single(self):
  a=blob();r=render(a,cam(),[0,0,0]);np.testing.assert_allclose(r['rgb'][16,19],[.4,.2,.1],atol=1e-8);self.assertAlmostEqual(float(r['alpha'][16,19]),.5,8)
 def test_front_back_source_transmittance(self):
  s=blob(op=.8);front=blob(1,.5,(0,0,0));back=blob(3,.5,(0,0,0));f=render(join(s,front),cam(),[0,0,0]);b=render(join(s,back),cam(),[0,0,0]);np.testing.assert_allclose(f['rgb'][16,19],np.array([.8,.4,.2])*.4,atol=2e-8);np.testing.assert_allclose(b['rgb'][16,19],np.array([.8,.4,.2])*.8,atol=2e-8)
 def test_not_RGB_multiply(self):
  s=blob(op=.8);b=blob(3,.5,(0,0,0));sr=render(s,cam(),[0,0,0])['rgb'];ir=render(b,cam(),[1,1,1])['rgb'];j=render(join(s,b),cam(),[0,0,0])['rgb'];self.assertGreater(float(abs(j-sr*ir).max()),.1)
 def test_order_permutation_unique_depth(self):
  a=join(blob(2),blob(3,.7,(.2,.7,.3)),blob(1,.4,(0,0,0)));b={k:v[[2,0,1]] for k,v in a.items()};np.testing.assert_array_equal(render(a,cam())['rgb'],render(b,cam())['rgb'])
 def test_transparent_line(self):
  s=blob();np.testing.assert_array_equal(render(s,cam())['rgb'],render(join(s,blob(1,0,(0,0,0))),cam())['rgb'])
 def test_no_source_is_line(self):
  a=blob(col=(0,0,0));empty={k:v[:0] for k,v in a.items()};np.testing.assert_array_equal(render(a,cam())['rgb'],render(join(empty,a),cam())['rgb'])
 def test_intrinsics_world_project(self):
  c=cam();E=np.eye(4);E[:3,3]=[.1,-.2,.4];c['extrinsic']=E.tolist();m=np.array([[.3,.5,2.]]);uv,z,S=project_cov(m,np.eye(3)[None]*.001,c,0);np.testing.assert_allclose(uv,[[20*.4/2.4+19,27*.3/2.4+16]],atol=1e-12);self.assertAlmostEqual(z[0],2.4);self.assertGreater(np.linalg.eigvalsh(S).min(),0)
 def test_near_and_offscreen(self):
  a=blob(.1);np.testing.assert_array_equal(render(a,cam())['rgb'],np.ones((35,41,3)));a=blob();a['means'][0,0]=1e5;np.testing.assert_array_equal(render(a,cam())['rgb'],np.ones((35,41,3)))
 def test_full_SH_not_DC_only(self):
  a=blob();a.pop('colors');a['SH']=np.zeros((1,3,16));a['means'][0]=[0,1,0];a['SH'][0,0,1]=.2;c=cam();col=colors(a,c);self.assertAlmostEqual(col[0,0],.5-.4886025119029199*.2,12);np.testing.assert_allclose(col[0,1:],[.5,.5])
 def test_covariance_symmetric_positive(self):
  a=blob();a['covariance'][0]=np.array([[.02,.005,.002],[.005,.03,0],[.002,0,.01]]);_,_,S=project_cov(a['means'],a['covariance'],cam(),.0144);np.testing.assert_allclose(S,S.transpose(0,2,1));self.assertGreater(np.linalg.eigvalsh(S).min(),0)
if __name__=='__main__':unittest.main()
