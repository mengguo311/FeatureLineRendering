import tempfile,unittest
from pathlib import Path

class CorrectedAuditTests(unittest.TestCase):
    def test_bootstrap_metadata_does_not_authorize_other_photographs(self):
        from src.corrected_audit import audit_policy
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);out=root/'run';out.mkdir();image=root/'F.png';image.write_bytes(b'allowed')
            forbidden=root/'C.png';forbidden.write_bytes(b'forbidden');config=root/'config.json';config.write_text('{}')
            trace=f'openat(AT_FDCWD, "{image}", O_RDONLY) = 3<{image}>\nopenat(AT_FDCWD, "{config}", O_RDONLY) = 3<{config}>\nopenat(AT_FDCWD, "{forbidden}", O_RDONLY) = 3<{forbidden}>\n'
            r=audit_policy(trace,dict(readonly=[str(image)],writable=[str(out)]),out,[config])
            self.assertFalse(r['passed']);self.assertEqual(r['forbidden_successes'],[str(forbidden)])
            self.assertIn(str(config),r['bootstrap_exceptions'])
