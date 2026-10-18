import unittest
import env
import numpy as np
from evaluation import agreement
class EvidenceTests(unittest.TestCase):
 def test_occluded_not_opposing_vote(self):
  state=np.r_[np.ones(40,int),np.full(60,2)];target=np.r_[np.ones(40,int),np.full(60,-1)];r=agreement(state,target,3);self.assertTrue(r['eligible']);self.assertEqual(r['dominant'],1);self.assertEqual(r['known'],40)
 def test_unknown_not_success(self):
  state=np.ones(80,int);target=np.r_[np.ones(30,int),np.zeros(50,int)];r=agreement(state,target,3);self.assertFalse(r['eligible']);self.assertEqual(r['target_unknown'],50)
 def test_tiny_visible_support_not_claim(self):
  state=np.r_[np.ones(30,int),np.full(200,2)];target=np.r_[np.ones(30,int),np.full(200,-1)];r=agreement(state,target,3);self.assertFalse(r['eligible']);self.assertEqual(r['dominant'],1)
 def test_visible_counterevidence_real(self):
  state=np.ones(80,int);target=np.r_[np.ones(40,int),np.full(40,2)];r=agreement(state,target,3);self.assertTrue(r['eligible']);self.assertEqual(r['dominant'],.5)
 def test_no_visible_no_identity(self):
  r=agreement(np.full(40,2),np.full(40,-1),3);self.assertFalse(r['eligible']);self.assertEqual(r['known'],0);self.assertEqual(r['matched_to'],0)
if __name__=='__main__':unittest.main()
