from env import np,json,R
CFG=json.loads((R/'CONFIG.json').read_text())
def infer_up(right,screen_up):
 r=np.asarray(right,float);s=np.asarray(screen_up,float);assert r.ndim==2 and r.shape[1]==3 and np.isfinite(r).all()
 ev,Q=np.linalg.eigh(r.T@r/len(r));u=Q[:,0];sign=np.sign(u@s.mean(0));u*=sign if sign else 1;rms=float(np.degrees(np.arcsin(np.sqrt(np.clip(ev[0],0,1)))));ratio=float(max(ev[0],0)/max(ev[1],1e-30))
 good=bool(ev[1]>.02 and ratio<=CFG['pose']['maximum_eigen_ratio'] and rms<=CFG['pose']['max_rms_degrees'] and abs(u@s.mean(0))>.1)
 return dict(up=u.tolist(),eigenvalues=ev.tolist(),rms_degrees=rms,eigen_ratio=ratio,qualified=good,not_gravity_truth=True)
def fit_support(X,p,view,per,central,up):
 A=CFG['plane'];X=np.asarray(X,float);p=np.asarray(p,float);v=np.asarray(view);pool=np.flatnonzero(per);uv=np.unique(v);rng=np.random.default_rng(CFG['seed']);best=None;scorebest=-1;limit=np.cos(np.radians(CFG['pose']['maximum_plane_tilt_degrees']));up=np.asarray(up)
 if len(pool)<2*A['counts_min'] or not central.any():return None
 if len(pool)>A['pool_cap']:pool=pool[np.linspace(0,len(pool)-1,A['pool_cap'],dtype=int)]
 ci=np.flatnonzero(central);ci=ci[np.linspace(0,len(ci)-1,min(len(ci),2000),dtype=int)];rejected=0
 for _ in range(A['hypotheses']):
  pts=X[rng.choice(pool,3,replace=False)];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);norm=np.linalg.norm(n)
  if norm<1e-12:continue
  n/=norm
  if abs(n@up)<limit:rejected+=1;continue
  d=-n@pts[0];good=abs(X[pool]@n+d)/p[pool]<=A['inlier_p'];fra=[float(good[v[pool]==i].mean()) if (v[pool]==i).any() else 0 for i in uv]
  if min(fra)<A['peripheral_min']:continue
  cf=float((abs(X[ci]@n+d)/p[ci]<=A['inlier_p']).mean())
  if cf>A['central_max']:continue
  if min(fra)>scorebest:best=(n,d);scorebest=min(fra)
 if best is None:return None
 n,d=best
 for _ in range(A['refit']):
  good=abs(X@n+d)/p<=A['inlier_p'];q=X[good];mid=q.mean(0);_,_,vt=np.linalg.svd((q-mid)/np.sqrt(p[good,None]),full_matrices=False);n=vt[-1];d=-n@mid
  if abs(n@up)<limit:return None
 if n@up<0:n=-n;d=-d
 r=(X@n+d)/p;good=abs(r)<=A['inlier_p'];fra=[float(good[per&(v==i)].mean()) for i in uv];counts=[int((good&per&(v==i)).sum()) for i in uv];cf=float(good[central].mean());sep=float(np.median(r[central]))
 if min(fra)<A['peripheral_min'] or min(counts)<A['counts_min'] or cf>A['central_max'] or abs(sep)<A['central_separation_p']:return None
 return dict(normal=n.tolist(),offset=float(d),sign=1 if sep>0 else -1,peripheral_fraction=fra,peripheral_inliers=counts,central_plane_fraction=cf,central_signed_median_p=sep,angle_to_up=float(np.degrees(np.arccos(np.clip(n@up,-1,1)))),orientation_rejected_hypotheses=rejected,not_physical_GT=True)
def plane_labels(X,p,m):
 d=(np.asarray(X)@np.asarray(m['normal'])+m['offset'])*m['sign']/p;r=np.full(len(d),-1,np.int8);r[d>CFG['plane']['mask_p']]=1;r[d< -CFG['plane']['mask_p']]=0;return r
