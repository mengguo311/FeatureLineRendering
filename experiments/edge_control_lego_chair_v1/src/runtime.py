"""All writes are new stage files; native inputs are read-only dependencies."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/edge_control_lego_chair_v1'
ART=ROOT/'artifacts/edge_control_lego_chair_v1'
OUT=ROOT/'out/edge_control_lego_chair_v1'
V1=Path('/home/u00134/3dgs_line/object_neighborhood_edge_control_v1/out/object_neighborhood_edge_control_v1')
PYTHON='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
for k,v in [('CUDA_VISIBLE_DEVICES','0'),('OMP_NUM_THREADS','2'),('OPENBLAS_NUM_THREADS','2'),('MKL_NUM_THREADS','2'),('PYTHONDONTWRITEBYTECODE','1')]:os.environ[k]=v
for k,v in [('TMPDIR',OUT/'tmp'),('CUDA_CACHE_PATH',OUT/'cache/cuda'),('TORCH_EXTENSIONS_DIR',OUT/'build')]:os.environ[k]=str(v)
for p in (OUT/'tmp',OUT/'logs',ART/'results'):p.mkdir(parents=True,exist_ok=True)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def atomic_json(p,v):
    p=Path(p).absolute()
    if not any(p.is_relative_to(q) for q in (ART,OUT,EXP)):raise ValueError('write outside isolated stage')
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n');os.replace(t,p)
def source_hashes():return {str(p.relative_to(ROOT)):sha(p) for p in sorted(EXP.rglob('*')) if p.is_file() and p.suffix in ('.py','.json','.sh')}
def event(unit,phase,**kw):
    v={'unit':unit,'phase':phase,'pid':os.getpid(),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw}
    atomic_json(OUT/'STATUS.json',v)
    with (OUT/'EVENTS.jsonl').open('a') as f:f.write(json.dumps(v,ensure_ascii=False)+'\n')
    print(json.dumps(v,ensure_ascii=False),flush=True)
def guard(unit,gpu=True):
    # A live foreign GPU owner is waited for, never signalled or killed.
    while True:
        common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip()).resolve()
        size=sum(p.stat().st_size for stage in (OUT,EXP,ART) for p in stage.rglob('*') if p.is_file() and not p.is_symlink())
        root=shutil.disk_usage(ROOT).free; gitfree=shutil.disk_usage(common).free
        if root<4*2**30 or gitfree<1.5*2**30 or size>16*2**30:raise RuntimeError('reserve/stage cap violated')
        uuids=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,memory.free','--format=csv,noheader'],text=True).strip().splitlines()
        u0=uuids[0].split(',')[0].strip()
        rows=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True).strip().splitlines()
        foreign=[r for r in rows if r.split(',')[0].strip()==u0 and int(r.split(',')[1])!=os.getpid()]
        v={'unit':unit,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'root_free_bytes':root,'git_free_bytes':gitfree,'stage_bytes':size,'gpu0_free':uuids[0],'foreign':foreign,'pid':os.getpid()}
        with (OUT/'logs/RESOURCE_GATE.jsonl').open('a') as f:f.write(json.dumps(v)+'\n')
        if not gpu or not foreign:return v
        event(unit,'WAIT_FOREIGN_GPU',foreign=foreign);time.sleep(15)
def result(name,v):atomic_json(ART/'results'/f'{name}.json',v)
