import unittest,tempfile
from env import *
from io_checks import safe_member,check_members,validate_partition,verify_frozen,gate_downstream
class IntegrityTests(unittest.TestCase):
 def test_unsafe_package_paths(self):
  for name in ['/x','../a','a/../x','a\\x','']:
   self.assertRaises(ValueError,safe_member,name)
  self.assertEqual(safe_member('data/a.npz'),'data/a.npz')
 def test_hash_tampering_detected(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);(p/'x').write_text('a');manifest=dict(members={'x':dict(sha256=sha(p/'x'))});check_members(p,manifest);(p/'x').write_text('b');self.assertRaises(AssertionError,check_members,p,manifest)
 def test_partition_unknown_exhaustive(self):
  m=np.array([[1,1],[1,0]],bool);l=np.array([[1,0],[2,0]],np.int16);u=np.array([[0,1],[0,0]],bool);self.assertTrue(validate_partition(m,l,u));self.assertRaises(AssertionError,validate_partition,m,l,np.zeros((2,2),bool))
 def test_no_labels_outside_subject(self):
  self.assertRaises(AssertionError,validate_partition,np.zeros((1,1),bool),np.ones((1,1),int),np.zeros((1,1),bool))
 def test_frozen_config_unchanged(self):self.assertTrue(verify_frozen())
 def test_NO_GO_never_launches_next_stage(self):
  for s in ['NO_GO','ENGINEERING_INVALID','NOT_RUN','PARTIAL']:self.assertEqual(gate_downstream(s),'NOT_RUN')
  self.assertEqual(gate_downstream('GO_PROXY'),'READY')
if __name__=='__main__':unittest.main()
