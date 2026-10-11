import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['PYTHONDONTWRITEBYTECODE']='1'
from pathlib import Path
import sys,json,time,hashlib,shutil
import numpy as np
T=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/structure_primitive_demo_v04')
B=T.parent/'balanced_multiview_v02';O=T.parent/'spatial_rgb_gaussian_demo_v01';V3=T.parent/'fusion_redesign_v03'
W=Path(__file__).resolve().parent
OLD=W.parent/'radegs_balanced_multiview_v02'
sys.path.insert(0,str(OLD))
import core,demo
import cv2
cv2.setNumThreads(2)
CFG=json.loads((T/'CONFIG.json').read_text())
BUILD=tuple(CFG['build']);HOLD=tuple(CFG['holdout'])
sha=demo.sha;js=demo.writejson
def status(phase,**kw):
    p=T/'STATUS.json';a=json.loads(p.read_text());a.update(phase=phase,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw);js(p,a);print(phase,kw,flush=True)
def guard():
    assert shutil.disk_usage('/').free>2**30
    assert shutil.disk_usage(T).free>10*2**30
    assert sum(p.stat().st_size for p in T.rglob('*') if p.is_file())<15*2**30
def seal(d):
    js(d/'SEAL.json',{'plan_sha256':sha(T/'PLAN_FREEZE.json'),'source_sha256':sha(T/'SOURCE_FREEZE.json'),'files':[{'path':str(p.relative_to(d)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(d.rglob('*')) if p.is_file() and p.name!='SEAL.json']})
