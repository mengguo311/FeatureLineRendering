from env import *
import unittest
from policy import withdraw
class ConflictTests(unittest.TestCase):
 def setUp(self):
  self.s=np.array([[1,1,0],[2,3,0]],np.uint8);self.uv=np.array([[0,0],[1,0],[0,1],[1,1]]);self.y=np.array([1,1,2,3]);self.p=np.array([0,2,2,2])
 def go(self,**kw):
  a=dict(seed_image=self.s,target_uv=self.uv,target_labels=self.y,predicted=self.p,training_view='aux',target_view='dev',mode='withdraw_conflict');a.update(kw);return withdraw(**a)
 def test_retract_not_relabel(self):
  a,m=self.go();np.testing.assert_array_equal(a,[[1,0,0],[2,0,0]]);self.assertEqual(int(m.sum()),2)
 def test_unknown_not_contradiction(self):
  a,m=self.go(predicted=np.zeros(4,int));np.testing.assert_array_equal(a,self.s);self.assertFalse(m.any())
 def test_other_view_only(self):
  with self.assertRaises(ValueError):self.go(training_view='dev')
 def test_exact_original_uv_and_labels(self):
  with self.assertRaises(ValueError):self.go(target_labels=np.array([3,1,2,3]))
 def test_duplicate_seed_rejected(self):
  with self.assertRaises(ValueError):self.go(target_uv=np.array([[0,0],[0,0],[0,1],[1,1]]))
if __name__=='__main__':unittest.main()
