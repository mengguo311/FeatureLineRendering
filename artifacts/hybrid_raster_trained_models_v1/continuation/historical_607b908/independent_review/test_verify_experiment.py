"""Independent mutation tests; fixtures are never production evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

from verify_experiment import (audit_access, canonical, check_counts,
    verify_camera_set, verify_freeze_chain, verify_seal, verify_source_lock)

ROOT = Path(__file__).resolve().parents[3]
TMP = ROOT/'out/hybrid_raster_trained_models_v1/independent_review/tmp'


class VerificationTests(unittest.TestCase):
    def test_zero_or_partial_counts_cannot_pass(self):
        with self.assertRaises(ValueError): check_counts({s:0 for s in ('hotdog','materials','mic','ship')})
        with self.assertRaises(ValueError): check_counts(dict(hotdog=49, materials=48, mic=49, ship=49))
        self.assertEqual(check_counts(dict(hotdog=49, materials=49, mic=49, ship=49)),196)

    def test_source_lock_mutations_rejected(self):
        recipe={'x':1}; norm={'recipe':recipe,'recipe_hash':canonical(recipe),'scales':{'x':2},'author_scale':3}
        config={'sources':{'science.py':'aaa'}}
        lock=dict(config=config,normalization=norm)
        lock['parameter_hash']=canonical(lock)
        lock['lock_hash']=canonical(lock)
        self.assertTrue(verify_source_lock(lock,{'science.py':'aaa'})['passed'])
        for field in ('scale','source','parameter','recipe'):
            bad=copy.deepcopy(lock)
            if field=='scale': bad['normalization']['scales']['x']=9
            elif field=='source': bad['config']['sources']['science.py']='bbb'
            elif field=='parameter': bad['parameter_hash']='wrong'
            else: bad['normalization']['recipe']['x']=9
            with self.subTest(field=field),self.assertRaises(ValueError): verify_source_lock(bad,{'science.py':'aaa'})

    def test_seal_detects_missing_corruption_context_and_extra(self):
        TMP.mkdir(parents=True,exist_ok=True)
        import hashlib
        with tempfile.TemporaryDirectory(dir=TMP) as d:
            p=Path(d); context={'camera':'frozen'}; (p/'data.bin').write_bytes(b'123')
            seal={'context':context,'context_sha256':canonical(context),'files':{'data.bin':hashlib.sha256(b'123').hexdigest()}}
            (p/'SEAL.json').write_text(json.dumps(seal)); (p/'SEAL.sha256').write_text(hashlib.sha256((p/'SEAL.json').read_bytes()).hexdigest())
            self.assertTrue(verify_seal(p,context)['passed'])
            with self.assertRaises(ValueError): verify_seal(p,{'camera':'changed'})
            (p/'extra.bin').write_bytes(b'x')
            with self.assertRaises(ValueError): verify_seal(p,context)
            (p/'extra.bin').unlink(); (p/'data.bin').write_bytes(b'456')
            with self.assertRaises(ValueError): verify_seal(p,context)
            (p/'data.bin').unlink()
            with self.assertRaises(ValueError): verify_seal(p,context)

    def test_freeze_chain_rejects_launch_before_push_and_arc_before_checkpoint(self):
        good=dict(protocol_pushed=1,training_launched=2,checkpoint_frozen=3,arc_frozen=4,npr_launched=5)
        self.assertTrue(verify_freeze_chain(good))
        for key,value in [('training_launched',0),('arc_frozen',2),('npr_launched',3)]:
            bad={**good,key:value}
            with self.assertRaises(ValueError): verify_freeze_chain(bad)

    def test_train_allowed_only_during_acquisition_and_diagnostic(self):
        trace='1 openat(AT_FDCWD, "/home/u00134/cglib/data/full/hotdog/train/r_7.png", O_RDONLY) = 3\n1 +++ exited with 0 +++\n'
        self.assertTrue(audit_access(trace,ROOT,'acquisition')['passed'])
        with self.assertRaises(ValueError): audit_access(trace,ROOT,'transport')
        self.assertTrue(audit_access(trace.replace('r_7','r_1'),ROOT,'diagnostic')['passed'])
        with self.assertRaises(ValueError): audit_access(trace,ROOT,'diagnostic')

    def test_forbidden_failed_attempts_and_metadata_are_not_hidden(self):
        for path in ['/home/u00134/cglib/data/full/hotdog/transforms_test.json','/home/u00134/cglib/data/full/hotdog/val/r_1.png','/assets/chair.obj']:
            for result in ('3','-1 ENOENT (No such file or directory)'):
                trace=f'1 openat(AT_FDCWD, "{path}", O_RDONLY) = {result}\n1 +++ exited with 0 +++\n'
                with self.subTest(path=path,result=result),self.assertRaises(ValueError): audit_access(trace,ROOT,'acquisition')

    def test_audit_rejects_incomplete_and_unresolved_trace(self):
        for trace in ['1 openat(AT_FDCWD, "/tmp/a", O_RDONLY <unfinished ...>\n','1 openat(99, "mystery", O_RDONLY) = 3\n1 +++ exited with 0 +++\n']:
            with self.assertRaises(ValueError): audit_access(trace,ROOT,'acquisition')

    def test_quiet_trace_requires_hash_bound_external_completion(self):
        import hashlib
        trace='1 openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY) = 3\n'
        receipt={'exit_code':0,'completed':True,'trace_sha256':hashlib.sha256(trace.encode()).hexdigest()}
        self.assertTrue(audit_access(trace,ROOT,'acquisition',completion_receipt=receipt)['passed'])
        for corrupt in ({**receipt,'exit_code':1},{**receipt,'trace_sha256':'changed'}):
            with self.assertRaises(ValueError): audit_access(trace,ROOT,'acquisition',completion_receipt=corrupt)

    def test_annotated_staged_train_symlink_is_still_a_source_image(self):
        trace=f'1 openat(AT_FDCWD, "{ROOT}/out/hybrid_raster_trained_models_v1/data/train/r_7.png", O_RDONLY) = 3</home/u00134/cglib/data/full/hotdog/train/r_7.png>\n1 +++ exited with 0 +++\n'
        self.assertTrue(audit_access(trace,ROOT,'acquisition')['passed'])
        with self.assertRaises(ValueError):audit_access(trace,ROOT,'transport')

    def test_actual_strace_nested_device_annotation_and_malformed_rejected(self):
        trace='1 openat(AT_FDCWD, "/dev/nvidiactl", O_RDWR) = 3</dev/nvidiactl<char 195:255>>\n1 +++ exited with 0 +++\n'
        self.assertTrue(audit_access(trace,ROOT,'verification')['passed'])
        for broken in (trace.replace('195:255','bad'),trace.replace('>>','>'),trace.replace('/dev/nvidiactl','/home/u00134/cglib/data/full/hotdog/transforms_test.json')):
            with self.assertRaises(ValueError):audit_access(broken,ROOT,'verification')

    def test_camera_principal_fov_and_duplicate_arc_mutations_rejected(self):
        fov=.6194058656692505; fx=400/np.tan(fov/2)
        base=dict(native_width=800,native_height=800,FoVx=fov,native_K=[[fx,0,399.5],[0,fx,399.5],[0,0,1]])
        rows=[]
        for split,indices in [('F',[1,14,27,41,53,67,79,93]),('C',[7,21,33,47,59,73,86,99]),('arc0',range(33))]:
            for i in indices:
                pose=np.eye(4); pose[0,3]=i
                rows.append(dict(split=split,key=f'{split}_{i:03d}',camera={**base,'w2c':pose.tolist()}))
        self.assertTrue(verify_camera_set(rows,fov)['passed'])
        bad=copy.deepcopy(rows); bad[0]['camera']['native_K'][0][2]=400
        with self.assertRaises(ValueError): verify_camera_set(bad,fov)
        bad=copy.deepcopy(rows); bad[-1]['camera']['w2c']=bad[-2]['camera']['w2c']
        with self.assertRaises(ValueError): verify_camera_set(bad,fov)
        with self.assertRaises(ValueError): verify_camera_set(rows,.6911112070083618)


if __name__=='__main__': unittest.main()
