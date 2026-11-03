"""Unit006 genuine functional score RED/GREEN; inherited tests identified separately."""
from runtime_io import *
import unittest,tempfile,copy
from unittest.mock import patch
import test_no_u,test_r6,test_relaxed,test_loader,test_scan24,test_scan65
import whole_core as w
from test_whole import synthetic
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103/units/unit_006/tests')
for module in [test_no_u,test_r6,test_relaxed,test_loader,test_scan24,test_scan65]:module.ROOT=ROOT

def unequal_fixture():
 d,o=synthetic(3);d['representatives'].update(member_rows=np.arange(3),member_offsets=np.arange(4))
 o[0].update(rows=np.union1d(o[0]['rows'],o[1]['rows']),leaves=[0,1],q=np.vstack([o[0]['q'],o[1]['q']]))
 del o[1]
 d['asset']['means'][o[2]['rows'],1]=.3
 d['tangents'][o[2]['rows']]=[np.cos(80*np.pi/180),np.sin(80*np.pi/180),0.]
 return d,o

class BalancedTests(unittest.TestCase):
 def test_actual_library_equal_group_weight_not_pooled_mean(self):
  try:import balanced_core as core
  except ImportError:import no_u_core as core
  d,o=unequal_fixture();banks=core.libraries(d,o,0,w.CompleteIndex(o))
  self.assertIn('GROUP_BALANCED_SCORE',banks,'actual catalog has no GROUP_BALANCED_SCORE policy')
  old=banks['NO_U_REWARD'];new=banks['GROUP_BALANCED_SCORE'];self.assertTrue(new['complete']);self.assertIsNotNone(new['selected']);changed=False
  for a,b in zip(old['records'],new['records']):
   self.assertEqual(a['connectable'],b['connectable']);self.assertEqual(a['reason'],b['reason'])
   if 'q' in a:np.testing.assert_array_equal(a['q'],b['q'])
   if not b['connectable']:continue
   Ds=[];Ts=[]
   for gid in [0,b['donor']]:
    rows=o[gid]['rows'];_,dist,tan,_,_=w.project(d['asset']['means'][rows]/d['p'],b['q']);t=d['tangents'][rows];valid=np.isfinite(t).all(1)&(np.linalg.norm(t,axis=1)>w.EPS)
    Ds.append(np.mean(dist**2));Ts.append(np.mean((np.degrees(np.arccos(np.clip(abs(np.sum(t[valid]*tan[valid],1)),0,1)))/90)**2))
   m=b['metrics'];expected=.5*sum(Ds)+.25*np.mean(Ts)+.05*m['turn_mean_square']+.1*m['max_gap_p']**2+.02*len(b['q'])/(m['length_p']+1)
   self.assertAlmostEqual(m['score'],expected,places=12);self.assertEqual(m['score_no_u_reward'],a['metrics']['score']);self.assertTrue(np.isfinite(m['score']));changed|=abs(m['score']-a['metrics']['score'])>1e-8
   self.assertEqual(m['group_balance']['G']['count'],24);self.assertEqual(m['group_balance']['F']['count'],12)
  self.assertTrue(changed)

 def test_missing_side_direction_normalization_without_new_veto(self):
  import balanced_core as core
  for missing in ['G','F','both']:
   d,o=test_r6.pooling_fixture()
   if missing in ['G','both']:d['tangents'][o[0]['rows']]=0
   if missing in ['F','both']:d['tangents'][o[1]['rows']]=0
   banks=core.libraries(d,o,0,w.CompleteIndex(o));old=banks[core.ORIGINAL];new=banks[core.NEW]
   self.assertTrue(new['complete']);self.assertEqual([z['reason'] for z in old['records']],[z['reason'] for z in new['records']])
   if missing=='both':
    self.assertIsNone(new['selected']);self.assertIn('UNKNOWN_direction',[z['reason'] for z in new['records']]);continue
   self.assertIsNotNone(new['selected']);m=new['records'][new['selected']]['metrics'];meta=m['group_balance'];other='F' if missing=='G' else 'G'
   self.assertEqual(meta[missing]['direction_status'],'UNKNOWN');self.assertEqual(meta[missing]['direction_weight'],0);self.assertEqual(meta[other]['direction_weight'],1);self.assertTrue(np.isfinite(m['score']));self.assertEqual(meta[missing]['count'],12)

 def test_size_balancing_changes_best_without_eligibility_gate(self):
  import balanced_core as core
  q=np.array([[0.,0,0],[10.,0,0]]);x=np.c_[np.full(201,5.),np.r_[np.zeros(100),.6,np.full(100,.5)],np.zeros(201)]
  d=dict(p=1.,asset=dict(means=x),tangents=np.tile([1.,0,0],(201,1)));g=dict(rows=np.arange(100));donors=[dict(rows=np.array([100])),dict(rows=np.arange(101,201))];records=[]
  for i,f in enumerate(donors,1):
   rr=np.union1d(g['rows'],f['rows']);dist=w.project(x[rr],q)[1];m=dict(score=float(np.mean(dist**2)+.04/11),turn_mean_square=0.,max_gap_p=0.,length_p=10.)
   records.append(dict(donor=i,relation='overlap',direction=0,connectable=True,q=q.copy(),metrics=m))
  self.assertEqual(w.best(records),0)
  for rec,f in zip(records,donors):core.balanced_record(d,g,f,rec)
  self.assertEqual(w.best(records),1);self.assertTrue(all(r['connectable'] and np.isfinite(r['metrics']['score']) for r in records))

 def test_compact_evidence_equal_sizes_and_incomplete_score_not_promoted(self):
  import balanced_core as core,balanced_delivery as delivery
  d,o=test_r6.pooling_fixture();banks=core.libraries(d,o,0,w.CompleteIndex(o));old=banks[core.ORIGINAL];new=banks[core.NEW];z=new['records'][new['selected']]
  self.assertAlmostEqual(z['metrics']['score'],old['records'][old['selected']]['metrics']['score']);self.assertEqual(z['metrics']['unique_donor_support_p'],0.)
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);delivery.save_library(p,new);saved=json.loads((p/'LIBRARY.json').read_text())['records'][new['selected']];arrays=dict(np.load(p/'SCORE_EVIDENCE.npz',allow_pickle=False))
   self.assertNotIn('score_evidence',saved)
   for k,v in z['score_evidence'].items():np.testing.assert_array_equal(arrays[saved['score_evidence_arrays'][k]],v)
   diag=json.loads((p/'RELATION_DIAGNOSTICS.json').read_text())['policies'][core.NEW]['donors'][0]['interpretations'][new['selected']]
   self.assertAlmostEqual(sum(diag['score_terms'].values()),z['metrics']['score'])
  with patch.object(core,'balanced_record',side_effect=w.Incomplete('SCORE_DEADLINE')):
   lib=core.libraries(d,o,0,w.CompleteIndex(o))[core.NEW];self.assertFalse(lib['complete']);self.assertIsNone(lib['selected']);self.assertEqual(lib['reason'],'SCORE_DEADLINE')

 def test_no_u_control_exact_replay_with_nonzero_selection(self):
  import balanced_core as core,no_u_core,r6_control,no_u_delivery
  d,o=unequal_fixture();old=no_u_core.libraries(d,o,0,w.CompleteIndex(o))[core.ORIGINAL];new=core.libraries(d,o,0,w.CompleteIndex(o))[core.ORIGINAL]
  self.assertIsNotNone(new['selected'])
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   p=Path(td);no_u_delivery.save_library(p,old);self.assertTrue(r6_control.compare_library(new,p/'LIBRARY.json')['complete'])
   bad=copy.deepcopy(new);bad['records'][bad['selected']]['metrics']['score']+=.001
   with self.assertRaisesRegex(AssertionError,'SCIENTIFIC_RECORD_MISMATCH'):r6_control.compare_library(bad,p/'LIBRARY.json')

 def test_balanced_scores_keep_relaxed_gap_and_selfcontact_finite(self):
  import balanced_core as core
  from port_paths import Leaf
  def score(d,g,f,q):
   ok,why,m,qq=w.evaluate(d,g,f,q,relaxed=[2,4,6]);self.assertTrue(ok,why);U=m['unique_donor_support_p'];m['score']+=.25*U/(1+U)
   rec=dict(q=qq,metrics=m);core.balanced_record(d,g,f,rec);self.assertTrue(np.isfinite(rec['metrics']['score']));self.assertFalse(rec['metrics']['closure']['supported']);return rec
  d,o=synthetic(2);rr=o[1]['rows'];d['asset']['means'][rr,0]+=2.8;d['leaves'][1].q=d['leaves'][1].q+[2.8,0,0];o[1]['q']=d['leaves'][1].q.copy()
  z=score(d,o[0],o[1],np.array([[0.,0,0],[7.,0,0]]));self.assertTrue(z['metrics']['rule6']['gap_exceeded'])
  a=np.linspace(0,2*np.pi-.08,49);q=np.c_[2*np.cos(a),2*np.sin(a),np.zeros(len(a))];x=q[[3,12,24,36,44]];tan=w.project(x,q)[2];rows=np.arange(5)
  leaves={0:Leaf(0,0,rows[:3],np.array([0]),q[:25],True,True,np.array([[0.,1.]])),1:Leaf(1,1,rows[3:],np.array([1]),q[25:],True,True,np.array([[0.,1.]]))}
  d=dict(p=1.,asset=dict(means=x,covariance=np.tile(np.eye(3)*.04,(5,1,1))),tangents=tan,leaves=leaves,representatives=dict(x=x[:2],t=tan[:2]));g=dict(rows=rows[:3],leaves=[0]);f=dict(rows=rows[3:],leaves=[1]);z=score(d,g,f,q);self.assertTrue(z['metrics']['rule6']['self_contact'])

 def test_actual_m4_loader_replay_archive_and_new_map_before_renderer(self):
  import scan65_loader,branch_loader,balanced_runner as runner,balanced_core as core,balanced_delivery as delivery,no_u_core,no_u_delivery
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=test_scan65.m4fixture(r);js(r/'raw.json',c);d=scan65_loader.load(c,lambda phase:None)
   o=copy.deepcopy(d['objects']);o[0].update(rows=np.arange(36),leaves=[0,1,2],q=np.vstack([o[i]['q'] for i in range(3)]),version=20);del o[1];del o[2]
   delivery.save_stage(r/'accepted',c,d,o,[dict(fixture_event=True)],21,'fixture-binding');js(r/'accepted/STOP.json',dict(status='PARTIAL',reason='PHASE_DEADLINE NO_U_REWARD'))
   c.update(raw_config=str(r/'raw.json'),restore_stage=str(r/'accepted'),restore_binding='fixture-binding',initial_stage=str(r/'accepted'),initial_next_version=21,seed_versions={'0':20},arms=[core.NEW],arm_policies=core.POLICIES,max_seconds=1350,absolute_deadline_jst='2026-11-03T05:35:00+09:00',archived_control_stage=str(r/'accepted'),archived_control_binding='fixture-binding',archived_control_compute_exit='fixture-not-science')
   phases=[];restored=branch_loader.load(c,phases.append);self.assertEqual(set(phases),{'readiness'});self.assertEqual(restored['next_version'],21);np.testing.assert_array_equal(restored['objects'][0]['q'],o[0]['q'])
   def bad(phase):raise RuntimeError('REAL_GUARD '+phase)
   with self.assertRaisesRegex(RuntimeError,'REAL_GUARD readiness'):branch_loader.load(c,bad)
   old=no_u_core.libraries(restored,restored['objects'],0,w.CompleteIndex(restored['objects']))[core.ORIGINAL];no_u_delivery.save_library(r/'old_library',old);c['control_replay_libraries']={'0':str(r/'old_library/LIBRARY.json')};js(r/'config.json',c)
   with patch.object(runner,'renderer',side_effect=RuntimeError('STOP_NATIVE_BOUNDARY')):
    with self.assertRaisesRegex(RuntimeError,'STOP_NATIVE_BOUNDARY'):runner.run(c,r/'config.json')
   scene=r/'run/scenes/fixture'
   for stage in ['START',core.NEW+'_FINAL']:
    out=scene/'stages'/stage;verify_checkpoint(out,sha(r/'config.json'));np.testing.assert_array_equal(np.load(out/'MEMBERSHIP.npz')['edge_id'],restored['initial_membership']['edge_id'])
   for policy in core.POLICIES:
    path=scene/'initial_catalogs'/policy/'0';self.assertTrue((path/'SCORE_COMPARISON.json').is_file());self.assertTrue((path/'SCORE_EVIDENCE.npz').is_file())
   result=json.loads((r/'run/RUN_RESULT.json').read_text());self.assertEqual(set(result['outputs']),{core.NEW});self.assertFalse(result['archived_control']['executed_in_this_unit']);self.assertEqual(result['archived_control']['stop']['status'],'PARTIAL');self.assertFalse(result['actual_pngs']);self.assertTrue(json.loads((scene/'control_replay/0.json').read_text())['complete'])

 def test_more_than_eight_requeries_best_union_and_failed_checkpoint(self):
  import balanced_runner as runner,balanced_core as core
  d,o=synthetic(11);d['representatives'].update(member_rows=np.arange(11),member_offsets=np.arange(12));saved=[];c=dict(seed_ids=[0],arm_policies=core.POLICIES)
  result,events,_,stop,_=runner.grow(d,c,core.NEW,o,20,lambda:None,lambda objects,ev,v,e:saved.append(set(objects[0]['rows'])),lambda *a:None)
  self.assertGreater(len(events),8);self.assertEqual(len(result[0]['rows']),132);self.assertTrue(all(a<=b for a,b in zip(saved,saved[1:])));self.assertEqual(stop['reason'],'NATURAL_SCOPE_EXHAUSTION');self.assertTrue(all(e['shadow_choices'] for e in events))
  bad=dict(complete=False,reason='KNOT_CAPACITY',neighbors=[],records=[dict(connectable=True)],selected=0)
  with patch.object(core,'library',return_value=bad):
   result,events,_,stop,_=runner.grow(d,c,core.NEW,o,20,lambda:None,lambda *a:None,lambda *a:None)
  self.assertFalse(events);self.assertEqual(stop['status'],'PARTIAL');np.testing.assert_array_equal(result[0]['rows'],o[0]['rows'])
  lib=core.libraries(d,o,0,w.CompleteIndex(o))[core.NEW];record=lib['records'][lib['selected']];before=copy.deepcopy(o)
  def failed_save(*a):raise RuntimeError('SAVE_FAILURE')
  with self.assertRaisesRegex(RuntimeError,'SAVE_FAILURE'):w.commit(o,0,record,20,failed_save)
  for gid in o:np.testing.assert_array_equal(o[gid]['rows'],before[gid]['rows']);np.testing.assert_array_equal(o[gid]['q'],before[gid]['q'])

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 classes=[BalancedTests,test_r6.R6Tests,test_relaxed.RelaxedTests,test_r6.WholeTests]
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in classes));raise SystemExit(0 if r.wasSuccessful() else 1)
