from env import *
import unittest
from test_color import ColorTests
from appearance import render_mode,activate_source
class RenderTests(unittest.TestCase):
 def test_geometry_invariant_transparency(self):
  a=ColorTests().asset();c,_=ColorTests().cameras();a['means'][1]=[0,0,3];b=render_mode(a,c,'full_sh',c)
  for arm in ['dc_only','anchor_sh']:
   x=render_mode(a,c,arm,c)
   for k in ['alpha','median_center_z','expected_center_z']:np.testing.assert_array_equal(x[k],b[k])
  np.testing.assert_array_equal(render_mode(a,c,'anchor_sh',c)['rgb'],b['rgb'])
  self.assertGreater(b['alpha'].max(),.5)
 def test_transparent_source_background(self):
  a=ColorTests().asset();a['opacity']*=0;c,_=ColorTests().cameras()
  for arm in ['full_sh','dc_only','anchor_sh']:
   r=render_mode(a,c,arm,c,background=(.2,.4,.7));np.testing.assert_allclose(r['rgb'],np.broadcast_to([.2,.4,.7],r['rgb'].shape),atol=3e-8,rtol=0);self.assertEqual(r['alpha'].max(),0)
 def test_filter_inf_source_preserved(self):
  names=['x','y','z','opacity',*[f'scale_{i}' for i in range(3)],*[f'rot_{i}' for i in range(4)],*[f'f_dc_{i}' for i in range(3)],'filter_3D']
  r=np.zeros(1,dtype=[(n,'f4') for n in names]);r['z']=2;r['opacity']=np.inf;r['rot_0']=1;r['filter_3D']=1;old=r.copy();a=activate_source(r,1)
  np.testing.assert_array_equal(r,old);np.testing.assert_allclose(a['covariance'][0],2*np.eye(3),atol=0,rtol=0);self.assertAlmostEqual(a['opacity'][0],1/np.sqrt(8),14)
 def test_projection_full_intrinsics(self):
  a=ColorTests().asset();c,_=ColorTests().cameras();uv,z=project(a['means'],c);np.testing.assert_allclose(uv,[[23.4,25.7],[23.4+80*.1/3,25.7]],atol=1e-14);np.testing.assert_allclose(unproject(uv,z,c),a['means'],atol=1e-14)
 def test_source_permutation_without_depth_ties(self):
  a=ColorTests().asset();c,_=ColorTests().cameras();b={k:v[::-1].copy() for k,v in a.items()}
  for arm in ['full_sh','dc_only','anchor_sh']:
   x=render_mode(a,c,arm,c);y=render_mode(b,c,arm,c)
   for k in x:np.testing.assert_array_equal(x[k],y[k])
 def test_plain_renderer_full_exact(self):
  import renderer as jr
  a=ColorTests().asset();c,_=ColorTests().cameras();x=jr.render(a,c);y=render_mode(a,c,'full_sh',c)
  for k in x:np.testing.assert_array_equal(x[k],y[k])
if __name__=='__main__':unittest.main(verbosity=2)
