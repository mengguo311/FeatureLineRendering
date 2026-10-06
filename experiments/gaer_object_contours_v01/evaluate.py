"""Freeze DEV choice, then exact four views and prior33 actual camera renders."""
import json,subprocess,time
from pathlib import Path
import numpy as np
import torch
import runtime as rt
from adapter import backend,scene_io,NativeWeights,ShapeWeights,shape_extension
from pipeline import run_view,native_output,save_image,sheet,quality_config
from silhouette import evidence,metrics,violation
from shape_arm import make_shape,run_shape
from fit import solve
FFMPEG=Path('/home/u00134/bin/miniconda3/envs/vfsdgs/lib/python3.9/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2')

def arc_manifest(record):
 cameras=record['arc'];return dict(frame_count=len(cameras),unique_camera_count=len({rt.digest(c['w2c']) for c in cameras}),width=800,height=800,cameras=cameras,fit_reset='zero each camera; no warm starts',scope='33 prior actual camera metadata entries, exploratory GS/research seen; no animation of stills')

def production_freeze():
 p=rt.ART/'DEFAULT_FREEZE.json'
 if p.exists():
  result=json.loads(p.read_text())
  for q,h in result['source_hashes'].items():
   if rt.sha(rt.ROOT/q)!=h:raise RuntimeError('production source changed '+q)
  if result['protocol_sha256']!=rt.sha(rt.ART/'PROTOCOL.json'):raise RuntimeError('protocol changed')
  return result
 cfg=json.loads((rt.ART/'PROTOCOL.json').read_text());choices={}
 for scene in cfg['scenes']:
  c=[];s=[];damages=[]
  for key in cfg['roles']['dev']:
   base=json.loads((rt.ART/'results'/(scene+'_'+key+'.json')).read_text());sh=json.loads((rt.ART/'results'/(scene+'_'+key+'_S.json')).read_text());c.append(violation(base['arms']['C']['metrics'],cfg['thresholds']));s.append(violation(sh['metrics'],cfg['thresholds']));damages.append(sh['alpha_damage']['passed'])
  better=all(damages) and sum(s)<=.9*sum(c);arm='S' if better else 'C'
  recognize=all((json.loads((rt.ART/'results'/(scene+'_'+key+('_S' if arm=='S' else '')+'.json')).read_text())['metrics'] if arm=='S' else json.loads((rt.ART/'results'/(scene+'_'+key+'.json')).read_text())['arms']['C']['metrics'])['recognizable'] for key in cfg['roles']['dev'])
  choices[scene]=dict(arm=arm,C_development_violation_sum=sum(c),S_development_violation_sum=sum(s),S_damage_passed_all=all(damages),required_improvement_fraction=.1,recognizable_both_dev=recognize,arc_indices=list(range(33)) if recognize else [0,16,32],visual_verdict='recognizable and mostly continuous, clean thresholds not all passed; no clean GO',development_views=cfg['roles']['dev'])
 result=dict(protocol_sha256=rt.sha(rt.ART/'PROTOCOL.json'),input_freeze_sha256=rt.sha(rt.ART/'INPUT_FREEZE.json'),source_hashes=rt.method_hashes(),choices=choices,frozen_before_evaluation_and_arc=True,previously_seen_exploratory=True,ffmpeg_binary=str(FFMPEG),ffmpeg_binary_sha256=rt.sha(FFMPEG),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
 rt.atomic_json(p,result);return result

def run_arc_frame(scene,camera,record,cfg,method,index,freeze,model):
 unit=scene+'_arc_'+camera['key'];old=rt.resume(unit,freeze)
 if old:return old
 t0=time.perf_counter();rt.guard(unit);mod=backend();s=scene_io.make_settings(mod,camera);base=NativeWeights(mod,s,model);alpha=base.A(torch.ones(base.n,device='cuda')).cpu().numpy();rgb=base.original().cpu().numpy().transpose(1,2,0);e=evidence(alpha,cfg['silhouette']);association=None;damage=None;op=base;edited_ids=np.empty(0,np.int32);override=np.empty((0,6),np.float32)
 if method=='S':
  cov,association=make_shape(base,e,cfg);op=ShapeWeights(shape_extension(),s,model,cov);edited_ids=np.asarray(association['edited_original_ids'],np.int32);override=cov[torch.as_tensor(edited_ids.astype(np.int64),device='cuda')].cpu().numpy();newalpha=op.A(torch.ones(op.n,device='cuda')).cpu().numpy();changed=int(((alpha>.5)!=(newalpha>.5)).sum());damage=dict(alpha_MAE_full_image=float(np.abs(newalpha-alpha).mean()),alpha_threshold_changed_pixels=changed,alpha_threshold_changed_fraction_of_original_foreground=changed/max(int((alpha>.5).sum()),1),foreground_lost_pixels=int(((alpha>.5)&(newalpha<=.5)).sum()));g=cfg['shape']['damage_refusal'];damage['passed']=damage['alpha_MAE_full_image']<=g['alpha_MAE_full_image_max'] and damage['alpha_threshold_changed_fraction_of_original_foreground']<=g['alpha_threshold_changed_fraction_of_original_foreground_max']
 else:newalpha=alpha
 b=op.AT(torch.as_tensor(e['beta'],device='cuda'));strength,fit=solve(op,e,b>0,cfg['solver'],unit+'_'+method);native,ink=native_output(op,strength);formula=float(np.abs(ink-op.A(strength).cpu().numpy()).max());m,profiles=metrics(ink,e,quality_config(cfg));raw=rt.OUT/'arc_raw'/scene/(camera['key']+'.npz');rt.npz(raw,original_rgb_SH3=rgb,original_alpha=alpha,styled_alpha=newalpha,native_rgb=native,native_ink=ink,**{k:v for k,v in e.items() if isinstance(v,np.ndarray) and k not in ['alpha']},**profiles);files=[raw]
 p=rt.ART/'downloads'/scene/'arc'/camera['key'];style=p/'style.npz';rt.npz(style,original_ids=np.arange(op.n,dtype=np.int32),strength=strength.cpu().numpy(),active_original_ids=np.flatnonzero(strength.cpu().numpy()>1e-5).astype(np.int32),edited_original_ids=edited_ids,temporary_covariance_rows=override,camera_json=np.array(json.dumps(camera)),camera_sha256=np.array(camera['camera_sha256']),source_model_sha256=np.array(record['model_sha256']),protocol_sha256=np.array(rt.sha(rt.ART/'PROTOCOL.json')),method=np.array(method));files.append(style);rt.atomic_json(p/'fit.json',fit);files.append(p/'fit.json')
 media=rt.ART/'media'/scene/'arc';files+=[save_image(media/'native_ink'/f'{index:03d}.png',native),save_image(media/'RGB_overlay_PRESENTATION'/f'{index:03d}.png',rgb*native),save_image(media/'original_RGB_SH3'/f'{index:03d}.png',rgb),save_image(media/'target_DIAGNOSTIC_ONLY'/f'{index:03d}.png',1-e['target'])]
 cache=rt.IMAGE/'out/image_space_edge_foundation_v1/raw'/scene/'arc'/camera['key']/'native.npz';prior=np.load(cache);replay=dict(original_RGB_cache_max_error=float(np.abs(rgb-prior['rgb']).max()),original_alpha_cache_max_error=float(np.abs(alpha-prior['alpha']).max()),prior_cache_sha256=rt.sha(cache))
 if formula>3e-6 or replay['original_RGB_cache_max_error']>2e-5 or replay['original_alpha_cache_max_error']>3e-6:raise RuntimeError('arc native formula/source-cache mismatch')
 result=dict(status='COMPLETE',scene=scene,camera=camera,index=index,method=method,original_N=op.n,fit=fit,metrics=m,alpha_damage=damage,edited_count=len(edited_ids),center_to_exterior_distance_quantiles=association['center_to_exterior_distance_quantiles'] if association else None,native_formula_max_error=formula,replay=replay,online_full_seconds=time.perf_counter()-t0,online_fitting_includes='per-camera full original alpha, SDF target, native contribution adjoint, shape if S, zero-start bounded joint fit, native render; no predictor',files=[rt.rel(q) for q in files]);print('ARC_FRAME',scene,index,camera['key'],method,'iterations',fit['iterations'],'budget',fit['maximum_iterations'],'status',fit['status'],'seconds',round(result['online_full_seconds'],3),'coverage',round(m['boundary_coverage'],4),flush=True);return rt.seal(unit,files,result,freeze)

def video(path,frame_dir,count):
 p=rt.scoped(path);tmp=p.with_name(p.stem+'.tmp.mp4');cmd=[str(FFMPEG),'-hide_banner','-loglevel','error','-y','-threads','2','-framerate','12','-i',str(frame_dir/'%03d.png'),'-frames:v',str(count),'-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(tmp)];subprocess.run(cmd,check=True);tmp.replace(p)
 # Decode EVERY frame using existing ffmpeg, count exact full RGB bytes.
 dec=subprocess.run([str(FFMPEG),'-hide_banner','-loglevel','error','-threads','2','-i',str(p),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True);framebytes=800*800*3;decoded=len(dec.stdout)//framebytes
 if len(dec.stdout)%framebytes or decoded!=count:raise RuntimeError('video full decode count mismatch')
 data=p.read_bytes();moov=data.find(b'moov');mdat=data.find(b'mdat');fast=0<=moov<mdat
 if not fast:raise RuntimeError('missing faststart')
 return dict(path=rt.rel(p),frame_count=count,decoded_frame_count=decoded,width=800,height=800,codec='H264/libx264',pixel_format='yuv420p',fps=12,faststart=fast,complete_decode=True,binary_sha256=rt.sha(FFMPEG),sha256=rt.sha(p))

def arc_finish(scene,record,choice,results,cfg,freeze):
 unit=scene+'_arc_media';old=rt.resume(unit,freeze)
 if old:return old
 media=rt.ART/'media'/scene/'arc';files=[];videos=[];count=len(results)
 for kind in ['native_ink','RGB_overlay_PRESENTATION']:
  p=media/(kind+'_33.mp4' if count==33 else kind+'_ENGINEERING3_STOP.mp4');videos.append(video(p,media/kind,count));files.append(p)
 rows=[]
 for start in range(0,count,11):
  row=[media/'native_ink'/f'{j:03d}.png' for j in range(start,min(start+11,count))];row += [np.ones((200,200,3))]*(11-len(row));rows.append(row)
 files.append(sheet(media/'all_frames_native_strip.png',rows,[f'column {i+1}' for i in range(11)],scene+' | all '+str(count)+' ACTUAL current-camera native frames | chronological row-major | '+choice['arm'],200))
 rows=[]
 for start in range(0,count,11):
  row=[media/'RGB_overlay_PRESENTATION'/f'{j:03d}.png' for j in range(start,min(start+11,count))];row += [np.ones((200,200,3))]*(11-len(row));rows.append(row)
 files.append(sheet(media/'all_frames_RGB_overlay_strip.png',rows,[f'column {i+1}' for i in range(11)],scene+' | all '+str(count)+' actual RGB overlays of native ink; presentation only',200))
 churn=[];previous=None;prevink=None;prevtarg=None
 for r in results:
  style=np.load(rt.ART/'downloads'/scene/'arc'/r['camera']['key']/'style.npz');s=style['strength'];raw=np.load(rt.OUT/'arc_raw'/scene/(r['camera']['key']+'.npz'));ink=raw['native_ink'];target=raw['target']
  if previous is not None:
   a=previous>1e-5;b=s>1e-5;jac=float((a&b).sum()/max((a|b).sum(),1));churn.append(dict(from_index=r['index']-1,to_index=r['index'],active_ID_Jaccard=jac,strength_normalized_L1=float(np.abs(s-previous).sum(dtype=np.float64))/max(float(s.sum(dtype=np.float64)+previous.sum(dtype=np.float64)),1e-12),target_corrected_pixel_L1=float(np.abs((ink-prevink)-(target-prevtarg)).mean()),interpretation='camera-dependent activation/image change, no established correspondence or proven temporal stability'))
  previous=s;prevink=ink;prevtarg=target
 vals=[r['metrics']['boundary_coverage'] for r in results];med=float(np.median([r['strength_normalized_L1'] for r in churn])) if churn else None;result=dict(status='COMPLETE_FULL33' if count==33 else 'ENGINEERING3_STOP',scene=scene,method=choice['arm'],frames=count,videos=videos,churn=churn,median_strength_normalized_L1=med,temporal_churn_gate=med is not None and med<=cfg['thresholds']['temporal_strength_normalized_L1_median_max'],coverage_min=float(min(vals)),coverage_max=float(max(vals)),coverage_drop=float(max(vals)-min(vals)),temporal_coverage_gate=max(vals)-min(vals)<=cfg['thresholds']['temporal_quality_coverage_drop_max'],all_clean_frame_count=sum(r['metrics']['clean_all'] for r in results),all_frames_certified=sum(r['fit']['status']=='CERTIFIED_WITH_ROUNDOFF_ALLOWANCE' for r in results),bad_frame_indices=[r['index'] for r in results if not r['metrics']['clean_all']],alpha_damage_refused_frame_indices=[r['index'] for r in results if r['alpha_damage'] is not None and not r['alpha_damage']['passed']],actual_camera_manifest=arc_manifest(record),raw_no_cleanup=True,files=[rt.rel(q) for q in files]);return rt.seal(unit,files,result,freeze)

def fixed_sheet(scene,cfg,choice):
 rows=[];selected=[]
 for key in cfg['roles']['fixed_sheet']:
  media=rt.ART/'media'/scene/key;rows.append([media/'original_RGB_SH3.png',media/'target_DIAGNOSTIC_ONLY.png']+[media/(a+'_native_ink.png') for a in ['A','B','C','P','S']]);selected.append([media/'original_RGB_SH3.png',media/(choice['arm']+'_native_ink.png'),media/(choice['arm']+'_RGB_overlay_PRESENTATION.png')])
 return [sheet(rt.ART/'media'/scene/'fixed_fourview_all_arms_800.png',rows,['full SH3 RGB','automatic target ONLY','A ratio binary','B same IDs fit','C full N fit','P alphaT binary','S bounded shape'],scene+' | 800px panels | row order r_1,r_14,r_7,r_33 | all raw native, target diagnostic',800),sheet(rt.ART/'media'/scene/'fixed_fourview_chosen_800.png',selected,['original full SH3','chosen '+choice['arm']+' native ink','RGB overlay of native ink PRESENTATION'],scene+' | view-dependent original-Gaussian stylization | row order r_1,r_14,r_7,r_33',800)]

def main():
 cfg=json.loads((rt.ART/'PROTOCOL.json').read_text());inputs=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());default=production_freeze();freeze=rt.digest(default)
 for scene in cfg['scenes']:
  rt.guard(scene+'_eval_load');record=inputs['scenes'][scene];model=scene_io.load_model(record);choice=default['choices'][scene]
  for key in cfg['roles']['evaluation']:
   camera=next(c for c in record['cameras'] if c['key']==key);run_view(scene,camera,record,cfg,freeze,model);run_shape(scene,camera,record,cfg,freeze,model,force=True)
  files=fixed_sheet(scene,cfg,choice);rt.seal(scene+'_fixed_sheets',files,dict(status='COMPLETE',method=choice['arm'],files=[rt.rel(q) for q in files]),freeze)
  results=[]
  for j,index in enumerate(choice['arc_indices']):results.append(run_arc_frame(scene,record['arc'][index],record,cfg,choice['arm'],j,freeze,model))
  arc_finish(scene,record,choice,results,cfg,freeze);del model
if __name__=='__main__':main()
