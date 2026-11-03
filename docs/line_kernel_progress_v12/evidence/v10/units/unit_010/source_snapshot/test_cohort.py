"""Unit009: actual restricted-loader cohort handoff, with no full-asset execution."""
from runtime_io import *
import unittest,tempfile,copy
import test_scan65,test_loader,test_scan24,test_relaxed
import scan65_loader,group_fit_delivery as delivery
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_009/tests')

def fixture(r):
 for m in [test_scan65,test_loader,test_scan24,test_relaxed]:m.ROOT=ROOT
 c=test_scan65.m4fixture(r)
 g=json.loads(Path(c['groups']).read_text());g['groups'][2]['supported_length_p']=12.
 Path(c['groups']).write_text(json.dumps(g));c['input_files'][c['groups']]=sha(c['groups'])
 js(r/'raw.json',c);d=scan65_loader.load(c,lambda phase:None);o=copy.deepcopy(d['objects'])
 o[0].update(rows=np.arange(24),leaves=[0,1],q=np.vstack([o[0]['q'],o[1]['q']]),version=20);del o[1]
 delivery.save_stage(r/'accepted',c,d,o,[dict(fixture_event=True)],21,'fixture-binding')
 js(r/'accepted/STOP.json',dict(status='completed',reason='NATURAL_SCOPE_EXHAUSTION'))
 c.update(raw_config=str(r/'raw.json'),restore_stage=str(r/'accepted'),restore_binding='fixture-binding',initial_stage=str(r/'accepted'),initial_next_version=21,restore_seed_ids=[0],restore_seed_versions={'0':20},seed_ids=[2],seed_versions={'2':12},seed_expected_rows={'2':12},tracked_origin_ids=[0,2])
 return c,d,o

