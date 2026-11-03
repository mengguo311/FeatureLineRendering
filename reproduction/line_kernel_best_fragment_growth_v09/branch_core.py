"""Frozen curve-tangent transport; original fit/search/ranking functions remain unchanged."""
from runtime_io import *
from geometry_base import project,arc,EPS
import whole_core as base
Incomplete=base.Incomplete

def rotate_axis(axis,a,b):
 axis=np.asarray(axis,float);a=np.asarray(a,float);b=np.asarray(b,float)
 if not np.isfinite(np.r_[axis,a,b]).all() or min(np.linalg.norm(axis),np.linalg.norm(a),np.linalg.norm(b))<=EPS:raise Incomplete('UNKNOWN_BRANCH_DIRECTION')
 a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);dot=float(np.clip(a@b,-1,1))
 if 1+dot<=EPS:raise Incomplete('UNKNOWN_BRANCH_ANTIPARALLEL')
 v=np.cross(a,b)
 if np.array_equal(a,b):return axis.copy()
 return axis+np.cross(v,axis)+np.cross(v,np.cross(v,axis))/(1+dot)

def clusters_for(sel,dirs,rr):
 clusters=[]
 for z,axis in zip(sel,dirs):
  for ax,members in clusters:
   if ax@axis>=np.cos(20*np.pi/180):members.append(int(z));break
  else:clusters.append((axis,[int(z)]))
 return clusters

def scan(d,leafids,q,centers,mode,guard):
 reps=np.unique(np.concatenate([d['leaves'][i].reps for i in leafids]));rx=d['representatives']['x'][reps]/d['p'];rt=d['representatives']['t'][reps]
 result=dict(status='CLEAR',reject=False,decision_complete=True,search_exhausted=True,centers_checked=0,first_witness=None)
 if len(reps)<9:return result
 ss,_,qt,_,_=project(rx,q);cs,_,ct,_,_=project(centers,q)
 for ci,center in enumerate(centers):
  guard();result['centers_checked']=ci+1;dx=rx-center;rr=np.linalg.norm(dx,axis=1);sel=np.flatnonzero((rr>EPS)&(rr<=4.))
  if len(sel)<9:continue
  raw=rt[sel]*np.where(np.sum(rt[sel]*dx[sel],1)>=0,1.,-1.)[:,None]
  try:dirs=np.asarray([rotate_axis(axis,qt[j],ct[ci]) for axis,j in zip(raw,sel)]) if mode=='TRANSPORT_BRANCH' else raw
  except Incomplete as exc:
   result.update(status=str(exc),reject=None,decision_complete=False,search_exhausted=False,first_witness=dict(center_index=ci,center=center,representative_ids=reps[sel],projected_s=ss[sel],center_s=cs[ci]));return result
  clusters=clusters_for(sel,dirs,rr);qual=[k for k,(_,ids) in enumerate(clusters) if len(ids)>=3 and np.ptp(rr[ids])>=2-EPS]
  if len(qual)>=3:
   rep=d['representatives'];source=[rep['member_rows'][rep['member_offsets'][int(k)]:rep['member_offsets'][int(k)+1]].tolist() for k in reps[sel]]
   result.update(status='BRANCH',reject=True,search_exhausted=False,first_witness=dict(center_index=ci,center=center,representative_ids=reps[sel],source_rows=source,leaf_ids=leafids,original_tangents=rt[sel],radial_axes=raw,tested_axes=dirs,projected_s=ss[sel],center_s=cs[ci],q_tangents=qt[sel],center_tangent=ct[ci],radial_distances=rr[sel],clusters=[dict(axis=ax,representative_ids=reps[ids],span=float(np.ptp(rr[ids])),qualifying=k in qual) for k,(ax,ids) in enumerate(clusters)]));return result
 return result

def pair_scan(d,ids,q,centers,guard):return {mode:scan(d,ids,q,centers,mode,guard) for mode in ['RADIAL_BRANCH','TRANSPORT_BRANCH']}

def evaluate(d,g,f,q,mode,guard):
 diagnostic=dict(status='NOT_REACHED');old_branch=base.branch
 def hooked(dd,ids,qq,gg):
  centers=np.vstack([qq]+[dd['leaves'][i].q for i in ids]);diagnostic.update(status='REACHED',union=pair_scan(dd,ids,qq,centers,gg),G=pair_scan(dd,g['leaves'],qq,centers,gg),F=pair_scan(dd,f['leaves'],qq,centers,gg))
  key=(g['id'],g['version']);cache=d.setdefault('_branch_premerge',{})
  if key not in cache:cache[key]=pair_scan(dd,g['leaves'],g['q'],np.vstack([g['q']]+[dd['leaves'][i].q for i in g['leaves']]),gg)
  diagnostic['premerge_G']=cache[key];chosen=diagnostic['union'][mode]
  if not chosen['decision_complete']:raise Incomplete(chosen['status'])
  return chosen['reject']
 base.branch=hooked
 try:return (*base.evaluate(d,g,f,q,guard),diagnostic)
 except Incomplete as exc:exc.branch_diagnostic=diagnostic;raise
 finally:base.branch=old_branch

def library(d,objects,gid,mode,index,guard=lambda:None):
 g=objects[gid];neighbors=index.query(g['q'],{gid},guard);records=[];result=dict(complete=False,neighbors=neighbors,records=records,selected=None)
 try:
  for fid,distance in neighbors:
   guard();f=objects[fid];result['current_donor']=fid
   if len(np.union1d(g['rows'],f['rows']))>8192:raise Incomplete('MEMBER_CAPACITY')
   for rec in base.proposals(g['q'],f['q'],guard):
    rec.update(donor=fid,distance_p=distance,connectable=False,branch_diagnostic=dict(status='NOT_REACHED'));records.append(rec)
    if rec['reason']!='template':continue
    x=d['asset']['means'][np.union1d(g['rows'],f['rows'])]/d['p'];q,fitmeta=base.fit(rec['template'],x,np.ones(len(rec['template']),bool),guard);rec['fit']=fitmeta
    try:ok,why,met,q,diag=evaluate(d,g,f,q,mode,guard)
    except Incomplete as exc:rec['branch_diagnostic']=getattr(exc,'branch_diagnostic',dict(status='UNRESOLVED'));rec['reason']=str(exc);raise
    rec.update(connectable=ok,reason=why,metrics=met,q=q,branch_diagnostic=diag)
    old_s,_,_,old_seg,old_near=project(g['q'],rec['template']);ts=arc(rec['template']);u=(old_s-ts[old_seg])/np.diff(ts)[old_seg];mapped=(1-u[:,None])*q[old_seg]+u[:,None]*q[old_seg+1]
    rec['old_curve_motion_p']=dict(max=float(np.linalg.norm(mapped-g['q'],axis=1).max()),rms=float(np.sqrt(np.mean(np.sum((mapped-g['q'])**2,1)))),fit_only_max=float(np.linalg.norm(mapped-old_near,axis=1).max()),correspondence='fixed template closest-segment barycentric coordinates')
  result.update(complete=True,selected=base.best(records),reason='complete')
 except (Incomplete,TimeoutError) as exc:result['reason']=str(exc);result['unattempted_donors']=[fid for fid,_ in neighbors if fid>=result.get('current_donor',-10**18)]
 return result
