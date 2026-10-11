import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
import control
from pipeline_scope import validate_scope

class Tests(unittest.TestCase):
 def config(self):
  O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01')
  c=json.loads((O/'pilot/state/runner_config.json').read_text())
  c.update(scene='scan37',purpose='official_C24_scan37_half30k',model=str(O/'models/scan37_official_half30k'),state_dir=str(O/'suite_v01/scan37/state'),data='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/data/prepared/scan37')
  c['inputs']['scan24_quality_review']='test';c['stage_commands']['smoke']=['fake'];return c
 def test_scan37_allowed_after_review(self):validate_scope(self.config())
 def test_reject_scope_escape_and_missing_gate(self):
  c=self.config()
  for change in ({'wn':5},{'scene':'scan83'},{'allowed_gpu_uuids':['GPU1']},{'automatic_scene_limit':2},{'regularization_from_iter':15001},{'model':'/tmp/foreign'}):
   with self.assertRaises(ValueError):validate_scope(dict(c,**change))
  c['inputs'].pop('scan24_quality_review')
  with self.assertRaises(ValueError):validate_scope(c)
 def test_smoke_precedes_train_and_rechecked_seals_only(self):
  e=object.__new__(control.OfficialRunner);e.config=self.config();e.directory=Path('/unused')
  sequence=('smoke','train','export','tsdf','eval')
  for n in range(6):
   with patch.object(control.safety,'verify_seal',side_effect=lambda p,s,i:s in sequence[:n]):
    self.assertEqual(e.pending_stage(),sequence[n] if n<5 else None)
if __name__=='__main__':unittest.main(verbosity=2)
