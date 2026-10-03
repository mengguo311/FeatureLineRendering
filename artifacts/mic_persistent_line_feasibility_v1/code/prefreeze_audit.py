#!/usr/bin/env python3
"""Read-only source byte/seal and NPY-header audit; never reads array values.

Only the explicit output beneath the standalone workspace is written. Checkpoint
files are hashed as opaque bytes: no checkpoint/model/mesh loader is called.
"""
import argparse
import ast
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import zipfile

WORKSPACE = Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/mic_fixed3d_standalone')
ARTIFACT = WORKSPACE / 'artifacts/mic_persistent_line_feasibility_v1'


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def npz_headers(path):
    """Read the magic/version/header only from each ZIP member, not its data."""
    result = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            with z.open(name) as f:
                assert f.read(6) == b'\x93NUMPY', (path, name)
                version = tuple(f.read(2))
                assert version in ((1, 0), (2, 0), (3, 0)), version
                n = struct.unpack('<H' if version == (1, 0) else '<I', f.read(2 if version == (1, 0) else 4))[0]
                assert n < (1 << 20), 'unexpectedly large NPY header'
                header = ast.literal_eval(f.read(n).decode('utf8' if version == (3, 0) else 'latin1').strip())
                result[name] = dict(header, shape=list(header['shape']))
    return result


def no_symlink_components(path):
    p = Path(path).absolute()
    return all(not q.is_symlink() for q in (p, *p.parents))


def storage_record():
    def git(*args):
        return subprocess.check_output(['git', '-C', str(WORKSPACE), *args], text=True).strip()
    common = Path(git('rev-parse', '--path-format=absolute', '--git-common-dir'))
    objects = Path(git('rev-parse', '--path-format=absolute', '--git-path', 'objects'))
    mount = json.loads(subprocess.check_output(['findmnt', '-J', '-T', str(objects), '-o', 'TARGET,SOURCE,FSTYPE'], text=True))['filesystems'][0]
    free = shutil.disk_usage(objects).free
    alternate_paths = [objects / 'info/alternates', objects / 'info/http-alternates']
    result = {
        'git_common_dir': str(common), 'git_common_dir_resolved': str(common.resolve()),
        'objectstore': str(objects), 'objectstore_resolved': str(objects.resolve()),
        'mount': mount, 'free_bytes': free, 'required_reserve_bytes': 1 << 30,
        'within_approved_workspace': common.resolve().is_relative_to(WORKSPACE) and objects.resolve().is_relative_to(WORKSPACE),
        'no_symlink_components': no_symlink_components(WORKSPACE) and no_symlink_components(common) and no_symlink_components(objects),
        'no_alternates': not any(p.exists() for p in alternate_paths) and not os.environ.get('GIT_ALTERNATE_OBJECT_DIRECTORIES'),
        'no_objectstore_environment_override': not os.environ.get('GIT_OBJECT_DIRECTORY'),
        'on_approved_hdd': mount['target'] == '/mnt/hdd1',
        'git_mutations_performed': False,
    }
    result['passed'] = all(result[k] for k in ['within_approved_workspace', 'no_symlink_components', 'no_alternates', 'no_objectstore_environment_override', 'on_approved_hdd']) and free > (1 << 30)
    return result


