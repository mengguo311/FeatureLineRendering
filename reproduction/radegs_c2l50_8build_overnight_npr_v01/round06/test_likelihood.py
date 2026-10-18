from env import *
import unittest
import numpy as np
from likelihood import fit,predict,shuffle,fit_rgb
class LikelihoodTests(unittest.TestCase):
 def data(self):
  y=np.repeat(np.arange(1,4),32);x=np.full((96,3),.5);f=np.repeat([[.05,.1,.1],[.4,.5,.5],[.9,.95,.95]],32,axis=0);e=np.ones(96,bool);return x,y,f,e
 def test_same_color_shape_has_information(self):
  x,y,f,e=self.data();m=fit([(x,y,f,e)],3);lab,_,_=predict(m,x,f,e);np.testing.assert_array_equal(lab,y)
 def test_unknown_morphology_exact_rgb_fallback(self):
  x,y,f,e=self.data();m=fit([(x,y,f,e)],3);a=predict(m,x,f,e*False);b=predict(m,x,f,e*False,use_shape=False)
  for u,v in zip(a,b):np.testing.assert_array_equal(u,v)
  self.assertFalse(a[0].any())
 def test_view_and_resampling_balance(self):
  x,y,f,e=self.data();a=fit([(x,y,f,e)],3);b=fit([(np.repeat(x,3,0),np.repeat(y,3),np.repeat(f,3,0),np.repeat(e,3)),(x,y,f,e)],3)
  for k in a:np.testing.assert_allclose(a[k],b[k],rtol=0,atol=1e-15)
 def test_shuffle_keeps_budget_not_labels(self):
  x,y,f,e=self.data();g,q=shuffle(f,e);np.testing.assert_array_equal(np.sort(g,axis=0),np.sort(f,axis=0));np.testing.assert_array_equal(np.sort(q),np.sort(e));self.assertFalse(np.array_equal(g,f));np.testing.assert_array_equal(shuffle(f,e)[0],g)
 def test_insufficient_class_not_fabricated(self):
  x,y,f,e=self.data();e[y==3]=False
  with self.assertRaises(ValueError):fit([(x,y,f,e)],3)
 def test_rgb_exact_existing_baseline(self):
  x,y,_,_=self.data();a=fit_rgb([(x,y)],3)
  import sys
  from pathlib import Path
  sys.path.append(str(Path(__file__).resolve().parent.parent/'round03'))
  from density import fit_density
  b=fit_density([(x,y)],3)
  for k in b:np.testing.assert_array_equal(a[k],b[k])
if __name__=='__main__':unittest.main(verbosity=2)
