import unittest
from env import *
from support_graph import pair_sides,aggregate_roles,diagnostic_vertices
CFG=dict(min_weighted_ID_overlap=.15,min_pairing_margin=.05,max_normal_deg=20,max_symmetric_plane_pixels=2,max_center_distance_pixels=20)
def node(ids,center=(0,0,2),normal=(0,0,1),role=0):
 return dict(ids=np.array(ids),mass=np.ones(len(ids))/max(1,len(ids)),valid=True,role_index=role,center=np.array(center),normal=np.array(normal),pixel=.001)
class GraphTests(unittest.TestCase):
 def test_genuine_reversed_pair(self):
  x=[node([1,2]),node([3,4])];y=x[::-1];r=pair_sides(x,y,CFG);self.assertEqual(r['pairing'],'reversed');self.assertEqual(len(r['accepted']),2)
 def test_same_ID_wrong_layer_not_merge(self):
  x=[node([1]),node([2])];y=[node([1],(0,0,2.02)),node([2],(0,0,2.02))];self.assertEqual(pair_sides(x,y,CFG)['accepted'],[])
 def test_wrong_normal_not_merge(self):
  x=[node([1]),node([2])];y=[node([1],normal=(1,0,0)),node([2],normal=(1,0,0))];self.assertEqual(pair_sides(x,y,CFG)['accepted'],[])
 def test_same_kernel_both_sides_ambiguous(self):
  x=[node([1,2]),node([1,2])];self.assertEqual(pair_sides(x,x,CFG)['reason'],'pairing_ambiguous')
 def test_unknown_not_promoted(self):
  x=[node([1],role=4),node([2],role=4)];self.assertEqual(pair_sides(x,x,CFG)['accepted'],[])
 def test_unobserved_is_unknown_multirole_kept(self):
  a=aggregate_roles(5,[(np.array([1]),np.array([1.]),np.array([.7,0,0,0,.3])),(np.array([1]),np.array([1.]),np.array([0,.7,0,0,.3]))]);self.assertTrue(np.array_equal(a['scores'][0],[0,0,0,0,1]));self.assertAlmostEqual(a['scores'][1,0],.35);self.assertAlmostEqual(a['scores'][1,1],.35)
 def test_ink_index_outside_source_refused(self):
  with self.assertRaises(ValueError):aggregate_roles(3,[(np.array([3]),np.ones(1),np.array([1,0,0,0,0]))])
 def test_diagnostic_no_geometry_motion(self):
  s=np.array([(1.,2.,3.),(2.,3.,4.)],dtype=[('x','f4'),('y','f4'),('z','f4')]);before=s.copy();a=aggregate_roles(2,[]);v=diagnostic_vertices(s,a,np.array([1]));self.assertEqual(v['source_index'][0],1);self.assertEqual(v['x'][0],s['x'][1]);self.assertTrue(np.array_equal(s,before))
 def test_ID_order_and_rigid_scale_invariance(self):
  x=[node([2,1]),node([4,3])];y=[node([1,2]),node([3,4])];a=pair_sides(x,y,CFG)
  for q in x+y:q['center']=q['center']*7+[3,4,5];q['pixel']*=7
  self.assertEqual(a['accepted'],pair_sides(x,y,CFG)['accepted'])
if __name__=='__main__':unittest.main(verbosity=2)
