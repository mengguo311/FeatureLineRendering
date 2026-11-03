"""Complete finite-neighborhood agglomeration; never modifies original kernels."""
import copy
import numpy as np
from scipy.sparse import coo_matrix,vstack,eye,diags
from scipy.sparse.linalg import lsqr
from scipy.spatial import cKDTree
from geometry_base import EPS,arc,project,sample,clean,union_intervals
from port_paths import parallel,Leaf
from contact_core import pair_minimum

class Incomplete(RuntimeError):pass

def at(q,s):
 a=arc(q);return np.array([np.interp(s,a,q[:,k]) for k in range(3)]).T

def fit(template,x,movable,guard=lambda:None):
 q=np.array(template,float,copy=True);k=len(q);n=len(x);move=np.flatnonzero(movable);fixed=np.flatnonzero(~np.asarray(movable,bool));receipts=[]
 if n>8192 or k>257:raise Incomplete('FIT_CAPACITY')
 if not len(move):return q,dict(iterations=5,lsqr=[],fixed_all=True)
 D=coo_matrix((np.tile([1.,-2.,1.],max(0,k-2)),(np.repeat(np.arange(max(0,k-2)),3),np.ravel(np.arange(max(0,k-2))[:,None]+[0,1,2]))),shape=(max(0,k-2),k)).tocsr()
 for it in range(5):
  guard();ss,dist,_,seg,near=project(x,q);lens=np.linalg.norm(np.diff(q,axis=0),axis=1);u=(ss-arc(q)[seg])/np.maximum(lens[seg],1e-30)
  H=coo_matrix((np.c_[1-u,u].ravel(),(np.repeat(np.arange(n),2),np.c_[seg,seg+1].ravel())),shape=(n,k)).tocsr()
  # Huber rho=0.5*r^2 inside delta; normalized derivative weights.
  weight=np.sqrt(np.minimum(1.,.5/np.maximum(dist,1e-30))/(2*n))
  matrix=vstack([diags(weight)@H,np.sqrt(.05/max(1,k-2))*D,np.sqrt(.001/k)*eye(k)],format='csr')
  rhs=np.vstack([weight[:,None]*x,np.zeros((max(0,k-2),3)),np.sqrt(.001/k)*template]);rhs-=matrix[:,fixed]@template[fixed]
  for dim in range(3):
   guard();res=lsqr(matrix[:,move],rhs[:,dim],atol=1e-8,btol=1e-8,iter_lim=2000)
   if res[1] not in (0,1,2,4,5):raise Incomplete('LSQR_NOT_CONVERGED '+str(res[1]))
   q[move,dim]=res[0];receipts.append([it,dim,int(res[1]),int(res[2]),float(res[3])])
  q[fixed]=template[fixed]
  if not np.isfinite(q).all() or np.any(np.linalg.norm(np.diff(q,axis=0),axis=1)<=EPS):return q,dict(iterations=it+1,lsqr=receipts,degenerate=True)
 return q,dict(iterations=5,lsqr=receipts,old_fixed_exact=bool(np.array_equal(q[fixed],template[fixed])),max_knot_displacement_p=float(np.linalg.norm(q-template,axis=1).max()))

def segment_distances(a,b,c,d):
 v=b-a;w=d-c;r=a-c;A=float(v@v);B=w@v;C=np.sum(w*w,1);D=r@v;E=np.sum(w*r,1);den=A*C-B*B
 dist=np.full(len(c),np.inf)
 for u,t in [(np.zeros(len(c)),np.clip(E/np.maximum(C,1e-30),0,1)),(np.ones(len(c)),np.clip((E+B)/np.maximum(C,1e-30),0,1)),(np.clip(-D/max(A,1e-30),0,1),np.zeros(len(c))),(np.clip((B-D)/max(A,1e-30),0,1),np.ones(len(c)))]:
  delta=r+u[:,None]*v-t[:,None]*w;dist=np.minimum(dist,np.sum(delta*delta,1))
 u=(B*E-C*D)/np.where(abs(den)>1e-20,den,1);t=(A*E-B*D)/np.where(abs(den)>1e-20,den,1);ok=(abs(den)>1e-20)&(u>=0)&(u<=1)&(t>=0)&(t<=1)
 delta=r+u[:,None]*v-t[:,None]*w;dist[ok]=np.minimum(dist[ok],np.sum(delta[ok]*delta[ok],1));return np.sqrt(np.maximum(0,dist))

