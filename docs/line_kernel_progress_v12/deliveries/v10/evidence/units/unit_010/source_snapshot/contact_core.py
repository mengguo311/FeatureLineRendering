"""Exact piecewise-linear nonlocal contact; no geometry changes or sampling."""
from contextlib import contextmanager
import numpy as np
from geometry_base import arc,EPS,contact_bounded

def pair_minimum(a,b,x,y,si,sj,li,lj,separation=None):
 """Convex quadratic on a rectangle clipped by one arclength half-plane."""
 polygon=[np.array(v,float) for v in ((0,0),(1,0),(1,1),(0,1))]
 normal=np.array([-li,lj]);bound=None if separation is None else separation-(sj-si)
 if bound is not None:
  clipped=[]
  for p,q in zip(polygon,polygon[1:]+polygon[:1]):
   dp=float(normal@p-bound);dq=float(normal@q-bound)
   if dp>=0:clipped.append(p)
   if (dp>=0)!=(dq>=0):clipped.append(p+(dp/(dp-dq))*(q-p))
  polygon=clipped
 if not polygon:return None
 w=a-b;matrix=np.column_stack((x,-y));points=[]
 # Boundary minimizers also cover singular quadratics and zero-area polygons.
 for p,q in zip(polygon,polygon[1:]+polygon[:1]):
  delta=q-p;v=matrix@delta;z=w+matrix@p;den=float(v@v)
  t=float(np.clip(-z@v/den,0,1)) if den>0 else 0.
  points.extend((p,p+t*delta))
 stationary=np.linalg.lstsq(matrix,-w,rcond=None)[0]
 if np.all(stationary>=0) and np.all(stationary<=1) and (bound is None or normal@stationary>=bound):points.append(stationary)
 best=None
 for z in points:
  u,v=map(float,z);res=w+u*x-v*y;d2=max(0.,float(res@res));sa=si+u*li;sb=sj+v*lj
  candidate=(d2,sa,sb,u,v)
  if best is None or candidate[:3]<best[:3]:best=candidate
 return best

def witnesses(q,guard=lambda:None):
 q=np.asarray(q,float);ss=arc(q);vv=np.diff(q,axis=0);ll=np.diff(ss);best={'INDEX':None,'ARC':None}
 if not np.isfinite(q).all() or np.any(ll<=0):raise ValueError('invalid contact geometry')
 def update(policy,candidate,i,j):
  if candidate is None:return
  d2,sa,sb,u,v=candidate;key=(d2,sa,sb,i,j)
  if best[policy] is None or key<best[policy][0]:
   best[policy]=(key,dict(distance_p=float(np.sqrt(d2)),segment_ids=[i,j],parameters=[u,v],arclengths_p=[sa,sb],arc_separation_p=sb-sa,points_p=[(q[i]+u*vv[i]).tolist(),(q[j]+v*vv[j]).tolist()]))
 for i in range(len(vv)):
  guard()
  for j in range(i,len(vv)):
   args=(q[i],q[j],vv[i],vv[j],ss[i],ss[j],ll[i],ll[j])
   if j>=i+2:update('INDEX',pair_minimum(*args),i,j)
   # Exact domain pruning, never an index or midpoint approximation.
   if ss[j+1]-ss[i]>=1.:update('ARC',pair_minimum(*args,separation=1.),i,j)
 result={k:(v[1] if v is not None else None) for k,v in best.items()}
 return result

def contact(q,policy='ARC',guard=lambda:None):
 if policy not in ('INDEX','ARC'):raise ValueError(policy)
 report=witnesses(q,guard);index_reject=contact_bounded(q,guard)
 arc_reject=report['ARC'] is not None and report['ARC']['distance_p']<.5-EPS
 return dict(policy=policy,reject=bool(index_reject if policy=='INDEX' else arc_reject),INDEX=dict(reject=bool(index_reject),witness=report['INDEX']),ARC=dict(reject=bool(arc_reject),witness=report['ARC']),intrinsic_separation_p=1.,contact_distance_p=.5,check_only=True,complete_pair_search=True)

@contextmanager
def validation_policy(policy):
 """Strictly serial, scoped dispatch only inside proposed-Q validation."""
 import overlap_core as oc
 original_validate=oc.validate;original_contact=oc.contact_bounded
 def validate(d,chain,q,guard=lambda:None):
  reports=[]
  def check(cq,inner_guard=lambda:None):
   report=contact(cq,policy,inner_guard);reports.append(report);return report['reject']
  oc.contact_bounded=check
  try:
   ok,why,meta=original_validate(d,chain,q,guard)
   if reports:meta['contact_diagnostics']=reports[-1]
   return ok,why,meta
  finally:oc.contact_bounded=original_contact
 oc.validate=validate
 try:yield
 finally:oc.validate=original_validate;oc.contact_bounded=original_contact

def library(d,state,sid,side,index,endpoints,policy,guard,max_prefixes=256,max_donors=3):
 import seam_core
 with validation_policy(policy):
  return seam_core.library(d,state,sid,side,index,endpoints,'HERMITE',guard,max_prefixes,max_donors)
