"""V2-only writes; v1 native libraries and inputs are explicitly read-only."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/object_neighborhood_edge_control_v2'
ART=ROOT/'artifacts/object_neighborhood_edge_control_v2'
OUT=ROOT/'out/object_neighborhood_edge_control_v2'
V1=Path('/home/u00134/3dgs_line/object_neighborhood_edge_control_v1')
INPUT=V1/'out/object_neighborhood_edge_control_v1'
PYTHON='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
for k,v in [('CUDA_VISIBLE_DEVICES','0'),('OMP_NUM_THREADS','2'),('OPENBLAS_NUM_THREADS','2'),('MKL_NUM_THREADS','2'),('PYTHONDONTWRITEBYTECODE','1')]:os.environ[k]=v
for k,v in [('CUDA_CACHE_PATH',OUT/'cache/cuda'),('TORCH_EXTENSIONS_DIR',OUT/'build'),('TMPDIR',OUT/'tmp')]:os.environ[k]=str(v)
(OUT/'tmp').mkdir(parents=True,exist_ok=True)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def atomic_json(p,value):
    from contracts import writable_path
    p=writable_path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n');os.replace(tmp,p)
def command(a):return subprocess.check_output(a,text=True).strip()
def source_hashes():return {str(p.relative_to(ROOT)):sha(p) for p in EXP.rglob('*') if p.is_file() and p.suffix in ('.py','.json','.sh')}
def resource_guard(gpu=True):
    common=Path(command(['git','rev-parse','--git-common-dir']))
    size=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file() and not p.is_symlink())
    root=shutil.disk_usage(ROOT).free;gitfree=shutil.disk_usage(common).free
    if root<4*2**30 or gitfree<1.5*2**30 or size>16*2**30:raise RuntimeError('disk reserve/cap violated')
    rows=command(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'])
    gpu0=command(['nvidia-smi','--query-gpu=uuid','--format=csv,noheader']).splitlines()[0]
    foreign=[r for r in rows.splitlines() if r.split(',')[0].strip()==gpu0 and int(r.split(',')[1])!=os.getpid()]
    if gpu and foreign:raise RuntimeError('GPU0 occupied; WAIT_FOREIGN_GPU')
    return {'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'root_free_bytes':root,'git_free_bytes':gitfree,'stage_bytes':size,'foreign_gpu0_count':len(foreign)}
def status(unit,phase,**kw):atomic_json(OUT/'STATUS.json',{'unit':unit,'phase':phase,'pid':os.getpid(),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw})
def result(name,value):
    atomic_json(ART/'results'/f'{name}.json',value)
    atomic_json(OUT/'results'/f'{name}.json',value)
