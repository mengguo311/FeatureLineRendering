"""Plain resumable production runner. No plugin, retraining or old-data writes."""
import argparse,sys,time,os,json,traceback,subprocess,shutil
from pathlib import Path
import numpy as np
from scipy import sparse,ndimage as ndi
import representative_core as core
from io_utils import *
from native_attributes import NativeAttributeRenderer,gpu_guard
import visuals

def evidence_stage():
 verify_s0();guard();normp=OUT/'NORMALIZATION.json'
 if normp.exists():norm=json.loads(normp.read_text())['scales'];verify(OUT/'NORMALIZATION_SEAL')
 else:
  pools=[[[] for c in range(3)] for s in range(3)]
  for f in frames('mic','F'):
   raw=read('mic',f,'S1_F_NORMALIZATION');fields=core.multiscale_fields(raw,CFG['sigmas_pixels'])
   for s,v in enumerate(fields):
    for c in range(3):
     a=v['magnitude'][:,:,c];pools[s][c].append(a[(a>1e-12)&v['roi'][:,:,c]])
  norm=[[max(float(np.percentile(np.concatenate(pools[s][c]),CFG['normalization_percentile'])),1e-12) if sum(map(len,pools[s][c])) else 1. for c in range(3)] for s in range(3)]
  atomic(normp,dict(scales=norm,scope='Mic all8 F only; inherited unchanged',F_hashes=[f['raw_sha256'] for f in frames('mic','F')],config_sha256=sha(ART/'code/config.json'),core_sha256=sha(ART/'code/representative_core.py')))
  d=OUT/'NORMALIZATION_SEAL';d.mkdir(exist_ok=True);atomic(d/'binding.json',dict(normalization_sha256=sha(normp)));seal(d,dict(F_only=True))
 for scene in CFG['scenes']:
  for f in frames(scene,'F'):
   d=OUT/scene/'F'/f['key']
   if (d/'SEAL.json').exists():verify(d);continue
   raw=read(scene,f,'S1_F_EVIDENCE');e,m=core.evidence(raw,norm,CFG);npz(d/'evidence.npz',**e)
   info=visuals.evidence_panel(d/'preview.jpg',raw,e,scene+' '+f['key']+' | F-only 多尺度证据')
   counts={k:{c:int((e[k][:,:,i]>0).sum()) for i,c in enumerate(core.CLASSES)} for k in ['fine','major','detail']}
   atomic(d/'COUNTS.json',dict(counts=counts,chunks=m,offedge_foreground_pixels=int(e['offedge'].sum()),foreground_pixels=int((raw['alpha']>=.08).sum()),preview=info))
   seal(d,dict(raw_sha256=f['raw_sha256'],camera_hash=f['camera_hash'],normalization_sha256=sha(normp),core_sha256=sha(ART/'code/representative_core.py')))
   event('S1_EVIDENCE_COMPLETE',scene=scene,key=f['key'],counts=counts,chunks={k:v['chunks'] for k,v in m.items()})
 event('S1_COMPLETE',actual_F=16,normalization_sha256=sha(normp))

