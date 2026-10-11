from common import *
import fcntl,resource,shutil
from scipy.optimize import minimize
from scipy.ndimage import distance_transform_edt
from skimage.morphology import skeletonize
from PIL import Image,ImageDraw
import inverse_ink as inv
V=('0000','0024','0048')

def asset(s,ids):
 p=s['pixel'][ids];return {'means':s['means'][ids].copy(),'covariance':np.eye(3)[None]*(.45*p[:,None,None])**2,'opacity':np.minimum(.95,s['darkness'][ids]).astype(np.float64),'colors':np.zeros((len(ids),3)),'view_votes':np.ones(len(ids),np.uint8),'source_count':np.ones(len(ids),np.uint16),'source_anchor':np.asarray(ids,np.int32)}

def metrics(r,D,region=None):
 if region is None:region=np.ones(D.shape,bool)
 return {'mean_darkness':float((1-r[...,0])[region].mean()),'target_mean_darkness':float(D[region].mean()),'MSE':float(np.mean(((1-r[...,0])-D)[region]**2)),'pixels_darkness_gt_02':int(((1-r[...,0]>.2)&region).sum())}

def diagnose_votes(sources,cs):
 results=[]
 for source in V:
  s=sources[source]
  for target in V:
   if source==target:continue
   t=sources[target];m=dict(np.load(B/'cache/scan24'/target/'maps.npz'));uv,z=core.project(s['means'],cs[target]);h,w=m['z'].shape;inside=np.isfinite(uv).all(1)&(z>0)&(uv[:,0]>=0)&(uv[:,0]<=w-1)&(uv[:,1]>=0)&(uv[:,1]<=h-1);xy=np.rint(np.nan_to_num(uv)).astype(int);x=np.clip(xy[:,0],0,w-1);y=np.clip(xy[:,1],0,h-1);idx=m['nearest_sample'][y,x];near=np.clip(idx,0,len(t['means'])-1);d=m['z'][y,x];alpha=m['alpha'][y,x];tol=np.maximum(.005*d,2*d/np.sqrt(cs[target]['fx']*cs[target]['fy']));known=inside&np.isfinite(d)&(d>0)&np.isfinite(alpha)&(alpha>=.5);visible=known&(abs(z-d)<=tol);hidden=known&(z>d+tol);front=known&(z<d-tol)
   nz=t['depth'][near];pixel=nz/np.sqrt(cs[target]['fx']*cs[target]['fy']);dist=np.linalg.norm(uv-t['uv'][near],axis=1)
   cond={'marked_candidate_exists':idx>=0,'near_line_within_1_5px':dist<=1.5,'target_fit_valid':t['fit_valid'][near],'world_distance_within_2_5px':np.linalg.norm(s['means']-t['means'][near],axis=1)<=2.5*np.minimum(s['pixel'],pixel),'tangent_dot_ge_cos45':abs(np.sum(s['tangent']*t['tangent'][near],axis=1))>=np.sqrt(.5),'candidate_depth_agrees':abs(z-nz)<=tol}
   compatible=np.logical_and.reduce(list(cond.values()));expected=core.visibility_class(z,d,alpha,inside,compatible,tol)
   with np.load(B/'pair_cache/scan24'/target/'votes.npz') as f:np.testing.assert_array_equal(f[source],expected)
   fail=visible&~compatible;nearbutfail=fail&cond['near_line_within_1_5px']
   r={'source':source,'target':target,'source_samples':len(z),'unknown':int((~known).sum()),'hidden':int(hidden.sum()),'front_depth_conflict':int(front.sum()),'visible':int(visible.sum()),'support':int((visible&compatible).sum()),'visible_incompatible':int(fail.sum()),'visible_incompatible_despite_near_marked_line':int(nearbutfail.sum()),'failure_flags_overlap_counts':{k:int((fail&~a).sum()) for k,a in cond.items()},'source_fit_false':int((~s['fit_valid']).sum()),'frozen_votes_exact':True};results.append(r)
 js(T/'VOTE_DECOMPOSITION.json',results)

def saveasset(path,a):
 np.savez_compressed(path.with_suffix('.npz'),**a);demo.save_ply(path.with_suffix('.ply'),a)

def single_view(sources,cs,images,fields):
 d=T/'single_view_controls';d.mkdir(exist_ok=True);rows=[]
 for v in V:
  s=sources[v];a=asset(s,np.arange(len(s['means'])));im=images[v];f=fields[v];r=core.render(a,cs[v]);rz=core.render(a,cs[v],im['z'],im['alpha']);saveasset(d/(v+'_raw'),a);demo.saveimage(d/(v+'_no_occlusion.png'),r);demo.saveimage(d/(v+'_depth_occlusion.png'),rz)
  demo.panel(d/(v+'_comparison.jpg'),[('Original RGB / build '+v,im['rgb']),('Original Spatial RGB soft ink',1-f['dark'][...,None].repeat(3,-1)),('Single source / Gaussian kernels',r),('Same / original-depth visibility',rz)],'scan24 | ONE SOURCE ONLY | no multiview fusion',cols=2)
  rows.append({'view':v,'new_gaussians':len(a['means']),'no_occlusion':metrics(r,f['dark']),'depth_occlusion':metrics(rz,f['dark'])})
 js(d/'RESULTS.json',rows);status('SINGLE_VIEW_CONTROLS_COMPLETE',single_view_controls=3)

