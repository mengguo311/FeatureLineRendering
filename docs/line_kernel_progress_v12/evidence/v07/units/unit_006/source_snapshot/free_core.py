"""Frozen-kernel finite-curve competition. All geometry is normalized by p."""
import numpy as np
from scipy.spatial import cKDTree
from scipy.linalg import solve
EPS=1e-8

def arc(q):return np.r_[0.,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
def project(x,q):
 a=q[:-1];v=np.diff(q,axis=0);ll=np.sum(v*v,axis=1);u=np.clip(np.einsum('nsi,si->ns',x[:,None,:]-a,v)/np.maximum(ll,1e-30),0,1);ds=np.sum((x[:,None,:]-a-u[:,:,None]*v)**2,axis=2);j=ds.argmin(1);w=u[np.arange(len(x)),j];return np.sqrt(ds[np.arange(len(x)),j]),arc(q)[j]+w*np.sqrt(ll[j]),j,w

def geometry_ok(q):
 if len(q)<2 or not np.isfinite(q).all():return False,'invalid'
 v=np.diff(q,axis=0);l=np.linalg.norm(v,axis=1)
 if np.any(l<EPS):return False,'zero_segment'
 t=v/l[:,None];angles=np.degrees(np.arccos(np.clip(np.sum(t[:-1]*t[1:],axis=1),-1,1)))
 if np.any(angles>30+EPS):return False,'vertex_turn'
 s=arc(q)[1:-1];cs=np.r_[0.,np.cumsum(angles)]
 for i,z in enumerate(s):
  j=np.searchsorted(s,z+8,side='right')
  if cs[j]-cs[i]>60+EPS:return False,'window_turn'
 # Exact nonadjacent segment distance: endpoints plus interior closest pair.
 ii,jj=np.triu_indices(len(v),2)
 if len(ii):
  a=q[:-1][ii];b=q[:-1][jj];u=v[ii];w=v[jj];r=a-b
  aa=np.sum(u*u,1);bb=np.sum(u*w,1);cc=np.sum(w*w,1);dd=np.sum(u*r,1);ee=np.sum(w*r,1);den=aa*cc-bb*bb
  sc=np.divide(bb*ee-cc*dd,den,out=np.zeros_like(den),where=abs(den)>1e-14);tc=np.divide(aa*ee-bb*dd,den,out=np.zeros_like(den),where=abs(den)>1e-14)
  ds=np.where((abs(den)>1e-14)&(sc>=0)&(sc<=1)&(tc>=0)&(tc<=1),np.sum((r+sc[:,None]*u-tc[:,None]*w)**2,1),np.inf)
  for p,z,d in [(a,b,w),(a+u,b,w),(b,a,u),(b+w,a,u)]:
   h=np.clip(np.sum((p-z)*d,1)/np.sum(d*d,1),0,1);ds=np.minimum(ds,np.sum((p-z-h[:,None]*d)**2,1))
  if np.any(ds<.25-EPS):return False,'self_contact'
 return True,'ok'

def resample(q):
 s=arc(q);n=int(np.ceil(s[-1]-EPS))+1
 if n>129:raise ValueError('knot_cap')
 z=np.linspace(0,s[-1],max(2,n));return np.stack([np.interp(z,s,q[:,k]) for k in range(3)],1)
def slice_q(q,lo,hi):
 s=arc(q);lo=max(0.,lo);hi=min(s[-1],hi);z=np.r_[lo,s[(s>lo+EPS)&(s<hi-EPS)],hi];z=np.unique(z)
 if len(z)<2:return None
 return np.stack([np.interp(z,s,q[:,k]) for k in range(3)],1)

def assign(x,t,valid,models,guard=lambda:None):
 n=len(x);best=np.full(n,np.inf);second=best.copy();bi=np.full(n,-1,np.int64);si=bi.copy();bs=np.zeros(n);bj=np.full(n,-1,np.int32);bu=np.zeros(n);count=np.zeros(n,np.int32)
 vr=np.flatnonzero(valid);tree=cKDTree(x[vr]) if len(vr) else None
 for mid,q in sorted(models.items()):
  guard();mc=np.full(n,np.inf);ms=np.zeros(n);mj=np.full(n,-1,np.int32);mu=np.zeros(n);ar=arc(q)
  for j,(a,b) in enumerate(zip(q[:-1],q[1:])):
   v=b-a;l=np.linalg.norm(v)
   if l<EPS or tree is None:continue
   rr=vr[np.asarray(tree.query_ball_point((a+b)/2,l/2+1+EPS,workers=1),dtype=np.int64)]
   if not len(rr):continue
   u=np.clip((x[rr]-a)@v/(l*l),0,1);dist=np.linalg.norm(x[rr]-a-u[:,None]*v,axis=1);ang=np.degrees(np.arccos(np.clip(np.abs(t[rr]@(v/l)),0,1)));ok=(dist<=1+EPS)&(ang<=30+EPS);rr=rr[ok];u=u[ok];co=dist[ok]**2+.25*(ang[ok]/30)**2
   take=co<mc[rr];rr=rr[take];mc[rr]=co[take];ms[rr]=ar[j]+u[take]*l;mj[rr]=j;mu[rr]=u[take]
  finite=np.isfinite(mc);count+=finite
  win=finite&(mc<best);other=finite&~win&(mc<second)
  second[win]=best[win];si[win]=bi[win];second[other]=mc[other];si[other]=mid
  best[win]=mc[win];bi[win]=mid;bs[win]=ms[win];bj[win]=mj[win];bu[win]=mu[win]
 # UNKNOWN is an explicit competitor, so a nearly cost-one fit can abstain.
 margin=np.minimum(second,1)-best;ids=bi.copy();ids[(best>=1)|(margin<=.05)|~valid]=-1
 reason=np.zeros(n,np.uint8);reason[~valid]=1;reason[valid&~np.isfinite(best)]=2;reason[valid&np.isfinite(best)&(ids<0)]=3
 return dict(edge_id=ids,alternatives=np.c_[bi,si],alternative_cost=np.c_[best,second],s=bs,segment=bj,u=bu,reason_code=reason,eligible_models=count)

def union(intervals):
 if not len(intervals):return [],0.,0.,0.,0.
 z=sorted(map(tuple,intervals));out=[list(z[0])]
 for a,b in z[1:]:
  if a<=out[-1][1]+EPS:out[-1][1]=max(out[-1][1],b)
  else:out.append([a,b])
 lengths=[b-a for a,b in out];g=[out[i+1][0]-out[i][1] for i in range(len(out)-1)];return out,float(sum(lengths)),float(max(lengths)),float(sum(g)),float(max(g,default=0))

def validate_support(x,half,models,a,next_id,guard=lambda:None):
 b={k:v.copy() for k,v in a.items()};out={};events=[]
 for mid,q in sorted(models.items()):
  guard();rr=np.flatnonzero(a['edge_id']==mid)
  if not len(rr):events.append(dict(operation='death',model=mid,reason='no_primary'));continue
  s=a['s'][rr];L=arc(q)[-1];ints=np.c_[np.maximum(0,s-half[rr]),np.minimum(L,s+half[rr])];merged=union(ints)[0];pieces=[]
  for lo,hi in merged:
   if pieces and lo-pieces[-1][1]<=1.5+EPS:pieces[-1][1]=hi
   else:pieces.append([lo,hi])
  split=len(pieces)>1
  for lo,hi in pieces:
   z=rr[(s>=lo-EPS)&(s<=hi+EPS)]
   if len(z)<12 or len(np.unique(np.floor(a['s'][z]-lo).astype(np.int64)))<6:
    b['edge_id'][z]=-1;b['reason_code'][z]=4;events.append(dict(operation='death_piece',model=mid,rows=len(z),domain=[lo,hi]));continue
   # Static curves stay unchanged unless a required gap split creates children.
   nq=slice_q(q,lo,hi) if split else q.copy()
   if nq is None or not geometry_ok(nq)[0]:b['edge_id'][z]=-1;b['reason_code'][z]=5;continue
   cid=next_id if split else mid
   if split:next_id+=1
   out[cid]=nq;b['edge_id'][z]=cid
   if split:
    _,ss,jj,uu=project(x[z],nq);b['s'][z]=ss;b['segment'][z]=jj;b['u'][z]=uu
    events.append(dict(operation='gap_split',parent=mid,child=cid,domain=[lo,hi],rows=len(z)))
  # no qualifying support leaves any phantom primary labels
  bad=rr[~np.isin(b['edge_id'][rr],list(out))];b['edge_id'][bad]=-1
 return out,b,events,next_id

class Field:
 def __init__(self,x,t,rows,guard=lambda:None):
  self.guard=guard;self.rows=np.asarray(rows);xx=x[rows];tt=t[rows]
  if not len(rows):self.x=np.empty((0,3));self.t=self.x.copy();self.seed=np.array([],int);self.tree=None;self.order=self.seed;return
  keys,inv=np.unique(np.floor(xx).astype(np.int64),axis=0,return_inverse=True);n=len(keys);cnt=np.bincount(inv)
  self.x=np.stack([np.bincount(inv,weights=xx[:,k])/cnt for k in range(3)],1)
  mat=np.empty((n,3,3))
  for i in range(3):
   for j in range(3):mat[:,i,j]=np.bincount(inv,weights=tt[:,i]*tt[:,j])/cnt
  _,vec=np.linalg.eigh(mat);self.t=vec[:,:,-1];k=np.argmax(abs(self.t),1);self.t*=np.where(self.t[np.arange(n),k]<0,-1,1)[:,None]
  self.seed=np.full(n,np.iinfo(np.int64).max,dtype=np.int64);np.minimum.at(self.seed,inv,rows);self.tree=cKDTree(self.x)
  counts=np.empty(n,int)
  for start in range(0,n,4096):guard();counts[start:start+4096]=self.tree.query_ball_point(self.x[start:start+4096],2,return_length=True,workers=1)
  self.order=np.lexsort((self.seed,-counts))
 def step(self,pos,direction):
  pred=pos+direction;ds,ix=self.tree.query(pred,k=min(32,len(self.x)),distance_upper_bound=2+EPS,workers=1);ds=np.atleast_1d(ds);ix=np.atleast_1d(ix);ok=np.isfinite(ds)&(ix<len(self.x));ds=ds[ok];ix=ix[ok]
  if not len(ix):return None
  order=np.lexsort((self.seed[ix],ds));ix=ix[order];ds=ds[order];v=self.x[ix]-pred;tt=self.t[ix];dot=tt@direction;ok=(np.abs(dot)>=np.cos(np.pi/6)-EPS)&(np.abs(v@direction)<=.5+EPS)
  if not ok.any():return None
  v=v[ok];tt=tt[ok]*np.where(dot[ok]<0,-1,1)[:,None];ww=np.exp(-.5*ds[ok]**2);corr=np.average(v,axis=0,weights=ww);corr-=direction*(corr@direction);norm=np.linalg.norm(corr);corr*=min(1,.5/max(norm,EPS));nt=np.average(tt,axis=0,weights=ww);nt/=max(np.linalg.norm(nt),EPS)
  return pred+corr,nt
 def trace(self,i,steps=64):
  sides=[]
  for sign in (-1,1):
   q=[self.x[i].copy()];dire=self.t[i]*sign
   for j in range(steps):
    if j%8==0:self.guard()
    z=self.step(q[-1],dire)
    if z is None:break
    nq=np.array(q+[z[0]])
    if not geometry_ok(nq)[0]:break
    q.append(z[0]);dire=z[1]
   sides.append(np.array(q))
  q=np.concatenate([sides[0][::-1],sides[1][1:]])
  if len(q)<2:return None
  # Tracing has a hard129-knot limit; resample without adding length.
  if arc(q)[-1]>128:q=slice_q(q,0,128)
  q=resample(q)
  return q if geometry_ok(q)[0] else None

def discover(field,existing,next_id,limit,guard=lambda:None):
 models={k:v.copy() for k,v in existing.items()};new={};log=[];tree=None;aa=vv=ll=mm=None
 def rebuild():
  nonlocal tree,aa,vv,ll,mm
  if not models:tree=None;return
  aa=np.concatenate([q[:-1] for q in models.values()]);bb=np.concatenate([q[1:] for q in models.values()]);vv=bb-aa;ll=np.linalg.norm(vv,axis=1);mm=(aa+bb)/2;tree=cKDTree(mm)
 rebuild();scanned=0
 for i in field.order:
  guard();scanned+=1;p=field.x[i]
  if tree is not None:
   jj=np.asarray(tree.query_ball_point(p,.5+float(ll.max())/2+EPS),int)
   if len(jj):
    u=np.clip(np.sum((p-aa[jj])*vv[jj],1)/ll[jj]**2,0,1);dist=np.linalg.norm(p-aa[jj]-u[:,None]*vv[jj],axis=1);ang=abs((vv[jj]/ll[jj,None])@field.t[i])
    if np.any((dist<=.5+EPS)&(ang>=np.cos(np.deg2rad(15))-EPS)):continue
  q=field.trace(i)
  if q is None:log.append(dict(seed_row=int(field.seed[i]),reason='trace_failed'));continue
  mid=next_id;next_id+=1;new[mid]=q;models[mid]=q;log.append(dict(seed_row=int(field.seed[i]),model=mid,knots=len(q),reason='birth'));rebuild()
  if len(new)>=limit:break
 return new,next_id,dict(seed_count=len(field.order),seeds_scanned=scanned,unvisited_seeds=len(field.order)-scanned,cap=limit,truncated=scanned<len(field.order),events=log)

def irls_update(x,q):
 dist,s,j,u=project(x,q);n=len(q);A=np.zeros((len(x),n));A[np.arange(len(x)),j]=1-u;A[np.arange(len(x)),j+1]=u;bins=np.floor(s).astype(int);_,inv,cnt=np.unique(bins,return_inverse=True,return_counts=True);base=1/cnt[inv];D=np.diff(np.eye(n),n=2,axis=0);cur=q.copy()
 for _ in range(3):
  residual=np.linalg.norm(A@cur-x,axis=1);w=base*np.minimum(1,.5/np.maximum(residual,EPS));H=A.T@(w[:,None]*A)+.1*(D.T@D);rhs=A.T@(w[:,None]*x)
  # lstsq handles unsupported endpoint nullspaces without an extra scientific ridge.
  cur=np.linalg.lstsq(H,rhs,rcond=None)[0]
 delta=cur-q;norm=np.linalg.norm(delta,axis=1);cur=q+delta*np.minimum(1,.5/np.maximum(norm,EPS))[:,None];return cur

def update_models(x,half,models,a,field,guard=lambda:None):
 out={};events=[]
 for mid,q in sorted(models.items()):
  guard();rr=np.flatnonzero(a['edge_id']==mid)
  if not len(rr):events.append(dict(model=mid,operation='death',reason='no_primary'));continue
  try:
   nq=irls_update(x[rr],q);ss=project(x[rr],nq)[1];L=arc(nq)[-1];nq=slice_q(nq,max(0,float(np.min(ss-half[rr]))),min(L,float(np.max(ss+half[rr]))))
   if nq is None:raise ValueError('empty_trim')
   for side in (0,1):
    for _ in range(2):
     p=nq[0] if side==0 else nq[-1];dr=(nq[0]-nq[1]) if side==0 else (nq[-1]-nq[-2]);dr/=np.linalg.norm(dr);z=field.step(p,dr)
     if z is None:break
     candidate=np.vstack([z[0],nq]) if side==0 else np.vstack([nq,z[0]])
     if not geometry_ok(candidate)[0]:break
     nq=candidate
   nq=resample(nq);ok,why=geometry_ok(nq)
   if not ok:raise ValueError(why)
   out[mid]=nq;events.append(dict(model=mid,operation='update',accepted=True,old_knots=len(q),new_knots=len(nq)))
  except (ValueError,np.linalg.LinAlgError) as exc:out[mid]=q.copy();events.append(dict(model=mid,operation='update',accepted=False,reason=str(exc)))
 return out,events
