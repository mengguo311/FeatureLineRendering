import os,sys
sys.dont_write_bytecode=True
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json,hashlib,time,subprocess,shutil,datetime,importlib.util
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_outside_in_v01');OLD=ROOT.parent/'c2l50_8build_geometry_roles_v01';BASE=ROOT.parent/'c2l50_multiview05_v01';JOINT=ROOT.parent/'c2l50_8build_joint_gs_v01'
CODE=Path(__file__).resolve().parent;GC=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_geometry_roles_v01/reproduction/radegs_c2l50_8build_geometry_roles_v01');JC=GC.parents[2]/'gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01'
os.environ['MPLCONFIGDIR']=str(ROOT/'mplconfig');sys.path.insert(0,str(JC));import common as old
from format import read_ply,activate
from renderer import render,project_cov,colors
sys.path.insert(0,str(GC));sys.path.insert(0,str(CODE))
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sha,js,now,save,panel=old.sha,old.js,old.now,old.save,old.panel
SCENES=['scan24','scan65','ficus'];DEV={'scan24':'0000','scan65':'0000','ficus':'train_r_80'};AUX={'scan24':'0024','scan65':'0024','ficus':'train_r_7'};RESERVED={'scan24':['0012','0036'],'scan65':['0012','0036'],'ficus':['test_r_14','test_r_79']}
def guard():
 d=dict(utc=now(),root_free=shutil.disk_usage('/').free,hdd_free=shutil.disk_usage(ROOT).free,task_bytes=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()));assert d['root_free']>=2**30 and d['hdd_free']>=10*2**30 and d['task_bytes']<8*2**30 and len(os.sched_getaffinity(0))<=2,d;return d
def state(phase,**kw):
 p=ROOT/'STATUS.json';d=json.loads(p.read_text()) if p.exists() else dict(expected_pilots=1,completed_pilots=0,children=[],no_automatic_continuation=True);d.update(phase=phase,utc=now(),resources=guard(),**kw);js(p,d);print(phase,flush=True)
def review(name,text,paths=()):
 p=ROOT/'reviews'/f'{name}.md';assert not p.exists();p.parent.mkdir(exist_ok=True);p.write_text('# '+name+'\n\n'+now()+'\n同一执行代理实际评估；不是第二模型/独立人工评审。\n\n'+text+'\n\n'+json.dumps({str(q):sha(q) for q in paths},indent=2));g=ROOT/'GATES.json';x=json.loads(g.read_text()) if g.exists() else dict(reviews=[]);x['reviews'].append(dict(path=str(p),sha256=sha(p)));js(g,x)
def registry():return json.loads((BASE/'REGISTRY.json').read_text())['scenes']
def cam(s,v):return next(c for c in registry()[s]['cameras'] if c['view']==v)
def rawpath(s,v):return BASE/'scenes'/s/'inputs'/f'{v}.npz'
def linepath(s):return BASE/'arms/C/scenes'/s/'full'
def npz(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def seal(p):
 assert not (p/'SEAL.json').exists();js(p/'SEAL.json',dict(members={str(q.relative_to(p)):dict(sha256=sha(q)) for q in sorted(p.rglob('*')) if q.is_file() and q.name!='SEAL.json'}))
def checkseal(p):
 for n,x in json.loads((p/'SEAL.json').read_text())['members'].items():assert sha(p/n)==x['sha256'],(p,n)
def projection(X,c):
 E=np.asarray(c['extrinsic']);q=X@E[:3,:3].T+E[:3,3];z=q[:,2];return np.c_[c['fx']*q[:,0]/z+c['cx'],c['fy']*q[:,1]/z+c['cy']],z
def unproject(uv,z,c):
 q=np.c_[(uv[:,0]-c['cx'])/c['fx']*z,(uv[:,1]-c['cy'])/c['fy']*z,z];E=np.asarray(c['extrinsic']);return (q-E[:3,3])@E[:3,:3]
def rollback():
 # Reuse read-only snapshot logic, with THIS launcher receipt; do not inspect credentials.
 spec=importlib.util.spec_from_file_location('previous_env',GC/'env.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=ROOT;os.environ['MPLCONFIGDIR']=str(ROOT/'mplconfig');sys.path.insert(0,str(CODE));return m.rollback()
def cases(s):return [x for x in json.loads((ROOT/'CASE_FREEZE.json').read_text())['cases'] if x['scene']==s]
def jsonsafe(v):
 if isinstance(v,np.ndarray):return v.tolist()
 if isinstance(v,np.generic):return v.item()
 if isinstance(v,dict):return {k:jsonsafe(x) for k,x in v.items()}
 if isinstance(v,list):return [jsonsafe(x) for x in v]
 return v
