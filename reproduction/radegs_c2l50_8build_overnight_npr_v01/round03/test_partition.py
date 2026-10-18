import unittest
import env
import numpy as np
from partition import dtu_seeds,infer_image,shuffle_labels,select_views
from density import fit_density
class PartitionTests(unittest.TestCase):
 def test_disjoint_dtu_seeds(self):
  shape=(4,6);angle=np.tile([0,0,35,45,60,90],(4,1));ar=dict(valid=np.ones(shape,bool),upright=angle<=20,angle=angle,peripheral=np.ones(shape,bool),central=np.ones(shape,bool));s=dtu_seeds(ar,2048);self.assertTrue((s[:,:2]==1).all());self.assertTrue((s[:,2:]==2).all())
 def test_uncertain_geometry_not_seeded(self):
  ar=dict(valid=np.array([[False,True,True]]),upright=np.array([[True,False,False]]),angle=np.array([[0.,28.,80.]]),peripheral=np.ones((1,3),bool),central=np.ones((1,3),bool));s=dtu_seeds(ar);np.testing.assert_array_equal(s,[[0,0,2]])
 def test_fixed_seed_cap(self):
  a=np.tile([0.,60.],(30,20));ar=dict(valid=np.ones(a.shape,bool),upright=a==0,angle=a,peripheral=np.ones(a.shape,bool),central=np.ones(a.shape,bool));s=dtu_seeds(ar,7);self.assertEqual((s==1).sum(),7);self.assertEqual((s==2).sum(),7);np.testing.assert_array_equal(s,dtu_seeds(ar,7))
 def test_mask_holes_preserved(self):
  x=np.array([[.8,.1,.1],[.1,.8,.1]]);m=fit_density([(x,np.array([1,2]))],2);rgb=np.tile(x[0],(4,5,1));mask=np.ones((4,5),bool);mask[1,2]=False;l,u,q,d=infer_image(m,rgb,mask);self.assertEqual(l[1,2],0);self.assertFalse(u[1,2]);self.assertEqual(q[1,2].sum(),0)
 def test_inference_unknown_no_forced_seed(self):
  x=np.array([[.8,.1,.1],[.1,.8,.1]]);m=fit_density([(x,np.array([1,2]))],2);rgb=np.tile([.1,.1,.9],(3,3,1));l,u,_,_=infer_image(m,rgb,np.ones((3,3),bool));self.assertFalse(l.any());self.assertTrue(u.all())
 def test_shuffle_preserves_source_positions_and_counts(self):
  s=np.array([0,1,2,3,0,1,2,3,0,1,2,3]);b=shuffle_labels(s);np.testing.assert_array_equal(s==0,b==0);np.testing.assert_array_equal(np.bincount(s),np.bincount(b));np.testing.assert_array_equal(b,shuffle_labels(s));self.assertTrue((b!=s).any())
 def test_dev_only_not_target_leak(self):
  views=[('dev','payload'),('aux','payload2')];self.assertEqual(select_views(views,'dev_only'),views[:1]);self.assertEqual(select_views(views,'pooled_rgb'),views)
if __name__=='__main__':unittest.main()
