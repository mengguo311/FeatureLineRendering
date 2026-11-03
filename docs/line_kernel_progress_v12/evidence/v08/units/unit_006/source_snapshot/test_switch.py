import runtime_io
import copy,unittest,tempfile,json
from pathlib import Path
import numpy as np
from port_paths import Leaf
import overlap_core as oc
import switch_core as sc
from frontier_core import endpoint_index,choices
from observation_core import ObservationOracle,port_evidence
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102/units/unit_005/tests')
def data():
 leaves={};means=[];ends=[];mids=[];owner=[]
 for cid,(a,b,n) in enumerate([(0.,4.,12),(4.2,5.3,6),(5.5,6.8,8)]):
  q=np.column_stack([np.linspace(a,b,9),np.zeros((9,2))]);x=np.linspace(q[0],q[-1],n);rr=np.arange(len(means),len(means)+n);reps=np.arange(len(ends),len(ends)+3)
  for chunk in np.array_split(rr,3):ends.append([x[chunk[0]-rr[0]],x[chunk[-1]-rr[0]]]);mids.append(int(chunk[len(chunk)//2]))
  leaves[cid]=Leaf(cid,cid,rr,reps,q,True,True,np.array([[0.,b-a]]));means.extend(x);owner.extend([cid]*n)
 x=np.array(means);own=np.array(owner);t=np.tile([1.,0,0],(len(x),1));m=dict(line_kernel_id=np.arange(len(x)),edge_id=own.copy(),carrier_id=own.copy(),primitive_id=own.copy(),reason_code=np.zeros(len(x),np.uint8),provisional=np.ones(len(x),bool),auxiliary_carrier_id=np.full((len(x),2),-1))
 d=dict(leaves=leaves,original_leaves=copy.deepcopy(leaves),asset=dict(means=x,covariance=np.tile(np.eye(3),(len(x),1,1)),opacity=np.ones(len(x)),primitive_id=own),tangents=t,p=1.,next_version=20,membership=m,owner=own,representatives=dict(x=x[mids],t=t[mids],mid=np.array(mids),endpoints=np.array(ends)))
 d['ports']={(i,p):port_evidence(v,p,oc.project(x[v.rows],v.q)[0],t[v.rows]) for i,v in leaves.items() for p in (0,1)}
 return d
def state(d):return oc.initial_overlap(d,[0],ObservationOracle(d['leaves'],d['ports']))
def library(d,st,**kw):return sc.candidates(d,st,0,1,oc.SegmentIndex(d['leaves']),endpoint_index(d['leaves']),**kw)
class SwitchTests(unittest.TestCase):
 def test_two_short_donors_jointly_reach_support(self):
  d=data();lib=library(d,state(d));good=[z for z in lib['records'] if z['common']]
  self.assertEqual(len(good),1,'overlap-only cannot promote the complete endpoint relay')
  z=good[0];self.assertEqual(z['donors'],[1,2]);self.assertAlmostEqual(z['outward_support_p'],2.4);self.assertEqual(z['relation'],'endpoint_relay')
  self.assertEqual(len(z['metrics']['unsupported_connectors_p']),2);self.assertAlmostEqual(z['metrics']['supported_length_p'],6.4)
 def test_preserve_current_auxiliary_seam(self):
  d=data();st=state(d);st['curves'][0][3][1]=.02;lib=library(d,st);z=next(v for v in lib['records'] if v['common']);np.testing.assert_array_equal(np.asarray(z['q'])[:len(st['curves'][0])],st['curves'][0])
 def test_failed_short_geometry_is_not_pruned(self):
  from unittest.mock import patch
  d=data();st=state(d);original=oc.validate
  def check(data0,chain,q,guard):
   return (False,'fixture_short_path_failure',{}) if len(chain)==2 else original(data0,chain,q,guard)
  with patch.object(oc,'validate',check):lib=library(d,st)
  self.assertTrue(any(z['common'] and z['donors']==[1,2] for z in lib['records']))
  self.assertIn('fixture_short_path_failure',[z['reason'] for z in lib['records']])
 def test_combined_overflow_revokes_all_promotion(self):
  d=data();lib=library(d,state(d),max_prefixes=5);self.assertEqual(lib['status'],'NOT_RUN_OVERSIZE');self.assertEqual(lib['combined_prefixes_seen'],6);self.assertFalse(any(z['common'] for z in lib['records']));self.assertTrue(lib['unexplored_frontiers'])
 def test_relation_and_shared_first_branch_ambiguity(self):
  records=[dict(common=True,gap=.2,total_gap=.3,relay=[(1,False)],relation='overlap',history={'eligible':True}),dict(common=True,gap=.2,total_gap=.4,relay=[(1,False),(2,False)],relation='endpoint_relay',history={'eligible':True})]
  self.assertEqual(choices(sorted(records,key=sc.sort_key))['reason'],'ambiguous_gap')
 def test_reversed_frontier_and_observed_unknown(self):
  d=data();d['leaves'][0].q=d['leaves'][0].q[::-1].copy();d['original_leaves'][0].q=d['leaves'][0].q.copy()
  for p in (0,1):d['ports'][(0,p)]=port_evidence(d['leaves'][0],p,oc.project(d['asset']['means'][d['leaves'][0].rows],d['leaves'][0].q)[0],d['tangents'][d['leaves'][0].rows])
  st=state(d);lib=sc.candidates(d,st,0,0,oc.SegmentIndex(d['leaves']),endpoint_index(d['leaves']));z=next(v for v in lib['records'] if v['common']);self.assertEqual(z['chain'],[(2,True),(1,True),(0,False)])
  st['ports'][0][0]['known']=False;lib=sc.candidates(d,st,0,0,oc.SegmentIndex(d['leaves']),endpoint_index(d['leaves']));self.assertFalse(any(v['common'] for v in lib['records']))
 def test_transaction_rollback_and_atomic_relay(self):
  d=data();st=state(d);z=next(v for v in library(d,st)['records'] if v['common']);before=copy.deepcopy(st)
  def fail(_):raise OSError('fixture_save_failure')
  with self.assertRaises(OSError):sc.commit(st,0,z,fail)
  self.assertEqual(st,before);nxt=sc.commit(st,0,z,lambda _:None);self.assertEqual(nxt['used'],{0,1,2});self.assertEqual(nxt['accepted'][0],1);self.assertEqual(nxt['events'][-1]['donors'],[1,2])
 def test_cold_restore_copy_and_new_counters(self):
  from switch_io import restore,copy_control,save_stage
  from runtime_io import sha,verify_checkpoint
  d=data();st=state(d);z=next(v for v in library(d,st)['records'] if v['common']);st=sc.commit(st,0,z,lambda _:None)
  with tempfile.TemporaryDirectory(dir=ROOT) as name:
   r=Path(name);carrier=r/'carriers';carrier.write_bytes(b'fixture');c=dict(membership='fixture',carriers=str(carrier),input_files={str(carrier):sha(carrier)});m,gs=save_stage(r/'prior',c,d,st,'prior')
   c.update(initial_stage=str(r/'prior'),prior_config_sha256='prior',kernel_count=26,initial_assigned=26,initial_next_version=st['next_version'],seeds=[[0,0]])
   from frontier_delivery import serial
   phases=[];loaded,mm,gg,cp=restore(c,d,phases.append);self.assertEqual(phases,['readiness']);self.assertEqual(json.loads(json.dumps(serial(loaded))),json.loads(json.dumps(serial(st))))
   out,_=copy_control(r/'control',c,loaded,mm,gg,cp,'new');self.assertEqual(sha(r/'control/MEMBERSHIP.npz'),sha(r/'prior/MEMBERSHIP.npz'))
   nxt=sc.reopen(loaded);self.assertEqual(nxt['accepted'],{0:0});self.assertEqual(nxt['initial_event_count'],1);self.assertEqual(nxt['used'],st['used']);self.assertEqual(nxt['curves'],st['curves']);self.assertEqual(nxt['next_version'],st['next_version'])
   replay,_=save_stage(r/'new_initial',c,d,nxt,'new')
   for key in out:np.testing.assert_array_equal(out[key],replay[key])
   from switch_io import statistics,replay_deadends
   from runtime_io import nz,js
   nz(r/'m4.npz',carrier_id=d['owner']);c.update(m4_membership=str(r/'m4.npz'),external_memberships={})
   statistics(r/'new_initial',c,d,replay,gg,nxt,loaded,lambda:None)
   increments=json.loads((r/'new_initial/INCREMENTAL_STATISTICS.json').read_text())['groups'];self.assertAlmostEqual(increments[0]['support_outside_unit004_seed_p'],0.);self.assertFalse(increments[0]['new_proxy_growth_gate'])
   oldlib=oc.candidates(d,loaded,0,1,oc.SegmentIndex(d['leaves']));js(r/'visit.json',dict(seed=0,side=1,version=loaded['versions'][0],shadow=choices(oldlib['records']),**oldlib));c['deadend_visits']=[str(r/'visit.json')];c['switch']={'max_combined_prefixes':256}
   receipt,_=replay_deadends(c,d,loaded,oc.SegmentIndex(d['leaves']),lambda:None);self.assertEqual(receipt['status'],'MATCHED')

if __name__=='__main__':
 import test_overlap,test_loader_fixture
 test_overlap.ROOT=ROOT;test_loader_fixture.ROOT=ROOT
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(SwitchTests),unittest.defaultTestLoader.loadTestsFromModule(test_overlap)])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 raise SystemExit(0 if result.wasSuccessful() else 1)
