import json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.append(str(Path(__file__).resolve().parents[3]/'stage2'))
from test_scope_runner import Scope
from safety import atomic_json
import pilot_runtime,gpu_stages,runner

class RuntimeScope(Scope):
 def args(self,path,**kw):
  c=json.loads(path.read_text())
  values=dict(pilot_config=str(path),iterations=30000,resolution=2,lambda_distortion=100,lambda_depth_normal=5,regularization_from_iter=15001,use_decoupled_appearance=True,eval=False,white_background=False,source_path=c['data'],model_path=c['model'],start_checkpoint=None)
  values.update(kw);return SimpleNamespace(**values)
 def test_training_scan37_scope_admitted(self):
  pilot_runtime.validate_pilot_arguments(self.args(self.config()))
 def test_training_method_scope_cannot_drift(self):
  path=self.config()
  for kw in [{'lambda_depth_normal':.05},{'regularization_from_iter':15000},{'start_checkpoint':'old.pth'},{'source_path':'/tmp/fake'}]:
   with self.assertRaises(ValueError):pilot_runtime.validate_pilot_arguments(self.args(path,**kw))
 def test_scene_counts_use_verified_manifest(self):
  c=json.loads(self.config().read_text());c['expected_scene']={'views':49,'initial_colmap_points':12345,'half_resolution':[777,581]}
  cams=[SimpleNamespace(image_width=777,image_height=581) for _ in range(49)]
  gpu_stages.validate_scene_manifest(c,cams,SimpleNamespace(_xyz=list(range(12345))),True)
  for bad in [cams[:-1],[SimpleNamespace(image_width=1554,image_height=1162)]*49]:
   with self.assertRaises(AssertionError):gpu_stages.validate_scene_manifest(c,bad,SimpleNamespace(_xyz=list(range(12345))),True)
 def test_vanished_adopted_child_is_failure_not_retry(self):
  with patch.object(runner,'process_identity',return_value=None):
   child=runner.AdoptedChild(100,{'uid':1},self.root/'missingreport')
   self.assertEqual(child.poll(),1)

if __name__=='__main__':unittest.main(verbosity=2)
