from runtime_io import *
import unittest,tempfile,copy
import whole_core as w
from test_whole import synthetic,WholeTests
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_001/tests')

class RelaxedTests(unittest.TestCase):
 def test_rule2_distance_is_soft_not_hidden_veto(self):
  d,o=synthetic(2);d['asset']['means'][3,1]=2.;q=np.array([[0.,0,0],[4.2,0,0]])
  self.assertEqual(w.evaluate(d,o[0],o[1],q)[1],'member_distance')
  z=w.evaluate(d,o[0],o[1],q,relaxed=[2]);self.assertTrue(z[0],z[1]);self.assertTrue(np.isfinite(z[2]['score']))
  self.assertEqual(z[2]['kernels'],24);self.assertIn(3,z[2]['rule2']['distance_exceed_rows'])
 def test_rule2_angle_is_soft_and_strict_unchanged(self):
  d,o=synthetic(2);d['tangents'][5]=[0.,1.,0];q=np.array([[0.,0,0],[4.2,0,0]])
  self.assertEqual(w.evaluate(d,o[0],o[1],q)[1],'gross_tangent_conflict')
  z=w.evaluate(d,o[0],o[1],q,relaxed=[2]);self.assertTrue(z[0],z[1]);self.assertGreater(z[2]['max_angle_deg'],75);self.assertTrue(np.isfinite(z[2]['score']))
 def test_rule6_pure_pooling_is_allowed_only_when_off(self):
  d,o=synthetic(2);rr=o[1]['rows'];d['asset']['means'][rr]=d['asset']['means'][o[0]['rows']];d['leaves'][1].q=o[0]['q'].copy();o[1]['q']=o[0]['q'].copy();q=o[0]['q'].copy()
  self.assertEqual(w.evaluate(d,o[0],o[1],q)[1],'no_unique_support')
  z=w.evaluate(d,o[0],o[1],q,relaxed=[6]);self.assertTrue(z[0],z[1]);self.assertEqual(z[2]['unique_donor_support_p'],0);self.assertTrue(np.isfinite(z[2]['score']))
 def test_rule4_parallel_is_diagnostic_only_when_off(self):
  d,o=synthetic(2);rr=o[1]['rows'];d['asset']['means'][rr]=np.c_[np.linspace(0,4,12),np.full(12,.8),np.zeros(12)];q1=np.array([[0.,.8,0],[4.,.8,0]]);d['leaves'][1].q=q1;o[1]['q']=q1
  q=np.array([[0.,.4,0],[4.,.4,0]]);self.assertEqual(w.evaluate(d,o[0],o[1],q)[1],'parallel_conflict')
  z=w.evaluate(d,o[0],o[1],q,relaxed=[4]);self.assertTrue(z[0],z[1]);self.assertTrue(z[2]['parallel_conflicts'])
 def test_strict_numerical_parity(self):
  import strict_whole_core as old
  d,o=synthetic(2);q=np.array([[0.,0,0],[4.2,0,0]])
  a=old.evaluate(d,o[0],o[1],q);b=w.evaluate(d,o[0],o[1],q)
  self.assertEqual(a[:2],b[:2]);self.assertEqual(a[2]['score'],b[2]['score']);np.testing.assert_array_equal(a[3],b[3])
 def test_remaining_degeneracy_not_relaxed(self):
  d,o=synthetic(2);q=np.array([[0.,0,0],[2.,0,0],[0.,0,0]])
  self.assertEqual(w.evaluate(d,o[0],o[1],q,relaxed=[2,4,6])[1],'vertex_degeneracy')
 def test_rule6_gap_and_selfcontact_have_no_hidden_veto(self):
  d,o=synthetic(2);rr=o[1]['rows'];d['asset']['means'][rr,0]+=2.8;d['leaves'][1].q=d['leaves'][1].q+[2.8,0,0];o[1]['q']=d['leaves'][1].q.copy();q=np.array([[0.,0,0],[7.,0,0]])
  self.assertEqual(w.evaluate(d,o[0],o[1],q)[1],'unsupported_gap')
  z=w.evaluate(d,o[0],o[1],q,relaxed=[6]);self.assertTrue(z[0],z[1]);self.assertGreater(z[2]['max_gap_p'],1.5)
  # A real nonlocal self-contact on a nearly closed finite arc; fewer than3 end rows prevents closure certification.
  from port_paths import Leaf
  angles=np.linspace(0,2*np.pi-.08,49);q=np.c_[2*np.cos(angles),2*np.sin(angles),np.zeros(len(angles))];x=q[[3,12,24,36,44]];tan=w.project(x,q)[2];rows=np.arange(5)
  leaves={0:Leaf(0,0,rows[:3],np.array([0]),q[:25],True,True,np.array([[0.,1.]])),1:Leaf(1,1,rows[3:],np.array([1]),q[25:],True,True,np.array([[0.,1.]]))}
  d=dict(p=1.,asset=dict(means=x,covariance=np.tile(np.eye(3)*.04,(5,1,1))),tangents=tan,leaves=leaves,representatives=dict(x=x[:2],t=tan[:2]));g=dict(rows=rows[:3],leaves=[0]);f=dict(rows=rows[3:],leaves=[1])
  self.assertEqual(w.evaluate(d,g,f,q,relaxed=[2,4])[1],'nonlocal_contact')
  z=w.evaluate(d,g,f,q,relaxed=[2,4,6]);self.assertTrue(z[0],z[1]);self.assertTrue(z[2]['contact']['reject']);self.assertFalse(z[2]['closure']['supported'])
 def test_real_m5_loader_restores_composite_and_guard(self):
  import test_loader,test_scan24,scan24_loader,relaxed_loader,whole_delivery
  test_loader.ROOT=ROOT;test_scan24.ROOT=ROOT
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=test_scan24.m5fixture(r);js(r/'raw.json',c);d=scan24_loader.load(c,lambda phase:None);o=copy.deepcopy(d['objects']);o[0].update(rows=np.union1d(o[0]['rows'],o[1]['rows']),leaves=[0,1],q=np.vstack([o[0]['q'],o[1]['q']]),version=20);del o[1]
   whole_delivery.save_stage(r/'accepted',c,d,o,[{'fixture_event':True}],21,'fixture-binding')
   c.update(raw_config=str(r/'raw.json'),restore_stage=str(r/'accepted'),restore_binding='fixture-binding',initial_stage=str(r/'accepted'),initial_next_version=21,seed_versions={'0':20});ph=[];got=relaxed_loader.load(c,ph.append)
   self.assertEqual(set(ph),{'readiness'});self.assertEqual(len(got['objects'][0]['rows']),24);self.assertEqual(got['next_version'],21);self.assertNotIn(1,got['objects']);np.testing.assert_array_equal(got['objects'][0]['q'],o[0]['q'])
   def fail(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):relaxed_loader.load(c,fail)
   import relaxed_runner
   from unittest.mock import patch
   c.update(arms=['STRICT_TRANSPORT','R2_OFF_TRANSPORT'],arm_policies={'STRICT_TRANSPORT':[],'R2_OFF_TRANSPORT':[2]},max_seconds=1800,absolute_deadline_jst='2026-11-03T05:35:00+09:00');js(r/'config.json',c)
   with patch.object(relaxed_runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):relaxed_runner.run(c,r/'config.json')
   for stage in ['START','STRICT_TRANSPORT_FINAL','R2_OFF_TRANSPORT_FINAL']:
    z=r/'run/scenes/fixture/stages'/stage;verify_checkpoint(z,sha(r/'config.json'));self.assertEqual(len(np.load(z/'MEMBERSHIP.npz')['edge_id']),36)
   self.assertTrue((r/'run/scenes/fixture/INITIAL_CATALOG_RECEIPT.json').exists())
 def test_new_runner_requeries_more_than_eight_and_no_truncated_winner(self):
  import relaxed_runner,relaxed_core
  from unittest.mock import patch
  d,o=synthetic(11);d['representatives'].update(member_rows=np.arange(11),member_offsets=np.arange(12));saved=[];c=dict(seed_ids=[0],arm_policies=relaxed_core.POLICIES)
  result,ev,v,status,_=relaxed_runner.grow(d,c,'R2_OFF_TRANSPORT',o,20,lambda:None,lambda obj,e,v,z:saved.append(set(obj[0]['rows'])),lambda *a:None)
  self.assertGreater(len(ev),8);self.assertTrue(all(a<=b for a,b in zip(saved,saved[1:])));self.assertEqual(status['reason'],'NATURAL_SCOPE_EXHAUSTION')
  bad=dict(complete=False,reason='MEMBER_CAPACITY',neighbors=[],records=[],selected=None)
  with patch.object(relaxed_core,'library',return_value=bad):
   _,events,_,stop,_=relaxed_runner.grow(d,c,'R2_OFF_TRANSPORT',o,20,lambda:None,lambda *a:None,lambda *a:None)
   self.assertFalse(events);self.assertEqual(stop['status'],'PARTIAL')

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in [RelaxedTests,WholeTests])
 r=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if r.wasSuccessful() else 1)
