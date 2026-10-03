"""CPU-only storage binding checks; all fixtures live in the approved external root."""
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import storage_paths as s
import run_storage_transport as r


class StorageAdapter(unittest.TestCase):
    def test_explicit_four_scene_resolver(self):
        self.assertEqual(s.scene_root('hotdog'), s.LEGACY_OUT)
        for scene in s.NEW_SCENES:
            self.assertEqual(s.scene_root(scene), s.OUT)
            self.assertEqual(s.output_path(scene, 'frames', 'F_001'), s.OUT/'frames'/scene/'F_001')
        with self.assertRaises(ValueError): s.scene_root('lego')
        with self.assertRaises(ValueError): s.output_path('mic', '../out')
        with self.assertRaises(ValueError): s.output_path('mic', 'frames', '../hotdog')

    def test_hotdog_cannot_be_launched_again(self):
        with self.assertRaises(ValueError): s.require_new_scene('hotdog')
        self.assertEqual(s.require_new_scene('mic'), 'mic')

    def test_storage_map_is_exact_and_frozen(self):
        self.assertEqual(json.loads((s.CONT/'STORAGE_MAP.json').read_text()), s.storage_map())
        self.assertEqual(s.storage_map()['scene_roots']['hotdog'], str(s.LEGACY_OUT))
        self.assertEqual(s.storage_map()['minimum_free_bytes_each_root'], 1024**3)

    def test_external_path_ownership_and_symlink_rejection(self):
        with tempfile.TemporaryDirectory(dir=s.EXTERNAL_ROOT/'tests/storage_adapter') as d:
            base = Path(d)
            self.assertEqual(s.require_safe_output(base/'future'), base/'future')
            (base/'link').symlink_to(base, target_is_directory=True)
            with self.assertRaises(ValueError): s.require_safe_output(base/'link'/'escape')
            with self.assertRaises(PermissionError): s.require_safe_output(s.LEGACY_OUT/'new')
            with patch.object(s.os, 'getuid', return_value=os.getuid()+1):
                with self.assertRaises(PermissionError): s.require_safe_output(base/'future')

    def test_both_storage_reserves_are_mandatory(self):
        low = types.SimpleNamespace(free=1024**3-1)
        high = types.SimpleNamespace(free=3*1024**3)
        for results in [(low, high), (high, low)]:
            with patch.object(s.shutil, 'disk_usage', side_effect=results):
                with self.assertRaises(RuntimeError): s.assert_roots()

    def test_write_policy_protects_old_results_sources_and_hotdog(self):
        for path in [s.LEGACY_OUT/'new.json', s.ART/'adapters.py',
                     s.ART/'hotdog'/'FRAMES.json', s.ROOT/'README.md',
                     s.OUT/'frames'/'hotdog'/'F_001'/'rgb.png']:
            with self.assertRaises(PermissionError): s.require_write_path(path, 'mic')
        for path in [s.OUT/'frames'/'mic'/'F_001'/'rgb.png',
                     s.ART/'mic'/'FRAMES.json', s.ART/'mic'/'.FRAMES.json.fixture',
                     s.ART/'STATUS.json', s.ART.parent/'STATUS.json']:
            s.require_write_path(path, 'mic')
        with self.assertRaises(PermissionError): s.require_write_path(s.ART/'ship'/'FRAMES.json', 'mic')

    def test_write_policy_checks_both_rename_paths(self):
        callback = s.write_audit_hook('mic')
        callback('open', (str(s.OUT/'cache'/'safe'), 'w', os.O_WRONLY|os.O_CREAT))
        callback('open', (str(s.LEGACY_OUT/'read_only.json'), 'r', os.O_RDONLY))
        with self.assertRaises(PermissionError):
            callback('os.rename', (str(s.ART/'hotdog'/'FRAMES.json'), str(s.OUT/'stolen.json'), -1, -1))
        with self.assertRaises(PermissionError):
            callback('open', (str(s.ART/'adapters.py'), 'w', os.O_WRONLY))

    def test_original_source_manifest_is_enforced(self):
        runner = r.import_runner()
        record = r.verify_original_sources(runner)
        self.assertEqual(set(record['files']), {'adapters.py','run_transport.py','test_adapters.py','test_runner.py'})
        with patch.object(runner, 'hash_file', return_value='0'*64):
            with self.assertRaises(RuntimeError): r.verify_original_sources(runner)

    def test_path_binding_changes_no_scientific_or_producer_functions(self):
        runner = r.import_runner()
        names = ('make_frame','run_scene','calibrate','context_for','media','require_release')
        funcs = {name: getattr(runner, name) for name in names}
        native_fn, gpu_fn, binaries = runner.native.render_native, runner.native.gpu_guard, runner.native.NATIVE
        r.bind_paths(runner)
        self.assertEqual(runner.OUT, s.OUT)
        self.assertEqual(runner.native.STAGE, s.OUT)
        self.assertEqual(sys.modules['adapters'].OUT, s.OUT)
        self.assertEqual(runner.ROOT, s.ROOT)
        self.assertEqual(runner.ART, s.ART)
        self.assertEqual(runner.native.NATIVE, binaries)
        self.assertIs(runner.native.render_native, native_fn)
        self.assertIs(runner.native.gpu_guard, gpu_fn)
        for name in names: self.assertIs(getattr(runner, name), funcs[name])

    def test_context_keeps_truthful_original_source_identity(self):
        runner = r.import_runner(); r.bind_paths(runner)
        spec = {'scene':'mic','key':'F_001','camera':{'fixed':'camera'}}
        manifest = {'checkpoint':{'sha256':'checkpoint'}}
        heritage = {'sources':{'src/hybrid_raster_native.py':'native'}}
        with patch.object(runner, 'hash_file', side_effect=lambda path: str(path)):
            context = runner.context_for(spec, manifest, heritage, {})
        self.assertEqual(context['adapter_source_hashes']['run_transport.py'], str(s.ART/'run_transport.py'))
        self.assertEqual(context['adapter_source_hashes']['adapters.py'], str(s.ART/'adapters.py'))
        self.assertEqual(context['calibration_sha256'], str(s.OUT/'calibration/mic/CALIBRATION.json'))
        self.assertEqual(context['scientific_parameter_hash'], '6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9')

    def test_external_seal_resume_rejects_partial_and_changed_context(self):
        runner = r.import_runner()
        with tempfile.TemporaryDirectory(dir=s.EXTERNAL_ROOT/'tests/storage_adapter') as d:
            base = Path(d); stage = base/'staging'; stage.mkdir(); dest = base/'frame'
            (stage/'payload.json').write_text('{"fixed":true}\n')
            context = {'scientific_parameter_hash':runner.PARAMETER_HASH, 'original_source':'unchanged'}
            self.assertFalse(runner.valid_seal(dest, context))
            runner.seal_frame(stage, dest, context)
            self.assertTrue(runner.valid_seal(dest, context))
            with self.assertRaises(ValueError): runner.valid_seal(dest, {**context, 'original_source':'changed'})
            partial = base/'partial'; partial.mkdir(); (partial/'payload').write_text('interrupted')
            with self.assertRaises(ValueError): runner.valid_seal(partial, context)
            (dest/'payload.json').write_text('{}')
            with self.assertRaises(ValueError): runner.valid_seal(dest, context)

    def test_inherited_parameters_sources_and_build_still_verified(self):
        runner = r.import_runner(); lock, heritage = runner.inherited()
        self.assertEqual(lock['parameter_hash'], runner.PARAMETER_HASH)
        self.assertEqual(len(heritage['sources']), 6)
        self.assertEqual(heritage['sources'], lock['config']['sources'])
        self.assertEqual(heritage['native_build'], runner.native.source_hashes())

    def test_real_cpu_native_import_under_process_write_guard(self):
        code = '''import sys
sys.path.insert(0, sys.argv[1])
import run_storage_transport as r
from storage_paths import write_audit_hook
r.process_environment()
sys.addaudithook(write_audit_hook('mic'))
runner = r.import_runner()
r.verify_original_sources(runner)
r.bind_paths(runner)
runner.inherited()
import torch
print('CPU_IMPORT_GUARD_PASS')
'''
        result = subprocess.run([sys.executable,'-B','-c',code,str(HERE)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('CPU_IMPORT_GUARD_PASS', result.stdout)


if __name__ == '__main__': unittest.main(verbosity=2)
