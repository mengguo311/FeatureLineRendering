import unittest
from unittest.mock import patch
from probe_control import Probe,control
from probe_scope import validate
class Tests(unittest.TestCase):
 def config(self):return {'method_variant':'official_code_fix_v01','scene':'scan55','purpose':'scan55_two_step_failure_replay','replay_limit':2,'stable_seconds':60,'allowed_gpu_uuids':['GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a'],'automatic_scene_limit':1,'stage_commands':{'smoke':['worker']},'model':'/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01/scan55_failure_v01/replay_v01/model','state_dir':'/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01/scan55_failure_v01/replay_v01/state'}
 def test_probe_terminal_not_depth_package(self):
  e=object.__new__(Probe)
  with patch.object(control.OfficialRunner,'persist') as persist:
   e.persist(status='PILOT_CHAIN_COMPLETE',depth_package_verified=True)
   self.assertFalse(persist.call_args.kwargs['depth_package_verified'])
 def test_bounded_original_method(self):validate(self.config())
 def test_no_full_train_other_scene_or_gpu(self):
  for bad in [{'replay_limit':3},{'scene':'scan63'},{'train_command':['bad']},{'stage_commands':{'train':['bad']}},{'allowed_gpu_uuids':['GPU1']}]:
   with self.assertRaises(ValueError):validate(dict(self.config(),**bad))
if __name__=='__main__':unittest.main()
