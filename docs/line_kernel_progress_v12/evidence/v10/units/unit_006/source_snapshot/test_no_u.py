"""Unit005 ranking ablation, genuine policy RED/GREEN; inherited regressions reused."""
from runtime_io import *
import unittest,tempfile,copy
from unittest.mock import patch
import test_r6,test_relaxed,test_loader,test_scan24,test_scan65
import whole_core as w
from test_whole import synthetic
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_005/tests')
for module in [test_r6,test_relaxed,test_loader,test_scan24,test_scan65]:module.ROOT=ROOT

class NoUTests(unittest.TestCase):
 def test_actual_library_only_removes_reward_and_retains_pooling(self):
  try:import no_u_core as core
  except ImportError:import scan65_relaxed_core as core
  for pooling in [False,True]:
   d,o=test_r6.pooling_fixture() if pooling else synthetic(2)
   d['representatives'].update(member_rows=np.arange(2),member_offsets=np.arange(3))
   banks=core.libraries(d,o,0,w.CompleteIndex(o))
   self.assertIn('NO_U_REWARD',banks,'actual catalog has no NO_U_REWARD policy')
   old=banks['R2_R4_R6_OFF_TRANSPORT'];new=banks['NO_U_REWARD'];self.assertTrue(old['complete'] and new['complete']);self.assertIsNotNone(new['selected'])
   for a,b in zip(old['records'],new['records']):
    self.assertEqual(a['reason'],b['reason']);self.assertEqual(a['connectable'],b['connectable'])
    if 'q' in a:np.testing.assert_array_equal(a['q'],b['q'])
    if a['connectable']:
     U=a['metrics']['unique_donor_support_p'];self.assertEqual(b['metrics']['score'],a['metrics']['score']+.25*U/(1+U));self.assertTrue(np.isfinite(b['metrics']['score']));self.assertEqual(b['metrics']['score_original'],a['metrics']['score'])
     if pooling:self.assertEqual(U,0);self.assertEqual(a['metrics']['score'],b['metrics']['score'])
   diag=new['relation_diagnostics']['donors'][0]['interpretations'][new['selected']]
   self.assertEqual(diag['score_terms']['unique_support'],0);self.assertAlmostEqual(sum(diag['score_terms'].values()),diag['score'])

 def test_reward_removal_changes_best_without_changing_eligibility(self):
  import no_u_core as core
  records=[dict(donor=i,relation='overlap',direction=0,policy=core.ORIGINAL,connectable=True,reason='connectable',metrics=dict(score=score,unique_donor_support_p=U)) for i,score,U in [(1,-.1,3.),(2,.05,0.)]]
  original=dict(complete=True,selected=0,records=records);new=core.without_reward(original)
  self.assertEqual(new['selected'],1);self.assertEqual(original['selected'],0);self.assertEqual(original['records'][0]['metrics']['score'],-.1)
  original['complete']=False;self.assertIsNone(core.without_reward(original)['selected'])

 def test_original_control_exact_replay_with_geometry(self):
  import no_u_core as core,scan65_relaxed_core,r6_control,scan65_relaxed_delivery
  d,o=synthetic(2);d['representatives'].update(member_rows=np.arange(2),member_offsets=np.arange(3))
  old=scan65_relaxed_core.libraries(d,o,0,w.CompleteIndex(o))[core.ORIGINAL];new=core.libraries(d,o,0,w.CompleteIndex(o))[core.ORIGINAL]
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);scan65_relaxed_delivery.save_library(p,old);self.assertTrue(r6_control.compare_library(new,p/'LIBRARY.json')['complete'])
   bad=copy.deepcopy(new);bad['records'][bad['selected']]['metrics']['score']+=.01
   with self.assertRaisesRegex(AssertionError,'SCIENTIFIC_RECORD_MISMATCH'):r6_control.compare_library(bad,p/'LIBRARY.json')

 def test_actual_m4_loader_replay_archive_and_new_map_before_renderer(self):
  import scan65_loader,branch_loader,no_u_runner as runner,no_u_core as core,no_u_delivery as delivery,scan65_relaxed_core,scan65_relaxed_delivery
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=test_scan65.m4fixture(r);js(r/'raw.json',c);d=scan65_loader.load(c,lambda phase:None)
   o=copy.deepcopy(d['objects']);o[0].update(rows=np.arange(36),leaves=[0,1,2],q=np.vstack([o[i]['q'] for i in range(3)]),version=20);del o[1];del o[2]
   delivery.save_stage(r/'accepted',c,d,o,[dict(fixture_event=True)],21,'fixture-binding');js(r/'accepted/STOP.json',dict(status='completed',reason='NATURAL_SCOPE_EXHAUSTION'))
   c.update(raw_config=str(r/'raw.json'),restore_stage=str(r/'accepted'),restore_binding='fixture-binding',initial_stage=str(r/'accepted'),initial_next_version=21,seed_versions={'0':20},arms=['NO_U_REWARD'],arm_policies=core.POLICIES,max_seconds=1350,absolute_deadline_jst='2026-11-03T05:35:00+09:00',archived_control_stage=str(r/'accepted'),archived_control_binding='fixture-binding',archived_control_compute_exit='fixture-not-science')
   phases=[];restored=branch_loader.load(c,phases.append);self.assertEqual(set(phases),{'readiness'});self.assertEqual(restored['next_version'],21);np.testing.assert_array_equal(restored['objects'][0]['q'],o[0]['q'])
   def bad(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):branch_loader.load(c,bad)
   old=scan65_relaxed_core.libraries(restored,restored['objects'],0,w.CompleteIndex(restored['objects']))[core.ORIGINAL];scan65_relaxed_delivery.save_library(r/'old_library',old);c['control_replay_libraries']={'0':str(r/'old_library/LIBRARY.json')};js(r/'config.json',c)
   with patch.object(runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):runner.run(c,r/'config.json')
   scene=r/'run/scenes/fixture'
   for stage in ['START','NO_U_REWARD_FINAL']:
    out=scene/'stages'/stage;verify_checkpoint(out,sha(r/'config.json'));np.testing.assert_array_equal(np.load(out/'MEMBERSHIP.npz')['edge_id'],restored['initial_membership']['edge_id'])
   for policy in core.POLICIES:
    path=scene/'initial_catalogs'/policy/'0';self.assertTrue((path/'SCORE_COMPARISON.json').is_file());self.assertEqual(set(json.loads((path/'RELATION_DIAGNOSTICS.json').read_text())['policies']),set(core.POLICIES))
   result=json.loads((r/'run/RUN_RESULT.json').read_text());self.assertEqual(set(result['outputs']),{'NO_U_REWARD'});self.assertFalse(result['archived_control']['executed_in_this_unit']);self.assertFalse(result['actual_pngs']);self.assertTrue(json.loads((scene/'control_replay/0.json').read_text())['complete'])

 def test_new_runner_more_than_eight_and_incomplete_never_wins(self):
  import no_u_runner as runner,no_u_core as core
  d,o=synthetic(11);d['representatives'].update(member_rows=np.arange(11),member_offsets=np.arange(12));saved=[];c=dict(seed_ids=[0],arm_policies=core.POLICIES)
  result,events,_,stop,_=runner.grow(d,c,'NO_U_REWARD',o,20,lambda:None,lambda objects,ev,v,e:saved.append(set(objects[0]['rows'])),lambda *a:None)
  self.assertGreater(len(events),8);self.assertEqual(len(result[0]['rows']),132);self.assertTrue(all(a<=b for a,b in zip(saved,saved[1:])));self.assertEqual(stop['reason'],'NATURAL_SCOPE_EXHAUSTION');self.assertTrue(all(e['shadow_choices'] for e in events))
  bad=dict(complete=False,reason='KNOT_CAPACITY',neighbors=[],records=[dict(connectable=True)],selected=0)
  with patch.object(core,'library',return_value=bad):
   result,events,_,stop,_=runner.grow(d,c,'NO_U_REWARD',o,20,lambda:None,lambda *a:None,lambda *a:None)
  self.assertFalse(events);self.assertEqual(stop['status'],'PARTIAL');np.testing.assert_array_equal(result[0]['rows'],o[0]['rows'])

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 classes=[NoUTests,test_r6.R6Tests,test_relaxed.RelaxedTests,test_r6.WholeTests]
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in classes));raise SystemExit(0 if r.wasSuccessful() else 1)
