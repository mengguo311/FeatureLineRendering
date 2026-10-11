import os
os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2';os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from pathlib import Path
import json,time,hashlib,shutil,fcntl,resource,traceback
import numpy as np
import cv2
import core,demo,multiview as mv
T=core.TASK;OLD=T.parent/'spatial_rgb_gaussian_demo_v01';SCENES=demo.SCENES;TIERS=[3,12,24,47]
cv2.setNumThreads(2)
def sha(p):return demo.sha(p)
def js(p,a):demo.writejson(p,a)
def guard():
 assert shutil.disk_usage(T).free>=10*1024**3 and shutil.disk_usage('/').free>=1024**3
 assert sum(p.stat().st_size for p in T.rglob('*') if p.is_file())<30*1024**3

def update(phase,**kw):
 p=T/'STATUS.json';a=json.loads(p.read_text()) if p.exists() else {};a.update(phase=phase,status='RUNNING',pid=os.getpid(),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw);js(p,a);print(json.dumps({'phase':phase,**kw}),flush=True)
def checkseal(directory):
 f=directory/'SEAL.json'
 if not f.exists():
  if directory.exists() and any(directory.iterdir()):raise RuntimeError('Unsealed prior attempt retained; explicit archive required: '+str(directory))
  directory.mkdir(parents=True,exist_ok=True);return False
 a=json.loads(f.read_text());assert a['recipe_sha256']==sha(T/'RECIPE_FREEZE.json')
 for row in a['files']:assert sha(directory/row['name'])==row['sha256'],row
 return True

