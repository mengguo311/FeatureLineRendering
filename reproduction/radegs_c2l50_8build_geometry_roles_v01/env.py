import os,sys
sys.dont_write_bytecode=True
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json,hashlib,time,subprocess,shutil,datetime
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_geometry_roles_v01')
os.environ['MPLCONFIGDIR']=str(ROOT/'mplconfig')
BASE=ROOT.parent/'c2l50_multiview05_v01';JOINT=ROOT.parent/'c2l50_8build_joint_gs_v01'
CODE=Path(__file__).resolve().parent
JC=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01')
sys.path.insert(0,str(JC));import common as old
from format import read_ply,write_ply,activate
from renderer import render,project_cov,colors
sys.path.insert(0,str(CODE))
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sha,js,now,save,panel=old.sha,old.js,old.now,old.save,old.panel
SCENES=['scan24','scan65','ficus'];DEV={'scan24':'0000','scan65':'0000','ficus':'train_r_80'}
VIEWS={'scan24':['0000','0012','0036'],'scan65':['0000','0012','0036'],'ficus':['train_r_80','test_r_14','test_r_79']}
def guard():
 d=dict(utc=now(),root_free=shutil.disk_usage('/').free,hdd_free=shutil.disk_usage(ROOT).free,task_bytes=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()))
 assert d['root_free']>=2**30 and d['hdd_free']>=10*2**30 and d['task_bytes']<10*2**30 and len(os.sched_getaffinity(0))<=2,d
 return d
def state(phase,**kw):
 p=ROOT/'STATUS.json';d=json.loads(p.read_text()) if p.exists() else dict(expected_scenes=3,children=[],no_automatic_continuation=True)
 d.update(phase=phase,utc=now(),resources=guard(),**kw);js(p,d);print(phase,flush=True)
def review(name,body,paths=()):
 p=ROOT/'reviews'/f'{name}.md';assert not p.exists();p.parent.mkdir(exist_ok=True)
 p.write_text('# '+name+'\n\n'+now()+'\n同一执行上下文实际自评，非另一模型/人工独立评审；启动元数据仅作为来源记录。\n\n'+body+'\n\n证据SHA\n'+json.dumps({str(q):sha(q) for q in paths},indent=2))
 g=ROOT/'GATES.json';x=json.loads(g.read_text()) if g.exists() else dict(reviews=[]);x['reviews'].append(dict(path=str(p),sha256=sha(p)));js(g,x)
def registry():return json.loads((BASE/'REGISTRY.json').read_text())['scenes']
def cam(s,v):return next(x for x in registry()[s]['cameras'] if x['view']==v)
def npz(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def linepath(s):return BASE/'arms/C/scenes'/s/'full'
def rawpath(s,v):return BASE/'scenes'/s/'inputs'/f'{v}.npz'
def seal(p):js(p/'SEAL.json',dict(files={q.name:sha(q) for q in p.iterdir() if q.is_file() and q.name!='SEAL.json'}))
def checkseal(p):
 for n,h in json.loads((p/'SEAL.json').read_text())['files'].items():assert sha(p/n)==h,(p,n)
def projection(X,c):
 E=np.asarray(c['extrinsic']);q=X@E[:3,:3].T+E[:3,3];z=q[:,2]
 return np.c_[c['fx']*q[:,0]/z+c['cx'],c['fy']*q[:,1]/z+c['cy']],z
def unproject(uv,z,c):
 q=np.c_[(uv[:,0]-c['cx'])/c['fx']*z,(uv[:,1]-c['cy'])/c['fy']*z,z];E=np.asarray(c['extrinsic']);return (q-E[:3,3])@E[:3,:3]
def snap(p):
 files=subprocess.check_output(['git','--no-optional-locks','-C',str(p),'ls-files','-co','--exclude-standard','-z']).decode().split('\0')
 assert not any(Path(f).name.lower() in {'auth.json','credentials.json','credentials','id_rsa','id_ed25519','.netrc','.npmrc','.env'} or Path(f).suffix in {'.pem','.p12','.pfx','.key'} for f in files if f),'Credential-like paths refused before file reads'
 return old.snapshot(p)
def rollback():
 r=json.loads((ROOT/'ROLLBACK_RECEIPT.json').read_text());p=Path(r['old_worktree']);s=snap(p)
 for k,kk in [('head','old_head'),('branch','old_branch'),('index_sha256','old_index_sha256')]:assert s[k]==r[kk]
 assert s['status']==r['old_status'].strip()
 for f,h in r['old_python_source_hashes'].items():assert sha(p/f)==h
 oldref=JOINT/'OLD_BEFORE.json';assert s==json.loads(oldref.read_text());out={}
 for name,a in r['protected_worktrees'].items():
  b=snap(Path(name))
  for k in ['head','branch','index_sha256','status']:assert b[k]==a[k].strip(),(name,k)
  for f,h in a.get('python_sha256',{}).items():assert sha(Path(name)/f)==h
  out[name]=dict(unchanged=True,head=b['head'])
 return dict(old_unchanged=True,old_python_files=len(r['old_python_source_hashes']),protected=out)
