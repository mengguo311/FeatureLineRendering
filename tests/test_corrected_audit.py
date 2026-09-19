import tempfile,unittest
from pathlib import Path

class CorrectedAuditTests(unittest.TestCase):
    def test_interleaved_opens_preserve_allowed_and_forbidden_access(self):
        from src.corrected_audit import audit_policy
        trace='''11 openat(AT_FDCWD, "/run/ok", O_RDONLY <unfinished ...>
12 openat(AT_FDCWD, "/secret/photo", O_RDONLY <unfinished ...>
11 <... openat resumed>) = 3</run/ok>
12 <... openat resumed>) = 4</secret/photo>
13 openat(AT_FDCWD, "/dev/null", O_RDONLY <unfinished ...>
13 <... openat resumed>) = 7</dev/null<char 1:3>>
'''
        result=audit_policy(trace,dict(readonly=['/dev'],writable=['/run']),'/run')
        self.assertEqual(result['unparsed_open_lines'],[])
        self.assertEqual(result['forbidden_successes'],['/secret/photo'])
        self.assertIn('/run/ok',result['successful_paths'])
        self.assertIn('/dev/null',result['successful_paths'])
        self.assertEqual(result['resumed_open_count'],3)

    def test_incomplete_trace_is_fail_closed(self):
        from src.corrected_audit import audit_policy
        for trace in ['11 openat(AT_FDCWD, "/run/ok", O_RDONLY <unfinished ...>',
                      '12 <... openat resumed>) = 4</secret/photo>']:
            result=audit_policy(trace,dict(readonly=[],writable=['/run']),'/run')
            self.assertFalse(result['passed'])
            self.assertEqual(len(result['unparsed_open_lines']),1)

    def test_runtime_bootstrap_must_precede_policy_creation(self):
        from src.corrected_audit import bootstrap_reads_before_policy
        early='1 openat(AT_FDCWD, "/var/cache/fontconfig/x", O_RDONLY) = 3</var/cache/fontconfig/x>\n'
        policy='1 openat(AT_FDCWD, "/run/allowlist.json", O_WRONLY|O_CREAT|O_EXCL, 0666) = 3</run/allowlist.json>\n'
        self.assertTrue(bootstrap_reads_before_policy(early+policy,'/run/allowlist.json',['/var/cache/fontconfig/x']))
        self.assertFalse(bootstrap_reads_before_policy(policy+early,'/run/allowlist.json',['/var/cache/fontconfig/x']))
        self.assertFalse(bootstrap_reads_before_policy(early,'/run/allowlist.json',['/var/cache/fontconfig/x']))

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
