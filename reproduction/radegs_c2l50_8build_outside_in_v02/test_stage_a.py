import unittest
from env import *
from anchor import visibility,fit_support_plane,plane_classify,plane_mask,source_only,isolated_coverage
class ATests(unittest.TestCase):
 def fixture(self):
  x,y=np.meshgrid(np.linspace(-2,2,24),np.linspace(-2,2,24));ground=np.c_[x.ravel(),y.ravel(),x.ravel()*0];obj=np.c_[x.ravel()*.3,y.ravel()*.3,np.ones(x.size)];X=np.concatenate([ground,obj,ground,obj]);n=len(ground);v=np.repeat([0,1],2*n);p=np.full(len(X),.01);per=np.tile(np.r_[np.ones(n,bool),np.zeros(n,bool)],2);cen=~per;return X,p,v,per,cen
 def test_same_rgb_different_support_layer(self):
  X,p,v,per,cen=self.fixture();m=fit_support_plane(X,p,v,per,cen);self.assertIsNotNone(m);a=plane_classify(X,p,m);self.assertTrue((a[cen]==1).all());self.assertTrue((a[per]!=1).all())
 def test_sloped_support_not_camera_z_cut(self):
  X,p,v,per,cen=self.fixture();X[:,2]+=.7*X[:,0];m=fit_support_plane(X,p,v,per,cen);self.assertIsNotNone(m);a=plane_classify(X,p,m);self.assertTrue((a[cen]==1).all())
 def test_no_central_separation_refuses(self):
  X,p,v,per,cen=self.fixture();X[:,2]=0;self.assertIsNone(fit_support_plane(X,p,v,per,cen))
 def test_footprint_hole_not_filled(self):
  z=np.ones((9,9));alpha=np.ones((9,9));alpha[4,4]=0;c=dict(width=9,height=9,fx=100,fy=80,cx=4,cy=4,extrinsic=np.eye(4).tolist());m=dict(normal=[0,0,1],offset=0.,sign=1);a,u=plane_mask(z,alpha,c,m);self.assertFalse(a[4,4]);self.assertTrue(a[3,4])
 def test_camera_roundtrip_full_intrinsics(self):
  E=np.eye(4);E[:3,3]=[.3,-.5,.1];c=dict(width=25,height=19,fx=83,fy=127,cx=13.4,cy=7.2,extrinsic=E.tolist());uv=np.array([[2.,3.],[19,10]]);z=np.array([2.,3.]);uv2,z2=projection(unproject(uv,z,c),c);np.testing.assert_allclose(uv,uv2,atol=1e-12);np.testing.assert_allclose(z,z2,atol=1e-12)
 def test_visibility_unknown_occlusion_and_front(self):
  c=dict(width=5,height=5,fx=1000,fy=1100);d=np.ones((5,5))*2;a=np.ones((5,5));q=np.tile([2,2],(5,1));q[-1]=[10,2];a[1,1]=.1
  r=visibility(q,np.array([2.,3.,1.,np.nan,2]),d,a,c);np.testing.assert_array_equal(r,[1,2,4,3,3]);self.assertEqual(visibility([[1,1]],[2],d,a,c)[0],0)
 def test_source_ink_separated(self):
  self.assertTrue(source_only(np.array([0,0])));self.assertRaises(ValueError,source_only,np.array([0,1]))
 def test_alpha_not_subject_if_border_covered(self):
  self.assertFalse(isolated_coverage([np.ones((20,20)),np.ones((20,20))]));a=np.zeros((20,20));a[5:15,5:15]=1;self.assertTrue(isolated_coverage([a,a]))
if __name__=='__main__':unittest.main()
