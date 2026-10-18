"""Depth-visible samples, not source Gaussian centers or physical surface GT."""
from env import *
CFG=json.loads((ROOT/'CONFIG_FREEZE.json').read_text());A=CFG['stageA']
def visibility(uv,z,depth,alpha,c):
 uv=np.asarray(uv);z=np.asarray(z);fin=np.isfinite(uv).all(1)&np.isfinite(z)&(z>.2);q=np.rint(np.nan_to_num(uv)).astype(np.int64);inside=fin&(q[:,0]>=0)&(q[:,0]<c['width'])&(q[:,1]>=0)&(q[:,1]<c['height']);s=np.zeros(len(z),np.uint8);s[~inside]=3;ids=np.flatnonzero(inside);d=depth[q[ids,1],q[ids,0]];a=alpha[q[ids,1],q[ids,0]];good=np.isfinite(d)&(d>.2)&(a>=.5);tol=np.maximum(CFG['visibility']['relative_z']*d,CFG['visibility']['worldpixel_z']*d/np.sqrt(c['fx']*c['fy']));delta=z[ids]-d;s[ids[good&(abs(delta)<=tol)]]=1;s[ids[good&(delta>tol)]]=2;s[ids[good&(delta< -tol)]]=4;return s
def source_only(groups):
 if (np.asarray(groups)!=0).any():raise ValueError('Ink cannot be source evidence')
 return True
def border(shape):
 h,w=shape;y,x=np.mgrid[:h,:w];b=A['border_band'];return (x<b*w)|(x>=(1-b)*w)|(y<b*h)|(y>=(1-b)*h)
def isolated_coverage(alphas):
 return all(float((a[border(a.shape)]>=.5).mean())<A['isolated_border_fraction_max'] and float((a>=.5).mean())<A['isolated_total_coverage_max'] for a in alphas)
def samples(s,vs):
 rows=[]
 for vi,v in enumerate(vs):
  rgb,z,a=raw(s,v);c=cam(s,v);stride=CFG['common']['sample_stride'];yy,xx=np.mgrid[:z.shape[0]:stride,:z.shape[1]:stride];valid=np.isfinite(z[yy,xx])&(z[yy,xx]>.2)&(a[yy,xx]>=.5);uv=np.c_[xx[valid],yy[valid]];limit=CFG['common']['max_samples_per_view'];uv=uv[np.linspace(0,len(uv)-1,min(limit,len(uv)),dtype=int)];d=z[uv[:,1],uv[:,0]];p=d/np.sqrt(c['fx']*c['fy']);x=uv[:,0]/c['width'];y=uv[:,1]/c['height'];per=((x<A['border_band'])|(x>1-A['border_band'])|(y>1-A['border_band']))&(y>A['plane_seed_lower_y']);cen=((x-.5)/.18)**2+((y-.5)/.26)**2<1
  rows.append(dict(world=unproject(uv,d,c),uv=uv,pixel_scale=p,rgb=rgb[uv[:,1],uv[:,0]],view_id=np.full(len(uv),vi,np.int16),peripheral=per,central=cen,raw_z=d))
 return {k:np.concatenate([r[k] for r in rows]) for k in rows[0]}
