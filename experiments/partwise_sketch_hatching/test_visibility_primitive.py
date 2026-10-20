"""Development controls; acceptance fixtures are separate and frozen in protocol."""
import round006_common as common
import argparse
import unittest
import numpy as np
from scipy.ndimage import maximum_filter
import core
import coverage_fixture as f
P=argparse.ArgumentParser();P.add_argument('--backend',choices=['legacy','new'],default='new');ARGS=P.parse_args()
if ARGS.backend=='new':import visibility_primitive as v

def cam():return {'size':128,'focal':128.,'center':np.array([64.,64.]),'R':np.eye(3),'t':np.zeros(3),'eye':np.zeros(3)}
def plane(z=3.,sx=0.,sy=0.,bounds=(8.,8.,120.,120.),pid=1):return {'z0':z,'sx':sx,'sy':sy,'bounds':list(bounds),'id':pid}
def render(planes,ends):
 c=cam();mesh=f.make_mesh(planes,c);path=f.points_on_plane(np.array(ends),planes[0],c)
 if ARGS.backend=='new':return v.render(mesh,[0,1],path,c)
 depth,parts=core.raster_surface(mesh,c);points=core.dense_path(path,c,.45);uv,z=core.project(points,c);pix=np.rint(uv).astype(int)
 pre=np.zeros(depth.shape);np.maximum.at(pre,(pix[:,1],pix[:,0]),.8)
 accepted=core.visible_points(points,c,depth,.006);q=pix[accepted];raw=np.zeros(depth.shape);np.maximum.at(raw,(q[:,1],q[:,0]),.8)
 high=maximum_filter(raw,size=2);high[parts==0]=0
 return {'pre_z':pre,'footprint':maximum_filter(pre,size=2),'high':high,'final_uint8':f.down(high),'scene_depth':depth}

class VisibilityTests(unittest.TestCase):
 def test_slanted_visible_coverage(self):
  a=render([plane(sx=1.5)],[[64.25,24.25],[64.25,104.25]])
  np.testing.assert_array_equal(a['high'],a['footprint'])
 def test_width_does_not_spill_onto_front(self):
  a=render([plane(),plane(2.,bounds=(32.,48.,96.,80.),pid=2)],[[64.25,24.25],[64.25,104.25]])
  self.assertEqual(int(np.count_nonzero(a['high'][48:81,32:97])),0)
  self.assertGreater(float(a['high'][:48].sum()),0)
 def test_owner_edge_against_other_foreground(self):
  a=render([plane(bounds=(8,8,64.4,120)),plane(2.,bounds=(64.5,8,100,120),pid=2)],[[64.25,24.25],[64.25,104.25]])
  self.assertGreater(float(a['footprint'][:,65].sum()),0)
  self.assertEqual(float(a['high'][:,65:].sum()),0)
  self.assertGreater(float(a['high'][:,64].sum()),0)
 def test_inherited_footprint_stencil(self):
  a=render([plane()],[[64.25,24.25],[64.25,104.25]])
  np.testing.assert_array_equal(a['footprint'],maximum_filter(a['pre_z'],size=2))
  self.assertEqual(set(np.nonzero(a['footprint'])[1]),{64,65})
 def test_quantization_aa_order(self):
  a=render([plane()],[[64.25,24.25],[64.25,104.25]])
  np.testing.assert_array_equal(a['final_uint8'],f.down(a['high']))
 @unittest.skipIf(ARGS.backend=='legacy','Candidate finite-site gate API')
 def test_nonfinite_and_nonpositive_depths_rejected(self):
  own=np.array([np.inf,3.,np.nan,3.,0.,-1.,3.]);scene=np.array([np.inf,np.inf,3.,np.nan,3.,3.,3.])
  np.testing.assert_array_equal(v.visibility_gate(own,scene),[False,False,False,False,False,False,True])
 @unittest.skipIf(ARGS.backend=='legacy','Candidate depth API')
 def test_known_triangle_depth_finite_bounds(self):
  m=f.make_mesh([plane(sx=1.5)],cam());uv=np.array([[64.,64.],[80.,64.],[48.,64.],[1.,1.]])
  z,_=v.owner_depth(m,[0,1],cam(),uv)
  np.testing.assert_allclose(z[:3],[3,48/13,48/19],atol=1e-12,rtol=0);self.assertTrue(np.isinf(z[3]))
 @unittest.skipIf(ARGS.backend=='legacy','Candidate ambiguity contract')
 def test_two_owner_layers_rejected(self):
  m=f.make_mesh([plane(),plane(4.,pid=1)],cam())
  with self.assertRaisesRegex(ValueError,'ambiguous'):v.owner_depth(m,[0,1,2,3],cam(),np.array([[64.,64.]]))
 @unittest.skipIf(ARGS.backend=='legacy','Candidate depth API')
 def test_shared_edge_and_face_order(self):
  m=f.make_mesh([plane(sx=.75,sy=.25)],cam());uv=np.array([[64.,64.],[40.,40.],[84.,84.]])
  z,_=v.owner_depth(m,[0,1],cam(),uv);zr,_=v.owner_depth(m,[1,0],cam(),uv)
  np.testing.assert_array_equal(z,zr);np.testing.assert_allclose(z,f.plane_depth(uv,plane(sx=.75,sy=.25),cam()),atol=1e-12)
 @unittest.skipIf(ARGS.backend=='legacy','Candidate finite-site gate API')
 def test_original_tolerance_policy(self):
  np.testing.assert_array_equal(v.visibility_gate(np.array([3.0059,3.0061]),np.array([3.,3.])),[True,False])
 @unittest.skipIf(ARGS.backend=='legacy','Candidate ownership validation')
 def test_empty_or_duplicate_owner_faces_rejected(self):
  m=f.make_mesh([plane()],cam())
  for ids in ([],[0,0]):
   with self.assertRaises(ValueError):v.owner_depth(m,ids,cam(),np.array([[64.,64.]]))

if __name__=='__main__':unittest.main(argv=['test_visibility_primitive'],verbosity=2)
