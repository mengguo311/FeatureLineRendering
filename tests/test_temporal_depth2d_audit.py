"""Audit parser contracts; these do not change frozen scientific code."""
import unittest,tempfile
from pathlib import Path
from scripts.audit_temporal_depth2d_probe import trace_audit, ROOT

class AuditBehavior(unittest.TestCase):
    def audit(self, text):
        with tempfile.TemporaryDirectory(dir=ROOT/'out/temporal_depth2d_video_probe') as tmp:
            p=Path(tmp)/'trace';p.write_text(text)
            return trace_audit(p,{'scenes':{'lego':{'files':[{'path':'/home/u00134/3dgs_line/tier1/allowed.npz'}]}}})

    def test_signals_are_not_unknown_file_syscalls(self):
        r=self.audit('10 --- SIGCHLD {si_signo=SIGCHLD, si_status=0} ---\n10 openat(AT_FDCWD, "src/temporal_depth2d.py", O_RDONLY) = 3\n')
        self.assertTrue(r['pass']);self.assertEqual(r['ignored_signal_records'],1)

    def test_reconstruct_resumed_open_and_keep_real_unknown(self):
        r=self.audit('10 openat(AT_FDCWD, "/home/u00134/3dgs_line/tier1/allowed.npz", O_RDONLY <unfinished ...>\n10 <... openat resumed>) = 3\n')
        self.assertTrue(r['pass']);self.assertEqual(len(r['scientific_unique_paths']),1)
        self.assertFalse(self.audit('10 genuinely unparsed syscall\n')['pass'])

    def test_forbidden_successful_science_read_and_write(self):
        r=self.audit('10 openat(AT_FDCWD, "/home/u00134/3dgs_line/tier1/raw_mesh.obj", O_RDONLY) = 3\n')
        self.assertFalse(r['pass']);self.assertEqual(len(r['forbidden_successful_access']),1)
        r=self.audit('10 openat(AT_FDCWD, "/home/u00134/3dgs_line/tier1/allowed.npz", O_WRONLY) = 3\n')
        self.assertFalse(r['pass']);self.assertEqual(len(r['writes_outside_worktree']),1)

    def test_denied_attempt_does_not_count_as_success(self):
        r=self.audit('10 openat(AT_FDCWD, "/home/u00134/3dgs_line/tier1/raw_mesh.obj", O_RDONLY) = -1 EACCES (Permission denied)\n')
        self.assertTrue(r['pass']);self.assertEqual(r['failed_file_syscalls'],1)

if __name__=='__main__':unittest.main()
