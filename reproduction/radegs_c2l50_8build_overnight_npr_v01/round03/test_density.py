import unittest
import env
import numpy as np
from density import fit_density,predict
class DensityTests(unittest.TestCase):
 def simple(self):
  x=np.array([[.8,.1,.1]]*40+[[.1,.8,.1]]*40);y=np.repeat([1,2],40);return x,y
 def test_separated_colors(self):
  x,y=self.simple();m=fit_density([(x,y)],2);l,q,d=predict(m,x);np.testing.assert_array_equal(l,y);self.assertTrue(np.all(q.max(1)>.99))
 def test_shared_color_unknown(self):
  x=np.repeat([[.3,.3,.3]],80,axis=0);y=np.repeat([1,2],40);l,q,d=predict(fit_density([(x,y)],2),x);self.assertFalse(l.any());np.testing.assert_allclose(q,.5,atol=1e-12)
 def test_unseen_color_rejected(self):
  x,y=self.simple();l,q,d=predict(fit_density([(x,y)],2),np.array([[.1,.1,.9]]));self.assertEqual(l[0],0)
 def test_sample_replication_view_balance(self):
  x,y=self.simple();a=fit_density([(x,y),(x*.8,y)],2);b=fit_density([(np.repeat(x,3,axis=0),np.repeat(y,3)),(x*.8,y)],2);np.testing.assert_array_equal(a['hist'],b['hist']);np.testing.assert_array_equal(a['threshold'],b['threshold'])
 def test_label_permutation(self):
  x,y=self.simple();a=fit_density([(x,y)],2);b=fit_density([(x,3-y)],2);np.testing.assert_array_equal(a['hist'],b['hist'][::-1]);l,_,_=predict(b,x);np.testing.assert_array_equal(l,3-y)
 def test_missing_class_invalid(self):
  x,y=self.simple()
  with self.assertRaises(ValueError):fit_density([(x,np.ones(len(y),int))],2)
 def test_no_spatial_connectivity_needed(self):
  x,y=self.simple();m=fit_density([(x,y)],2);l,_,_=predict(m,x[[0,50,1,49]]);np.testing.assert_array_equal(l,y[[0,50,1,49]])
 def test_finite_domain_validation(self):
  x,y=self.simple();x[0,0]=np.nan
  with self.assertRaises(ValueError):fit_density([(x,y)],2)
if __name__=='__main__':unittest.main()
