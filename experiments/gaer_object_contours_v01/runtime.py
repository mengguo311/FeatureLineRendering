"""Stage-only writes, PID-only GPU ownership, reversible units and source guards."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXP=ROOT/'experiments/gaer_object_contours_v01';ART=ROOT/'artifacts/gaer_object_contours_v01';OUT=ROOT/'out/gaer_object_contours_v01'
ATTR=Path('/home/u00134/3dgs_line/gaer_attribution_buffer_v01')
CAP=Path('/home/u00134/3dgs_line/gaer_attribution_capacity_v02')
IMAGE=Path('/home/u00134/3dgs_line/image_space_edge_foundation_v1')
NATIVE=Path('/home/u00134/3dgs_line/object_neighborhood_edge_control_v1/out/object_neighborhood_edge_control_v1')
PYTHON='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
os.environ.update(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',MAX_JOBS='2',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(OUT/'tmp'),CUDA_CACHE_PATH=str(OUT/'cache/cuda'),TORCH_EXTENSIONS_DIR=str(OUT/'torch_extensions'),MPLCONFIGDIR=str(OUT/'cache/mpl'),XDG_CACHE_HOME=str(OUT/'cache'))
os.environ['PATH']=str(Path(PYTHON).parent)+':/usr/local/cuda/bin:'+os.environ.get('PATH','')
sys.dont_write_bytecode=True
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
for p in [OUT/'tmp',OUT/'logs',OUT/'cache',ART/'results',ART/'seals',ART/'downloads',ART/'tests',ART/'media',ART/'tdd']:p.mkdir(parents=True,exist_ok=True)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def scoped(p):
 p=Path(p).resolve()
 if not any(p.is_relative_to(r) for r in [EXP,ART,OUT]):raise ValueError('outside authorized stage')
 p.parent.mkdir(parents=True,exist_ok=True);return p
def audit(event,args):
 paths=[]
 if event=='open':
  p,mode,flags=args
  if isinstance(p,(str,bytes,os.PathLike)) and (flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):paths=[p]
 elif event in ['os.mkdir','os.remove','os.rmdir']:paths=[args[0]]
 elif event in ['os.rename','os.link','os.symlink']:paths=list(args[:2])
 for p in paths:
  p=Path(os.fsdecode(p)).resolve()
  if not any(p.is_relative_to(r) for r in [EXP,ART,OUT,Path('/dev')]):raise PermissionError('outside stage write denied: '+str(p))
sys.addaudithook(audit)
def atomic_json(p,obj):
 p=scoped(p);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');os.replace(tmp,p)
def npz(p,**arrays):
 import numpy as np
 p=scoped(p);tmp=p.with_suffix(p.suffix+'.tmp')
 with tmp.open('wb') as f:np.savez_compressed(f,**arrays)
 os.replace(tmp,p)
def rel(p):return str(Path(p).relative_to(ROOT))
def guard(unit,gpu=True):
 common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip());common=common if common.is_absolute() else ROOT/common
 rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True).splitlines();uuid=next(r.split(',')[1].strip() for r in rows if r.split(',')[0].strip()=='0')
 apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True).splitlines();pids=[int(r.split(',')[1]) for r in apps if r.split(',')[0].strip()==uuid]
 size=sum(p.stat().st_size for r in [EXP,ART,OUT] for p in r.rglob('*') if p.is_file() and not p.is_symlink())
 rec=dict(unit=unit,pid=os.getpid(),gpu0_pids=pids,stage_bytes=size,root_free_bytes=shutil.disk_usage(ROOT).free,git_free_bytes=shutil.disk_usage(common).free,cpu_affinity=sorted(os.sched_getaffinity(0)),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
 with (OUT/'logs/resources.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
 if rec['root_free_bytes']<4*2**30 or rec['git_free_bytes']<1.5*2**30 or size>=8*2**30:raise RuntimeError('resource reserve/cap')
 if gpu and any(p!=os.getpid() for p in pids):raise RuntimeError('foreign GPU0 PID; no overlap or kill')
 return rec

def method_hashes():return {rel(p):sha(p) for p in sorted(EXP.rglob('*')) if p.is_file() and p.suffix in ['.py','.json','.sh']}
def seal(unit,files,result,freeze):
 result=dict(result,unit=unit,protocol_sha256=sha(ART/'PROTOCOL.json'),freeze_sha256=freeze)
 p=ART/'results'/(unit+'.json');atomic_json(p,result)
 atomic_json(ART/'seals'/(unit+'.json'),dict(unit=unit,freeze_sha256=freeze,files={rel(q):sha(q) for q in [p]+files},status=result.get('status','COMPLETE')))
 return result
def resume(unit,freeze):
 p=ART/'seals'/(unit+'.json')
 if not p.exists():return None
 s=json.loads(p.read_text())
 if s['freeze_sha256']!=freeze:raise RuntimeError('unit freeze mismatch')
 for q,h in s['files'].items():
  if sha(ROOT/q)!=h:raise RuntimeError('sealed bytes changed '+q)
 print('SEALED_SKIP',unit,flush=True);return json.loads((ART/'results'/(unit+'.json')).read_text())
