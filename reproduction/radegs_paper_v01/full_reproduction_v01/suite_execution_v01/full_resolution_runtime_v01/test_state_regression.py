"""Original eight control tests applied to the new resolved per-scene scope."""
import importlib.util,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parents[3]/'stage2';sys.path.append(str(BASE))
from safety import atomic_json,sha256
import runner
spec=importlib.util.spec_from_file_location('old_control_tests',BASE/'test_runner.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
ROOT=Path(__file__).resolve().parents[5]
PROTO=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/FULL_SUITE_PROTOCOL.json'
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
class StateRegression(old.RunnerTests):
 def setUp(self):
  self.locktmp=tempfile.TemporaryDirectory();self.lockpatch=patch.object(runner,'GLOBAL_GPU_LOCK_DIR',Path(self.locktmp.name));self.lockpatch.start()
  def augment(path,value):
   if 'stage_commands' in value:value.update(dataset='DTU',entry_id='DTU_scan24_half30k_TSDF',iterations=30000,resolution_divisor=2,full_suite_protocol=str(PROTO),full_suite_protocol_sha256=sha256(PROTO),data=str(H/'data/prepared/scan24'),model=str(H/'models/scope_test_only'))
   return atomic_json(path,value)
  self.writer=patch.object(old,'atomic_json',side_effect=augment);self.writer.start();super().setUp()
 def tearDown(self):
  super().tearDown();self.writer.stop();self.lockpatch.stop();self.locktmp.cleanup()
if __name__=='__main__':unittest.main(verbosity=2)
