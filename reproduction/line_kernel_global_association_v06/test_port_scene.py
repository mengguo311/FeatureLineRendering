"""Bounded ficus port-runner contract: source loading/rendering mocked, 18 rows."""
from runtime_io import *
import unittest,importlib,sys
from unittest.mock import patch
import test_runner_fixture as fixture_module
from paired_delivery import restore_pair
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_009/tests')
RUNNER=importlib.import_module('runner')
class PortSceneTests(unittest.TestCase):
 def fixture(self):
  root=U/('port_fixture_'+str(time.time_ns()));root.mkdir(parents=True)
  d=fixture_module.RunnerFixture().data()
  nz(root/'gaussians.npz',**d['asset']);nz(root/'reference.npz',edge_id=np.array([1]*6+[-1]*12));(root/'state.txt').write_text('SYNTHETIC18')
  js(root/'cameras.json',{'ficus':[{'view':'test_r_1'},{'view':'test_r_79'}]})
  c=dict(scene='ficus',unit=str(root),runtime=str(U),max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00',parent_launch_latest_jst='2026-11-01T09:08:00+09:00',p=1.,kernel_count=18,expected_candidate_records=2,expected_successful_endpoints=2,expected_eligible_endpoints=2,expected_endpoint_components=1,decision_carrier_cap=128,reference_membership=str(root/'reference.npz'),seed_groups=[1],priority_carrier_ids=[1],fixed_carrier_ids=[3],reference_leaf_sets=[[1,2]],negative_pairs=[],candidate_metrics='synthetic',input_files={str(root/'gaussians.npz'):sha(root/'gaussians.npz'),str(root/'state.txt'):sha(root/'state.txt')},helper_files={},source_files={},solver=dict(per_context_seconds=5,total_seconds=10,max_cut_rounds=32),membership='synthetic',state=str(root/'state.txt'),gaussians=str(root/'gaussians.npz'),cameras=str(root/'cameras.json'),views=['test_r_1','test_r_79'],external_memberships={})
  c['input_files'][c['cameras']]=sha(c['cameras'])
  js(root/'CONFIG.json',c);return root,c,d
 def execute(self,root,c,d):
  with patch.object(RUNNER,'load',return_value=d),patch.object(RUNNER,'renderer',side_effect=RuntimeError('DELIBERATE_NO_RENDER')):
   with self.assertRaisesRegex(RuntimeError,'DELIBERATE_NO_RENDER'):RUNNER.run(c,root/'CONFIG.json')
 def test_ficus_paths_and_later_failure_preserve_complete_mappings(self):
  root,c,d=self.fixture();self.execute(root,c,d)
  self.assertFalse((root/'scenes/scan24').exists())
  r=json.loads((root/'RUN_RESULT.json').read_text());self.assertEqual(r['fit_calls'],0);self.assertEqual(r['actual_saved_pngs'],[])
  for arm in ['greedy','joint']:
   out=root/'scenes/ficus/stages'/arm;verify_checkpoint(out,sha(root/'CONFIG.json'))
   m=np.load(out/'MEMBERSHIP.npz');self.assertEqual(m['edge_id'].tolist(),[1]*18)
   g=json.loads((out/'GROUPS.json').read_text());self.assertEqual(g['scene'],'ficus');self.assertEqual(len(g['groups'][0]['leaves']),3)
 def test_resume_complete_pairs_without_new_solve_or_export(self):
  root,c,d=self.fixture();self.execute(root,c,d);files={str(p):sha(p) for p in root.rglob('CHECKPOINT.json')};(root/'RUN_RESULT.json').rename(root/'EXPECTED_FAILURE.json')
  with patch.object(RUNNER,'greedy',side_effect=AssertionError('NO_NEW_SOLVE')),patch.object(RUNNER,'joint',side_effect=AssertionError('NO_NEW_SOLVE')),patch.object(RUNNER,'export_arm',side_effect=AssertionError('NO_NEW_EXPORT')):self.execute(root,c,d)
  self.assertEqual(files,{p:sha(p) for p in files})
 def test_bad_component_count_blocks_before_mapping(self):
  root,c,d=self.fixture();c['expected_endpoint_components']=2
  with patch.object(RUNNER,'load',return_value=d),patch.object(RUNNER,'renderer',side_effect=AssertionError('NO_RENDER')):
   with self.assertRaisesRegex(AssertionError,'FROZEN_COMPONENT_COUNT'):RUNNER.run(c,root/'CONFIG.json')
  self.assertEqual(list(root.rglob('MEMBERSHIP.npz')),[])
 def test_missing_paths_still_select_fixed_evidence(self):
  from port_scene_policy import diagnostic_cases
  root,c,d=self.fixture();saved={a:(d['membership'],[]) for a in ['greedy','joint']}
  out=diagnostic_cases(c,d,saved,[],[]);self.assertTrue(any(x['core_carriers']==[1,2] for x in out['cases']));self.assertTrue(any(x['core_carriers']==[3] for x in out['cases']))

 def test_reference_withdrawals_and_unknown_activation(self):
  from port_scene_references import reference_comparisons
  from scene_render import membership_for
  from port_paths import PathOracle
  root,c,d=self.fixture();d['leaves'][1].intervals=np.array([[0.,1.]])
  d['leaves'][2].intervals=np.array([[0.,1.]])
  oracle=PathOracle(d['leaves']);m,g,l=membership_for(d,[0],oracle)
  self.assertTrue(np.all(m['edge_id'][6:12]<0));self.assertTrue(np.all(m['edge_id'][:6]==1))
  result=reference_comparisons({'new':({'edge_id':np.array([1,-1,3])},[])},{'ref':({'edge_id':np.array([-1,2,3])},[])})
  self.assertEqual(result['new']['ref']['assigned_gained'],1);self.assertEqual(result['new']['ref']['assigned_lost'],1)

 def test_full_synthetic_delivery_keeps_scene_and_references(self):
  root,c,d=self.fixture();calls=[]
  def fake_renderer(asset,cam,background,floor):
   calls.append((len(asset['means']),cam['view']));rgb=np.ones((12,14,3));rgb[6,7]=.5;return {'rgb':rgb}
  with patch.object(RUNNER,'load',return_value=d),patch.object(RUNNER,'renderer',return_value=fake_renderer):RUNNER.run(c,root/'CONFIG.json')
  r=json.loads((root/'RUN_RESULT.json').read_text());self.assertTrue(r['delivery_gate']);self.assertEqual(r['status'],'complete');self.assertEqual(r['fit_calls'],0)
  self.assertEqual(calls[:4],[(18,'test_r_1'),(18,'test_r_79')]*2)
  self.assertFalse((root/'scenes/scan24').exists())
  compare=json.loads((root/'scenes/ficus/REFERENCE_COMPARISON.json').read_text());self.assertEqual(compare['joint']['M4_reference']['assigned_lost'],0)
  diag=json.loads((root/'scenes/ficus/diagnostics/SELECTION.json').read_text());self.assertIn('top3_actual_arm_member_differences',diag['missing'])
  self.assertTrue((root/'scenes/ficus/stages/M4_reference/diagnostics/REFERENCE_1_2_GROUP_test_r_1.png').exists())