class CompleteIndex:
 def __init__(self,objects):
  aa=[];bb=[];ids=[]
  for gid,o in sorted(objects.items()):
   if not o['available']:continue
   q=o['q'];aa.extend(q[:-1]);bb.extend(q[1:]);ids.extend([gid]*(len(q)-1))
  self.a=np.asarray(aa).reshape(-1,3);self.b=np.asarray(bb).reshape(-1,3);self.ids=np.asarray(ids,np.int64);self.half=np.linalg.norm(self.b-self.a,axis=1)/2;self.tree=cKDTree((self.a+self.b)/2);self.maximum=float(self.half.max(initial=0))
 def query(self,q,excluded,guard=lambda:None):
  result={}
  for a,b in zip(q[:-1],q[1:]):
   guard();pick=np.asarray(self.tree.query_ball_point((a+b)/2,2.+np.linalg.norm(b-a)/2+self.maximum+EPS),int)
   if not len(pick):continue
   distances=segment_distances(a,b,self.a[pick],self.b[pick]);yes=np.flatnonzero(distances<=2+EPS)
   for k in yes:
    gid=int(self.ids[pick[k]])
    if gid not in excluded:result[gid]=min(result.get(gid,float('inf')),float(distances[k]))
  return sorted(result.items())

def unit(v):
 n=np.linalg.norm(v);return v/n if n>EPS else None

def template_record(q,old_domain,joins,relation,direction):
 q=clean(q)
 if len(q)<2 or not np.isfinite(q).all():return dict(reason='degenerate_template',relation=relation,direction=direction)
 # Resampling is a representation budget; no candidate is truncated.
 if int(np.ceil(arc(q)[-1]))+1>257:raise Incomplete('KNOT_CAPACITY')
 t=sample(q,1.);a=arc(t);old_lo,old_hi=old_domain
 movable=(a<old_lo-EPS)|(a>old_hi+EPS)
 for j in joins:movable|=abs(a-j)<=2+EPS
 return dict(template=t,local_movable=movable,relation=relation,direction=direction,reason='template',joins_p=list(map(float,joins)))

def proposals(a,b,guard=lambda:None):
 LA=float(arc(a)[-1]);LB=float(arc(b)[-1]);out=[]
 for rev in (0,1):
  guard();bb=b[::-1] if rev else b;xs=sample(bb,1.);sb=arc(xs);sa,dd,ta,_,_=project(xs,a);seg=np.clip(np.searchsorted(arc(bb),sb,side='left')-1,0,len(bb)-2);tb=np.diff(bb,axis=0)[seg];tb/=np.linalg.norm(tb,axis=1)[:,None];ok=(dd<=1+EPS)&(np.sum(ta*tb,1)>0)
  if not np.any(ok):out.append(dict(relation='overlap',direction=rev,reason='no_registration_correspondence'))
  else:
   delta=float(np.median(sa[ok]-sb[ok]));left=max(0.,delta);right=min(LA,delta+LB)
   if right<=left+EPS:out.append(dict(relation='overlap',direction=rev,reason='empty_overlap'))
   else:
    coords=np.unique(np.r_[arc(a),arc(bb)+delta,left,right]);q=[]
    left_owner=0 if 0<=delta else 1;right_owner=0 if LA>=delta+LB else 1
    for s in coords:
     pa=at(a,np.clip(s,0,LA));pb=at(bb,np.clip(s-delta,0,LB))
     if s<left:q.append(pa if left_owner==0 else pb)
     elif s>right:q.append(pa if right_owner==0 else pb)
     elif left_owner==right_owner:q.append(pa if left_owner==0 else pb)
     else:
      t=(s-left)/(right-left);q.append((1-t)*(pa if left_owner==0 else pb)+t*(pa if right_owner==0 else pb))
    q=clean(np.asarray(q));oldproj=project(a[[0,-1]],q)[0];jp=project(np.array([at(a,left),at(a,right)]),q)[0]
    z=template_record(q,(float(oldproj.min()),float(oldproj.max())),jp,'overlap',rev);z.update(delta_p=delta,correspondence_count=int(ok.sum()));out.append(z)
 for side in (0,1):
  aa=a if side else a[::-1]
  for rev in (0,1):
   bb=b[::-1] if rev else b;gap=float(np.linalg.norm(aa[-1]-bb[0]));direction=2*side+rev
   if gap>2+EPS:out.append(dict(relation='endpoint',direction=direction,reason='endpoint_distance',gap_p=gap));continue
   q=clean(np.vstack([aa,bb]));L=float(arc(q)[-1]);j=LA
   if not side:q=q[::-1];lo=L-LA;hi=L;j=L-LA
   else:lo=0.;hi=LA
   z=template_record(q,(lo,hi),[j],'endpoint',direction);z['gap_p']=gap;out.append(z)
 return out

