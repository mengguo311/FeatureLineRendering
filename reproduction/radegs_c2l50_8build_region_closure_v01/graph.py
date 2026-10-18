from env import *
from closure import *
from scipy.spatial import cKDTree
from scipy.ndimage import binary_dilation
from skimage.measure import find_contours
import networkx as nx

def sample_path(uv,z,step=1.):
 uv=np.asarray(uv);z=np.asarray(z);out=[];zz=[];piece=[]
 for j,(a,b) in enumerate(zip(uv[:-1],uv[1:])):
  n=max(1,int(np.ceil(np.linalg.norm(b-a)/step)));t=np.arange(n)/n;out.extend(a+t[:,None]*(b-a));zz.extend(1/((1-t)/z[j]+t/z[j+1]));piece.extend([j]*n)
 out.append(uv[-1]);zz.append(z[-1]);piece.append(max(0,len(uv)-2));return np.asarray(out),np.asarray(zz),np.asarray(piece)
def lookup(raw,uv):
 xy=np.rint(uv).astype(int);H,W=raw['alpha'].squeeze().shape;inside=(xy[:,0]>=0)&(xy[:,0]<W)&(xy[:,1]>=0)&(xy[:,1]<H);z=np.full(len(xy),np.nan);al=np.zeros(len(xy));rgb=np.zeros((len(xy),3));ii=xy[inside];z[inside]=raw['median_camera_z'].squeeze()[ii[:,1],ii[:,0]];al[inside]=raw['alpha'].squeeze()[ii[:,1],ii[:,0]];rgb[inside]=raw['rgb'][ii[:,1],ii[:,0]];return z,al,rgb,inside

def fragments(parents,c,raw,center,half=48,shift=0.):
 fs=[];ledger=[]
 for pid,p in enumerate(parents):
  uv,z=projection(np.asarray(p['control']),c);uv[:,0]+=shift
  if (uv.max(0)<center-half).any() or (uv.min(0)>center+half).any():continue
  # Bound giant projections without manufacturing a region: skip absurd/nearplane paths, record.
  if (z<=.2).any() or not np.isfinite(uv).all() or np.linalg.norm(np.diff(uv,axis=0),axis=1).sum()>20000:
   ledger.append(dict(parent=pid,reason='nearplane_or_projection_budget'));continue
  u,zz,piece=sample_path(uv,z);sd,al,_,inside=lookup(raw,u);vis=visible_state(zz,sd,al,np.sqrt(c['fx']*c['fy']));roi=(abs(u-center)<=half).all(1);ok=(vis=='visible')&inside&roi
  for v in np.unique(vis):ledger.append(dict(parent=pid,reason=str(v),samples=int((vis==v).sum())))
  starts=np.flatnonzero(ok&~np.r_[False,ok[:-1]]);ends=np.flatnonzero(ok&~np.r_[ok[1:],False])+1
  for lo,hi in zip(starts,ends):
   if hi-lo<2:continue
   fs.append(dict(uv=u[lo:hi],z=zz[lo:hi],parent=pid,indices=piece[lo:hi],end_ok=[bool(lo==0),bool(hi==len(u))],closed=bool(p['closed'] and lo==0 and hi==len(u)),source_views=p['source_views']))
 return fs,ledger

def boundary_evidence(uv,raw,c,n=32):
 u,z,_=sample_path(np.asarray(uv),np.ones(len(uv)));i=np.linspace(0,len(u)-2,n,dtype=int);q=u[i];d=u[np.minimum(i+1,len(u)-1)]-u[np.maximum(0,i-1)];d/=np.maximum(np.linalg.norm(d,axis=1)[:,None],1e-12);normal=np.c_[-d[:,1],d[:,0]]
 support=[];detail=[]
 for off in [2.,4.]:
  zl,al,cl,il=lookup(raw,q+normal*off);zr,ar,cr,ir=lookup(raw,q-normal*off);contrast=np.linalg.norm(cl-cr,axis=1)/np.sqrt(3);valid=il&ir;geom=np.isfinite(zl)&np.isfinite(zr)&(al>=.5)&(ar>=.5)&(zl>.2)&(zr>.2);p=np.minimum(zl,zr)/np.sqrt(c['fx']*c['fy']);jump=geom&(abs(zl-zr)>3*p);alphaedge=abs(al-ar)>.35;yes=valid&((contrast>=.025)|jump|alphaedge);support.append(yes);detail.append(dict(offset=off,contrast=contrast.tolist(),depth_step=jump.tolist(),alpha_boundary=alphaedge.tolist()))
 return dict(support_fraction=float((support[0]&support[1]).mean()),any_offset_fraction=float((support[0]|support[1]).mean()),slots=n,unique_pixels=int(len(np.unique(np.rint(q),axis=0))),evidence=detail)

