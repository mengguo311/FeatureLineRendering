import json,unittest
from pathlib import Path
from pipeline_scope import validate_scope
class Tests(unittest.TestCase):
 def config(self):
  c=json.loads(Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01/scan63_v01/state/runner_config.json').read_text())
  c.update(scene='scan65',purpose='official_C24_scan65_depth_only_half30k',data='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/data/prepared/scan65')
  return c
 def test_current_scene_accepted(self):validate_scope(self.config())
 def test_other_scene_or_mesh_or_wrong_native_rejected(self):
  for update in [{'scene':'scan55'},{'allowed_gpu_uuids':['GPU1']},{'stage_commands':{'smoke':['fake'],'train':['fake'],'export':['fake'],'tsdf':['fake']}},{'numerical_revision':'unverified'}]:
   c=self.config();c.update(update)
   with self.assertRaises(ValueError):validate_scope(c)
if __name__=='__main__':unittest.main()