class CohortTests(unittest.TestCase):
 def test_actual_loader_keeps_old_composite_and_activates_new_origin(self):
  try:from cohort_loader import load
  except ImportError:from branch_loader import load
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c,d,o=fixture(r);phases=[];z=load(c,phases.append)
   self.assertEqual(z['objects'][0]['seed_origins'],[0]);self.assertEqual(z['objects'][2]['seed_origins'],[2])
   self.assertEqual(z['seed_status'],{2:'READY'});self.assertEqual(z['next_version'],21)
   for gid in [0,2]:
    np.testing.assert_array_equal(z['objects'][gid]['rows'],o[gid]['rows']);np.testing.assert_array_equal(z['objects'][gid]['q'],o[gid]['q']);self.assertEqual(z['objects'][gid]['version'],o[gid]['version'])
   np.testing.assert_array_equal(z['initial_membership']['edge_id'],np.load(r/'accepted/MEMBERSHIP.npz')['edge_id'])
   self.assertEqual(set(phases),{'readiness'})
   def bad(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):load(c,bad)

 def test_no_replacement_on_new_version_failure(self):
  from cohort_loader import load
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   c,d,o=fixture(Path(td));c['seed_versions']['2']=999;z=load(c,lambda phase:None)
   self.assertEqual(z['seed_status'][2],'NOT_RUN_SEED_BINDING');self.assertEqual(z['objects'][2]['seed_origins'],[])
   self.assertEqual(z['objects'][0]['seed_origins'],[0]);self.assertEqual(z['next_version'],21)

 def test_real_restore_replay_new_catalog_and_maps_before_renderer(self):
  from unittest.mock import patch
  import cohort_loader,cohort_runner as runner,group_fit_core as core
  import whole_core as whole
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c,d,o=fixture(r);z=cohort_loader.load(c,lambda phase:None)
   old=core.library(z,z['objects'],0,core.NEW,whole.CompleteIndex(z['objects']));self.assertIsNone(old['selected']);delivery.save_library(r/'old_library',old)
   c.update(arms=[core.NEW],arm_policies=core.POLICIES,max_seconds=1350,absolute_deadline_jst='2026-11-03T05:35:00+09:00',archived_control_stage=str(r/'accepted'),archived_control_binding='fixture-binding',archived_control_compute_exit='fixture-not-science',control_replay_libraries={'0':str(r/'old_library/LIBRARY.json')})
   js(r/'config.json',c)
   with patch.object(runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):runner.run(c,r/'config.json')
   scene=r/'run/scenes/fixture'
   for stage in ['START',core.NEW+'_FINAL']:
    out=scene/'stages'/stage;verify_checkpoint(out,sha(r/'config.json'));bank=np.load(out/'MODELS.npz');np.testing.assert_array_equal(bank['group_id'],[0,2]);np.testing.assert_array_equal(bank['version'],[20,12])
    np.testing.assert_array_equal(np.load(out/'MEMBERSHIP.npz')['edge_id'],z['initial_membership']['edge_id'])
    support=json.loads((out/'FIXED_SUPPORT.json').read_text());self.assertEqual({v['seed_origin'] for v in support['records']},{0,2});self.assertTrue(all(v['new_minus_inherited_p']==0 for v in support['records']))
   self.assertTrue(json.loads((scene/'RESTORE_REPLAY_RECEIPT.json').read_text())['complete'])
   self.assertEqual(json.loads((scene/'COHORT_SELECTION.json').read_text())['selected'],[2])
   self.assertEqual(json.loads((scene/'stages'/f'{core.NEW}_FINAL/STOP.json').read_text())['groups'],{'2':'NO_CONNECTABLE_FRAGMENT'})
   for policy in core.POLICIES:self.assertTrue((scene/'initial_catalogs'/policy/'2/LIBRARY.json').is_file())
   for name in ['CHECKPOINT.json','MEMBERSHIP.npz','MODELS.npz','GROUPS.json','LINEAGE.json']:self.assertEqual((r/'accepted'/name).read_bytes(),(scene/'stages/NO_FURTHER_GROWTH'/name).read_bytes())

 def test_all_eleven_origins_cold_checkpoint_and_reference_survival(self):
  from test_whole import synthetic
  from cohort_support import freeze_references,save_diagnostics
  d,o=synthetic(11);owners=d['asset']['primitive_id'];n=len(owners)
  d.update(objects=o,initial_membership=dict(edge_id=owners.copy(),carrier_id=owners.copy(),line_kernel_id=np.arange(n)),historical_events=[],cohort_receipt={'tracked_origins':list(range(11))})
  for gid,obj in o.items():obj['seed_origins']=[gid]
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=dict(initial_stage='fixture-background');delivery.save_stage(r/'START',c,d,o,[],21,'fixture')
   freeze_references(c,d,r/'START','fixture',lambda phase:None);self.assertEqual(len(d['_fixed_references']['UNIT009_START']),11)
   save_diagnostics(r/'START',c,d,lambda:None)
   report=json.loads((r/'START/FIXED_SUPPORT.json').read_text());self.assertEqual(len(report['records']),11)
   self.assertTrue(all(x['new_minus_inherited_p']==0 for x in report['records']))

 def test_new_runner_requeries_over_eight_and_partial_never_promotes(self):
  from test_whole import synthetic
  from unittest.mock import patch
  import cohort_runner as runner,group_fit_core as core
  d,o=synthetic(11);d['representatives'].update(member_rows=np.arange(11),member_offsets=np.arange(12));d['seed_status']={0:'READY'};saved=[];c=dict(seed_ids=[0],arm_policies=core.POLICIES)
  final,events,version,stop,ctx=runner.grow(d,c,core.NEW,o,20,lambda:None,lambda objects,ev,v,e:saved.append(set(objects[0]['rows'])),lambda *a:None)
  self.assertGreater(len(events),8);self.assertEqual(len(final[0]['rows']),132);self.assertEqual(stop['reason'],'NATURAL_SCOPE_EXHAUSTION');self.assertTrue(all(a<=b for a,b in zip(saved,saved[1:])))
  with patch.object(core,'library',return_value=dict(complete=False,reason='KNOT_CAPACITY',neighbors=[],records=[dict(connectable=True)],selected=0)):
   final,events,_,stop,_=runner.grow(d,c,core.NEW,o,20,lambda:None,lambda *a:None,lambda *a:None)
  self.assertFalse(events);self.assertEqual(stop['status'],'PARTIAL');np.testing.assert_array_equal(final[0]['rows'],o[0]['rows'])

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 import test_carry_forward,test_group_fit,test_r6,test_balanced,test_no_u
 for m in [test_carry_forward,test_group_fit,test_r6,test_balanced,test_no_u,test_scan65,test_loader,test_scan24,test_relaxed]:m.ROOT=ROOT
 classes=[CohortTests,test_carry_forward.CarryTests,test_group_fit.GroupFitTests,test_r6.R6Tests,test_relaxed.RelaxedTests,test_r6.WholeTests]
 result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in classes))
 raise SystemExit(0 if result.wasSuccessful() else 1)
