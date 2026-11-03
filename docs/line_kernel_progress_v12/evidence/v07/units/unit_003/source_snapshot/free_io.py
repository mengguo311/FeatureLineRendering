"""Isolated I/O, guards and frozen original-kernel loading; no legacy producer imports."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='2'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import json,hashlib,time,datetime,signal,shutil,ast,ctypes
from pathlib import Path
import numpy as np
from PIL import Image

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def atomic(path,writer):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():raise FileExistsError(path)
 tmp=path.with_name(path.name+'.partial')
 with open(tmp,'xb') as f:writer(f);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def js(path,obj):atomic(path,lambda f:f.write(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False).encode()))
def nz(path,**kw):atomic(path,lambda f:np.savez_compressed(f,**kw))
def fingerprints(a):return {k:dict(shape=list(v.shape),dtype=str(v.dtype),sha256=hashlib.sha256(v.tobytes()).hexdigest()) for k,v in a.items()}
def verify(files,guard=lambda:None):
 for path,h in files.items():guard();assert sha(path)==h,'HASH_MISMATCH '+path
class Limits:
 def __init__(self,c):
  self.c=c;self.start=time.monotonic();self.last=0;self.seconds=min(c['max_seconds'],datetime.datetime.fromisoformat(c['absolute_deadline_jst']).timestamp()-time.time())
  if self.seconds<=600:raise TimeoutError('INSUFFICIENT_DELIVERY_RESERVE')
  signal.signal(signal.SIGALRM,self.alarm);signal.setitimer(signal.ITIMER_REAL,self.seconds)
 def alarm(self,*_):raise TimeoutError('UNIT_DEADLINE')
 def guard(self,phase='delivery'):
  elapsed=time.monotonic()-self.start;limit={'readiness':120,'initialization':360,'science':1200}.get(phase,self.seconds)
  if phase!='delivery':limit=min(limit,self.seconds-600)
  if elapsed>=limit:raise TimeoutError('PHASE_DEADLINE '+phase)
  if elapsed-self.last>3 or self.last==0:
   self.last=elapsed
   assert len(os.sched_getaffinity(0))<=2,'CPU_AFFINITY'
   assert shutil.disk_usage('/').free>=2**30,'ROOT_SPACE'
   assert shutil.disk_usage(self.c['unit_root']).free>=10*2**30,'HDD_SPACE'
   u=sum(p.stat().st_size for p in Path(self.c['unit_root']).rglob('*') if p.is_file());assert u<=2*2**30,'UNIT_SIZE'
   total=sum(p.stat().st_size for p in Path(self.c['runtime_root']).rglob('*') if p.is_file());assert total<=20*2**30,'RUNTIME_SIZE'
 def elapsed(self):return time.monotonic()-self.start

def load(c,guard):
 guard('readiness');verify(c['input_files'],lambda:guard('readiness'));verify(c.get('helper_files',{}),lambda:guard('readiness'))
 with np.load(c['gaussians'],allow_pickle=False) as z:a={k:z[k] for k in z.files}
 with np.load(c['controls'],allow_pickle=False) as z:ct={k:z[k] for k in ('control','control_index','derivative_basis','primitive_id','internal_piece_id','arc_t')}
 n=c['kernel_count'];assert a['means'].shape==(n,3) and a['covariance'].shape==(n,3,3) and a['opacity'].shape==(n,)
 for key,v in a.items():assert len(v)==n and np.isfinite(v).all(),key
 assert np.all(a['opacity']>=0) and np.all(a['opacity']<=1),'opacity'
 for key in ('primitive_id','internal_piece_id','arc_t'):np.testing.assert_array_equal(a[key],ct[key])
 ix=ct['control_index'];assert ix.shape==(n,2) and np.issubdtype(ix.dtype,np.integer) and ix.min()>=0 and ix.max()<len(ct['control']);assert ct['derivative_basis'].shape==(n,2)
 derivative=np.sum(ct['control'][ix]*ct['derivative_basis'][:,:,None],axis=1);norm=np.linalg.norm(derivative,axis=1);valid=np.isfinite(derivative).all(1)&np.isfinite(norm)&(norm>1e-15);t=np.zeros_like(derivative);t[valid]=derivative[valid]/norm[valid,None]
 cov=a['covariance'];assert np.max(abs(cov-cov.transpose(0,2,1)))<=1e-10;assert np.min(np.linalg.eigvalsh(cov))>=-1e-12,'NON_PSD'
 half=np.minimum(.5,np.sqrt(np.maximum(0,np.einsum('ni,nij,nj->n',t,cov,t)))/c['p'])
 fp=fingerprints(a)
 for v in a.values():v.flags.writeable=False
 return dict(asset=a,x=a['means']/c['p'],t=t,valid=valid,half=half,fingerprint=fp,p=c['p'])

def save_stage(out,d,models,a,events,next_id,binding,scope):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);n=len(d['x']);kw={k:v for k,v in a.items()};kw.update(line_kernel_id=np.arange(n,dtype=np.int64),primitive_id=d['asset']['primitive_id'],provisional=np.ones(n,bool));nz(out/'MEMBERSHIP.npz',**kw)
 mids=sorted(models);offset=[0];qq=[]
 for mid in mids:qq.append(models[mid]);offset.append(offset[-1]+len(models[mid]))
 nz(out/'MODELS.npz',model_id=np.array(mids,np.int64),offsets=np.array(offset,np.int64),q_normalized=np.concatenate(qq) if qq else np.empty((0,3)),p=np.array(d['p']))
 js(out/'LINEAGE.json',dict(events=events,next_id=next_id,stage=out.name,predecessor_stage=scope.get('predecessor_stage'),model_versions={str(mid):hashlib.sha256(models[mid].tobytes()).hexdigest() for mid in mids},alternatives_reference='raw pre-validation model IDs; raw sibling checkpoint preserves removed/split models',old_groups_locked=False,model_geometry_auxiliary_only=True));js(out/'SCOPE.json',scope)
 js(out/'METRICS.json',dict(rows=n,assigned=int(np.sum(a['edge_id']>=0)),UNKNOWN=int(np.sum(a['edge_id']<0)),models=len(models),all_rows_exported=True,reason_codes={'0':'assigned','1':'invalid_tangent','2':'no_geometric_candidate','3':'competition_or_UNKNOWN_margin','4':'insufficient_support','5':'invalid_split_geometry'}))
 assert fingerprints(d['asset'])==d['fingerprint'],'ORIGINAL_GEOMETRY_CHANGED'
 js(out/'GEOMETRY_AUDIT.json',dict(before=d['fingerprint'],after=fingerprints(d['asset']),all_fields_exact=True,rows=n))
 names=['MEMBERSHIP.npz','MODELS.npz','LINEAGE.json','SCOPE.json','GEOMETRY_AUDIT.json','METRICS.json'];js(out/'CHECKPOINT.json',dict(complete=True,config_sha256=binding,files={name:sha(out/name) for name in names},stage=out.name))
 cold_stage(out,binding)
def cold_stage(out,binding):
 out=Path(out);cp=json.loads((out/'CHECKPOINT.json').read_text());assert cp['complete'] and cp['config_sha256']==binding;verify({str(out/k):v for k,v in cp['files'].items()})
 with np.load(out/'MEMBERSHIP.npz',allow_pickle=False) as z:a={k:z[k] for k in z.files}
 with np.load(out/'MODELS.npz',allow_pickle=False) as z:m={int(mid):z['q_normalized'][z['offsets'][i]:z['offsets'][i+1]].copy() for i,mid in enumerate(z['model_id'])}
 return m,a,json.loads((out/'LINEAGE.json').read_text())
def renderer(c):
 path=Path(c['renderer']);ns=dict(np=np,ctypes=ctypes,ROOT=Path(c['libroot']),_lib=None,Path=Path)
 tree=ast.parse(path.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'colors','project_cov','render'}];assert len(nodes)==3
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns);return ns['render']
def colors(ids):
 z=np.asarray(ids,np.int64);h=(z.astype(np.uint64)*np.uint64(2654435761))%np.uint64(2**32);c=np.stack([.12+.72*((h>>s)&255)/255 for s in (0,8,16)],1);c[z<0]=.68;return c
def image(path,rgb):atomic(path,lambda f:Image.fromarray(np.uint8(np.rint(np.clip(rgb,0,1)*255))).save(f,format='PNG'))
