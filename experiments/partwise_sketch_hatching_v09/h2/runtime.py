"""Serial CPU runtime. Every write is confined to a new v09 HDD output."""
import os
import sys
os.environ['CUDA_VISIBLE_DEVICES'] = ''
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
sys.dont_write_bytecode = True
from pathlib import Path
import datetime
import hashlib
import json
import shutil

ROOT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09').resolve()
OUTPUT_ROOT = None

def output_guard(path):
    path = Path(path).resolve()
    if ROOT not in path.parents or ROOT/'orchestration' == path or ROOT/'orchestration' in path.parents:
        raise ValueError('writes require a v09 HDD path outside orchestration')
    if shutil.disk_usage('/').free < 2**30 or shutil.disk_usage(ROOT).free < 10*2**30:
        raise RuntimeError('insufficient disk headroom')
    return path

def configure_output(path):
    global OUTPUT_ROOT
    path = output_guard(path)
    path.mkdir(parents=True, exist_ok=False)
    OUTPUT_ROOT = path
    (path/'scratch').mkdir()
    os.environ['TMPDIR'] = str(path/'scratch')
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
