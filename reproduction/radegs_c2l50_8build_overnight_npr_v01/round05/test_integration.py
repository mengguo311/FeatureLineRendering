from env import *
import unittest
from binding import apply_seed_policy
from experiment import infer_arrays
class IntegrationTests(unittest.TestCase):
 def data(self):
  return dict(view='dev',mask=np.ones((1,4),bool),world=np.zeros((4,3)),color=np.zeros((4,3)),seeds=np.array([1,1,0,2]),i=np.array([0,1,2]),j=np.array([1,2,3]),d=np.ones(3),unary=np.array([[1.,0],[0.,1],[0.,1],[0.,1]]),accepted=np.ones(4,bool))
 def changed(self,mode):
  d=self.data();e=dict(target_uv=np.array([[0,0],[1,0],[3,0]]),target_seed_labels=np.array([1,1,2]),predicted=np.array([1,2,2]));return apply_seed_policy(d,e,'aux',mode)[0]
 def test_retraction_enters_actual_solver(self):
  a,_=infer_arrays([self.data()],'withdraw_conflict');b,_=infer_arrays([self.changed('withdraw_conflict')],'withdraw_conflict');self.assertEqual(a['probability'][1,1],0);self.assertGreater(b['probability'][1,1],.1)
 def test_only_dirichlet_set_changes(self):
  a,_=infer_arrays([self.data()],'withdraw_conflict');b,_=infer_arrays([self.changed('withdraw_conflict')],'withdraw_conflict')
  for k in ['i','j','weight','gamma','prior','view_offsets']:np.testing.assert_array_equal(a[k],b[k])
 def test_random_same_graph_and_precision(self):
  a,_=infer_arrays([self.changed('withdraw_conflict')],'withdraw_conflict');b,_=infer_arrays([self.changed('withdraw_random')],'withdraw_random')
  for k in ['i','j','weight','gamma','prior']:np.testing.assert_array_equal(a[k],b[k])
  self.assertEqual(np.count_nonzero(a['seeds']),np.count_nonzero(b['seeds']))
 def test_empty_evidence_unknown(self):
  d=self.data();d['accepted'][:]=False;d['seeds'][:]=0;a,_=infer_arrays([d],'withdraw_conflict');self.assertFalse(a['probability'].any())
if __name__=='__main__':unittest.main()
