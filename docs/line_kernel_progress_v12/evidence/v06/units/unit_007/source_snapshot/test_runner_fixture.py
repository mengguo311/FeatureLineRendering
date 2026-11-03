"""18-row synthetic vertical runner fixture; source loader/rendering are mocked."""
from runtime_io import *
from port_paths import Leaf,Edge
from paired_delivery import diagnostic_cases,prior_scope_receipt,render_diagnostics
from unittest.mock import patch
import unittest
import runner
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_002/tests')

class RunnerFixture(unittest.TestCase):
    def data(self):
        leaves={i:Leaf(i,i,np.arange((i-1)*6,i*6),np.arange((i-1)*3,i*3),np.array([[0.,0,0],[2.,0,0]])+[(i-1)*2.1,0,0],True,False,np.array([[0.,2.]])) for i in (1,2,3)}
        means=np.concatenate([np.linspace(x.q[0],x.q[1],6) for x in leaves.values()]);parents=np.repeat([11,12,13],6)
        asset=dict(means=means,covariance=np.tile(np.eye(3)[None],(18,1,1)),opacity=np.ones(18),primitive_id=parents)
        mid=np.arange(0,18,2);ends=np.concatenate([np.repeat(x.q[None],3,axis=0) for x in leaves.values()]);t=np.tile([1.,0,0],(18,1))
        return dict(leaves=leaves,asset=asset,p=1.,next_version=100,representatives=dict(x=means[mid],t=t[mid],mid=mid,endpoints=ends),tangents=t,membership=dict(line_kernel_id=np.arange(18),edge_id=np.array([1]*6+[-1]*12),carrier_id=np.repeat([1,2,3],6),primitive_id=parents,reason_code=np.ones(18,np.int8)),owner=np.repeat([1,2,3],6),edges=[Edge(0,1,1,2,0,.2),Edge(1,2,1,3,0,.2)],all_endpoint=[Edge(0,1,1,2,0,.2),Edge(1,2,1,3,0,.2)],pairs=[(1,2),(2,3)],ambiguous=set(),candidates=dict(a=np.array([1,2]),b=np.array([2,3])),ordered=dict(a=np.array([1,2]),b=np.array([2,3])),arrays=dict(carrier_id=np.array([1,2,3]),kind=np.array(['line']*3)))
    def test_plain_runner_saves_both_mappings_before_render_failure(self):
        root=U/('runner_fixture_'+str(time.time_ns()));root.mkdir();d=self.data()
        js(root/'SYNTHETIC_FIXTURE.json',dict(synthetic=True,rows=18,source_loader_mocked=True,renderer_never_called=True))
        nz(root/'gaussians.npz',**d['asset']);nz(root/'reference.npz',edge_id=np.array([53254]*6+[-1]*12));(root/'state.txt').write_text('synthetic fixture')
        js(root/'cameras.json',{'scan24':[{'view':'0012'},{'view':'0036'}]})
        c=dict(unit=str(root),runtime=str(U),max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00',p=1.,kernel_count=18,expected_successful_endpoints=2,expected_eligible_endpoints=2,decision_carrier_cap=128,reference_membership=str(root/'reference.npz'),seed_groups=[53254],negative_pairs=[],candidate_metrics='synthetic',input_files={str(root/'gaussians.npz'):sha(root/'gaussians.npz'),str(root/'state.txt'):sha(root/'state.txt')},helper_files={},source_files={},solver=dict(per_context_seconds=5,total_seconds=10,max_cut_rounds=32),membership='synthetic',state=str(root/'state.txt'),gaussians=str(root/'gaussians.npz'),cameras=str(root/'cameras.json'),views=['0012','0036'])
        js(root/'CONFIG.json',c)
        with patch.object(runner,'load',return_value=d),patch.object(runner,'renderer',side_effect=RuntimeError('intentional fixture render refusal')):
            with self.assertRaisesRegex(RuntimeError,'intentional fixture'):runner.run(c,root/'CONFIG.json')
        result=json.loads((root/'RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial');self.assertEqual(result['fit_calls'],0);self.assertEqual(result['actual_saved_pngs'],[])
        saved={}
        for arm in ('greedy','joint'):
            out=root/'scenes/scan24/stages'/arm;verify_checkpoint(out,sha(root/'CONFIG.json'))
            with np.load(out/'MEMBERSHIP.npz') as z:self.assertEqual(z['edge_id'].tolist(),[1]*18)
            groups=json.loads((out/'GROUPS.json').read_text())['groups'];self.assertEqual(len(groups[0]['leaves']),3);saved[arm]=({},groups)
        contexts=json.loads((root/'scenes/scan24/readiness/SELECTION.json').read_text())['contexts']
        sel=diagnostic_cases(c,d,saved,contexts,[('reference_group_53254',[1])]);self.assertEqual(len(sel['cases']),1);self.assertIn('largest_polyline_leaf_path',sel['missing'])
        self.assertEqual(sel['cases'][0]['evidence_carriers'],[1,2,3])
    def test_prior_scope_mismatch_blocks(self):
        root=U/('prior_'+str(time.time_ns()));root.mkdir();js(root/'scope.json',dict(contexts=[dict(context_id=1,eligible_edge_ids=[0,1])]))
        for arm in ('greedy','joint'):nz(root/(arm+'.npz'),record_index=np.array([0]))
        c=dict(prior_scope=str(root/'scope.json'),prior_links={a:str(root/(a+'.npz')) for a in ('greedy','joint')});ctx=[dict(context_id=0,eligible_edge_ids=[0,1])]
        self.assertEqual(prior_scope_receipt(c,dict(greedy=[0],joint=[0]),[0],ctx)['status'],'EXACT_SELECTED_LINKS_REPRODUCED')
        with self.assertRaises(AssertionError):prior_scope_receipt(c,dict(greedy=[0],joint=[1]),[0],ctx)
        self.assertEqual(prior_scope_receipt(c,dict(greedy=[],joint=[]),[],ctx)['status'],'NOT_RUN_UNPROCESSED_COMPONENT')
    def test_diagnostic_pipeline_uses_identical_complete_rows(self):
        root=U/('diagnostic_fixture_'+str(time.time_ns()));root.mkdir();d=self.data();original=d['asset']['means'].copy();calls=[]
        saved={'greedy':(dict(edge_id=np.ones(18,dtype=int)),[]),'joint':(dict(edge_id=np.full(18,-1)),[])}
        case=dict(case_id='SYNTHETIC',core_carriers=[1,2],evidence_carriers=[1,2,3],incident_record_ids=[0,1])
        def fake_render(sub,cam,background,floor):
            calls.append(sub['means'].copy());rgb=np.ones((80,100,3));rgb[30,40]=sub['colors'][0];return dict(rgb=rgb)
        images=render_diagnostics(root,{},d,saved,dict(cases=[case],missing=[]),fake_render,[{'view':'0012'}],lambda:None,'fixture')
        self.assertEqual([len(x) for x in calls],[12,12,18,18]);np.testing.assert_array_equal(calls[0],calls[1]);np.testing.assert_array_equal(calls[2],calls[3]);np.testing.assert_array_equal(original,d['asset']['means'])
        self.assertEqual(len(images['greedy']),4);self.assertEqual(len(images['joint']),4)
        receipt=json.loads((root/'scenes/scan24/diagnostics/CROPS.json').read_text());self.assertEqual(len(receipt['records']),2)
        with np.load(root/'scenes/scan24/diagnostics/SYNTHETIC_ROWS.npz') as rows:self.assertEqual(len(rows['evidence_rows']),18)

if __name__=='__main__':unittest.main(verbosity=2)
