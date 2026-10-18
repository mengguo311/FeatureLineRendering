from env import *
from responsibility import ProjectedSource,measure_difference,mass
from geometry_roles import fit_patch,classify,plane_ray_depth,ROLES,PALETTE
def unique_rows(rows,xy,mask):
 ids=np.flatnonzero(mask);_,ii=np.unique(xy[ids],axis=0,return_index=True);return [rows[i] for i in ids[ii]],ids[ii]
def geometry_axis(proj,uv):
 r=proj.query(np.rint(np.median(uv,axis=0)));ix=np.searchsorted(proj.ids,r['ids']);S=proj.S[ix];w=r['weight']
 if w.sum()==0:return np.array([1.,0.])
 c=np.sum(S*w[:,None,None],axis=0)/w.sum();_,U=np.linalg.eigh(c);return U[:,-1]
def query_case(case,arm,c,raw,proj,a):
 line=npz(linepath(case['scene'])/'gaussians.npz');X=line['means'][case['child_ids']];uv,z=projection(X,c);d=np.gradient(uv,axis=0);length=np.linalg.norm(d,axis=1);t=d/np.maximum(length[:,None],1e-12);n=np.c_[-t[:,1],t[:,0]]
 if arm=='shifted_12px':uv=uv+12*n
 if arm=='source_geometry_axis':
  axis=geometry_axis(proj,uv);L=np.sum(np.linalg.norm(np.diff(uv,axis=0),axis=1));uv=np.median(uv,axis=0)+np.linspace(-L/2,L/2,len(uv))[:,None]*axis;t=np.tile(axis,(len(uv),1));n=np.c_[-t[:,1],t[:,0]]
 cfg=json.loads((ROOT/'CONFIG.json').read_text());offs=np.array(cfg['offsets']);xy=np.rint(uv[:,None,:]+n[:,None,:]*offs[None,:,None]).astype(int).reshape(-1,2);along=np.repeat(np.arange(len(uv)),len(offs));side=np.tile(offs,len(uv));W,H=c['width'],c['height'];inside=(xy[:,0]>=0)&(xy[:,0]<W)&(xy[:,1]>=0)&(xy[:,1]<H);rows=[];cache={}
 empty=lambda:dict(ids=np.empty(0,int),weight=np.empty(0),alpha_i=np.empty(0),T=np.empty(0),z=np.empty(0),q=np.empty(0),alpha=0.,median=0.,expected=0.,z_quantiles=np.zeros(3),rgb=np.zeros(3),trans=1.)
 for q,ok in zip(xy,inside):
  key=tuple(q)
  if key not in cache:cache[key]=proj.query(q) if ok else empty()
  rows.append(cache[key])
 native_z=np.full(len(xy),np.nan);native_a=np.zeros(len(xy));rgb=np.zeros((len(xy),3));native_z[inside]=raw['median_camera_z'].squeeze()[xy[inside,1],xy[inside,0]];native_a[inside]=raw['alpha'].squeeze()[xy[inside,1],xy[inside,0]];rgb[inside]=raw['rgb'][xy[inside,1],xy[inside,0]]
 f=np.sqrt(c['fx']*c['fy']);p=float(np.median(z[z>.2])/f) if np.any(z>.2) else 1.;qalpha=np.array([r['alpha'] for r in rows]);qmed=np.array([r['median'] for r in rows]);qwidth=np.array([r['z_quantiles'][2]-r['z_quantiles'][0] for r in rows]);valid=inside&np.isfinite(native_z)&(native_z>.2)&(native_a>=.5)&(qalpha>=.5)&(qmed>.2)&(abs(qmed-native_z)<=np.maximum(.02*native_z,4*native_z/f))
 lr,li=unique_rows(rows,xy,side<0);rr,ri=unique_rows(rows,xy,side>0);diff=measure_difference(lr,rr);lc=li[valid[li]];rc=ri[valid[ri]];left=fit_patch(unproject(xy[lc],native_z[lc],c),qalpha[lc],p);right=fit_patch(unproject(xy[rc],native_z[rc],c),qalpha[rc],p)
 pl=plane_ray_depth(left,uv,c);pr=plane_ray_depth(right,uv,c);j=abs(pl-pr)/p;finite=np.isfinite(j);join=float(np.median(j[finite])) if finite.any() else 1e9
 ci=np.flatnonzero(side==0);center_supported=valid[ci]&(abs(z-native_z[ci])<=np.maximum(.02*native_z[ci],4*native_z[ci]/f))
 if arm=='source_geometry_axis':center_supported=valid[ci] # No ink-depth assertion in no-line control.
 cr,cids=unique_rows(rows,xy,side==0);ids,m=mass(cr);good=m>0;ids=ids[good];m=m[good];tube=0.
 if len(ids):
  e=np.linalg.eigvalsh(a['covariance'][ids]);ax=(e[:,2]/e[:,1]>9)&(e[:,1]/e[:,0]<3);tube=float(np.dot(m,ax)/m.sum())
 side_rgb=float(np.linalg.norm(np.mean(rgb[li],axis=0)-np.mean(rgb[ri],axis=0))/np.sqrt(3));qw=qwidth[valid];raywidth=float(np.median(qw)/p) if len(qw) else 1e9
 info=dict(center_supported=bool(center_supported.mean()>=.6),center_supported_fraction=float(center_supported.mean()),join_pixels=join,L1=diff['L1'],ray_width_pixels=raywidth,alpha_left=diff['left_alpha'],alpha_right=diff['right_alpha'],alpha_center=float(qalpha[ci].mean()),filament_shape=tube>=.7,tube_like_source_mass=tube,rgb_side_difference=side_rgb,pixel_world_proxy=p)
 role=classify(left,right,info);front='left' if finite.any() and np.median(pl[finite]-pr[finite])<-4*p else 'right' if finite.any() and np.median(pl[finite]-pr[finite])>4*p else 'not_resolved'
 # Per-offset responsibility/normal stability is evidence, never tuned to lower UNKNOWN.
 offsets={}
 for off in [2,4,6]:
  la,lidx=unique_rows(rows,xy,side==-off);ra,ridx=unique_rows(rows,xy,side==off);dd=measure_difference(la,ra);offsets[str(off)]=dict(L1=dd['L1'],overlap=dd['overlap'],left_alpha=dd['left_alpha'],right_alpha=dd['right_alpha'])
 starts=np.r_[0,np.cumsum([len(r['ids']) for r in rows])];arrays=dict(query_uv=xy,proposed_line_uv=uv,line_z=z,along_index=along,side_offset=side,inside=inside,native_z=native_z,native_alpha=native_a,query_alpha=qalpha,query_median_center_z=qmed,query_layer_width=qwidth,patch_valid=valid,original_child_id=np.asarray(case['child_ids']),world_line=X,csr_offsets=starts,source_index=np.concatenate([r['ids'] for r in rows]),weight=np.concatenate([r['weight'] for r in rows]),alpha_i=np.concatenate([r['alpha_i'] for r in rows]),T=np.concatenate([r['T'] for r in rows]),source_center_z=np.concatenate([r['z'] for r in rows]),participant_ids=diff['ids'],left_mass=diff['left'],right_mass=diff['right'],differential_responsibility=diff['difference'],left_patch_source_uv=xy[lc],right_patch_source_uv=xy[rc],left_points=np.asarray(left['points']).reshape(-1,3),right_points=np.asarray(right['points']).reshape(-1,3))
 result=dict(scene=case['scene'],case=case['case'],arm=arm,view=c['view'],parent_id=case['parent_id'],source_views=case['source_views'],source_only=True,query_count=len(rows),unique_pixel_count=len(cache),all_participants_kept=True,info=info,role=role,left_patch=left,right_patch=right,front_side=front,offset_evidence=offsets,overlap=diff['overlap'],participant_count=len(diff['ids']),positive_mass_participants=int(np.sum(diff['left']+diff['right']>0)),physical_primitive_reconstructed=False)
 return result,arrays

