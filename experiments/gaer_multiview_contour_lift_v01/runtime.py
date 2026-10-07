import os,sys,json,hashlib,time,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TAG='gaer_multiview_contour_lift_v01'
EXP=ROOT/'experiments'/TAG; ART=ROOT/'artifacts'/TAG; OUT=ROOT/'out'/TAG
PYTHON='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',NUMBA_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(OUT/'tmp'),XDG_CACHE_HOME=str(OUT/'cache'),NUMBA_CACHE_DIR=str(OUT/'cache/numba'),MPLCONFIGDIR=str(OUT/'cache/mpl'),CUDA_CACHE_PATH=str(OUT/'cache/cuda'),TORCH_EXTENSIONS_DIR=str(OUT/'cache/torch'))
sys.dont_write_bytecode=True
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
for p in [OUT/'tmp',OUT/'cache',ART/'seals',ART/'logs',ART/'results',ART/'tdd']:p.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def scoped(p):
 p=Path(p).resolve()
 if not any(p.is_relative_to(r) for r in (EXP,ART,OUT)):raise PermissionError(str(p))
 p.parent.mkdir(parents=True,exist_ok=True);return p
def atomic_json(p,x):
 p=scoped(p);q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n');q.replace(p)
def npz(p,**x):
 import numpy as np
 p=scoped(p);q=p.with_suffix(p.suffix+'.tmp')
 with q.open('wb') as f:np.savez_compressed(f,**x)
 q.replace(p)
def guard(unit):
 common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
 size=sum(p.stat().st_size for r in (EXP,ART,OUT) for p in r.rglob('*') if p.is_file() and not p.is_symlink())
 rec=dict(unit=unit,root_free=shutil.disk_usage(ROOT).free,git_free=shutil.disk_usage(common).free,stage_bytes=size,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
 with (ART/'logs/resources.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
 if rec['root_free']<4*2**30 or rec['git_free']<1.5*2**30 or size>=4*2**30:raise RuntimeError('stage guard')
 return rec
def seal(unit,files,result):
 guard(unit);result=dict(result,method_hashes=method_hashes());p=ART/'results'/(unit+'.json');atomic_json(p,result)
 atomic_json(ART/'seals'/(unit+'.json'),dict(unit=unit,files={str(q.relative_to(ROOT)):sha(q) for q in [p]+list(files)},utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
def resume(unit):
 p=ART/'seals'/(unit+'.json')
 if not p.exists():return False
 s=json.loads(p.read_text())
 if not all((ROOT/q).exists() and sha(ROOT/q)==h for q,h in s['files'].items()):raise RuntimeError('seal mismatch '+unit)
 result=json.loads((ART/'results'/(unit+'.json')).read_text())
 if result.get('method_hashes')!=method_hashes():raise RuntimeError('sealed producer code differs '+unit)
 return True
def method_hashes():
 names=['runtime.py','core.py','cpu_native.py','mesh_tools.py','mesh_raster.cpp','metrics.py','media_tools.py','pipeline.py']
 return {n:sha(EXP/n) for n in names if (EXP/n).exists()}
