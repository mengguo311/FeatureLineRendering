"""Small, isolated vertical tests; never opens real scene assets or renders."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='2'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import unittest, tempfile, pathlib, sys
import numpy as np
import free_core as f
from free_io import load,sha,save_stage,cold_stage

class FreeTests(unittest.TestCase):
 def data(self,n=30):
  x=np.c_[np.linspace(0,10,n),np.zeros((n,2))];t=np.tile([1.,0,0],(n,1));return x,t
 def test_ambiguity(self):
  x,t=self.data();m={1:np.array([[0.,.1,0],[10,.1,0]]),2:np.array([[0.,-.1,0],[10,-.1,0]])}
  a=f.assign(x,t,np.ones(len(x),bool),m);self.assertTrue(np.all(a['edge_id']==-1));self.assertTrue(np.all(a['alternatives']>=0))
 def test_same_model_segments_not_competitors(self):
  x,t=self.data();q=np.c_[np.arange(11.),np.zeros((11,2))];a=f.assign(x,t,np.ones(len(x),bool),{7:q});self.assertTrue(np.all(a['edge_id']==7))
 def test_free_split_and_revoke(self):
  x=np.array([[0.,0,0],[0,3,0],[20,20,0]]);t=np.tile([1.,0,0],(3,1));m={5:np.array([[-1.,0,0],[1,0,0]]),6:np.array([[-1.,3,0],[1,3,0]])};a=f.assign(x,t,np.ones(3,bool),m);self.assertEqual(a['edge_id'].tolist(),[5,6,-1])
 def test_complete_competitors(self):
  x=np.array([[0.,0,0]]);t=np.array([[1.,0,0]]);m={i:np.array([[-1.,.01*i,0],[1,.01*i,0]]) for i in range(80)};a=f.assign(x,t,np.ones(1,bool),m);self.assertEqual(a['eligible_models'][0],80);self.assertEqual(a['edge_id'][0],-1)
 def test_finite_distance(self):
  x=np.array([[3.,0,0]]);t=np.array([[1.,0,0]]);a=f.assign(x,t,np.ones(1,bool),{0:np.array([[0.,0,0],[1,0,0]])});self.assertEqual(a['edge_id'][0],-1)
 def test_gap_split_and_death(self):
  x=np.c_[np.r_[np.linspace(0,6,36),np.linspace(10,16,36),[20.,20.1]],np.zeros((74,2))];t=np.tile([1.,0,0],(74,1));q=np.c_[np.arange(22.),np.zeros((22,2))];a=f.assign(x,t,np.ones(74,bool),{0:q});m,b,events,nxt=f.validate_support(x,np.full(74,.3),{0:q},a,1);self.assertEqual(len(m),2);self.assertTrue(np.all(b['edge_id'][-2:]==-1));self.assertNotEqual(b['edge_id'][0],b['edge_id'][40])
 def test_split_coordinates_match_child(self):
  x=np.c_[np.r_[np.linspace(0,6,36),np.linspace(10,16,36)],np.zeros((72,2))];t=np.tile([1.,0,0],(72,1));q=np.c_[np.arange(18.),np.zeros((18,2))];a=f.assign(x,t,np.ones(72,bool),{0:q});m,b,e,n=f.validate_support(x,np.full(72,.3),{0:q},a,1)
  for mid,child in m.items():
   rr=np.flatnonzero(b['edge_id']==mid);dist,ss,j,u=f.project(x[rr],child);np.testing.assert_array_equal(b['segment'][rr],j);np.testing.assert_allclose(b['u'][rr],u)
 def test_short_dies(self):
  x,t=self.data(10);a=f.assign(x,t,np.ones(10,bool),{0:np.array([[0.,0,0],[10,0,0]])});m,b,e,n=f.validate_support(x,np.full(10,.3),{0:np.array([[0.,0,0],[10,0,0]])},a,1);self.assertFalse(m);self.assertTrue(np.all(b['edge_id']==-1))
 def test_geometry_turn_and_contact(self):
  self.assertFalse(f.geometry_ok(np.array([[0.,0,0],[1,0,0],[1,1,0]]))[0]);self.assertTrue(f.geometry_ok(np.c_[np.arange(12.),np.zeros((12,2))])[0])
 def test_update_movement(self):
  x,t=self.data(80);x[:,1]=.2;q=np.c_[np.arange(11.),np.zeros((11,2))];new=f.irls_update(x,q);self.assertLessEqual(np.max(np.linalg.norm(new-q,axis=1)),.50000001);self.assertGreater(np.mean(new[:,1]),0)
 def test_trace_and_small_cycle(self):
  x,t=self.data(96);rows=np.arange(len(x));field=f.Field(x,t,rows);models,nxt,log=f.discover(field,{},0,3);self.assertTrue(models);self.assertLessEqual(max(map(len,models.values())),129)
  a=f.assign(x,t,np.ones(len(x),bool),models);m,a,e,nxt=f.validate_support(x,np.full(len(x),.3),models,a,nxt);self.assertTrue(m)
  updated,e=f.update_models(x,np.full(len(x),.3),m,a,field);b=f.assign(x,t,np.ones(len(x),bool),updated);self.assertEqual(len(b['edge_id']),96)
 def test_guard_during_assignment(self):
  x,t=self.data()
  def guard():raise TimeoutError('science')
  with self.assertRaisesRegex(TimeoutError,'science'):f.assign(x,t,np.ones(len(x),bool),{1:np.array([[0.,0,0],[10,0,0]])},guard)
 def test_unknown_competes_with_cost_near_one(self):
  x=np.array([[0.,.99,0]]);t=np.array([[1.,0,0]]);a=f.assign(x,t,np.ones(1,bool),{1:np.array([[-1.,0,0],[1,0,0]])});self.assertEqual(a['edge_id'][0],-1)
 def test_group_diagnostics_real_arrays(self):
  from free_delivery import groups
  x,t=self.data(96);q=np.c_[np.arange(11.),np.zeros((11,2))];a=f.assign(x,t,np.ones(96,bool),{4:q});d=dict(x=x,half=np.full(96,.3),asset=dict(means=x,primitive_id=np.repeat(np.arange(3),32)));gg=groups(d,{4:q},a,np.repeat(np.arange(3),32),lambda:None);self.assertEqual(gg[0]['kernels'],96)
 def test_runner_actual_loader_four_stages_no_render(self):
  import runner
  from unittest.mock import patch
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   p=pathlib.Path(td);c=self.fixture(p);dec=p/'DECISION.json';dec.write_text('{}');c.update(unit_root=str(p/'output'),runtime_root=str(p),scene='fixture',max_seconds=1800,absolute_deadline_jst='2026-11-01T19:38:00+09:00',decision_path=str(dec),decision_sha256=sha(dec));(p/'output').mkdir()
   # Only render/diagnostics replaced: actual load, trace, assignment, update and cold checkpoints execute on30 rows.
   with patch.object(runner,'deliver',return_value={'fixture_delivery_not_rendered':True}):rc=runner.run(c,'fixture')
   self.assertEqual(rc,0)
   import json
   result=json.loads((p/'output'/'RUN_RESULT.json').read_text());self.assertEqual(len(result['completed_stages']),4);self.assertFalse(result['errors'])
 def fixture(self,tmp):
  x,t=self.data();n=len(x);a=dict(means=x,covariance=np.tile(np.eye(3)*.01,(n,1,1)),opacity=np.ones(n),colors=np.zeros((n,3)),primitive_id=np.arange(n,dtype=np.int32),internal_piece_id=np.arange(n,dtype=np.int32),arc_t=np.arange(n,dtype=float));ct=dict(control=np.array([[0.,0,0],[1,0,0]]),control_index=np.tile([0,1],(n,1)),derivative_basis=np.tile([-1.,1.],(n,1)),primitive_id=a['primitive_id'],internal_piece_id=a['internal_piece_id'],arc_t=a['arc_t']);ct['derivative_basis'][0]=0
  ap=tmp/'a.npz';cp=tmp/'c.npz';np.savez(ap,**a);np.savez(cp,**ct);return dict(gaussians=str(ap),controls=str(cp),kernel_count=n,p=1.,input_files={str(ap):sha(ap),str(cp):sha(cp)},helper_files={})
 def test_real_loader_callback_and_zero_derivative(self):
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   c=self.fixture(pathlib.Path(td));calls=[];d=load(c,lambda phase:calls.append(phase));self.assertIn('readiness',calls);self.assertFalse(d['valid'][0]);self.assertTrue(d['valid'][1:].all());self.assertFalse(d['asset']['means'].flags.writeable)
 def test_loader_guard_exception_propagates(self):
  def guard(phase):raise TimeoutError(phase)
  with self.assertRaisesRegex(TimeoutError,'readiness'):load({},guard)
 def test_checkpoint_cold_and_tamper(self):
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   p=pathlib.Path(td);c=self.fixture(p);d=load(c,lambda phase:None);a=f.assign(d['x'],d['t'],d['valid'],{1:np.array([[0.,0,0],[10,0,0]])});save_stage(p/'stage',d,{1:np.array([[0.,0,0],[10,0,0]])},a,[],2,'fixture',{});m,b,k=cold_stage(p/'stage','fixture');np.testing.assert_array_equal(a['edge_id'],b['edge_id']);(p/'stage'/'LINEAGE.json').write_text('{}');self.assertRaises(AssertionError,cold_stage,p/'stage','fixture')
if __name__=='__main__':unittest.main(verbosity=2)