def calibration(s,c,raw,source,proj,out):
 ref=render(source,c,[1]*3 if s=='ficus' else [0]*3,.3 if s=='ficus' else .0144);z=raw['median_camera_z'].squeeze();al=raw['alpha'].squeeze();good=(z>.2)&np.isfinite(z)&(al>=.5)&(ref['median_center_z']>.2);m=dict(rgb_mae=float(abs(ref['rgb']-raw['rgb']).mean()),alpha_mae=float(abs(ref['alpha']-al).mean()),center_surface_p95=float(np.percentile(abs(ref['median_center_z'][good]-z[good])/z[good],95)))
 m['engineering_go']=m['rgb_mae']<=.02 and m['alpha_mae']<=.02 and m['center_surface_p95']<=.15;yy,xx=np.nonzero(good);ix=np.linspace(0,len(xx)-1,12,dtype=int);err=[];equal=[]
 for i in ix:
  q=[xx[i],yy[i]];a=proj.query(q);b=proj.query(q,all_N=True);assert np.array_equal(a['ids'],b['ids']);error=float(np.max(abs(a['weight']-b['weight']),initial=0));assert error<=2e-12;rgb=a['rgb']+a['trans']*(1 if s=='ficus' else 0);delta=float(max(np.max(abs(rgb-ref['rgb'][q[1],q[0]])),abs(a['alpha']-ref['alpha'][q[1],q[0]])));assert delta<=5e-7,(q,delta);err.append(delta);equal.append(error)
 m.update(all_N_pixels=12,all_N_max_error=max(equal),renderer_query_max_abs=max(err),source_count=len(source['means']),source_projection_invalid_ids=len(proj.invalid_source_ids));out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'REFERENCE.npz',**ref,original_rgb=raw['rgb'],original_depth=z,original_alpha=al);js(out/'CALIBRATION.json',m);seal(out);return ref,m

