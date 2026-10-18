import os,sys
sys.dont_write_bytecode=True
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json,hashlib,time,datetime,subprocess,shutil
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_outside_in_v02')
V1=ROOT.parent/'c2l50_8build_outside_in_v01';BASE=ROOT.parent/'c2l50_multiview05_v01';JOINT=ROOT.parent/'c2l50_8build_joint_gs_v01'
CODE=Path(__file__).resolve().parent;V1CODE=CODE.parents[2]/'gaer_c2l50_8build_outside_in_v01/reproduction/radegs_c2l50_8build_outside_in_v01'
JC=CODE.parents[2]/'gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01'
os.environ['MPLCONFIGDIR']=str(ROOT/'mplconfig')
sys.path.append(str(JC))
from common import sha,js,now,save,panel,git
import numpy as np
from PIL import Image,ImageDraw,ImageFont
SCENES=['scan24','scan65','ficus'];DEV={'scan24':'0000','scan65':'0000','ficus':'train_r_80'};AUX={'scan24':'0024','scan65':'0024','ficus':'train_r_7'};RES={'scan24':['0012','0036'],'scan65':['0012','0036'],'ficus':['test_r_14','test_r_79']}
def views(s):return [DEV[s],AUX[s],*RES[s]]
def registry():return json.loads((BASE/'REGISTRY.json').read_text())['scenes']
def cam(s,v):return next(c for c in registry()[s]['cameras'] if c['view']==v)
def rawpath(s,v):return BASE/'scenes'/s/'inputs'/f'{v}.npz'
def npz(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def raw(s,v):
 d=npz(rawpath(s,v));return d['rgb'],d['median_camera_z'].squeeze(),d['alpha'].squeeze()
def projection(X,c):
 E=np.asarray(c['extrinsic']);q=X@E[:3,:3].T+E[:3,3];z=q[:,2]
 with np.errstate(divide='ignore',invalid='ignore'):uv=np.c_[c['fx']*q[:,0]/z+c['cx'],c['fy']*q[:,1]/z+c['cy']]
 return uv,z
def unproject(uv,z,c):
 q=np.c_[(uv[:,0]-c['cx'])/c['fx']*z,(uv[:,1]-c['cy'])/c['fy']*z,z];E=np.asarray(c['extrinsic']);return (q-E[:3,3])@E[:3,:3]
def guard():
 d=dict(utc=now(),root_free=shutil.disk_usage('/').free,hdd_free=shutil.disk_usage(ROOT).free,task_bytes=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()))
 assert d['root_free']>=2**30 and d['hdd_free']>=10*2**30 and d['task_bytes']<8*2**30 and len(os.sched_getaffinity(0))<=2,d
 return d
def state(phase,**kw):
 p=ROOT/'STATUS.json';d=json.loads(p.read_text()) if p.exists() else dict(expected_scenes=3,children=[],no_automatic_continuation=True)
 d.update(phase=phase,utc=now(),resources=guard(),**kw);js(p,d);print(phase,flush=True)
def review(name,body,paths=()):
 p=ROOT/'reviews'/f'{name}.md';assert not p.exists();p.parent.mkdir(exist_ok=True)
 p.write_text('# '+name+'\n\n'+now()+'\n同一执行上下文的实际自评，不是另一模型或独立人工审查。\n\n'+body+'\n\n'+json.dumps({str(q):sha(q) for q in paths},indent=2))
 g=ROOT/'GATES.json';d=json.loads(g.read_text()) if g.exists() else dict(reviews=[]);d['reviews'].append(dict(path=str(p),sha256=sha(p)));js(g,d)
def seal(p):
 assert not (p/'SEAL.json').exists();js(p/'SEAL.json',dict(members={str(f.relative_to(p)):dict(sha256=sha(f)) for f in sorted(p.rglob('*')) if f.is_file() and f.name!='SEAL.json'}))
def checkseal(p):
 for f,v in json.loads((p/'SEAL.json').read_text())['members'].items():assert sha(p/f)==v['sha256'],(p,f)
def rollback():
 r=json.loads((ROOT/'ROLLBACK_RECEIPT.json').read_text());alltrees={r['old_worktree']:dict(head=r['old_head'],branch=r['old_branch'],status=r['old_status'],index_sha256=r['old_index_sha256'],python_sha256=r['old_python_source_hashes']),**r['protected_worktrees']};out={}
 for name,a in alltrees.items():
  p=Path(name);idx=Path(git(p,'rev-parse','--git-path','index'));idx=idx if idx.is_absolute() else p/idx
  b=dict(head=git(p,'rev-parse','HEAD'),branch=git(p,'branch','--show-current'),status=git(p,'status','--porcelain'),index_sha256=sha(idx))
  for k in b:assert b[k]==a[k].strip(),(name,k)
  fs=a.get('python_sha256',{})
  for f,h in fs.items():assert f.endswith('.py') and sha(p/f)==h,(name,f)
  out[name]=dict(unchanged=True,python_files=len(fs),**b)
 return dict(old_python_files=len(r['old_python_source_hashes']),protected=out)
def grey(x):return np.repeat(np.asarray(x)[...,None],3,axis=2)
def overlay(rgb,mask,unknown=None):
 x=rgb.copy();x[mask]=.55*x[mask]+.45*np.array([.05,.85,.4])
 if unknown is not None:x[unknown]=.45*x[unknown]+.55*np.array([1,.45,.02])
 return x
PALETTE=np.array([[.8,.8,.8],[.15,.65,.95],[.95,.4,.15],[.5,.8,.2],[.75,.3,.85],[.95,.78,.1],[.2,.85,.75],[.9,.3,.55],[.45,.45,.95]])
def colors(rgb,lab,unknown=None):
 x=rgb.copy();m=lab>0;x[m]=.32*x[m]+.68*PALETTE[lab[m]%len(PALETTE)]
 if unknown is not None:x[unknown]=.45*x[unknown]+.55*np.array([.5,.5,.5])
 return x
