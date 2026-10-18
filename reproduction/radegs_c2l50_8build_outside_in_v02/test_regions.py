import unittest
from env import *
from regions import fit_model,predict_features,make_features,region_gate,mutual_pairs,soft_source_region
class RegionTests(unittest.TestCase):
 def toy(self):
  rng=np.random.default_rng(15);X=np.r_[rng.normal([0,0,0],.015,(90,3)),rng.normal([0,0,1],.015,(90,3)),rng.normal([0,0,2],.015,(90,3))];rgb=np.repeat([[.08,.07,.05],[.45,.3,.15],[.2,.65,.15]],90,axis=0);width=np.repeat([.12,.005,.02],90);return X,rgb,width
 def test_three_coarse_blocks_and_replay(self):
  X,rgb,w=self.toy();model=fit_model(X,rgb,w,3,'shared_xyz_lab_width');r=predict_features(X,rgb,w,model);labs=[np.unique(r['labels'][i*90:(i+1)*90]) for i in range(3)];self.assertTrue(all(len(q)==1 and q[0]>0 for q in labs));self.assertEqual(len(set(int(q[0]) for q in labs)),3);np.testing.assert_array_equal(r['labels'],predict_features(X,rgb,w,model)['labels'])
 def test_unseen_not_forced_into_cluster(self):
  X,rgb,w=self.toy();m=fit_model(X,rgb,w,3,'shared_xyz_lab_width');r=predict_features(X+100,rgb,w,m);self.assertTrue((r['labels']==0).all())
 def test_equal_affinity_unknown(self):
  X,rgb,w=self.toy();m=fit_model(X,rgb,w,3,'shared_xyz_lab_width');m['centers'][:]=m['centers'][0];r=predict_features(X,rgb,w,m);self.assertTrue((r['labels']==0).all())
 def test_id_permutation_not_false_mismatch(self):
  ab={1:(3,.9),2:(1,.9)};ba={3:(1,.95),1:(2,.9)};self.assertEqual(mutual_pairs(ab,ba),[(1,3),(2,1)])
 def test_same_color_id_not_evidence(self):
  self.assertEqual(mutual_pairs({1:(1,.4),2:(2,.6)},{1:(1,.9),2:(2,.9)}),[])
 def test_multiple_blocks_not_semantic_success(self):
  self.assertEqual(region_gate(3,.1,False),'NO_GO');self.assertEqual(region_gate(1,.1,True),'NO_GO');self.assertEqual(region_gate(3,.1,True),'GO_PROXY')
 def test_one_source_kernel_two_regions_soft_unknown(self):
  p,unknown=soft_source_region([1,2],[.5,.5],2);np.testing.assert_allclose(p,[.5,.5]);self.assertTrue(unknown)
 def test_rgb_baseline_same_feature_budget(self):
  X,rgb,w=self.toy();m=fit_model(X,rgb,w,3,'shared_rgb_only');self.assertEqual(m['centers'].shape,(3,3));f=make_features(X,rgb,w,m);np.testing.assert_allclose(f,make_features(X+2,rgb,w,m))
if __name__=='__main__':unittest.main()
