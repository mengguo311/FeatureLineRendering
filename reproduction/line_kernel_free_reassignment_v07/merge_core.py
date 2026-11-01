"""Unit003 dynamic model replacement; free kernel competition, no legacy atoms."""
import hashlib
import numpy as np
import free_core as f

def version(q):return hashlib.sha256(q.tobytes()).hexdigest()
def key(p):return (p['a'],p['version_a'],p['pa'],p['b'],p['version_b'],p['pb'])

def enumerate_candidates(models,guard=lambda:None):
 guard();ids=np.array(sorted(models),np.int64);ii,jj=np.triu_indices(len(ids),1);cols=[];candidates=[]
 if not len(ii):return [],{k:np.array([],dtype=float if k in ('gap','tangent','connector') else np.int64) for k in ('a','b','pa','pb','gap','tangent','connector','reason')}
 qs=[models[int(i)] for i in ids];ends=np.array([[q[0],q[-1]] for q in qs]);tt=np.array([[(q[1]-q[0])/np.linalg.norm(q[1]-q[0]),(q[-1]-q[-2])/np.linalg.norm(q[-1]-q[-2])] for q in qs]);versions={int(i):version(models[int(i)]) for i in ids}
 for pa in (0,1):
  for pb in (0,1):
   guard();delta=ends[jj,pb]-ends[ii,pa];gap=np.linalg.norm(delta,axis=1);ta=tt[ii,pa]*(1 if pa else -1);tb=tt[jj,pb]*(1 if pb==0 else -1)
   tangent=np.degrees(np.arccos(np.clip(np.sum(ta*tb,axis=1),-1,1)));direction=delta/np.maximum(gap[:,None],f.EPS)
   connector=np.maximum(np.degrees(np.arccos(np.clip(np.sum(direction*ta,axis=1),-1,1))),np.degrees(np.arccos(np.clip(np.sum(direction*tb,axis=1),-1,1))));connector[gap<=f.EPS]=0
   reason=np.zeros(len(ii),np.uint8);reason[connector>35+f.EPS]=3;reason[tangent>30+f.EPS]=2;reason[gap>1.5+f.EPS]=1
   cols.append(dict(a=ids[ii],b=ids[jj],pa=np.full(len(ii),pa,np.uint8),pb=np.full(len(ii),pb,np.uint8),gap=gap,tangent=tangent,connector=connector,reason=reason))
   for j in np.flatnonzero(reason==0):
    a=int(ids[ii[j]]);b=int(ids[jj[j]]);candidates.append(dict(a=a,b=b,pa=pa,pb=pb,gap=float(gap[j]),tangent=float(tangent[j]),connector=float(connector[j]),version_a=versions[a],version_b=versions[b]))
 candidates.sort(key=lambda z:(z['gap'],z['a'],z['b'],z['pa'],z['pb']))
 return candidates,{k:np.concatenate([z[k] for z in cols]) for k in cols[0]}

def template(models,p):
 a=models[p['a']] if p['pa']==1 else models[p['a']][::-1];b=models[p['b']] if p['pb']==0 else models[p['b']][::-1]
 joined=np.concatenate([a,b]);q=[joined[0]]
 for v in joined[1:]:
  if np.linalg.norm(v-q[-1])>f.EPS:q.append(v)
 q=np.array(q)
 if f.arc(q)[-1]>128+f.EPS:raise ValueError('length_cap')
 return f.resample(q)

def row_cost(x,t,q):
 best=np.full(len(x),np.inf)
 for a,b in zip(q[:-1],q[1:]):
  v=b-a;l=np.linalg.norm(v);u=np.clip((x-a)@v/(l*l),0,1);dist=np.linalg.norm(x-a-u[:,None]*v,axis=1);angle=np.degrees(np.arccos(np.clip(np.abs(t@(v/l)),0,1)));cost=dist**2+.25*(angle/30)**2;cost[(dist>1+f.EPS)|(angle>30+f.EPS)]=np.inf;best=np.minimum(best,cost)
 return best

def energy(d,models,a,guard=lambda:None):
 loss=np.ones(len(d['x']));labels=a['edge_id'];assert set(np.unique(labels[labels>=0])).issubset(models),'DANGLING_PRIMARY'
 for mid,q in sorted(models.items()):
  guard();rr=np.flatnonzero(labels==mid)
  if len(rr):loss[rr]=row_cost(d['x'][rr],d['t'][rr],q)
 if not np.isfinite(loss).all():raise RuntimeError('ASSIGNED_COST_NOT_FINITE')
 data=float(loss.sum());return dict(data=data,model_penalty=float(len(models)),models=len(models),total=data+len(models),UNKNOWN=int(np.sum(labels<0)))

def trial(d,models,a,next_id,p,guard=lambda:None,progress=lambda phase,r:None):
 guard();assert version(models[p['a']])==p['version_a'] and version(models[p['b']])==p['version_b'],'STALE_PROPOSAL'
 before=energy(d,models,a,guard);r=dict(accepted=False,reason=None,before=before,after=None,proposal=p,model_id=next_id,next_id=next_id,models=None,assignment=None,raw=None,events=[],template=None,q=None)
 rr=np.flatnonzero(np.isin(a['edge_id'],[p['a'],p['b']]))
 r['fit_rows']=rr
 if len(rr)>8192:r['reason']='member_cap';return r
 if not len(rr):r['reason']='no_fit_members';return r
 try:
  q=template(models,p);r['template']=q.copy();q=f.irls_update(d['x'][rr],q);r['q']=q.copy();ok,why=f.geometry_ok(q)
 except (ValueError,np.linalg.LinAlgError) as exc:r['reason']='fit:'+str(exc);return r
 progress('fitted',r)
 if not ok:r['reason']='geometry:'+why;return r
 mm={mid:v.copy() for mid,v in models.items() if mid not in (p['a'],p['b'])};mm[next_id]=q
 aa=f.assign(d['x'],d['t'],d['valid'],mm,guard);r['raw']={k:v.copy() for k,v in aa.items()};progress('raw',r)
 mm,aa,events,nxt=f.validate_support(d['x'],d['half'],mm,aa,next_id+1,guard);r.update(models=mm,assignment=aa,events=events,next_id=nxt);progress('validated',r)
 after=energy(d,mm,aa,guard);r['after']=after
 children=[mid for mid in mm if mid==next_id or any(e.get('operation')=='gap_split' and e.get('parent')==next_id and e.get('child')==mid for e in events)]
 r['surviving_children']=children
 if len(children)!=1:r['reason']='merged_support_not_one_piece';return r
 if len(mm)>704:r['reason']='active_model_cap';return r
 if before['total']-after['total']<=f.EPS:r['reason']='no_energy_decrease';return r
 r['accepted']=True;r['reason']='energy_decrease';return r

def delta(base,other):
 """Lossless differences for all membership fields, including revoked/UNKNOWN rows."""
 changed=np.zeros(len(base['edge_id']),bool)
 for k in base:
  if k not in other:raise KeyError(k)
  different=base[k]!=other[k]
  if different.ndim>1:different=np.any(different,axis=tuple(range(1,different.ndim)))
  changed|=different
 rr=np.flatnonzero(changed);return dict(changed_rows=rr,**{k:other[k][rr] for k in base})
