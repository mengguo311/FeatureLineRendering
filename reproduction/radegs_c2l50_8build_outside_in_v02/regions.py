"""Shared multi-view visible-sample coarse regions; no source GS identities as features."""
from env import *
from anchor import visibility
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from sklearn.cluster import KMeans
from skimage.color import rgb2lab
CFG=json.loads((ROOT/'CONFIG_FREEZE.json').read_text());B=CFG['stageB']
def make_features(X,rgb,width,m):
 xyz=(X-m['origin'])/(m['scale']*B['spatial_scale_fraction']);lab=rgb2lab(np.clip(rgb,0,1).reshape(-1,1,3)).reshape(-1,3)/np.asarray(B['lab_scale']);thick=B['thickness_weight']*np.log1p(np.maximum(width,0)/(B['thickness_scale_fraction']*m['scale']))
 if m['arm']=='shared_xyz_lab_width':return np.c_[xyz,lab,thick]
 if m['arm']=='shared_rgb_only':return lab
 if m['arm']=='shared_xyz_only':return xyz
 raise ValueError('unsupported arm')
def fit_model(X,rgb,width,k,arm,pixel_scale=None):
 X=np.asarray(X,float);lo,hi=np.quantile(X,[.01,.99],axis=0);scale=float(np.linalg.norm(hi-lo));assert scale>0
 m=dict(arm=arm,origin=(lo+hi)/2,scale=scale,anchors=X.copy(),reference_p=float(np.median(pixel_scale)) if pixel_scale is not None else scale/1000)
 f=make_features(X,rgb,width,m);fit=KMeans(n_clusters=k,random_state=CFG['common']['seed'],n_init=B['kmeans_n_init'],max_iter=B['kmeans_max_iter'],algorithm='lloyd').fit(f);cent=fit.cluster_centers_;order=np.lexsort(cent.T[::-1]);m.update(centers=cent[order],k=k,inertia=float(fit.inertia_),iterations=int(fit.n_iter_),sample_count=len(X));return m
def predict_features(X,rgb,width,m,pixel_scale=None):
 f=make_features(X,rgb,width,m);ds=((f[:,None,:]-m['centers'][None,:,:])**2).sum(2);score=-ds/(2*B['soft_temperature']**2);score-=score.max(1,keepdims=True);prob=np.exp(score);prob/=prob.sum(1,keepdims=True);order=np.sort(prob,axis=1);margin=order[:,-1]-order[:,-2];nearest=cKDTree(m['anchors']).query(X,workers=1)[0];ps=np.full(len(X),m['reference_p']) if pixel_scale is None else pixel_scale;radius=np.maximum(B['anchor_support_radius_worldpixels']*ps,B['anchor_support_radius_fraction']*m['scale']);supported=nearest<=radius;known=(order[:,-1]>=B['minimum_posterior'])&(margin>=B['minimum_margin'])&supported;lab=(np.argmax(prob,1)+1).astype(np.int16);lab[~known]=0
 return dict(labels=lab,probability=prob.astype(np.float32),margin=margin.astype(np.float32),nearest_observed_distance=nearest.astype(np.float32),observed_neighborhood=supported)
def region_gate(mutual_count,unknown_fraction,visual):
 return 'GO_PROXY' if mutual_count>=CFG['gates']['B_min_stable_regions'] and unknown_fraction<=CFG['gates']['B_max_unknown'] and visual else 'NO_GO'
def mutual_pairs(ab,ba):
 t=CFG['gates']['B_mutual_fraction'];return [(i,j) for i,(j,p) in sorted(ab.items()) if p>=t and j in ba and ba[j][0]==i and ba[j][1]>=t]
def soft_source_region(region_ids,weights,k):
 # Pure API safeguard only. No source responsibility production unless Stage D is allowed.
 mass=np.bincount(np.asarray(region_ids),weights=np.asarray(weights),minlength=k+1)[1:k+1];mass/=max(mass.sum(),1e-30);return mass,bool(mass.max(initial=0)<.75)
