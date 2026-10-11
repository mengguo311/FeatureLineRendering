"""Diagnostic smoke-only gate: real CPU lifecycle, no CUDA or GPU queries."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'runtime'))
from test_scope_runner import Scope,GPU
from safety import atomic_json,sha256
from replay_runner import ReplayRunner
SAMPLE=[{'uuid':GPU,'memory_mib':10000,'total_mib':49140,'free_mib':38000,'util_percent':0,'contexts':[]}]
class Child:
 pid=123456
 code=None
 def poll(self):return self.code
class SmokeOnly(Scope):
 def config(self,**kw):
  p=super().config(entry_id='DTU_scan37_half30k_TSDF',resolution_divisor=2,**kw);c=json.loads(p.read_text());c['stage_commands']={'smoke':['fake']};c['reports']={'smoke':str(self.root/'smoke.report.json')};c['synchronous_replay_only']=True;c['inputs']['scene_entry']=c['entry_id'];atomic_json(p,c);return p
 def make(self,p,query=lambda:SAMPLE):
  e=ReplayRunner(p,spawn=lambda *a,**k:Child(),query=query,space_check=lambda:True);self.engines.append(e);return e
 def test_completion_seals_smoke_and_never_dispatches_train(self):
  p=self.config();e=self.make(p);e.tick(SAMPLE,0);e.tick(SAMPLE,60);self.assertIsNotNone(e.child)
  out=self.root/'output';out.write_text('actual test evidence');atomic_json(e.config['reports']['smoke'],{'stage':'smoke','status':'PASS','attempt':e.attempt,'inputs':e.config['inputs'],'outputs':{str(out):sha256(out)}})
  e.child.code=0;e.tick(SAMPLE,65);e.tick(SAMPLE,70);self.assertEqual(e.state['status'],'CUDA_REPLAY_DIAGNOSTIC_COMPLETE');self.assertFalse(e.state['pilot_evaluation_verified']);self.assertIsNone(e.child)
  e.close();self.engines.remove(e);e=self.make(p);self.assertIsNone(e.pending_stage());out.write_text('changed');self.assertEqual(e.pending_stage(),'smoke')
 def test_stale_half_resolution_provenance_rejected(self):
  p=self.config();c=json.loads(p.read_text());c['inputs']['scene_entry']='DTU_scan37_full30k_TSDF';atomic_json(p,c)
  with self.assertRaises(ValueError):self.make(p)
 def test_training_scope_and_missing_marker_rejected(self):
  for i,changes in enumerate([{'stage_commands':{'smoke':['fake'],'train':['forbidden']}},{'synchronous_replay_only':False},{'resolution_divisor':1,'entry_id':'DTU_scan37_full30k_TSDF'}]):
   p=self.config(name=str(i));c=json.loads(p.read_text());c.update(changes);atomic_json(p,c)
   with self.assertRaises(ValueError):self.make(p)
 def test_failed_query_no_launch_and_failed_smoke_no_retry(self):
  e=self.make(self.config());e.tick(SAMPLE,0);e.tick(None,60);self.assertIsNone(e.child);e.tick(SAMPLE,120);e.tick(SAMPLE,180);e.child.code=1;e.tick(SAMPLE,185);e.tick(SAMPLE,250);self.assertEqual(e.state['status'],'ENGINEERING_NOT_READY');self.assertIsNone(e.child)
def load_tests(loader,tests,pattern):return unittest.TestSuite(SmokeOnly(n) for n in SmokeOnly.__dict__ if n.startswith('test_'))
if __name__=='__main__':unittest.main(verbosity=2)
