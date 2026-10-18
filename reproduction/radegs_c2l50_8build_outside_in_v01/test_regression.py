import unittest
from env import *
from subject import propose,consensus
from protocol import visibility
class Regression(unittest.TestCase):
 def test_actual_cut_thin_open_and_hole(self):
  h=w=72;y,x=np.mgrid[:h,:w];truth=((x-36)**2+(y-36)**2<22**2)&~((x-36)**2+(y-36)**2<7**2);truth[12:37,35]=True;truth[8,30:43]=True
  rgb=np.ones((h,w,3),float);rgb[truth]=[.15,.5,.2];a=np.where(truth,1.,0.);z=np.where(truth,2.+.003*x,0.)
  m,margin,_,_,_=propose(rgb,a,z,dict(fx=100,fy=130),0)
  self.assertGreater((m&truth).sum()/truth.sum(),.99);self.assertFalse(m[36,40]);self.assertTrue(m[8,35]);self.assertFalse(m[0,0])
 def test_translation_uses_world_camera(self):
  E=np.eye(4);E[:3,3]=[.4,-.2,1.];c=dict(extrinsic=E.tolist(),fx=120,fy=90,cx=30,cy=40);uv=np.array([[12.,32.],[36.,43.]]);z=np.array([2.,4.]);x=unproject(uv,z,c);u,d=projection(x,c);np.testing.assert_allclose(u,uv,atol=1e-12);np.testing.assert_allclose(d,z,atol=1e-12)
 def test_rolling_outline_not_fixed_line_veto(self):
  c=dict(width=20,height=20,fx=100,fy=100,cx=10,cy=10,extrinsic=np.eye(4).tolist());dep=np.ones((20,20))*2;alpha=np.ones_like(dep);v=visibility(np.array([[10.,10.]]),np.array([2.]),dep,alpha,c)
  self.assertEqual(v[0],1) # no comparison to any C8 edge/identity: point visible may become interior
 def test_source_whole_alpha_can_be_background(self):
  from subject import seeds
  im=np.ones((60,60,3))*.4;im[15:45,15:45]=.9;a=np.ones((60,60));f,b,_,_=seeds(im,a,a*2,0);self.assertTrue(b[0,0]);self.assertTrue(f[30,30]);self.assertEqual(a[0,0],a[30,30])
if __name__=='__main__':unittest.main()
