"""Frozen domain and release gates for the raster evidence stage; no image loading."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS_PATH = ROOT / 'artifacts/direct_curve_global_fit_probe/INPUTS.json'
F = [1, 14, 27, 41, 53, 67, 79, 93]
C = [7, 21, 33, 47, 59, 73, 86, 99]
SCENES = ('lego', 'chair', 'drums', 'ficus')


def read_inputs():
    inputs = json.loads(INPUTS_PATH.read_text())
    if inputs['F'] != F or inputs['C'] != C:
        raise ValueError('Inherited input split differs from frozen stage protocol')
    return inputs


def frame_specs(inputs, scene, split):
    if scene not in SCENES or split not in ('F', 'C', 'arc0'):
        raise ValueError('Only frozen F/C/arc0 domains may be opened')
    data = inputs['scenes'][scene]
    if split == 'arc0':
        cameras = data['arcs'][0]['frames']
        if len(cameras) != 33:
            raise ValueError('Frozen arc0 must contain all 33 cameras')
        return [dict(scene=scene, split=split, index=i, key=f'arc0_{i:03d}', camera=cam)
                for i, cam in enumerate(cameras)]
    return [dict(scene=scene, split=split, index=i, key=f'{split}_{i:03d}',
                 camera=data['cameras'][str(i)]) for i in (F if split == 'F' else C)]


def require_evaluation_lock(root):
    """C/arc execution requires the intact normalization lock and all primary F seals."""
    from src.hybrid_raster_io import canonical_hash, hash_file, valid_seal
    path = Path(root)/'LOCK.json'
    if not path.is_file():
        raise RuntimeError('C/arc closed: primary F normalization not locked')
    lock = json.loads(path.read_text())
    if 'lock_hash' not in lock or canonical_hash({k:v for k,v in lock.items() if k != 'lock_hash'}) != lock['lock_hash']:
        raise RuntimeError('C/arc closed: invalid normalization lock hash')
    if lock.get('parameter_hash') != canonical_hash({'config':lock.get('config'), 'normalization':lock.get('normalization')}):
        raise RuntimeError('C/arc closed: parameter hash does not match normalization/config')
    expected = {(s, f'F_{i:03d}') for s in ('lego', 'chair') for i in F}
    found = {(r['scene'], r['key']) for r in lock.get('primary_F', [])}
    if found != expected or len(lock.get('primary_F', [])) != 16:
        raise RuntimeError('C/arc closed: lock does not cover exact 16 primary F frames')
    for record in lock['primary_F']:
        if record['context'].get('parameter_hash') != lock['parameter_hash'] or record['context'].get('source_hashes') != lock['config']['sources']:
            raise RuntimeError('C/arc closed: F frame context differs from locked recipe')
        frame = Path(root)/'frames'/record['scene']/record['key']
        if not valid_seal(frame, record['context']):
            raise RuntimeError(f'C/arc closed: missing F frame {frame}')
        if hash_file(frame/'SEAL.json') != record['seal_sha256']:
            raise RuntimeError(f'C/arc closed: changed F seal {frame}')
    return lock
