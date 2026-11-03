"""Bounded single-process I/O; never imports historical runner/common modules."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='2'
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
import json,time,datetime,hashlib,shutil,signal,ast,ctypes
from pathlib import Path
import numpy as np
from PIL import Image

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
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
def verify(files):
    for f,h in files.items():
        if sha(f)!=h:raise RuntimeError('HASH_MISMATCH '+str(f))
def checkpoint(out,files,binding,stage):
    js(Path(out)/'CHECKPOINT.json',dict(complete=True,stage=stage,config_sha256=binding,files={name:sha(Path(out)/name) for name in files}))
def verify_checkpoint(out,binding):
    out=Path(out);c=json.loads((out/'CHECKPOINT.json').read_text());assert c['complete'] and c['config_sha256']==binding
    verify({str(out/k):v for k,v in c['files'].items()});return c
class Limits:
    def __init__(self,c):
        self.c=c;self.start=time.monotonic();self.last_resource=0
        remaining=datetime.datetime.fromisoformat(c['absolute_deadline_jst']).timestamp()-time.time()
        self.seconds=min(c['max_seconds'],remaining)
        if self.seconds<=0:raise TimeoutError('EXPIRED_CONFIG')
        signal.signal(signal.SIGALRM,self.alarm);signal.setitimer(signal.ITIMER_REAL,self.seconds)
    def alarm(self,*_):raise TimeoutError('HARD_UNIT_DEADLINE')
    def guard(self,phase='delivery'):
        elapsed=time.monotonic()-self.start
        limit={'readiness':300,'selection':1200,'delivery':self.seconds}.get(phase,self.seconds)
        if elapsed>=min(limit,self.seconds-(600 if phase=='selection' else 0)):raise TimeoutError('PHASE_DEADLINE '+phase)
        if time.monotonic()-self.last_resource>10:
            self.last_resource=time.monotonic()
            if shutil.disk_usage('/').free<2**30 or shutil.disk_usage('/mnt/hdd1').free<10*2**30:raise RuntimeError('FREE_SPACE_GUARD')
            for path,cap in [(self.c['unit'],2*2**30),(self.c['runtime'],20*2**30)]:
                if sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())>=cap:raise RuntimeError('OUTPUT_CAP '+path)
    def close(self):signal.setitimer(signal.ITIMER_REAL,0)
def colors(ids):
    z=np.asarray(ids,dtype=np.int64);h=(z*2654435761)%4294967296
    c=np.stack([.12+.72*((h>>s)&255)/255 for s in (0,8,16)],axis=1);c[z<0]=.68;return c

def renderer(c):
    path=Path(c['renderer']);ns=dict(np=np,ctypes=ctypes,ROOT=Path(c['libroot']),_lib=None,Path=Path)
    tree=ast.parse(path.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'colors','project_cov','render'}]
    assert len(nodes)==3;exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns);return ns['render']
def save_image(path,rgb):atomic(path,lambda f:Image.fromarray(np.uint8(np.rint(np.clip(rgb,0,1)*255))).save(f,format='PNG'))