def support(d,rows,q):
 rows=np.asarray(rows,int);s,_,tan,_,_=project(d['asset']['means'][rows]/d['p'],q);t=d['tangents'][rows];valid=np.isfinite(t).all(1)&(np.linalg.norm(t,axis=1)>EPS)
 # Original derivative axes, not fitted directions, set covariance support.
 tt=t/np.maximum(np.linalg.norm(t,axis=1)[:,None],1e-30);cov=d['asset']['covariance'][rows]/d['p']**2
 half=np.minimum(.5,np.sqrt(np.maximum(0,np.einsum('ni,nij,nj->n',tt,cov,tt))));half[~valid]=0.;raw=np.c_[s-half,s+half];iv=np.clip(raw,0,arc(q)[-1]);union,length,run,gap,total=union_intervals(iv[valid])
 return dict(intervals=union,s=s,valid=valid,half=half,union=float(length),run=float(run),gap=float(gap),total_gap=float(total),clamped_endpoints=int(np.sum(iv!=raw)),max_clamp=float(np.max(abs(iv-raw),initial=0)))

def union_difference(a,b):
 total=0.
 for lo,hi in a:
  rem=hi-lo
  for x,y in b:rem-=max(0.,min(hi,y)-max(lo,x))
  total+=max(0.,rem)
 return float(total)

def pair_cyclic(a,b,x,y,si,sj,li,lj,L):
 polygon=[np.array(z,float) for z in ((0,0),(1,0),(1,1),(0,1))];normal=np.array([-li,lj])
 for n,bound in [(normal,1-(sj-si)),(-normal,-(L-1)+(sj-si))]:
  cut=[]
  for p,q in zip(polygon,polygon[1:]+polygon[:1]):
   dp=float(n@p-bound);dq=float(n@q-bound)
   if dp>=0:cut.append(p)
   if (dp>=0)!=(dq>=0):cut.append(p+dp/(dp-dq)*(q-p))
  polygon=cut
  if not polygon:return None
 matrix=np.column_stack([x,-y]);offset=a-b;points=[]
 for p,q in zip(polygon,polygon[1:]+polygon[:1]):
  delta=q-p;v=matrix@delta;den=v@v;u=np.clip(-(offset+matrix@p)@v/den,0,1) if den>0 else 0.;points.extend([p,p+u*delta])
 z=np.linalg.lstsq(matrix,-offset,rcond=None)[0];ds=sj-si+normal@z
 if np.all(z>=0)&np.all(z<=1) and 1<=ds<=L-1:points.append(z)
 return min(float(np.sum((offset+matrix@z)**2)) for z in points)

def contact(q,closed,guard):
 ss=arc(q);v=np.diff(q,axis=0);lo=np.minimum(q[:-1],q[1:]);hi=np.maximum(q[:-1],q[1:])
 for i in range(len(v)):
  guard();separation=np.maximum(np.maximum(lo-hi[i],lo[i]-hi),0.);candidates=np.flatnonzero(np.sum(separation*separation,1)<(.5-EPS)**2)
  for j in candidates[candidates>=i]:
   if ss[j+1]-ss[i]<1:continue
   args=(q[i],q[j],v[i],v[j],ss[i],ss[j],ss[i+1]-ss[i],ss[j+1]-ss[j])
   value=pair_cyclic(*args,float(ss[-1])) if closed else pair_minimum(*args,separation=1.)
   d2=value if closed else (None if value is None else value[0])
   if d2 is not None and d2<(.5-EPS)**2:return dict(reject=True,segments=[int(i),int(j)],distance_p=float(np.sqrt(d2)),periodic=bool(closed))
 return dict(reject=False,complete=True,periodic=bool(closed))

