"""Complete raw native outputs; evidence targets are diagnostic files only."""
import json,time
from pathlib import Path
import numpy as np
import torch
from PIL import Image,ImageDraw
import runtime as rt
from adapter import backend,scene_io,NativeWeights
from silhouette import evidence,metrics
from fit import solve

def native_output(op,strength):
 rgb=op.ink_rgb(strength).cpu().numpy().transpose(1,2,0)
 return rgb,1-rgb[...,0]

def save_image(path,array):
 p=rt.scoped(path);a=np.asarray(array)
 if a.ndim==2:a=np.repeat(a[...,None],3,-1)
 im=Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5));tmp=p.with_name(p.name+'.tmp');im.save(tmp,format='PNG');tmp.replace(p);return p

def sheet(path,rows,labels,title,size=800):
 width=len(labels)*size;height=len(rows)*(size+26)+60;im=Image.new('RGB',(width,height),'white');d=ImageDraw.Draw(im);d.text((8,8),title,fill='black')
 for j,label in enumerate(labels):d.text((j*size+8,34),label,fill='black')
 for r,row in enumerate(rows):
  for j,a in enumerate(row):
   if isinstance(a,(Path,str)):tile=Image.open(a).convert('RGB')
   else:
    a=np.asarray(a);a=np.repeat(a[...,None],3,-1) if a.ndim==2 else a;tile=Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5))
   if tile.size!=(size,size):tile=tile.resize((size,size),Image.Resampling.LANCZOS)
   im.paste(tile,(j*size,60+r*(size+26)))
 p=rt.scoped(path);tmp=p.with_name(p.name+'.tmp');im.save(tmp,format='PNG');tmp.replace(p);return p

