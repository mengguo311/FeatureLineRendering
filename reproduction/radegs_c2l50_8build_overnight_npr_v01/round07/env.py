import os,sys
sys.dont_write_bytecode=True
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json,hashlib,datetime,shutil,subprocess,time
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_overnight_npr_v01');R=ROOT/'rounds/r07';CODE=Path(__file__).resolve().parent
BASE=ROOT.parent/'c2l50_multiview05_v01';V2=ROOT.parent/'c2l50_8build_outside_in_v02';V1=ROOT.parent/'c2l50_8build_outside_in_v01'
JC=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01')
sys.path.append(str(JC));from common import sha,js,now,panel,git
os.environ['MPLCONFIGDIR']=str(R/'mplconfig')
R1=ROOT/'rounds/r01';R2=ROOT/'rounds/r02';R3=ROOT/'rounds/r03'
SCENES=['scan24','scan65','ficus'];DEV={'scan24':'0000','scan65':'0000','ficus':'train_r_80'};AUX={'scan24':'0024','scan65':'0024','ficus':'train_r_7'};RES={'scan24':['0012','0036'],'scan65':['0012','0036'],'ficus':['test_r_14','test_r_79']}
def views(s):return [DEV[s],AUX[s],*RES[s]]
def npz(p):
 with np.load(p,allow_pickle=False) as d:return {k:d[k].copy() for k in d.files}
def reg():return json.loads((BASE/'REGISTRY.json').read_text())['scenes']
def cam(s,v):return next(c for c in reg()[s]['cameras'] if c['view']==v)
def raw(s,v):
 d=npz(BASE/'scenes'/s/'inputs'/(v+'.npz'));return d['rgb'],d['median_camera_z'].squeeze(),d['alpha'].squeeze()
def unproject(uv,z,c):
 q=np.c_[(uv[:,0]-c['cx'])/c['fx']*z,(uv[:,1]-c['cy'])/c['fy']*z,z];E=np.asarray(c['extrinsic']);return (q-E[:3,3])@E[:3,:3]
def project(X,c):
 E=np.asarray(c['extrinsic']);q=X@E[:3,:3].T+E[:3,3];z=q[:,2]
 with np.errstate(divide='ignore',invalid='ignore'):uv=np.c_[c['fx']*q[:,0]/z+c['cx'],c['fy']*q[:,1]/z+c['cy']]
 return uv,z
def guard():
 x=dict(utc=now(),root_free=shutil.disk_usage('/').free,hdd_free=shutil.disk_usage(ROOT).free,task_bytes=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()),cpu_affinity=sorted(os.sched_getaffinity(0)))
 assert x['root_free']>=2**30 and x['hdd_free']>=10*2**30 and x['task_bytes']<12*2**30 and len(x['cpu_affinity'])<=2,x
 return x
def status(phase,**kw):js(R/'WORK_STATUS.json',dict(round=7,phase=phase,resources=guard(),utc=now(),**kw))
def seal(p):
 assert not (p/'SEAL.json').exists();js(p/'SEAL.json',dict(members={str(f.relative_to(p)):dict(sha256=sha(f)) for f in sorted(p.rglob('*')) if f.is_file() and f.name!='SEAL.json'}))
def checkseal(p):
 for f,x in json.loads((p/'SEAL.json').read_text())['members'].items():assert sha(p/f)==x['sha256'],(p,f)
def review(name,body,evidence=()):
 p=R/'reviews'/(name+'.md');assert not p.exists();p.parent.mkdir(exist_ok=True);p.write_text('# '+name+'\n\nUTC '+now()+'\n同一执行上下文实际自评；非另一个模型或人工独立审查。\n\n'+body+'\n\n'+json.dumps({str(q):sha(q) for q in evidence},indent=2))
 d=json.loads((R/'GATES.json').read_text()) if (R/'GATES.json').exists() else {'reviews':[]};d['reviews'].append(dict(path=str(p.relative_to(R)),sha256=sha(p)));js(R/'GATES.json',d)
def rollback():
 r=json.loads((ROOT/'ROLLBACK_RECEIPT.json').read_text());trees={r['old_worktree']:dict(head=r['old_head'],branch=r['old_branch'],status=r['old_status'],index_sha256=r['old_index_sha256'],python_sha256=r['old_python_source_hashes']),**r['protected_worktrees']};o={}
 for name,a in trees.items():
  p=Path(name);idx=Path(git(p,'rev-parse','--git-path','index'));idx=idx if idx.is_absolute() else p/idx;b=dict(head=git(p,'rev-parse','HEAD'),branch=git(p,'branch','--show-current'),status=git(p,'status','--porcelain'),index_sha256=sha(idx))
  for k in b:assert b[k]==a[k].strip(),(name,k)
  for f,h in a.get('python_sha256',{}).items():assert f.endswith('.py') and sha(p/f)==h,(name,f)
  o[name]=dict(unchanged=True,python_files=len(a.get('python_sha256',{})),**b)
 return dict(old_python_files=len(r['old_python_source_hashes']),protected=o)
def overlay(rgb,m,u):
 out=rgb.copy();out[m]=.55*out[m]+.45*np.array([.05,.85,.4]);out[u]=.45*out[u]+.55*np.array([1,.45,.02]);return out
PAL=np.array([[.5,.5,.5],[.15,.65,.95],[.95,.4,.15],[.5,.8,.2],[.75,.3,.85],[.95,.78,.1]])
def colors(rgb,l,u):
 out=rgb.copy();m=l>0;out[m]=.32*out[m]+.68*PAL[l[m]%len(PAL)];out[u]=.45*out[u]+.55*PAL[0];return out

R4=ROOT/'rounds/r04'

R5=ROOT/'rounds/r05'

R6=ROOT/'rounds/r06'
