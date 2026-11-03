"""Dynamic shared-kernel overlap proposals; all coordinates normalized by p."""
import numpy as np
from scipy.spatial import cKDTree
import free_core as f
import merge_core as m

class TemplateError(ValueError):
 def __init__(self,reason,meta):super().__init__(reason);self.meta=meta

def key(p):return (p['a'],p['version_a'],p['b'],p['version_b'])

def compatibility(d,models,cache,guard=lambda:None):
 """Complete model-major sparse relation; minimum-cost segment, never top-k."""
 vr=np.flatnonzero(d['valid']);tree=cKDTree(d['x'][vr]) if len(vr) else None;out={};n=len(d['x'])
 for mid,q in sorted(models.items()):
  guard();vk=(mid,m.version(q))
  if vk in cache:out[mid]=cache[vk];continue
  co=np.full(n,np.inf);ss=np.zeros(n);jj=np.full(n,-1,np.int32);uu=np.zeros(n);ar=f.arc(q)
  for j,(a,b) in enumerate(zip(q[:-1],q[1:])):
   guard();v=b-a;l=np.linalg.norm(v)
   if l<f.EPS or tree is None:continue
   rr=vr[np.asarray(tree.query_ball_point((a+b)/2,l/2+1+f.EPS,workers=1),dtype=np.int64)]
   if not len(rr):continue
   u=np.clip((d['x'][rr]-a)@v/(l*l),0,1);dist=np.linalg.norm(d['x'][rr]-a-u[:,None]*v,axis=1);ang=np.degrees(np.arccos(np.clip(np.abs(d['t'][rr]@(v/l)),0,1)));ok=(dist<=1+f.EPS)&(ang<=30+f.EPS);rr=rr[ok];u=u[ok];cost=dist[ok]**2+.25*(ang[ok]/30)**2
   take=cost<co[rr];rr=rr[take];co[rr]=cost[take];ss[rr]=ar[j]+u[take]*l;jj[rr]=j;uu[rr]=u[take]
  rr=np.flatnonzero(co<1);z=dict(rows=rr,cost=co[rr],s=ss[rr],segment=jj[rr],u=uu[rr]);cache[vk]=z;out[mid]=z
 return out

def shared(tables,a,b):return np.intersect1d(tables[a]['rows'],tables[b]['rows'],assume_unique=True,return_indices=True)

def enumerate_candidates(d,models,tables,guard=lambda:None):
 ids=sorted(models);ar={i:f.arc(models[i])[-1] for i in ids};versions={i:m.version(models[i]) for i in ids};records=[];eligible=[]
 for ai,a in enumerate(ids):
  guard()
  for b in ids[ai+1:]:
   guard();rr,ia,ib=shared(tables,a,b);sa=sb=-1.;reason=1
   if len(rr)>=12:
    h=d['half'][rr];sa=f.union(np.c_[np.maximum(0,tables[a]['s'][ia]-h),np.minimum(ar[a],tables[a]['s'][ia]+h)])[1];sb=f.union(np.c_[np.maximum(0,tables[b]['s'][ib]-h),np.minimum(ar[b],tables[b]['s'][ib]+h)])[1];reason=0 if sa>=2 and sb>=2 else 2
   records.append((a,b,len(rr),sa,sb,reason))
   if reason==0:eligible.append(dict(a=a,b=b,version_a=versions[a],version_b=versions[b],shared_rows=len(rr),support_a=sa,support_b=sb,score=min(sa,sb)))
 eligible.sort(key=lambda z:(-z['score'],z['a'],z['b']))
 names=('a','b','shared_rows','support_a','support_b','reason');arrays={name:np.array([r[j] for r in records],dtype=np.float64 if j in (3,4) else np.int64) for j,name in enumerate(names)}
 return eligible,arrays

def evaluate(q,z):
 s=f.arc(q);z=np.asarray(z);assert np.all(z>=-f.EPS) and np.all(z<=s[-1]+f.EPS),'EXTRAPOLATION'
 z=np.clip(z,0,s[-1]);j=np.clip(np.searchsorted(s[1:],z,side='left'),0,len(q)-2);v=q[j+1]-q[j];length=s[j+1]-s[j];u=(z-s[j])/length;return q[j]+u[:,None]*v,v/length[:,None]

