import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from acquisition_support import (read_train_metadata, patch_sources, check_resume, canonical_hash,
                                 atomic_json, gpu_guard_rows, validate_checkpoint_sidecar, audit_trace)

class AcquisitionContract(unittest.TestCase):
    def test_train_only_loader_ignores_forbidden_metadata(self):
        with tempfile.TemporaryDirectory(dir=HERE.parents[2] / 'out/hybrid_raster_trained_models_v1/training') as tmp:
            root=Path(tmp)
            (root/'transforms_train.json').write_text(json.dumps({'camera_angle_x':.69,'frames':[{'file_path':'./train/r_0','transform_matrix':[[1,0,0,0],[0,1,0,0],[0,0,1,4],[0,0,0,1]]}]}))
            (root/'transforms_test.json').write_text('DO NOT READ')
            (root/'transforms_val.json').write_text('DO NOT READ')
            value=read_train_metadata(root)
            self.assertEqual(len(value['frames']),1)
    def test_train_loader_rejects_traversal_and_nontrain(self):
        for name in ['../test/r_0','./val/r_0','/tmp/train/r_0','train/../test/r_0']:
            with tempfile.TemporaryDirectory(dir=HERE.parents[2] / 'out/hybrid_raster_trained_models_v1/training') as tmp:
                root=Path(tmp)
                (root/'transforms_train.json').write_text(json.dumps({'camera_angle_x':.69,'frames':[{'file_path':name,'transform_matrix':[[1,0,0,0],[0,1,0,0],[0,0,1,4],[0,0,0,1]]}]}))
                with self.assertRaises(ValueError): read_train_metadata(root)
    def test_seed_patch_and_no_test_read(self):
        source=Path('/home/u00134/3dgs_line/ext/gaussian-splatting')
        names=['train.py','utils/general_utils.py','scene/dataset_readers.py']
        patched=patch_sources({n:(source/n).read_text() for n in names})
        self.assertIn('safe_state(args.quiet, args.seed)',patched['train.py'])
        self.assertIn('random.seed(seed)',patched['utils/general_utils.py'])
        self.assertNotIn('readCamerasFromTransforms(path, "transforms_test.json"',patched['scene/dataset_readers.py'])
        self.assertIn('test_cam_infos = []',patched['scene/dataset_readers.py'])
        for expression in ['loss = (1.0 - opt.lambda_dssim) * Ll1 + opt.lambda_dssim * (1.0 - ssim(image, gt_image))','gaussians.densify_and_prune(opt.densify_grad_threshold, 0.005, scene.cameras_extent, size_threshold)']:
            self.assertIn(expression,patched['train.py'])
    def test_materialized_source_uses_git_pin_not_dirty_worktree(self):
        import hashlib
        import subprocess
        source=Path('/home/u00134/3dgs_line/ext/gaussian-splatting')
        manifest=json.loads((HERE/'SOURCE_MANIFEST.json').read_text())
        for row in manifest['files']:
            blob=subprocess.check_output(['git','show',manifest['commit']+':'+row['relative_path']],cwd=source)
            self.assertEqual(row['upstream_sha256'],hashlib.sha256(blob).hexdigest(),row['relative_path'])
        renderer=Path(next(row['path'] for row in manifest['files'] if row['relative_path']=='gaussian_renderer/__init__.py')).read_text()
        self.assertIn('rendered_image, radii = rasterizer(',renderer)
        self.assertNotIn('rendered_image, radii, _depth, _alpha = rasterizer(',renderer)

    def test_seed_rng_actual_cpu_determinism(self):
        import contextlib
        import io
        import random
        import numpy as np
        import torch
        from unittest.mock import patch
        source=Path('/home/u00134/3dgs_line/ext/gaussian-splatting')
        originals={n:(source/n).read_text() for n in ['train.py','utils/general_utils.py','scene/dataset_readers.py']}
        namespace={};exec(compile(patch_sources(originals)['utils/general_utils.py'],'seed_fixture','exec'),namespace)
        draws=[]
        for _ in range(2):
            with contextlib.redirect_stdout(io.StringIO()),patch.object(torch.cuda,'set_device'):
                namespace['safe_state'](True,1729)
                draws.append((random.random(),np.random.random(4),torch.rand(4)))
        self.assertEqual(draws[0][0],draws[1][0]);np.testing.assert_array_equal(draws[0][1],draws[1][1])
        self.assertTrue(torch.equal(draws[0][2],draws[1][2]))
        self.assertEqual(draws[0][0],random.Random(1729).random())

    def test_resume_identity_rejects_changed_manifest(self):
        manifest={'scene':'hotdog','seed':1729,'iterations':30000}
        sidecar={'manifest_sha256':canonical_hash(manifest),'iteration':7000,'sha256':'a'*64}
        check_resume(manifest,sidecar)
        with self.assertRaises(ValueError): check_resume(dict(manifest,seed=0),sidecar)
        with self.assertRaises(ValueError): check_resume(manifest,dict(sidecar,iteration=30001))
    def test_actual_checkpoint_resume_restores_rng_and_camera_permutation(self):
        import acquisition_runtime as runtime
        import random
        import numpy as np
        import torch
        from types import SimpleNamespace
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=HERE.parents[2] / 'out/hybrid_raster_trained_models_v1/training') as tmp:
            root=Path(tmp);model=root/'checkpoints';model.mkdir()
            manifest={'scene':'synthetic','seed':1729,'iterations':30000,'directory':str(root)}
            runtime.configure(manifest)
            cameras=[SimpleNamespace(image_name=name) for name in ['r_2','r_0','r_1']]
            scene=SimpleNamespace(model_path=str(model),train_cameras={1.0:cameras})
            scene.getTrainCameras=lambda:scene.train_cameras[1.0]
            gaussians=SimpleNamespace(capture=lambda:torch.tensor([3.,4.]))
            random.seed(1729);np.random.seed(1729);torch.manual_seed(1729)
            with patch.object(torch.cuda,'get_rng_state_all',return_value=[]):runtime.save_checkpoint(gaussians,7000,scene,[cameras[2]],.123)
            expected=(random.random(),np.random.random(),torch.rand(2))
            random.seed(0);np.random.seed(0);torch.manual_seed(0)
            loaded,iteration=runtime.load_checkpoint(model/'chkpnt7000.pth')
            scene.train_cameras[1.0]=list(reversed(cameras))
            with patch.object(torch.cuda,'set_rng_state_all'):
                stack,ema=runtime.restore_loop(str(model/'chkpnt7000.pth'),scene)
            self.assertEqual(iteration,7000);self.assertEqual(ema,.123)
            self.assertEqual([c.image_name for c in stack],['r_1'])
            self.assertEqual([c.image_name for c in scene.getTrainCameras()],['r_2','r_0','r_1'])
            self.assertEqual(random.random(),expected[0]);self.assertEqual(np.random.random(),expected[1]);self.assertTrue(torch.equal(torch.rand(2),expected[2]))
            runtime.LOSS.close()

    def test_checkpoint_sidecar_requires_hash(self):
        with tempfile.TemporaryDirectory(dir=HERE.parents[2] / 'out/hybrid_raster_trained_models_v1/training') as tmp:
            root=Path(tmp); checkpoint=root/'c.pth'; checkpoint.write_bytes(b'complete')
            sidecar={'sha256':'f'*64}
            with self.assertRaises(ValueError): validate_checkpoint_sidecar(checkpoint,sidecar)
    def test_atomic_status_no_temp_left(self):
        with tempfile.TemporaryDirectory(dir=HERE.parents[2] / 'out/hybrid_raster_trained_models_v1/training') as tmp:
            path=Path(tmp)/'STATUS.json'; atomic_json(path,{'state':'RUNNING'}); atomic_json(path,{'state':'FAILED'})
            self.assertEqual(json.loads(path.read_text())['state'],'FAILED')
            self.assertEqual(len(list(Path(tmp).iterdir())),1)
    def test_audit_allows_exact_train_landlock_handle_only(self):
        with tempfile.TemporaryDirectory(dir=HERE.parents[2] / 'out/hybrid_raster_trained_models_v1/training') as tmp:
            root=Path(tmp);trace=root/'trace.txt';data=root/'source'
            trace.write_text(f'1 openat(AT_FDCWD, "{data}/train", O_RDONLY|O_CLOEXEC|O_PATH) = 7<{data}/train>\n')
            self.assertTrue(audit_trace(trace,data)['passed'])
            trace.write_text(f'1 openat(AT_FDCWD, "{data}/test", O_RDONLY|O_CLOEXEC|O_PATH) = 7<{data}/test>\n')
            self.assertFalse(audit_trace(trace,data)['passed'])
            trace.write_text(f'1 openat(AT_FDCWD, "{data}/train", O_RDONLY) = 7<{data}/train>\n')
            self.assertFalse(audit_trace(trace,data)['passed'])

    def test_gpu_guard_rejects_selected_device_any_job(self):
        rows=[{'gpu_uuid':'GPU-A','pid':111},{'gpu_uuid':'GPU-B','pid':222}]
        with self.assertRaises(RuntimeError): gpu_guard_rows('GPU-A',rows,{222})
        with self.assertRaises(RuntimeError): gpu_guard_rows('GPU-B',rows,{222})
    def test_gpu_guard_other_device_own_jobs_allowed_foreign_denied(self):
        gpu_guard_rows('GPU-A',[{'gpu_uuid':'GPU-B','pid':222}],{222})
        with self.assertRaises(RuntimeError): gpu_guard_rows('GPU-A',[{'gpu_uuid':'GPU-B','pid':333}],{222})

if __name__=='__main__': unittest.main()
