"""Unit003-only CPU/runtime adapter; historical runtimes are never imported."""
import os,sys,json,hashlib,datetime,shutil
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']=''
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[key]='1'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
VENDOR=HERE.parent/'vendor'
sys.path.insert(1,str(VENDOR))
OUTPUT_ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07')
ACTIVE_UNIT=OUTPUT_ROOT/'units/unit_003'
os.environ['TMPDIR']=str(ACTIVE_UNIT/'scratch')
os.environ['XDG_CACHE_HOME']=str(OUTPUT_ROOT/'cache')
def output_guard(path):
    path=Path(path).resolve()
    if ACTIVE_UNIT not in path.parents: raise ValueError('unit003 output only')
    if shutil.disk_usage('/').free<2**30 or shutil.disk_usage(OUTPUT_ROOT).free<10*2**30: raise RuntimeError('disk headroom')
    return path
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(2**20),b''): h.update(block)
    return h.hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def json_default(x):
    if hasattr(x,'tolist'): return x.tolist()
    if isinstance(x,Path): return str(x)
    raise TypeError(type(x).__name__)
def js(path,value):
    path=output_guard(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=json_default,allow_nan=False)+'\n')
