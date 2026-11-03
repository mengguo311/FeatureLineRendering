"""Real NPZ loader, atomic artifacts, byte-level preservation audit."""
import limits
import json
import hashlib
import os
from pathlib import Path
import numpy as np

SCHEMA = {'means': (np.dtype('float64'), (3,)), 'covariance': (np.dtype('float64'), (3,3)),
          'opacity': (np.dtype('float64'), ()), 'colors': (np.dtype('float64'), (3,)),
          'primitive_id': (np.dtype('int32'), ()), 'internal_piece_id': (np.dtype('int32'), ()),
          'arc_t': (np.dtype('float64'), ())}

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def array_sha(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()

def json_safe(value):
    if isinstance(value, np.ndarray): return json_safe(value.tolist())
    if isinstance(value, np.generic): return json_safe(value.item())
    if isinstance(value, Path): return str(value)
    if isinstance(value, dict): return {str(k): json_safe(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)): return [json_safe(v) for v in value]
    return value

def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w') as f:
        json.dump(json_safe(value), f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    tmp.replace(path)

def save_npz(path, arrays):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    with tmp.open('wb') as f:
        np.savez_compressed(f, **arrays); f.flush(); os.fsync(f.fileno())
    tmp.replace(path)

def load_asset(path, guard, expected_rows=None, allow_nonfinite_geometry=False):
    guard('load_asset_begin')
    with np.load(path, allow_pickle=False) as data:
        if set(data.files) != set(SCHEMA): raise ValueError('unexpected Gaussian fields')
        a = {}
        for k in SCHEMA:
            guard('load_asset_'+k)
            a[k] = data[k].copy()
    n = len(a['means'])
    if expected_rows is not None and n != expected_rows: raise ValueError('row count mismatch')
    for k, (dtype, tail) in SCHEMA.items():
        if a[k].shape != (n,)+tail or a[k].dtype != dtype: raise ValueError('schema '+k)
        # A bad assigned group's geometry is retained and accounted locally.
        # Nongeometry/schema corruption is still a whole-input failure.
        if not (allow_nonfinite_geometry and k in ('means','covariance')) and not np.isfinite(a[k]).all():
            raise ValueError('nonfinite '+k)
    guard('load_asset_end')
    return a

def same_bytes(a, b):
    return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()

def preservation_audit(original, candidate, rows, position_only=False):
    if set(original) != set(candidate): raise ValueError('field loss')
    outside = np.ones(len(original['means']), dtype=bool); outside[rows] = False
    fields = {}
    for k in original:
        fields[k] = dict(dtype_unchanged=original[k].dtype == candidate[k].dtype,
                         shape_unchanged=original[k].shape == candidate[k].shape,
                         non_target_bitwise=same_bytes(original[k][outside], candidate[k][outside]),
                         original_sha256=array_sha(original[k]), candidate_sha256=array_sha(candidate[k]))
        if k not in ('means', 'covariance') or (position_only and k == 'covariance'):
            fields[k]['all_rows_bitwise'] = same_bytes(original[k], candidate[k])
        if not all(v for key,v in fields[k].items() if key.endswith(('unchanged','bitwise'))):
            raise ValueError('preservation failed: '+k)
    vals, vecs = np.linalg.eigh(candidate['covariance'][rows])
    if not np.isfinite(vals).all() or np.any(vals <= 0): raise ValueError('covariance not SPD')
    return dict(fields=fields, original_row_count=len(original['means']), target_count=len(rows),
                non_target_all_fields_bitwise=True, target_non_geometry_bitwise=True,
                covariance_spd=True, minimum_eigenvalue=float(vals.min()),
                changed_mean_rows=int(np.count_nonzero(np.any(original['means'][rows] != candidate['means'][rows],axis=1))),
                changed_covariance_rows=int(np.count_nonzero(np.any(original['covariance'][rows] != candidate['covariance'][rows],axis=(1,2)))))
