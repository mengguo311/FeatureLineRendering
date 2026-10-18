from env import *
import unittest
from binding import apply_seed_policy
class BindingTests(unittest.TestCase):
 def setUp(self):
  self.d=dict(view='dev',mask=np.ones((2,2),bool),seeds=np.array([1,1,2,2]),unary=np.array([[.9,.1]]*4),world=np.arange(12).reshape(4,3));self.e=dict(target_uv=np.array([[0,0],[1,0],[0,1],[1,1]]),target_seed_labels=np.array([1,1,2,2]),predicted=np.array([1,2,2,2]))
 def test_only_seed_changes(self):
  a,m=apply_seed_policy(self.d,self.e,'aux','withdraw_conflict');np.testing.assert_array_equal(a['seeds'],[1,0,2,2]);np.testing.assert_array_equal(a['world'],self.d['world']);np.testing.assert_array_equal(a['unary'],self.d['unary']);np.testing.assert_array_equal(self.d['seeds'],[1,1,2,2])
 def test_reserved_cannot_add_seed(self):
  d=dict(self.d,view='reserved',seeds=np.zeros(4,int));a,m=apply_seed_policy(d,None,None,'withdraw_conflict');self.assertFalse(a['seeds'].any());self.assertFalse(m.any())
 def test_missing_crossfit_for_build_refused(self):
  with self.assertRaises(ValueError):apply_seed_policy(self.d,None,None,'withdraw_conflict')
 def test_self_evidence_refused(self):
  with self.assertRaises(ValueError):apply_seed_policy(self.d,self.e,'dev','withdraw_conflict')
 def test_complete_uv_coverage_required(self):
  e={k:v[:-1] for k,v in self.e.items()}
  with self.assertRaises(ValueError):apply_seed_policy(self.d,e,'aux','withdraw_conflict')
if __name__=='__main__':unittest.main()
