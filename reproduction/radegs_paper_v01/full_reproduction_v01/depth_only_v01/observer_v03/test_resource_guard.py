import unittest,tempfile,json,os
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import resource_guard
from resource_guard import reserve_ok,same_owner_identity
G=1024**3
class Tests(unittest.TestCase):
 def test_reserve_boundaries(self):
  self.assertTrue(reserve_ok(10*G,50*G));self.assertFalse(reserve_ok(10*G-1,70*G));self.assertFalse(reserve_ok(20*G,50*G-1));self.assertFalse(reserve_ok(None,None))
 def test_foreign_or_reused_pid_never_signaled(self):
  expected={'uid':1026,'start_ticks':'12','pgid':44}
  self.assertTrue(same_owner_identity(dict(expected),expected,1026));self.assertFalse(same_owner_identity(None,expected,1026));self.assertFalse(same_owner_identity(dict(expected,start_ticks='13'),expected,1026));self.assertFalse(same_owner_identity(dict(expected),expected,1002))
 def exercise_stop(self,reused=False,query_error=False):
  with tempfile.TemporaryDirectory(dir='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01') as t:
   root=Path(t);ident={'uid':os.getuid(),'start_ticks':'12','pgid':44};cfg=root/'config.json';out=root/'state.json'
   cfg.write_text(json.dumps({'runner_identity':ident,'runner_pid':44,'output':str(out),'hdd_path':str(root)}))
   identities=[ident,dict(ident,start_ticks='13') if reused else ident]
   with patch.object(resource_guard,'identity',side_effect=identities),patch.object(resource_guard.os,'kill') as kill,patch.object(resource_guard.shutil,'disk_usage',side_effect=OSError('simulated query failure') if query_error else [SimpleNamespace(free=9*G),SimpleNamespace(free=100*G)]):
    resource_guard.monitor(cfg)
    if reused:kill.assert_not_called()
    else:kill.assert_called_once_with(44,resource_guard.signal.SIGTERM)
   self.assertEqual(json.loads(out.read_text())['status'],'LOW_DISK_STOP_REQUESTED')
 def test_low_disk_only_signals_owned_supervisor(self):self.exercise_stop()
 def test_query_failure_requests_own_safe_stop(self):self.exercise_stop(query_error=True)
 def test_reused_pid_before_signal_refused(self):self.exercise_stop(reused=True)
if __name__=='__main__':unittest.main(verbosity=2)
