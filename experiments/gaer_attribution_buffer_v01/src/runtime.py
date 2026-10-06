"""Scoped writes, resource checks and read-only dependency discovery."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / 'experiments/gaer_attribution_buffer_v01'
ART = ROOT / 'artifacts/gaer_attribution_buffer_v01'
OUT = ROOT / 'out/gaer_attribution_buffer_v01'
PYTHON = '/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
os.environ['PATH'] = str(Path(PYTHON).parent) + ':/usr/local/cuda/bin:' + os.environ.get('PATH', '')
for key, value in dict(CUDA_VISIBLE_DEVICES='0', OMP_NUM_THREADS='2',
                       OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2', MAX_JOBS='2',
                       PYTHONDONTWRITEBYTECODE='1', TORCH_CUDA_ARCH_LIST='8.6',
                       CUDA_HOME='/usr/local/cuda', TMPDIR=str(OUT / 'tmp'),
                       CUDA_CACHE_PATH=str(OUT / 'cache/cuda'),
                       TORCH_EXTENSIONS_DIR=str(OUT / 'torch_extensions'),
                       XDG_CACHE_HOME=str(OUT / 'cache')).items():
    os.environ[key] = value
for p in [OUT / 'tmp', OUT / 'logs', OUT / 'cache/cuda', OUT / 'torch_extensions']:
    p.mkdir(parents=True, exist_ok=True)
if hasattr(os, 'sched_getaffinity'):
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(2**20), b''):
            h.update(b)
    return h.hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def scoped(path):
    p = Path(path).resolve()
    if not any(p.is_relative_to(r) for r in (EXP, ART, OUT)):
        raise ValueError('write outside authorized stage: ' + str(p))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def atomic_json(path, value):
    p = scoped(path)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    os.replace(tmp, p)

def source_hashes():
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(EXP.rglob('*'))
            if p.is_file() and p.suffix in ('.py', '.json', '.sh', '.patch', '.md')}

def guard(unit, gpu=True):
    common = Path(subprocess.check_output(['git', 'rev-parse', '--git-common-dir'], cwd=ROOT, text=True).strip())
    if not common.is_absolute():
        common = ROOT / common
    size = sum(p.stat().st_size for r in (EXP, ART, OUT) for p in r.rglob('*')
               if p.is_file() and not p.is_symlink())
    free, gitfree = shutil.disk_usage(ROOT).free, shutil.disk_usage(common).free
    rows = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid', '--format=csv,noheader'], text=True).splitlines()
    uuid = next(r.split(',')[1].strip() for r in rows if r.split(',')[0].strip() == '0')
    apps = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'], text=True).splitlines()
    pids = [int(r.split(',')[1]) for r in apps if r.split(',')[0].strip() == uuid]
    record = dict(unit=unit, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  pid=os.getpid(), root_free_bytes=free, common_git_free_bytes=gitfree,
                  stage_bytes=size, gpu0_pids=pids, cpu_affinity=sorted(os.sched_getaffinity(0)))
    with (OUT / 'logs/resource_checks.jsonl').open('a') as f:
        f.write(json.dumps(record) + '\n')
    if free < 4 * 2**30 or gitfree < 1.5 * 2**30 or size >= 5 * 2**30:
        raise RuntimeError('4GiB root / 1.5GiB common Git reserve / 5GiB stage cap')
    if gpu and any(p != os.getpid() for p in pids):
        raise RuntimeError('GPU0 occupied by another process; no job will be terminated')
    return record

def discover_native():
    # Parse literals; importing old runtime would create files in a protected root.
    parent = Path('/home/u00134/3dgs_line/image_space_edge_foundation_v1')
    path = parent / 'experiments/edge_responsibility_lego_chair_v2/src/runtime.py'
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'NATIVE' for t in node.targets):
            return Path(ast.literal_eval(node.value.args[0]))
    raise RuntimeError('actual adapter dependency was not discovered')

NATIVE = discover_native()
SOURCE = NATIVE / 'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization'
DATA_FREEZE = ROOT / 'artifacts/edge_control_lego_chair_v1/DATA_FREEZE.json'
