"""Explicit paths and CPU-only utilities for the v02 continuation."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
os.environ['TMPDIR'] = '/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/orchestration/scratch'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.sched_setaffinity(0, [0, 1])
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

WORK = Path(__file__).resolve().parents[2]
OUT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_001')
OLD = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_002')
LEGACY = WORK / 'experiments/partwise_sketch_hatching'
sys.path.insert(0, str(LEGACY))
import core
import core_walk_v2 as walker
PYTHON = '/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
FFMPEG = '/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'

def native(value):
    if isinstance(value, dict): return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [native(v) for v in value]
    if isinstance(value, np.ndarray): return native(value.tolist())
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, Path): return str(value)
    return value

def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(native(value), indent=2, ensure_ascii=False, allow_nan=False) + '\n')

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def load_strokes(path):
    a = np.load(path, allow_pickle=False)
    out = []
    for i, sid in enumerate(a['ids']):
        lo, hi = a['offsets'][i:i+2]
        out.append(dict(id=str(sid), part=int(a['parts'][i]), faces=a['faces'][lo:hi].copy(),
                        bary=a['bary'][lo:hi].copy(), ink=float(a['inks'][i]),
                        style='mixed', layer=int(str(sid).split('layer')[-1]), angle=0.))
    return out

def load_inputs():
    cfg = json.loads((WORK/'docs/partwise_sketch_hatching/round_001/PROTOCOL.json').read_text())
    cfg['widths_by_part'] = {'1': 1., '2': 1., '3': 1.}
    cfg['renderer']['supersample'] = 2
    cfg['renderer']['contour_width_px'] = .8
    cfg['renderer']['structure_width_px'] = .65
    a = np.load(OUT/'inputs/lamp_mesh.npz', allow_pickle=False)
    mesh = core.finalize_mesh(a['vertices'], a['faces'], a['parts'])
    strokes = load_strokes(OUT/'inputs/mixed.npz')
    return mesh, strokes, cfg

def check_resources():
    import shutil
    root_free = shutil.disk_usage(WORK).free
    hdd_free = shutil.disk_usage(OUT).free
    output_bytes = sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    assert root_free >= 2**30 and hdd_free >= 10*2**30 and output_bytes < 20*2**30
    return dict(root_free_bytes=root_free, hdd_free_bytes=hdd_free, output_bytes=output_bytes,
                cpu_affinity=sorted(os.sched_getaffinity(0)), numeric_threads=1, gpu=False)
