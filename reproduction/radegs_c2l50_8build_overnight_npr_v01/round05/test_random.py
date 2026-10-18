from test_policy import ConflictTests
import unittest
import numpy as np
class RandomTests(ConflictTests):
 def test_random_budget_each_class(self):
  a,m=self.go(mode='withdraw_random');_,c=self.go()
  for k in [1,2,3]:self.assertEqual(int(((self.s==k)&m).sum()),int(((self.s==k)&c).sum()))
 def test_random_determinism(self):
  a,m=self.go(mode='withdraw_random');b,n=self.go(mode='withdraw_random');np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(m,n)
 def test_original_unmodified(self):
  before=self.s.copy();a,m=self.go(mode='withdraw_random');np.testing.assert_array_equal(self.s,before);self.assertTrue(np.all(a[(a>0)]==before[(a>0)]));self.assertFalse(m[self.s==0].any())
 def test_zero_withdrawal_unchanged(self):
  a,m=self.go(mode='withdraw_random',predicted=self.y);np.testing.assert_array_equal(a,self.s);self.assertFalse(m.any())
if __name__=='__main__':
 suite=unittest.TestSuite(RandomTests(n) for n in ['test_random_budget_each_class','test_random_determinism','test_original_unmodified','test_zero_withdrawal_unchanged']);r=unittest.TextTestRunner().run(suite);raise SystemExit(not r.wasSuccessful())
