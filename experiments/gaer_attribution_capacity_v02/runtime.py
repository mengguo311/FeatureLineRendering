"""Authorized stage writes, atomic seals, resource and source stability guards."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXP=ROOT/'experiments/gaer_attribution_capacity_v02';ART=ROOT/'artifacts/gaer_attribution_capacity_v02';OUT=ROOT/'out/gaer_attribution_capacity_v02'
OLD=Path('/home/u00134/3dgs_line/gaer_rgb_union_voting_v01')
ATTR=Path('/home/u00134/3dgs_line/gaer_attribution_buffer_v01')
NATIVE=Path('/home/u00134/3dgs_line/object_neighborhood_edge_control_v1/out/object_neighborhood_edge_control_v1')
SOURCE=ATTR/'out/gaer_attribution_buffer_v01/native/patched'
PYTHON='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
for k,v in dict(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',MAX_JOBS='2',PYTHONDONTWRITEBYTECODE='1',TORCH_CUDA_ARCH_LIST='8.6',CUDA_HOME='/usr/local/cuda',TMPDIR=str(OUT/'tmp'),CUDA_CACHE_PATH=str(OUT/'cache/cuda'),TORCH_EXTENSIONS_DIR=str(OUT/'torch_extensions'),MPLCONFIGDIR=str(OUT/'cache/mpl'),XDG_CACHE_HOME=str(OUT/'cache')).items():os.environ[k]=v
os.environ['PATH']=str(Path(PYTHON).parent)+':/usr/local/cuda/bin:'+os.environ.get('PATH','')
for p in (OUT/'tmp',OUT/'logs',OUT/'cache',ART/'results',ART/'seals',ART/'downloads',ART/'tests',ART/'media'):p.mkdir(parents=True,exist_ok=True)
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def scoped(p):
 p=Path(p).resolve()
 if not any(p.is_relative_to(r) for r in (EXP,ART,OUT)):raise ValueError('outside stage')
 p.parent.mkdir(parents=True,exist_ok=True);return p
 def_unused=None
def atomic_json(p,v):
 p=scoped(p);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n');os.replace(tmp,p)
def npz(p,**a):
 p=scoped(p);tmp=p.with_suffix(p.suffix+'.tmp')
 with tmp.open('wb') as f:__import__('numpy').savez_compressed(f,**a)
 os.replace(tmp,p)
def rel(p):return str(Path(p).relative_to(ROOT))
def guard(unit,gpu=True):
 common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip());common=common if common.is_absolute() else ROOT/common
 size=sum(p.stat().st_size for r in (EXP,ART,OUT) for p in r.rglob('*') if p.is_file() and not p.is_symlink())
 rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True).splitlines();uuid=next(r.split(',')[1].strip() for r in rows if r.split(',')[0].strip()=='0')
 apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True).splitlines();pids=[int(r.split(',')[1]) for r in apps if r.split(',')[0].strip()==uuid]
 rec=dict(unit=unit,pid=os.getpid(),gpu0_pids=pids,stage_bytes=size,root_free_bytes=shutil.disk_usage(ROOT).free,git_free_bytes=shutil.disk_usage(common).free,cpu_affinity=sorted(os.sched_getaffinity(0)),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
 with (OUT/'logs/resources.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
 if rec['root_free_bytes']<4*2**30 or rec['git_free_bytes']<1.5*2**30 or size>=8*2**30:raise RuntimeError('resource reserve')
 if gpu and any(p!=os.getpid() for p in pids):raise RuntimeError('foreign GPU0 PID; no overlap or kill')
 return rec

def method_hashes():return {rel(p):sha(p) for p in sorted(EXP.rglob('*')) if p.is_file() and p.suffix in ('.py','.cu','.cpp','.patch','.json','.sh')}
def sealed(unit,fn):
 guard(unit);freeze=json.loads((ART/'RUN_FREEZE.json').read_text())
 if method_hashes()!=freeze['method_hashes']:raise RuntimeError('runner source changed after RUN_FREEZE')
 if sha(ART/'PROTOCOL.json')!=freeze['protocol_sha256']:raise RuntimeError('protocol changed')
 seal=ART/'seals'/f'{unit}.json';p=ART/'results'/f'{unit}.json'
 if seal.exists():
  s=json.loads(seal.read_text())
  for q,h in s['files'].items():
   if sha(ROOT/q)!=h:raise RuntimeError('sealed bytes changed '+q)
  print('SEALED_SKIP',unit,flush=True);return json.loads(p.read_text())
 start=time.perf_counter();print('RUNNING',unit,flush=True);r=fn();r.update(unit=unit,status=r.get('status','COMPLETE'),wall_seconds=time.perf_counter()-start,protocol_sha256=freeze['protocol_sha256']);atomic_json(p,r)
 files=[p]+[ROOT/q for q in r.get('files',[])];atomic_json(seal,dict(unit=unit,protocol_sha256=freeze['protocol_sha256'],method_digest=digest(freeze['method_hashes']),status=r['status'],files={rel(q):sha(q) for q in files}));print('COMPLETE',unit,round(r['wall_seconds'],2),flush=True);return r
