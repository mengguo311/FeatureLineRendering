from env import *
import unittest
from partition import fit_sheet, select_sheets, pair_patch
class PlaneTests(unittest.TestCase):
 def test_slanted_plane_full_cov_points(self):
  x,y=np.meshgrid(np.linspace(-4,4,9),np.linspace(-3,3,7));X=np.c_[x.ravel(),y.ravel(),2+.3*x.ravel()-.2*y.ravel()];r=fit_sheet(X,np.ones(len(X)),np.arange(len(X)),np.arange(len(X))%7,1)
  self.assertTrue(r['valid']);self.assertLess(r['rms_p'],1e-10);self.assertGreater(abs(np.dot(r['normal'],np.array([-.3,.2,1])/np.linalg.norm([-.3,.2,1]))),1-1e-10)
 def test_pixel_not_kernel_is_sample(self):
  X=np.tile(np.array([[0.,0,2],[1,0,2],[0,1,2]]),(50,1));r=fit_sheet(X,np.ones(len(X)),np.tile(np.arange(3),50),np.arange(len(X)),1);self.assertFalse(r['valid']);self.assertEqual(r['unique_pixels'],3)
 def test_rigid_scale_invariance_and_immutable(self):
  x,y=np.meshgrid(np.arange(6.),np.arange(5.));X=np.c_[x.ravel(),y.ravel(),x.ravel()*.2];saved=X.copy();q=np.array([[0,0,1],[1,0,0],[0,1,0]]);args=(np.ones(len(X)),np.arange(len(X)),np.arange(len(X))%8)
  a=fit_sheet(X,*args,.1);b=fit_sheet(X@q.T*7+4,*args,.7);self.assertEqual(a['valid'],b['valid']);self.assertLess(abs(a['rms_p']-b['rms_p']),1e-10);np.testing.assert_array_equal(X,saved)
class SelectionTests(unittest.TestCase):
 def setup_data(self,kind):
  x,y=np.meshgrid(np.linspace(-6,6,17),np.linspace(-4,4,9));x=x.ravel();y=y.ravel();side=np.where(x<0,-1,1);z=np.zeros(len(x)) if kind=='plane' else (np.abs(x)*.8 if kind=='fold' else np.where(x<0,0,8))
  return np.c_[x,y,z],np.ones(len(x)),np.arange(len(x)),np.arange(len(x)),side
 def test_texture_labels_do_not_create_two_sheets(self):
  r=select_sheets(*self.setup_data('plane'),1);self.assertEqual(r['model'],'single');self.assertFalse(r['physical_primitive_certified'])
 def test_real_fold_and_two_depths(self):
  for k in ['fold','layers']:self.assertEqual(select_sheets(*self.setup_data(k),1)['model'],'two')
 def test_same_wide_source_is_not_two_physical_sheets(self):
  X,w,pix,ids,side=self.setup_data('layers');ids=ids%3;r=select_sheets(X,w,pix,ids,side,1);self.assertNotEqual(r['model'],'two');self.assertGreater(r['source_overlap'],.85)
 def test_duplicate_hypotheses_not_confidence_inflation(self):
  a=self.setup_data('fold');r=select_sheets(*a,1);b=tuple(np.repeat(x,4,axis=0) for x in a);q=select_sheets(*b,1);self.assertEqual(r['model'],q['model']);self.assertAlmostEqual(r['two_bic'],q['two_bic'],places=9)
 def test_unknown_empty_refused(self):
  r=select_sheets(np.empty((0,3)),np.empty(0),np.empty(0,int),np.empty(0,int),np.empty(0,int),1);self.assertEqual(r['model'],'REFUSED')
class PairTests(unittest.TestCase):
 def patch(self,ids=(1,2,3),z=0):return dict(valid=True,center=[0,0,z],normal=[0,0,1],ids=list(ids),mass=[1/3]*3)
 def test_geometric_coincidence_without_ID_evidence_refused(self):
  self.assertFalse(pair_patch(self.patch(),self.patch((4,5,6)),1)['eligible'])
 def test_same_source_proxy_two_views_allowed_not_physical_GT(self):
  x=pair_patch(self.patch(),self.patch(),1);self.assertTrue(x['eligible']);self.assertFalse(x['physical_primitive_certified'])
 def test_nearby_parallel_layer_not_same_sheet(self):
  self.assertFalse(pair_patch(self.patch(),self.patch(z=4),1)['eligible'])
 def test_normal_sign_is_not_opposite_plane(self):
  a=self.patch();b=self.patch();b['normal']=[0,0,-1];self.assertTrue(pair_patch(a,b,1)['eligible'])
if __name__=='__main__':unittest.main()
