import runtime_io
from runtime_io import *
import unittest,sys,types,pickle
from frontier_loader import Carrier,load
from frontier_core import initial
from frontier_delivery import save_stage
from port_paths import PathOracle
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102/units/unit_003/tests')
class Fixture(unittest.TestCase):
 def test_real_loader_and_checkpoint(self):
  import tempfile
  with tempfile.TemporaryDirectory(dir=ROOT) as name:
   r=Path(name);q=np.array([[0.,0,0],[4.,0,0]]);rows=np.arange(6);reps=np.arange(3);carrier=Carrier(0,reps,rows,q,'line',True,True,(0,),5)
   mod=types.ModuleType('core');mod.Carrier=Carrier;sys.modules['core']=mod;oldmodule=Carrier.__module__;Carrier.__module__='core'
   try:(r/'STATE.pkl').write_bytes(pickle.dumps(dict(carriers={0:carrier},aux={},next_version=6)))
   finally:Carrier.__module__=oldmodule;del sys.modules['core']
   nz(r/'carriers.npz',carrier_id=np.array([0]),version=np.array([5]),valid=np.array([True]),baseline=np.array([True]),kind=np.array(['line']),rows=rows,row_offsets=np.array([0,6]),seedlets=reps,seed_offsets=np.array([0,3]),origins=np.array([0]),origin_offsets=np.array([0,1]),knots=q,knot_offsets=np.array([0,2]),supported_intervals=np.array([[0.,4.]]),interval_offsets=np.array([0,1]))
   nz(r/'membership.npz',line_kernel_id=rows,carrier_id=np.zeros(6,int),edge_id=np.zeros(6,int),primitive_id=np.zeros(6,int),reason_code=np.zeros(6,np.uint8),provisional=np.ones(6,bool))
   means=np.linspace(q[0],q[1],6);nz(r/'gaussians.npz',means=means,covariance=np.tile(np.eye(3),(6,1,1)),opacity=np.ones(6),primitive_id=np.zeros(6,int))
   nz(r/'representatives.npz',member_rows=rows,member_offsets=np.array([0,2,4,6]),kernel_rep=np.repeat(reps,2),x=means[[0,2,4]],t=np.tile([1.,0,0],(3,1)),mid=np.array([0,2,4]),endpoints=means.reshape(3,2,3))
   nz(r/'controls.npz',control=np.array([[0.,0,0],[1.,0,0]]),control_index=np.tile([0,1],(6,1)),derivative_basis=np.tile([-1.,1],(6,1)))
   js(r/'DECISION.json',{'fixture':True});decision=sha(r/'DECISION.json');js(r/'old_config.json',dict(decision_path=str(r/'DECISION.json'),decision_sha256=decision))
   js(r/'CHECKPOINT.json',dict(complete=True,stage='M5_STATE',config_binding=sha(r/'old_config.json'),decision_sha256=decision,files={'STATE.pkl':sha(r/'STATE.pkl')}))
   c=dict(input_files={},helper_files={},source_files={},decision_path=str(r/'DECISION.json'),decision_sha256=decision,predecessor_checkpoint=str(r/'CHECKPOINT.json'),predecessor_config=str(r/'old_config.json'),state=str(r/'STATE.pkl'),kernel_count=6,carrier_count=1,knot_count=2,next_version=6,p=1.,scene='fixture')
   for k in ['carriers','membership','gaussians','representatives','controls']:c[k]=str(r/(k+'.npz'));c['input_files'][c[k]]=sha(c[k])
   phases=[];d=load(c,phases.append);self.assertEqual(phases,['readiness','readiness']);self.assertEqual(len(d['owner']),6)
   out=r/'stage';cold,gs=save_stage(out,c,d,initial([0],6),PathOracle(d['leaves']),decision);self.assertEqual(cold['edge_id'].tolist(),[0]*6)
   with self.assertRaises(FileExistsError):save_stage(out,c,d,initial([0],6),PathOracle(d['leaves']),decision)
   # Dormant complete leaves activate only after composite support meets gate.
   import copy
   from port_paths import Leaf
   d2=copy.deepcopy(d);q2=q+np.array([4.2,0,0]);d2['leaves'][1]=Leaf(1,0,np.arange(6,12),np.arange(3,6),q2,True,False,np.array([[0.,4.]]))
   for key,value in list(d2['membership'].items()):d2['membership'][key]=np.concatenate([value,value])
   d2['membership']['edge_id'][6:]=-1;d2['membership']['line_kernel_id']=np.arange(12)
   state=initial([0],6);state['chains'][0]=[(0,False),(1,False)]
   cold,_=save_stage(r/'activated',c,d2,state,PathOracle(d2['leaves']),decision)
   self.assertEqual(cold['edge_id'].tolist(),[0]*12)

if __name__=='__main__':unittest.main(verbosity=2)
