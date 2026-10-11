import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import control
from safety import atomic_json,sha256
from test_scope_order import Tests as ScopeTests
class Adoption(unittest.TestCase):
 def test_live_child_restart_preserves_foreign_identities(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);c=ScopeTests().config();c.update(state_dir=str(p/'state'),log_dir=str(p/'logs'),engineering_ready=True,poll_seconds=60,immutable_files={},runtime_env={},cwd=str(p),preflight_report=str(p/'preflight.json'),reports={'train':str(p/'train.report.json')});atomic_json(c['preflight_report'],{'passed':True});config=p/'config.json';atomic_json(config,c)
   pid=999999998;ident={'uid':os.getuid(),'pgid':pid,'start_ticks':'55'};baseline={'888888888':{'uid':999,'pgid':888888888,'start_ticks':'44'}}
   atomic_json(p/'state/runner_state.json',{'status':'RUNNING','child_pid':pid,'child_identity':ident,'config_sha256':sha256(config),'selected_gpu_uuid':control.policy.GPU,'stage':'train','attempt':'test','baseline_identities':baseline})
   with patch.object(control.runner,'validate_config_scope'),patch.object(control.runner,'process_identity',return_value=ident):
    e=control.OfficialRunner(config,query=lambda:None,space_check=lambda:True)
    try:self.assertEqual(e.baseline_identities,{int(k):v for k,v in baseline.items()});self.assertEqual(e.state['status'],'ADOPTED_OWN_STAGE')
    finally:e.close()
if __name__=='__main__':unittest.main(verbosity=2)
