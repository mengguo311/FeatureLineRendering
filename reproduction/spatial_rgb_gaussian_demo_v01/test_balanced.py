import unittest
import numpy as np
from balanced import evidence_weight
class BalancedTests(unittest.TestCase):
 def test_no_hard_deletion(self):
  a=evidence_weight(np.array([0,1,2,3]),np.array([3,2,1,0]));self.assertTrue(np.all(a>0));np.testing.assert_array_equal(a,[.4,.4,.4,1.])
 def test_hidden_and_unknown_not_negative(self):
  np.testing.assert_array_equal(evidence_weight(np.array([1,2,3]),np.zeros(3)),[.7,1.,1.])
 def test_support_monotonic_counter_reduces(self):
  a=evidence_weight(np.arange(4),np.zeros(4));self.assertTrue(np.all(np.diff(a)>=0));self.assertLess(evidence_weight(np.array([2]),np.array([1]))[0],a[2])
if __name__=='__main__':unittest.main(verbosity=2)