def prototype(sources,cs,images,fields):
 d=T/'roi_pilot';d.mkdir(exist_ok=True);v='0000';im=images[v];h,w=im['z'].shape;x0=(w-128)//2;y0=(h-128)//2;x1=x0+128;y1=y0+128;s=sources[v];uv=s['uv'];roi=(uv[:,0]>=x0)&(uv[:,0]<x1)&(uv[:,1]>=y0)&(uv[:,1]<y1);rawids=np.flatnonzero(roi);raw=asset(s,rawids);mask=np.zeros((h,w),bool);mask[uv[rawids,1],uv[rawids,0]]=True;skel=skeletonize(mask);keep=roi&skel[uv[:,1],uv[:,0]];ids=np.flatnonzero(keep);assert len(ids)>0
 a=asset(s,ids);initial=a['opacity'].copy();observations=[];windows={};G={}
 for v in V:
  c=cs[v];q,z=core.project(raw['means'],c);inside=(z>0)&np.isfinite(q).all(1);q=q[inside];left=max(0,int(np.floor(q[:,0].min()))-8);right=min(w,int(np.ceil(q[:,0].max()))+9);top=max(0,int(np.floor(q[:,1].min()))-8);bottom=min(h,int(np.ceil(q[:,1].max()))+9);region=np.zeros((h,w),bool);region[top:bottom,left:right]=True;windows[v]=[left,top,right,bottom]
  m=inv.kernel_matrix(a,c,images[v]['z'],images[v]['alpha']);G[v]=m;known=np.isfinite(images[v]['z'])&(images[v]['z']>0)&np.isfinite(images[v]['alpha'])&(images[v]['alpha']>=.5);observations.append({'view':v,'G':m,'target':fields[v]['dark'].ravel(),'region':region.ravel(),'negative_known':known.ravel()})
  canvas=Image.fromarray(np.uint8(np.clip(images[v]['rgb'],0,1)*255));draw=ImageDraw.Draw(canvas);draw.rectangle((left,top,right-1,bottom-1),outline=(255,0,0),width=2);canvas.save(d/(v+'_full_reference_window.png'))
  demo.saveimage(d/(v+'_full_original_spatial.png'),1-fields[v]['dark'][...,None].repeat(3,-1))
 trace=[]
 def cb(x):trace.append(float(inv.objective(x,observations)[0]))
 start=time.monotonic();f0=inv.objective(initial,observations)[0];res=minimize(lambda x:inv.objective(x,observations),initial,jac=True,bounds=[(0,.95)]*len(initial),method='L-BFGS-B',callback=cb,options={'maxiter':80,'ftol':1e-10,'gtol':1e-7,'maxls':30});fit=dict(a);fit['opacity']=res.x.copy();saveasset(d/'roi_all_pixel_raw',raw);saveasset(d/'skeleton_initial',a);saveasset(d/'skeleton_opacity_fit',fit)
 lookup=np.full((h,w),-1,np.int32);lookup[uv[ids,1],uv[ids,0]]=np.arange(len(ids));_,near=distance_transform_edt(~skel,return_indices=True);mapping=lookup[near[0,uv[rawids,1],uv[rawids,0]],near[1,uv[rawids,1],uv[rawids,0]]]
 np.savez_compressed(d/'provenance.npz',all_source_cache_rows=rawids,all_source_uv=uv[rawids],all_source_depth=s['depth'][rawids],all_source_darkness=s['darkness'][rawids],representative_source_cache_rows=ids,source_to_nearest_skeleton_2d=mapping,source_view=np.zeros(len(rawids),np.int8),source_fit_valid=s['fit_valid'][rawids],skeleton_mask=skel,roi_mask=mask)
 renderstats={}
 reload=dict(np.load(d/'skeleton_opacity_fit.npz'))
 for v in V:
  im=images[v];renders=[core.render(aa,cs[v],im['z'],im['alpha']) for aa in [raw,a,reload]];pred=inv.forward(res.x,G[v]).reshape(h,w);err=float(abs(pred-(1-renders[-1][...,0])).max());assert err<2e-6
  np.testing.assert_array_equal(renders[-1],core.render(fit,cs[v],im['z'],im['alpha']))
  left,top,right,bottom=windows[v];target=1-fields[v]['dark'][...,None].repeat(3,-1);items=[('Original Spatial RGB / build '+v,target)]+list(zip(['All source pixels (ROI only)','Skeleton representatives / init','Joint 3-build opacity fit'],renders))
  demo.panel(d/(v+'_fullframe_comparison.jpg'),items,'LOCAL PILOT ONLY | fixed center128 ROI in 0000 | no full-scene reconstruction',cols=2)
  demo.panel(d/(v+'_window_comparison.jpg'),[(k,im[top:bottom,left:right]) for k,im in items],v+' | diagnostic crop of declared window | NOT full scene',cols=2)
  for arm,r in zip(['raw','initial','fit'],renders):demo.saveimage(d/(v+'_'+arm+'.png'),r)
  renderstats[v]={'native_vs_sparse_max_abs':err,'window':windows[v],'initial':metrics(renders[1],fields[v]['dark'],observations[V.index(v)]['region'].reshape(h,w)),'fit':metrics(renders[-1],fields[v]['dark'],observations[V.index(v)]['region'].reshape(h,w)),'target_positive_pixels_in_window':int(((fields[v]['dark']>.2)&observations[V.index(v)]['region'].reshape(h,w)).sum()),'positive_pixels_outside_dictionary_footprints':int(((fields[v]['dark'].ravel()>.2)&observations[V.index(v)]['region']&(np.asarray(G[v].getnnz(axis=1))==0)).sum())}
 rows={'real_full_scene_fusion':False,'source_view':'0000','optimization_views':V,'heldout_used':False,'roi_xyxy':[x0,y0,x1,y1],'raw_sources':len(rawids),'fixed_representatives':len(ids),'nonzero_fitted_opacity':int((res.x>1e-6).sum()),'zero_opacity_representatives':int((res.x<=1e-6).sum()),'geometry_optimized':False,'initial_objective':f0,'final_objective':float(res.fun),'transparent_objective':float(inv.objective(np.zeros_like(initial),observations)[0]),'all095_objective':float(inv.objective(np.full_like(initial,.95),observations)[0]),'optimizer_success':bool(res.success),'termination':str(res.message),'iterations':int(res.nit),'seconds':time.monotonic()-start,'trace':trace,'render_checks':renderstats,'limitations':['skeleton nearest mapping is 2D bookkeeping, not curve identity','no multiview mean/covariance fitting or geometry correction','positive target not covered by seeded dictionary is still included in objective','opacity fit can suppress useful but misregistered evidence; no complete-subject claim']};js(d/'RESULTS.json',rows);status('LOCAL_PILOT_COMPLETE',roi_models=3,roi_raw_sources=len(rawids),roi_representatives=len(ids),prototype_visual_review_pending=True)

