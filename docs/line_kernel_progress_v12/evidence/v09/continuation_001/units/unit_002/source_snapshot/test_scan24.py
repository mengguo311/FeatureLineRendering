"""Bounded fixtures only; all temporary output belongs to this continuation."""
from runtime_io import *
import unittest,tempfile,copy
import test_loader
from test_whole import WholeTests
from test_loader import LoaderTests,fixture
import scan24_loader
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_best_fragment_growth_v09_20261102/continuation_001/units/unit_001/tests')
test_loader.ROOT=ROOT

def m5fixture(r):
 c=fixture(r);c.update(initial_stage=str(r),prior_config_sha256=sha(r/'old_config.json'),seed_versions={'0':10},seed_selection_per_model=1)
 g=[dict(edge_id=i,version=10+i,valid=True,model='line',supported_length_p=4-i,M4_contributions=[dict(kernels=12,mapped_supported_length_p=2)]*2) for i in range(3)]
 js(r/'groups.json',dict(groups=g));js(r/'lineage.json',dict(events=[dict(operation='endpoint',output=[i,10+i]) for i in range(3)]))
 c['groups']=str(r/'groups.json');c['lineage']=str(r/'lineage.json');c['camera_shape']=[40,30];c['camera_convention']='COLMAP_W2C_NO_GL'
 cams=[dict(view=v,width=40,height=30,fx=20.,fy=20.,cx=20.,cy=15.,extrinsic=np.eye(4).tolist()) for v in ['a','b']]
 (r/'cameras.json').write_text(json.dumps({'fixture':cams}));return c

class ScanTests(unittest.TestCase):
 def test_full_object_crop_keeps_unqueried_depth_competitor(self):
  from scan24_delivery import union_box,crop_full_context
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);iso=np.full((50,70,3),255,np.uint8);iso[25,30]=[80,20,10]
   box,ink=union_box([Image.fromarray(iso)]);self.assertEqual(box,(14,9,47,42));self.assertEqual(ink,1)
   full=iso.copy();full[25,35]=[10,30,90];Image.fromarray(full).save(r/'full.png')
   crop_full_context(r/'full.png',r/'context.png',box)
   a=np.asarray(Image.open(r/'context.png'));np.testing.assert_array_equal(a[25-box[1],35-box[0]],[10,30,90])
 def test_cameras_use_native_colmap_and_validate_shape(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   c=m5fixture(Path(td));z=scan24_loader.cameras(c);self.assertTrue(z['no_axis_conversion'])
   np.testing.assert_array_equal(z['cameras'][0]['extrinsic'],np.eye(4));c['camera_shape']=[800,800]
   with self.assertRaisesRegex(AssertionError,'CAMERA_SIZE'):scan24_loader.cameras(c)
 def test_seed_version_failure_not_replaced(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   c=m5fixture(Path(td));c['seed_versions']['0']=999;d=scan24_loader.load(c,lambda phase:None)
   self.assertEqual(d['seed_status'][0],'NOT_RUN_SEED_BINDING');self.assertFalse(any(o['seed_origins'] for o in d['objects'].values()))
 def test_scan24_runner_cold_maps_before_native_renderer(self):
  from unittest.mock import patch
  import scan24_runner,whole_runner
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=m5fixture(r);js(r/'config.json',c);old=(whole_runner.load,whole_runner.grow,whole_runner.diagnostics)
   try:
    with patch.object(whole_runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
     with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):scan24_runner.run(c,r/'config.json')
   finally:whole_runner.load,whole_runner.grow,whole_runner.diagnostics=old
   result=json.loads((r/'run/RUN_RESULT.json').read_text())
   self.assertEqual(result['actual_pngs'],[])
   for arm in ['START','LOCAL_FINAL','WHOLE_FINAL']:
    out=r/'run/scenes/fixture/stages'/arm;verify_checkpoint(out,sha(r/'config.json'))
    np.testing.assert_array_equal(np.load(out/'MEMBERSHIP.npz')['edge_id'],np.repeat(np.arange(3),12))
 def test_real_m5_loader_without_ficus_growth_state(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=m5fixture(r);ph=[];d=scan24_loader.load(c,ph.append)
   self.assertEqual(set(ph),{'readiness'});self.assertEqual(d['next_version'],20)
   np.testing.assert_array_equal(d['initial_membership']['edge_id'],np.repeat(np.arange(3),12))
   self.assertEqual(d['objects'][0]['version'],10);self.assertEqual(d['seed_ledger']['selected'],[0])
   def bad(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):scan24_loader.load(c,bad)

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in [ScanTests,WholeTests,LoaderTests]));raise SystemExit(0 if r.wasSuccessful() else 1)
