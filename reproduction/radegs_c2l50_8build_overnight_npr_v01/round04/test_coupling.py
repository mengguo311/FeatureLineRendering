import unittest
import env
import numpy as np
from coupling import solve_graph,unary_prior,combine_priors
class CouplingTests(unittest.TestCase):
 def test_disconnected_leaf_has_independent_evidence(self):
  p=np.array([[0.,1.,0.],[0.,0.,1.]]);g,u=unary_prior(p,np.array([True,True]),np.zeros(2));q,m=solve_graph(2,[],[],[],np.zeros(2,int),g,u);np.testing.assert_allclose(q,p,atol=1e-12)
 def test_no_evidence_component_unknown(self):
  q,m=solve_graph(3,[0],[1],[1.],np.zeros(3,int),np.zeros(3),np.zeros((3,2)));self.assertEqual(q.sum(),0);self.assertEqual(m['unanchored_nodes'],3)
 def test_short_wrong_color_band_corrected(self):
  n=31;i=np.arange(n-1);j=i+1;w=np.ones(n-1);p=np.tile([1.,0.],(n,1));p[14:17]=[0,1];degree=np.bincount(np.r_[i,j],weights=np.r_[w,w],minlength=n);g,u=unary_prior(p,np.ones(n,bool),degree);q,m=solve_graph(n,i,j,w,np.zeros(n,int),g,u);self.assertGreater(q[15,0],.65)
 def test_disconnected_depth_layer_not_bridged(self):
  p=np.array([[1.,0.],[1.,0.],[0.,1.],[0.,1.]]);g,u=unary_prior(p,np.ones(4,bool),np.ones(4));q,m=solve_graph(4,[0,2],[1,3],[1,1],np.zeros(4,int),g,u);np.testing.assert_allclose(q,p,atol=1e-12)
 def test_hard_seed_conflict_is_not_hidden(self):
  p=np.tile([1.,0.],(3,1));g,u=unary_prior(p,np.ones(3,bool),np.ones(3));q,m=solve_graph(3,[0,1],[1,2],[1.,1.],np.array([0,2,0]),g,u);np.testing.assert_array_equal(q[1],[0,1]);self.assertEqual(m['fixed'],1)
 def test_global_weight_scaling_invariant(self):
  p=np.array([[1.,0.],[.2,.8],[0.,1.]]);g,u=unary_prior(p,np.ones(3,bool),np.full(3,2.));a,_=solve_graph(3,[0,1,2],[1,2,0],[1,1,1],np.zeros(3,int),g,u);g2,u2=unary_prior(p,np.ones(3,bool),np.full(3,8.));b,_=solve_graph(3,[0,1,2],[1,2,0],[4,4,4],np.zeros(3,int),g2,u2);np.testing.assert_allclose(a,b,atol=1e-10)
 def test_rejected_density_not_weak_positive(self):
  p=np.array([[.99,.01]]);g,u=unary_prior(p,np.array([False]),np.array([4.]));self.assertEqual(g[0],0);q,_=solve_graph(1,[],[],[],np.zeros(1,int),g,u);self.assertEqual(q.sum(),0)
 def test_priors_combine_by_mass_not_label_numbers(self):
  g,p=combine_priors(np.array([1.]),np.array([[1.,0.,0.]]),np.array([3.]),np.array([[0.,0.,1.]]));np.testing.assert_array_equal(g,[4]);np.testing.assert_array_equal(p,[[.25,0,.75]])
if __name__=='__main__':unittest.main()
