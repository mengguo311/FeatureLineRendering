"""Audit exceptions are explicit; scene data cannot hide in runtime allowances."""
import tempfile
from pathlib import Path
import unittest
import py_compile


class AuditTests(unittest.TestCase):
    def test_bootstrap_exceptions_are_separate_from_forbidden_scene_reads(self):
        from src.multiscene_audit import audit_stage
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'output').mkdir();(root/'runtime').mkdir()
            source=root/'entry.py';source.write_text('pass\n')
            allowed=root/'F.png';allowed.write_text('allowed')
            forbidden=root/'DEV.png';forbidden.write_text('sealed')
            trace='\n'.join(f'1 openat(AT_FDCWD<{root}>, "{p}", O_RDONLY) = 3<{p}>' for p in [source,allowed,forbidden])
            result=audit_stage(trace,[str(allowed)],[str(root/'runtime')],str(root/'output'),[str(source)])
            self.assertEqual(result['forbidden_successes'],[str(forbidden)])
            self.assertEqual(result['bootstrap_exceptions'],[str(source)])
            self.assertFalse(result['passed'])
            clean=trace.splitlines()[:2]
            result=audit_stage('\n'.join(clean),[str(allowed)],[str(root/'runtime')],str(root/'output'),[str(source)])
            self.assertTrue(result['passed'])
            broken=audit_stage('1 openat(AT_FDCWD, "unknown", O_RDONLY) <unfinished ...>',[],[],str(root/'output'),[])
            self.assertFalse(broken['passed'])

    def test_bootstrap_bytecode_requires_current_header_and_equal_source(self):
        from src.multiscene_audit import bytecode_matches_source
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.py';cache=Path(tmp)/'source.pyc'
            source.write_text('value=42\n');py_compile.compile(str(source),cfile=str(cache),doraise=True)
            self.assertTrue(bytecode_matches_source(cache,source))
            source.write_text('value=43\n')
            self.assertFalse(bytecode_matches_source(cache,source))
            cache.write_bytes(b'WRONG'+cache.read_bytes()[5:])
            self.assertFalse(bytecode_matches_source(cache,source))

    def test_stale_timestamp_cache_is_disclosed_and_requires_source_fallback(self):
        from src.multiscene_audit import bytecode_status
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.py';cache=Path(tmp)/'source.pyc'
            source.write_text('value=42\n');py_compile.compile(str(source),cfile=str(cache),doraise=True)
            self.assertEqual(bytecode_status(cache,source)['status'],'SOURCE_EQUIVALENT')
            source.write_text('value=42123456\n')
            status=bytecode_status(cache,source)
            self.assertEqual(status['status'],'STALE_TIMESTAMP_CACHE')
            self.assertTrue(status['requires_observed_source_fallback'])


if __name__=='__main__':unittest.main()
