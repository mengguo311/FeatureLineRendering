"""Storage-continuation mutation tests. Synthetic evidence never counts as production."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from verify_multiroot import (ROOT,EXTERNAL,TART,CONT,scene_root,assert_owned_path,
    verify_owned_seal,strict_access,verify_frame_manifest,canonical)

TMP=EXTERNAL/'independent_review/tests'


def trace(path,flags='O_RDONLY',result='3',exit_line='1 +++ exited with 0 +++'):
    return f'1 openat(AT_FDCWD, "{path}", {flags}) = {result}\n{exit_line}\n'


class MultirootTests(unittest.TestCase):
    def test_explicit_root_mapping(self):
        self.assertEqual(scene_root('hotdog'),ROOT/'out/hybrid_raster_trained_models_v1/transport')
        for scene in ('materials','mic','ship'):self.assertEqual(scene_root(scene),EXTERNAL/'transport')
        for scene in ('lego','../hotdog','',None):
            with self.assertRaises(ValueError):scene_root(scene)

    def test_path_ownership_and_no_lexical_escape(self):
        self.assertEqual(assert_owned_path(EXTERNAL/'transport/frames/mic',EXTERNAL),EXTERNAL/'transport/frames/mic')
        for p in (ROOT/'out/x',EXTERNAL.parent/'elsewhere',EXTERNAL/'transport/../../escaped'):
            with self.assertRaises(ValueError):assert_owned_path(p,EXTERNAL)

    def test_symlink_parent_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TMP) as d:
            p=Path(d);(p/'real').mkdir();(p/'alias').symlink_to(p/'real',target_is_directory=True)
            with self.assertRaises(ValueError):assert_owned_path(p/'alias'/'data',EXTERNAL)

    def test_owned_seal_rejects_corrupt_context_extra_and_symlink(self):
        with tempfile.TemporaryDirectory(dir=TMP) as d:
            p=Path(d);(p/'payload').write_bytes(b'data');context={'frozen':True}
            seal={'context':context,'context_sha256':canonical(context),'files':{'payload':hashlib.sha256(b'data').hexdigest()}}
            (p/'SEAL.json').write_text(json.dumps(seal));(p/'SEAL.sha256').write_text(hashlib.sha256((p/'SEAL.json').read_bytes()).hexdigest())
            self.assertTrue(verify_owned_seal(p,EXTERNAL,context)['passed'])
            with self.assertRaises(ValueError):verify_owned_seal(p,EXTERNAL,{'frozen':False})
            (p/'extra').write_bytes(b'x')
            with self.assertRaises(ValueError):verify_owned_seal(p,EXTERNAL)
            (p/'extra').unlink();(p/'payload').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify_owned_seal(p,EXTERNAL)
            (p/'payload').unlink();(p/'outside').write_bytes(b'data');(p/'payload').symlink_to(p/'outside')
            with self.assertRaises(ValueError):verify_owned_seal(p,EXTERNAL)

    def test_normal_completed_trace_passes(self):
        result=strict_access(trace(EXTERNAL/'transport/frames/mic/a.npz','O_WRONLY|O_CREAT'))
        self.assertTrue(result['passed']);self.assertEqual(result['normal_exit_pids'],[1])

    def test_missing_nonzero_or_signal_exit_cannot_pass(self):
        for ending in ('','1 +++ exited with 1 +++','1 +++ killed by SIGTERM +++'):
            with self.subTest(ending=ending),self.assertRaises(ValueError):strict_access(trace('/etc/ld.so.cache',exit_line=ending))

    def test_old_output_and_arbitrary_repo_writes_rejected(self):
        for p in (ROOT/'out/hybrid_raster_trained_models_v1/transport/frames/hotdog/a',ROOT/'src/code.py',ROOT/'unrelated.json','/tmp/cache'):
            with self.subTest(path=p),self.assertRaises(ValueError):strict_access(trace(p,'O_WRONLY|O_CREAT'))

    def test_precise_small_metadata_writes_allowed(self):
        for p in (TART/'materials/FRAMES.json.tmp',TART/'materials/.FRAMES.json.abc123xy',TART/'.STATUS.json.kjhjks87',TART/'STATUS.json',TART.parent/'STATUS.json.tmp',CONT/'independent_review/a.json'):
            self.assertTrue(strict_access(trace(p,'O_WRONLY|O_CREAT'))['passed'])
        with self.assertRaises(ValueError):strict_access(trace(TART/'hotdog/FRAMES.json','O_WRONLY'))
        with self.assertRaises(ValueError):strict_access(trace(TART/'materials/large.npz','O_WRONLY'))

    def test_failed_forbidden_reads_still_rejected(self):
        for p in ('/home/u00134/cglib/data/full/mic/transforms_test.json','/home/u00134/cglib/data/full/mic/train/r_7.png','/any/mesh.obj'):
            for result in ('3','-1 ENOENT (No such file or directory)'):
                with self.subTest(path=p,result=result),self.assertRaises(ValueError):strict_access(trace(p,result=result))

    def test_source_alias_returned_target_rejected(self):
        p=EXTERNAL/'alias.png';source='/home/u00134/cglib/data/full/mic/train/r_7.png'
        with self.assertRaises(ValueError):strict_access(trace(p,result=f'3<{source}>'))

    def test_frozen_checkpoint_allowlist_exact(self):
        p=ROOT/'out/hybrid_raster_trained_models_v1/training/mic/checkpoint.ply'
        self.assertTrue(strict_access(trace(p),allowed_geometry=[p])['passed'])
        with self.assertRaises(ValueError):strict_access(trace(p))

    def test_unfinished_numeric_dirfd_and_malformed_rejected(self):
        for blob in ('1 openat(AT_FDCWD, "/etc/a", O_RDONLY <unfinished ...>\n1 +++ exited with 0 +++\n',
                     '1 openat(99, "a", O_RDONLY) = 3\n1 +++ exited with 0 +++\n',
                     '1 nonsense syscall\n1 +++ exited with 0 +++\n'):
            with self.assertRaises(ValueError):strict_access(blob)

    def test_open_and_creat_calls_supported(self):
        for body in (f'open("{EXTERNAL}/test", O_WRONLY|O_CREAT, 0600) = 3',f'creat("{EXTERNAL}/test", 0600) = 3'):
            self.assertTrue(strict_access('1 '+body+'\n1 +++ exited with 0 +++\n')['passed'])

    def test_complete_resumed_open_and_device_annotations(self):
        blob='1 openat(AT_FDCWD, "/dev/nvidiactl", O_RDWR <unfinished ...>\n1 <... openat resumed>) = 3</dev/nvidiactl<char 195:255>>\n1 +++ exited with 0 +++\n'
        self.assertTrue(strict_access(blob)['passed'])

    def test_qualifying_open_set_must_be_observed(self):
        with self.assertRaises(ValueError):strict_access(trace('/etc/ld.so.cache'),required_reads=['/frozen/CAMERAS.json'])
        self.assertTrue(strict_access(trace('/frozen/CAMERAS.json'),required_reads=['/frozen/CAMERAS.json'])['passed'])

    def test_frame_manifest_rejects_partial_duplicates_and_context_changes(self):
        keys=[f'F_{i:03d}' for i in (1,14,27,41,53,67,79,93)]+[f'C_{i:03d}' for i in (7,21,33,47,59,73,86,99)]+[f'arc0_{i:03d}' for i in range(33)]
        frames={k:{'seal_sha256':k,'context':{'key':k}} for k in keys}
        manifest={'scene':'mic','expected_frames':49,'actual_frames':49,'records':[dict(key=k,**v) for k,v in frames.items()],'missing':[]}
        self.assertTrue(verify_frame_manifest(manifest,'mic',frames))
        bad=json.loads(json.dumps(manifest));bad['records'].pop()
        with self.assertRaises(ValueError):verify_frame_manifest(bad,'mic',frames)
        bad=json.loads(json.dumps(manifest));bad['records'][-1]=bad['records'][0]
        with self.assertRaises(ValueError):verify_frame_manifest(bad,'mic',frames)
        bad=json.loads(json.dumps(manifest));bad['records'][0]['context']['key']='changed'
        with self.assertRaises(ValueError):verify_frame_manifest(bad,'mic',frames)


if __name__=='__main__':unittest.main()
