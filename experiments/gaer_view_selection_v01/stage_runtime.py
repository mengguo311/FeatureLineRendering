"""Only the three authorized new-stage roots receive experiment writes."""
import hashlib, json, os, shutil, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXP=ROOT/'experiments/gaer_view_selection_v01'
ART=ROOT/'artifacts/gaer_view_selection_v01'
OUT=ROOT/'out/gaer_view_selection_v01'
OLD=Path('/home/u00134/3dgs_line/gaer_attribution_buffer_v01')
PY='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
os.environ['PATH']=str(Path(PY).parent)+':/usr/local/cuda/bin:'+os.environ.get('PATH','')
for k,v in dict(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',
    MKL_NUM_THREADS='2',MAX_JOBS='2',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(OUT/'tmp'),
    CUDA_CACHE_PATH=str(OUT/'cache/cuda'),XDG_CACHE_HOME=str(OUT/'cache')).items(): os.environ[k]=v
if hasattr(os,'sched_getaffinity'): os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''): h.update(b)
    return h.hexdigest()

def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def atomic_json(p,v):
    p=Path(p).resolve()
    if not any(p.is_relative_to(r) for r in (EXP,ART,OUT)): raise ValueError('write outside new stage')
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n'); os.replace(tmp,p)

def guard(unit):
    common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
    if not common.is_absolute(): common=ROOT/common
    size=sum(p.stat().st_size for r in (EXP,ART,OUT) for p in r.rglob('*') if p.is_file() and not p.is_symlink())
    rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True).splitlines()
    uuid=next(r.split(',')[1].strip() for r in rows if r.split(',')[0].strip()=='0')
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True).splitlines()
    pids=[int(r.split(',')[1]) for r in apps if r.split(',')[0].strip()==uuid]
    rec=dict(unit=unit,pid=os.getpid(),gpu0_pids=pids,cpu_affinity=sorted(os.sched_getaffinity(0)),
        utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),stage_bytes=size,
        root_free_bytes=shutil.disk_usage(ROOT).free,git_free_bytes=shutil.disk_usage(common).free)
    with (OUT/'logs/resource_checks.jsonl').open('a') as f: f.write(json.dumps(rec)+'\n')
    if rec['root_free_bytes']<4*2**30 or rec['git_free_bytes']<1.5*2**30 or size>=8*2**30: raise RuntimeError('reserve/cap failed')
    if any(p!=os.getpid() for p in pids): raise RuntimeError('foreign GPU0 PID; no overlap or kill permitted')
    return rec
