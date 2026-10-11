import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import control
from safety import atomic_json,sha256
from test_depth_scope import Tests as ScopeFixture
G=[{'uuid':control.policy.GPU,'memory_mib':10000,'total_mib':49140,'free_mib':39000,'util_percent':0,'contexts':[]}]
class Child:
 pid=999999998;code=None
 def poll(self):return self.code
class SupervisorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01');self.p=Path(self.tmp.name);self.calls=[]
  self.lock_patch=patch.object(control.runner,'GLOBAL_GPU_LOCK_DIR',self.p/'private_mock_gpu_locks');self.lock_patch.start()
  self.c=ScopeFixture().config();self.c.update(state_dir=str(self.p/'state'),log_dir=str(self.p/'logs'),engineering_ready=True,immutable_files={},runtime_env={},cwd=str(self.p),preflight_report=str(self.p/'preflight.json'),reports={s:str(self.p/(s+'.json')) for s in ('smoke','train','export','depth_review')},stage_commands={s:['fake'] for s in ('smoke','train','export','depth_review')})
  atomic_json(self.c['preflight_report'],{'passed':True});self.config=self.p/'config.json';atomic_json(self.config,self.c)
  def spawn(*a,**k):self.calls.append((a,k));return Child()
  self.e=control.OfficialRunner(self.config,spawn=spawn,query=lambda:copy.deepcopy(G),space_check=lambda:True)
 def tearDown(self):self.e.close();self.lock_patch.stop();self.tmp.cleanup()
 def test_depth_terminal_never_claims_evaluation(self):
  with patch.object(self.e,'pending_stage',return_value=None):self.e.tick(G,0)
  self.assertEqual(self.e.state['status'],'DEPTH_DELIVERED_VISUAL_REVIEW_REQUIRED')
  self.assertFalse(self.e.state.get('pilot_evaluation_verified',False))
  self.assertFalse(self.e.state.get('depth_review_passed',False))
 def test_busy_failed_stable60_fresh_recheck(self):
  self.e.tick(None,0);busy=copy.deepcopy(G);busy[0]['util_percent']=11;self.e.tick(busy,60)
  self.e.tick(G,120);self.e.tick(G,179);self.assertFalse(self.calls);self.e.tick(G,180);self.assertEqual(len(self.calls),1);self.assertEqual(self.e.state['stage'],'smoke')
 def test_immediate_changed_context_fail_closed(self):
  g=copy.deepcopy(G);g[0]['contexts']=[{'pid':888888888,'type':'C'}];self.e.raw_query=lambda:g
  self.e.tick(G,0);self.e.tick(G,60);self.assertFalse(self.calls)
 def test_failed_stage_no_automatic_retry(self):
  self.e.tick(G,0);self.e.tick(G,60);self.e.child.code=1;self.e.tick(G,65);self.e.tick(G,180)
  self.assertEqual(self.e.state['status'],'ENGINEERING_NOT_READY');self.assertEqual(len(self.calls),1)
 def test_atomic_seal_tamper_returns_to_smoke(self):
  self.e.tick(G,0);self.e.tick(G,60);f=self.p/'output';f.write_text('ok')
  atomic_json(self.c['reports']['smoke'],{'stage':'smoke','status':'PASS','attempt':self.e.attempt,'inputs':self.c['inputs'],'outputs':{str(f):sha256(f)}})
  self.e.child.code=0;self.e.tick(G,65);self.assertEqual(self.e.pending_stage(),'train');f.write_text('tampered');self.assertEqual(self.e.pending_stage(),'smoke')
 def test_preemption_cause_survives_child_exit(self):
  self.e.tick(G,0);self.e.tick(G,60);low=copy.deepcopy(G);low[0]['free_mib']=1779
  with patch.object(self.e,'request_own_stop') as stop:self.e.tick(low,65);stop.assert_called_once()
  self.e.child.code=75;self.e.tick(G,70);self.assertEqual(self.e.state['preemption_event']['cause'],'LOW_FREE_MEMORY')
 def test_adopt_identity_preserves_original_foreign_baseline(self):
  self.e.close();pid=999999998;ident={'uid':os.getuid(),'pgid':pid,'start_ticks':'55'};baseline={'888888888':{'uid':999,'pgid':888888888,'start_ticks':'44'}}
  atomic_json(self.p/'state/runner_state.json',{'status':'RUNNING','child_pid':pid,'child_identity':ident,'config_sha256':sha256(self.config),'selected_gpu_uuid':control.policy.GPU,'stage':'smoke','attempt':'test','baseline_identities':baseline})
  with patch.object(control.runner,'process_identity',return_value=ident):
   self.e=control.OfficialRunner(self.config,query=lambda:None,space_check=lambda:True)
   self.assertEqual(self.e.baseline_identities,{int(k):v for k,v in baseline.items()});self.assertEqual(self.e.state['status'],'ADOPTED_OWN_STAGE')
if __name__=='__main__':unittest.main(verbosity=2)
