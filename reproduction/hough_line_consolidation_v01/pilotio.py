"""Owned I/O and strict serial resource limits; no old producer imports."""
import os, sys
sys.dont_write_bytecode = True
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
import json, time, hashlib, datetime, shutil
from pathlib import Path
import numpy as np
CODE = Path(__file__).resolve().parent
CFG = json.loads((CODE/'config.json').read_text())
OUT = Path(CFG['output'])
BASE = OUT.parents[2]/'c2l50_multiview05_v01'
ORCH = OUT.parents[1]/'orchestration'

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''): h.update(b)
    return h.hexdigest()

def plain(x):
    if isinstance(x,np.ndarray): return x.tolist()
    if isinstance(x,np.generic): return x.item()
    if isinstance(x,Path): return str(x)
    raise TypeError(type(x).__name__)

def js(path,obj):
    path=Path(path)
    assert path.resolve().is_relative_to(OUT.resolve()), path
    assert path.name != 'DECISION.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=plain,allow_nan=False))
    tmp.replace(path)

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def guard():
    assert shutil.disk_usage('/').free>=2**30
    assert shutil.disk_usage(OUT).free>=10*2**30
    assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())<8*2**30
    assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(CFG['deadline_utc']), 'PILOT_DEADLINE'
def status(stage,**kw):
    js(OUT/'STATUS.json',dict(stage=stage,utc=now(),claim='PARTIAL/UNDETERMINED',**kw))
    print(stage,kw,flush=True)
def project(x,c):
    E=np.asarray(c['extrinsic']); q=np.asarray(x)@E[:3,:3].T+E[:3,3]
    return np.c_[c['fx']*q[:,0]/q[:,2]+c['cx'], c['fy']*q[:,1]/q[:,2]+c['cy']],q[:,2]
def unit(x): return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-30)
def quant(x):
    x=np.asarray(x); x=x[np.isfinite(x)]
    return dict(n=len(x),q=np.quantile(x,[0,.5,.9,.99,1]).tolist()) if len(x) else dict(n=0,q=None)
def load_np(path):
    with np.load(path,allow_pickle=False) as z: return {k:z[k] for k in z.files}
