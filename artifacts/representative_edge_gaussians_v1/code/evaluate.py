"""Read-only holdout evaluation of all fixed original-ID fields under full T."""
import json,os,traceback
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
import representative_core as core
from io_utils import *
from native_attributes import NativeAttributeRenderer
import visuals

ARMLABEL={'A':'旧独立 A','B':'新独立 B','C':'联合 λ=0','D':'联合 λ=0.1','E':'联合 λ=0.3'}
def metric(alpha,e,q):
 fg=alpha>=.08;demand=np.maximum(.5*alpha,1e-30);coverage=np.minimum(q/demand,1)
 classes={};chunkstats={};kindvalue={}
 for kind in ('major','detail'):
  vals=[];chunkstats[kind]={}
  for c,name in enumerate(core.CLASSES):
   ridge=e[kind][:,:,c]*(fg);ch,w,meta=core.chunks(ridge,32,3);value=float((w*coverage).sum()) if w.sum()>0 else None
   classes.setdefault(name,{})[kind+'_coverage']=value
   sums=np.bincount(ch.ravel(),weights=(w*coverage).ravel());den=np.bincount(ch.ravel(),weights=w.ravel());valid=den[1:]>0;cc=sums[1:][valid]/den[1:][valid]
   chunkstats[kind][name]=dict(count=len(cc),mean=float(cc.mean()) if len(cc) else None,p10=float(np.quantile(cc,.1)) if len(cc) else None,min=float(cc.min()) if len(cc) else None)
   if value is not None:vals.append(value)
  kindvalue[kind]=float(np.mean(vals)) if vals else None
 off=e['offedge'];mass=float(q.sum());offalpha=float(alpha[off].sum());union=(e['major'].max(-1)>0)|(e['detail'].max(-1)>0);ridge_count=int((union&fg).sum());dist=ndi.distance_transform_edt(~union) if union.any() else None
 return dict(major_coverage=kindvalue['major'],detail_coverage=kindvalue['detail'],offedge_alpha_fraction=float(q[off].sum()/offalpha) if offalpha else None,offedge_selected_mass_fraction=float(q[off].sum()/mass) if mass else None,visible_mass=mass,foreground_selected_mass=float(q[fg].sum()),class_metrics=classes,chunk_metrics=chunkstats,ink_area={str(t):int(((q>t)&fg).sum()) for t in CFG['ink_thresholds']},equivalent_ink_width_pixels={str(t):float(((q>t)&fg).sum()/ridge_count) if ridge_count else None for t in CFG['ink_thresholds']},Q_weighted_distance_to_evidence_pixels=float((dist*q).sum()/mass) if dist is not None and mass else None)

def bank(selection,n,phase):
 entries=[];fields=[]
 for arm in ('A','B','C','D','E'):
  order=selection['arms'][arm]['ordered_original_ids']
  counts=[min(selection['budgets'][1],len(order))] if phase=='arc' else selection['evaluation_counts'][arm]
  for count in counts:
   ids=np.asarray(order[:count],np.int32);v=np.zeros(n,np.float32);v[ids]=1;fields.append(v);entries.append(dict(arm=arm,count=count,field_label=arm+'_'+str(count),original_IDs_sha256=hashlib.sha256(ids.tobytes()).hexdigest()))
 return np.stack([np.ones(n,np.float32)]+fields,-1),entries

