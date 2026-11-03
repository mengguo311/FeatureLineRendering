"""Bounded fresh-scene contract and checkpoint regressions, no rendering."""
from runtime_io import *
from test_overlap_model import fixture
from pair_model import fit_engine,fit_pair
from unittest.mock import patch
import unittest,importlib
RUNNER=importlib.import_module('coverage_runner')
ADAPTER=importlib.import_module('adapter')
STAGES=importlib.import_module('coverage_stages')
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_008/tests')
CORE=Path(__file__).parent/'pinned_v05_fit_core.py'

class SceneContract(unittest.TestCase):
 def fixture(self):
  root=U/('fixture_'+str(time.time_ns()));root.mkdir(parents=True)
  d=fixture(4,offsets=[0.,.4,10.,10.4]);d['ambiguous']=set()
  d['asset']['means'][:6,1]=-.2;d['asset']['means'][6:12,1]=.6;d['asset']['means'][12:18,1]=9.8;d['asset']['means'][18:,1]=10.6
  d['representatives']['x']=d['asset']['means'][d['representatives']['mid']].copy()
  d['pairs']=[(0,1),(2,3)];d['overlaps']=[dict(a=a,b=b,record_id=i) for i,(a,b) in enumerate(d['pairs'])]
  e=fit_engine(CORE,d);models=[fit_pair(e,d,a,b,i,None) for i,(a,b) in enumerate(d['pairs'])];self.assertTrue(all(m['status']=='RECOVERED' for m in models));names=list(models[0]['metrics'])
  d['candidates']=dict(a=np.array([0,2]),b=np.array([1,3]),operation=np.array(['overlap']*2),reason=np.array(['accepted']*2),cost=np.array([m['cost'] for m in models]),metric_names=np.array(names),metrics=np.array([[m['metrics'][n] for n in names] for m in models]));d['ordered']=dict(a=np.array([0,2]),b=np.array([1,3]))
  nz(root/'source.npz',**d['asset']);(root/'state.txt').write_text('SYNTHETIC24');js(root/'cameras.json',dict(ficus=[dict(view='test_r_1'),dict(view='test_r_79')]))
  c=dict(scene='ficus',unit=str(root/'new'),runtime=str(U),max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00',kernel_count=24,p=1.,expected_candidate_records=2,expected_successful_overlap=2,overlap_priority_ids=[0],decision_carrier_cap=128,expected_all_components=2,control_contexts=0,candidate_metrics='synthetic',solver=dict(per_context_seconds=5,total_seconds=30),source_files={},helper_files={},input_files={str(root/'state.txt'):sha(root/'state.txt'),str(root/'source.npz'):sha(root/'source.npz')},state=str(root/'state.txt'),membership='synthetic',gaussians=str(root/'source.npz'),cameras=str(root/'cameras.json'),views=['test_r_1','test_r_79'],negative_pairs=[],fixed_member_ids=[0],previous_arms={},fit_source=str(CORE),model_fit=dict(maximum_attempts=2))
  js(root/'CONFIG.json',c);return root,c,d
 def run_no_render(self,root,c,d):
  with patch.object(RUNNER,'load',return_value=d),patch.object(RUNNER,'successful_overlaps',return_value=d['overlaps']),patch.object(RUNNER,'renderer',side_effect=RuntimeError('DELIBERATE_NO_RENDER')):
   with self.assertRaisesRegex(RuntimeError,'DELIBERATE_NO_RENDER'):RUNNER.run(c,root/'CONFIG.json')
 def test_fresh_scene_bootstrap_and_paths(self):
  root,c,d=self.fixture();self.run_no_render(root,c,d);out=Path(c['unit']);r=json.loads((out/'RUN_RESULT.json').read_text())
  self.assertEqual(r['fit_calls'],2);self.assertEqual(r['actual_saved_pngs'],[]);self.assertFalse((out/'scenes/scan24').exists())
  for arm in ('greedy','joint'):
   p=out/'scenes/ficus/stages'/arm;verify_checkpoint(p,sha(root/'CONFIG.json'));m=np.load(p/'MEMBERSHIP.npz',allow_pickle=False)
   self.assertEqual(len(m['edge_id']),24);self.assertTrue(np.all(m['edge_id'][:12]==0));self.assertTrue(np.all(m['edge_id'][12:]==2))
  hashes={str(p):sha(p) for p in out.rglob('CHECKPOINT.json')};(out/'RUN_RESULT.json').rename(out/'EXPECTED_FAILURE.json')
  with patch.object(STAGES,'fit_engine',side_effect=AssertionError('NO_REFIT')),patch.object(STAGES,'build_bank',side_effect=AssertionError('NO_REBUILD')),patch.object(RUNNER,'export_overlap',side_effect=AssertionError('NO_REEXPORT')):self.run_no_render(root,c,d)
  self.assertEqual(hashes,{p:sha(p) for p in hashes})
 def test_adapter_uses_configured_count(self):
  root=U/('adapter_'+str(time.time_ns()));root.mkdir(parents=True);n=24
  (root/'DECISION.json').write_text('{}');js(root/'old.json',dict(decision_path=str(root/'DECISION.json'),decision_sha256=sha(root/'DECISION.json')))
  js(root/'checkpoint.json',dict(complete=True,stage='M4_STATE',config_binding=sha(root/'old.json'),decision_sha256=sha(root/'DECISION.json'),files={}))
  nz(root/'asset.npz',means=np.zeros((n,3)));nz(root/'carriers.npz',carrier_id=np.empty(0,np.int64))
  nz(root/'members.npz',edge_id=np.full(n,-1,np.int64),carrier_id=np.full(n,-1,np.int64),line_kernel_id=np.arange(n))
  nz(root/'reps.npz',kernel_rep=np.full(n,-1,np.int64))
  nz(root/'candidates.npz',a=np.empty(0,np.int64),b=np.empty(0,np.int64),operation=np.array([],dtype='U8'),reason=np.array([],dtype='U16'),metric_names=np.array(['residual_max','residual_q95','tangent_max']),metrics=np.empty((0,3)),cost=np.empty(0))
  nz(root/'ordered.npz',a=np.empty(0,np.int64),b=np.empty(0,np.int64));nz(root/'ambiguity.npz',pairs=np.empty((0,2),np.int64))
  nz(root/'controls.npz',control=np.array([[[1.,0,0],[0,0,0]]]),control_index=np.zeros(n,np.int64),derivative_basis=np.tile([1.,0],(n,1)))
  c=dict(input_files={},helper_files={},source_files={},decision_path=str(root/'DECISION.json'),decision_sha256=sha(root/'DECISION.json'),predecessor_checkpoint=str(root/'checkpoint.json'),predecessor_config=str(root/'old.json'),state='SYNTHETIC',kernel_count=n,p=1.)
  for key,name in [('gaussians','asset'),('carriers','carriers'),('membership','members'),('representatives','reps'),('candidate_status','candidates'),('ordered_candidates','ordered'),('ambiguity','ambiguity'),('controls','controls')]:c[key]=str(root/(name+'.npz'))
  with patch.object(ADAPTER,'state_read',return_value=dict(carriers={},aux={},next_version=1)):
   d=ADAPTER.load(c,lambda *_:None)
  self.assertEqual(len(d['asset']['means']),n)
 def test_whole_component_mismatch_retains_M4(self):
  root,c,d=self.fixture();d['candidates']['metrics'][1,0]+=.01;self.run_no_render(root,c,d)
  p=Path(c['unit'])/'scenes/ficus';bank=json.loads((p/'banks/component_00001/BANK.json').read_text());self.assertEqual(bank['status'],'BLOCKED_REPRODUCTION');self.assertEqual(bank['hypotheses'],[])
  for arm in ('greedy','joint'):
   m=np.load(p/'stages'/arm/'MEMBERSHIP.npz');self.assertTrue(np.all(m['edge_id'][12:]<0))
 def test_no_joint_incumbent_keeps_same_scope(self):
  root,c,d=self.fixture()
  with patch.object(RUNNER,'select_joint',return_value=([],dict(status='partial',feasible_incumbent=False,seconds=0))):self.run_no_render(root,c,d)
  for arm in ('greedy','joint'):
   m=np.load(Path(c['unit'])/'scenes/ficus/stages'/arm/'MEMBERSHIP.npz');np.testing.assert_array_equal(m['edge_id'],d['membership']['edge_id'])
 def test_bank_deadline_preserves_full_mapping(self):
  root,c,d=self.fixture()
  with patch.object(STAGES,'build_bank',side_effect=TimeoutError('PHASE_DEADLINE readiness')):self.run_no_render(root,c,d)
  for arm in ('greedy','joint'):
   m=np.load(Path(c['unit'])/'scenes/ficus/stages'/arm/'MEMBERSHIP.npz');np.testing.assert_array_equal(m['edge_id'],d['membership']['edge_id'])
  r=json.loads((Path(c['unit'])/'RUN_RESULT.json').read_text());self.assertEqual(r['fit_calls'],0)
 def test_fixed_references_survive_zero_hypotheses(self):
  from scene_policy import diagnostics
  root,c,d=self.fixture();c['fixed_member_ids']=[0,1];c['reference_leaf_sets']=[[0,1]]
  result=diagnostics(c,d,{a:(d['membership'],[]) for a in ['greedy','joint']},[])
  self.assertEqual(result['cases'][0]['core_carriers'],[0,1]);self.assertEqual(result['cases'][0]['evidence_carriers'],[0,1]);self.assertIn('largest_new_polyline_member_group',result['missing'])
