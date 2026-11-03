from runtime_io import *
import unittest,tempfile
import test_cohort
ROOT=Path("/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_011/tests")
class NewSeedsTests(unittest.TestCase):
 def test_real_restore_then_activate_without_mutating_old_union(self):
  try:from final_cohort_loader import load
  except ImportError:from contact_soft_loader import load
  test_cohort.ROOT=ROOT
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   c,d,o=test_cohort.fixture(Path(td));c.update(raw_seed_ids=[0],restored_origin_ids=[0]);phases=[];z=load(c,phases.append)
   self.assertEqual(z['objects'][2]['seed_origins'],[2]);self.assertEqual(z['objects'][0]['seed_origins'],[0]);self.assertEqual(z['next_version'],21)
   for gid in [0,2]:
    np.testing.assert_array_equal(o[gid]['rows'],z['objects'][gid]['rows']);np.testing.assert_array_equal(o[gid]['q'],z['objects'][gid]['q']);self.assertEqual(o[gid]['version'],z['objects'][gid]['version'])
   self.assertEqual(set(phases),{'readiness'})
   def bad(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):load(c,bad)
 def test_thirteen_origins_checkpoint_and_fixed_reference(self):
  from test_whole import synthetic
  from final_cohort_delivery import save_stage,freeze_references,save_diagnostics
  d,o=synthetic(13);owners=d['asset']['primitive_id'];n=len(owners)
  d.update(objects=o,initial_membership=dict(edge_id=owners.copy(),carrier_id=owners.copy(),line_kernel_id=np.arange(n)),historical_events=[],cohort_receipt={'tracked_origins':list(range(13))})
  for gid,obj in o.items():obj['seed_origins']=[gid]
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);c=dict(initial_stage='fixture');save_stage(p/'START',c,d,o,[],21,'fixture');freeze_references(c,d,p/'START','fixture',lambda phase:None);save_diagnostics(p/'START',c,d,lambda:None)
   verify_checkpoint(p/'START','fixture');self.assertEqual(len(d['_fixed_references']['UNIT011_START']),13);self.assertEqual(len(json.loads((p/'START/FIXED_SUPPORT.json').read_text())['records']),13)
if __name__=='__main__':
 import test_contact_soft,test_r6,test_relaxed,test_scan65,test_loader,test_scan24,test_carry_forward,test_group_fit,test_balanced,test_no_u
 for m in [test_cohort,test_contact_soft,test_r6,test_relaxed,test_scan65,test_loader,test_scan24,test_carry_forward,test_group_fit,test_balanced,test_no_u]:m.ROOT=ROOT
 classes=[NewSeedsTests,test_contact_soft.ContactSoftTests,test_r6.R6Tests,test_relaxed.RelaxedTests,test_r6.WholeTests]
 result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in classes));raise SystemExit(0 if result.wasSuccessful() else 1)
