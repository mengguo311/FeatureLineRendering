from env import *
import unittest
from protocol import training,pack,authorize_fit
class Protocol(unittest.TestCase):
 def test_null_preserves_multiset_and_budget(self):
  x=np.array([[.8,.1,.1],[.7,.2,.1],[.1,.8,.1],[.2,.7,.1]]);y=np.array([1,1,2,2]);a=training(x,y,'chromaticity',2);b=training(x,y,'shuffled_chromaticity',2)
  np.testing.assert_array_equal(np.sort(a['features'],axis=0),np.sort(b['features'],axis=0));np.testing.assert_array_equal(a['labels'],b['labels']);np.testing.assert_array_equal(a['eligible'],b['eligible']);np.testing.assert_array_equal(b['features'],training(x,y,'shuffled_chromaticity',2)['features'])
 def test_missing_class_refused(self):
  with self.assertRaises(ValueError):training(np.array([[.2,.1,.1],[0,0,0]]),np.array([1,2]),'chromaticity',2)
 def test_reserved_not_fit(self):
  with self.assertRaises(ValueError):authorize_fit('ficus',['train_r_80','test_r_14'])
 def test_two_build_only(self):
  authorize_fit('ficus',['train_r_80','train_r_7'])
 def test_mask_coverage_unknown(self):
  m=np.array([[1,1],[0,1]],bool);u=np.array([[0,0],[1,0]],bool);a=pack(m,u,np.array([1,0,2]),np.array([[1,0],[0,0],[0,1.]]),np.zeros((3,2)),np.array([1,0,1],bool));np.testing.assert_array_equal(a['unknown'],[[0,1],[1,0]]);assert a['labels'][1,0]==0;assert (a['source_uv']==[[0,0],[1,0],[1,1]]).all()
 def test_grey_classes_stay_unknown(self):
  from density import fit_density,predict
  t=training(np.array([[.1,.1,.1],[.8,.8,.8]]),np.array([1,2]),'chromaticity',2);m=fit_density([(t['features'],t['labels'])],2);l,q,d=predict(m,t['features']);assert not l.any();np.testing.assert_allclose(q,.5)
 def test_scalar_samples_same_label(self):
  from density import fit_density,predict
  x=np.array([[.7,.2,.1],[.14,.04,.02],[.1,.7,.2],[.02,.14,.04]]);y=np.array([1,1,2,2]);t=training(x,y,'chromaticity',2);m=fit_density([(t['features'],t['labels'])],2);l,q,d=predict(m,t['features']);np.testing.assert_array_equal(l,y)
 def test_raw_training_exact(self):
  x=np.array([[0,0,0],[.9,.2,.1]]);y=np.array([1,2]);t=training(x,y,'raw_rgb',2);np.testing.assert_array_equal(t['features'],x)
if __name__=='__main__':unittest.main()
