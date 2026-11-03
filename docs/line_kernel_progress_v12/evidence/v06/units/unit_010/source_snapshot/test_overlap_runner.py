"""24-row vertical tests: mock source loader, refuse renderer, preserve completed mappings."""
from runtime_io import *
import unittest
from unittest.mock import patch
import test_overlap_model as fixtures
import overlap_runner as runner
from overlap_delivery import export_overlap,enrich,diagnostics
from overlap_model import build_bank,select_greedy
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_004/tests')

class VerticalTests(unittest.TestCase):
    def setup_fixture(self):
        root=U/('vertical_'+str(time.time_ns()));root.mkdir();d=fixtures.fixture();d['ambiguous']=set();d['candidates']=dict(a=np.array([a for a,b in d['pairs']]),b=np.array([b for a,b in d['pairs']]));d['ordered']=d['candidates'].copy()
        nz(root/'source.npz',**d['asset']);(root/'state.txt').write_text('SYNTHETIC24');js(root/'cameras.json',{'scan24':[dict(view='0012'),dict(view='0036')]})
        c=dict(unit=str(root),runtime=str(U),max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00',kernel_count=24,p=1.,expected_candidate_records=6,expected_successful_overlap=6,overlap_priority_ids=[0],decision_carrier_cap=128,max_components=8,candidate_metrics='synthetic',solver=dict(per_context_seconds=5,total_seconds=10),source_files={},helper_files={},input_files={str(root/'state.txt'):sha(root/'state.txt'),str(root/'source.npz'):sha(root/'source.npz')},state=str(root/'state.txt'),membership='synthetic',gaussians=str(root/'source.npz'),cameras=str(root/'cameras.json'),views=['0012','0036'],negative_pairs=[],reference_leaf_groups={'fixture':[0,1]})
        js(root/'CONFIG.json',c);js(root/'FIXTURE.json',dict(rows=24,synthetic=True,loader_mocked=True,renderer_refused=True))
        return root,c,d
    def test_checkpoint_before_later_failure(self):
        root,c,d=self.setup_fixture()
        with patch.object(runner,'load',return_value=d),patch.object(runner,'successful_overlaps',return_value=d['overlaps']),patch.object(runner,'renderer',side_effect=RuntimeError('fixture deliberate renderer refusal')):
            with self.assertRaisesRegex(RuntimeError,'deliberate'):runner.run(c,root/'CONFIG.json')
        result=json.loads((root/'RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial');self.assertEqual(result['actual_saved_pngs'],[])
        for arm in ['greedy','joint']:
            out=root/'scenes/scan24/stages'/arm;verify_checkpoint(out,sha(root/'CONFIG.json'));m=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False));self.assertTrue(np.all(m['edge_id']==0));self.assertEqual(len(m['line_kernel_id']),24)
            gs=json.loads((out/'GROUPS.json').read_text())['groups'];stats=enrich(d,gs);self.assertTrue(stats[0]['pooled_between_carriers']);self.assertEqual(stats[0]['anchor_outward_support_p'],0.)
        # Simulate interruption after closed stages but before final run-result publication.
        # Only this fresh synthetic fixture is changed; no historical output is touched.
        hashes={str(p):sha(p) for p in (root/'scenes').rglob('CHECKPOINT.json')}
        (root/'RUN_RESULT.json').rename(root/'FIRST_EXPECTED_FAILURE.json')
        with patch.object(runner,'load',return_value=d),patch.object(runner,'successful_overlaps',return_value=d['overlaps']),patch.object(runner,'build_bank',side_effect=AssertionError('bank must resume')),patch.object(runner,'select_joint',side_effect=AssertionError('solver must resume')),patch.object(runner,'export_overlap',side_effect=AssertionError('mapping must resume')),patch.object(runner,'renderer',side_effect=RuntimeError('fixture deliberate renderer refusal')):
            with self.assertRaisesRegex(RuntimeError,'deliberate'):runner.run(c,root/'CONFIG.json')
        self.assertEqual(hashes,{p:sha(p) for p in hashes})
        # Read-only checkpoint resume has exact binding and rejects corrupted files.
        out=root/'scenes/scan24/stages/greedy';self.assertTrue(runner.clean_resume(out,sha(root/'CONFIG.json'))['complete'])
        with self.assertRaises(AssertionError):runner.clean_resume(out,'wrong-binding')
        corrupt=U/('corruption_'+str(time.time_ns()));corrupt.mkdir();(corrupt/'x').write_text('closed');checkpoint(corrupt,['x'],'fixture','COMPLETE');(corrupt/'x').write_text('changed')
        with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):runner.clean_resume(corrupt,'fixture')
    def test_incomplete_stage_is_not_reused(self):
        root=U/('incomplete_'+str(time.time_ns()));root.mkdir();(root/'x').write_text('uncommitted')
        with self.assertRaisesRegex(RuntimeError,'INCOMPLETE_STAGE'):runner.clean_resume(root,'fixture')
    def test_diagnostics_both_arms_same_complete_rows_and_missing_curve(self):
        d=fixtures.fixture();hs,_=build_bank(d,dict(carriers=list(d['leaves'])),lambda:None);chosen=select_greedy(hs)
        from overlap_delivery import membership_for
        m,gs,_=membership_for(d,[h for h in hs if h['hid'] in chosen],hs)
        ctx=dict(carriers=list(d['leaves']),evidence_carriers=list(d['leaves']),incident_record_ids=list(range(6)))
        sel=diagnostics(dict(reference_leaf_groups={'x':[0,1]},negative_pairs=[]),d,dict(greedy=(m,gs),joint=(m,gs)),[ctx])
        self.assertIn('top3_different_identities',sel['missing']);self.assertIn('largest_polyline_anchor',sel['missing']);self.assertTrue(all(set(x['core_carriers'])<=set(x['evidence_carriers']) for x in sel['cases']))

if __name__=='__main__':unittest.main(verbosity=2)
