"""Actual loader callback contract; stop before any numerical asset read."""
from runtime_io import *
import unittest
from unittest.mock import patch
import path_library_runner as runner
import scene_adapter
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_011/tests')
class LoaderCallback(unittest.TestCase):
 def fixture(self):
  p=U/('callback_'+str(time.time_ns()));p.mkdir(parents=True)
  c=dict(unit=str(p),runtime=str(U),max_seconds=1200,absolute_deadline_jst='2026-11-01T09:38:00+09:00',parent_launch_latest_jst='2026-11-01T09:18:00+09:00',stage_budgets=dict(models_by=400),input_files={},helper_files={},source_files={})
  js(p/'CONFIG.json',c);return p,c
 def test_real_loader_propagates_phase_deadline(self):
  p,c=self.fixture()
  self.assertIs(runner.load,scene_adapter.load)
  with patch.object(runner.Limits,'guard',side_effect=TimeoutError('PHASE_DEADLINE readiness')) as g,patch.object(scene_adapter,'state_read',side_effect=AssertionError('NO_ASSET_READ')) as read:
   with self.assertRaisesRegex(TimeoutError,'PHASE_DEADLINE readiness'):runner.run(c,p/'CONFIG.json')
   g.assert_called_once_with('readiness');read.assert_not_called()
  r=json.loads((p/'RUN_RESULT.json').read_text());self.assertEqual(r['completed'],[]);self.assertEqual(r['fit_calls'],0)
 def test_real_loader_propagates_resource_guard(self):
  p,c=self.fixture()
  with patch.object(runner.Limits,'guard',side_effect=RuntimeError('FREE_SPACE_GUARD')) as g,patch.object(scene_adapter,'state_read',side_effect=AssertionError('NO_ASSET_READ')) as read:
   with self.assertRaisesRegex(RuntimeError,'FREE_SPACE_GUARD'):runner.run(c,p/'CONFIG.json')
   g.assert_called_once_with('readiness');read.assert_not_called()
 def test_real_guard_reaches_bound_state_read_without_asset_loading(self):
  p,c=self.fixture();js(p/'decision.json',dict(synthetic=True));old=dict(decision_path=str(p/'decision.json'),decision_sha256=sha(p/'decision.json'))
  js(p/'predecessor.json',old);js(p/'CHECKPOINT.json',dict(complete=True,stage='M4_STATE',config_binding=sha(p/'predecessor.json'),decision_sha256=old['decision_sha256'],files={}))
  c.update(decision_path=old['decision_path'],decision_sha256=old['decision_sha256'],predecessor_checkpoint=str(p/'CHECKPOINT.json'),predecessor_config=str(p/'predecessor.json'),state=str(p/'SYNTHETIC_NOT_LOADED.pkl'))
  with patch.object(scene_adapter,'state_read',side_effect=RuntimeError('REACHED_STATE_BOUNDARY')) as read:
   with self.assertRaisesRegex(RuntimeError,'REACHED_STATE_BOUNDARY'):runner.run(c,p/'CONFIG.json')
   read.assert_called_once_with(c['state'])

if __name__=='__main__':unittest.main(verbosity=2)
