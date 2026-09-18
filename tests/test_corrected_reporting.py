import copy,unittest


class ReportingTests(unittest.TestCase):
    def test_markdown_is_checked_against_every_scene_gate_and_total(self):
        from src.corrected_reporting import render_results,check_markdown
        scene=dict(scene='lego',eligible=True,route_a=False,route_b=True,verdict='STOP_B',invariance_scope='CONTROLLED_ONLY',query_count=256,mode_count=18,accepted_count=0,qualified_doses=9,machine=dict(G0=True,G1=False,G2_machine=False,G3=False,G4_machine=False),manual='PENDING_INDEPENDENT_REVIEW')
        result=dict(protocol=dict(config_sha256='abc',prereg_commit='fb4488e',nonblind=True),totals=dict(posteriors=8,doses=36,quality_rows=512,dose_rows=1152,eligible_scenes=1,local_arms=85,local_queries=21760,local_modes=18),scenes=[scene],scope=dict(core=dict(verdict='STOP_B'),expanded=dict(verdict='INSUFFICIENT_POSTERIOR_QUALITY')),manual='PENDING_INDEPENDENT_REVIEW',access_audit=dict(passed=True,forbidden_successes=0),limitations=['Known post-hoc correction.'])
        text=render_results(result);self.assertTrue(check_markdown(result,text))
        with self.assertRaises(ValueError):check_markdown(result,text.replace('1152','1151'))
        altered=copy.deepcopy(result);altered['scenes'][0]['machine']['G1']=True
        with self.assertRaises(ValueError):check_markdown(altered,text)

    def test_manifest_checks_content_and_exposes_missing_server_artifacts(self):
        from src.corrected_reporting import file_inventory,check_inventory
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'one.json').write_text('{}');(root/'large.npz').write_bytes(b'array')
            inventory=file_inventory(root,exclude=['MANIFEST.json']);self.assertTrue(check_inventory(root,inventory))
            (root/'large.npz').write_bytes(b'changed')
            with self.assertRaises(ValueError):check_inventory(root,inventory)
