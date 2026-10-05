from pathlib import Path
import os,json,hashlib,datetime,shutil,subprocess,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'artifacts/representative_edge_gaussians_three_v1';OUT=ROOT/'out/representative_edge_gaussians_three_v1'
CFG=json.loads((ART/'code/config.json').read_text());INPUTS=json.loads((ART/'INPUT_HASH_MANIFEST.json').read_text());SRC=Path(INPUTS['source_root'])
if (OUT/'BUDGET_SEAL/binding.json').exists():CFG['budgets']=json.loads((OUT/'BUDGET_SEAL/binding.json').read_text())['counts']
COMMON=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def local(p):
 p=Path(p).resolve()
 if not any(p==r or r in p.parents for r in [ART,OUT]):raise ValueError('Output containment')
 return p
def guard(payload=0):
 if datetime.datetime.now(datetime.timezone.utc)>datetime.datetime.fromisoformat(CFG['stage_deadline']):raise RuntimeError('DEADLINE_BLOCKER')
 if payload:
  mem={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemAvailable:','MemTotal:'))}
  if mem['MemAvailable']<payload*3+512*1024**2:raise RuntimeError('RESIDENT_MEMORY_BLOCKER '+str(dict(peak_estimate_bytes=payload*3+512*1024**2,available_bytes=mem['MemAvailable'])))
 root=shutil.disk_usage(ROOT).free;git=shutil.disk_usage(COMMON).free
 used=sum(p.stat().st_size for r in [ART,OUT] for p in r.rglob('*') if p.is_file())
 if root < CFG['root_reserve_bytes']+payload or git < CFG['git_reserve_bytes'] or used+payload>CFG['science_budget_bytes']:raise RuntimeError('BUDGET_BLOCKER '+str(dict(root_free=root,git_free=git,used=used,estimated_payload=payload)))
 return dict(root_free=root,git_free=git,stage_bytes=used)
def atomic(p,x):
 p=local(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.partial');q.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');os.replace(q,p)
def npz(p,**arrays):
 p=local(p);guard(sum(np.asarray(v).nbytes for v in arrays.values())+1048576);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.partial.npz');np.savez_compressed(q,**arrays);os.replace(q,p)
def load(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def event(phase,**kw):
 rec=dict(utc=utc(),phase=phase,**kw);OUT.mkdir(parents=True,exist_ok=True)
 with (OUT/'EVENTS.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
 print(json.dumps(rec),flush=True);atomic(OUT/'STATUS.json',dict(state=phase,**rec))
def seal(folder,context):
 folder=local(folder);files={str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='SEAL.json' and '.partial' not in p.name}
 atomic(folder/'SEAL.json',dict(utc=utc(),context=context,files=files));return sha(folder/'SEAL.json')
def verify(folder):
 m=json.loads((Path(folder)/'SEAL.json').read_text())
 for f,h in m['files'].items():
  if sha(Path(folder)/f)!=h:raise RuntimeError('SEAL_CHANGED '+f)
 return m

def verify_s0():
 s=json.loads((ART/'S0_SEAL.json').read_text())
 for f,h in s['files'].items():
  if sha(ROOT/f)!=h:raise RuntimeError('S0_CHANGED '+f)
 return sha(ART/'S0_SEAL.json')
def frames(scene,phase):
 from scene_binding import scene_id
 scene=scene_id(scene)
 return [f for f in INPUTS['scenes'][scene]['frames'] if (f['key'].startswith(phase+'_') if phase in ('F','C') else f['key'].startswith('arc0_'))]
def read(scene,spec,phase):
 if not spec['key'].startswith('F_'):
  verify(OUT/'F_SELECTION_SEAL');
  for s in CFG['scenes']:verify(OUT/s/'assets')
 if sha(spec['raw_path'])!=spec['raw_sha256']:raise RuntimeError('Raw SHA mismatch')
 cam=json.loads(Path(spec['camera_json_path']).read_text());cam=cam.get('camera',cam)
 from native_attributes import canonical_hash,camera_record
 if canonical_hash(cam)!=spec['camera_hash']:raise RuntimeError('Camera identity changed')
 event('READ',scene=scene,key=spec['key'],stage=phase,raw_sha256=spec['raw_sha256'],camera_hash=spec['camera_hash'])
 with np.load(spec['raw_path'],allow_pickle=False) as z:return {k:z[k] for k in ('rgb','alpha','depth','median_depth','topk_id','topk_w','topk_depth')}
def calibration(a,b):
 tol=CFG['calibration'];res={}
 for k in ('rgb','alpha','depth','median_depth','topk_id','topk_w','topk_depth'):
  v=a[k][...,:4] if k.startswith('topk_') else a[k];w=b[k]
  if v.shape!=w.shape:raise ValueError('Calibration shape '+k)
  d=float(np.max(np.abs(v.astype(np.float64)-w.astype(np.float64)),initial=0));t=0 if k=='topk_id' else (tol['top4_depth_atol'] if k=='topk_depth' else tol['top4_w_atol'] if k=='topk_w' else tol['depth_atol'] if 'depth' in k else tol['alpha_atol'] if k=='alpha' else tol['rgb_atol'])
  if d>t:raise RuntimeError('CALIBRATION_FAIL '+k+' '+str(d))
  res[k]=d
 return res
