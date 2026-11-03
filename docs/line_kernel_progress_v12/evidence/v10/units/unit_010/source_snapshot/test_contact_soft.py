"""Unit010 finite contact-score interface; bounded real numerical fixtures only."""
from runtime_io import *
import unittest,copy,tempfile
import group_fit_core,whole_core
import test_r6
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_010/tests')

class ContactSoftTests(unittest.TestCase):
 def test_actual_library_has_matched_finite_contact_score_policies(self):
  try:import contact_soft_core as core
  except ImportError:core=group_fit_core
  d,o=test_r6.pooling_fixture();banks=core.libraries(d,o,0,whole_core.CompleteIndex(o))
  self.assertIn('CONTACT_SOFT_J',banks,'existing actual library has no finite CONTACT_SOFT_J policy')
  base=banks['BASE_J'];soft=banks['CONTACT_SOFT_J'];self.assertTrue(base['complete'] and soft['complete'])
  for a,b in zip(base['records'],soft['records']):
   self.assertEqual(a['connectable'],b['connectable'])
   if 'q' in a:np.testing.assert_array_equal(a['q'],b['q'])
   if a['connectable']:
    self.assertAlmostEqual(b['metrics']['score'],a['metrics']['score']+.01*bool(a['metrics']['rule6']['self_contact']))
    self.assertTrue(np.isfinite(b['metrics']['score']))
  self.assertIsNotNone(soft['selected'])

 def test_real_self_contact_stays_finite_selectable_and_commits(self):
  import contact_soft_core as core,contact_soft_runner as runner
  from port_paths import Leaf
  a=np.linspace(0,2*np.pi-.08,49);q=np.c_[2*np.cos(a),2*np.sin(a),np.zeros(len(a))];x=q[[3,12,24,36,44]];tan=whole_core.project(x,q)[2];rr=np.arange(5)
  leaves={0:Leaf(0,10,rr[:3],np.array([0]),q[:25],True,True,np.array([[0.,1.]])),1:Leaf(1,11,rr[3:],np.array([1]),q[25:],True,True,np.array([[0.,1.]]))}
  d=dict(p=1.,asset=dict(means=x,covariance=np.tile(np.eye(3)*.04,(5,1,1))),tangents=tan,leaves=leaves,representatives=dict(x=x[:2],t=tan[:2]))
  objects={i:dict(id=i,version=10+i,rows=leaf.rows,leaves=[i],q=leaf.q,seed_origins=[0] if i==0 else [],available=True) for i,leaf in leaves.items()}
  ok,why,m,qq=whole_core.evaluate(d,objects[0],objects[1],q,relaxed=[2,4,6]);self.assertTrue(ok,why);self.assertTrue(m['rule6']['self_contact'])
  rec=dict(donor=1,relation='endpoint',direction=0,connectable=True,reason=why,metrics=m,q=qq,old_curve_motion_p={'max':0.})
  raw=dict(complete=True,reason='complete',neighbors=[(1,0.)],records=[rec],selected=0)
  b=core.score_bank(raw,.01);self.assertEqual(b['selected'],0);self.assertAlmostEqual(b['records'][0]['metrics']['score'],m['score']+.01)
  self.assertFalse(b['records'][0]['metrics']['closure']['supported']);self.assertTrue(b['records'][0]['connectable'])
  d['_catalogs']={core.NEW:{0:b}};saved=[]
  final,events,_,stop,_=runner.grow(d,dict(seed_ids=[0],arm_policies=core.POLICIES),core.NEW,objects,20,lambda:None,lambda o,e,v,z:saved.append(o[0]['rows'].copy()),lambda *a:None)
  self.assertEqual(len(events),1);np.testing.assert_array_equal(saved[0],rr);self.assertEqual(stop['reason'],'NATURAL_SCOPE_EXHAUSTION')

 def test_missing_contact_is_partial_not_hidden_rejection_or_truncated_winner(self):
  import contact_soft_core as core
  d,o=test_r6.pooling_fixture();raw=group_fit_core.libraries(d,o,0,whole_core.CompleteIndex(o))[group_fit_core.NEW]
  raw['records'][raw['selected']]['metrics']['rule6'].pop('self_contact')
  b=core.score_bank(raw,.01);self.assertFalse(b['complete']);self.assertIsNone(b['selected']);self.assertEqual(b['reason'],'MISSING_CONTACT_DIAGNOSTIC')
  partial=copy.deepcopy(raw);partial.update(complete=False,reason='PHASE_DEADLINE fixture',selected=None)
  b=core.score_bank(partial,.01);self.assertIsNone(b['selected'])

 def test_original_replay_and_paired_score_geometry_are_exact(self):
  import contact_soft_core as core,contact_soft_delivery as out,group_fit_delivery,test_balanced
  d,o=test_balanced.unequal_fixture();banks=core.libraries(d,o,0,whole_core.CompleteIndex(o));raw=banks[core.ORIGINAL]['baseline_fit_library']
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);group_fit_delivery.save_library(p/'prior',raw)
   self.assertTrue(group_fit_delivery.compare_library(raw,p/'prior/LIBRARY.json')['complete'])
   for policy in core.POLICIES:out.save_library(p/policy,banks[policy])
   self.assertTrue((p/core.NEW/'ROW_FIT_CONTROL/LIBRARY.json').exists())
   for original,a,b in zip(raw['records'],banks[core.ORIGINAL]['records'],banks[core.NEW]['records']):
    if original['connectable']:self.assertEqual(original['metrics']['score'],a['metrics']['score'])
    for field in ['q','template','local_movable']:
     if field in original:np.testing.assert_array_equal(original[field],a[field]);np.testing.assert_array_equal(a[field],b[field])
   bad=copy.deepcopy(raw);bad['selected']=None
   with self.assertRaisesRegex(AssertionError,'SELECTION_MISMATCH'):group_fit_delivery.compare_library(bad,p/'prior/LIBRARY.json')

 def test_real_restore_all_saved_origins_and_two_maps_before_renderer(self):
  import test_cohort,cohort_loader,contact_soft_loader,contact_soft_runner as runner,contact_soft_core as core,group_fit_delivery
  from unittest.mock import patch
  test_cohort.ROOT=ROOT
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);c,d,o=test_cohort.fixture(p);activated=cohort_loader.load(c,lambda phase:None)
   group_fit_delivery.save_stage(p/'all_tracked',c,activated,activated['objects'],[],21,'tracked-binding');js(p/'all_tracked/STOP.json',dict(status='completed',reason='FIXTURE_ONLY'))
   c.update(raw_seed_ids=[0],restore_stage=str(p/'all_tracked'),restore_binding='tracked-binding',restore_seed_versions={'0':20,'2':12},initial_stage=str(p/'all_tracked'),tracked_origin_ids=[0,2],arms=list(core.POLICIES),arm_policies=core.POLICIES,max_seconds=1320,absolute_deadline_jst='2026-11-03T05:35:00+09:00',archived_control_stage=str(p/'all_tracked'),archived_control_binding='tracked-binding',archived_control_compute_exit='fixture-not-science')
   phases=[];z=contact_soft_loader.load(c,phases.append);self.assertEqual(set(phases),{'readiness'});self.assertEqual(z['cohort_receipt']['tracked_origins'],[0,2]);self.assertEqual(z['seed_status'],{2:'READY'})
   for gid in [0,2]:np.testing.assert_array_equal(z['objects'][gid]['q'],activated['objects'][gid]['q']);np.testing.assert_array_equal(z['objects'][gid]['rows'],activated['objects'][gid]['rows'])
   def bad(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):contact_soft_loader.load(c,bad)
   prior=group_fit_core.library(z,z['objects'],2,group_fit_core.NEW,whole_core.CompleteIndex(z['objects']));group_fit_delivery.save_library(p/'prior',prior);c['control_replay_libraries']={'2':str(p/'prior/LIBRARY.json')};js(p/'config.json',c)
   with patch.object(runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):runner.run(c,p/'config.json')
   scene=p/'run/scenes/fixture'
   for stage in ['START',*[x+'_FINAL' for x in core.POLICIES]]:
    out=scene/'stages'/stage;verify_checkpoint(out,sha(p/'config.json'));np.testing.assert_array_equal(np.load(out/'MEMBERSHIP.npz')['edge_id'],z['initial_membership']['edge_id']);np.testing.assert_array_equal(np.load(out/'MODELS.npz')['group_id'],[0,2])
    fix=json.loads((out/'FIXED_SUPPORT.json').read_text());self.assertEqual(set(fix['references']),{'UNIT010_START'});self.assertEqual(len(fix['records']),2)
   result=json.loads((p/'run/RUN_RESULT.json').read_text());self.assertEqual(set(result['outputs']),set(core.POLICIES));self.assertFalse(result['actual_pngs']);self.assertTrue(json.loads((scene/'control_replay/2.json').read_text())['complete'])
   for name in ['CHECKPOINT.json','MEMBERSHIP.npz','MODELS.npz','GROUPS.json','LINEAGE.json']:self.assertEqual((p/'all_tracked'/name).read_bytes(),(scene/'stages/NO_FURTHER_GROWTH'/name).read_bytes())

 def test_new_score_runner_over_eight_and_atomic_rollback(self):
  import contact_soft_core as core,contact_soft_runner as runner
  from test_whole import synthetic
  from unittest.mock import patch
  d,o=synthetic(11);d['representatives'].update(member_rows=np.arange(11),member_offsets=np.arange(12));saved=[];c=dict(seed_ids=[0],arm_policies=core.POLICIES)
  final,ev,_,stop,_=runner.grow(d,c,core.NEW,o,20,lambda:None,lambda ob,e,v,z:saved.append(set(ob[0]['rows'])),lambda *a:None)
  self.assertGreater(len(ev),8);self.assertEqual(len(final[0]['rows']),132);self.assertTrue(all(a<=b for a,b in zip(saved,saved[1:])));self.assertEqual(stop['reason'],'NATURAL_SCOPE_EXHAUSTION')
  with patch.object(core,'library',return_value=dict(complete=False,reason='KNOT_CAPACITY',neighbors=[],records=[dict(connectable=True)],selected=0)):
   _,ev,_,stop,_=runner.grow(d,c,core.NEW,o,20,lambda:None,lambda *a:None,lambda *a:None)
  self.assertFalse(ev);self.assertEqual(stop['status'],'PARTIAL')
  lib=core.library(d,o,0,core.NEW,whole_core.CompleteIndex(o));before=copy.deepcopy(o)
  def fail(*args):raise RuntimeError('SAVE_FAILURE')
  with self.assertRaisesRegex(RuntimeError,'SAVE_FAILURE'):whole_core.commit(o,0,lib['records'][lib['selected']],20,fail)
  for gid in o:np.testing.assert_array_equal(o[gid]['rows'],before[gid]['rows']);np.testing.assert_array_equal(o[gid]['q'],before[gid]['q'])

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 import test_cohort,test_carry_forward,test_group_fit,test_balanced,test_no_u,test_relaxed,test_loader,test_scan24,test_scan65
 for m in [test_cohort,test_carry_forward,test_group_fit,test_balanced,test_no_u,test_relaxed,test_loader,test_scan24,test_scan65,test_r6]:m.ROOT=ROOT
 classes=[ContactSoftTests,test_cohort.CohortTests,test_carry_forward.CarryTests,test_group_fit.GroupFitTests,test_r6.R6Tests,test_relaxed.RelaxedTests,test_r6.WholeTests]
 result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in classes))
 raise SystemExit(0 if result.wasSuccessful() else 1)
