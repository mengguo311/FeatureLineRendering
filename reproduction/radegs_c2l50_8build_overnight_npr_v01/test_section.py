import unittest
from env import np
from section import split_profile,profile_labels,cross_sections
class SectionTests(unittest.TestCase):
 def profile(self):return np.r_[np.ones(8)*.4,np.ones(10)*.08,np.ones(14)*.75]
 def test_broad_neck_broad(self):
  p=self.profile();m=split_profile(p,np.ones(32,bool));self.assertTrue(m['qualified']);self.assertLessEqual(abs(m['cuts'][0]-8),1);self.assertLessEqual(abs(m['cuts'][1]-18),1)
 def test_monotone_not_forced_three_parts(self):self.assertFalse(split_profile(np.linspace(.1,1,32),np.ones(32,bool))['qualified'])
 def test_flat_not_forced(self):self.assertFalse(split_profile(np.ones(32),np.ones(32,bool))['qualified'])
 def test_missing_not_filled(self):
  v=np.ones(32,bool);v[12:20]=False;self.assertFalse(split_profile(self.profile(),v)['qualified'])
 def test_geometry_scale_invariance(self):
  a=split_profile(self.profile(),np.ones(32,bool));b=split_profile(self.profile()*8,np.ones(32,bool));self.assertEqual(a['cuts'],b['cuts'])
 def test_open_mask_and_unknown_bounds(self):
  l=profile_labels(np.array([-.1,.1,.25,.4,.5625,.9,1.1]),0,1,[8,18],32);np.testing.assert_array_equal(l,[0,1,0,2,0,3,0])
 def test_sections_use_two_independent_views(self):
  rng=np.random.default_rng(1);h=np.repeat((np.arange(32)+.5)/32,20);a=rng.uniform(0,2*np.pi,len(h));w=np.repeat(self.profile(),20);X=np.c_[w*np.cos(a),w*np.sin(a),h];r=cross_sections(X,np.zeros(len(X),int),[0,0,1],32);self.assertFalse(r['valid'].any())
if __name__=='__main__':unittest.main()