def build_variant(k):
 d=OUT/'native'/('top'+str(k));build=d/'BUILD.json'
 if build.exists():return json.loads(build.read_text())
 guard(128*1024**2);gpu_guard(OUT/'native/logs');source=SRC/'native_extension/top32'
 sourcehash={}
 for p in source.rglob('*'):
  if not p.is_file() or 'build' in p.relative_to(source).parts or '__pycache__' in p.parts or p.suffix in ('.so','.pyc'):continue
  rel=p.relative_to(source);q=d/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);sourcehash[str(rel)]=sha(p)
 p=d/'cuda_rasterizer/render_forward.cu';before=p.read_text();old='constexpr int ATTR_TOPK = 32;';assert before.count(old)==1;p.write_text(before.replace(old,'constexpr int ATTR_TOPK = '+str(k)+';'))
 import difflib
 patch=''.join(difflib.unified_diff(before.splitlines(True),p.read_text().splitlines(True),fromfile='source/top32/render_forward.cu',tofile='local/top'+str(k)+'/render_forward.cu'));(d/'capacity.patch').write_text(patch)
 env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',CUDA_HOME='/usr/local/cuda',TORCH_CUDA_ARCH_LIST='8.6',MAX_JOBS='2',TMPDIR=str(OUT/'tmp'),XDG_CACHE_HOME=str(OUT/'native/cache'),TORCH_EXTENSIONS_DIR=str(OUT/'native/torch_extensions'),PATH='/home/u00134/bin/miniconda3/envs/vfsdgs/bin:/usr/local/cuda/bin:'+env.get('PATH',''))
 for key in ('TMPDIR','XDG_CACHE_HOME','TORCH_EXTENSIONS_DIR'):Path(env[key]).mkdir(parents=True,exist_ok=True)
 event('S2_BUILD_START',topk=k);t=time.time()
 with (d/'build.log').open('w') as log:r=subprocess.run([sys.executable,'-B','setup.py','build_ext','--inplace'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT)
 rec=dict(returncode=r.returncode,seconds=time.time()-t,topk=k,source_hashes=sourcehash,forward_sha256=sha(p),patch_sha256=sha(d/'capacity.patch'),source='read-only RaDe-derived historical TOP32, isolated capacity-only modification')
 if r.returncode==0:
  libs=list((d/'diff_gaussian_rasterization').glob('_C*.so'));assert len(libs)==1;rec.update(library=str(libs[0]),library_sha256=sha(libs[0]))
 atomic(build,rec)
 if r.returncode:raise RuntimeError('NATIVE_BUILD_FAILED '+str(k))
 return rec

def coverage(raw,e,ids,w):
 a=raw['alpha'];capture=w.sum(-1,dtype=np.float64);fg=a>=.08;ratio=np.divide(capture,a,out=np.zeros_like(capture),where=a>0)
 def audit(mask,weight=None):
  count=int(mask.sum())
  if not count:return dict(pixels=0,captured_mass_fraction=None,p10=None,p05=None,min=None,mean=None,residual_mass=None)
  ww=np.ones_like(a) if weight is None else weight
  den=float((ww[mask]*a[mask]).sum());return dict(pixels=count,captured_mass_fraction=float((ww[mask]*capture[mask]).sum()/den) if den else None,p10=float(np.quantile(ratio[mask],.1)),p05=float(np.quantile(ratio[mask],.05)),min=float(ratio[mask].min()),mean=float(ratio[mask].mean()),residual_mass=float(np.maximum(a[mask]-capture[mask],0).sum()))
 major=(e['major'].max(-1)>0)&fg;omega=e['omega'].sum(-1);m=audit(major,omega)
 out=dict(foreground=audit(fg),major=m,detail=audit((e['detail'].max(-1)>0)&fg),offedge=audit(e['offedge']),classes={})
 for c,n in enumerate(core.CLASSES):out['classes'][n]={kind:audit((e[kind][:,:,c]>0)&fg,e['omega'][:,:,c] if kind=='major' else None) for kind in ('major','detail')}
 out['gate_pass']=m['captured_mass_fraction'] is not None and m['captured_mass_fraction']>=.95 and m['p10']>=.9
 return out

def contributions_stage():
 verify_s0();norm=json.loads((OUT/'NORMALIZATION.json').read_text());audits=[];used=32;block=None
 sourcebuild=json.loads((SRC/'native_extension/BUILD_TOP32.json').read_text())
 for k in CFG['topk_sequence']:
  try:build=sourcebuild if k==32 else build_variant(k)
  except Exception as ex:
   block=str(ex);event('S2_CAPACITY_BLOCKER',requested_K=k,last_available_K=used,error=block);break
  rows=[]
  for scene in CFG['scenes']:
   cp=INPUTS['scenes'][scene]['checkpoint'];renderer=NativeAttributeRenderer(cp['path'],cp['sha256'],OUT/'native/logs',build['library'],build['library_sha256'],topk=k);n=len(renderer.g['mu'])
   for f in frames(scene,'F'):
    d=OUT/scene/'contributions'/('K'+str(k))/f['key']
    if (d/'SEAL.json').exists():verify(d);rows.append(json.loads((d/'AUDIT.json').read_text()));continue
    raw=read(scene,f,'S2_TOPK_'+str(k));e=load(OUT/scene/'F'/f['key']/'evidence.npz');event('S2_RENDER',scene=scene,key=f['key'],topk=k);guard(256*1024**2)
    rendered=renderer.render_rgb(f['camera'],export_topk=True);cal=calibration(rendered,raw);ids=rendered['topk_id'];w=rendered['topk_w'];audit=coverage(raw,e,ids,w)
    flatid=ids.ravel();flatw=w.ravel();ok=flatid>=0;mass=np.bincount(flatid[ok],weights=flatw[ok],minlength=n)
    fg=raw['alpha']>=.08;pixels=np.flatnonzero(fg.ravel()).astype(np.int32);fi=ids.reshape(-1,k)[pixels];fw=w.reshape(-1,k)[pixels];valid=fi>=0;ptr=np.r_[0,np.cumsum(valid.sum(1))].astype(np.int64)
    fgcost=np.bincount(fi[valid],weights=(fw/np.maximum(raw['alpha'].ravel()[pixels,None],1e-30))[valid],minlength=n)/max(len(pixels),1)
    off=e['offedge'];oi=ids[off];ow=w[off];valid_o=oi>=0;cost=np.bincount(oi[valid_o],weights=(ow/np.maximum(raw['alpha'][off,None],1e-30))[valid_o],minlength=n)/max(int(off.sum()),1)
    counters=[];positive=[]
    for c in range(3):
     cm=(e['major'][:,:,c]>0)|(e['detail'][:,:,c]>0);band=ndi.distance_transform_edt(~cm)<=2 if cm.any() else cm;mask=fg&~band;i=ids[mask];v=w[mask];counters.append(np.bincount(i[i>=0],weights=v[i>=0],minlength=n));mask=fg&cm;i=ids[mask];v=w[mask];positive.append(np.bincount(i[i>=0],weights=v[i>=0],minlength=n))
    npz(d/'foreground_csr.npz',pixels=pixels,indptr=ptr,original_ids=fi[valid],weights=fw[valid],alpha=raw['alpha'].ravel()[pixels])
    npz(d/'statistics.npz',raw_mass=mass,visible=mass>0,foreground_mean_fraction=fgcost,nonedge_mean_fraction=cost,class_counter_mass=np.stack(counters),class_positive_mass=np.stack(positive))
    rec=dict(scene=scene,key=f['key'],topk=k,calibration=cal,coverage=audit,library_sha256=build['library_sha256'],raw_sha256=f['raw_sha256'],camera_hash=f['camera_hash'],fullgrid_captured_raw_mass=float(mass.sum()),foreground_contributors=int(valid.sum()))
    atomic(d/'AUDIT.json',rec);seal(d,dict(calibrated=True,F_only=True));rows.append(rec);event('S2_POSE_COMPLETE',scene=scene,key=f['key'],topk=k,gate=audit['gate_pass'],major=audit['major'])
    del rendered,ids,w,fi,fw
   del renderer
   import gc;gc.collect()
  used=k;audits.append(dict(K=k,rows=rows,all16_gate_pass=all(r['coverage']['gate_pass'] for r in rows)))
  atomic(OUT/'COMPLETENESS.json',dict(available_K=used,audits=audits,blocker=block,mathematically_full_attribution='UNDETERMINED',operational_gate_pass=audits[-1]['all16_gate_pass']))
  if audits[-1]['all16_gate_pass']:break
 atomic(OUT/'COMPLETENESS.json',dict(available_K=used,audits=audits,blocker=block,mathematically_full_attribution='UNDETERMINED',operational_gate_pass=audits[-1]['all16_gate_pass'] if audits else None))
 event('S2_COMPLETE',available_K=used,all16_gate_pass=audits[-1]['all16_gate_pass'] if audits else None)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['evidence','contributions']);a=p.parse_args()
 try:
  if a.phase=='evidence':evidence_stage()
  elif a.phase=='contributions':contributions_stage()
 except Exception as e:
  event('ENGINEERING_STOP',requested_phase=a.phase,error=str(e),traceback=traceback.format_exc());raise
