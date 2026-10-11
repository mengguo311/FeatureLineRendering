import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import control
from pipeline_scope import validate_scope
class Tests(unittest.TestCase):
 def config(self):
  H='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01'
  return {'method_variant':'official_code_fix_v01','scene':'scan24','automatic_scene_limit':1,'allowed_gpu_uuids':[control.policy.GPU],'stable_seconds':60,'purpose':'official_C24_scan24_half30k','stage_commands':{x:['fake'] for x in sorted(['train','export','tsdf','eval'])},'model':H+'/models/scan24_official_half30k','state_dir':H+'/pilot/state','data':'/mnt/hdd1/u00134/radegs_paper_reproduction_v01/data/prepared/scan24','iterations':30000,'resolution_divisor':2,'wd':100,'wn':.05,'regularization_from_iter':15000,'geometry_start_inclusive':True,'optimizer_final_step':False,'inputs':{'native_validated':'a','runtime_validated':'b'}}
 def test_json_sorted_commands_do_not_reorder_scientific_stages(self):
  e=object.__new__(control.OfficialRunner);e.config=self.config();e.directory=Path('/unused')
  with patch.object(control.safety,'verify_seal',return_value=False):self.assertEqual(e.pending_stage(),'train')
  with patch.object(control.safety,'verify_seal',side_effect=lambda p,s,i:s=='train'):self.assertEqual(e.pending_stage(),'export')
 def test_reject_other_method_source_scene_schedule(self):
  c=self.config();validate_scope(c)
  for v in ({'wn':5},{'regularization_from_iter':15001},{'optimizer_final_step':True},{'scene':'scan83'},{'model':'/tmp/foreign'},{'stage_commands':{'train':['fake']}},{'inputs':{'native_validated':'a'}}):
   with self.assertRaises(ValueError):validate_scope(dict(c,**v))
if __name__=='__main__':unittest.main(verbosity=2)