def closure(d,rows,q):
 L=float(arc(q)[-1]);gap=float(np.linalg.norm(q[-1]-q[0]));result=dict(supported=False,gap_p=gap,length_p=L)
 if gap>.5+EPS or L<6-EPS:return q,result
 sup=support(d,rows,q);near=(sup['s']<=1+EPS)&sup['valid'];far=(sup['s']>=L-1-EPS)&sup['valid'];result.update(start_rows=np.asarray(rows)[near].tolist(),end_rows=np.asarray(rows)[far].tolist())
 if near.sum()<3 or far.sum()<3:return q,result
 t0=unit(q[1]-q[0]);t1=unit(q[-1]-q[-2]);angle=float(np.degrees(np.arccos(np.clip(t0@t1,-1,1))));result['tangent_angle_deg']=angle
 if angle>45+EPS:return q,result
 seamrows=np.asarray(rows)[near|far];xyz=d['asset']['means'][seamrows]/d['p'];axis=unit(q[0]-q[-1]) if gap>EPS else t0;delta=xyz-q[-1];s=delta@axis;dist=np.linalg.norm(delta-s[:,None]*axis,axis=1);hs=sup['half'][near|far];iv=np.c_[s-hs,s+hs];iv=np.clip(iv,0,gap);iv=iv[dist<=.5+EPS];u,length,_,holes,_=union_intervals(iv)
 result.update(bridge_support_p=u.tolist(),support_proxy=True)
 if gap>EPS and (not len(u) or u[0,0]>EPS or u[-1,1]<gap-EPS or holes>EPS):return q,result
 result['supported']=True;closed=np.vstack([q,q[0]]) if gap>EPS else q.copy();closed[-1]=closed[0];return closed,result

def branch(d,leafids,q,guard):
 reps=np.unique(np.concatenate([d['leaves'][i].reps for i in leafids]));rx=d['representatives']['x'][reps]/d['p'];rt=d['representatives']['t'][reps]
 if len(reps)<9:return False
 centers=np.vstack([q]+[d['leaves'][i].q for i in leafids])
 for center in centers:
  guard();dx=rx-center;rr=np.linalg.norm(dx,axis=1);sel=np.flatnonzero((rr>EPS)&(rr<=4.))
  if len(sel)<9:continue
  dirs=rt[sel]*np.where(np.sum(rt[sel]*dx[sel],1)>=0,1.,-1.)[:,None];clusters=[]
  for z,axis in zip(sel,dirs):
   for ax,members in clusters:
    if ax@axis>=np.cos(20*np.pi/180):members.append(z);break
   else:clusters.append((axis,[z]))
  if sum(len(ids)>=3 and np.ptp(rr[ids])>=2-EPS for _,ids in clusters)>=3:return True
 return False

def evaluate(d,g,f,q,guard=lambda:None):
 rows=np.union1d(g['rows'],f['rows']);ids=sorted(set(g['leaves'])|set(f['leaves']));meta={}
 if len(rows)<=len(g['rows']):return False,'no_new_rows',meta,q
 if len(rows)>8192:raise Incomplete('MEMBER_CAPACITY')
 if len(q)<2 or not np.isfinite(q).all() or np.any(np.linalg.norm(np.diff(q,axis=0),axis=1)<=EPS):return False,'degenerate',meta,q
 q,cl=closure(d,rows,q)
 if len(q)>257:raise Incomplete('CLOSED_KNOT_CAPACITY')
 meta['closure']=cl;closed=cl['supported'];ss,dist,tan,_,_=project(d['asset']['means'][rows]/d['p'],q);t=d['tangents'][rows];valid=np.isfinite(t).all(1)&(np.linalg.norm(t,axis=1)>EPS)
 if not valid.any():return False,'UNKNOWN_direction',meta,q
 theta=np.degrees(np.arccos(np.clip(abs(np.sum(t[valid]*tan[valid],1)),0,1)));meta.update(max_distance_p=float(dist.max()),q95_distance_p=float(np.quantile(dist,.95)),max_angle_deg=float(theta.max()),invalid_derivative_rows=rows[~valid].tolist())
 if dist.max()>1.5+EPS:return False,'member_distance',meta,q
 if theta.max()>75+EPS:return False,'gross_tangent_conflict',meta,q
 directions=np.diff(q,axis=0);directions/=np.linalg.norm(directions,axis=1)[:,None];angles=np.degrees(np.arccos(np.clip(np.sum(directions[:-1]*directions[1:],1),-1,1)))
 if closed:angles=np.r_[angles,np.degrees(np.arccos(np.clip(directions[-1]@directions[0],-1,1)))]
 if angles.max(initial=0)>=90:return False,'vertex_degeneracy',meta,q
 orientations={};L=float(arc(q)[-1])
 for cid in ids:
  guard();s=project(sample(d['leaves'][cid].q,1.),q)[0];ds=np.diff(s)
  if closed:ds=(ds+L/2)%L-L/2
  if np.all(ds>=-EPS):orientations[str(cid)]=False
  elif np.all(ds<=EPS):orientations[str(cid)]=True
  else:return False,'original_leaf_nonmonotone',meta,q
 for j,cid in enumerate(ids):
  for other in ids[j+1:]:
   if parallel(d['leaves'][cid],d['leaves'][other]):return False,'parallel_conflict',meta,q
 if branch(d,ids,q,guard):return False,'branch_conflict',meta,q
 con=contact(q,closed,guard);meta['contact']=con
 if con['reject']:return False,'nonlocal_contact',meta,q
 sup=support(d,rows,q);old=support(d,g['rows'],q);new=support(d,f['rows'],q);U=union_difference(new['intervals'],old['intervals'])
 meta.update(support_union_p=sup['union'],longest_run_p=sup['run'],max_gap_p=sup['gap'],total_gap_p=sup['total_gap'],supported_intervals=sup['intervals'].tolist(),support_clamped_endpoints=sup['clamped_endpoints'],support_max_clamp_p=sup['max_clamp'],unique_donor_support_p=U,leaf_orientations=orientations,length_p=L,kernels=len(rows))
 if sup['gap']>1.5+EPS:return False,'unsupported_gap',meta,q
 if U<=EPS:return False,'no_unique_support',meta,q
 score=float(np.mean(dist**2)+.25*np.mean((theta/90)**2)+.05*np.mean((angles/90)**2) if len(angles) else np.mean(dist**2)+.25*np.mean((theta/90)**2))
 score+=.1*sup['gap']**2+.02*len(q)/(L+1)-.25*U/(1+U)
 meta.update(score=score,position_mean_square=float(np.mean(dist**2)),tangent_mean_square=float(np.mean((theta/90)**2)),turn_mean_square=float(np.mean((angles/90)**2)) if len(angles) else 0.)
 return True,'connectable',meta,q

