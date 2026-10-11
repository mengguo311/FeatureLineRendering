import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from official_control import validate_scope,OfficialRunner,policy
from safety import atomic_json,sha256
G=[{'uuid':policy.GPU,'memory_mib':10000,'total_mib':49140,'free_mib':39000,'util_percent':0,'contexts':[]}]
class Child:
 pid=123456789;code=None
 def poll(self):return self.code
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name);self.spawned=[]
  self.c={'method_variant':'official_code_fix_v01','scene':'scan24','automatic_scene_limit':1,'engineering_ready':True,'purpose':'native_validation','allowed_gpu_uuids':[policy.GPU],'stable_seconds':60,'poll_seconds':60,'state_dir':str(self.p/'state'),'log_dir':str(self.p/'logs'),'cwd':str(self.p),'stage_commands':{'smoke':['fake']},'reports':{'smoke':str(self.p/'report.json')},'inputs':{'method':'test'},'immutable_files':{},'runtime_env':{},'preflight_report':str(self.p/'preflight.json')}
  atomic_json(self.c['preflight_report'],{'passed':True});self.path=self.p/'config.json';atomic_json(self.path,self.c)
  def spawn(*a,**kw):self.spawned.append((a,kw));return Child()
  self.e=OfficialRunner(self.path,spawn=spawn,query=lambda:copy.deepcopy(G),space_check=lambda:True)
 def tearDown(self):self.e.close();self.tmp.cleanup()
 def test_scope_rejects_old_route_and_training_in_validation(self):
  for changes in ({'method_variant':'paper_text'},{'scene':'scan83'},{'allowed_gpu_uuids':['GPU1']},{'stable_seconds':0},{'stage_commands':{'smoke':['fake'],'train':['fake']}}):
   with self.assertRaises(ValueError):validate_scope(dict(self.c,**changes))
 def test_idle_stability_busy_failed_and_recheck(self):
  self.e.tick(None,0);busy=copy.deepcopy(G);busy[0]['util_percent']=11
  self.e.tick(busy,60);self.e.tick(G,120);self.e.tick(G,179);self.assertFalse(self.spawned)
  self.e.tick(G,180);self.assertEqual(len(self.spawned),1);self.assertEqual(self.spawned[0][1]['env']['CUDA_VISIBLE_DEVICES'],policy.GPU)
 def test_new_context_in_immediate_query_does_not_launch(self):
  fresh=copy.deepcopy(G);fresh[0]['contexts']=[{'pid':999999999,'type':'C'}];self.e.raw_query=lambda:fresh
  self.e.tick(G,0);self.e.tick(G,60);self.assertFalse(self.spawned)
 def test_query_failure_on_immediate_query_does_not_launch(self):
  self.e.raw_query=lambda:None;self.e.tick(G,0);self.e.tick(G,60);self.assertFalse(self.spawned)
 def test_exact_preemption_reason_survives_exit(self):
  self.e.tick(G,0);self.e.tick(G,60)
  with patch.object(self.e,'request_own_stop') as stop:self.e.tick(None,65);stop.assert_called_once()
  self.e.child.code=75;self.e.tick(G,70);self.assertEqual(self.e.state['preemption_event']['cause'],'QUERY_FAILED')
 def test_failed_stage_cannot_be_silently_retried(self):
  self.e.tick(G,0);self.e.tick(G,60);self.e.child.code=1;self.e.tick(G,65);self.e.tick(G,180)
  self.assertEqual(self.e.state['status'],'ENGINEERING_NOT_READY');self.assertEqual(len(self.spawned),1)
 def test_only_verified_output_skips_and_completion_not_scientific(self):
  self.e.tick(G,0);self.e.tick(G,60);f=self.p/'output';f.write_text('pass')
  atomic_json(self.c['reports']['smoke'],{'status':'PASS','stage':'smoke','attempt':self.e.attempt,'inputs':self.c['inputs'],'outputs':{str(f):sha256(f)}})
  self.e.child.code=0;self.e.tick(G,65);self.e.tick(G,70);self.assertEqual(self.e.state['status'],'OFFICIAL_NATIVE_VALIDATION_COMPLETE');self.assertFalse(self.e.state['scientificdone'])
  f.write_text('changed');self.assertEqual(self.e.pending_stage(),'smoke')
if __name__=='__main__':unittest.main(verbosity=2)
