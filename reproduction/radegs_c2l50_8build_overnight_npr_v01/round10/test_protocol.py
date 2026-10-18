from env import *
import unittest
from protocol import fit_supported,predict_supported,pack_supported
sys.path.append(str(CODE.parent/'round09'))
from likelihood import fit,predict
class Protocol(unittest.TestCase):
 def data(self):
  x=np.array([[.8,.2,.1],[.8,.2,.1],[.1,.7,.3],[.1,.7,.3]]);t=np.array([[.1,.5,.5],[.1,.5,.5],[.9,.5,.5],[.9,.5,.5]]);y=np.array([1,1,2,2]);return [(x,t,y),(x.copy(),t.copy(),y.copy())]
 def test_all_valid_same_frozen_model(self):
  data=self.data();m=fit_supported('ficus',['train_r_80','train_r_7'],data,2,[np.ones(4,bool)]*2);n=fit(data,2,'rgb_texture')
  for k in m:np.testing.assert_array_equal(m[k],n[k])
 def test_unavailable_seed_refuses_not_drops(self):
  with self.assertRaises(ValueError):fit_supported('ficus',['train_r_80','train_r_7'],self.data(),2,[np.array([1,0,1,1],bool),np.ones(4,bool)])
 def test_reserved_not_fit(self):
  with self.assertRaises(ValueError):fit_supported('ficus',['train_r_80','test_r_14'],self.data(),2,[np.ones(4,bool)]*2)
 def test_valid_predict_exact(self):
  d=self.data();m=fit(d,2,'rgb_texture');a=predict_supported(m,d[0][0],d[0][1],np.ones(4,bool));b=predict(m,d[0][0],d[0][1],'rgb_texture')
  for x,y in zip(a,b):np.testing.assert_array_equal(x,y)
 def test_invalid_not_probability_vote(self):
  d=self.data();m=fit(d,2,'rgb_texture');l,q,den=predict_supported(m,d[0][0],d[0][1],np.array([0,1,1,1],bool));assert l[0]==0 and not q[0].any() and not den[0].any();assert l[1]==1
 def test_all_invalid_no_labels(self):
  d=self.data();m=fit(d,2,'rgb_texture');l,q,den=predict_supported(m,d[0][0],d[0][1],np.zeros(4,bool));assert not l.any() and not q.any() and not den.any()
 def test_pack_preserves_mask_and_uv(self):
  mask=np.array([[1,0],[1,1]],bool);u=np.array([[0,1],[0,0]],bool);e=np.array([[1,1],[0,1]],bool);a=pack_supported(mask,u,np.array([1,0,2],np.uint8),np.zeros((3,2)),np.zeros((3,2)),e);np.testing.assert_array_equal(a['inference_mask'],mask);np.testing.assert_array_equal(a['source_uv'],[[0,0],[0,1],[1,1]]);np.testing.assert_array_equal(a['unknown'],[[0,1],[1,0]]);np.testing.assert_array_equal(a['feature_eligible'],e)
 def test_original_samples_unchanged(self):
  d=self.data();before=[tuple(a.copy() for a in x) for x in d];fit_supported('ficus',['train_r_80','train_r_7'],d,2,[np.ones(4,bool)]*2)
  for a,b in zip(d,before):
   for x,y in zip(a,b):np.testing.assert_array_equal(x,y)
if __name__=='__main__':unittest.main()
