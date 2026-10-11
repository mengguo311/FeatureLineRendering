import copy,unittest
from unittest.mock import patch
import official_control_v02 as control
from test_control import Tests,G
class ExitRaceTests(Tests):
 def setUp(self):
  super().setUp();self.e.close();self.spawned=[]
  from test_control import Child
  def spawn(*a,**kw):self.spawned.append((a,kw));return Child()
  self.e=control.OfficialRunner(self.path,spawn=spawn,query=lambda:copy.deepcopy(G),space_check=lambda:True)
 def test_exited_owned_pid_stale_in_gpu_snapshot_is_not_foreign(self):
  self.e.tick(G,0);self.e.tick(G,60);pid=self.e.child.pid;self.e.identity={'uid':1026,'pgid':pid,'start_ticks':'123'}
  stale=copy.deepcopy(G);stale[0]['contexts']=[{'pid':pid,'type':'C'}]
  with patch.object(control.runner,'process_identity',return_value=None),patch.object(self.e,'owned_pids',return_value=set()),patch.object(self.e,'request_own_stop') as stop:
   self.e.tick(stale,65);stop.assert_not_called()
  self.assertIsNone(self.e.stop_time)
 def test_reused_owned_pid_is_still_foreign(self):
  self.e.tick(G,0);self.e.tick(G,60);pid=self.e.child.pid;self.e.identity={'uid':1026,'pgid':pid,'start_ticks':'123'}
  sample=copy.deepcopy(G);sample[0]['contexts']=[{'pid':pid,'type':'C'}]
  with patch.object(control.runner,'process_identity',return_value={'uid':999,'pgid':pid,'start_ticks':'456'}),patch.object(self.e,'owned_pids',return_value=set()),patch.object(self.e,'request_own_stop') as stop:
   self.e.tick(sample,65);stop.assert_called_once()
if __name__=='__main__':unittest.main(verbosity=2)
