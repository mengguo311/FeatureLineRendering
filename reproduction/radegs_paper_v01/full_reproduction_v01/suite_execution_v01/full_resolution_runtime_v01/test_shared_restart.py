"""Shared policy + durable CPU child adoption; no CUDA imports or GPU calls."""
import json,subprocess,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
from test_scope_runner import Scope,GPU
import suite_runner,runner
from safety import atomic_json

SAMPLE=[{'uuid':GPU,'memory_mib':10000,'total_mib':49140,'free_mib':38500,'util_percent':0,'contexts':[{'pid':987654321,'type':'C'}]}]
class SharedRestart(Scope):
 def make(self,path,spawn=None):
  e=suite_runner.PilotRunner(path,spawn=spawn or (lambda *a,**k:type('Child',(),{'pid':123456,'poll':lambda s:None})()),query=lambda:SAMPLE,space_check=lambda:True);self.engines.append(e);return e
 # The inherited base admission fixtures use the exclusive sample; run only the
 # explicit shared tests below via load_tests, rather than changing its fixture.
 def test_shared_context_baseline_survives_real_CPU_child_adoption(self):
  p=self.config();c=json.loads(p.read_text());c['stage_commands']['smoke']=[sys.executable,'-c','import time; time.sleep(60)'];c['reports']['smoke']=str(self.root/'absent_report.json');atomic_json(p,c)
  e=self.make(p,subprocess.Popen);e.tick(SAMPLE,0);e.tick(SAMPLE,60);original=e.child;self.assertIsNotNone(original)
  try:
   e.close();self.engines.remove(e);new=self.make(p,subprocess.Popen)
   self.assertEqual(new.state['status'],'ADOPTED_OWN_STAGE')
   self.assertEqual(new.baseline,{987654321})
   new.tick(SAMPLE,65);self.assertEqual(new.state['status'],'RUNNING')
   busy=[dict(SAMPLE[0],contexts=SAMPLE[0]['contexts']+[{'pid':987654320,'type':'G'}])]
   new.tick(busy,70);original.wait(timeout=5);new.tick(SAMPLE,75)
   self.assertEqual(new.state['status'],'WAITING_FOR_LOW_LOAD_GPU')
  finally:
   if original.poll() is None:original.terminate();original.wait(timeout=5)
 def test_failedquery_busy_and_actualfree_never_launch(self):
  e=self.make(self.config())
  for t,s in [(0,SAMPLE),(59,None),(60,SAMPLE),(119,[dict(SAMPLE[0],free_mib=12000)]),(180,[dict(SAMPLE[0],util_percent=11)])]:e.tick(s,t)
  self.assertIsNone(e.child)
 def test_scene_scoped_global_lock_and_recheck(self):
  a=self.make(self.config(name='a'));b=self.make(self.config(name='b'))
  a.tick(SAMPLE,0);a.tick(SAMPLE,60);b.tick(SAMPLE,0);b.tick(SAMPLE,60);self.assertIsNone(b.child)
 def test_new_context_safe_stop_and_query_failure(self):
  e=self.make(self.config());e.tick(SAMPLE,0);e.tick(SAMPLE,60)
  with patch.object(e,'request_own_stop') as stop:e.tick(None,65);stop.assert_called_once()
 def test_foreign_arrival_in_final_recheck_does_not_launch(self):
  p=self.config();fresh=[dict(SAMPLE[0],contexts=SAMPLE[0]['contexts']+[{'pid':987654320,'type':'C'}])]
  e=suite_runner.PilotRunner(p,spawn=lambda *a,**k:type('Child',(),{'pid':123456,'poll':lambda s:None})(),query=lambda:fresh,space_check=lambda:True);self.engines.append(e)
  e.tick(SAMPLE,0);e.tick(SAMPLE,60);self.assertIsNone(e.child)

def load_tests(loader,tests,pattern):
 names=[n for n in SharedRestart.__dict__ if n.startswith('test_')]
 return unittest.TestSuite(SharedRestart(n) for n in names)
if __name__=='__main__':unittest.main(verbosity=2)