def run(output):
    started = time.time()
    inputs_path = ARTIFACT / 'INPUTS.json'
    inputs = json.loads(inputs_path.read_text())
    result = {
        'schema': 'mic-fixed3d-prefreeze-current-v1', 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'workspace': str(WORKSPACE), 'inputs_sha256': sha256(inputs_path),
        'pixels_decoded': False, 'array_values_inspected': False, 'scientific_algorithm_executed': False,
        'source_reads': 'Opaque byte hashing, JSON metadata and ZIP NPY headers only; no model/mesh parser.',
        'historical_lineage': 'Historical 7000 checkpoint and training snapshot references are not active inputs and are not opened.',
        'storage': storage_record(), 'errors': [], 'file_checks': [], 'sets': [],
    }
    assert result['storage']['passed'], result['storage']
    checked = {}

    def check(record):
        path = record['path']
        if path not in checked:
            try:
                p = Path(path)
                checked[path] = {'path': path, 'bytes': p.stat().st_size, 'sha256': sha256(p)}
            except Exception as e:
                result['errors'].append({'path': path, 'error': repr(e)})
                return
        actual = checked[path]
        for k in ('bytes', 'sha256'):
            if k in record and actual[k] != record[k]:
                result['errors'].append({'path': path, 'field': k, 'expected': record[k], 'actual': actual[k]})

    for record in inputs['metadata'] + inputs['interpretation_source_metadata'] + [inputs['camera_manifest'], inputs['checkpoint'], inputs['checkpoint_lock']]:
        check(record)
    manifest = json.loads(Path(inputs['camera_manifest']['path']).read_text())
    cameras = {f'{split}_{index:03d}': manifest['cameras'][str(index)] for split in ['F', 'C'] for index in manifest[split]}
    for arc_index, arc in enumerate(manifest['arcs']):
        cameras.update({f'arc{arc_index}_{i:03d}': camera for i, camera in enumerate(arc['frames'])})
    expected_keys = {key for keys in inputs['splits'].values() for key in keys}
    assert len(expected_keys) == 49 and set(cameras) == expected_keys
    native_hashes = {}
    header_count = 0
    for source in inputs['sets']:
        directory = Path(source['path'])
        for record in source['files']:
            check(record)
        seal = json.loads((directory / 'SEAL.json').read_text())
        seal_hash = checked[str(directory / 'SEAL.json')]['sha256']
        assert seal_hash == source['seal_sha256'] == (directory / 'SEAL.sha256').read_text().strip()
        assert canonical_hash(seal['context']) == source['context_sha256'] == seal['context_sha256']
        assert set(seal['files']) | {'SEAL.json', 'SEAL.sha256'} == {Path(x['path']).name for x in source['files']}
        for name, expected_hash in seal['files'].items():
            assert checked[str(directory / name)]['sha256'] == expected_hash, (directory, name)
        entry = {'kind': source['kind'], 'key': source.get('key'), 'scope': source['scope'], 'seal_verified': True}
        if source['kind'] != 'media':
            key = source['key']
            context = json.loads((directory / 'camera.json').read_text())
            camera = context['camera']
            assert context == seal['context']
            assert canonical_hash(camera) == context['camera_hash'] == source['camera_sha256']
            assert camera == cameras[key], (key, 'camera metadata mismatch')
            assert (camera['native_width'], camera['native_height']) == (800, 800)
            assert len(camera['native_K']) == 3 and all(len(row) == 3 for row in camera['native_K'])
            assert len(camera['w2c']) == 4 and all(len(row) == 4 for row in camera['w2c'])
            assert all(math.isfinite(v) for m in [camera['native_K'], camera['w2c']] for row in m for v in row)
            assert context['checkpoint_sha256'] == inputs['checkpoint']['sha256']
            assert context['scientific_parameter_hash'] == inputs['native_parameter_sha256']
            assert context['camera_manifest_sha256'] == inputs['camera_manifest']['sha256']
            assert context['render_recipe'] == inputs['native_render_recipe']
            native_hashes.setdefault(key, {})[source['kind']] = checked[str(directory / 'native.npz')]['sha256']
            entry['camera_matches_manifest'] = True
            for name, expected in inputs['native_cache_npy_headers'].items():
                if (directory / name).exists():
                    assert npz_headers(directory / name) == expected, (directory, name, 'NPY header mismatch')
                    header_count += 1
            entry['headers_match_inputs'] = True
        result['sets'].append(entry)
    assert set(native_hashes) == expected_keys
    assert all(h.get('raw') == h.get('frames') for h in native_hashes.values())
    result['file_checks'] = list(checked.values())
    result['counts'] = {
        'unique_files_hashed': len(checked), 'unique_bytes_hashed': sum(x['bytes'] for x in checked.values()),
        'sealed_sets': len(result['sets']), 'camera_count': len(cameras), 'arc_camera_count': 33,
        'raw_frame_native_hash_pairs_equal': len(native_hashes), 'npz_archives_headers_checked': header_count,
    }
    result['native_cache_npy_headers'] = inputs['native_cache_npy_headers']
    result['native_depth_convention'] = inputs['native_depth_convention']
    result['camera_convention'] = 'world-to-camera homogeneous w2c; native_K fx=fy=1111.1110311937682, cx=cy=399.5; 800x800; all declared F/C are GS TRAIN, arc interpolation is not blind evaluation.'
    result['python'] = {'executable': sys.executable, 'version': sys.version}
    versions = {}
    for name in ['numpy', 'scipy', 'opencv-python', 'Pillow', 'scikit-image', 'pytest', 'torch']:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    result['package_metadata_versions'] = versions
    result['scope_qualification'] = inputs['qualification']
    result['inputs_unchanged'] = sha256(inputs_path) == result['inputs_sha256']
    result['completed_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    result['elapsed_seconds'] = time.time() - started
    result['passed'] = not result['errors'] and result['inputs_unchanged']
    output = output.absolute()
    assert output.resolve().is_relative_to(WORKSPACE) and no_symlink_components(output.parent)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ['passed', 'counts', 'elapsed_seconds', 'errors', 'package_metadata_versions']}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ARTIFACT / 'PREFLIGHT_CURRENT.json')
    raise SystemExit(run(parser.parse_args().output))
