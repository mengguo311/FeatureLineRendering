"""Serial resource limits and durable local artifacts, with no producer imports."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='2'
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
import json,time,datetime,hashlib,shutil,ast,ctypes,pickle
from pathlib import Path
import numpy as np
from PIL import Image
CFG=None
END=None
PHASE='build_test'
START=None
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def atomic(path,writer):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    tmp=path.with_name(path.name+'.partial')
    with tmp.open('xb') as f:writer(f);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
def js(path,obj):atomic(path,lambda f:f.write(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False).encode()))
def nz(path,**obj):atomic(path,lambda f:np.savez_compressed(f,**obj))
def pk(path,obj):atomic(path,lambda f:pickle.dump(obj,f,protocol=5))
def verify(files):
    for f,h in files.items():
        if sha(f)!=h:raise RuntimeError('HASH_MISMATCH '+f)
def guard(reserve=0):
    if END is not None:
        if CFG and START is not None and PHASE in CFG['stage_elapsed_limits'] and time.time()>START+CFG['stage_elapsed_limits'][PHASE]:raise TimeoutError('stage elapsed limit '+PHASE)
        reserve=max(reserve,300 if PHASE=='topology' else 0)
        if time.time()>=END-reserve:raise TimeoutError('configured deadline / export reserve')
    if shutil.disk_usage('/').free<2**30 or shutil.disk_usage('/mnt/hdd1').free<10*2**30:raise RuntimeError('FREE_SPACE_GUARD')
    if CFG:
        for key,limit in [('unit',2*2**30),('runtime',8*2**30)]:
            if sum(f.stat().st_size for f in Path(CFG[key]).rglob('*') if f.is_file())>=limit:raise RuntimeError('OUTPUT_CAP '+key)
def configure(c):
    global CFG,END,START
    CFG=c;START=time.time();END=min(time.time()+c['max_seconds'],datetime.datetime.fromisoformat(c['science_deadline']).timestamp(),datetime.datetime.fromisoformat(c['unit_deadline']).timestamp())
def colors(ids):
    z=np.asarray(ids,dtype=np.int64);h=(z*2654435761)%4294967296
    c=np.stack([.12+.72*((h>>s)&255)/255 for s in (0,8,16)],1);c[z<0]=.68
    return c

def save_image(path,rgb):
    atomic(path,lambda f:Image.fromarray(np.uint8(np.rint(np.clip(rgb,0,1)*255))).save(f,format='PNG'))
def helpers(c):
    ns=dict(np=np,ctypes=ctypes,ROOT=Path(c['libroot']),_lib=None,Path=Path)
    path=Path(c['renderer']);tree=ast.parse(path.read_text());wanted={'colors','project_cov','render'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
    assert len(nodes)==3
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
    return ns
