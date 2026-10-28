"""Delivery-only I/O boundary. Never imports or invokes scientific producers."""
import os
import sys
import json
import hashlib
import datetime
from pathlib import Path

os.environ['CUDA_VISIBLE_DEVICES'] = ''
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
sys.dont_write_bytecode = True
ROOT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09')
UNIT = ROOT / 'units/unit_005'
WORK = Path('/home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v09')
CODE = WORK / 'experiments/partwise_sketch_hatching_v09/delivery'
ROOT_FILES = {'DEMO_README_ZH.md', 'DELIVERY_STATUS.json', 'DELIVERY_CONTENTS.json'}

def guard(path):
    p = Path(path).resolve()
    if p.name == 'DECISION.json' or p == UNIT / 'ASTRA_DECISION_ZH.md':
        raise ValueError('immutable parent decision')
    if UNIT in p.parents or (p.parent == ROOT and p.name in ROOT_FILES):
        return p
    raise ValueError('unit005 delivery output only')

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    return h.hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def write(path, value):
    p = guard(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f:
        f.write(value)

def js(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
