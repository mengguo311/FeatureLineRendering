import json,unittest
from pathlib import Path
from unittest.mock import patch
import control
from pipeline_scope import validate_scope
class Tests(unittest.TestCase):
 def config(self):
  H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');c=json.loads((H/'official_code_fix_v01/suite_v01/scan37/state/runner_config.json').read_text())
  c.update(scene='scan55',purpose='official_C24_scan55_depth_only_half30k',workflow='depth_only_v01',model=str(H/'depth_only_v01/models/scan55_official_half30k'),state_dir=str(H/'depth_only_v01/scan55/state'),data=str(H/'data/prepared/scan55'),stage_commands={s:['fake'] for s in ['smoke','train','export','depth_review']})
  c['inputs'].pop('scan24_quality_review',None);c['inputs']['previous_depth_review']='fixture';return c
 def test_no_mesh_gate_and_depth_scope_allowed(self):validate_scope(self.config())
 def test_mesh_eval_and_unfrozen_scenes_rejected(self):
  c=self.config()
  for changes in ({'scene':'scan83'},{'wn':5},{'workflow':'mesh'},{'allowed_gpu_uuids':['GPU1']},{'automatic_scene_limit':2},{'model':'/tmp/old'}):
   with self.assertRaises(ValueError):validate_scope(dict(c,**changes))
  for stage in ('tsdf','eval','mesh'):
   bad=dict(c,stage_commands=dict(c['stage_commands'],**{stage:['fake']}))
   with self.assertRaises(ValueError):validate_scope(bad)
 def test_depth_review_terminal_no_mesh_after_export(self):
  e=object.__new__(control.OfficialRunner);e.config=self.config();e.directory=Path('/unused');seq=('smoke','train','export','depth_review')
  for n in range(5):
   with patch.object(control.safety,'verify_seal',side_effect=lambda p,s,i:s in seq[:n]):self.assertEqual(e.pending_stage(),seq[n] if n<4 else None)
if __name__=='__main__':unittest.main(verbosity=2)
