"""Small real loader/checkpoint fixture, never original full assets or rendering."""
from runtime_io import *
import unittest,tempfile,pickle,types,sys,copy
from unittest.mock import patch
from frontier_loader import Carrier
from whole_loader import load
from whole_delivery import save_stage,mapping
import whole_runner
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_best_fragment_growth_v09_20261102/units/unit_001/tests')

def fixture(r):
 n=36;xx=np.c_[np.r_[np.linspace(0,4,12),np.linspace(20,24,12),np.linspace(40,44,12)],np.zeros((n,2))];owner=np.repeat(np.arange(3),12);rr=np.arange(n);carriers={};qs=[]
 asset=dict(means=xx,covariance=np.tile(np.eye(3)*.04,(n,1,1)),opacity=np.ones(n),primitive_id=owner.copy(),internal_piece_id=rr.copy(),arc_t=np.tile(np.linspace(0,1,12),3))
 m=dict(line_kernel_id=rr,edge_id=owner.copy(),carrier_id=owner.copy(),primitive_id=owner.copy(),reason_code=np.zeros(n,np.uint8),provisional=np.ones(n,bool))
 for i in range(3):
  rows=rr[i*12:(i+1)*12];q=xx[rows[[0,-1]]];qs.append(q);carriers[i]=Carrier(i,np.array([i]),rows,q,'line',True,True,(i,),10+i)
 rep=dict(x=xx[[6,18,30]],t=np.tile([1.,0,0],(3,1)),mid=np.array([6,18,30]),endpoints=np.array(qs),member_rows=rr,member_offsets=np.arange(4)*12,kernel_rep=owner)
 nz(r/'gaussians.npz',**asset);nz(r/'membership.npz',**m);nz(r/'representatives.npz',**rep)
 control=np.repeat(xx,2,axis=0);control[1::2,0]+=1;indices=np.arange(2*n).reshape(n,2)
 nz(r/'controls.npz',control=control,control_index=indices,piece_control_indices=indices,parent_control_offsets=np.c_[np.arange(3)*24,np.arange(1,4)*24],basis=np.tile([1.,0],(n,1)),derivative_basis=np.tile([-1.,1],(n,1)),primitive_id=owner,internal_piece_id=rr,arc_t=asset['arc_t'])
 nz(r/'carriers.npz',carrier_id=np.arange(3),version=np.arange(10,13),valid=np.ones(3,bool),baseline=np.ones(3,bool),kind=np.array(['line']*3),knots=np.concatenate(qs),knot_offsets=np.arange(4)*2,rows=rr,row_offsets=np.arange(4)*12,seedlets=np.arange(3),seed_offsets=np.arange(4),origins=np.arange(3),origin_offsets=np.arange(4),supported_intervals=np.tile([0.,4],(3,1)),interval_offsets=np.arange(4))
 mod=types.ModuleType('core');mod.Carrier=Carrier;sys.modules['core']=mod;oldmodule=Carrier.__module__;Carrier.__module__='core'
 try:(r/'STATE.pkl').write_bytes(pickle.dumps(dict(carriers=carriers,aux={},next_version=20)))
 finally:Carrier.__module__=oldmodule;del sys.modules['core']
 js(r/'decision.json',{'fixture':True});js(r/'old_config.json',dict(decision_path=str(r/'decision.json'),decision_sha256=sha(r/'decision.json')))
 js(r/'CHECKPOINT.json',dict(complete=True,stage='M5_STATE',config_binding=sha(r/'old_config.json'),decision_sha256=sha(r/'decision.json'),files={'STATE.pkl':sha(r/'STATE.pkl')}))
 stage=r/'prior';nz(stage/'MEMBERSHIP.npz',**m);nz(stage/'CARRIERS.npz',carrier_id=np.arange(3),version=np.arange(10,13),knots=np.concatenate(qs),knot_offsets=np.arange(4)*2)
 js(stage/'GROWTH_STATE.json',dict(curves={str(i):qs[i].tolist() for i in range(3)},versions={str(i):10+i for i in range(3)},events=[],next_version=20));checkpoint(stage,['MEMBERSHIP.npz','CARRIERS.npz','GROWTH_STATE.json'],'prior','COMPLETE')
 c=dict(unit_root=str(r/'run'),runtime_root=str(r),unit=str(r/'run'),runtime=str(r),max_seconds=1800,absolute_deadline_jst='2026-11-02T15:38:00+09:00',source_files={},helper_files={},input_files={},decision_path=str(r/'decision.json'),decision_sha256=sha(r/'decision.json'),predecessor_checkpoint=str(r/'CHECKPOINT.json'),predecessor_config=str(r/'old_config.json'),state=str(r/'STATE.pkl'),kernel_count=n,carrier_count=3,knot_count=6,next_version=20,p=1.,initial_stage=str(stage),prior_config_sha256='prior',initial_assigned=n,initial_next_version=20,seed_ids=[0],scene='fixture',control_identity={'expected':{'controls':2*n,'pieces':n,'parents':3}},source_snapshot_root='bounded_fixture',views=['a','b'])
 for key in ['gaussians','membership','representatives','controls','carriers']:c[key]=str(r/(key+'.npz'));c['input_files'][c[key]]=sha(c[key])
 js(r/'cameras.json',dict(fixture=[{'view':'a'},{'view':'b'}]));c['cameras']=str(r/'cameras.json');return c

class LoaderTests(unittest.TestCase):
 def test_real_phase_guard_and_complete_current_group_loading(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=fixture(r);ph=[];d=load(c,ph.append);self.assertTrue(ph);self.assertEqual(set(ph),{'readiness'});self.assertEqual(len(d['objects']),3)
   def fail(phase):raise RuntimeError('RESOURCE '+phase)
   with self.assertRaisesRegex(RuntimeError,'RESOURCE readiness'):load(c,fail)
   m=save_stage(r/'saved',c,d,d['objects'],[],20,'fixture');np.testing.assert_array_equal(m['edge_id'],d['initial_membership']['edge_id']);verify_checkpoint(r/'saved','fixture')
 def test_real_runner_two_full_maps_saved_before_renderer(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=fixture(r);js(r/'config.json',c)
   with patch.object(whole_runner,'renderer',side_effect=RuntimeError('STOP_BEFORE_RENDER')):
    with self.assertRaisesRegex(RuntimeError,'STOP_BEFORE_RENDER'):whole_runner.run(c,r/'config.json')
   result=json.loads((r/'run/RUN_RESULT.json').read_text());self.assertEqual(result['actual_pngs'],[])
   for arm in ['LOCAL','WHOLE']:self.assertIn(arm+'_FINAL_MAPPING',result['completed']);self.assertEqual(result['outputs'][arm]['accepted'],0)