def best(records):
 eligible=[(r['metrics']['score'],r['donor'],r['relation'],r['direction'],i) for i,r in enumerate(records) if r.get('connectable')]
 return min(eligible)[-1] if eligible else None

def library(d,objects,gid,policy,index,guard=lambda:None):
 g=objects[gid];neighbors=index.query(g['q'],{gid},guard);records=[];result=dict(complete=False,neighbors=neighbors,records=records,selected=None)
 try:
  for fid,distance in neighbors:
   guard();f=objects[fid];result['current_donor']=fid
   if len(np.union1d(g['rows'],f['rows']))>8192:raise Incomplete('MEMBER_CAPACITY')
   for rec in proposals(g['q'],f['q'],guard):
    rec.update(donor=fid,distance_p=distance,connectable=False);records.append(rec)
    if rec['reason']!='template':continue
    movable=np.ones(len(rec['template']),bool) if policy=='WHOLE' else rec['local_movable'];x=d['asset']['means'][np.union1d(g['rows'],f['rows'])]/d['p'];q,fitmeta=fit(rec['template'],x,movable,guard);rec['fit']=fitmeta
    ok,why,met,q=evaluate(d,g,f,q,guard);rec.update(connectable=ok,reason=why,metrics=met,q=q)
    old_s,_,_,old_seg,old_near=project(g['q'],rec['template']);ts=arc(rec['template']);u=(old_s-ts[old_seg])/np.diff(ts)[old_seg];mapped=(1-u[:,None])*q[old_seg]+u[:,None]*q[old_seg+1];rec['old_curve_motion_p']=dict(max=float(np.linalg.norm(mapped-g['q'],axis=1).max()),rms=float(np.sqrt(np.mean(np.sum((mapped-g['q'])**2,1)))),fit_only_max=float(np.linalg.norm(mapped-old_near,axis=1).max()),correspondence='fixed template closest-segment barycentric coordinates')
  result.update(complete=True,selected=best(records),reason='complete')
 except (Incomplete,TimeoutError) as exc:
  result['reason']=str(exc);result['unattempted_donors']=[fid for fid,_ in neighbors if fid>=result.get('current_donor',-10**18)]
 return result

def commit(objects,gid,record,next_version,save):
 fid=record['donor'];old=objects[gid];other=objects[fid];new=dict(old,rows=np.union1d(old['rows'],other['rows']),leaves=sorted(set(old['leaves'])|set(other['leaves'])),q=record['q'].copy(),version=next_version,metrics=copy.deepcopy(record['metrics']),available=True,seed_origins=sorted(set(old.get('seed_origins',[]))|set(other.get('seed_origins',[]))),origin_objects=sorted(set(old.get('origin_objects',[gid]))|set(other.get('origin_objects',[fid]))))
 assert len(new['rows'])>len(old['rows']) and np.isin(old['rows'],new['rows']).all()
 trial=dict(objects);trial[gid]=new;del trial[fid];save(trial,new);return trial,next_version+1
