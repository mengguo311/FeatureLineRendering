from runtime_io import *
import unittest
from unittest.mock import patch
import test_runner_fixture as fixture_module
import path_library_runner as runner
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_010/tests')
class Vertical(unittest.TestCase):
 def fixture(self):
  p=U/('fixture_'+str(time.time_ns()));p.mkdir();d=fixture_module.RunnerFixture().data()
  nz(p/'gaussians.npz',**d['asset']);(p/'state.txt').write_text('SYNTHETIC18');js(p/'cameras.json',dict(ficus=[dict(view='test_r_1'),dict(view='test_r_79')]))
  c=dict(unit=str(p),output=str(p),runtime=str(U),scene='ficus',max_seconds=1200,absolute_deadline_jst='2026-11-01T09:38:00+09:00',parent_launch_latest_jst='2026-11-01T09:18:00+09:00',stage_budgets=dict(models_by=400),solver=dict(per_context_seconds=5,total_seconds=20),path_cap=128,p=1.,kernel_count=18,expected_candidate_records=2,expected_successful_endpoints=2,expected_eligible_endpoints=2,expected_endpoint_components=1,expected_max_component=3,expected_masked_endpoints=0,priority_carrier_ids=[1],negative_pairs=[],reference_leaf_sets=[[1,2]],decision_carrier_cap=128,fit_source=str(Path(__file__).parent/'pinned_v05_fit_core.py'),gaussians=str(p/'gaussians.npz'),state=str(p/'state.txt'),membership='synthetic',cameras=str(p/'cameras.json'),views=['test_r_1','test_r_79'],input_files={},source_files={},helper_files={},external_memberships={})
  c['input_files']={str(p/n):sha(p/n) for n in ['gaussians.npz','state.txt','cameras.json']};js(p/'CONFIG.json',c);return p,c,d
 def test_checkpoint_before_failure_and_verified_resume(self):
  p,c,d=self.fixture()
  def fail():
   with patch.object(runner,'load',return_value=d),patch.object(runner,'renderer',side_effect=RuntimeError('NO_RENDER_FIXTURE')):
    with self.assertRaisesRegex(RuntimeError,'NO_RENDER_FIXTURE'):runner.run(c,p/'CONFIG.json')
  fail();self.assertEqual(list(p.rglob('*.png')),[])
  for arm in runner.ARMS:
   out=p/'scenes/ficus/stages'/arm;verify_checkpoint(out,sha(p/'CONFIG.json'));m=np.load(out/'MEMBERSHIP.npz');self.assertEqual(m['edge_id'].tolist(),[1]*18)
  hashes={str(x):sha(x) for x in p.rglob('CHECKPOINT.json')};(p/'RUN_RESULT.json').rename(p/'EXPECTED_FAILURE.json')
  with patch.object(runner,'build_banks',side_effect=AssertionError('NO_REFIT')),patch.object(runner,'export',side_effect=AssertionError('NO_EXPORT')):fail()
  self.assertEqual(hashes,{x:sha(x) for x in hashes})
 def test_full_mocked_delivery_and_overflow_fallback(self):
  for cap in [128,1]:
   p,c,d=self.fixture();c['path_cap']=cap
   def render(*args):
    x=np.ones((10,12,3));x[5,6]=.4;return dict(rgb=x)
   with patch.object(runner,'load',return_value=d),patch.object(runner,'renderer',return_value=render):runner.run(c,p/'CONFIG.json')
   r=json.loads((p/'RUN_RESULT.json').read_text());self.assertTrue(r['delivery_gate']);self.assertEqual(r['status'],'complete' if cap==128 else 'partial')
   for arm in runner.ARMS:
    m=np.load(p/'scenes/ficus/stages'/arm/'MEMBERSHIP.npz')
    self.assertEqual(m['edge_id'].tolist(),[1]*18 if cap==128 else [1]*6+[-1]*12)
    self.assertTrue((p/'scenes/ficus/stages'/arm/'test_r_79_FULL.png').exists())
   if cap==128:
    hashes={str(x):sha(x) for x in p.rglob('*') if x.is_file() and x.name!='RUN_RESULT.json'}
    (p/'RUN_RESULT.json').rename(p/'FIRST_RUN_RESULT.json')
    with patch.object(runner,'load',return_value=d),patch.object(runner,'renderer',return_value=lambda *a:(_ for _ in ()).throw(AssertionError('NO_RERENDER'))),patch.object(runner,'build_banks',side_effect=AssertionError('NO_REFIT')):runner.run(c,p/'CONFIG.json')
    self.assertEqual(hashes,{x:sha(x) for x in hashes})

if __name__=='__main__':unittest.main(verbosity=2)
