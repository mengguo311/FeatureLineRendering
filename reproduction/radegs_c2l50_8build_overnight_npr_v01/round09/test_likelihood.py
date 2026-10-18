from env import *
import unittest
from likelihood import fit,predict,authorize_fit,pack
from density import fit_density,predict as rgb_predict
class Likelihood(unittest.TestCase):
 def data(self):
  x=np.array([[.8,.2,.1],[.8,.2,.1],[.1,.7,.3],[.1,.7,.3]]);t=np.array([[.1,.5,.5],[.15,.5,.5],[.9,.5,.5],[.85,.5,.5]]);y=np.array([1,1,2,2]);return [(x,t,y)]
 def test_raw_exact(self):
  d=self.data();m=fit(d,2,'raw_rgb');old=fit_density([(x,y) for x,t,y in d],2);a=predict(m,d[0][0],d[0][1],'raw_rgb');b=rgb_predict(old,d[0][0]);
  for x,y in zip(a,b):np.testing.assert_array_equal(x,y)
 def test_texture_rejects_below_frozen_quantile(self):
  x,t,y=self.data()[0];x[:]=.5;m=fit([(x,t,y)],2,'rgb_texture');l,q,d=predict(m,x,t,'rgb_texture');np.testing.assert_array_equal(l,[1,0,2,0]);np.testing.assert_array_equal(q.argmax(1)+1,y)
 def test_repeated_texture_modes_disambiguate_same_color(self):
  x,t,y=self.data()[0];x[:]=.5;t[1]=t[0];t[3]=t[2];m=fit([(x,t,y)],2,'rgb_texture');l,q,d=predict(m,x,t,'rgb_texture');np.testing.assert_array_equal(l,y)
 def test_identical_cues_unknown(self):
  x,t,y=self.data()[0];x[:]=.5;t[:]=.5;m=fit([(x,t,y)],2,'rgb_texture');l,q,d=predict(m,x,t,'rgb_texture');assert not l.any();np.testing.assert_allclose(q,.5)
 def test_raw_ignores_texture(self):
  x,t,y=self.data()[0];m=fit([(x,t,y)],2,'raw_rgb');a=predict(m,x,t,'raw_rgb');b=predict(m,x,1-t,'raw_rgb');
  for q,r in zip(a,b):np.testing.assert_array_equal(q,r)
 def test_texture_only_ignores_rgb(self):
  x,t,y=self.data()[0];m=fit([(x,t,y)],2,'texture_only');a=predict(m,x,t,'texture_only');b=predict(m,1-x,t,'texture_only');
  for q,r in zip(a,b):np.testing.assert_array_equal(q,r)
 def test_fit_reserved_refused(self):
  with self.assertRaises(ValueError):authorize_fit('ficus',['train_r_80','test_r_14'])
 def test_missing_class_refused(self):
  x,t,y=self.data()[0]
  with self.assertRaises(ValueError):fit([(x,t,np.ones(4))],2,'rgb_texture')
 def test_complete_mask_unknown(self):
  m=np.array([[1,0],[1,1]],bool);u=np.array([[0,1],[0,0]],bool);a=pack(m,u,np.array([1,0,2]),np.zeros((3,2)),np.zeros((3,2)));np.testing.assert_array_equal(a['unknown'],[[0,1],[1,0]]);np.testing.assert_array_equal(a['source_uv'],[[0,0],[0,1],[1,1]])
if __name__=='__main__':unittest.main()
