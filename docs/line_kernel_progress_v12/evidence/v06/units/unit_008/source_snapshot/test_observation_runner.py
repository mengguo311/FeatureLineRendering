"""12-row bounded vertical experiment: saved model adapter, no renderer/asset load."""
from runtime_io import *
import unittest
from unittest.mock import patch
from test_pair_model import recoverable
from overlap_model import select_components
from pair_delivery import export_overlap
import observation_runner as runner
import observation_stages as stages
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_006/tests')
class Vertical(unittest.TestCase):
    def fixture(self,tail=True):
        root=U/('vertical_'+str(time.time_ns()));root.mkdir();d=recoverable();d['ambiguous']=set()
        for leaf in d['leaves'].values():
            if tail:leaf.q[:,0]=[-.2,6.2];leaf.intervals=np.array([[.2,6.2]])
        names=['residual_max','residual_q95','tangent_max','vertex_turn','window_turn','supported_length','longest_run','max_gap','total_gap'];metrics=[.4,.4,0.,0.,0.,6.,6.,0.,0.]
        d['candidates']=dict(a=np.array([0]),b=np.array([1]),operation=np.array(['overlap']),reason=np.array(['accepted']),cost=np.array([.4]),metric_names=np.array(names),metrics=np.array([metrics]));d['ordered']=dict(a=np.array([0]),b=np.array([1]));d['pairs']=[(0,1)]
        nz(root/'source.npz',**d['asset']);(root/'state.txt').write_text('SYNTHETIC12');js(root/'cameras.json',dict(scan24=[dict(view='0012'),dict(view='0036')]))
        prior=root/'unit005';base=root/'unit004'
        c=dict(unit=str(root/'new'),runtime=str(U),max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00',kernel_count=12,p=1.,expected_candidate_records=1,expected_successful_overlap=1,overlap_priority_ids=[0],decision_carrier_cap=128,max_components=8,candidate_metrics='synthetic',solver=dict(per_context_seconds=5,total_seconds=10),source_files={},helper_files={},input_files={str(root/'state.txt'):sha(root/'state.txt'),str(root/'source.npz'):sha(root/'source.npz')},state=str(root/'state.txt'),membership='synthetic',gaussians=str(root/'source.npz'),cameras=str(root/'cameras.json'),views=['0012','0036'],negative_pairs=[],reference_leaf_groups={},prior_unit=str(prior),base_bank_unit=str(base),base_bank_config_sha256='base',previous_config_sha256='prior',expected_selected_pairs=1,expected_contexts=1,expected_decision_leaves=2,expected_old_hypotheses=0,expected_control_hypotheses=0)
        contexts,audit=select_components(c,d);js(prior/'selection.json',dict(contexts=contexts,audit=audit));c['prior_selection']=str(prior/'selection.json')
        model=dict(model_key=[1,0,1],seed_pair=[0,1],input_versions=[100,101],record_id=0,anchor=0,status='RECOVERED',fit_calls=1,fit_reason='accepted',metrics=dict(zip(names,metrics)),q=[[0.,.2,0],[6.,.2,0]],kind='line',cost=.4,context_id=0)
        p=prior/'scenes/scan24/models/pair_0_1';js(p/'MODEL.json',model);checkpoint(p,['MODEL.json'],'prior','PAIR_MODEL_ATTEMPT_CLOSED')
        from pair_model import build_extra_bank
        hs,rejections=build_extra_bank(d,contexts[0],[model]);self.assertEqual(len(hs),0 if tail else 1)
        for i,h in enumerate(hs):h.update(hid=i,context_id=0)
        c['expected_control_hypotheses']=len(hs)
        for path,binding in [(base,'base'),(prior,'prior')]:
            p=path/'scenes/scan24/banks/component_00000';js(p/'BANK.json',dict(status='BANK_COMPLETE',hypotheses=hs if path==prior else []));js(p/'REJECTIONS.json',rejections if path==prior else []);checkpoint(p,['BANK.json','REJECTIONS.json'],binding,'BANK')
        c['previous_arms']={}
        for ai,a in enumerate(('greedy','joint')):
            p=prior/'scenes/scan24/stages'/a;c['previous_arms'][a]=str(p);export_overlap(p,c,dict(d,next_version=1000+ai*12),[h['hid'] for h in hs],hs,[],{},'prior')
        js(root/'CONFIG.json',c);return root,c,d
    def test_checkpoint_before_later_failure_resume_never_fits(self):
        root,c,d=self.fixture()
        def run():
            with patch.object(runner,'load',return_value=d),patch.object(runner,'successful_overlaps',return_value=d['overlaps']),patch.object(runner,'renderer',side_effect=RuntimeError('DELIBERATE_NO_RENDER')),patch('pair_model.fit_engine',side_effect=AssertionError('NO_FITTING')):
                with self.assertRaisesRegex(RuntimeError,'DELIBERATE_NO_RENDER'):runner.run(c,root/'CONFIG.json')
        run();out=Path(c['unit']);result=json.loads((out/'RUN_RESULT.json').read_text());self.assertEqual(result['fit_calls'],0);self.assertTrue(result['control_replay_exact']);self.assertEqual(result['actual_saved_pngs'],[])
        for a in ('greedy','joint'):
            p=out/'scenes/scan24/stages'/a;verify_checkpoint(p,sha(root/'CONFIG.json'));m=np.load(p/'MEMBERSHIP.npz',allow_pickle=False);self.assertEqual(len(m['edge_id']),12);self.assertTrue(np.all(m['edge_id']==0))
        hashes={str(p):sha(p) for p in out.rglob('CHECKPOINT.json')};(out/'RUN_RESULT.json').rename(out/'EXPECTED_FIRST_FAILURE.json')
        with patch.object(stages,'legacy_bank',side_effect=AssertionError('NO_REPLAY_REBUILD')),patch.object(stages,'build_extra_bank',side_effect=AssertionError('NO_VARIANT_REBUILD')),patch.object(stages,'membership_for',side_effect=AssertionError('NO_CONTROL_MAPPING_REBUILD')),patch.object(runner,'select_joint',side_effect=AssertionError('NO_RESOLVE')),patch.object(runner,'export_overlap',side_effect=AssertionError('NO_REEXPORT')):run()
        self.assertEqual(hashes,{p:sha(p) for p in hashes})
    def test_nonempty_control_full_membership_and_versions(self):
        root,c,d=self.fixture(tail=False)
        with patch.object(runner,'load',return_value=d),patch.object(runner,'successful_overlaps',return_value=d['overlaps']),patch.object(runner,'renderer',side_effect=RuntimeError('DELIBERATE_NO_RENDER')):
            with self.assertRaisesRegex(RuntimeError,'DELIBERATE_NO_RENDER'):runner.run(c,root/'CONFIG.json')
        out=Path(c['unit']);rec=json.loads((out/'scenes/scan24/control_replay/full/REPLAY.json').read_text());self.assertTrue(rec['exact'])
        for arm in ('greedy','joint'):self.assertTrue(rec['arms'][arm]['all_membership_fields_exact'])
    def test_model_version_mismatch_blocks(self):
        root,c,d=self.fixture();d['leaves'][1].version+=1
        with patch.object(runner,'load',return_value=d),patch.object(runner,'successful_overlaps',return_value=d['overlaps']):
            with self.assertRaises(AssertionError):runner.run(c,root/'CONFIG.json')
        self.assertFalse((Path(c['unit'])/'scenes/scan24/stages/joint/CHECKPOINT.json').exists())
    def test_control_mapping_mismatch_blocks(self):
        root,c,d=self.fixture();d['membership']['reason_code'][0]=7
        with patch.object(runner,'load',return_value=d),patch.object(runner,'successful_overlaps',return_value=d['overlaps']):
            with self.assertRaisesRegex(AssertionError,'CONTROL_MAPPING'):runner.run(c,root/'CONFIG.json')
        self.assertFalse((Path(c['unit'])/'scenes/scan24/stages/joint/CHECKPOINT.json').exists())
if __name__=='__main__':unittest.main(verbosity=2)
