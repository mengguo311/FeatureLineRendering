"""Small vertical saved-state and later-failure tests, all outputs in unit003/tests."""
from runtime_io import *
from port_paths import Leaf,Edge,PathOracle
from delivery import membership_for
from ambiguity_delivery import merge_membership,ambiguity_diagnostics
from paired_delivery import restore_pair
from unittest.mock import patch
import unittest
import ambiguity_runner
import test_runner_fixture as legacy_fixture
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_003/tests')
class AmbiguityDeliveryTests(unittest.TestCase):
    def make(self):
        d=legacy_fixture.RunnerFixture().data();d['edges']=[];d['ambiguous']={(1,2),(2,3)}
        d['candidates'].update(operation=np.array(['endpoint']*2),reason=np.array(['ambiguous']*2))
        pm,pg,pl=membership_for(d,[],PathOracle(d['leaves']))
        prior={a:dict(membership={k:v.copy() for k,v in pm.items()},groups=pg,lineage={'events':pl},path='synthetic_prior',selected=[]) for a in ('greedy','joint')}
        return d,prior
    def test_real_solver_vertical_checkpoint_precedes_render_failure(self):
        d,prior=self.make();root=U/('vertical_'+str(time.time_ns()));root.mkdir()
        js(root/'SYNTHETIC_FIXTURE.json',dict(rows=18,no_actual_asset_loaded=True,source_loader_mocked=True,renderer_refused=True))
        nz(root/'gaussians.npz',**d['asset']);(root/'state.txt').write_text('fixture')
        js(root/'cameras.json',{'scan24':[{'view':'0012'},{'view':'0036'}]})
        c=dict(unit=str(root),runtime=str(U),max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00',p=1.,kernel_count=18,expected_successful_endpoints=2,expected_eligible_endpoints=0,expected_ambiguity_components=1,decision_carrier_cap=128,candidate_metrics='fixture',input_files={str(root/'gaussians.npz'):sha(root/'gaussians.npz'),str(root/'state.txt'):sha(root/'state.txt')},helper_files={},source_files={},solver=dict(per_context_seconds=5,total_seconds=10,max_cut_rounds=32),membership='fixture',state=str(root/'state.txt'),gaussians=str(root/'gaussians.npz'),cameras=str(root/'cameras.json'),views=['0012','0036'],negative_pairs=[],reference_groups=[1])
        js(root/'CONFIG.json',c)
        with patch.object(ambiguity_runner,'load',return_value=d),patch.object(ambiguity_runner,'load_prior',return_value=prior),patch.object(ambiguity_runner,'renderer',side_effect=RuntimeError('intentional render refusal after mappings')):
            with self.assertRaisesRegex(RuntimeError,'intentional render refusal'):ambiguity_runner.run(c,root/'CONFIG.json')
        result=json.loads((root/'RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial');self.assertEqual(result['actual_saved_pngs'],[])
        saved={};versions=[]
        for arm in ('greedy','joint'):
            out=root/'scenes/scan24/stages'/arm;verify_checkpoint(out,sha(root/'CONFIG.json'))
            m=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False));np.testing.assert_array_equal(m['edge_id'],np.ones(18))
            gs=json.loads((out/'GROUPS.json').read_text())['groups'];versions.append(gs[0]['version']);saved[arm]=(m,gs)
        self.assertNotEqual(*versions)
        choices,receipts=restore_pair(root/'scenes/scan24/progress/component_00000',sha(root/'CONFIG.json'),0)
        self.assertEqual(choices,dict(greedy=[0,1],joint=[0,1]));self.assertEqual(receipts['joint']['status'],'certified_complete')
        with self.assertRaises(AssertionError):restore_pair(root/'scenes/scan24/progress/component_00000','wrong',0)
        contexts=json.loads((root/'scenes/scan24/readiness/SELECTION.json').read_text())['contexts']
        diag=ambiguity_diagnostics(c,d,saved,prior,contexts);self.assertIn('largest_new_polyline_leaf_path',diag['missing'])
        self.assertTrue(any('top3_new_certified_paths' in x['labels'] for x in diag['cases']))
    def test_outside_rows_and_metadata_remain_exact(self):
        d,prior=self.make();d['edges']=d['all_endpoint'];oracle=PathOracle(d['leaves'])
        # Only the first pair is a changed component; third leaf is outside.
        p=prior['greedy'];p['membership']['reason_code'][12:]=9;p['membership']['composite_version'][12:]=777
        m,gs,lineage,inside=merge_membership(d,[0],oracle,p,{1,2},1000)
        for k,v in p['membership'].items():np.testing.assert_array_equal(m[k][12:],v[12:])
        self.assertEqual(gs[0]['version'],1000);self.assertFalse(np.any(inside[12:]))
    def test_no_change_preserves_previous_groups_versions(self):
        d,prior=self.make();d['edges']=d['all_endpoint'];o=PathOracle(d['leaves'])
        pm,pg,pl=membership_for(d,[0,1],o);pg[0]['version']=777;pm['composite_version'][:]=777
        p=dict(membership=pm,groups=pg,lineage={'events':pl},path='fixture',selected=[0,1])
        m,gs,_,_=merge_membership(d,[0,1],o,p,set(),1000)
        for k,v in pm.items():np.testing.assert_array_equal(m[k],v)
        self.assertEqual(gs[0]['version'],777)
if __name__=='__main__':unittest.main(verbosity=2)