def simple_polygon(uv):
 # Preserve samples, removing only exactly consecutive duplicates. Test proper crossings; no polygon repair.
 p=np.asarray(uv);p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-9]]
 if len(p)<4:return False
 if np.linalg.norm(p[0]-p[-1])>1e-8:p=np.r_[p,p[:1]]
 a=p[:-1];b=p[1:];N=len(a)
 for i in range(N):
  js=np.arange(i+2,N)
  if i==0:js=js[js!=N-1]
  if not len(js):continue
  u=b[i]-a[i];v=b[js]-a[js];cross=lambda x,y:x[...,0]*y[...,1]-x[...,1]*y[...,0]
  d1=cross(u,a[js]-a[i]);d2=cross(u,b[js]-a[i]);d3=cross(v,a[i]-a[js]);d4=cross(v,b[i]-a[js]);hit=(d1*d2 < -1e-12)&(d3*d4 < -1e-12)
  if hit.any():return False
 return True

def describe_region(uv,gaps,parents,shape,raw,c,kind='line_cycle'):
 p=np.asarray(uv)
 if np.linalg.norm(p[0]-p[-1])>1e-8:p=np.r_[p,p[:1]]
 if not simple_polygon(p):return None
 d=np.diff(p,axis=0);L=float(np.linalg.norm(d,axis=1).sum());area=float(abs(np.sum(p[:-1,0]*p[1:,1]-p[1:,0]*p[:-1,1]))/2);cl=closure_score(gaps,L)
 if L<24 or area<16:return None
 dirs=d/np.maximum(np.linalg.norm(d,axis=1)[:,None],1e-12);dot=np.sum(dirs*np.roll(dirs,1,axis=0),axis=1);turn=np.arccos(np.clip(dot,-1,1));bend=float(np.sum(turn**2));gapfrac=float(sum(gaps)/L)
 mask=region_mask([p],shape);ev=boundary_evidence(p,raw,c)
 reasons=[]
 if cl<.9:reasons.append('large_L2_gap')
 if gapfrac>.2:reasons.append('excess_gap_fraction')
 if (turn>np.deg2rad(150)).sum()>2:reasons.append('overfold')
 if ev['support_fraction']<.5:reasons.append('weak_independent_boundary')
 return dict(uv=p.tolist(),parents=sorted(set(parents)),gaps=list(map(float,gaps)),area=area,perimeter=L,closure=cl,gap_fraction=gapfrac,turn_squared=bend,overfolds=int((turn>np.deg2rad(150)).sum()),boundary=ev,qualified=len(reasons)==0,reasons=reasons or ['local_2D_hypothesis_only'],kind=kind,mask=mask)

