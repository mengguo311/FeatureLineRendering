"""v06-only serial CPU runtime. No old output helper is imported."""
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

OUTPUT_ROOT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06')
ACTIVE_UNIT = Path(os.environ.get('V06_UNIT_DIR', str(OUTPUT_ROOT/'units/unit_001'))).resolve()

def output_guard(path):
    path = Path(path).resolve()
    if OUTPUT_ROOT not in path.parents or OUTPUT_ROOT/'orchestration' in path.parents or path == OUTPUT_ROOT/'orchestration':
        raise ValueError('v06 output only, outside orchestration')
    if shutil.disk_usage('/').free < 2**30 or shutil.disk_usage(OUTPUT_ROOT).free < 10*2**30:
        raise RuntimeError('insufficient disk headroom')
    return path

output_guard(ACTIVE_UNIT)
os.environ['TMPDIR'] = str(ACTIVE_UNIT/'scratch')

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
