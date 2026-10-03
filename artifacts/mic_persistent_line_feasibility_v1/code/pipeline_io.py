"""Stage-scoped frozen input loading, atomic chronology, immutable asset seals."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import numpy as np

ART = Path(__file__).resolve().parents[1]
ROOT = ART.parents[1]
OUT = ROOT / 'out' / ART.name
CFG = json.loads((ART/'CONFIG.json').read_text())
SOURCE = Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/transport')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(clean(value), indent=2, sort_keys=True, allow_nan=False)+'\n')
    os.replace(temp, path)


def event(stage, action, **kwargs):
    rec = dict(utc=utc(), stage=stage, action=action, **clean(kwargs))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'EVENTS.jsonl').open('a') as f:
        f.write(json.dumps(rec, sort_keys=True)+'\n'); f.flush(); os.fsync(f.fileno())
    write_json(ART/'STATUS.json', rec)
    return rec


def check_freeze():
    push = json.loads((ART/'PROTOCOL_PUSH.json').read_text())
    if not push['verified'] or push['protocol_commit'] != push['remote_sha']:
        raise ValueError('protocol not remote verified')
    for name, digest in push['files'].items():
        if sha(ART/name) != digest:
            raise ValueError('frozen file changed: '+name)
    return push


def assert_stage_access(stage, key):
    allowed = {'construction': CFG['construction'], 'validation': CFG['validation'],
               'render': CFG['construction']+CFG['validation']+CFG['evaluation']+
               [f"arc0_{i:03d}" for i in range(CFG['arc']['frames'])]}
    if stage not in allowed or key not in allowed[stage]:
        raise ValueError(f'forbidden stage input: {stage}/{key}')


def verify_seal(name):
    rec = json.loads((ART/name).read_text())
    for filename, digest in rec['files'].items():
        if sha(ART/filename) != digest:
            raise ValueError('broken seal: '+filename)
    return rec


def load_view(stage, key):
    assert_stage_access(stage, key)
    check_freeze()
    if stage == 'construction':
        green = json.loads((ART/'SYNTHETIC_TESTS.json').read_text())
        if green.get('green_exit_code') != 0:
            raise ValueError('synthetic calibration not GREEN')
    elif stage == 'validation':
        verify_seal('PROPOSALS_SEAL.json')
    else:
        verify_seal('ASSET_SEAL.json')
    rawdir, framedir = SOURCE/'raw/mic'/key, SOURCE/'frames/mic'/key
    camera = json.loads((rawdir/'camera.json').read_text())['camera']
    native_names = ['rgb', 'alpha', 'depth', 'median_depth', 'moment2', 'topk_depth', 'topk_w', 'topk_id']
    response_names = ['A', 'B_delta_D', 'B_delta_A']
    if stage == 'render':
        response_names.append('C')
    event(stage, 'pixel_decode_start', key=key, native_path=str(rawdir/'native.npz'),
          response_path=str(framedir/'responses.npz'), native_members=native_names,
          response_members=response_names)
    with np.load(rawdir/'native.npz', allow_pickle=False) as data:
        native = {name: data[name] for name in native_names}
    with np.load(framedir/'responses.npz', allow_pickle=False) as data:
        responses = {name: data[name] for name in response_names}
    for name, value in dict(native, **responses).items():
        if not np.isfinite(value).all():
            raise ValueError(f'nonfinite native/response {key}/{name}')
    return camera, native, responses


def geometry_arrays(paths):
    arrays = [np.asarray(p['controls_xyz'], dtype='<f8').reshape(-1, 3) for p in paths]
    controls = np.concatenate(arrays) if arrays else np.empty((0, 3), dtype='<f8')
    offsets = np.asarray([0]+list(np.cumsum([len(a) for a in arrays])), dtype='<i8')
    if not np.isfinite(controls).all():
        raise ValueError('nonfinite geometry')
    return controls, offsets


def geometry_hash(paths):
    controls, offsets = geometry_arrays(paths)
    return hashlib.sha256(controls.tobytes()+offsets.tobytes()).hexdigest()


def save_geometry_asset(stem, paths, metadata):
    controls, offsets = geometry_arrays(paths)
    record = dict(schema='mic-fixed3d-asset-v1', paths=paths,
                  geometry_sha256=geometry_hash(paths), **metadata)
    write_json(ART/(stem+'.json'), record)
    np.savez(ART/(stem+'.npz'), controls=controls, offsets=offsets)
    seal = dict(utc=utc(), geometry_sha256=record['geometry_sha256'],
                files={stem+ext: sha(ART/(stem+ext)) for ext in ['.json', '.npz']})
    write_json(ART/(stem+'_SEAL.json'), seal)
    return record, seal


def load_asset(path):
    path = Path(path)
    stem = path.stem
    seal = json.loads(path.with_name(stem+'_SEAL.json').read_text())
    for name, digest in seal['files'].items():
        if sha(path.parent/name) != digest:
            raise ValueError('broken asset seal: '+name)
    record = json.loads(path.read_text())
    controls, offsets = geometry_arrays(record['paths'])
    if geometry_hash(record['paths']) != seal['geometry_sha256'] or record['geometry_sha256'] != seal['geometry_sha256']:
        raise ValueError('geometry hash mismatch')
    with np.load(path.with_suffix('.npz'), allow_pickle=False) as data:
        if not np.array_equal(data['controls'], controls) or not np.array_equal(data['offsets'], offsets):
            raise ValueError('asset JSON/NPZ disagreement')
    return record
