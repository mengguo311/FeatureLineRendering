import unittest,tempfile
from pathlib import Path
import numpy as np
import core

class GeometryTests(unittest.TestCase):
 def setUp(self):
  self.c={'width':21,'height':17,'fx':20.,'fy':22.,'extrinsic':np.eye(4).tolist()}
 def test_roundtrip_pixel_center_and_extrinsic(self):
  c=dict(self.c);e=np.eye(4);t=.35;e[:3,:3]=[[np.cos(t),0,np.sin(t)],[0,1,0],[-np.sin(t),0,np.cos(t)]];e[:3,3]=[.4,-.7,1.];c['extrinsic']=e.tolist()
  uv=np.array([[0.,0.],[10.,8.],[20.,16.],[3.2,5.7]]);z=np.array([2.,3.,4.,1.])
  x=core.backproject(uv,z,c);p,d=core.project(x,c);np.testing.assert_allclose(p,uv,atol=1e-12);np.testing.assert_allclose(d,z,atol=1e-12)
 def test_axis_center(self):
  np.testing.assert_allclose(core.backproject(np.array([[10.,8.]]),np.array([2.]),self.c),[[0,0,2]],atol=1e-14)
 def test_invalid_depth_and_no_near_cut(self):
  z=np.array([1,100,np.nan,0,-1,np.inf]);np.testing.assert_array_equal(core.valid_depth(z),[1,1,0,0,0,0])
 def test_covariance_positive_definite(self):
  C=core.ink_covariance(np.array([[1.,0,0]]),np.array([[0.,0,1]]),np.array([.02]),True);np.testing.assert_allclose(np.linalg.eigvalsh(C)[0],np.sort((np.array([.70,.35,.18])*.02)**2),rtol=1e-12)
 def test_projection_analytic_and_jacobian(self):
  x=np.array([[0,0,2.],[.3,-.1,3.]]);C=np.repeat(np.eye(3)[None]*.01,2,0);uv,z,S=core.project_cov(x,C,self.c,0.)
  np.testing.assert_allclose(S[0],[[1.,0],[0,1.21]],atol=1e-12)
  eps=1e-5;J=np.stack([(core.project(x+np.eye(3)[i]*eps,self.c)[0]-core.project(x-np.eye(3)[i]*eps,self.c)[0])/(2*eps) for i in range(3)],-1)
  np.testing.assert_allclose(S,J@C@J.transpose(0,2,1),rtol=1e-8,atol=1e-9)
 def test_gaussian_center_and_offaxis(self):
  a={'means':np.array([[0.,0,2]]),'covariance':np.eye(3)[None]*(.1**2),'opacity':np.array([.6])}
  rgb=core.render(a,self.c,filter_sigma=0)
  self.assertAlmostEqual(float(rgb[8,10,0]),.4,places=6);self.assertAlmostEqual(float(rgb[8,11,0]),1-.6*np.exp(-.5),places=6)
 def test_true_anisotropic_ellipse(self):
  a={'means':np.array([[0.,0,2]]),'covariance':np.diag([.01,.0025,.0001])[None],'opacity':np.array([.8])};rgb=core.render(a,self.c,filter_sigma=0)
  self.assertLess(rgb[8,11,0],rgb[9,10,0])
 def test_colored_front_to_back_and_input_order(self):
  a={'means':np.array([[0.,0,3],[0.,0,2]]),'covariance':np.repeat(np.eye(3)[None]*.01,2,0),'opacity':np.array([.5,.5]),'colors':np.array([[0.,0,1],[1.,0,0]])};im=core.render(a,self.c,filter_sigma=0)
  np.testing.assert_allclose(im[8,10],[.75,.25,.5],atol=1e-7)
  b={k:v[::-1].copy() for k,v in a.items()};np.testing.assert_array_equal(im,core.render(b,self.c,filter_sigma=0))
 def test_scene_occlusion_not_sprite(self):
  a={'means':np.array([[0.,0,3]]),'covariance':np.eye(3)[None]*.01,'opacity':np.array([.8])};d=np.ones((17,21))*2;alpha=np.ones_like(d)
  np.testing.assert_array_equal(core.render(a,self.c,d,alpha),np.ones((17,21,3)))
  np.testing.assert_array_equal(core.render(a,self.c,d,alpha*0),core.render(a,self.c))
 def test_visibility_hidden_not_negative(self):
  states=core.visibility_class(np.array([3.,2.,1.]),np.array([2.,2.,2.]),np.ones(3),np.ones(3,bool),np.array([False,False,True]),np.ones(3)*.01)
  np.testing.assert_array_equal(states,[2,-1,-2])
 def test_visibility_unknown_and_support(self):
  s=core.visibility_class(np.array([2.,2.,2.]),np.array([2.,np.nan,2.]),np.array([1.,1.,.2]),np.ones(3,bool),np.ones(3,bool),np.ones(3)*.01);np.testing.assert_array_equal(s,[1,0,0])
 def test_close_layers_and_duplicate_view_do_not_merge(self):
  p=np.array([[0,0,1.],[0,0,1.001],[0,0,1.02]]);tan=np.tile([1.,0,0],(3,1));groups=core.group_samples(p,np.array([0,0,1]),np.ones(3)*.001,tan,np.ones(3))
  self.assertEqual(len(groups),3)
 def test_bounded_fusion_distinct_views(self):
  p=np.array([[0,0,1.],[.0004,0,1.],[.0008,0,1.]]);groups=core.group_samples(p,np.array([0,1,2]),np.ones(3)*.001,np.tile([1.,0,0],(3,1)),np.ones(3));self.assertEqual([len(g) for g in groups],[3])
 def test_holdout_creation_forbidden(self):
  core.assert_build_views(['0000','0024','0048'])
  with self.assertRaises(ValueError):core.assert_build_views(['0012'])
 def test_asset_reload_exact_render(self):
  a={'means':np.array([[0.,0,2]]),'covariance':np.eye(3)[None]*.01,'opacity':np.array([.7])}
  with tempfile.TemporaryDirectory(dir=core.TASK) as d:
   f=Path(d)/'a.npz';np.savez(f,**a);b=dict(np.load(f));np.testing.assert_array_equal(core.render(a,self.c),core.render(b,self.c))
if __name__=='__main__':unittest.main(verbosity=2)
