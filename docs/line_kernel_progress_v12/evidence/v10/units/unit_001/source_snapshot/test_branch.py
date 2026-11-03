from runtime_io import *
import unittest,tempfile
import branch_core as bc
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_best_fragment_growth_v09_20261102/continuation_001/units/unit_003/tests')
class BranchTests(unittest.TestCase):
 def test_minimal_rotation_changes_axis_and_preserves_axial_reversal(self):
  a=np.array([1.,0,0]);b=np.array([0.,1,0]);np.testing.assert_allclose(bc.rotate_axis(a,a,b),b,rtol=0,atol=1e-12)
  np.testing.assert_allclose(bc.rotate_axis(-a,a,b),-b,rtol=0,atol=1e-12)
 def test_identity_and_antiparallel_unknown(self):
  a=np.array([1.,0,0]);np.testing.assert_array_equal(bc.rotate_axis(a,a,a),a)
  with self.assertRaises(bc.Incomplete):bc.rotate_axis(a,a,-a)
 def test_curved_two_arms_and_real_three_arms(self):
  from port_paths import Leaf
  from geometry_base import project
  import whole_core
  def data(x,t,q):
   n=len(x);return dict(p=1.,leaves={0:Leaf(0,0,np.arange(n),np.arange(n),q,True,True,np.array([[0.,1.]]))},representatives=dict(x=x,t=t,member_rows=np.arange(n),member_offsets=np.arange(n+1)))
  theta=np.linspace(-1.2,1.2,49);q=np.c_[4*np.cos(theta),4*np.sin(theta),np.zeros(len(theta))];x=q.copy();t=project(x,q)[2];d=data(x,t,q);centers=np.vstack([q,q])
  z=bc.scan(d,[0],q,centers,'TRANSPORT_BRANCH',lambda:None);self.assertTrue(z['decision_complete']);self.assertFalse(z['reject'])
  self.assertEqual(bc.scan(d,[0],q,centers,'RADIAL_BRANCH',lambda:None)['reject'],whole_core.branch(d,[0],q,lambda:None))
  axes=np.array([[1.,0,0],[-1.,0,0],[0,1.,0]]);x=np.concatenate([np.array([.5,1.5,3.])[:,None]*v for v in axes]);t=np.repeat(axes,3,axis=0);q=np.array([[-4.,0,0],[0,0,0],[4,0,0]]);d=data(x,t,q)
  for policy in ['RADIAL_BRANCH','TRANSPORT_BRANCH']:
   z=bc.scan(d,[0],q,np.vstack([q,q]),policy,lambda:None);self.assertTrue(z['reject']);self.assertEqual(len(z['first_witness']['source_rows']),9)
 def test_real_loader_composite_restoration_and_guard(self):
  import test_loader,test_scan24,test_scan65,scan65_loader,branch_loader,whole_delivery,copy
  test_loader.ROOT=ROOT;test_scan24.ROOT=ROOT;test_scan65.ROOT=ROOT
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=test_scan65.m4fixture(r);js(r/'raw.json',c);d=scan65_loader.load(c,lambda phase:None);o=copy.deepcopy(d['objects']);o[0].update(rows=np.union1d(o[0]['rows'],o[1]['rows']),leaves=[0,1],q=np.vstack([o[0]['q'],o[1]['q']]),version=20);del o[1]
   whole_delivery.save_stage(r/'accepted',c,d,o,[{'fixture_event':True}],21,'fixture-binding')
   c.update(raw_config=str(r/'raw.json'),restore_stage=str(r/'accepted'),restore_binding='fixture-binding',initial_stage=str(r/'accepted'),initial_next_version=21,seed_versions={'0':20});ph=[];got=branch_loader.load(c,ph.append)
   self.assertEqual(set(ph),{'readiness'});self.assertEqual(got['next_version'],21);self.assertEqual(len(got['objects'][0]['rows']),24);np.testing.assert_array_equal(got['objects'][0]['q'],o[0]['q']);self.assertNotIn(1,got['objects'])
   def guard(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):branch_loader.load(c,guard)
   import branch_runner
   lib=bc.library(got,got['objects'],0,'RADIAL_BRANCH',bc.base.CompleteIndex(got['objects']))
   old=bc.base.library(got,got['objects'],0,'WHOLE',bc.base.CompleteIndex(got['objects']));self.assertEqual(branch_runner.scientific(lib),branch_runner.scientific(old))
   whole_delivery.save_library(r/'replay',old);c['replay_libraries']={'0':str(r/'replay/LIBRARY.json')};c['max_seconds']=1200;js(r/'config.json',c)
   from unittest.mock import patch
   with patch.object(branch_runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):branch_runner.run(c,r/'config.json')
   for stage in ['START','RADIAL_BRANCH_FINAL','TRANSPORT_BRANCH_FINAL']:
    z=r/'run/scenes/fixture/stages'/stage;verify_checkpoint(z,sha(r/'config.json'));np.testing.assert_array_equal(np.load(z/'MEMBERSHIP.npz')['edge_id'],got['initial_membership']['edge_id'])
   self.assertTrue((r/'run/scenes/fixture/INITIAL_CATALOG_RECEIPT.json').exists())

if __name__=='__main__':
 import test_loader,test_scan24,test_scan65
 from test_whole import WholeTests
 test_loader.ROOT=ROOT;test_scan24.ROOT=ROOT;test_scan65.ROOT=ROOT
 ROOT.mkdir(parents=True,exist_ok=True);classes=[BranchTests,WholeTests,test_loader.LoaderTests,test_scan65.Scan65Tests]
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in classes));raise SystemExit(0 if r.wasSuccessful() else 1)
