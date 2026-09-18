import tempfile,unittest
from pathlib import Path

class CorrectedAuditTests(unittest.TestCase):
    def test_archived_attempt_uses_its_own_trace_and_status(self):
        from src.corrected_audit import stage_record_paths
        root=Path('/run')
        for attempt in ['attempt_00_thread_contention','attempt_01_serial']:
            policy=root/'local/chair'/attempt/'F/allowlist.json'
            trace,status=stage_record_paths(root,policy,'local_chair_seed_1729_primary')
            self.assertEqual(trace,root/'setup'/attempt/'local_chair_seed_1729_primary.strace')
            self.assertEqual(status,root/'setup'/attempt/'local_chair_seed_1729_primary_exit.json')
        trace,status=stage_record_paths(root,root/'local/chair/F/allowlist.json','local_chair_seed_1729_primary')
        self.assertEqual(trace,root/'setup/local_chair_seed_1729_primary.strace')

    def test_bootstrap_metadata_does_not_authorize_other_photographs(self):
        from src.corrected_audit import audit_policy
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);out=root/'run';out.mkdir();image=root/'F.png';image.write_bytes(b'allowed')
            forbidden=root/'C.png';forbidden.write_bytes(b'forbidden');config=root/'config.json';config.write_text('{}')
            trace=f'openat(AT_FDCWD, "{image}", O_RDONLY) = 3<{image}>\nopenat(AT_FDCWD, "{config}", O_RDONLY) = 3<{config}>\nopenat(AT_FDCWD, "{forbidden}", O_RDONLY) = 3<{forbidden}>\n'
            r=audit_policy(trace,dict(readonly=[str(image)],writable=[str(out)]),out,[config])
            self.assertFalse(r['passed']);self.assertEqual(r['forbidden_successes'],[str(forbidden)])
            self.assertIn(str(config),r['bootstrap_exceptions'])

    def test_bootstrap_source_exception_requires_exact_pinned_bytes(self):
        from src.corrected_audit import verified_source_exception
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'source.py';p.write_text('x=1\n');digest=hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(verified_source_exception(p,digest),str(p))
            p.write_text('x=2\n')
            with self.assertRaises(ValueError):verified_source_exception(p,digest)
