"""Synthetic syscall traces: attribution and forbidden source-asset detection."""
import unittest
from pathlib import Path

from scripts.audit_hybrid_raster_access import parse_trace_text, audit_calls

ROOT = Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2')
CHECKPOINT = '/home/u00134/3dgs_line/tier1/out/lego/point_cloud.ply'


class AccessAuditTests(unittest.TestCase):
    def test_interleaved_unfinished_openat_and_openat2_are_paired_by_pid(self):
        trace = '\n'.join([
            '101 openat(AT_FDCWD, "/home/u00134/cglib/data/full/lego/train/r_1.png", O_RDONLY <unfinished ...>',
            '102 openat2(AT_FDCWD, "out/hybrid_raster_evidence_v2/frames/lego/C_007/rgb.png", {flags=O_RDONLY, resolve=0}, 24 <unfinished ...>',
            '102 <... openat2 resumed>) = 7',
            '101 <... openat resumed>) = 3',
            '101 +++ exited with 0 +++',
            '102 +++ exited with 0 +++',
        ])
        parsed = parse_trace_text(trace, ROOT)
        self.assertEqual(len(parsed['calls']), 2)
        self.assertFalse(parsed['unparsed'])
        self.assertFalse(parsed['pending'])
        self.assertFalse(parsed['active_pids'])
        audit = audit_calls(parsed['calls'], ROOT, {CHECKPOINT})
        self.assertEqual(len(audit['forbidden_images']), 1)
        self.assertEqual(audit['forbidden_images'][0]['pid'], 101)
        self.assertEqual(audit['forbidden_images'][0]['path'], '/home/u00134/cglib/data/full/lego/train/r_1.png')

    def test_failed_image_open_does_not_claim_a_successful_decode(self):
        parsed = parse_trace_text('55 openat(AT_FDCWD, "/data/TEST/photo.jpg", O_RDONLY) = -1 ENOENT (No such file or directory)\n55 +++ exited with 0 +++', ROOT)
        audit = audit_calls(parsed['calls'], ROOT, {CHECKPOINT})
        self.assertFalse(audit['forbidden_images'])
        self.assertEqual(audit['failed_open_count'], 1)

    def test_checkpoint_mesh_cache_and_runtime_device_have_distinct_classes(self):
        trace = '\n'.join([
            f'8 openat(AT_FDCWD, "{CHECKPOINT}", O_RDONLY) = 3',
            '8 openat(AT_FDCWD, "/assets/model.obj", O_RDONLY) = 4',
            '8 openat(AT_FDCWD, "/home/u00134/.cache/new.bin", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 5',
            '8 openat(AT_FDCWD, "/dev/nvidia0", O_RDWR|O_CLOEXEC) = 6',
            '8 openat(AT_FDCWD, "/other/DEV/image.exr", O_RDONLY) = 7',
            '8 +++ exited with 0 +++',
        ])
        audit = audit_calls(parse_trace_text(trace, ROOT)['calls'], ROOT, {CHECKPOINT})
        self.assertEqual(audit['checkpoints'][CHECKPOINT], 1)
        self.assertEqual(len(audit['mesh_assets']), 1)
        self.assertEqual(len(audit['outside_worktree_writes']), 1)
        self.assertEqual(len(audit['runtime_device_writes']), 1)
        self.assertEqual(len(audit['forbidden_images']), 1)

    def test_unresolved_dirfd_and_unfinished_calls_cannot_silently_pass(self):
        parsed = parse_trace_text('9 openat(77, "image.png", O_RDONLY) = 4\n9 openat(AT_FDCWD, "/unknown", O_RDONLY <unfinished ...>', ROOT)
        self.assertEqual(len(parsed['pending']), 1)
        self.assertIsNone(parsed['calls'][0]['path'])
        audit = audit_calls(parsed['calls'], ROOT, set())
        self.assertEqual(len(audit['unresolved_successful_opens']), 1)

    def test_known_directory_fd_and_escaped_path_are_resolved(self):
        trace = '\n'.join([
            '4 openat(AT_FDCWD, "/dataset/TEST", O_RDONLY|O_DIRECTORY) = 3',
            '4 openat(3, "line\\040detail.png", O_RDONLY) = 4',
            '4 +++ exited with 0 +++',
        ])
        parsed = parse_trace_text(trace, ROOT)
        self.assertEqual(parsed['calls'][1]['path'], '/dataset/TEST/line detail.png')
        audit = audit_calls(parsed['calls'], ROOT, set())
        self.assertEqual(len(audit['forbidden_images']), 1)


if __name__ == '__main__': unittest.main()
