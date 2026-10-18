from env import *
from conditional import weighted_quantile

def compose_weights(alpha,depth):
 order=np.argsort(depth,kind='stable');a=np.clip(np.asarray(alpha)[order],0,.999);T=np.r_[1.,np.cumprod(1-a)[:-1]] if len(a) else np.empty(0);a=a*(T>=1e-5);T=np.r_[1.,np.cumprod(1-a)[:-1]] if len(a) else np.empty(0);out=np.empty(len(a));out[order]=a*T;return out

def visibility_states(line_z,native,alpha,inside,p):
 out=np.full(len(line_z),'UNKNOWN',dtype='<U24');out[~inside]='OUT_OF_FRAME';ok=inside&np.isfinite(native)&(native>.2)&(alpha>=.5)&np.isfinite(line_z)&(line_z>.2);tol=np.maximum(.02*native,4*p);out[ok&(abs(line_z-native)<=tol)]='COMPARABLE';out[ok&(line_z>native+tol)]='OCCLUDED';out[ok&(line_z<native-tol)]='IN_FRONT_INCONSISTENT';return out

def evaluate_frozen(patch,X,w,ids,pix,p,comparable):
 from partition import source_distribution,overlap_of
 out=dict(eligible=False,state='UNOBSERVED',negative_evidence=False,physical_primitive_certified=False)
 if comparable<.6 or len(np.unique(pix))<10 or not patch.get('valid'):return out
 _,ii=np.unique(pix,return_inverse=True);w=w/np.maximum(np.bincount(ii,weights=w)[ii],1e-30);r=(X-np.asarray(patch['center']))@np.asarray(patch['normal']);rms=float(np.sqrt(np.average(r*r,weights=w))/p);ia,wa=source_distribution(ids,w);overlap=overlap_of(ia,wa,np.asarray(patch['ids']),np.asarray(patch['mass']));ok=rms<=1 and overlap>=.15
 out.update(eligible=bool(ok),state='SUPPORTED_PROXY_ONLY' if ok else 'VISIBLE_DISAGREEMENT',negative_evidence=not bool(ok),source_overlap=overlap,rms_p=rms,unique_pixels=len(np.unique(pix)),parameters_unchanged=True);return out

def ordering_diagnostic(e,a,proj,p):
 ids=e['source_index'];ix=np.searchsorted(proj.ids,ids);assert np.array_equal(proj.ids[ix],ids);row=e['conditional_row'];d=e['query_uv'][row]-proj.uv[ix];S=proj.S[ix];q=(S[:,1,1]*d[:,0]**2-2*S[:,0,1]*d[:,0]*d[:,1]+S[:,0,0]*d[:,1]**2)/proj.det[ix];rawalpha=np.clip(a['opacity'][ids]*np.exp(-.5*q),0,.999)
 # Includes all finite-EWA contributors; original early-stop zeros are NOT treated as raw opacity.
 newdepth=np.where(e['conditional_valid'],e['conditional_z'],e['source_center_z']);wnew=np.zeros(len(ids));stats=np.full((len(e['query_uv']),9),np.nan);replay=0.
 for j,(lo,hi) in enumerate(zip(e['csr_offsets'][:-1],e['csr_offsets'][1:])):
  w0=compose_weights(rawalpha[lo:hi],e['source_center_z'][lo:hi]);wn=compose_weights(rawalpha[lo:hi],newdepth[lo:hi]);replay=max(replay,float(np.max(abs(w0-e['weight'][lo:hi]),initial=0)));wnew[lo:hi]=wn;total0=w0.sum();totaln=wn.sum();valid=e['conditional_valid'][lo:hi];z=e['conditional_z'][lo:hi];q0=weighted_quantile(z,w0*valid,.5);qn=weighted_quantile(z,wn*valid,.5);width=weighted_quantile(z,wn*valid,.9)-weighted_quantile(z,wn*valid,.1);native=e['native_z'][j];stats[j]=[np.sum(abs(w0/max(total0,1e-30)-wn/max(totaln,1e-30))),q0,qn,width,(wn*valid).sum()/max(totaln,1e-30),abs(q0-native)/p if native>.2 else np.nan,abs(qn-native)/p if native>.2 else np.nan,total0,totaln]
 assert replay<=2e-12,replay
 ci=np.flatnonzero(e['side_offset']==0);vis=visibility_states(e['line_z'],e['native_z'][ci],e['native_alpha'][ci],e['inside'][ci],p);ok=e['patch_valid']&(e['conditional_stats'][:,4]>=.8)&(stats[:,4]>=.8)&np.isfinite(stats[:,5:7]).all(1)
 summary=dict(unknown_sort_fallback='source mean depth if conditional qmin/near invalid',original_weight_replay_max=replay,matched_error_pixels=int(ok.sum()),same_budget_query_pixels=len(stats),old_conditional_native_error_p=float(np.median(stats[ok,5])) if ok.any() else None,reordered_conditional_native_error_p=float(np.median(stats[ok,6])) if ok.any() else None,mean_responsibility_L1=float(np.nanmean(stats[:,0])),mean_unknown_mass_original=float(np.mean(1-e['conditional_stats'][:,4])),mean_unknown_mass_reordered=float(np.mean(1-stats[:,4])),source_visibility_counts={v:int(np.sum(vis==v)) for v in np.unique(vis)},no_physical_depth_GT=True,original_sort='mean z',alternative='conditional mode valid, mean z otherwise; ROI diagnostic only')
 return dict(reordered_weight=wnew,raw_alpha=rawalpha,ordering_stats=stats,visibility=vis),summary

def alln_roi(proj,e):
 uv=np.unique(e['query_uv'][e['inside']],axis=0);ix=np.linspace(0,len(uv)-1,min(3,len(uv))).astype(int) if len(uv) else [];errors=[]
 for j in ix:
  x=proj.query(uv[j]);y=proj.query(uv[j],all_N=True);assert np.array_equal(x['ids'],y['ids']);errors.append(float(np.max(abs(x['weight']-y['weight']),initial=0)));assert errors[-1]<=2e-12
 return dict(pixels=uv[ix].tolist() if len(ix) else [],all_N_max=max(errors,default=0),count=len(ix))

def evaluate_models(s,case,arm,v,e,base):
 from partition import extract_points
 p=base['info']['pixel_world_proxy'];d=extract_points(e,p,cam(s,v));ci=np.flatnonzero(e['side_offset']==0);vis=visibility_states(e['line_z'],e['native_z'][ci],e['native_alpha'][ci],e['inside'][ci],p);fraction=float(np.mean(vis=='COMPARABLE'));out=[]
 for train_v in [DEV[s],AUX[s]]:
  path=ROOT/'round2/models'/s/train_v/case/arm/'RESULT.json';r=json.loads(path.read_text())
  for patch in r['patches']:
   result=evaluate_frozen(patch,d['X'],d['weight'],d['source_index'],d['pixel_id'],p,fraction);result.update(frozen_view=train_v,patch=patch['local_patch_id'],frozen_model_hash=sha(path),model=r['model']);out.append(result)
 return out
