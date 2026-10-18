from env import *
import unittest
from validation import compose_weights, visibility_states, evaluate_frozen
class VisibilityTests(unittest.TestCase):
 def test_occluded_unknown_not_negative(self):
  q=visibility_states(np.array([2.,2.,2.,2.,2.]),np.array([1.,np.nan,2.,3.,2.]),np.array([1.,1.,1.,1.,.1]),np.ones(5,bool),.01)
  self.assertEqual(q.tolist(),['OCCLUDED','UNKNOWN','COMPARABLE','IN_FRONT_INCONSISTENT','UNKNOWN'])
 def test_outside_not_visible_counterexample(self):
  self.assertEqual(visibility_states(np.array([3.]),np.array([1.]),np.array([1.]),np.array([False]),.01)[0],'OUT_OF_FRAME')
 def test_depth_order_changes_responsibility_not_alpha(self):
  a=np.array([.9,.8]);w=compose_weights(a,np.array([1.,2.]));v=compose_weights(a,np.array([2.,1.]));np.testing.assert_allclose(w,[.9,.08],atol=1e-14);np.testing.assert_allclose(v,[.18,.8],atol=1e-14);self.assertAlmostEqual(w.sum(),v.sum(),places=14)
 def test_transparent_and_permutation(self):
  a=np.array([.2,0.,.4]);z=np.array([2.,1.,3.]);w=compose_weights(a,z);perm=[2,0,1];v=compose_weights(a[perm],z[perm]);np.testing.assert_allclose(v,w[perm],atol=1e-14)
class FrozenTests(unittest.TestCase):
 def data(self):
  x,y=np.meshgrid(np.arange(4.),np.arange(4.));X=np.c_[x.ravel(),y.ravel(),np.ones(16)*2];q=dict(valid=True,center=[0,0,2],normal=[0,0,1],ids=[0,1,2,3],mass=[.25]*4);return q,X,np.ones(16),np.arange(16)%4,np.arange(16)
 def test_plane_heldout_replay_not_refit(self):
  q,X,w,ids,pix=self.data();s=json.dumps(q);r=evaluate_frozen(q,X,w,ids,pix,.1,1);self.assertTrue(r['eligible']);self.assertEqual(json.dumps(q),s)
 def test_visible_wrong_plane_rejected(self):
  q,X,w,ids,pix=self.data();X[:,2]+=1;self.assertFalse(evaluate_frozen(q,X,w,ids,pix,.1,1)['eligible'])
 def test_hidden_has_no_negative_plane_vote(self):
  q,X,w,ids,pix=self.data();r=evaluate_frozen(q,X,w,ids,pix,.1,0);self.assertEqual(r['state'],'UNOBSERVED');self.assertFalse(r['negative_evidence'])
 def test_source_identity_cannot_be_ink_or_geometric_only(self):
  q,X,w,ids,pix=self.data();r=evaluate_frozen(q,X,w,ids+100,pix,.1,1);self.assertFalse(r['eligible']);self.assertEqual(r['source_overlap'],0)
if __name__=='__main__':unittest.main()
