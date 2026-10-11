import unittest
from start_observers import ready
class ObserverAdmission(unittest.TestCase):
 def test_dead_preflight_PID_cannot_admit_observers(self):
  self.assertFalse(ready({'config_sha256':'ok','runner_pid':12,'status':'WAITING_FOR_LOW_LOAD_GPU'},'ok',1026,lambda pid:None))
 def test_live_matching_own_runner_admits(self):
  self.assertTrue(ready({'config_sha256':'ok','runner_pid':12,'status':'WAITING_FOR_LOW_LOAD_GPU'},'ok',1026,lambda pid:{'uid':1026}))
 def test_wrong_owner_hash_or_failed_state_reject(self):
  s={'config_sha256':'ok','runner_pid':12,'status':'WAITING_FOR_LOW_LOAD_GPU'}
  self.assertFalse(ready(s,'ok',1026,lambda pid:{'uid':900}))
  self.assertFalse(ready(s,'wrong',1026,lambda pid:{'uid':1026}))
  self.assertFalse(ready(dict(s,status='ENGINEERING_NOT_READY'),'ok',1026,lambda pid:{'uid':1026}))
if __name__=='__main__':unittest.main(verbosity=2)
