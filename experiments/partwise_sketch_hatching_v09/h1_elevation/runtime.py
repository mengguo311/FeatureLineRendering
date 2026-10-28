"""Unit004-only output guard; frozen inherited code is never executed as a CLI."""
import os,sys,json,hashlib,datetime,shutil
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']=''
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
sys.dont_write_bytecode=True
ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_004')
CODE=Path(__file__).resolve().parent
BASECODE=ROOT/'source/base'
sys.path.append(str(BASECODE))
def output_guard(path):
    path=Path(path).resolve()
    if path!=ROOT and ROOT not in path.parents:raise ValueError('unit004 output required')
    if path.name=='DECISION.json':raise ValueError('immutable parent decision')
    if shutil.disk_usage('/').free<2**30 or shutil.disk_usage(ROOT).free<10*2**30:raise RuntimeError('disk reserve')
    return path
def configure_output(path):
    path=output_guard(path);path.mkdir(parents=True,exist_ok=False)
    (path/'scratch').mkdir();os.environ['TMPDIR']=str(path/'scratch');return path
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def json_default(x):
    if hasattr(x,'tolist'):return x.tolist()
    if hasattr(x,'item'):return x.item()
    if isinstance(x,Path):return str(x)
    raise TypeError(type(x).__name__)
def js(path,value):
    path=output_guard(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False,default=json_default)+'\n')
