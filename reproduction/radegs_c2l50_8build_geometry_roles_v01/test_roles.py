import unittest
from env import *
from geometry_roles import fit_patch,classify,ROLES
class Roles(unittest.TestCase):
 def patch(self,tilt=0,z=2):
  x,y=np.meshgrid(np.linspace(-.02,.02,9),np.linspace(-.01,.01,5));return fit_patch(np.c_[x.ravel(),y.ravel(),z+tilt*x.ravel()],np.ones(x.size),.001)
 def info(self):return dict(center_supported=True,join_pixels=0.,L1=1.,ray_width_pixels=1.,alpha_left=1.,alpha_right=1.,alpha_center=1.,filament_shape=False,rgb_side_difference=0.)
 def test_slanted_single_sheet_not_depth_step(self):
  p=self.patch(3);self.assertTrue(p['valid']);self.assertEqual(classify(p,p,self.info())['role'],ROLES[0])
 def test_two_sheets_angle(self):
  a,b=self.patch(-1),self.patch(1);self.assertEqual(classify(a,b,self.info())['role'],ROLES[1])
 def test_parallel_layers(self):
  x=self.info();x['join_pixels']=10;self.assertEqual(classify(self.patch(),self.patch(z=2.01),x)['role'],ROLES[1])
 def test_texture_alone_not_geometry(self):
  x=self.info();x['rgb_side_difference']=.8;r=classify(self.patch(),self.patch(),x);self.assertEqual(r['role'],ROLES[0]);self.assertTrue(r['appearance_cue'])
 def test_same_kernel_crossing_not_edge_owner(self):
  x=self.info();x['join_pixels']=10;x['L1']=0;self.assertEqual(classify(self.patch(),self.patch(z=2.01),x)['role'],ROLES[3])
 def test_low_support_unknown(self):
  p=fit_patch(np.zeros((3,3)),np.ones(3),.001);self.assertFalse(p['valid']);self.assertEqual(classify(p,p,self.info())['role'],ROLES[4])
 def test_floater_not_surface(self):
  x=self.info();x['center_supported']=False;self.assertEqual(classify(self.patch(),self.patch(),x)['role'],ROLES[4])
 def test_mixed_ray_layers_ambiguous(self):
  x=self.info();x['ray_width_pixels']=20;self.assertEqual(classify(self.patch(),self.patch(),x)['role'],ROLES[3])
 def test_leaf_not_forced_cylinder(self):
  x=self.info();x.update(alpha_left=0,alpha_right=0,filament_shape=False);p=dict(valid=False);self.assertEqual(classify(p,p,x)['role'],ROLES[4])
 def test_filament_is_candidate_only(self):
  x=self.info();x.update(alpha_left=0,alpha_right=0,filament_shape=True);r=classify(dict(valid=False),dict(valid=False),x);self.assertEqual(r['role'],ROLES[2]);self.assertFalse(r['physical_primitive_certified'])
 def test_rigid_and_scale_plane(self):
  p=self.patch(.2);X=np.array(p['points']);q=fit_patch(X*7+[3,4,5],np.ones(len(X)),.007);self.assertAlmostEqual(abs(np.dot(p['normal'],q['normal'])),1,places=10);self.assertEqual(p['valid'],q['valid'])
if __name__=='__main__':unittest.main(verbosity=2)
