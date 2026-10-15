import os,sys
sys.dont_write_bytecode=True
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json,hashlib,time,datetime,shutil,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_joint_gs_v01');BASE=ROOT.parent/'c2l50_multiview05_v01';CODE=Path(__file__).resolve().parent;OLD=Path('/home/u00134/3dgs_line/gaer_rade_depth_lift_v01');SCENES=['scan24','scan65','ficus']
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def js(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False));q.replace(p)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def guard():
 d=dict(utc=now(),root_free=shutil.disk_usage('/').free,hdd_free=shutil.disk_usage(ROOT).free,task_bytes=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()))
 assert d['root_free']>=2**30 and d['hdd_free']>=10*2**30 and d['task_bytes']<10*2**30,d
 return d
def state(phase,**kw):
 p=ROOT/'STATUS.json';d=json.loads(p.read_text()) if p.exists() else dict(expected_scenes=3,children=[],no_automatic_continuation=True)
 d.update(phase=phase,utc=now(),resources=guard(),**kw);js(p,d);print(phase,flush=True)
def review(name,body,evidence=()):
 p=ROOT/'reviews'/f'{name}.md';assert not p.exists();p.parent.mkdir(exist_ok=True)
 launch=json.loads((ROOT/'AGENT_LAUNCH.json').read_text());p.write_text('# '+name+'\n\nUTC '+now()+'\n同一执行上下文自评；launcher记录 '+json.dumps(launch,ensure_ascii=False)+'；非独立模型审查。\n\n'+body+'\n\n证据SHA\n'+json.dumps({str(x):sha(x) for x in evidence},indent=2))
 q=ROOT/'GATES.json';g=json.loads(q.read_text()) if q.exists() else {'reviews':[]};g['reviews'].append(dict(path=str(p),sha256=sha(p),utc=now()));js(q,g)
def git(p,*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(p),*args]).decode().strip()
def snapshot(p):
 fs=subprocess.check_output(['git','--no-optional-locks','-C',str(p),'ls-files','-co','--exclude-standard','-z']).decode().split('\0');index=Path(git(p,'rev-parse','--git-path','index'));index=index if index.is_absolute() else p/index
 return dict(head=git(p,'rev-parse','HEAD'),branch=git(p,'branch','--show-current'),index_sha256=sha(index),status=git(p,'status','--porcelain'),files={f:sha(p/f) for f in sorted(set(fs)) if f and (p/f).is_file()})
def rollback():
 r=json.loads((ROOT/'ROLLBACK_RECEIPT.json').read_text());a=snapshot(OLD)
 for key,rkey in [('head','old_head'),('branch','old_branch'),('index_sha256','old_index_sha256')]:assert a[key]==r[rkey]
 assert a['status']==r['old_status'].strip()
 for f,h in r['old_python_source_hashes'].items():assert sha(OLD/f)==h,f
 p=ROOT/'OLD_BEFORE.json'
 if p.exists():assert a==json.loads(p.read_text())
 return dict(unchanged=True,python_files=len(r['old_python_source_hashes']),full_files=len(a['files']))
def registry():return json.loads((BASE/'REGISTRY.json').read_text())['scenes']
def line_dir(s):return BASE/'arms/C/scenes'/s/'full'
def save(p,a):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(np.uint8(np.round(np.clip(a,0,1)*255))).save(p)
def panel(p,items,title,subtitle='',cols=2):
 h,w=items[0][1].shape[:2];out=Image.new('RGB',(cols*w,((len(items)+cols-1)//cols)*(h+32)+70),'white');d=ImageDraw.Draw(out);font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';d.text((8,5),title,fill='black',font=ImageFont.truetype(font,20));d.text((8,35),subtitle,fill='black',font=ImageFont.truetype(font,13))
 for i,(lab,a) in enumerate(items):
  assert a.shape[:2]==(h,w);x=i%cols*w;y=70+i//cols*(h+32);d.text((x+5,y+3),lab,fill='black',font=ImageFont.truetype(font,15));out.paste(Image.fromarray(np.uint8(np.round(np.clip(a,0,1)*255))),(x,y+30))
 Path(p).parent.mkdir(parents=True,exist_ok=True);out.save(p)