def fit_support_plane(X,p,view,per,central):
 X=np.asarray(X,float);p=np.asarray(p,float);v=np.asarray(view);pool=np.flatnonzero(per);uv=np.unique(v);rng=np.random.default_rng(CFG['common']['seed']);best=None;bestscore=-1.;receipts=[]
 if len(pool)<2*A['plane_min_each_view'] or not central.any():return None
 if len(pool)>A['plane_pool_cap']:pool=pool[np.linspace(0,len(pool)-1,A['plane_pool_cap'],dtype=int)]
 # Score bounded hypothesis pool; qualifying decision always uses all recorded samples.
 center_ids=np.flatnonzero(central);center_ids=center_ids[np.linspace(0,len(center_ids)-1,min(len(center_ids),2000),dtype=int)]
 for _ in range(A['plane_hypotheses']):
  pts=X[rng.choice(pool,3,replace=False)];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);norm=np.linalg.norm(n)
  if norm<1e-12:continue
  n/=norm;d=-n@pts[0];r=abs(X[pool]@n+d)/p[pool];ok=r<=A['plane_inlier_worldpixels'];fra=[float(ok[v[pool]==j].mean()) if (v[pool]==j).any() else 0 for j in uv]
  if min(fra)<A['plane_peripheral_fraction_min']:continue
  cf=float((abs(X[center_ids]@n+d)/p[center_ids]<=A['plane_inlier_worldpixels']).mean())
  if cf>A['plane_central_fraction_max']:continue
  score=min(fra)
  if score>bestscore:best=(n,d);bestscore=score
 if best is None:return None
 n,d=best
 for _ in range(A['plane_refit_steps']):
  good=abs(X@n+d)/p<=A['plane_inlier_worldpixels'];q=X[good];mid=q.mean(0);_,_,vt=np.linalg.svd((q-mid)/np.sqrt(p[good,None]),full_matrices=False);n=vt[-1];d=-n@mid
 r=(X@n+d)/p;good=abs(r)<=A['plane_inlier_worldpixels'];fra=[float(good[per&(v==j)].mean()) if (per&(v==j)).any() else 0 for j in uv];counts=[int((good&per&(v==j)).sum()) for j in uv];cf=float(good[central].mean());sep=float(np.median(r[central]));sign=1 if sep>0 else -1
 if min(fra)<A['plane_peripheral_fraction_min'] or min(counts)<A['plane_min_each_view'] or cf>A['plane_central_fraction_max'] or abs(sep)<A['plane_min_seed_separation_worldpixels']:return None
 return dict(normal=n.tolist(),offset=float(d),sign=sign,peripheral_fraction=fra,peripheral_inliers=counts,central_plane_fraction=cf,central_signed_median_worldpixels=sep,hypotheses=A['plane_hypotheses'],not_physical_GT=True)
def plane_classify(X,p,m):
 d=(np.asarray(X)@np.asarray(m['normal'])+m['offset'])*m['sign']/np.asarray(p);r=np.full(len(d),-1,np.int8);r[d>A['plane_mask_worldpixels']]=1;r[d< -A['plane_mask_worldpixels']]=0;return r
def plane_mask(z,a,c,m):
 yy,xx=np.mgrid[:z.shape[0],:z.shape[1]];valid=np.isfinite(z)&(z>.2)&(a>=.5);uv=np.c_[xx[valid],yy[valid]];d=z[valid];lab=plane_classify(unproject(uv,d,c),d/np.sqrt(c['fx']*c['fy']),m);mask=np.zeros_like(valid);unknown=(a>=.1)&~valid;mask[valid]=lab==1;unknown[valid]=lab==-1;return mask,unknown
def coverage_mask(z,a):
 valid=np.isfinite(z)&(z>.2);mask=(a>=.5)&valid;unknown=(a>=.1)&((a<.5)|~valid);return mask,unknown
def directed_overlap(s,v,tv,m,tm):
 _,z,a=raw(s,v);_,tz,ta=raw(s,tv);c=cam(s,v);tc=cam(s,tv);stride=CFG['visibility']['stride'];yy,xx=np.mgrid[:m.shape[0]:stride,:m.shape[1]:stride];ok=m[yy,xx]&np.isfinite(z[yy,xx])&(z[yy,xx]>.2)&(a[yy,xx]>=.5);uv=np.c_[xx[ok],yy[ok]];X=unproject(uv,z[uv[:,1],uv[:,0]],c);q,d=projection(X,tc);st=visibility(q,d,tz,ta,tc);ix=np.flatnonzero(st==1);xy=np.rint(q[ix]).astype(int);hit=tm[xy[:,1],xy[:,0]];result=dict(n=len(st),visible=len(ix),comparable_fraction=float(len(ix)/max(len(st),1)),retained=float(hit.mean()) if len(ix) else None,occluded=int((st==2).sum()),front_inconsistent=int((st==4).sum()),unknown=int((st==0).sum()),outside=int((st==3).sum()))
 return result,dict(source_uv=uv,target_uv=q,target_z=d,state=st,visible_hit=hit)
