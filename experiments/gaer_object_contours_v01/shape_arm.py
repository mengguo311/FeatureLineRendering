"""One bounded, center-fixed original-ID shape arm, only after DEV C quality failure."""
import json,time
import numpy as np
import torch
from scipy.ndimage import map_coordinates
import runtime as rt
from adapter import backend,scene_io,NativeWeights,ShapeWeights,query_extension,shape_extension
from silhouette import metrics,violation
from pipeline import native_output,save_image,sheet,quality_config
from fit import solve

def make_shape(op,e,config):
 ext=query_extension();R,_,radii,g,b,i=op.state;xy,original_cov,conic,_=ext.geometry(g,op.n);xy=xy.cpu().numpy();conic=conic.cpu().numpy();cv=original_cov.cpu().numpy();visible=radii.cpu().numpy()>0
 beta=torch.as_tensor(e['beta'],device='cuda');b=op.AT(beta);nx=e['normal_yx'][...,1];ny=e['normal_yx'][...,0];u=op.AT(torch.as_tensor(e['beta']*(nx*nx-ny*ny),device='cuda')).cpu().numpy();v=op.AT(torch.as_tensor(e['beta']*(2*nx*ny),device='cuda')).cpu().numpy();dist=map_coordinates(np.abs(e['sdf']),[xy[:,1],xy[:,0]],order=1,mode='constant',cval=1e6);det=conic[:,0]*conic[:,2]-conic[:,1]**2;ids=np.flatnonzero(visible&(b.cpu().numpy()>1e-5)&(dist<=4)&np.isfinite(det)&(det>0)).astype(np.int32)
 angle=.5*np.arctan2(v[ids],u[ids]);n=np.stack([np.cos(angle),np.sin(angle)],-1);t=np.stack([-n[:,1],n[:,0]],-1);C=np.stack([conic[ids,2],-conic[ids,1],-conic[ids,1],conic[ids,0]],-1).reshape(-1,2,2)/det[ids,None,None];vn=np.einsum('ni,nij,nj->n',n,C,n);vt=np.einsum('ni,nij,nj->n',t,C,t);desired=vt[:,None,None]*t[:,:,None]*t[:,None,:]+np.maximum(.3,vn/4)[:,None,None]*n[:,:,None]*n[:,None,:]
 vals,vec=np.linalg.eigh(C);sqrt=np.einsum('nik,nk,njk->nij',vec,np.sqrt(vals),vec);inv=np.einsum('nik,nk,njk->nij',vec,1/np.sqrt(vals),vec);relative=inv@desired@inv;rv,re=np.linalg.eigh(relative);clipped=np.clip(rv,.25,1);styled=sqrt@(np.einsum('nik,nk,njk->nij',re,clipped,re))@sqrt;cv[ids,0]=styled[:,0,0];cv[ids,1]=styled[:,0,1];cv[ids,2]=styled[:,1,1];cv[ids,3:5]=0;cv[ids,5]=-12345
 stats=dict(edited_original_ids=ids.tolist(),original_projected_centers_xy=xy[ids].tolist(),screen_covariance_original=C.tolist(),screen_covariance_override=styled.tolist(),center_to_exterior_distance_quantiles=np.quantile(dist[ids],[0,.25,.5,.75,.95,1]).tolist(),generalized_eigenvalue_min=float(clipped.min()),generalized_eigenvalue_max=float(clipped.max()),bounded_clipping_fraction=float((clipped!=rv).any(1).mean()),steering='double-angle weighted full-native participation; eigenvalue bound can limit exact tangent alignment',centers_fixed=True,original_opacity_retained=True)
 return torch.as_tensor(cv,device='cuda'),stats

