"""Isolated experiment001 I/O; never import v02 common (it changes TMPDIR)."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['TMPDIR'] = '/mnt/hdd1/u00134/partwise_sketch_hatching_p2_v03/orchestration/scratch'
os.sched_setaffinity(0, [0, 1])
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import numpy as np

WORK = Path(__file__).resolve().parents[2]
ROOT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p2_v03/experiment_001')
BASE = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010')
ASSET = BASE / 'outputs/edited'
DOC = WORK / 'docs/partwise_sketch_hatching_v03'
CODE = WORK / 'experiments/partwise_sketch_hatching_v03'
PYTHON = '/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
FFMPEG = '/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
sys.path.insert(0, str(WORK))
from experiments.partwise_sketch_hatching import core

def native(x):
    if isinstance(x, dict): return {str(k): native(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)): return [native(v) for v in x]
    if isinstance(x, np.ndarray): return native(x.tolist())
    if isinstance(x, np.generic): return x.item()
    if isinstance(x, Path): return str(x)
    return x

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def output_path(path):
    p = Path(path).resolve()
    if not any(p.is_relative_to(root) for root in (ROOT, DOC, CODE)):
        raise ValueError(f'Output outside authorized roots: {p}')
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def write_json(path, value):
    p = output_path(path)
    temp = p.with_name(p.name + '.partial')
    temp.write_text(json.dumps(native(value), indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    temp.replace(p)

def update_status(stage, **kwargs):
    status = json.loads((ROOT / 'STATUS.json').read_text())
    status.update(stage=stage, updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **kwargs)
    write_json(ROOT / 'STATUS.json', status)

def resources():
    root_free = shutil.disk_usage(WORK).free
    hdd_free = shutil.disk_usage(ROOT).free
    used = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert root_free >= 2**30 and hdd_free >= 10 * 2**30 and used <= 8 * 2**30
    assert sorted(os.sched_getaffinity(0)) == [0, 1]
    return dict(root_free_bytes=root_free, hdd_free_bytes=hdd_free, output_bytes=used,
                affinity=[0, 1], numeric_threads=1, gpu=False)

def load_asset():
    manifest = json.loads((ASSET / 'asset.json').read_text())
    for key in ('mesh', 'strokes', 'config'):
        assert sha(ASSET / manifest[key]['path']) == manifest[key]['sha256']
    with np.load(ASSET / 'mesh.npz', allow_pickle=False) as data:
        mesh = core.finalize_mesh(data['vertices'], data['faces'], data['parts'])
    strokes = []
    with np.load(ASSET / 'strokes.npz', allow_pickle=False) as data:
        for i, sid in enumerate(data['ids']):
            lo, hi = data['offsets'][i:i+2]
            strokes.append(dict(id=str(sid), part=int(data['parts'][i]),
                                faces=data['faces'][lo:hi].copy(), bary=data['bary'][lo:hi].copy(),
                                ink=float(data['inks'][i])))
    return mesh, strokes, json.loads((ASSET / 'config.json').read_text())
