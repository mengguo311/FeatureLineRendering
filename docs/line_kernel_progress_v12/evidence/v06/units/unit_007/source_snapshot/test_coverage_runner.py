"""24 synthetic kernels, four carriers: real model recovery and durable mappings only."""
from runtime_io import *
import unittest
from unittest.mock import patch
from test_overlap_model import fixture
from coverage_policy import select_scope
from overlap_model import select_components
from observation_model import build_extra_bank
from pair_model import fit_engine,fit_pair
from pair_delivery import export_overlap
import coverage_runner as runner
import coverage_stages as stages
import coverage_control as control
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_007/tests')
CORE=Path(__file__).parent/'pinned_v05_fit_core.py'
class VerticalCoverage(unittest.TestCase):
 def fixture(self):
  root=U/('vertical_'+str(time.time_ns()));root.mkdir(parents=True);d=fixture(4,offsets=[0.,.4,10.,10.4]);d['asset']['means'][:6,1]=-.2;d['asset']['means'][6:12,1]=.6;d['asset']['means'][12:18,1]=9.8;d['asset']['means'][18:,1]=10.6;d['representatives']['x']=d['asset']['means'][d['representatives']['mid']].copy();d['ambiguous']=set()
  d['pairs']=[(0,1),(2,3)];d['overlaps']=[dict(a=a,b=b,record_id=i) for i,(a,b) in enumerate(d['pairs'])]
  e=fit_engine(CORE,d);models=[fit_pair(e,d,a,b,i,None) for i,(a,b) in enumerate(d['pairs'])];self.assertTrue(all(m['status']=='RECOVERED' for m in models));names=list(models[0]['metrics'])
  d['candidates']=dict(a=np.array([0,2]),b=np.array([1,3]),operation=np.array(['overlap']*2),reason=np.array(['accepted']*2),cost=np.array([m['cost'] for m in models]),metric_names=np.array(names),metrics=np.array([[m['metrics'][n] for n in names] for m in models]));d['ordered']=dict(a=np.array([0,2]),b=np.array([1,3]))
  nz(root/'source.npz',**d['asset']);(root/'state.txt').write_text('SYNTHETIC24');js(root/'cameras.json',dict(scan24=[dict(view='0012'),dict(view='0036')]))
  prior=root/'control';base=root/'fixed';c=dict(unit=str(root/'new'),runtime=str(U),max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00',kernel_count=24,p=1.,expected_candidate_records=2,expected_successful_overlap=2,overlap_priority_ids=[0],decision_carrier_cap=128,max_components=1,expected_all_components=2,control_contexts=1,candidate_metrics='synthetic',solver=dict(per_context_seconds=5,total_seconds=30),source_files={},helper_files={},input_files={str(root/'state.txt'):sha(root/'state.txt'),str(root/'source.npz'):sha(root/'source.npz')},state=str(root/'state.txt'),membership='synthetic',gaussians=str(root/'source.npz'),cameras=str(root/'cameras.json'),views=['0012','0036'],negative_pairs=[],prior_unit=str(prior),base_bank_unit=str(base),base_bank_config_sha256='base',previous_config_sha256='prior',expected_selected_pairs=1,expected_old_hypotheses=0,expected_control_hypotheses=1,fit_source=str(CORE),model_fit=dict(maximum_attempts=1))
  contexts,audit=select_components(c,d);js(prior/'selection.json',dict(contexts=contexts,audit=audit));c['prior_selection']=str(prior/'selection.json')
  model=models[0];model['context_id']=0;p=prior/'scenes/scan24/models/pair_0_1';js(p/'MODEL.json',model);checkpoint(p,['MODEL.json'],'prior','MODEL')
  hs,recs=build_extra_bank(d,contexts[0],[model]);self.assertEqual(len(hs),1)
  for i,h in enumerate(hs):h.update(hid=i,context_id=0)
  for path,binding in [(base,'base'),(prior,'prior')]:
   p=path/'scenes/scan24/banks/component_00000';js(p/'BANK.json',dict(status='BANK_COMPLETE',hypotheses=hs if path==prior else []));js(p/'REJECTIONS.json',recs if path==prior else []);checkpoint(p,['BANK.json','REJECTIONS.json'],binding,'BANK')
  c['previous_arms']={}
  for ai,a in enumerate(('greedy','joint')):
   p=prior/'scenes/scan24/stages'/a;c['previous_arms'][a]=str(p);export_overlap(p,c,dict(d,next_version=1000+ai*24),[0],hs,[],{},'prior')
  js(root/'CONFIG.json',c);return root,c,d
 def run_no_render(self,root,c,d):
  with patch.object(runner,'load',return_value=d),patch.object(runner,'successful_overlaps',return_value=d['overlaps']),patch.object(runner,'renderer',side_effect=RuntimeError('DELIBERATE_NO_RENDER')):
   with self.assertRaisesRegex(RuntimeError,'DELIBERATE_NO_RENDER'):runner.run(c,root/'CONFIG.json')
 def test_new_component_real_fit_control_versions_and_later_failure_resume(self):
  root,c,d=self.fixture();self.run_no_render(root,c,d);out=Path(c['unit']);r=json.loads((out/'RUN_RESULT.json').read_text());self.assertEqual(r['fit_calls'],1);self.assertTrue(r['control_replay_exact']);self.assertEqual(r['actual_saved_pngs'],[])
  for arm in ('greedy','joint'):
   p=out/'scenes/scan24/stages'/arm;verify_checkpoint(p,sha(root/'CONFIG.json'));m=np.load(p/'MEMBERSHIP.npz',allow_pickle=False);self.assertEqual(len(m['edge_id']),24);self.assertTrue(np.all(m['edge_id'][:12]==0));self.assertTrue(np.all(m['edge_id'][12:]==2))
   self.assertEqual(json.loads((p/'GROUPS.json').read_text())['groups'][0],json.loads((Path(c['previous_arms'][arm])/'GROUPS.json').read_text())['groups'][0])
  hashes={str(p):sha(p) for p in out.rglob('CHECKPOINT.json')};(out/'RUN_RESULT.json').rename(out/'EXPECTED_FIRST_FAILURE.json')
  with patch.object(stages,'fit_engine',side_effect=AssertionError('NO_REFIT')),patch.object(stages,'build_bank',side_effect=AssertionError('NO_REBUILD')),patch.object(control,'legacy_bank',side_effect=AssertionError('NO_CONTROL_REBUILD')),patch.object(runner,'export_overlap',side_effect=AssertionError('NO_REEXPORT')):self.run_no_render(root,c,d)
  self.assertEqual(hashes,{p:sha(p) for p in hashes})
 def test_partial_component_never_promoted(self):
  root,c,d=self.fixture()
  with patch.object(stages,'build_bank',side_effect=TimeoutError('PHASE_DEADLINE readiness')):self.run_no_render(root,c,d)
  out=Path(c['unit']);bank=json.loads((out/'scenes/scan24/banks/component_00001/BANK.json').read_text());self.assertEqual(bank['hypotheses'],[]);self.assertEqual(bank['status'],'NOT_RUN_BANK_DEADLINE')
  m=np.load(out/'scenes/scan24/stages/joint/MEMBERSHIP.npz',allow_pickle=False);self.assertTrue(np.all(m['edge_id'][12:]<0));self.assertTrue(np.all(m['edge_id'][:12]==0))
 def test_fit_mismatch_blocks_whole_component(self):
  root,c,d=self.fixture();d['candidates']['metrics'][1,0]+=.01
  self.run_no_render(root,c,d);bank=json.loads((Path(c['unit'])/'scenes/scan24/banks/component_00001/BANK.json').read_text());self.assertEqual(bank['status'],'BLOCKED_REPRODUCTION');self.assertEqual(bank['hypotheses'],[])
 def test_timeout_after_real_fit_retains_true_attempt_count(self):
  root,c,d=self.fixture();actual=stages.fit_pair
  def interrupted(*args,**kwargs):
   actual(*args,**kwargs)
   raise TimeoutError('PHASE_DEADLINE readiness after fit')
  with patch.object(stages,'fit_pair',side_effect=interrupted):self.run_no_render(root,c,d)
  out=Path(c['unit']);r=json.loads((out/'RUN_RESULT.json').read_text());self.assertEqual(r['fit_calls'],1)
  m=json.loads((out/'scenes/scan24/models/pair_2_3/MODEL.json').read_text());self.assertEqual(m['fit_calls'],1);self.assertEqual(m['status'],'NOT_RUN_BANK_DEADLINE')
  bank=json.loads((out/'scenes/scan24/banks/component_00001/BANK.json').read_text());self.assertEqual(bank['hypotheses'],[])
 def test_missing_joint_incumbent_keeps_both_arms_on_M4(self):
  root,c,d=self.fixture();actual=runner.select_joint
  def solve(hs,*args,**kwargs):
   if any(2 in h['leaves'] for h in hs):return [],dict(status='partial',feasible_incumbent=False,seconds=0.,bound=None,gap=None)
   return actual(hs,*args,**kwargs)
  with patch.object(runner,'select_joint',side_effect=solve):self.run_no_render(root,c,d)
  for arm in ('greedy','joint'):
   m=np.load(Path(c['unit'])/'scenes/scan24/stages'/arm/'MEMBERSHIP.npz',allow_pickle=False)
   self.assertTrue(np.all(m['edge_id'][12:]<0));self.assertTrue(np.all(m['edge_id'][:12]==0))
 def test_control_version_mismatch_blocks_before_mapping(self):
  root,c,d=self.fixture();d['leaves'][1].version+=1
  with patch.object(runner,'load',return_value=d),patch.object(runner,'successful_overlaps',return_value=d['overlaps']):
   with self.assertRaises(AssertionError):runner.run(c,root/'CONFIG.json')
  self.assertFalse((Path(c['unit'])/'scenes/scan24/stages/joint/CHECKPOINT.json').exists())
if __name__=='__main__':unittest.main(verbosity=2)
