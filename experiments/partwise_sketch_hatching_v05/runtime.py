"""CPU-only, serial runtime and task-local output guard."""
import os
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = ''
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
sys.dont_write_bytecode = True

from pathlib import Path
import datetime
import hashlib
import json
import shutil

OUTPUT_ROOT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05')
os.environ['TMPDIR'] = str(OUTPUT_ROOT/'units/unit_001/scratch')

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(2**20), b''):
            h.update(chunk)
    return h.hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def js(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, default=json_default) + '\n')

def json_default(value):
    if hasattr(value, 'tolist'): return value.tolist()
    if hasattr(value, 'item'): return value.item()
    if isinstance(value, Path): return str(value)
    raise TypeError(type(value).__name__)

def output_guard(path):
    path = Path(path).resolve()
    root = OUTPUT_ROOT.resolve()
    if root not in path.parents or root / 'orchestration' in path.parents:
        raise ValueError('output must be inside the new task output root, outside orchestration')
    if shutil.disk_usage('/').free < 2**30 or shutil.disk_usage(root).free < 10*2**30:
        raise RuntimeError('insufficient disk headroom')
    total = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if total >= 20*2**30:
        raise RuntimeError('task output budget exceeded')
    return path
