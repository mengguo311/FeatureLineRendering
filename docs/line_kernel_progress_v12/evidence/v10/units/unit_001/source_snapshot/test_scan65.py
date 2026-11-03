from runtime_io import *
import unittest,tempfile
import test_loader,test_scan24
from paired_loader import load as restricted_load
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_best_fragment_growth_v09_20261102/continuation_001/units/unit_002/tests')
test_loader.ROOT=ROOT;test_scan24.ROOT=ROOT

def m4fixture(r):
 c=test_scan24.m5fixture(r);c['predecessor_checkpoint_stage']='M4_STATE'
 cp=json.loads((r/'CHECKPOINT.json').read_text());cp['stage']='M4_STATE';(r/'CHECKPOINT.json').write_text(json.dumps(cp))
 g=json.loads((r/'groups.json').read_text())
 for z in g['groups']:z['M3_contributions']=z.pop('M4_contributions')
 (r/'groups.json').write_text(json.dumps(g));c['challenge_seed_ids']=[];return c

class Scan65Tests(unittest.TestCase):
 def test_actual_restricted_m4_loader_guard(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   c=m4fixture(Path(td));ph=[];d=restricted_load(c,ph.append)
   self.assertEqual(d['next_version'],20);self.assertEqual(set(ph),{'readiness'})
   np.testing.assert_array_equal(d['membership']['edge_id'],np.repeat(np.arange(3),12))
   def guard(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):restricted_load(c,guard)

 def test_fixed_cohort_challenge_and_no_replacement(self):
  import scan65_loader
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=m4fixture(r);g=json.loads((r/'groups.json').read_text());g['groups'][0]['M3_contributions']=g['groups'][0]['M3_contributions'][:1];(r/'groups.json').write_text(json.dumps(g));c['challenge_seed_ids']=[0]
   d=scan65_loader.load(c,lambda phase:None);self.assertEqual(d['seed_status'][0],'READY');z=d['seed_ledger']['records'][0];self.assertTrue(z['challenge_only']);self.assertFalse(z['initial_multifragment_success'])
   c['seed_versions']['0']=999;d=scan65_loader.load(c,lambda phase:None);self.assertEqual(d['seed_ledger']['selected'],[]);self.assertEqual(d['seed_status'][0],'NOT_RUN_SEED_BINDING')
 def test_exact_original_negative_rows_and_damage_rows(self):
  from scan65_delivery import reference_items
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);nz(r/'negative.npz',rows=np.array([3,1,8]),input_ids=np.array([1,8]));nz(r/'damage.npz',carrier_id=np.array([10]),rows=np.array([2,7]),row_offsets=np.array([0,2]))
   c=dict(negative_contexts=[dict(category='branch',rows_path=str(r/'negative.npz'))],damage_carriers=str(r/'damage.npz'),damage_reference_ids=[10]);items=reference_items(c,12)
   np.testing.assert_array_equal(items[0][1],[1,3,8]);np.testing.assert_array_equal(items[1][1],[2,7]);self.assertEqual(len(items),2)
 def test_scan65_real_adapter_cold_maps_before_renderer(self):
  from unittest.mock import patch
  import scan65_runner,whole_runner
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=m4fixture(r);js(r/'config.json',c);old=(whole_runner.load,whole_runner.grow,whole_runner.diagnostics,whole_runner.statistics)
   try:
    with patch.object(whole_runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
     with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):scan65_runner.run(c,r/'config.json')
   finally:whole_runner.load,whole_runner.grow,whole_runner.diagnostics,whole_runner.statistics=old
   for arm in ['START','LOCAL_FINAL','WHOLE_FINAL']:
    out=r/'run/scenes/fixture/stages'/arm;verify_checkpoint(out,sha(r/'config.json'));np.testing.assert_array_equal(np.load(out/'MEMBERSHIP.npz')['edge_id'],np.repeat(np.arange(3),12))
   self.assertEqual(json.loads((r/'run/RUN_RESULT.json').read_text())['actual_pngs'],[])

if __name__=='__main__':
 from test_whole import WholeTests
 ROOT.mkdir(parents=True,exist_ok=True)
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in [test_scan24.ScanTests,WholeTests,test_loader.LoaderTests,Scan65Tests])
 r=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if r.wasSuccessful() else 1)
