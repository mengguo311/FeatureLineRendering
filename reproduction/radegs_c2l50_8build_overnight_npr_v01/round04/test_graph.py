import unittest
from unittest.mock import patch
import env
import numpy as np
from graph import build_graph,transfer_priors,view_seed_policy
from geometry import correspond
class GraphTests(unittest.TestCase):
 def data(self):
  a=dict(world=np.zeros((2,3)),i=np.array([0]),j=np.array([1]),d=np.array([1.]),color=np.array([[0.,0,0],[.2,.2,.2]]));return [a,a]
 def test_cross_ablation_exact(self):
  with patch('graph.links',return_value=(np.array([0]),np.array([1]),np.array([1,0]))):
   a=build_graph(self.data(),'coupled');b=build_graph(self.data(),'no_cross')
  self.assertEqual(len(b[0]),2);self.assertEqual(len(a[0]),4);np.testing.assert_array_equal(a[0][:2],b[0]);np.testing.assert_array_equal(a[2][:2],b[2])
 def test_geometry_pair_removes_only_edge_color(self):
  with patch('graph.links',return_value=(np.array([],int),np.array([],int),np.array([0,0]))):
   a=build_graph(self.data(),'coupled');b=build_graph(self.data(),'geometry_pair')
  np.testing.assert_array_equal(a[0],b[0]);self.assertTrue((b[2]>a[2]).all());np.testing.assert_array_equal(b[2],[1,1])
 def test_unary_only_has_no_graph(self):
  a=build_graph(self.data(),'unary_seeded');self.assertEqual(len(a[0]),0)
 def test_projected_observation_duplication_not_more_mass(self):
  ids=np.array([0,1]);q=np.array([[1.,0.],[0.,1.]]);w=np.array([.5,.2]);a=transfer_priors(2,ids,q,w,2);b=transfer_priors(2,np.repeat(ids,3),np.repeat(q,3,axis=0),np.repeat(w,3),2);np.testing.assert_allclose(a[0],b[0],atol=1e-15);np.testing.assert_array_equal(a[1],b[1])
 def test_reserved_seed_policy_no_height(self):
  s=np.array([1,2,3]);np.testing.assert_array_equal(view_seed_policy(s,False),[0,0,0]);np.testing.assert_array_equal(view_seed_policy(s,True),s)
 def test_real_occluded_point_no_positive_link(self):
  c=dict(extrinsic=np.eye(4).tolist(),fx=100.,fy=80.,cx=2.,cy=2.,width=5,height=5);z=np.ones((5,5));alpha=np.ones((5,5));state,uv=correspond(np.array([[0.,0.,2.]]),np.array([[2.,2.]]),c,c,z,alpha);self.assertEqual(state[0],2)
if __name__=='__main__':unittest.main()
