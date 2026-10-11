import unittest,numpy as np
import multiview as m
import core
class Tests(unittest.TestCase):
 def test_47_distinct_votes(self):
  votes=np.ones((2,47),np.int8);votes[1,10:]=2;s,c,w=m.summarize_votes(votes);np.testing.assert_array_equal(s,[47,10]);np.testing.assert_array_equal(c,[0,0]);np.testing.assert_array_equal(w,[1,1])
 def test_hidden_and_unknown_not_counter(self):
  s,c,w=m.summarize_votes(np.array([[1,2,0,2],[0,0,0,0],[1,-1,1,1]],np.int8));np.testing.assert_array_equal(w,[.7,.7,.4]);np.testing.assert_array_equal(c,[0,0,1])
 def test_density_transmittance(self):
  a=np.array([.1,.5,.95]);np.testing.assert_array_equal(m.density_opacity(a,3),a);np.testing.assert_allclose((1-m.density_opacity(a,12))**4,1-a,atol=1e-12)
 def test_no_majority_and_no_delete(self):
  votes=np.zeros((3,47),np.int8);votes[0,:2]=1;votes[1,:46]=1;votes[1,-1]=-1;s,c,w=m.summarize_votes(votes);np.testing.assert_array_equal(w,[1,.4,.7]);self.assertTrue(np.all(w>0))
 def test_pair_chunk_equivalence_and_visibility(self):
  c={'width':9,'height':9,'fx':10.,'fy':10.,'extrinsic':np.eye(4).tolist()};uv=np.array([[4,4],[4,4],[4,4],[1,1]]);z=np.array([2.,3.,1.,2.]);points=core.backproject(uv,z,c)
  source={'means':points,'pixel':np.ones(4)*.2,'tangent':np.tile([1.,0,0],(4,1)),'fit_valid':np.ones(4,bool)}
  target={'means':np.array([[0.,0,2.]]),'pixel':np.array([.2]),'tangent':np.array([[1.,0,0]]),'fit_valid':np.array([True]),'uv':np.array([[4,4]])}
  maps={'z':np.ones((9,9))*2,'alpha':np.ones((9,9)),'nearest_sample':np.zeros((9,9),int)}
  a=m.pair_votes(source,target,maps,c,1);b=m.pair_votes(source,target,maps,c,99);np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(a,[1,2,-2,-1])
 def test_distinct_groups_layers_nontransitive(self):
  p=np.array([[0,0,1.],[.0008,0,1.],[.0016,0,1.],[0,0,1.1]]);g=core.group_samples(p,np.array([0,1,2,3]),np.ones(4)*.001,np.tile([1.,0,0],(4,1)),np.array([4.,3.,2.,1.]));self.assertEqual(g,[[0,1],[2],[3]])
 def test_generic_build_rejects_holdout(self):
  core.assert_build_views([f'{i:04d}' for i in range(49) if i not in [12,36]])
  with self.assertRaises(ValueError):core.assert_build_views(['0036'])
if __name__=='__main__':unittest.main(verbosity=2)
