"""Unit008 fixed-frame evidence and actual continuation interface tests."""
from runtime_io import *
import unittest, tempfile, copy
import whole_core as whole
from unittest.mock import patch
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_008/tests')

class CarryTests(unittest.TestCase):
 def test_fixed_coordinates_keep_rows_clipping_and_original_derivative_width(self):
  try:
   from carry_forward_support import account
  except ImportError:
   def account(d,q,inherited,current):return whole.support(d,current,q)
  q=np.array([[0.,0,0],[2.,0,0]])
  x=np.array([[0.,0,0],[1.,0,0],[2.4,0,0],[1.5,.4,0]])
  d=dict(p=1.,asset=dict(means=x,covariance=np.tile(np.diag([.04,.25,.01]),(4,1,1))),tangents=np.array([[1.,0,0],[0,1.,0],[1.,0,0],[0.,0,0]]))
  before=copy.deepcopy(d);result=account(d,q,np.array([0,1]),np.arange(4))
  self.assertIn('evidence',result,'dynamic support lacks fixed-reference row/extrapolation accounting')
  e=result['evidence'];s=result['summary']
  np.testing.assert_array_equal(e['rows'],np.arange(4));np.testing.assert_array_equal(e['valid'],[True,True,True,False])
  self.assertAlmostEqual(e['half'][1],.5);self.assertAlmostEqual(e['finite_s'][2],2.)
  self.assertAlmostEqual(e['extended_s'][2],2.4);self.assertFalse(e['valid'][3])
  self.assertTrue(e['clipped'][2].any());self.assertEqual(s['sets']['current']['rows'],4)
  self.assertGreater(s['new_minus_inherited_p'],0);self.assertFalse(s['used_for_decision'])
  np.testing.assert_array_equal(d['asset']['means'],before['asset']['means'])
  np.testing.assert_array_equal(q,[[0,0,0],[2,0,0]])

 def test_complete_and_interrupted_prefix_exact_replay(self):
  import group_fit_core as core,group_fit_delivery as delivery,test_balanced
  from carry_forward_support import compare_saved
  d,o=test_balanced.unequal_fixture();lib=core.library(d,o,0,core.NEW,whole.CompleteIndex(o))
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);delivery.save_library(p/'complete',lib)
   self.assertTrue(compare_saved(lib,p/'complete/LIBRARY.json')['complete'])
   old=copy.deepcopy(lib);old.update(complete=False,reason='PHASE_DEADLINE fixture',selected=None)
   old['records']=old['records'][:2]+[dict(donor=old['records'][2]['donor'],relation=old['records'][2]['relation'],direction=old['records'][2]['direction'],reason='template',connectable=False)]
   delivery.save_library(p/'partial',old);receipt=compare_saved(lib,p/'partial/LIBRARY.json')
   self.assertEqual(receipt['completed_prefix_records'],2);self.assertEqual(receipt['excluded_interrupted_records'],[2])
   bad=copy.deepcopy(lib);bad['records'][0]['reason']='corrupted'
   with self.assertRaisesRegex(AssertionError,'PREFIX_RECORD_MISMATCH'):compare_saved(bad,p/'partial/LIBRARY.json')
   bad=copy.deepcopy(lib);bad['neighbors']=[]
   with self.assertRaisesRegex(AssertionError,'NEIGHBORS_MISMATCH'):compare_saved(bad,p/'partial/LIBRARY.json')
   bad=copy.deepcopy(lib);bad['complete']=False
   with self.assertRaisesRegex(AssertionError,'NEW_LIBRARY_INCOMPLETE'):compare_saved(bad,p/'partial/LIBRARY.json')

 def test_actual_loader_restores_prior_union_and_maps_before_renderer(self):
  import test_scan65,test_loader,test_scan24,test_relaxed
  import scan65_loader,branch_loader,carry_forward_runner as runner,group_fit_core as core,group_fit_delivery as delivery
  for module in [test_scan65,test_loader,test_scan24,test_relaxed]:module.ROOT=ROOT
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=test_scan65.m4fixture(r);js(r/'raw.json',c);d=scan65_loader.load(c,lambda phase:None)
   o=copy.deepcopy(d['objects']);o[0].update(rows=np.arange(36),leaves=[0,1,2],q=np.vstack([o[i]['q'] for i in range(3)]),version=20);del o[1];del o[2]
   delivery.save_stage(r/'accepted',c,d,o,[dict(fixture_event=True)],21,'fixture-binding');js(r/'accepted/STOP.json',dict(status='completed',reason='NATURAL_SCOPE_EXHAUSTION'))
   c.update(raw_config=str(r/'raw.json'),restore_stage=str(r/'accepted'),restore_binding='fixture-binding',initial_stage=str(r/'accepted'),initial_next_version=21,seed_versions={'0':20},arms=[core.NEW],arm_policies=core.POLICIES,max_seconds=1350,absolute_deadline_jst='2026-11-03T05:35:00+09:00',archived_control_stage=str(r/'accepted'),archived_control_binding='fixture-binding',archived_control_compute_exit='fixture-not-science',fixed_reference_stages={name:dict(stage=str(r/'accepted'),binding='fixture-binding') for name in ['UNIT007_START','UNIT008_START']})
   phases=[];restored=branch_loader.load(c,phases.append);self.assertEqual(set(phases),{'readiness'});self.assertEqual(restored['next_version'],21)
   np.testing.assert_array_equal(restored['objects'][0]['q'],o[0]['q'])
   def bad_guard(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):branch_loader.load(c,bad_guard)
   prior=core.library(restored,restored['objects'],0,core.NEW,whole.CompleteIndex(restored['objects']));delivery.save_library(r/'library',prior);c['control_replay_libraries']={'0':str(r/'library/LIBRARY.json')};js(r/'config.json',c)
   with patch.object(runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):runner.run(c,r/'config.json')
   scene=r/'run/scenes/fixture'
   for stage in ['START',core.NEW+'_FINAL']:
    out=scene/'stages'/stage;verify_checkpoint(out,sha(r/'config.json'));np.testing.assert_array_equal(np.load(out/'MEMBERSHIP.npz')['edge_id'],restored['initial_membership']['edge_id'])
    diag=json.loads((out/'FIXED_SUPPORT.json').read_text());self.assertFalse(diag['used_for_decision']);self.assertEqual(len(diag['records']),2)
    self.assertTrue(all(z['new_minus_inherited_p']==0 for z in diag['records']))
   result=json.loads((r/'run/RUN_RESULT.json').read_text());self.assertTrue(result['fixed_support_diagnostics_complete']);self.assertFalse(result['actual_pngs'])
   self.assertFalse(result['archived_control']['matched_to_this_start']);self.assertTrue(json.loads((scene/'control_replay/0.json').read_text())['complete'])
   for n in ['CHECKPOINT.json','MEMBERSHIP.npz','MODELS.npz','GROUPS.json','LINEAGE.json']:
    self.assertEqual((r/'accepted'/n).read_bytes(),(scene/'stages/NO_FURTHER_GROWTH'/n).read_bytes())

 def test_inherited_member_loss_is_not_hidden(self):
  from carry_forward_support import account
  d=dict(p=1.,asset=dict(means=np.zeros((2,3)),covariance=np.tile(np.eye(3),(2,1,1))),tangents=np.ones((2,3)))
  with self.assertRaisesRegex(AssertionError,'MEMBERS_LOST'):account(d,np.array([[0,0,0],[1,0,0]]),[0,1],[0])

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 import test_group_fit,test_r6,test_relaxed,test_loader,test_scan24,test_scan65,test_balanced,test_no_u
 for m in [test_group_fit,test_r6,test_relaxed,test_loader,test_scan24,test_scan65,test_balanced,test_no_u]:m.ROOT=ROOT
 classes=[CarryTests,test_group_fit.GroupFitTests,test_r6.R6Tests,test_relaxed.RelaxedTests,test_r6.WholeTests]
 result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in classes))
 raise SystemExit(0 if result.wasSuccessful() else 1)