def run(s,views):
 cfg=json.loads((ROOT/'CONFIG.json').read_text());source=activate(read_ply(registry()[s]['model']));cases=[x for x in json.loads((ROOT/'CASE_FREEZE.json').read_text())['cases'] if x['scene']==s];out=ROOT/'scenes'/s/'stage1';out.mkdir(parents=True,exist_ok=True);allcounts=[]
 for v in views:
  guard();c=cam(s,v);raw=npz(rawpath(s,v));proj=ProjectedSource.from_asset(source,c,s);ref,cal=calibration(s,c,raw,source,proj,out/v/'reference')
  for case in cases:
   d=out/v/case['case'];d.mkdir(parents=True,exist_ok=True)
   if not case['selection_valid'] or not cal['engineering_go']:js(d/'UNAVAILABLE.json',dict(case=case['case'],selection_valid=case['selection_valid'],calibration_go=cal['engineering_go']));continue
   for arm in cfg['controls']:
    start=time.time();r,a=query_case(case,arm,c,raw,proj,source);p=d/arm;p.mkdir(exist_ok=True);np.savez_compressed(p/'EVIDENCE.npz',**a);js(p/'RESULT.json',r);seal(p);allcounts.append(dict(case=case['case'],view=v,arm=arm,role=r['role']['role'],participants=r['positive_mass_participants'],seconds=time.time()-start));print(s,v,case['case'],arm,r['role']['role'],flush=True)
  del proj
 js(out/('EXECUTION_'+views[0]+'.json'),dict(exit_code=0,counts=allcounts,views=views));return allcounts
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--secondary',action='store_true');a=p.parse_args();fail=[]
 for s in SCENES:
  try:state('SECONDARY_MEASURE' if a.secondary else 'DEV_MEASURE',scene=s,status='RUNNING',children=[os.getpid()]);run(s,VIEWS[s][1:] if a.secondary else [DEV[s]]);state('MEASURE_COMPLETE',status='READY_FOR_REVIEW',children=[])
  except Exception as e:js(ROOT/f'FAILURE_{s}_{"secondary" if a.secondary else "dev"}.json',dict(error=repr(e)));fail.append(s)
 if fail:state('MEASURE_FAILURE',status='ENGINEERING_NOT_READY',children=[],failed_scenes=fail);raise SystemExit(1)
