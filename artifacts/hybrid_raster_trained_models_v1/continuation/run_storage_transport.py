"""Storage-only launcher for the byte-identical frozen NPR producer.

ROOT/ART/__file__ retain their truthful repository identities. Only destination
globals change; the original functions, scientific parameters and native builds
are neither copied nor edited. A separate binding receipt records this glue.
"""
import argparse
import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
from storage_paths import (ROOT, ART, CONT, EXTERNAL_ROOT, OUT, LEGACY_OUT,
    NEW_SCENES, MAP_PATH, assert_roots, require_new_scene, require_safe_output,
    storage_map, write_audit_hook)


def import_runner():
    sys.path.insert(0, str(ART))
    return importlib.import_module('run_transport')


def verify_original_sources(runner):
    manifest_path = ART/'SOURCE_MANIFEST.json'
    manifest = json.loads(manifest_path.read_text())
    actual = {name: runner.hash_file(ART/name) for name in manifest['files']}
    if actual != manifest['files']: raise RuntimeError('Original transport SOURCE_MANIFEST changed')
    return {'path':str(manifest_path), 'sha256':runner.hash_file(manifest_path), 'files':actual}


def require_storage_release(runner=None):
    if runner is None: runner = import_runner()
    receipt_path = CONT/'STORAGE_FREEZE.json'
    receipt = json.loads(receipt_path.read_text())
    required = [CONT/name for name in ('PROTOCOL.md','PROTOCOL.json','STORAGE_MAP.json',
        'storage_paths.py','run_storage_transport.py','test_storage_adapter.py',
        'launch_storage.py','test_launch_storage.py','independent_review/verify_multiroot.py',
        'independent_review/test_verify_multiroot.py')]
    if not {p.relative_to(ROOT).as_posix() for p in required} <= set(receipt['files']):
        raise RuntimeError('Storage release lacks required frozen protocol/path/source files')
    commit = receipt['commit']
    for relative, expected in receipt['files'].items():
        path = ROOT/relative
        if path.resolve() != path or not path.is_relative_to(ROOT): raise RuntimeError('Invalid frozen source path')
        if runner.hash_file(path) != expected: raise RuntimeError('Storage release file changed: '+relative)
        committed = subprocess.check_output(['git','show',commit+':'+relative], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != expected: raise RuntimeError('Storage file is not committed: '+relative)
    remote = subprocess.check_output(['git','ls-remote','origin','refs/heads/hybrid-raster-trained-models-v1'], cwd=ROOT, text=True).split()[0]
    subprocess.run(['git','merge-base','--is-ancestor',commit,remote], cwd=ROOT, check=True)
    if json.loads(MAP_PATH.read_text()) != storage_map(): raise RuntimeError('Frozen storage mapping differs')
    return {'path':str(receipt_path), 'sha256':runner.hash_file(receipt_path), 'commit':commit, 'verified_remote':remote}


def bind_paths(runner):
    runner.OUT = OUT
    sys.modules['adapters'].OUT = OUT
    runner.native.STAGE = OUT
    if runner.ROOT != ROOT or runner.ART != ART:
        raise RuntimeError('Original source/camera context root changed')
    if runner.native.NATIVE != runner.OLD/'out/hybrid_raster_evidence_v2/native':
        raise RuntimeError('Original native build root changed')
    return {'runner_OUT':str(runner.OUT), 'adapters_OUT':str(sys.modules['adapters'].OUT),
            'native_STAGE':str(runner.native.STAGE), 'ROOT':str(runner.ROOT),
            'ART':str(runner.ART), 'native_NATIVE':str(runner.native.NATIVE)}


def process_environment():
    destinations = {
        'TMPDIR': EXTERNAL_ROOT/'tmp', 'TMP': EXTERNAL_ROOT/'tmp', 'TEMP': EXTERNAL_ROOT/'tmp',
        'XDG_CACHE_HOME': EXTERNAL_ROOT/'cache', 'TORCH_HOME':EXTERNAL_ROOT/'cache/torch',
        'TORCH_EXTENSIONS_DIR':EXTERNAL_ROOT/'cache/torch_extensions',
        'CUDA_CACHE_PATH':EXTERNAL_ROOT/'cache/cuda', 'MPLCONFIGDIR':EXTERNAL_ROOT/'cache/matplotlib',
    }
    for name, path in destinations.items():
        require_safe_output(path).mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(path)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    import tempfile
    tempfile.tempdir = str(destinations['TMPDIR'])
    return {name:str(path) for name,path in destinations.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', required=True, choices=('render','media'))
    parser.add_argument('--scene', required=True, choices=NEW_SCENES)
    args = parser.parse_args()
    require_new_scene(args.scene)
    checks = assert_roots()
    environment = process_environment()
    sys.addaudithook(write_audit_hook(args.scene))
    runner = import_runner()
    sources = verify_original_sources(runner)
    release = require_storage_release(runner)
    binding = bind_paths(runner)
    # Qualify the unchanged six source hashes, parameters and both native builds before any GPU work.
    _, heritage = runner.inherited()
    receipt = {
        'scene':args.scene, 'phase':args.phase, 'pid':os.getpid(),
        'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **storage_map(), 'schema':'storage-binding-v1',
        'original_source_manifest':sources,
        'storage_glue_sources':{name:runner.hash_file(CONT/name) for name in ('storage_paths.py','run_storage_transport.py')},
        'storage_map':{'path':str(MAP_PATH),'sha256':runner.hash_file(MAP_PATH)},
        'storage_release':release, 'storage_checks':checks, 'binding':binding,
        'process_environment':environment, 'scientific_heritage':heritage,
        'write_guard':'Python audit write restriction plus independent syscall trace for actual native/child processes',
        'unchanged_functions':{name:{'co_filename':getattr(runner,name).__code__.co_filename,
                              'source_sha256':runner.hash_file(getattr(runner,name).__code__.co_filename)}
                              for name in ('make_frame','run_scene','calibrate','context_for','media','require_release')},
    }
    path = OUT/'bindings'/f'{args.scene}_{args.phase}_{os.getpid()}.json'
    require_safe_output(path)
    runner.atomic_json(path, receipt)
    print(json.dumps({'storage_binding_receipt':str(path),'sha256':runner.hash_file(path)}), flush=True)
    # Main's parser sees the same phase and scene; all original calibration/seal/resume checks run.
    runner.main()


if __name__ == '__main__': main()