def run_shape(scene,camera,record,config,freeze,model=None,force=False):
 unit=scene+'_'+camera['key']+'_S';old=rt.resume(unit,freeze)
 if old:return old
 base=json.loads((rt.ART/'results'/(scene+'_'+camera['key']+'.json')).read_text());cm=base['arms']['C']['metrics']
 if cm['clean_all'] and not force:return rt.seal(unit,[],dict(status='NOT_RUN',reason='C passes all clean DEV thresholds'),freeze)
 rt.guard(unit);module=backend();model=model or scene_io.load_model(record);s=scene_io.make_settings(module,camera);op=NativeWeights(module,s,model);e=dict(np.load(rt.ART/'downloads'/scene/camera['key']/'evidence.npz'));cov,association=make_shape(op,e,config);styled=ShapeWeights(shape_extension(),s,model,cov);newalpha=styled.A(torch.ones(styled.n,device='cuda')).cpu().numpy();original=e['alpha'];damage=dict(alpha_MAE_full_image=float(np.abs(newalpha-original).mean()),alpha_MSE_full_image=float(np.square(newalpha-original).mean()),alpha_threshold_changed_pixels=int(((newalpha>.5)!=(original>.5)).sum()),foreground_lost_pixels=int(((original>.5)&(newalpha<=.5)).sum()),new_alpha_low_target_pixels=int((newalpha<e['target']-1e-5).sum()));damage['alpha_threshold_changed_fraction_of_original_foreground']=damage['alpha_threshold_changed_pixels']/max(int((original>.5).sum()),1);gates=config['shape']['damage_refusal'];damage['passed']=damage['alpha_MAE_full_image']<=gates['alpha_MAE_full_image_max'] and damage['alpha_threshold_changed_fraction_of_original_foreground']<=gates['alpha_threshold_changed_fraction_of_original_foreground_max']
 beta=torch.as_tensor(e['beta'],device='cuda');b=styled.AT(beta);strength,fit=solve(styled,e,b>0,config['solver'],unit);image,ink=native_output(styled,strength);m,profiles=metrics(ink,e,quality_config(config));p=rt.ART/'downloads'/scene/camera['key'];media=rt.ART/'media'/scene/camera['key'];ids=np.asarray(association['edited_original_ids'],np.int32);files=[];sp=p/'S_style.npz';rt.npz(sp,original_ids=np.arange(op.n,dtype=np.int32),strength=strength.cpu().numpy(),edited_original_ids=ids,temporary_covariance_rows=cov[torch.as_tensor(ids.astype(np.int64),device='cuda')].cpu().numpy(),camera_json=np.array(json.dumps(camera)),camera_sha256=np.array(camera['camera_sha256']),source_model_sha256=np.array(record['model_sha256']),protocol_sha256=np.array(rt.sha(rt.ART/'PROTOCOL.json')),native_rgb=image,native_ink=ink,original_alpha=original,styled_alpha=newalpha,**profiles);files.append(sp);files+=[save_image(media/'S_native_ink.png',image),save_image(media/'S_raw_alpha_damage_DIAGNOSTIC.png',np.abs(newalpha-original))]
 # Original RGB comes from unchanged full SH3 float render for overlay, not style-S SH.
 original_rgb=op.original().cpu().numpy().transpose(1,2,0);files.append(save_image(media/'S_RGB_overlay_PRESENTATION.png',original_rgb*image))
 files.append(sheet(media/'C_vs_S.png',[[1-e['target'],np.load(p/'C_style.npz')['native_rgb'],image]],['automatic target ONLY','C original footprints','S bounded shape + refit'],scene+' '+camera['key']+' | full T recomputed | no ink cleanup',800))
 z=json.loads((p/'zoom_boxes.json').read_text())['boxes_xyxy'];rows=[[1-e['target'][y0:y1,x0:x1],np.load(p/'C_style.npz')['native_rgb'][y0:y1,x0:x1],image[y0:y1,x0:x1]] for x0,y0,x1,y1 in z];files.append(sheet(media/'S_edge_zooms_native96.png',rows,['target ONLY','C','S'],scene+' '+camera['key']+' | raw-native 96px crops',96))
 rt.atomic_json(p/'S_fit.json',fit);files.append(p/'S_fit.json');rt.atomic_json(p/'S_association.json',association);files.append(p/'S_association.json');result=dict(status='COMPLETE',scene=scene,camera=camera,metrics=m,fit=fit,alpha_damage=damage,association=association,C_violation=violation(cm,config['thresholds']),S_violation=violation(m,config['thresholds']),scope='one bounded camera-dependent temporary original-ID covariance arm, not fixed 3D curves',files=[rt.rel(q) for q in files]);return rt.seal(unit,files,result,freeze)

def main():
 cfg=json.loads((rt.ART/'PROTOCOL.json').read_text());f=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());p=rt.ART/'SHAPE_DEV_FREEZE.json'
 if not p.exists():rt.atomic_json(p,dict(protocol_sha256=rt.sha(rt.ART/'PROTOCOL.json'),input_freeze_sha256=rt.sha(rt.ART/'INPUT_FREEZE.json'),source_hashes=rt.method_hashes(),trigger='all four DEV C fail at least contour-distance threshold, actual C still recognizable'))
 freeze=json.loads(p.read_text())
 for q,h in freeze['source_hashes'].items():
  if rt.sha(rt.ROOT/q)!=h:raise RuntimeError('shape DEV source changed '+q)
 for scene in cfg['scenes']:
  rt.guard(scene+'_shape_load');rec=f['scenes'][scene];model=scene_io.load_model(rec)
  for key in cfg['roles']['dev']:run_shape(scene,next(c for c in rec['cameras'] if c['key']==key),rec,cfg,rt.digest(freeze),model)
  del model
if __name__=='__main__':main()
