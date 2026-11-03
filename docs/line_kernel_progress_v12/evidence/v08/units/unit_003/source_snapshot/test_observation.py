import runtime_io
import unittest,numpy as np
from port_paths import Leaf,PathOracle
from observation_core import clipped_leaf,port_evidence,ObservationOracle

def leaf():
 return Leaf(1,7,np.arange(6),np.arange(3),np.array([[0.,0,0],[2,0,0],[4,0,0]]),True,True,np.array([[.5,1.5],[2.5,3.5]]))

class ObservationTests(unittest.TestCase):
 def test_support_clipping_retains_all_members(self):
  old=leaf();new,receipt=clipped_leaf(old)
  np.testing.assert_allclose(new.q,[[.5,0,0],[2,0,0],[3.5,0,0]])
  np.testing.assert_array_equal(new.rows,old.rows);np.testing.assert_allclose(new.intervals,[[0,1],[2,3]])
  np.testing.assert_allclose(old.q,[[0,0,0],[2,0,0],[4,0,0]]);self.assertEqual(receipt['status'],'ready')
 def test_bounds_reject_without_clamping_real_excess(self):
  old=leaf();old.intervals=np.array([[-.1,4.]])
  new,r=clipped_leaf(old);self.assertFalse(new.valid);self.assertEqual(r['status'],'support_out_of_domain')
 def test_axis_reversal_and_bin_balance(self):
  q=leaf();q.q=np.array([[0.,0,0],[4.,0,0]]);ss=np.array([0.,.1,.2,1.1,1.2,3.9]);tt=np.tile([1.,0,0],(6,1));tt[1::2]*=-1
  a=port_evidence(q,0,ss,tt);self.assertTrue(a['known']);np.testing.assert_allclose(a['axis'],[-1,0,0]);self.assertEqual(a['bins'],[0,0,0,1,1])
  tt[3:5]=[0,1,0];b=port_evidence(q,0,ss,tt);self.assertFalse(b['known']);self.assertEqual(b['reason'],'weak_axis')
 def test_insufficient_and_sign_unknown(self):
  q=leaf();ss=np.arange(6,dtype=float);tt=np.tile([0.,1,0],(6,1));self.assertEqual(port_evidence(q,0,ss,tt)['reason'],'orthogonal_sign')
  self.assertEqual(port_evidence(q,1,ss,np.tile([1.,0,0],(6,1)))['known'],True)
  self.assertEqual(port_evidence(q,0,np.ones(6)*3,np.tile([1.,0,0],(6,1)))['reason'],'insufficient_derivatives')
 def test_oracle_consistent_port_dispatch(self):
  a=leaf();a.q=np.array([[0.,0,0],[4.,0,0]]);a.intervals=np.array([[0.,4.]])
  b=Leaf(2,0,np.arange(6,12),np.arange(3,6),np.array([[4.2,0,0],[8.2,0,0]]),True,True,np.array([[0.,4.]]))
  ports={(1,0):dict(known=True,axis=[-1.,0,0]),(1,1):dict(known=True,axis=[0.,1,0]),(2,0):dict(known=True,axis=[-1.,0,0]),(2,1):dict(known=True,axis=[1.,0,0])}
  self.assertTrue(PathOracle({1:a,2:b})([(1,False),(2,False)])[0])
  self.assertEqual(ObservationOracle({1:a,2:b},ports)([(1,False),(2,False)])[1],'observed_endpoint_tangent')
 def test_old_endpoint_veto_is_not_reapplied(self):
  a=leaf();a.q=np.array([[0.,0,0],[4.,0,0]]);a.intervals=np.array([[0.,4.]])
  angle=np.deg2rad(17.5);axis=np.array([np.cos(angle),np.sin(angle),0.]);v=np.array([np.cos(2*angle),np.sin(2*angle),0.]);start=a.q[-1]+axis
  b=Leaf(2,0,np.arange(6,12),np.arange(3,6),np.array([start,start+4*v]),True,True,np.array([[0.,4.]]))
  ports={(i,p):dict(known=True,axis=(axis*(1 if p else -1)).tolist()) for i in [1,2] for p in [0,1]}
  self.assertEqual(PathOracle({1:a,2:b})([(1,False),(2,False)])[1],'endpoint_tangent')
  self.assertTrue(ObservationOracle({1:a,2:b},ports)([(1,False),(2,False)])[0])
 def test_complete_pipeline_and_cold_observation_checkpoint(self):
  from test_relay import data
  from observation_core import observations
  from observation_relay import observed_candidates
  from frontier_core import initial,endpoint_index,choices
  from relay_core import commit_relay
  from observation_bank import export_bank
  from observation_delivery import save_stage
  from runtime_io import Path,sha,verify_checkpoint
  import tempfile,copy
  raw=data();raw['tangents']=np.tile([1.,0,0],(12,1));raw['owner']=np.repeat([0,1,2],[6,3,3]);raw['next_version']=10
  raw['membership']=dict(line_kernel_id=np.arange(12),edge_id=raw['owner'].copy(),carrier_id=raw['owner'].copy(),primitive_id=raw['owner'].copy(),reason_code=np.zeros(12,np.uint8),provisional=np.ones(12,bool),auxiliary_carrier_id=np.tile([2,9],(12,1)))
  d=observations(raw,lambda:None);state=initial([0],10);oracle=ObservationOracle(d['leaves'],d['ports']);idx=endpoint_index(d['leaves'])
  lib=observed_candidates(d,state,0,1,idx,oracle,lambda:None,old_index=endpoint_index(raw['leaves']));choice=choices(lib['records']);z=lib['records'][choice['BASE']]
  self.assertEqual(z['donors'],[1,2]);self.assertEqual(choice['BASE'],choice['HISTORY']);self.assertTrue(lib['queries'][0]['original_endpoint_neighbors'])
  with tempfile.TemporaryDirectory(dir='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102/units/unit_003/tests') as name:
   r=Path(name);source=r/'source';source.write_bytes(b'fixture');c=dict(membership='fixture',carriers=str(source),input_files={str(source):sha(source)},observation_bank=str(r/'bank'))
   export_bank(r/'bank',c,d,'fixture');verify_checkpoint(r/'bank','fixture');box={}
   def save(trial):box['m'],_=save_stage(r/'accepted',c,d,trial,oracle,'fixture')
   accepted=commit_relay(state,0,z,save);verify_checkpoint(r/'accepted','fixture');self.assertEqual(box['m']['edge_id'].tolist(),[0]*12)
   self.assertEqual(accepted['used'],{0,1,2});self.assertEqual(state['used'],{0})
   old=np.load(r/'accepted/ORIGINAL_LEAF_CARRIERS.npz',allow_pickle=False);new=np.load(r/'accepted/CARRIERS.npz',allow_pickle=False);np.testing.assert_array_equal(old['carrier_id'],new['carrier_id'])
  d['ports'][(0,1)]=dict(known=False,reason='fixture_unknown');blocked=observed_candidates(d,state,0,1,idx,oracle,lambda:None)
  self.assertFalse(any(x['common'] for x in blocked['records']))

if __name__=='__main__':unittest.main(verbosity=2)