def template(models,p,tables):
 a,b=p['a'],p['b'];qa=models[a];qb=models[b];rr,ia,ib=shared(tables,a,b);meta=dict(shared_rows=len(rr),a=a,b=b)
 if len(rr)<12:raise TemplateError('shared_count',meta)
 va=np.diff(qa,axis=0);va/=np.linalg.norm(va,axis=1)[:,None];vb=np.diff(qb,axis=0);vb/=np.linalg.norm(vb,axis=1)[:,None];dot=float(np.sum(va[tables[a]['segment'][ia]]*vb[tables[b]['segment'][ib]]));rev=dot<0;LA=f.arc(qa)[-1];LB=f.arc(qb)[-1];sa=tables[a]['s'][ia];sb=LB-tables[b]['s'][ib] if rev else tables[b]['s'][ib];qb=qb[::-1] if rev else qb;delta=float(np.median(sa-sb));lo=max(0.,delta);hi=min(LA,delta+LB)
 meta.update(reverse_b=bool(rev),signed_dot_sum=dot,delta=delta,domain_a=[0.,float(LA)],domain_b=[delta,float(delta+LB)],overlap=[lo,hi],alignment_absolute_error_max=float(np.max(np.abs(sa-sb-delta))))
 if hi-lo<2:raise TemplateError('overlap_domain',meta)
 z=np.linspace(lo,hi,max(2,int(np.ceil(hi-lo-f.EPS))+1));xa,ta=evaluate(qa,z);xb,tb=evaluate(qb,z-delta);dist=np.linalg.norm(xa-xb,axis=1);angle=np.degrees(np.arccos(np.clip(np.sum(ta*tb,axis=1),-1,1)));meta.update(check_coordinates=z.tolist(),check_distances=dist.tolist(),check_angles=angle.tolist(),max_distance=float(dist.max()),max_angle=float(angle.max()))
 if np.any(dist>1+f.EPS):raise TemplateError('overlap_distance',meta)
 if np.any(angle>30+f.EPS):raise TemplateError('overlap_tangent',meta)
 left=a if 0<=delta else b;right=a if LA>=delta+LB else b;meta.update(left_owner=left,right_owner=right)
 if left==right:q=qa.copy() if left==a else qb.copy()
 else:
  zz=np.unique(np.r_[f.arc(qa),delta+f.arc(qb),lo,hi]);points=[]
  for t in zz:
   if t<lo:point=evaluate(qa,np.array([t]))[0][0] if left==a else evaluate(qb,np.array([t-delta]))[0][0]
   elif t>hi:point=evaluate(qa,np.array([t]))[0][0] if right==a else evaluate(qb,np.array([t-delta]))[0][0]
   else:
    pa=evaluate(qa,np.array([t]))[0][0];pb=evaluate(qb,np.array([t-delta]))[0][0];w=(t-lo)/(hi-lo);point=(1-w)*pa+w*pb if left==a else (1-w)*pb+w*pa
   points.append(point)
  q=np.array(points)
  keep=np.r_[True,np.linalg.norm(np.diff(q,axis=0),axis=1)>f.EPS];q=q[keep]
 meta['template_length_p']=float(f.arc(q)[-1])
 if meta['template_length_p']>128+f.EPS:raise TemplateError('length_cap',meta)
 try:return f.resample(q),meta
 except ValueError as exc:raise TemplateError(str(exc),meta)

def trial(d,models,a,next_id,p,tables,guard=lambda:None,progress=lambda phase,r:None):
 guard();assert m.version(models[p['a']])==p['version_a'] and m.version(models[p['b']])==p['version_b'],'STALE_PROPOSAL'
 before=m.energy(d,models,a,guard);r=dict(accepted=False,reason=None,before=before,after=None,proposal=p,model_id=next_id,next_id=next_id,models=None,assignment=None,raw=None,events=[],template=None,q=None,parameterization={})
 rr=np.flatnonzero(np.isin(a['edge_id'],[p['a'],p['b']]));r['fit_rows']=rr
 if len(rr)>8192:r['reason']='member_cap';return r
 if not len(rr):r['reason']='no_fit_members';return r
 try:
  q,meta=template(models,p,tables);r['parameterization']=meta;r['template']=q.copy();progress('template',r);guard();q=f.irls_update(d['x'][rr],q);r['q']=q.copy();ok,why=f.geometry_ok(q)
 except TemplateError as exc:r['parameterization']=exc.meta;r['reason']='template:'+str(exc);return r
 except (ValueError,np.linalg.LinAlgError) as exc:r['reason']='fit:'+str(exc);return r
 progress('fitted',r)
 if not ok:r['reason']='geometry:'+why;return r
 mm={mid:v.copy() for mid,v in models.items() if mid not in (p['a'],p['b'])};mm[next_id]=q
 aa=f.assign(d['x'],d['t'],d['valid'],mm,guard);r['raw']={k:v.copy() for k,v in aa.items()};progress('raw',r)
 mm,aa,events,nxt=f.validate_support(d['x'],d['half'],mm,aa,next_id+1,guard);r.update(models=mm,assignment=aa,events=events,next_id=nxt);progress('validated',r);r['after']=m.energy(d,mm,aa,guard)
 children=[mid for mid in mm if mid==next_id or any(e.get('operation')=='gap_split' and e.get('parent')==next_id and e.get('child')==mid for e in events)];r['surviving_children']=children
 if len(children)!=1:r['reason']='merged_support_not_one_piece';return r
 if len(mm)>704:r['reason']='active_model_cap';return r
 if before['total']-r['after']['total']<=f.EPS:r['reason']='no_energy_decrease';return r
 r['accepted']=True;r['reason']='energy_decrease';return r
