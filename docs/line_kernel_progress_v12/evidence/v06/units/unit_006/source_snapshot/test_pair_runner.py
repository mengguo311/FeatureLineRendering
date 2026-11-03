"""12-row real-fit vertical fixture: no full-asset adapter execution or render."""
from runtime_io import *
import unittest
from unittest.mock import patch
from test_pair_model import recoverable,CORE
import pair_runner as runner
import pair_stages
from overlap_model import select_components,build_bank,select_greedy
from pair_model import model_group_guard
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_005/tests')

class Vertical(unittest.TestCase):
    def fixture(self,bad=False):
        root=U/('vertical_'+str(time.time_ns()));root.mkdir();prior=root/'old';prior.mkdir();d=recoverable();d['ambiguous']=set()
        names=['residual_max','residual_q95','tangent_max','vertex_turn','window_turn','supported_length','longest_run','max_gap','total_gap'];met=[.4,.4,0.,0.,0.,6.,6.,0.,0.]
        if bad:met[0]=99.
        d['candidates']=dict(a=np.array([0]),b=np.array([1]),operation=np.array(['overlap']),reason=np.array(['accepted']),cost=np.array([met[0]]),metric_names=np.array(names),metrics=np.array([met]));d['ordered']=dict(a=np.array([0]),b=np.array([1]));d['pairs']=[(0,1)]
        nz(root/'source.npz',**d['asset']);(root/'state.txt').write_text('SYNTHETIC12');js(root/'cameras.json',{'scan24':[dict(view='0012'),dict(view='0036')]})
        c=dict(unit=str(root/'new'),runtime=str(U),max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00',kernel_count=12,p=1.,expected_candidate_records=1,expected_successful_overlap=1,overlap_priority_ids=[0],decision_carrier_cap=128,max_components=8,candidate_metrics='synthetic',solver=dict(per_context_seconds=5,total_seconds=10),source_files={},helper_files={},input_files={str(root/'state.txt'):sha(root/'state.txt'),str(root/'source.npz'):sha(root/'source.npz')},state=str(root/'state.txt'),membership='synthetic',gaussians=str(root/'source.npz'),cameras=str(root/'cameras.json'),views=['0012','0036'],negative_pairs=[],reference_leaf_groups={},prior_unit=str(prior),previous_config_sha256='old-binding',fit_source=str(CORE),expected_selected_pairs=1,expected_contexts=1,expected_decision_leaves=2)
        contexts,audit=select_components(c,d);js(prior/'selection.json',dict(contexts=contexts,audit=audit));c['prior_selection']=str(prior/'selection.json')
        hs,_=build_bank(d,contexts[0]);self.assertEqual(hs,[]);c['expected_old_hypotheses']=0
        bank=prior/'scenes/scan24/banks/component_00000';js(bank/'BANK.json',dict(status='BANK_COMPLETE',hypotheses=hs));checkpoint(bank,['BANK.json'],'old-binding','BANK')
        c['previous_arms']={}
        for arm in ['greedy','joint']:
            p=prior/'scenes/scan24/stages'/arm;c['previous_arms'][arm]=str(p);nz(p/'SELECTED_HYPOTHESES.npz',hypothesis_id=np.array([],np.int64));nz(p/'MEMBERSHIP.npz',**d['membership']);js(p/'GROUPS.json',dict(groups=[]))
        js(root/'CONFIG.json',c);return root,c,d
    def test_complete_models_and_mappings_survive_later_failure_and_resume(self):
        root,c,d=self.fixture()
        def run():
            with patch.object(runner,'load',return_value=d),patch.object(runner,'successful_overlaps',return_value=d['overlaps']),patch.object(runner,'renderer',side_effect=RuntimeError('DELIBERATE_NO_RENDER')):
                with self.assertRaisesRegex(RuntimeError,'DELIBERATE_NO_RENDER'):runner.run(c,root/'CONFIG.json')
        run();out=Path(c['unit']);result=json.loads((out/'RUN_RESULT.json').read_text());self.assertEqual(result['fit_calls'],1);self.assertEqual(result['recovered_models'],1);self.assertEqual(result['actual_saved_pngs'],[])
        for arm in ['greedy','joint']:
            p=out/'scenes/scan24/stages'/arm;verify_checkpoint(p,sha(root/'CONFIG.json'));m=np.load(p/'MEMBERSHIP.npz',allow_pickle=False);self.assertEqual(len(m['edge_id']),12);self.assertTrue(np.all(m['edge_id']==0));g=json.loads((p/'GROUPS.json').read_text())['groups'][0];self.assertEqual(g['seed_pair'],[0,1]);self.assertIn('model_q',g)
        hashes={str(p):sha(p) for p in out.rglob('CHECKPOINT.json')};(out/'RUN_RESULT.json').rename(out/'FIRST_EXPECTED_FAILURE.json')
        with patch.object(pair_stages,'fit_engine',side_effect=AssertionError('NO_REFIT_ON_RESUME')),patch.object(pair_stages,'old_joint',side_effect=AssertionError('NO_CONTROL_RESOLVE')),patch.object(pair_stages,'build_extra_bank',side_effect=AssertionError('NO_BANK_REBUILD')),patch.object(runner,'select_joint',side_effect=AssertionError('NO_RESOLVE')),patch.object(runner,'export_overlap',side_effect=AssertionError('NO_REEXPORT')):run()
        self.assertEqual(hashes,{p:sha(p) for p in hashes})
        self.assertEqual(json.loads((out/'RUN_RESULT.json').read_text())['fit_calls'],1)
    def test_mismatch_keeps_original_control_and_durable_failure(self):
        root,c,d=self.fixture(bad=True)
        with patch.object(runner,'load',return_value=d),patch.object(runner,'successful_overlaps',return_value=d['overlaps']),patch.object(runner,'renderer',side_effect=RuntimeError('DELIBERATE_NO_RENDER')):
            with self.assertRaisesRegex(RuntimeError,'DELIBERATE_NO_RENDER'):runner.run(c,root/'CONFIG.json')
        out=Path(c['unit']);result=json.loads((out/'RUN_RESULT.json').read_text());self.assertEqual(result['recovered_models'],0);self.assertEqual(result['bank_status'][0]['status'],'BLOCKED_REPRODUCTION')
        for arm in ['greedy','joint']:np.testing.assert_array_equal(np.load(out/'scenes/scan24/stages'/arm/'MEMBERSHIP.npz')['edge_id'],d['membership']['edge_id'])
    def test_parallel_and_branch_unchanged_for_new_model(self):
        from test_overlap_model import fixture
        d=fixture(2,offsets=[0.,.6]);self.assertEqual(model_group_guard(d,d['leaves'][0].q,[0,1])[1],'parallel')
        d=fixture(3);dirs=np.array([[1.,0,0],[-.5,.8660254,0],[-.5,-.8660254,0]])
        d['representatives']['x']=np.concatenate([np.array([.5,1.6,2.8])[:,None]*v for v in dirs]);d['representatives']['t']=np.repeat(dirs,3,axis=0)
        self.assertEqual(model_group_guard(d,d['leaves'][0].q,[0,1,2])[1],'branch')

if __name__=='__main__':unittest.main(verbosity=2)
