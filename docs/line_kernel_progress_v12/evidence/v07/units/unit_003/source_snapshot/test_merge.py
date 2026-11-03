"""Small unit003 contracts; no original asset loads or rendering."""
from free_io import *
import unittest,tempfile
import free_core as f
import merge_core as m

class MergeTests(unittest.TestCase):
 def data(self):
  x=np.c_[np.r_[np.linspace(0,6,31),np.linspace(7,13,31),[50.]],np.zeros((63,2))]
  return dict(x=x,t=np.tile([1.,0,0],(63,1)),valid=np.ones(63,bool),half=np.full(63,.3))
 def models(self):return {4:np.c_[np.arange(7.),np.zeros((7,2))],8:np.c_[np.arange(7.,14.),np.zeros((7,2))]}
 def test_all_endpoint_candidates_no_topk(self):
  models={0:np.array([[0.,0,0],[6,0,0]])}
  for i in range(1,81):models[i]=np.array([[7.,.001*i,0],[13,.001*i,0]])
  candidates,records=m.enumerate_candidates(models)
  self.assertEqual(sum(z['a']==0 for z in candidates),80)
  self.assertEqual(len(records['a']),4*81*80//2)
 def test_orient_and_zero_gap(self):
  models={4:np.array([[6.,0,0],[0,0,0]]),8:np.array([[6.,0,0],[12,0,0]])}
  candidates,_=m.enumerate_candidates(models);self.assertEqual(len(candidates),1)
  q=m.template(models,candidates[0]);self.assertEqual(q[0,0],0);self.assertEqual(q[-1,0],12)
  self.assertTrue(np.all(np.linalg.norm(np.diff(q,axis=0),axis=1)>0))
 def test_energy_uses_actual_model_not_stale_cost(self):
  d=self.data();models=self.models();a=f.assign(d['x'],d['t'],d['valid'],models);a['alternative_cost'][:]=999
  z=m.energy(d,models,a);self.assertAlmostEqual(z['data'],1);self.assertAlmostEqual(z['total'],3)
 def test_real_merge_free_assignment_and_originals_unchanged(self):
  d=self.data();models=self.models();a=f.assign(d['x'],d['t'],d['valid'],models);old={k:v.copy() for k,v in a.items()};qq={k:v.copy() for k,v in models.items()};p=m.enumerate_candidates(models)[0][0]
  r=m.trial(d,models,a,10,p)
  self.assertTrue(r['accepted'],r['reason']);self.assertEqual(len(r['models']),1);self.assertEqual(r['assignment']['edge_id'][-1],-1)
  self.assertLess(r['after']['total'],r['before']['total']-f.EPS)
  for k in a:np.testing.assert_array_equal(a[k],old[k])
  for k in models:np.testing.assert_array_equal(models[k],qq[k])
 def test_support_split_rejects_merge_transactionally(self):
  d=self.data();d['x'][31:62,0]+=3;models={4:np.c_[np.arange(9.),np.zeros((9,2))],8:np.c_[np.arange(9.,18.),np.zeros((9,2))]};a=f.assign(d['x'],d['t'],d['valid'],models);p=m.enumerate_candidates(models)[0][0]
  r=m.trial(d,models,a,10,p);self.assertFalse(r['accepted']);self.assertIn(r['reason'],['merged_support_not_one_piece','geometry:window_turn','geometry:vertex_turn'])
 def test_guard_propagates(self):
  def guard():raise TimeoutError('fixture_deadline')
  self.assertRaisesRegex(TimeoutError,'fixture_deadline',m.enumerate_candidates,self.models(),guard)
 def test_failure_after_assignment_exposes_saved_progress(self):
  from unittest.mock import patch
  d=self.data();mm=self.models();a=f.assign(d['x'],d['t'],d['valid'],mm);p=m.enumerate_candidates(mm)[0][0];progress=[]
  with patch.object(f,'validate_support',side_effect=RuntimeError('later_support_failure')):
   with self.assertRaisesRegex(RuntimeError,'later_support_failure'):
    m.trial(d,mm,a,10,p,progress=lambda phase,r:progress.append(phase))
  self.assertEqual(progress,['fitted','raw'])
 def test_version_key_geometry_sensitive(self):
  mm=self.models();p=m.enumerate_candidates(mm)[0][0];key=m.key(p);mm[4]=mm[4]+[0,.01,0];p2=m.enumerate_candidates(mm)[0][0];self.assertNotEqual(key,m.key(p2))
 def test_bad_angle_and_large_template(self):
  mm={4:np.array([[0.,0,0],[6,0,0]]),8:np.array([[7.,0,0],[7,6,0]])};self.assertFalse(m.enumerate_candidates(mm)[0])
  mm={4:np.array([[0.,0,0],[128,0,0]]),8:np.array([[129.,0,0],[140,0,0]])};p=m.enumerate_candidates(mm)[0][0]
  self.assertRaisesRegex(ValueError,'length_cap',m.template,mm,p)

 def test_lossless_delta_includes_unknown_and_auxiliary(self):
  d=self.data();a=f.assign(d['x'],d['t'],d['valid'],self.models());b={k:v.copy() for k,v in a.items()};b['edge_id'][0]=-1;b['alternative_cost'][10,1]=.4;b['alternatives'][20,0]=91
  delta=m.delta(a,b);recovered={k:v.copy() for k,v in a.items()}
  for k in a:recovered[k][delta['changed_rows']]=delta[k];np.testing.assert_array_equal(recovered[k],b[k])
 def fixture(self,p):
  from merge_runner import FIELDS
  x=self.data()['x'];n=len(x);asset=dict(means=x,covariance=np.tile(np.eye(3)*.09,(n,1,1)),opacity=np.ones(n),colors=np.zeros((n,3)),primitive_id=np.arange(n,dtype=np.int32),internal_piece_id=np.arange(n,dtype=np.int32),arc_t=np.arange(n,dtype=float));ct=dict(control=np.array([[0.,0,0],[1,0,0]]),control_index=np.tile([0,1],(n,1)),derivative_basis=np.tile([-1.,1.],(n,1)),**{k:asset[k] for k in ['primitive_id','internal_piece_id','arc_t']});ap=p/'asset.npz';cp=p/'controls.npz';np.savez(ap,**asset);np.savez(cp,**ct);c=dict(gaussians=str(ap),controls=str(cp),kernel_count=n,p=1.,input_files={str(ap):sha(ap),str(cp):sha(cp)},helper_files={});d=load(c,lambda phase:None);models=self.models();a=f.assign(d['x'],d['t'],d['valid'],models)
  dec=p/'OLD_DECISION.json';dec.write_text('{}');pc=p/'OLD_CONFIG.json';pc.write_text(json.dumps(dict(decision_path=str(dec),decision_sha256=sha(dec))))
  stage=p/'previous';save_stage(stage,d,models,a,[],10,sha(pc),{});c.update(predecessor_stage=str(stage),predecessor_config=str(pc),predecessor_config_sha256=sha(pc),predecessor_model_count=2,predecessor_next_id=10)
  return c,d
 def test_real_restore_callback_contract(self):
  from merge_runner import restore
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   c,d=self.fixture(Path(td));calls=[];mm,a,nxt=restore(c,d,lambda phase:calls.append(phase));self.assertTrue(all(p=='readiness' for p in calls));self.assertEqual(nxt,10);self.assertEqual(len(mm),2)
 def test_restore_guard_and_bad_offset(self):
  from merge_runner import restore
  def guard(phase):raise TimeoutError('stage:'+phase)
  self.assertRaisesRegex(TimeoutError,'stage:readiness',restore,{},None,guard)
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   c,d=self.fixture(Path(td));mp=Path(c['predecessor_stage'])/'MODELS.npz'
   with np.load(mp) as z:kw={k:z[k] for k in z.files}
   kw['offsets'][0]=1;np.savez(mp,**kw);cp=mp.parent/'CHECKPOINT.json';obj=json.loads(cp.read_text());obj['files']['MODELS.npz']=sha(mp);cp.write_text(json.dumps(obj));self.assertRaises(AssertionError,restore,c,d,lambda phase:None)
 def runner_fixture(self,p):
  from test_coverage import CoverageTests
  c,d=self.fixture(p);sp=p/'seed';sp.mkdir();seed=CoverageTests().fixture(sp)
  with np.load(seed['seed_carriers']) as z:kw={k:z[k] for k in z.files}
  kw['rows']=np.arange(63);kw['row_offsets']=np.array([0,31,63]);np.savez(seed['seed_carriers'],**kw);cp=Path(seed['seed_checkpoint']);obj=json.loads(cp.read_text());obj['all_rows']=63;obj['files']['CARRIERS.npz']=sha(seed['seed_carriers']);cp.write_text(json.dumps(obj));np.savez(seed['reference_memberships']['v05_M4'],line_kernel_id=np.arange(63),carrier_id=np.r_[np.full(31,11),np.full(32,80709)],edge_id=np.full(63,-1));seed['kernel_count']=63;c.update(seed)
  dec=p/'DECISION.json';dec.write_text('{}');out=p/'out';out.mkdir();c.update(unit_root=str(out),runtime_root=str(p),scene='fixture',max_seconds=1800,absolute_deadline_jst='2026-11-01T19:38:00+09:00',decision_path=str(dec),decision_sha256=sha(dec));return c
 def test_real_runner_no_render_and_later_failure_preserves_control(self):
  import merge_runner as runner
  from unittest.mock import patch
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   p=Path(td);c=self.runner_fixture(p)
   with patch.object(runner,'deliver',side_effect=RuntimeError('fixture_render_failure')):rc=runner.run(c,'fixture')
   self.assertEqual(rc,1);out=Path(c['unit_root']);self.assertTrue((out/'scenes/fixture/stages/NO_MERGE/CHECKPOINT.json').exists());cold_stage(out/'scenes/fixture/stages/NO_MERGE','fixture');res=json.loads((out/'RUN_RESULT.json').read_text());self.assertTrue(res['fatal']);self.assertIn('MERGE_FINAL',res['completed_stages'])
 def test_real_runner_and_cold_full_rows(self):
  import merge_runner as runner
  from unittest.mock import patch
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as td:
   p=Path(td);c=self.runner_fixture(p)
   with patch.object(runner,'deliver',return_value=dict(fixture_render_not_run=True)):rc=runner.run(c,'fixture')
   self.assertEqual(rc,0);out=Path(c['unit_root']);mm,a,line=cold_stage(out/'scenes/fixture/stages/MERGE_FINAL','fixture');self.assertEqual(len(a['edge_id']),63);self.assertEqual(len(mm),1);self.assertTrue((out/'scenes/fixture/stages/MERGE_001/CHECKPOINT.json').exists());self.assertTrue((out/'trials/TRIAL_000/PROGRESS_RAW_DELTA.npz').exists())
 def test_energy_rejection_preserves_input(self):
  from unittest.mock import patch
  d=self.data();mm=self.models();a=f.assign(d['x'],d['t'],d['valid'],mm);old=a['edge_id'].copy();p=m.enumerate_candidates(mm)[0][0]
  with patch.object(f,'irls_update',side_effect=lambda x,q:q+[0,.4,0]):r=m.trial(d,mm,a,10,p)
  self.assertFalse(r['accepted']);self.assertEqual(r['reason'],'no_energy_decrease');self.assertGreater(r['after']['data'],r['before']['data']);np.testing.assert_array_equal(a['edge_id'],old)

if __name__=='__main__':unittest.main(verbosity=2)
