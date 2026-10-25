"""Portable delivery adapter; writes only below a new explicit CLI output root."""
import os
import sys
os.environ['CUDA_VISIBLE_DEVICES'] = ''
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'
if hasattr(os, 'sched_setaffinity'):
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
sys.dont_write_bytecode = True
from pathlib import Path
import datetime
import hashlib
import json
OUTPUT_ROOT = None

def configure_output(path):
    global OUTPUT_ROOT
    path = Path(path).expanduser().resolve()
    package = Path(__file__).resolve().parent.parent
    if path == package or path in package.parents or package/'code' == path or package/'code' in path.parents or package/'data' == path or package/'data' in path.parents:
        raise ValueError('output cannot overwrite package code/data')
    if path.exists():
        raise FileExistsError('use a NEW explicit output directory')
    path.mkdir(parents=True, exist_ok=False)
    OUTPUT_ROOT = path
    (path/'scratch').mkdir()
    os.environ['TMPDIR'] = str(path/'scratch')
    return path

def output_guard(path):
    path = Path(path).resolve()
    if OUTPUT_ROOT is None or (path != OUTPUT_ROOT and OUTPUT_ROOT not in path.parents):
        raise ValueError('writes restricted to explicit new output directory')
    return path

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    return h.hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def json_default(value):
    if hasattr(value, 'tolist'): return value.tolist()
    if hasattr(value, 'item'): return value.item()
    if isinstance(value, Path): return str(value)
    raise TypeError(type(value).__name__)

def js(path, value):
    path = output_guard(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, default=json_default)+'\n')