def view_samples(s,v,limit=None):
 rgb,z,a=raw(s,v);c=cam(s,v);subject=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');mask=subject['candidate'];good=mask&np.isfinite(z)&(z>.2)&(a>=.5)&~subject['unknown'];stride=CFG['common']['sample_stride'];yy,xx=np.mgrid[:z.shape[0]:stride,:z.shape[1]:stride];uv=np.c_[xx[good[yy,xx]],yy[good[yy,xx]]]
 if limit is not None and len(uv)>limit:uv=uv[np.linspace(0,len(uv)-1,limit,dtype=int)]
 p=z[uv[:,1],uv[:,0]]/np.sqrt(c['fx']*c['fy']);dt=ndi.distance_transform_edt(mask)
 return dict(world=unproject(uv,z[uv[:,1],uv[:,0]],c),rgb=rgb[uv[:,1],uv[:,0]],width=dt[uv[:,1],uv[:,0]]*p,pixel_scale=p,uv=uv)
def predict_view(s,v,m):
 rgb,z,a=raw(s,v);c=cam(s,v);subject=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');mask=subject['candidate'];good=mask&np.isfinite(z)&(z>.2)&(a>=.5)&~subject['unknown'];yy,xx=np.nonzero(good);uv=np.c_[xx,yy];p=z[yy,xx]/np.sqrt(c['fx']*c['fy']);X=unproject(uv,z[yy,xx],c);width=ndi.distance_transform_edt(mask)[yy,xx]*p;r=predict_features(X,rgb[yy,xx],width,m,p);lab=np.zeros(z.shape,np.int16);lab[yy,xx]=r['labels'];post=np.zeros((*z.shape,m['k']),np.float32);post[yy,xx]=r['probability'];unknown=(mask&(lab==0))|subject['unknown'];return dict(labels=lab,probability=post,unknown=unknown,query_uv=uv,nearest_observed_distance=r['nearest_observed_distance'],observed_neighborhood=r['observed_neighborhood'])
def match(s,v,tv,lab,tlab):
 _,z,a=raw(s,v);_,tz,ta=raw(s,tv);c=cam(s,v);tc=cam(s,tv);stride=CFG['visibility']['stride'];yy,xx=np.mgrid[:z.shape[0]:stride,:z.shape[1]:stride];size=np.bincount(lab.ravel());tsize=np.bincount(tlab.ravel());minarea=CFG['gates']['B_min_region_fraction']*int(npz(ROOT/'stageA'/s/v/'SUBJECT.npz')['candidate'].sum());pred={};rows=[];arrays=[]
 for gid in np.flatnonzero(size>=minarea):
  if gid==0:continue
  good=(lab[yy,xx]==gid)&np.isfinite(z[yy,xx])&(z[yy,xx]>.2)&(a[yy,xx]>=.5);uv=np.c_[xx[good],yy[good]];X=unproject(uv,z[uv[:,1],uv[:,0]],c);pv,pz=projection(X,tc);st=visibility(pv,pz,tz,ta,tc);ix=np.flatnonzero(st==1);q=np.rint(pv[ix]).astype(int);t=tlab[q[:,1],q[:,0]];known=t>0;ct=np.bincount(t[known],minlength=int(tlab.max())+1);ct[0]=0;target=int(ct.argmax()) if known.any() else 0;fraction=float(ct[target]/max(known.sum(),1));eligible=len(ix)/max(len(st),1)>=CFG['visibility']['minimum_visible_fraction'] and known.sum()>=CFG['visibility']['minimum_visible_samples'];unknown_fraction=float((~known).sum()/max(len(ix),1))
  if eligible and unknown_fraction<=CFG['gates']['B_max_unknown']:pred[int(gid)]=(target,fraction)
  rows.append(dict(region=int(gid),target=target,source_area=int(size[gid]),target_area=int(tsize[target]) if target else 0,samples=len(st),visible=len(ix),target_unknown=int((~known).sum()),known=int(known.sum()),dominant_fraction=fraction,visible_fraction=float(len(ix)/max(len(st),1)),eligible=bool(eligible),occluded=int((st==2).sum()),front_inconsistent=int((st==4).sum()),outside=int((st==3).sum()),unknown_depth=int((st==0).sum())))
  arrays.append(dict(region=np.full(len(st),gid,np.int16),source_uv=uv,target_uv=pv,state=st,target_label=np.full(len(st),-1,np.int16)))
  arrays[-1]['target_label'][ix]=t
 return pred,rows,{k:np.concatenate([r[k] for r in arrays]) for k in arrays[0]} if arrays else {}
