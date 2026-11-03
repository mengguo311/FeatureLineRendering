"""Unit003 functional changes; inherited regressions are explicitly reused."""
from runtime_io import *
import unittest,tempfile,copy
from unittest.mock import patch
import whole_core as w
from test_whole import synthetic,WholeTests
import test_relaxed
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_003/tests')
test_relaxed.ROOT=ROOT

def pooling_fixture():
 d,o=synthetic(2);r=o[1]['rows'];d['asset']['means'][r]=d['asset']['means'][o[0]['rows']]
 d['leaves'][1].q=o[0]['q'].copy();o[1]['q']=o[0]['q'].copy()
 d['representatives'].update(member_rows=np.arange(2),member_offsets=np.arange(3))
 return d,o

class R6Tests(unittest.TestCase):
 def test_actual_library_dispatches_pure_pooling(self):
  try:import r6_core as core
  except ImportError:import r4_core as core
  d,o=pooling_fixture();banks=core.libraries(d,o,0,w.CompleteIndex(o))
  self.assertIn('R2_R4_R6_OFF_TRANSPORT',banks,'actual library never dispatches [2,4,6]')
  a=banks['R2_R4_OFF_TRANSPORT'];b=banks['R2_R4_R6_OFF_TRANSPORT']
  self.assertTrue(a['complete'] and b['complete']);self.assertIsNone(a['selected']);self.assertIsNotNone(b['selected'])
  z=b['records'][b['selected']];self.assertEqual(z['relaxed_rule_groups'],[2,4,6]);self.assertEqual(z['metrics']['unique_donor_support_p'],0)
  self.assertTrue(z['metrics']['rule6']['pure_pooling']);self.assertTrue(np.isfinite(z['metrics']['score']));self.assertEqual(z['metrics']['kernels'],24)
  self.assertFalse(any(r['reason'] in ['no_unique_support','unsupported_gap','nonlocal_contact'] for r in b['records']))

 def test_closed_geometry_with_support_gap_accepts_without_closed_stop(self):
  from port_paths import Leaf
  a=np.linspace(0,2*np.pi,65);q=np.c_[2*np.cos(a),2*np.sin(a),np.zeros(len(a))];q[-1]=q[0]
  idx=np.array([1,2,3,61,62,63]);x=q[idx];t=w.project(x,q)[2];rows=np.arange(6)
  leaves={0:Leaf(0,0,rows[:3],np.array([0]),q[:5],True,True,np.array([[0.,.5]])),1:Leaf(1,1,rows[3:],np.array([1]),q[-5:],True,True,np.array([[0.,.5]]))}
  d=dict(p=1.,asset=dict(means=x,covariance=np.tile(np.eye(3)*.04,(6,1,1))),tangents=t,leaves=leaves,representatives=dict(x=x[:2],t=t[:2]))
  g=dict(rows=rows[:3],leaves=[0]);f=dict(rows=rows[3:],leaves=[1])
  self.assertEqual(w.evaluate(d,g,f,q,relaxed=[2,4])[1],'unsupported_gap')
  ok,reason,meta,_=w.evaluate(d,g,f,q,relaxed=[2,4,6]);self.assertTrue(ok,reason)
  self.assertGreater(meta['max_gap_p'],1.5);self.assertTrue(np.isfinite(meta['score']))
  self.assertFalse(meta['closure']['supported'],'gap relaxation falsely certifies supported closure')

 def test_control_replay_including_nonzero_selected_and_corruption(self):
  import r6_core,r4_core,r6_control,r6_delivery
  from test_r4 import parallel_fixture
  d,o=parallel_fixture();index=w.CompleteIndex(o)
  old=r4_core.libraries(d,o,0,index)['R2_R4_OFF_TRANSPORT'];new=r6_core.libraries(d,o,0,index)['R2_R4_OFF_TRANSPORT']
  self.assertIsNotNone(old['selected'])
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);r6_delivery.save_library(p,old);receipt=r6_control.compare_library(new,p/'LIBRARY.json');self.assertEqual(receipt['selected'],old['selected'])
   bad=copy.deepcopy(new);bad['selected']=None
   with self.assertRaisesRegex(AssertionError,'SELECTION_MISMATCH'):r6_control.compare_library(bad,p/'LIBRARY.json')
   bad=copy.deepcopy(new);next(r for r in bad['records'] if 'q' in r)['q'][0,0]+=.01
   with self.assertRaises(AssertionError):r6_control.compare_library(bad,p/'LIBRARY.json')

 def test_real_loader_and_runner_archive_only_before_native_boundary(self):
  import test_loader,test_scan24,scan24_loader,relaxed_loader,r6_delivery,r6_core,r6_runner,r4_core
  test_loader.ROOT=ROOT;test_scan24.ROOT=ROOT
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=test_scan24.m5fixture(r);js(r/'raw.json',c);d=scan24_loader.load(c,lambda phase:None)
   o=copy.deepcopy(d['objects']);o[0].update(rows=np.arange(36),leaves=[0,1,2],q=np.vstack([o[i]['q'] for i in range(3)]),version=20);del o[1];del o[2]
   r6_delivery.save_stage(r/'accepted',c,d,o,[dict(fixture_event=True)],21,'fixture-binding');js(r/'accepted/STOP.json',dict(status='PARTIAL',reason='FIXTURE_ARCHIVED_CAPACITY'))
   c.update(raw_config=str(r/'raw.json'),restore_stage=str(r/'accepted'),restore_binding='fixture-binding',initial_stage=str(r/'accepted'),initial_next_version=21,seed_versions={'0':20},arms=['R2_R4_R6_OFF_TRANSPORT'],arm_policies=r6_core.POLICIES,max_seconds=1800,absolute_deadline_jst='2026-11-03T05:35:00+09:00',archived_control_stage=str(r/'accepted'),archived_control_binding='fixture-binding',archived_control_compute_exit='fixture-not-science')
   phases=[];restored=relaxed_loader.load(c,phases.append);self.assertEqual(set(phases),{'readiness'});self.assertEqual(restored['next_version'],21);np.testing.assert_array_equal(restored['objects'][0]['q'],o[0]['q'])
   def bad(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):relaxed_loader.load(c,bad)
   old=r4_core.libraries(restored,restored['objects'],0,w.CompleteIndex(restored['objects']))['R2_R4_OFF_TRANSPORT'];r6_delivery.save_library(r/'prior_library',old)
   c['control_replay_libraries']={'0':str(r/'prior_library/LIBRARY.json')};js(r/'config.json',c)
   with patch.object(r6_runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):r6_runner.run(c,r/'config.json')
   scene=r/'run/scenes/fixture'
   for stage in ['START','R2_R4_R6_OFF_TRANSPORT_FINAL']:
    verify_checkpoint(scene/'stages'/stage,sha(r/'config.json'));self.assertEqual(len(np.load(scene/'stages'/stage/'MEMBERSHIP.npz')['edge_id']),36)
   self.assertFalse((scene/'stages/R2_R4_OFF_TRANSPORT_FINAL').exists())
   ref=json.loads((scene/'ARCHIVED_CONTROL_REFERENCE.json').read_text());self.assertFalse(ref['executed_in_this_unit']);self.assertEqual(ref['stop']['reason'],'FIXTURE_ARCHIVED_CAPACITY')
   self.assertTrue(json.loads((scene/'control_replay/0.json').read_text())['complete']);self.assertFalse(list((r/'run').rglob('*.png')))

 def test_new_policy_requeries_more_than_eight_and_never_promotes_partial(self):
  import r6_core,r6_runner
  d,o=synthetic(11);d['representatives'].update(member_rows=np.arange(11),member_offsets=np.arange(12));saved=[];c=dict(seed_ids=[0],arm_policies=r6_core.POLICIES)
  result,events,_,stop,_=r6_runner.grow(d,c,'R2_R4_R6_OFF_TRANSPORT',o,20,lambda:None,lambda objects,ev,v,e:saved.append(set(objects[0]['rows'])),lambda *a:None)
  self.assertGreater(len(events),8);self.assertTrue(all(a<=b for a,b in zip(saved,saved[1:])));self.assertEqual(stop['reason'],'NATURAL_SCOPE_EXHAUSTION');self.assertEqual(len(result[0]['rows']),132)
  bad=dict(complete=False,reason='KNOT_CAPACITY',neighbors=[],records=[dict(connectable=True)],selected=0)
  with patch.object(r6_core,'library',return_value=bad):
   _,events,_,stop,_=r6_runner.grow(d,c,'R2_R4_R6_OFF_TRANSPORT',o,20,lambda:None,lambda *a:None,lambda *a:None)
  self.assertFalse(events);self.assertEqual(stop['status'],'PARTIAL')

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in [R6Tests,test_relaxed.RelaxedTests,WholeTests])
 result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