def run_view(scene,camera,record,config,freeze,model=None,arms=('A','B','C','P')):
 unit=scene+'_'+camera['key'];old=rt.resume(unit,freeze)
 if old:return old
 rt.guard(unit);module=backend();model=model or scene_io.load_model(record);s=scene_io.make_settings(module,camera);op=NativeWeights(module,s,model);alpha=op.A(torch.ones(op.n,device='cuda')).cpu().numpy();rgb=op.original().cpu().numpy().transpose(1,2,0);e=evidence(alpha,config['silhouette']);p=rt.ART/'downloads'/scene/camera['key'];media=rt.ART/'media'/scene/camera['key'];files=[]
 fields=p/'evidence.npz';rt.npz(fields,**{k:v for k,v in e.items() if isinstance(v,np.ndarray)},camera_json=np.array(json.dumps(camera)),source_model_sha256=np.array(record['model_sha256']));files.append(fields)
 files+=[save_image(media/'original_RGB_SH3.png',rgb),save_image(media/'target_DIAGNOSTIC_ONLY.png',1-e['target']),save_image(media/'raw_alpha.png',alpha),save_image(media/'coverage_holes_DIAGNOSTIC_ONLY.png',e['holes'])]
 scores=np.load(rt.ROOT/'artifacts/gaer_view_selection_v01/downloads'/(scene+'_'+camera['key']+'_scores_ids.npz'));ids=scores['gaer_ratio_0.005_ids'];b=op.AT(torch.as_tensor(e['beta'],device='cuda'));mass=op.AT(torch.ones((800,800),device='cuda'));allowed=torch.zeros(op.n,device='cuda',dtype=torch.bool);allowed[torch.as_tensor(ids.astype(np.int64),device='cuda')]=True;results={};fits={}
 strengths={}
 for arm in arms:
  rt.guard(unit+'_'+arm)
  if arm=='A':strength=allowed.float();fit=dict(status='BINARY_REFERENCE',allowed_ids=len(ids),active_ids=len(ids))
  elif arm=='B':strength,fit=solve(op,e,allowed,config['solver'],unit+'_B')
  elif arm=='C':strength,fit=solve(op,e,b>0,config['solver'],unit+'_C')
  elif arm=='P':
   n=len(ids);participation=b.cpu().numpy();selected=np.lexsort((np.arange(op.n),-participation))[:n];strength=torch.zeros(op.n,device='cuda');strength[torch.as_tensor(selected,device='cuda')]=1;fit=dict(status='BINARY_ALPHAT_PARTICIPATION',allowed_ids=n,active_ids=n)
  else:raise ValueError(arm)
  strengths[arm]=strength;image,ink=native_output(op,strength);a=op.A(strength).cpu().numpy();err=float(np.abs(ink-a).max())
  if err>3e-6:raise RuntimeError('native white-background formula mismatch')
  m,profiles=metrics(ink,e,config['thresholds']);sp=p/(arm+'_style.npz');rt.npz(sp,original_ids=np.arange(op.n,dtype=np.int32),strength=strength.cpu().numpy(),active_original_ids=np.flatnonzero(strength.cpu().numpy()>1e-5).astype(np.int32),camera_json=np.array(json.dumps(camera)),camera_sha256=np.array(camera['camera_sha256']),source_model_sha256=np.array(record['model_sha256']),protocol_sha256=np.array(rt.sha(rt.ART/'PROTOCOL.json')),original_alpha=alpha,native_ink=ink,native_rgb=image,full_visible_mass=mass.cpu().numpy(),silhouette_participation=b.cpu().numpy(),**profiles);files.append(sp);files+=[save_image(media/(arm+'_native_ink.png'),image),save_image(media/(arm+'_RGB_overlay_PRESENTATION.png'),rgb*image)]
  results[arm]=dict(metrics=m,fit=fit,native_formula_max_error=err,support_visibility_mass=float(mass[strength>1e-5].double().sum()),full_native=True,deleted_gaussians=0)
  rt.atomic_json(p/(arm+'_fit.json'),fit);files.append(p/(arm+'_fit.json'))
 # Fixed panels contain target only in a separately labeled column, no target multiplication of native ink.
 files.append(sheet(media/'comparison.png',[[rgb,1-e['target']]+[1-np.load(p/(a+'_style.npz'))['native_ink'] for a in arms]],['original full SH3','automatic target ONLY']+[a+' full-native ink' for a in arms],scene+' '+camera['key']+' | original Gaussian IDs | gain1 | view-dependent',800))
 oldimage=rt.ROOT/'artifacts/gaer_view_selection_v01/figures'/(scene+'_'+camera['key']+'_gaer_ratio_selected_only.jpg');files.append(sheet(media/'old_deleted_vs_fullT.png',[[oldimage,np.load(p/'A_style.npz')['native_rgb']]],['OLD selected-only RGB: deletes others / changes T','A: black IDs; all original opacity/T retained'],scene+' '+camera['key']+' | different compositing contracts',800))
 # Deterministic native-resolution edge crops, chosen from evidence alone.
 points=np.argwhere(e['boundary']);ys=[np.quantile(points[:,0],v) for v in [.2,.5,.8]];rows=[];boxes=[]
 for y in ys:
  idx=int(np.argmin(np.abs(points[:,0]-y)));cy,cx=map(int,points[idx]);x0=max(0,min(704,cx-48));y0=max(0,min(704,cy-48));boxes.append([x0,y0,x0+96,y0+96]);rows.append([a[y0:y0+96,x0:x0+96] for a in [rgb,1-e['target']]+[np.load(p/(a+'_style.npz'))['native_rgb'] for a in arms]])
 files.append(sheet(media/'edge_zooms_native96.png',rows,['original RGB','target ONLY']+list(arms),scene+' '+camera['key']+' | exact 96x96 native crops; no gain',96));rt.atomic_json(p/'zoom_boxes.json',dict(boxes_xyxy=boxes,selection='alpha exterior y quantiles .2,.5,.8, first closest pixel'));files.append(p/'zoom_boxes.json')
 result=dict(status='COMPLETE',scene=scene,camera=camera,camera_role='DEV' if camera['key'] in config['roles']['dev'] else 'EVALUATION_EXPLORATORY',count=op.n,source_model_sha256=record['model_sha256'],arms=results,components={k:e[k] for k in ['components_total','components_kept','component_sizes','holes_count','hole_sizes']},files=[rt.rel(q) for q in files]);return rt.seal(unit,files,result,freeze)
