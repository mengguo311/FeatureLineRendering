"""Unit002 tests. Existing core regressions are reused, not newly claimed TDD."""
from runtime_io import *
import unittest,tempfile,copy
from unittest.mock import patch
import relaxed_core
from test_whole import synthetic,WholeTests
import test_relaxed
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_002/tests')
test_relaxed.ROOT=ROOT

def parallel_fixture():
 d,o=synthetic(2);rr=o[1]['rows'];d['asset']['means'][rr]=np.c_[np.linspace(0,4,12),np.full(12,.8),np.zeros(12)]
 q=np.array([[0.,.8,0],[4.,.8,0]]);d['leaves'][1].q=q.copy();o[1]['q']=q.copy()
 d['representatives'].update(member_rows=np.arange(2),member_offsets=np.arange(3))
 return d,o

class R4Tests(unittest.TestCase):
 def test_actual_policy_dispatch_parallel_candidate_finite(self):
  # Before unit002 implementation this calls the real unit001 library: [2,4] is absent.
  try:import r4_core as core
  except ImportError:core=relaxed_core
  d,o=parallel_fixture();banks=core.libraries(d,o,0,core.base.CompleteIndex(o))
  self.assertIn('R2_R4_OFF_TRANSPORT',banks,'actual library never dispatches [2,4]')
  ctl=banks['R2_OFF_TRANSPORT'];new=banks['R2_R4_OFF_TRANSPORT']
  self.assertTrue(ctl['complete']);self.assertIsNone(ctl['selected']);self.assertTrue(new['complete'])
  self.assertIsNotNone(new['selected'],[r['reason'] for r in new['records']])
  z=new['records'][new['selected']];self.assertEqual(z['relaxed_rule_groups'],[2,4]);self.assertTrue(z['metrics']['parallel_conflicts']);self.assertTrue(np.isfinite(z['metrics']['score']));self.assertEqual(z['metrics']['kernels'],24)
  self.assertFalse(any(r['reason']=='parallel_conflict' for r in new['records']))
  self.assertTrue(any(r['reason']=='parallel_conflict' for r in ctl['records']))

 def test_replay_exact_saved_control_and_geometry_mismatch(self):
  import r4_core,r4_control,relaxed_delivery
  d,o=parallel_fixture();index=r4_core.base.CompleteIndex(o)
  current=r4_core.libraries(d,o,0,index)['R2_OFF_TRANSPORT']
  old=relaxed_core.libraries(d,o,0,index)['R2_OFF_TRANSPORT']
  self.assertEqual(relaxed_delivery.scientific(current),relaxed_delivery.scientific(old))
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);relaxed_delivery.save_library(p,old)
   receipt=r4_control.compare_library(current,p/'LIBRARY.json');self.assertTrue(receipt['complete'])
   bad=copy.deepcopy(current);next(r for r in bad['records'] if 'q' in r)['q'][0,0]+=.01
   with self.assertRaises(AssertionError):r4_control.compare_library(bad,p/'LIBRARY.json')
   bad=copy.deepcopy(current);bad['records'][0]['reason']='changed_gate'
   with self.assertRaisesRegex(AssertionError,'SCIENTIFIC_RECORD'):r4_control.compare_library(bad,p/'LIBRARY.json')

 def test_real_restored_loader_and_new_runner_before_render(self):
  import test_loader,test_scan24,scan24_loader,relaxed_loader,relaxed_delivery,r4_runner,r4_core
  test_loader.ROOT=ROOT;test_scan24.ROOT=ROOT
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=test_scan24.m5fixture(r);js(r/'raw.json',c);d=scan24_loader.load(c,lambda phase:None)
   o=copy.deepcopy(d['objects']);o[0].update(rows=np.arange(36),leaves=[0,1,2],q=np.vstack([o[i]['q'] for i in range(3)]),version=20);del o[1];del o[2]
   relaxed_delivery.save_stage(r/'accepted',c,d,o,[dict(fixture_event=True)],21,'fixture-binding')
   c.update(raw_config=str(r/'raw.json'),restore_stage=str(r/'accepted'),restore_binding='fixture-binding',initial_stage=str(r/'accepted'),initial_next_version=21,seed_versions={'0':20},arms=list(r4_core.POLICIES),arm_policies=r4_core.POLICIES,max_seconds=1800,absolute_deadline_jst='2026-11-03T05:35:00+09:00')
   phases=[];restored=relaxed_loader.load(c,phases.append);self.assertEqual(set(phases),{'readiness'});self.assertEqual(restored['next_version'],21);np.testing.assert_array_equal(restored['objects'][0]['q'],o[0]['q'])
   def bad(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):relaxed_loader.load(c,bad)
   banks=r4_core.libraries(restored,restored['objects'],0,r4_core.base.CompleteIndex(restored['objects']));relaxed_delivery.save_library(r/'prior_library',banks['R2_OFF_TRANSPORT'])
   c['control_replay_libraries']={'0':str(r/'prior_library/LIBRARY.json')};js(r/'config.json',c)
   with patch.object(r4_runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):r4_runner.run(c,r/'config.json')
   scene=r/'run/scenes/fixture'
   for stage in ['START','R2_OFF_TRANSPORT_FINAL','R2_R4_OFF_TRANSPORT_FINAL']:
    verify_checkpoint(scene/'stages'/stage,sha(r/'config.json'));self.assertEqual(len(np.load(scene/'stages'/stage/'MEMBERSHIP.npz')['edge_id']),36)
   self.assertTrue(json.loads((scene/'CONTROL_STATE_PARITY.json').read_text())['identical'])
   self.assertTrue(json.loads((scene/'control_replay/0.json').read_text())['complete'])
   self.assertFalse(list((r/'run').rglob('*.png')))

 def test_rule6_remains_and_r4_runner_requeries_without_cap(self):
  import whole_core as core,r4_core,r4_runner
  d,o=synthetic(2);rr=o[1]['rows'];d['asset']['means'][rr]=d['asset']['means'][o[0]['rows']];d['leaves'][1].q=o[0]['q'].copy();o[1]['q']=o[0]['q'].copy()
  self.assertEqual(core.evaluate(d,o[0],o[1],o[0]['q'],relaxed=[2,4])[1],'no_unique_support')
  d,o=synthetic(11);d['representatives'].update(member_rows=np.arange(11),member_offsets=np.arange(12));saved=[];c=dict(seed_ids=[0],arm_policies=r4_core.POLICIES)
  result,events,_,stop,_=r4_runner.grow(d,c,'R2_R4_OFF_TRANSPORT',o,20,lambda:None,lambda objects,ev,v,e:saved.append(set(objects[0]['rows'])),lambda *a:None)
  self.assertGreater(len(events),8);self.assertTrue(all(a<=b for a,b in zip(saved,saved[1:])));self.assertEqual(stop['reason'],'NATURAL_SCOPE_EXHAUSTION')
  self.assertEqual(len(result[0]['rows']),132)
  with patch.object(r4_core,'library',return_value=dict(complete=False,reason='FIT_CAPACITY',neighbors=[],records=[],selected=None)):
   _,events,_,stop,_=r4_runner.grow(d,c,'R2_R4_OFF_TRANSPORT',o,20,lambda:None,lambda *a:None,lambda *a:None)
   self.assertFalse(events);self.assertEqual(stop['status'],'PARTIAL')

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in [R4Tests,test_relaxed.RelaxedTests,WholeTests])
 result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
