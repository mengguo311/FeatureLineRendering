"""Scoped writes, resource guards and resumable, hash sealed units."""
import hashlib, json, os, shutil, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / 'experiments/edge_responsibility_lego_chair_v2'
ART = ROOT / 'artifacts/edge_responsibility_lego_chair_v2'
OUT = ROOT / 'out/edge_responsibility_lego_chair_v2'
OLD = Path('/home/u00134/3dgs_line/edge_control_lego_chair_v1')
NATIVE = Path('/home/u00134/3dgs_line/object_neighborhood_edge_control_v1/out/object_neighborhood_edge_control_v1')
PYTHON = '/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
for k, v in {'CUDA_VISIBLE_DEVICES':'0', 'OMP_NUM_THREADS':'2', 'OPENBLAS_NUM_THREADS':'2',
             'MKL_NUM_THREADS':'2', 'PYTHONDONTWRITEBYTECODE':'1',
             'TMPDIR':str(OUT/'tmp'), 'CUDA_CACHE_PATH':str(OUT/'cache/cuda'),
             'TORCH_EXTENSIONS_DIR':str(OUT/'cache/torch'), 'MPLCONFIGDIR':str(OUT/'cache/mpl'),
             'XDG_CACHE_HOME':str(OUT/'cache')}.items():
    os.environ[k] = v
for p in (OUT/'tmp', OUT/'logs', OUT/'cache', ART/'results', ART/'seals'):
    p.mkdir(parents=True, exist_ok=True)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda:f.read(2**20), b''): h.update(b)
    return h.hexdigest()

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',',':')).encode()).hexdigest()

def atomic_json(path, obj):
    path = Path(path).absolute()
    if not any(path.is_relative_to(p) for p in (EXP, ART, OUT)):
        raise ValueError('write outside authorized stage')
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    os.replace(tmp, path)

def event(unit, phase, **kw):
    obj = dict(unit=unit, phase=phase, pid=os.getpid(), utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **kw)
    atomic_json(OUT/'STATUS.json', obj)
    with (OUT/'EVENTS.jsonl').open('a') as f: f.write(json.dumps(obj, ensure_ascii=False)+'\n')
    print(json.dumps(obj, ensure_ascii=False), flush=True)

def guard(unit, gpu=True):
    common = Path(subprocess.check_output(['git','rev-parse','--git-common-dir'], cwd=ROOT, text=True).strip())
    if not common.is_absolute(): common = ROOT/common
    size = sum(p.stat().st_size for base in (EXP, ART, OUT) for p in base.rglob('*') if p.is_file() and not p.is_symlink())
    free, gitfree = shutil.disk_usage(ROOT).free, shutil.disk_usage(common).free
    if free < 4*2**30 or gitfree < 1.5*2**30 or size >= 10*2**30:
        raise RuntimeError('4GiB root/1.5GiB common Git reserve or 10GiB stage cap violated')
    # Record actual compute PID ownership before every atomic GPU unit. Never kill jobs.
    gpu_rows = subprocess.check_output(['nvidia-smi','--query-gpu=uuid,memory.free','--format=csv,noheader'], text=True).strip().splitlines()
    uid = gpu_rows[0].split(',')[0].strip()
    rows = subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'], text=True).strip().splitlines()
    owners = [int(r.split(',')[1]) for r in rows if r.split(',')[0].strip() == uid]
    foreign = [p for p in owners if p != os.getpid()]
    record = dict(unit=unit, root_free_bytes=free, common_git_free_bytes=gitfree,
                  stage_bytes=size, gpu0_pids=owners, foreign_pids=foreign, pid=os.getpid(), time=time.time())
    with (OUT/'logs/RESOURCE_GATE.jsonl').open('a') as f: f.write(json.dumps(record)+'\n')
    if gpu and foreign: raise RuntimeError('GPU0 has foreign owner; resume when available')
    return record

def source_hashes():
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(EXP.rglob('*')) if p.is_file() and p.suffix in ('.py','.json','.sh')}

def unit(name, fn, frozen_hash):
    seal = ART/'seals'/f'{name}.json'
    if seal.exists():
        prior = json.loads(seal.read_text())
        if prior['input_freeze_sha256'] != frozen_hash: raise RuntimeError('existing seal has different inputs')
        if all(sha(ROOT/p) == h for p,h in prior['outputs'].items()):
            event(name, 'SEALED_SKIP'); return json.loads((ART/'results'/f'{name}.json').read_text())
        raise RuntimeError('sealed output modified')
    event(name, 'RUNNING'); t = time.perf_counter()
    try:
        guard(name)
        obj = fn()
        obj['wall_seconds'] = time.perf_counter()-t
        result = ART/'results'/f'{name}.json'
        atomic_json(result, obj)
        outputs = [result] + [ROOT/p for p in obj.get('sealed_files', [])]
        atomic_json(seal, dict(unit=name, input_freeze_sha256=frozen_hash, seconds=obj['wall_seconds'],
                              outputs={str(p.relative_to(ROOT)):sha(p) for p in outputs}, status='COMPLETE'))
        event(name,'COMPLETE',seconds=obj['wall_seconds']); return obj
    except Exception as e:
        import traceback
        failure = dict(unit=name, status='ENGINEERING_NOT_READY', error=str(e),
                       traceback=traceback.format_exc(), seconds=time.perf_counter()-t)
        atomic_json(ART/'failures'/f'{name}_{time.time_ns()}.json', failure)
        event(name,'FAILED',error=str(e)); return failure