def seal(d,extra=None):
 rows=[{'name':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(d.iterdir()) if p.is_file() and p.name!='SEAL.json'];js(d/'SEAL.json',{'recipe_sha256':sha(T/'RECIPE_FREEZE.json'),'files':rows,'extra':extra,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})

def cache_view(scene,v,c):
 core.assert_build_views([v]);d=T/'cache'/scene/v
 if checkseal(d):return
 a=demo.read(scene,v);f=demo.detect(a);g=demo.fields(a,f,c);valid=f['marked']&core.valid_depth(a['z']);y,x=np.nonzero(valid);n=len(x);pixel=a['z'][y,x]/np.sqrt(c['fx']*c['fy']);s={'means':g['world'][y,x],'uv':np.stack([x,y],-1),'depth':a['z'][y,x],'darkness':f['dark'][y,x],'line_confidence':f['confidence'][y,x],'alpha':a['alpha'][y,x],'pixel':pixel,'tangent':g['tangent'][y,x],'normal':g['normal'][y,x],'fit_valid':g['fit'][y,x]}
 lookup=np.full(a['z'].shape,-1,np.int32);lookup[y,x]=np.arange(n);ny,nx=g['nearest'];near=lookup[ny,nx]
 np.savez_compressed(d/'samples.npz',**s);np.savez_compressed(d/'maps.npz',z=a['z'],alpha=a['alpha'],nearest_sample=near,marked=f['marked'],invalid_depth_rejected=f['marked']&~valid)
 uv,z=core.project(s['means'],c);err=float(abs(uv-s['uv']).max()) if n else 0;assert err<1e-8
 js(d/'SUMMARY.json',{'scene':scene,'view':v,'sample_count':n,'marked':int(f['marked'].sum()),'invalid_depth_rejected':int((f['marked']&~valid).sum()),'alpha_unqualified_preserved':int((~np.isfinite(s['alpha'])|(s['alpha']<.5)).sum()),'roundtrip_max_pixels':err,'source_npz_sha256':sha(demo.E/(scene+'_'+v+'.npz'))});seal(d);update('SOURCE_CACHE',current_scene=scene,current_view=v,samples_this_view=n)

def loadsource(scene,v):return dict(np.load(T/'cache'/scene/v/'samples.npz'))
def concatenate(sources,views):
 s={k:np.concatenate([sources[v][k] for v in views]) for k in sources[views[0]]};s['source_view']=np.concatenate([np.full(len(sources[v]['means']),i,np.int8) for i,v in enumerate(views)]);return s

def compute_pairs(scene,views,sources,cs):
 for target in views:
  d=T/'pair_cache'/scene/target
  if checkseal(d):continue
  maps=dict(np.load(T/'cache'/scene/target/'maps.npz'));pairs={}
  for v in views:
   pairs[v]=np.where(sources[v]['fit_valid'],1,0).astype(np.int8) if v==target else mv.pair_votes(sources[v],sources[target],maps,cs[target])
  np.savez_compressed(d/'votes.npz',**pairs);seal(d,{'source_views':views,'target':target});update('PAIR_VOTES',current_scene=scene,target_view=target)

def assemble_votes(scene,views,sources,cs,use_cache):
 n=sum(len(sources[v]['means']) for v in views);votes=np.empty((n,len(views)),np.int8)
 for col,t in enumerate(views):
  if use_cache:
   with np.load(T/'pair_cache'/scene/t/'votes.npz') as p:votes[:,col]=np.concatenate([p[v] for v in views])
  else:
   maps=dict(np.load(T/'cache'/scene/t/'maps.npz'));votes[:,col]=np.concatenate([np.where(sources[v]['fit_valid'],1,0).astype(np.int8) if v==t else mv.pair_votes(sources[v],sources[t],maps,cs[t]) for v in views])
 return votes

def build_tier(scene,nviews,views,sources,cs,use_cache):
 d=T/'models'/scene/(f'views_{nviews:02d}')
 if checkseal(d):return
 started=time.monotonic();guard();s=concatenate(sources,views);votes=assemble_votes(scene,views,sources,cs,use_cache);a,prov=mv.assemble_asset(s,votes)
 if nviews==3:
  oldsource=dict(np.load(OLD/'results_v1'/scene/'source_samples.npz'));old=dict(np.load(OLD/'results_v2'/scene/'balanced_gaussians.npz'));oldp=dict(np.load(OLD/'results_v2'/scene/'balanced_provenance.npz'));np.testing.assert_array_equal(votes,oldsource['votes']);np.testing.assert_array_equal(prov['source_to_asset'],oldp['source_to_balanced_id']);errors={}
  for key in old:
   err=float(np.max(abs(a[key].astype(float)-old[key].astype(float)))) if len(a[key]) else 0;errors[key]=err;np.testing.assert_allclose(a[key],old[key],rtol=0,atol=1e-7 if key=='opacity' else 1e-9)
  im=demo.read(scene,'0024');one=core.render(a,cs['0024'],im['z'],im['alpha']);two=core.render(old,cs['0024'],im['z'],im['alpha']);np.testing.assert_allclose(one,two,rtol=0,atol=1e-6);js(d/'BASELINE_REGRESSION.json',{'pass':True,'errors':errors,'render_max_abs':float(abs(one-two).max()),'votes_exact':True,'mapping_exact':True})
 assert np.isfinite(a['means']).all() and np.isfinite(a['covariance']).all() and (np.diagonal(a['covariance'],axis1=1,axis2=2)>0).all()
 np.savez_compressed(d/'balanced.npz',**a);demo.save_ply(d/'balanced.ply',a)
 # One density asset per tier, explicit separate arm, no geometry changes.
 density=dict(a);density['opacity']=mv.density_opacity(a['opacity'],nviews);np.savez_compressed(d/'density_compensated.npz',**density);demo.save_ply(d/'density_compensated.ply',density)
 np.savez_compressed(d/'provenance.npz',**prov,votes=votes)
 offsets=np.r_[0,np.cumsum([len(sources[v]['means']) for v in views])];js(d/'SOURCES.json',{'views':views,'ranges':[{'view':v,'start':int(offsets[i]),'stop':int(offsets[i+1]),'cache':str(T/'cache'/scene/v),'samples_sha256':sha(T/'cache'/scene/v/'samples.npz')} for i,v in enumerate(views)],'mapping':'source row = concatenation in this order; source_to_asset has one nonnegative asset row for EVERY finite positive-depth marked source'})
 summary={'scene':scene,'views':nviews,'view_ids':views,'source_samples':len(s['means']),'gaussians':len(a['means']),'merged_duplicate_samples':len(s['means'])-len(a['means']),'merged_duplicate_ratio':1-len(a['means'])/len(s['means']),'source_rows_represented':len(prov['source_to_asset']),'source_weight_histogram':{str(w):int((prov['source_weight']==w).sum()) for w in [.4,.7,1.]},'support_histogram':{str(k):int((prov['source_support_count']==k).sum()) for k in np.unique(prov['source_support_count'])},'vote_categories':{str(k):int((votes==k).sum()) for k in [-2,-1,0,1,2]},'maximum_group_sources':int(a['source_count'].max()),'seconds':time.monotonic()-started,'process_maxrss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'density_formula':'1-(1-alpha)^(3/N); N3 exact identity','never_deleted_unmerged_source':True}
 js(d/'SUMMARY.json',summary);seal(d,summary);completed=len(list((T/'models').glob('*/views_*/SEAL.json')));update('MODEL_SEALED',current_scene=scene,current_tier=nviews,models_completed=completed,gaussians=len(a['means']))

# Purely camera-metadata framing, no heldout content and no per-tier framing.
def make_arc(cs,views):
 from scipy.spatial.transform import Rotation
 Es=[np.array(cs[v]['extrinsic']) for v in views];centers=np.array([-np.linalg.solve(e[:3,:3],e[:3,3]) for e in Es]);dirs=np.array([e[2,:3]/np.linalg.norm(e[2,:3]) for e in Es]);P=np.eye(3)[None]-dirs[:,:,None]*dirs[:,None,:];focus=np.linalg.solve(P.sum(0),np.einsum('nij,nj->i',P,centers));c0=cs['0024'];e0=np.array(c0['extrinsic']);C0=-np.linalg.solve(e0[:3,:3],e0[:3,3]);direction=core.normalize((C0-focus)[None])[0];up=core.normalize((-e0[1,:3])[None])[0];dist=1.6*float(np.median(np.linalg.norm(centers-focus,axis=1)));arc=[]
 for angle in np.linspace(-8,8,33):
  C=focus+Rotation.from_rotvec(up*np.deg2rad(angle)).apply(direction)*dist;forward=core.normalize((focus-C)[None])[0];right=core.normalize(np.cross(forward,up)[None])[0];down=np.cross(forward,right);R=np.stack([right,down,forward]);E=np.eye(4);E[:3,:3]=R;E[:3,3]=-R@C;arc.append(dict(c0,extrinsic=E.tolist(),view='arc',arc_degrees=float(angle)))
 return {'focus':focus.tolist(),'distance':dist,'original_scene_occlusion':False,'framing':'pose-only optical-axis intersection, 1.6x median orbit radius; same across all tiers; background points may be outside viewport, no asset filtering','cameras':arc}

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['build']);args=p.parse_args()
 lock=open(T/'pipeline.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);update('BEGIN_BUILD',models_completed=len(list((T/'models').glob('*/views_*/SEAL.json'))))
 selection=json.loads((T/'VIEW_SELECTION.json').read_text())
 try:
  for scene in SCENES:
   cs=demo.cameras(scene);seq=selection[scene]['sequence'];sources={}
   for v in seq[:3]:cache_view(scene,v,cs[v]);sources[v]=loadsource(scene,v)
   build_tier(scene,3,seq[:3],sources,cs,False)
   for v in seq[3:]:cache_view(scene,v,cs[v]);sources[v]=loadsource(scene,v)
   compute_pairs(scene,seq,sources,cs)
   for n in [12,24,47]:build_tier(scene,n,seq[:n],sources,cs,True)
   js(T/'models'/scene/'ARC_CAMERAS.json',make_arc(cs,seq));del sources
  update('ALL_MODELS_FROZEN',models_completed=12,heldout_content_read_this_run=False)
 except Exception:
  update('ENGINEERING_FAILURE',failure=traceback.format_exc());raise
if __name__=='__main__':main()