def synthetic_controls():
 d=T/'synthetic';d.mkdir(exist_ok=True);c={'width':161,'height':81,'fx':100.,'fy':100.,'extrinsic':np.eye(4).tolist()};uv=np.stack([np.arange(15,146),np.full(131,40)],-1);means=core.backproject(uv,np.full(131,2.),c);a={'means':means,'covariance':np.repeat((np.eye(3)*(.45*2/100)**2)[None],131,0),'opacity':np.full(131,.6),'colors':np.zeros((131,3))};items=[];rows=[]
 for n in [1,3,12,47]:
  dup={k:np.repeat(v,n,axis=0) for k,v in a.items()};r=core.render(dup,c);items.append((str(n)+' repeated observations as NEW kernels',r));rows.append({'repeat':n,'gaussians':len(dup['means']),'center_darkness':float(1-r[40,80,0]),'mean_darkness':float((1-r[...,0]).mean())})
 demo.panel(d/'duplicate_ink_negative_control.png',items,'Synthetic identical observations | tests opacity accumulation, NOT 3D correspondence',cols=1)
 js(d/'RESULTS.json',{'observations':rows,'fixed_dictionary_gaussians':131,'fixed_dictionary_independent_of_replication':True,'note':'analytic synthetic line; no real RGB detector or new geometry recovery claimed'})

if __name__=='__main__':
 lock=open(T/'prototype.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert (T/'EVIDENCE_MANIFEST.json').exists();assert shutil.disk_usage(T).free>10*2**30 and shutil.disk_usage('/').free>2**30
 assert not (T/'roi_pilot/RESULTS.json').exists(),'Preserve completed prototype; do not overwrite'
 files=[p for p in Path(__file__).parent.glob('*.py')];js(T/'CODE_FREEZE.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':[{'path':str(p.resolve()),'sha256':sha(p)} for p in files],'plan_sha256':sha(T/'PROTOTYPE_PLAN_ZH.md'),'clarification_sha256':sha(T/'PROTOTYPE_CLARIFICATION_ZH.md')})
 status('RUNNING_BOUNDED_PROTOTYPES',heldout_used_for_optimization=False)
 cs=demo.cameras('scan24');sources={v:dict(np.load(B/'cache/scan24'/v/'samples.npz')) for v in V};images={v:demo.read('scan24',v) for v in V};fields={v:demo.detect(images[v]) for v in V}
 diagnose_votes(sources,cs);single_view(sources,cs,images,fields);prototype(sources,cs,images,fields);synthetic_controls();status('AWAITING_VISUAL_REVIEW',all_bounded_prototypes_executed=True,process_maxrss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