def scene_eval(scene):
 asset=OUT/scene/'assets';verify(asset);selection=json.loads((asset/'selected_ids.json').read_text());meta=json.loads((asset/'ASSET.json').read_text())
 for name,digest in meta['code_hashes'].items():
  if sha(ART/'code'/name)!=digest:raise RuntimeError('F selection code changed '+name)
 if sha(OUT/'NORMALIZATION.json')!=meta['normalization_sha256']:raise RuntimeError('F normalization changed')
 norm=json.loads((OUT/'NORMALIZATION.json').read_text())['scales'];cp=INPUTS['scenes'][scene]['checkpoint'];r=NativeAttributeRenderer(cp['path'],cp['sha256'],OUT/'native/evaluation_logs');n=len(r.g['mu'])
 for phase in ('F','C','arc'):
  fields,entries=bank(selection,n,phase)
  for f in frames(scene,phase):
   d=OUT/scene/'evaluation'/f['key']
   if (d/'SEAL.json').exists():verify(d);continue
   raw=read(scene,f,'S4_NATIVE_EVALUATION');event('S4_RENDER',scene=scene,key=f['key'],fields=fields.shape[1]);guard(128*1024**2)
   original=r.render_rgb(f['camera'],export_topk=True);cal=calibration(original,raw)
   rendered=r.render_field_bank(f['camera'],fields);allones=rendered['attributes'][:,:,0];error=float(np.max(np.abs(allones-raw['alpha'])))
   if error>CFG['calibration']['attribute_alpha_atol']:raise RuntimeError('ALLONES_ALPHA_CALIBRATION_FAIL')
   for key in ('alpha','depth','median_depth'):
    if not np.array_equal(rendered[key],original[key]):raise RuntimeError('FIELD_CHANGED_ORIGINAL_'+key)
   q=rendered['attributes'][:,:,1:]
   if np.any(q<0) or np.any(q>raw['alpha'][:,:,None]+3e-6):raise RuntimeError('Attribute raw alphaT bound')
   if phase=='F':e=load(OUT/scene/'F'/f['key']/'evidence.npz');counts=json.loads((OUT/scene/'F'/f['key']/'COUNTS.json').read_text())
   else:
    e,chunks=core.evidence(raw,norm,CFG);counts=dict(counts={k:{c:int((e[k][:,:,i]>0).sum()) for i,c in enumerate(core.CLASSES)} for k in ['fine','major','detail']},chunks=chunks,offedge_foreground_pixels=int(e['offedge'].sum()),foreground_pixels=int((raw['alpha']>=.08).sum()))
   metrics=[]
   for j,item in enumerate(entries):metrics.append(dict(**item,**metric(raw['alpha'],e,q[:,:,j])))
   primary=[];labels=[]
   for arm in ('A','B','C','D','E'):
    count=min(selection['budgets'][1],selection['arms'][arm]['actual_prefix_length']);index=next(j for j,x in enumerate(entries) if x['arm']==arm and x['count']==count);primary.append(q[:,:,index]);labels.append(ARMLABEL[arm]+' | '+str(count)+' IDs')
   info=visuals.comparison(d/'comparison.jpg',raw,e,np.stack(primary,-1),labels,scene+' '+f['key']+' | native800 全原始模型T | 主预算 '+str(selection['budgets'][1]))
   tiermedia={}
   if phase in ('F','C'):
    for b in selection['budgets']:
     if b==selection['budgets'][1]:continue
     indices=[next(j for j,x in enumerate(entries) if x['arm']==arm and x['count']==min(b,selection['arms'][arm]['actual_prefix_length'])) for arm in ('A','B','C','D','E')]
     lab=[ARMLABEL[arm]+' | '+str(entries[j]['count'])+' IDs' for arm,j in zip(('A','B','C','D','E'),indices)]
     tiermedia[str(b)]=visuals.comparison(d/('budget_'+str(b)+'.jpg'),raw,e,q[:,:,indices],lab,scene+' '+f['key']+' | 预声明预算 '+str(b))
   npz(d/'projection.npz',Q=q,alpha=raw['alpha'])
   if phase!='F':npz(d/'evidence.npz',**e)
   atomic(d/'METRICS.json',dict(scene=scene,key=f['key'],phase=phase,camera_hash=f['camera_hash'],camera_json_sha256=f['camera_json_sha256'],raw_sha256=f['raw_sha256'],rgb_content_sha256=hashlib.sha256(np.rint(np.clip(raw['rgb'],0,1)*255).astype(np.uint8).tobytes()).hexdigest(),original_calibration=cal,allones_alpha_max_abs=error,attributes_alpha_depth_exact=True,fields=entries,metrics=metrics,counts=counts,primary_media=info,other_budgets=tiermedia,projection='FULL_NATIVE_ORIGINAL_T',gain=1,ink_mass_matched=False,F_selection_seal_sha256=sha(OUT/'F_SELECTION_SEAL/SEAL.json')))
   seal(d,dict(camera_hash=f['camera_hash'],F_selection_immutable=True,phase=phase));event('S4_POSE_COMPLETE',scene=scene,key=f['key'],field_count=len(entries),allones_error=error)
 del r
 event('S4_SCENE_COMPLETE',scene=scene,actual_poses=49)

def stage():
 verify_s0();verify(OUT/'F_SELECTION_SEAL')
 for scene in CFG['scenes']:scene_eval(scene)
 event('S4_NATIVE_COMPLETE',actual_poses=98)
if __name__=='__main__':
 try:stage()
 except Exception as ex:event('ENGINEERING_STOP',requested_phase='evaluation',error=str(ex),traceback=traceback.format_exc());raise
