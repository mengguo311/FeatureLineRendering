"""Unit007 functional fit-policy RED/GREEN; no full asset execution."""
from runtime_io import *
import unittest,copy,tempfile
from unittest.mock import patch
import test_balanced,test_no_u,test_r6,test_relaxed,test_loader,test_scan24,test_scan65
import whole_core as w
from test_whole import synthetic
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_007/tests')
for module in [test_balanced,test_no_u,test_r6,test_relaxed,test_loader,test_scan24,test_scan65]:module.ROOT=ROOT

class GroupFitTests(unittest.TestCase):
 def test_actual_library_separate_group_fit(self):
  try:import group_fit_core as core
  except ImportError:import balanced_core as core
  d,o=test_balanced.unequal_fixture();banks=core.libraries(d,o,0,w.CompleteIndex(o))
  self.assertIn('GROUP_BALANCED_FIT',banks,'actual catalog has no GROUP_BALANCED_FIT policy')
  old=banks['GROUP_BALANCED_SCORE'];new=banks['GROUP_BALANCED_FIT'];self.assertTrue(old['complete'] and new['complete'])
  self.assertEqual(old['neighbors'],new['neighbors']);changed=False
  for a,b in zip(old['records'],new['records']):
   if 'q' not in a or 'q' not in b:continue
   np.testing.assert_array_equal(a['template'],b['template']);changed|=not np.array_equal(a['q'],b['q'])
   f=b['fit']['group_weighting'];self.assertEqual(f['G_count'],24);self.assertEqual(f['F_count'],12)
  self.assertTrue(changed,'unequal group weights must change actual fitted Q')

 def test_equal_size_exact_original_fit_and_unequal_normalization(self):
  import group_fit_core as c
  template=np.c_[np.linspace(0,8,9),np.zeros((9,2))]
  x=np.c_[np.tile(np.linspace(.2,7.8,10),2),np.repeat([.1,.4],10),np.zeros(20)]
  side=np.repeat([0,1],10);q0,m0=w.fit(template,x,np.ones(9,bool));q1,m1=c.fit(template,x,np.ones(9,bool),side,np.arange(20))
  np.testing.assert_array_equal(q0,q1);self.assertEqual(m0['lsqr'],m1['lsqr'])
  side=np.r_[np.zeros(18,int),np.ones(2,int)];before=x.copy();q,meta=c.fit(template,x,np.ones(9,bool),side,np.arange(20))
  ev=meta['_evidence'];np.testing.assert_array_equal(x,before);np.testing.assert_array_equal(ev['rows'],np.arange(20))
  for h in [0,1]:self.assertAlmostEqual(float(ev['base_weights'][side==h].sum()),.5)
  for i in range(5):np.testing.assert_allclose(ev[f'round_{i}_matrix_weights']**2,.5*ev['base_weights']*ev[f'round_{i}_robust_weights'],rtol=1e-14)
  self.assertEqual(len(meta['round_losses']),5);self.assertTrue(np.linalg.norm(q[0]-template[0])>0)
  with self.assertRaisesRegex(w.Incomplete,'MEMBERSHIP_PARTITION'):c.partition(dict(rows=[0,1]),dict(rows=[1,2]))

 def test_row_fit_replay_scientific_and_geometry(self):
  import group_fit_core as c,balanced_core,balanced_delivery,group_fit_delivery as out
  d,o=test_balanced.unequal_fixture();old=balanced_core.libraries(d,o,0,w.CompleteIndex(o))[c.ORIGINAL];new=c.libraries(d,o,0,w.CompleteIndex(o))[c.ORIGINAL]
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);balanced_delivery.save_library(p,old);self.assertTrue(out.compare_library(new,p/'LIBRARY.json')['complete'])
   bad=copy.deepcopy(new);bad['records'][bad['selected']]['metrics']['score']+=.001
   with self.assertRaisesRegex(AssertionError,'SCIENTIFIC_RECORD_MISMATCH'):out.compare_library(bad,p/'LIBRARY.json')

 def test_fit_evidence_both_saved_and_failed_fit_is_partial(self):
  import group_fit_core as c,group_fit_delivery as out
  d,o=test_r6.pooling_fixture();lib=c.library(d,o,0,c.NEW,w.CompleteIndex(o));self.assertTrue(lib['complete']);self.assertIsNotNone(lib['selected']);r=lib['records'][lib['selected']]
  self.assertTrue(r['metrics']['rule6']['pure_pooling']);self.assertTrue(np.isfinite(r['metrics']['score']));self.assertEqual(r['relaxed_rule_groups'],[2,4,6])
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);out.save_library(p,lib);self.assertTrue((p/'ROW_FIT_CONTROL/GEOMETRY.npz').exists());arr=np.load(p/'FIT_EVIDENCE.npz');rec=json.loads((p/'LIBRARY.json').read_text())['records'][lib['selected']]
   for key,value in r['fit_evidence'].items():np.testing.assert_array_equal(value,arr[rec['fit_evidence_arrays'][key]])
  with patch.object(c,'fit',side_effect=w.Incomplete('LSQR_NOT_CONVERGED 7')):
   banks=c.libraries(d,o,0,w.CompleteIndex(o));self.assertTrue(banks[c.ORIGINAL]['complete']);self.assertFalse(banks[c.NEW]['complete']);self.assertIsNone(banks[c.NEW]['selected'])

 def test_actual_m4_loader_replay_archive_and_new_map_before_renderer(self):
  import scan65_loader,branch_loader,group_fit_runner as runner,group_fit_core as core,group_fit_delivery as delivery,balanced_core,balanced_delivery
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=test_scan65.m4fixture(r);js(r/'raw.json',c);d=scan65_loader.load(c,lambda phase:None)
   o=copy.deepcopy(d['objects']);o[0].update(rows=np.arange(36),leaves=[0,1,2],q=np.vstack([o[i]['q'] for i in range(3)]),version=20);del o[1];del o[2]
   delivery.save_stage(r/'accepted',c,d,o,[dict(fixture_event=True)],21,'fixture-binding');js(r/'accepted/STOP.json',dict(status='completed',reason='NATURAL_SCOPE_EXHAUSTION'))
   c.update(raw_config=str(r/'raw.json'),restore_stage=str(r/'accepted'),restore_binding='fixture-binding',initial_stage=str(r/'accepted'),initial_next_version=21,seed_versions={'0':20},arms=[core.NEW],arm_policies=core.POLICIES,max_seconds=1350,absolute_deadline_jst='2026-11-03T05:35:00+09:00',archived_control_stage=str(r/'accepted'),archived_control_binding='fixture-binding',archived_control_compute_exit='fixture-not-science')
   phases=[];restored=branch_loader.load(c,phases.append);self.assertEqual(set(phases),{'readiness'});self.assertEqual(restored['next_version'],21);np.testing.assert_array_equal(restored['objects'][0]['q'],o[0]['q'])
   def bad(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):branch_loader.load(c,bad)
   old=balanced_core.libraries(restored,restored['objects'],0,w.CompleteIndex(restored['objects']))[core.ORIGINAL];balanced_delivery.save_library(r/'old_library',old);c['control_replay_libraries']={'0':str(r/'old_library/LIBRARY.json')};js(r/'config.json',c)
   with patch.object(runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):runner.run(c,r/'config.json')
   scene=r/'run/scenes/fixture'
   for stage in ['START',core.NEW+'_FINAL']:
    out=scene/'stages'/stage;verify_checkpoint(out,sha(r/'config.json'));np.testing.assert_array_equal(np.load(out/'MEMBERSHIP.npz')['edge_id'],restored['initial_membership']['edge_id'])
   for policy in core.POLICIES:
    path=scene/'initial_catalogs'/policy/'0';self.assertTrue((path/'SCORE_COMPARISON.json').is_file());self.assertTrue((path/'SCORE_EVIDENCE.npz').is_file())
   result=json.loads((r/'run/RUN_RESULT.json').read_text());self.assertEqual(set(result['outputs']),{core.NEW});self.assertFalse(result['archived_control']['executed_in_this_unit']);self.assertEqual(result['archived_control']['stop']['status'],'completed');self.assertFalse(result['actual_pngs']);self.assertTrue(json.loads((scene/'control_replay/0.json').read_text())['complete'])

 def test_more_than_eight_requeries_best_union_and_failed_checkpoint(self):
  import group_fit_runner as runner,group_fit_core as core
  d,o=synthetic(11);d['representatives'].update(member_rows=np.arange(11),member_offsets=np.arange(12));saved=[];c=dict(seed_ids=[0],arm_policies=core.POLICIES)
  result,events,_,stop,_=runner.grow(d,c,core.NEW,o,20,lambda:None,lambda objects,ev,v,e:saved.append(set(objects[0]['rows'])),lambda *a:None)
  self.assertGreater(len(events),8);self.assertEqual(len(result[0]['rows']),132);self.assertTrue(all(a<=b for a,b in zip(saved,saved[1:])));self.assertEqual(stop['reason'],'NATURAL_SCOPE_EXHAUSTION');self.assertTrue(all(e['shadow_choices'] for e in events))
  bad=dict(complete=False,reason='KNOT_CAPACITY',neighbors=[],records=[dict(connectable=True)],selected=0)
  with patch.object(core,'library',return_value=bad):
   result,events,_,stop,_=runner.grow(d,c,core.NEW,o,20,lambda:None,lambda *a:None,lambda *a:None)
  self.assertFalse(events);self.assertEqual(stop['status'],'PARTIAL');np.testing.assert_array_equal(result[0]['rows'],o[0]['rows'])
  lib=core.libraries(d,o,0,w.CompleteIndex(o))[core.NEW];record=lib['records'][lib['selected']];before=copy.deepcopy(o)
  def failed_save(*a):raise RuntimeError('SAVE_FAILURE')
  with self.assertRaisesRegex(RuntimeError,'SAVE_FAILURE'):w.commit(o,0,record,20,failed_save)
  for gid in o:np.testing.assert_array_equal(o[gid]['rows'],before[gid]['rows']);np.testing.assert_array_equal(o[gid]['q'],before[gid]['q'])

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 classes=[GroupFitTests,test_r6.R6Tests,test_relaxed.RelaxedTests,test_r6.WholeTests]
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in classes));raise SystemExit(0 if r.wasSuccessful() else 1)
