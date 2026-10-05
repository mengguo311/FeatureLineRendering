"""New-stage paths, atomic records and hard resource guards."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / 'experiments/object_neighborhood_edge_control_v1'
ART = ROOT / 'artifacts/object_neighborhood_edge_control_v1'
OUT = ROOT / 'out/object_neighborhood_edge_control_v1'
PYTHON = '/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(2**20), b''):
            h.update(b)
    return h.hexdigest()

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    os.replace(tmp, path)

def command(args):
    return subprocess.check_output(args, text=True).strip()

def resource_guard(gpu=True):
    """Called before build/training/native GPU allocation; never kills a job."""
    root_free = shutil.disk_usage(ROOT).free
    common = Path(command(['git', 'rev-parse', '--git-common-dir']))
    git_free = shutil.disk_usage(common).free
    size = sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file() and not p.is_symlink())
    if root_free < 4*2**30 or git_free < 1.5*2**30 or size > 16*2**30:
        raise RuntimeError(f'resource limit: root={root_free}, git={git_free}, stage={size}')
    jobs = command(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,process_name,used_memory','--format=csv,noheader'])
    gpu0 = command(['nvidia-smi','--query-gpu=uuid','--format=csv,noheader']).splitlines()[0].strip()
    if gpu:
        for row in jobs.splitlines():
            parts = [x.strip() for x in row.split(',')]
            if parts and parts[0] == gpu0 and int(parts[1]) != os.getpid():
                raise RuntimeError('GPU0 occupied by foreign job; wait and resume: ' + row)
    return {'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'root_free_bytes':root_free,'common_git_free_bytes':git_free,
            'new_stage_bytes':size,'compute_jobs':jobs}

def code_identity():
    return {'commit':command(['git','rev-parse','HEAD']),
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in EXP.rglob('*')
                            if p.is_file() and p.suffix in ('.py','.sh','.json','.yaml','.patch')}}