def find_regions(fs,raw,c):
 shape=raw['alpha'].squeeze().shape;G=nx.Graph();ledger=[];regions=[];ends=[];tang=[];depth=[];usable=[]
 for i,f in enumerate(fs):
  u=f['uv'];zz=f['z'];t0=u[0]-u[min(3,len(u)-1)];t1=u[-1]-u[max(0,len(u)-4)];ts=[t0,t1];ts=[t/max(np.linalg.norm(t),1e-15) for t in ts]
  ends.extend([u[0],u[-1]]);tang.extend(ts);depth.extend([zz[0],zz[-1]]);usable.extend(f['end_ok']);G.add_edge(2*i,2*i+1,solid=True,frag=i)
  if f['closed']:
   r=describe_region(u,[],[f['parent']],shape,raw,c)
   if r is not None:regions.append(r)
 if not ends:return regions,ledger
 E=np.asarray(ends);pairs=sorted(cKDTree(E).query_pairs(6.));focal=np.sqrt(c['fx']*c['fy'])
 for a,b in pairs:
  if a//2==b//2:continue
  ok,why=link_gate(E[a],E[b],tang[a],tang[b],depth[a],depth[b],min(depth[a],depth[b])/focal,usable[a],usable[b]);record=dict(a=a,b=b,parent_a=fs[a//2]['parent'],parent_b=fs[b//2]['parent'],distance=float(np.linalg.norm(E[a]-E[b])),accepted=False,reason=why)
  if ok:
   # The possible link itself must be visible and source-depth-supported throughout.
   u,zz,_=sample_path(E[[a,b]],np.array(depth)[[a,b]]);sd,al,_,inside=lookup(raw,u);v=visible_state(zz,sd,al,focal)
   ok=bool(inside.all() and (v=='visible').all());record['reason']='local_hypothesis' if ok else 'gap_unobserved_or_wrong_layer'
  if ok:G.add_edge(a,b,solid=False,length=record['distance']);record['accepted']=True
  ledger.append(record)
 cycles=nx.cycle_basis(G);ledger.append(dict(cycle_basis_count=len(cycles),searched=min(4096,len(cycles)),exhaustive=False))
 for cyc in cycles[:4096]:
  ed=[(cyc[j],cyc[(j+1)%len(cyc)]) for j in range(len(cyc))];solid=[G[a][b]['solid'] for a,b in ed]
  if not all(solid[j]!=solid[(j+1)%len(solid)] for j in range(len(solid))):continue
  pts=[];gaps=[];parents=[]
  for a,b in ed:
   if G[a][b]['solid']:
    ff=fs[a//2];u=ff['uv'] if a%2==0 else ff['uv'][::-1];pts.extend(u);parents.append(ff['parent'])
   else:gaps.append(G[a][b]['length']);pts.extend([E[a],E[b]])
  r=describe_region(pts,gaps,parents,shape,raw,c)
  if r is not None:regions.append(r)
 # Dedupe polygon masks; projected duplicate curves are NOT new independent observations.
 out=[];seen=set()
 for r in sorted(regions,key=lambda x:(not x['qualified'],-x['closure'],x['gap_fraction'],x['turn_squared'],x['area'])):
  key=np.packbits(r['mask']).tobytes()
  if key in seen:continue
  seen.add(key);out.append(r)
 return out[:16],ledger

def no_line_regions(raw,c,center,half=48):
 H,W=raw['alpha'].squeeze().shape;x0,y0=np.maximum(0,np.floor(center-half)).astype(int);x1,y1=np.minimum([W,H],np.ceil(center+half+1)).astype(int);out=[]
 if x1<=x0 or y1<=y0:return out
 lum=raw['rgb'].mean(2);channels=[(lum,.25),(lum,.5),(lum,.75),(raw['alpha'].squeeze(),.5)]
 for field,level in channels:
  for contour in find_contours(field[y0:y1,x0:x1],level):
   if len(contour)<5 or np.linalg.norm(contour[0]-contour[-1])>1e-6:continue
   p=contour[:,::-1]+[x0,y0];r=describe_region(p,[],[],(H,W),raw,c,'source_only_levelset')
   if r is not None:r['level']=level;out.append(r)
 return sorted(out,key=lambda r:(not r['qualified'],-r['boundary']['support_fraction'],r['area']))[:16]

def transfer_region(mask,raw,c,raw2,c2,candidates):
 yy,xx=np.nonzero(mask);n=len(xx)
 if not n:return dict(iou=0.,comparable_fraction=0.,reason='empty',best=-1)
 uv=np.c_[xx,yy];z=raw['median_camera_z'].squeeze()[yy,xx];alpha=raw['alpha'].squeeze()[yy,xx];valid=np.isfinite(z)&(z>.2)&(alpha>=.5);X=unproject(uv[valid],z[valid],c);q,zz=projection(X,c2);sd,al,_,inside=lookup(raw2,q);vis=visible_state(zz,sd,al,np.sqrt(c2['fx']*c2['fy']));ok=inside&(vis=='visible');fraction=float(ok.sum()/n);dest=np.zeros_like(raw2['alpha'].squeeze(),bool);ix=np.rint(q[ok]).astype(int);dest[ix[:,1],ix[:,0]]=True
 # Equal 1px dilation on both masks mitigates forward-projection raster holes; no hole filling.
 a=binary_dilation(dest);ious=[]
 for b in candidates:
  b=binary_dilation(b);ious.append(float((a&b).sum()/max(1,(a|b).sum())))
 best=int(np.argmax(ious)) if ious else -1;return dict(iou=max(ious,default=0.),comparable_fraction=fraction,best=best,visible=int(ok.sum()),occluded=int((vis=='occluded').sum()),unknown=int((vis=='unknown').sum()),front_inconsistent=int((vis=='front_inconsistent').sum()),input_pixels=n,transfer_pixels=int(dest.sum()),reason='proxy_depth_forward_transfer_not_physical_region')
