import runtime_io
import unittest,numpy as np
from overlap_core import register
from geometry_base import arc
class OverlapTests(unittest.TestCase):
 def test_registration_does_not_double_back(self):
  a=np.array([[0.,0,0],[2,0,0],[4,0,0]])
  b=np.array([[2.,0,0],[4,0,0],[6,0,0],[8,0,0]])
  q,r=register(a,b,2.)
  self.assertEqual(r['status'],'ok')
  self.assertAlmostEqual(arc(q)[-1],8.)
  self.assertTrue(np.all(np.diff(q[:,0])>0))

import copy,tempfile
from pathlib import Path
from port_paths import Leaf
from observation_core import ObservationOracle,port_evidence
from frontier_core import choices
import overlap_core as oc
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102/units/unit_004/tests')
def data(third=True,isolated=False):
 leaves={};means=[];repends=[];mids=[];owner=[];nextrow=0
 for cid,(a,b,n) in enumerate([(0.,4.,12),(20.,24.,12),(40.,44.,12),(60.,64.,12)] if isolated else [(0.,4.,12),(2.,8.,18)]+([(6.,10.5,18)] if third else [])):
  q=np.column_stack([np.linspace(a,b,int((b-a)*2)+1),np.zeros((int((b-a)*2)+1,2))]);x=np.linspace(q[0],q[-1],n);rr=np.arange(nextrow,nextrow+n);reps=np.arange(len(repends),len(repends)+3);nextrow+=n
  for chunk in np.array_split(rr,3):repends.append([x[chunk[0]-rr[0]],x[chunk[-1]-rr[0]]]);mids.append(int(chunk[len(chunk)//2]))
  leaves[cid]=Leaf(cid,10+cid,rr,reps,q,True,True,np.array([[0.,b-a]]));means.extend(x);owner.extend([cid]*n)
 x=np.asarray(means);t=np.tile([1.,0,0],(len(x),1));own=np.array(owner);m=dict(line_kernel_id=np.arange(len(x)),edge_id=own.copy(),carrier_id=own.copy(),primitive_id=own.copy(),reason_code=np.zeros(len(x),np.uint8),provisional=np.ones(len(x),bool),auxiliary_carrier_id=np.tile([1,99],(len(x),1)))
 d=dict(leaves=leaves,original_leaves=copy.deepcopy(leaves),asset=dict(means=x,covariance=np.tile(np.eye(3),(len(x),1,1)),opacity=np.ones(len(x)),primitive_id=own.copy()),p=1.,next_version=20,tangents=t,membership=m,owner=own,representatives=dict(x=x[mids],t=t[mids],mid=np.array(mids),endpoints=np.asarray(repends)))
 d['ports']={}
 for cid,leaf in leaves.items():
  ss=oc.project(x[leaf.rows],leaf.q)[0]
  for p in (0,1):d['ports'][(cid,p)]=port_evidence(leaf,p,ss,t[leaf.rows])
 return d

def state(d):return oc.initial_overlap(d,[0],ObservationOracle(d['leaves'],d['ports']))
class PipelineTests(unittest.TestCase):
 def test_repeated_growth_and_left_reverse(self):
  d=data();st=state(d);idx=oc.SegmentIndex(d['leaves']);lib=oc.candidates(d,st,0,1,idx);sel=choices(lib['records']);self.assertEqual(sel['BASE'],sel['HISTORY']);z=lib['records'][sel['BASE']];self.assertEqual(z['donor'],1)
  self.assertAlmostEqual(z['metrics']['supported_length_p'],8.);self.assertGreaterEqual(z['outward_support_p'],2)
  nxt=oc.commit(st,0,z,lambda _:None);lib2=oc.candidates(d,nxt,0,1,idx);z2=lib2['records'][choices(lib2['records'])['BASE']];self.assertEqual(z2['donor'],2)
  final=oc.commit(nxt,0,z2,lambda _:None);self.assertEqual(final['accepted'][0],2);self.assertEqual(final['used'],{0,1,2});self.assertAlmostEqual(final['metrics'][0]['supported_length_p'],10.5)
  d=data(False);d['leaves'][0].q=d['leaves'][0].q[::-1].copy();d['original_leaves'][0].q=d['leaves'][0].q.copy()
  for p in (0,1):d['ports'][(0,p)]=port_evidence(d['leaves'][0],p,oc.project(d['asset']['means'][:12],d['leaves'][0].q)[0],d['tangents'][:12])
  st=state(d);lib=oc.candidates(d,st,0,0,oc.SegmentIndex(d['leaves']));z=lib['records'][choices(lib['records'])['BASE']];self.assertEqual(z['chain'],[(1,True),(0,False)]);self.assertGreater(z['q'][0][0],z['q'][-1][0])
 def test_finite_domain_and_whole_member_rejection(self):
  d=data(False);d['asset']['means'][0,0]=-.1;lib=oc.candidates(d,state(d),0,1,oc.SegmentIndex(d['leaves']));self.assertFalse(any(z['common'] for z in lib['records']));self.assertIn('kernel_outside_finite_domain',[z['reason'] for z in lib['records']])
  d=data(False);d['asset']['means'][13,1]=1.1;lib=oc.candidates(d,state(d),0,1,oc.SegmentIndex(d['leaves']));self.assertIn('whole_member_residual_tangent',[z['reason'] for z in lib['records']])
 def test_failed_save_is_exact_rollback(self):
  d=data(False);st=state(d);lib=oc.candidates(d,st,0,1,oc.SegmentIndex(d['leaves']));z=lib['records'][choices(lib['records'])['BASE']];before=copy.deepcopy(st)
  def fail(_):raise OSError('bounded disk fixture')
  with self.assertRaises(OSError):oc.commit(st,0,z,fail)
  self.assertEqual(st,before)
 def test_complete_competitors_and_capacity(self):
  d=data(False);st=state(d);leaf=copy.deepcopy(d['leaves'][1]);leaf.cid=7;d['leaves'][7]=leaf;d['original_leaves'][7]=copy.deepcopy(leaf)
  lib=oc.candidates(d,st,0,1,oc.SegmentIndex(d['leaves']));self.assertEqual(lib['proposals_seen'],4);self.assertEqual(choices(lib['records'])['reason'],'ambiguous_gap')
  limited=oc.candidates(d,st,0,1,oc.SegmentIndex(d['leaves']),max_proposals=3);self.assertEqual(limited['status'],'NOT_RUN_OVERSIZE');self.assertFalse(any(z['common'] for z in limited['records']));self.assertEqual(len(limited['records']),4)
 def test_reversed_registration_and_guard_rejection(self):
  a=np.array([[0.,0,0],[4,0,0]]);b=np.array([[8.,0,0],[2,0,0]])
  q,r=oc.register(a,b,4);self.assertIsNone(q);self.assertIn(r['status'],['overlap_tangent','overlap_distance']);self.assertGreater(max(r['angles_deg']),30)
  b=np.array([[2.,1.1,0],[8,1.1,0]]);q,r=oc.register(a,b,2);self.assertIsNone(q);self.assertEqual(r['status'],'overlap_distance')
  q,r=oc.register(a,np.array([[4.,0,0],[8,0,0]]),0);self.assertIsNone(q)
 def test_monotonicity_parallel_branch_guards(self):
  d=data(False);q=np.array([[0.,0,0],[8,0,0]])
  d['original_leaves'][1].q=np.array([[2.,0,0],[6,0,0],[4,0,0],[8,0,0]])
  self.assertEqual(oc.validate(d,[(0,False),(1,False)],q)[1],'leaf_nonmonotone')
  d=data(False);d['leaves'][1].q[:,1]=.6;d['original_leaves'][1].q[:,1]=.6
  self.assertEqual(oc.validate(d,[(0,False),(1,False)],q)[1],'parallel')
  d=data(False);rr=np.arange(9);d['leaves'][0].reps=rr[:3];d['leaves'][1].reps=rr[3:]
  positions=np.array([[r,0,0] for r in (1.,2.,3.)]+[[0,r,0] for r in (1.,2.,3.)]+[[0,0,r] for r in (1.,2.,3.)]);d['representatives']['x']=positions;d['representatives']['t']=positions/np.linalg.norm(positions,axis=1)[:,None]
  self.assertEqual(oc.validate(d,[(0,False),(1,False)],q)[1],'branch')
 def test_cold_membership_aux_unknown_and_checkpoint(self):
  from overlap_delivery import save_stage
  from runtime_io import sha,verify_checkpoint
  d=data(False);d['membership']['edge_id'][12:]=-1;st=state(d);lib=oc.candidates(d,st,0,1,oc.SegmentIndex(d['leaves']));z=lib['records'][choices(lib['records'])['BASE']]
  with tempfile.TemporaryDirectory(dir=ROOT) as name:
   r=Path(name);f=r/'carrier';f.write_bytes(b'fixture');c=dict(membership='fixture',carriers=str(f),input_files={str(f):sha(f)});box={}
   def save(s):box['m'],box['g']=save_stage(r/'stage',c,d,s,'fixture')
   after=oc.commit(st,0,z,save);verify_checkpoint(r/'stage','fixture');self.assertEqual(box['m']['edge_id'].tolist(),[0]*30);self.assertEqual(after['next_version'],22);self.assertEqual(st['used'],{0})
   np.testing.assert_array_equal(box['m']['auxiliary_carrier_id'],d['membership']['auxiliary_carrier_id']);self.assertEqual(box['m']['auxiliary_composite_id'].tolist(),[[99,-1]]*30)
   from overlap_delivery import statistics_overlap
   from runtime_io import nz
   import json
   nz(r/'m4.npz',carrier_id=d['owner']);c.update(m4_membership=str(r/'m4.npz'),external_memberships={})
   statistics_overlap(r/'stage',c,d,box['m'],box['g'],after,lambda:None)
   stats=json.loads((r/'stage/GROUP_STATISTICS.json').read_text())['groups'][0];self.assertAlmostEqual(stats['support_outside_seed_domain_p'],4.);self.assertEqual(len(stats['M4_contributions']),2)
   self.assertAlmostEqual(stats['internal_fill_or_pooling_proxy_p'],0.)
   bad=copy.deepcopy(after);bad['metrics'][0]['seedlets']=2;mm,_=save_stage(r/'dormant',c,d,bad,'fixture');self.assertTrue(np.all(mm['edge_id'][12:]<0))
 def test_real_loader_contract_without_replacing_loader(self):
  import test_loader_fixture
  test_loader_fixture.ROOT=ROOT
  result=unittest.TestResult();test_loader_fixture.Fixture('test_real_loader_and_checkpoint').run(result)
  self.assertEqual(result.errors,[]);self.assertEqual(result.failures,[])
 def test_loader_phase_resource_exception_propagates(self):
  import frontier_loader
  def guard(phase):self.assertEqual(phase,'readiness');raise TimeoutError('fixture resource phase')
  with self.assertRaisesRegex(TimeoutError,'fixture resource phase'):frontier_loader.load(dict(input_files={},helper_files={},source_files={}),guard)

 def test_observation_bank_and_eight_visit_replay(self):
  from observation_core import observations
  from observation_bank import export_bank
  from observation_relay import observed_candidates
  from frontier_loader import local_validator
  from frontier_core import initial,endpoint_index
  from overlap_replay import replay
  from runtime_io import sha,js,verify_checkpoint
  raw=data(isolated=True);d=observations(raw,lambda:None);seedids=list(range(4));st=initial(seedids,d['next_version']);idx=endpoint_index(d['leaves']);oldidx=endpoint_index(raw['leaves']);oracle=ObservationOracle(d['leaves'],d['ports'],d['representatives']['x'],d['representatives']['t'],local_validator(d,1.))
  with tempfile.TemporaryDirectory(dir=ROOT) as name:
   r=Path(name);source=r/'original';source.write_bytes(b'fixture');c=dict(carriers=str(source),input_files={str(source):sha(source)},prior_config_sha256='old-fixture',prior_observation_bank=str(r/'old'),prior_observed_visits_root=str(r/'visits'),seeds=[[i,10+i] for i in seedids])
   export_bank(r/'old',c,d,'old-fixture');export_bank(r/'new',c,d,'new-fixture')
   for i in seedids:
    for side in (0,1):
     lib=observed_candidates(d,st,i,side,idx,oracle,lambda:None,256,3,oldidx);js(r/'visits'/f'{2*i+side:04d}.json',dict(seed=i,side=side,version=st['versions'][i],shadow=choices(lib['records']),**lib))
   receipt,contexts=replay(c,raw,d,r/'new',lambda:None);self.assertEqual(receipt['status'],'MATCHED');self.assertEqual(len(receipt['visits']),8)
 def test_history_abstains_on_short_tail_and_no_pool_growth(self):
  d=data(False);d['leaves'][1].intervals=np.array([[0.,2.]])
  lib=oc.candidates(d,state(d),0,1,oc.SegmentIndex(d['leaves']));self.assertFalse(any(z['common'] for z in lib['records']));self.assertIn('outward_support',[z['reason'] for z in lib['records']])
  h=oc.history(np.array([[0.,0,0],[4,0,0]]),np.array([[4.,0,0],[5,0,0]]),0.);self.assertFalse(h['eligible'])

if __name__=='__main__':unittest.main(verbosity=2)
