"""New scan65 integration and relation-accounting tests; core regressions are reused."""
from runtime_io import *
import unittest,tempfile,copy
from unittest.mock import patch
import test_r6,test_relaxed,test_loader,test_scan24,test_scan65
from test_r6 import pooling_fixture
import whole_core as w
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_004/tests')
for module in [test_r6,test_relaxed,test_loader,test_scan24,test_scan65]:module.ROOT=ROOT

class Scan65RelaxedTests(unittest.TestCase):
 def test_real_library_relation_rows_and_unchanged_choices(self):
  try:import scan65_relaxed_core as core
  except ImportError:import r6_core as core
  import r6_core
  from r6_delivery import scientific
  d,o=pooling_fixture();old=r6_core.libraries(d,o,0,w.CompleteIndex(o));new=core.libraries(d,o,0,w.CompleteIndex(o))
  for policy,b in new.items():
   self.assertIn('relation_diagnostics',b,'same-donor relation evidence missing')
   self.assertEqual(scientific(old[policy]),scientific(b))
   np.testing.assert_array_equal(b['relation_rows']['group_rows'],o[0]['rows'])
   np.testing.assert_array_equal(b['relation_rows']['donor_rows'],o[1]['rows'])
   records=b['relation_diagnostics']['donors'][0]['interpretations']
   self.assertEqual(len(records),len(b['records']))
   for z,r in zip(records,b['records']):
    self.assertEqual(z['selected'],b['selected']==z['record_index'])
    if 'rule6' not in r.get('metrics',{}):self.assertEqual(z['rule6_status'],'NOT_REACHED')
  b=new['R2_R4_R6_OFF_TRANSPORT'];z=b['relation_diagnostics']['donors'][0]['interpretations'][b['selected']]
  self.assertEqual(z['unique_donor_support_p'],0);self.assertAlmostEqual(sum(z['score_terms'].values()),z['score'])

 def test_actual_m4_restore_and_both_arms_checkpoint_before_render(self):
  import scan65_loader,branch_loader,scan65_relaxed_runner as runner,scan65_relaxed_core as core,scan65_relaxed_delivery as delivery
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=test_scan65.m4fixture(r);js(r/'raw.json',c);d=scan65_loader.load(c,lambda phase:None)
   o=copy.deepcopy(d['objects']);o[0].update(rows=np.arange(36),leaves=[0,1,2],q=np.vstack([o[i]['q'] for i in range(3)]),version=20);del o[1];del o[2]
   delivery.save_stage(r/'accepted',c,d,o,[dict(fixture_event=True)],21,'fixture-binding')
   c.update(raw_config=str(r/'raw.json'),restore_stage=str(r/'accepted'),restore_binding='fixture-binding',initial_stage=str(r/'accepted'),initial_next_version=21,seed_versions={'0':20},arms=list(core.POLICIES),arm_policies=core.POLICIES,max_seconds=1800,absolute_deadline_jst='2026-11-03T05:35:00+09:00')
   phases=[];restored=branch_loader.load(c,phases.append);self.assertEqual(set(phases),{'readiness'});self.assertEqual(restored['next_version'],21);np.testing.assert_array_equal(restored['objects'][0]['q'],o[0]['q'])
   def bad(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):branch_loader.load(c,bad)
   js(r/'config.json',c)
   with patch.object(runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):runner.run(c,r/'config.json')
   scene=r/'run/scenes/fixture'
   for stage in ['START',*[p+'_FINAL' for p in core.POLICIES]]:
    out=scene/'stages'/stage;verify_checkpoint(out,sha(r/'config.json'));np.testing.assert_array_equal(np.load(out/'MEMBERSHIP.npz')['edge_id'],restored['initial_membership']['edge_id'])
   for policy in core.POLICIES:
    path=scene/'initial_catalogs'/policy/'0';self.assertTrue((path/'RELATION_ROWS.npz').is_file());self.assertEqual(set(json.loads((path/'RELATION_DIAGNOSTICS.json').read_text())['policies']),set(core.POLICIES))
   result=json.loads((r/'run/RUN_RESULT.json').read_text());self.assertEqual(set(result['outputs']),set(core.POLICIES));self.assertNotIn('archived_control',result);self.assertFalse(result['actual_pngs'])

 def test_new_runner_reenters_after_eight_and_rolls_back(self):
  from test_whole import synthetic
  import scan65_relaxed_runner as runner,scan65_relaxed_core as core
  d,o=synthetic(11);d['representatives'].update(member_rows=np.arange(11),member_offsets=np.arange(12));saved=[];c=dict(seed_ids=[0],arm_policies=core.POLICIES)
  result,events,_,stop,_=runner.grow(d,c,'R2_R4_R6_OFF_TRANSPORT',o,20,lambda:None,lambda objects,ev,v,e:saved.append(set(objects[0]['rows'])),lambda *a:None)
  self.assertGreater(len(events),8);self.assertEqual(len(result[0]['rows']),132);self.assertTrue(all(a<=b for a,b in zip(saved,saved[1:])));self.assertEqual(stop['reason'],'NATURAL_SCOPE_EXHAUSTION')
  bad=dict(complete=False,reason='KNOT_CAPACITY',neighbors=[],records=[dict(connectable=True)],selected=0)
  with patch.object(core,'library',return_value=bad):
   result,events,_,stop,_=runner.grow(d,c,'R2_R4_R6_OFF_TRANSPORT',o,20,lambda:None,lambda *a:None,lambda *a:None)
  self.assertFalse(events);self.assertEqual(stop['status'],'PARTIAL');np.testing.assert_array_equal(result[0]['rows'],o[0]['rows'])

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 classes=[Scan65RelaxedTests,test_r6.R6Tests,test_relaxed.RelaxedTests,test_r6.WholeTests]
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in classes));raise SystemExit(0 if r.wasSuccessful() else 1)
