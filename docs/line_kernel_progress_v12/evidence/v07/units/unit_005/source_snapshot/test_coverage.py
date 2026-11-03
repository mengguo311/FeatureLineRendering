"""Unit002 isolated seed adapter and exact-coverage tests; no original asset reads."""
from free_io import *
import unittest,tempfile
import free_core as f
import seed_coverage as s
from scipy.spatial import cKDTree

class CoverageTests(unittest.TestCase):
 def test_marginal_coverage_not_density(self):
  cov=[np.array([0,1,2]),np.array([0,1,2]),np.array([3,4])];keys=[(0,0,0),(1,0,0),(2,0,0)];chosen,gain,remaining=s.select(cov,keys,2);self.assertEqual(chosen,[0,2]);self.assertEqual(gain,[3,2]);self.assertEqual(remaining.tolist(),[0,0,0])
 def test_all_equal_ties_canonical(self):
  chosen,gain,left=s.select([np.array([1,2]),np.array([2,3])],[(7,0,0),(4,0,0)],2);self.assertEqual(chosen,[1,0]);self.assertEqual(gain,[2,1])
 def test_zero_gain_stop_and_empty(self):
  chosen,gain,left=s.select([np.array([],int),np.array([1]),np.array([1])],[(0,0,0),(1,0,0),(2,0,0)],10);self.assertEqual(chosen,[1]);self.assertTrue(np.all(left==0))
 def test_complete_radius_and_voxel_dedup(self):
  x=np.c_[np.linspace(0,.7,80),np.zeros((80,2))];t=np.tile([1.,0,0],(80,1));rr=s.compatible_rows(x,t,np.arange(80),cKDTree(x),np.array([[0.,0,0],[1,0,0]]));self.assertEqual(len(rr),80);self.assertEqual(len(np.unique(np.floor(x[rr]).astype(int),axis=0)),1)
 def test_neighbor_outside_old_owner_is_included(self):
  x=np.array([[0.,0,0],[1,0,0],[2,0,0]]);t=np.tile([1.,0,0],(3,1));rr=s.compatible_rows(x,t,np.arange(3),cKDTree(x),np.array([[0.,0,0],[2,0,0]]));self.assertEqual(rr.tolist(),[0,1,2])
 def test_finite_cost_and_tangent(self):
  x=np.array([[0.,0,0],[0,.99,0],[0,0,0],[5,0,0]]);t=np.array([[1.,0,0],[1,0,0],[0,1,0],[1,0,0]]);rr=s.compatible_rows(x,t,np.arange(4),cKDTree(x),np.array([[-1.,0,0],[1,0,0]]));self.assertEqual(rr.tolist(),[0,1])
 def test_canonical_windows(self):
  q=np.array([[0.,0,0],[300,0,0]]);z=list(s.windows(q));self.assertEqual(len(z),3);self.assertEqual([(round(a),round(b)) for _,a,b,_ in z],[(0,128),(128,256),(256,300)]);self.assertTrue(all(len(v)<=129 for _,_,_,v in z));self.assertEqual(z[-1][3][-1,0],300)
 def fixture(self,p):
  arr=dict(carrier_id=np.array([11,80709]),version=np.array([3,4]),valid=np.array([False,True]),baseline=np.array([True,False]),kind=np.array(['invalid','line']),knot_offsets=np.array([0,2,4]),knots=np.array([[0.,0,0],[10,0,0],[0,3,0],[10,3,0]]),row_offsets=np.array([0,2,4]),rows=np.array([0,2,1,3]))
  carrier=p/'CARRIERS.npz';np.savez(carrier,**arr);dec=p/'OLD_DECISION.json';dec.write_text('{}');pc=p/'OLD_CONFIG.json';pc.write_text(json.dumps(dict(decision_path=str(dec),decision_sha256=sha(dec))));cp=p/'CHECKPOINT.json';cp.write_text(json.dumps(dict(complete=True,stage='M4_MERGE_ONLY_NATIVE',all_rows=4,config_binding=sha(pc),decision_sha256=sha(dec),files={'CARRIERS.npz':sha(carrier)})));m=p/'MEMBERSHIP.npz';np.savez(m,line_kernel_id=np.arange(4),carrier_id=np.array([11,80709,11,80709]),edge_id=np.full(4,-1));return dict(seed_carriers=str(carrier),seed_checkpoint=str(cp),seed_predecessor_config=str(pc),seed_expected_carriers=2,seed_expected_knots=4,kernel_count=4,p=1.,reference_memberships={'v05_M4':str(m)})
 def test_real_seed_loader_guard_unknown_and_offsets(self):
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   c=self.fixture(Path(td));calls=[];a=s.load_seeds(c,lambda phase:calls.append(phase));self.assertIn('readiness',calls);self.assertEqual(s.context_rows(a,[11,80709]).tolist(),[0,1,2,3]);self.assertFalse(a['valid'][0]);self.assertEqual(len(list(s.windows(a['knots'][:2]))),1)
 def test_loader_bad_ownership_rejected(self):
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   c=self.fixture(Path(td));np.savez(c['reference_memberships']['v05_M4'],line_kernel_id=np.arange(4),carrier_id=np.full(4,11));self.assertRaises(AssertionError,s.load_seeds,c,lambda phase:None)
 def test_seed_guard_exception(self):
  def guard(phase):raise TimeoutError(phase)
  self.assertRaisesRegex(TimeoutError,'readiness',s.load_seeds,{},guard)
 def test_bank_numerical_failure_cannot_be_rejection(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   p=Path(td);c=self.fixture(p);c.update(unit_root=str(p/'out'),decision_sha256='fixture');a=s.load_seeds(c,lambda phase:None);d=dict(x=np.array([[0.,0,0],[1,0,0],[0,3,0],[1,3,0]]),t=np.tile([1.,0,0],(4,1)),valid=np.ones(4,bool),p=1.)
   with patch.object(s,'compatible_rows',side_effect=ValueError('coverage_numeric_failure')):
    with self.assertRaisesRegex(ValueError,'coverage_numeric_failure'):s.initialize(c,d,a,lambda:None)
   self.assertFalse((p/'out/seed_bank/BANK_CHECKPOINT.json').exists());self.assertFalse((p/'out/seed_bank/SELECTION.npz').exists())
 def test_complete_bank_and_flags_do_not_lock(self):
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   p=Path(td);c=self.fixture(p);c.update(unit_root=str(p/'out'),decision_sha256='fixture');a=s.load_seeds(c,lambda phase:None);x=np.array([[0.,0,0],[1,0,0],[0,3,0],[1,3,0]]);d=dict(x=x,t=np.tile([1.,0,0],(4,1)),valid=np.ones(4,bool),p=1.);m,n,info=s.initialize(c,d,a,lambda:None);self.assertEqual(len(m),2);self.assertTrue(info['seed_bank_complete']);self.assertEqual(info['covered_voxels'],4);self.assertTrue((p/'out/seed_bank/SELECTION_CHECKPOINT.json').exists())
 def test_real_new_runner_contract(self):
  from test_free import FreeTests
  from unittest.mock import patch
  import coverage_runner as runner
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   p=Path(td);base=FreeTests().fixture(p);sp=p/'seed';sp.mkdir();seed=self.fixture(sp)
   with np.load(seed['seed_carriers']) as z:a={k:z[k] for k in z.files}
   a['rows']=np.arange(30);a['row_offsets']=np.array([0,15,30]);np.savez(seed['seed_carriers'],**a)
   cp=json.loads(Path(seed['seed_checkpoint']).read_text());cp['all_rows']=30;cp['files']['CARRIERS.npz']=sha(seed['seed_carriers']);Path(seed['seed_checkpoint']).write_text(json.dumps(cp));np.savez(seed['reference_memberships']['v05_M4'],line_kernel_id=np.arange(30),carrier_id=np.repeat([11,80709],15),edge_id=np.full(30,-1))
   seed['kernel_count']=30;base.update(seed);base.update(unit_root=str(p/'out'),runtime_root=str(p),scene='fixture',max_seconds=1800,absolute_deadline_jst='2026-11-01T19:38:00+09:00');Path(base['unit_root']).mkdir();dec=p/'DECISION.json';dec.write_text('{}');base.update(decision_path=str(dec),decision_sha256=sha(dec))
   with patch.object(runner,'deliver',return_value={'fixture_render_not_run':True}):rc=runner.run(base,'fixture')
   result=json.loads((p/'out/RUN_RESULT.json').read_text());self.assertEqual(rc,0,result);self.assertEqual(len(result['completed_stages']),4);self.assertFalse(result['errors']);self.assertTrue((p/'out/seed_bank/BANK_CHECKPOINT.json').exists());scope=json.loads((p/'out/scenes/fixture/stages/FREE_STATIC/SCOPE.json').read_text());self.assertFalse(scope['model_discovery_complete']);self.assertTrue(scope['seed_bank_complete'])
 def test_unchanged_frozen_core(self):
  self.assertEqual(sha(f.__file__),'5fa12b98da4d24000294a760281e3a51054e455d5cf0762ea18b2b1bb4efa81e')
 def test_lazy_matches_full_recompute(self):
  cov=[np.array([0,1,3]),np.array([1,2,4]),np.array([0,2,5]),np.array([6]),np.array([2,5,6])];keys=[(i,0,0) for i in range(5)];chosen,gain,left=s.select(cov,keys,4);covered=set();want=[]
  for _ in range(4):
   options=[(len(set(v)-covered),keys[i],i) for i,v in enumerate(cov) if i not in want];g,k,i=min(options,key=lambda z:(-z[0],z[1]))
   if not g:break
   want.append(i);covered.update(cov[i])
  self.assertEqual(chosen,want)
if __name__=='__main__':unittest.main(verbosity=2)
