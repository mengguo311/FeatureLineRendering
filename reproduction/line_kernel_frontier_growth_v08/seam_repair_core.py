"""Bounded two-handle repair, with all original members and immutable outer knots."""
import copy,time,hashlib
import numpy as np
from scipy.optimize import least_squares
import overlap_core as oc
import contact_core, switch_core, paired_history_core
from geometry_base import arc,clean,project,EPS

def geometry(a,b,s,handles):
 h=np.asarray(handles,float)
 if h.shape!=(2,) or not np.isfinite(h).all() or np.any(h<1/6) or np.any(h>1/2):raise ValueError('handle_bounds')
 la=float(arc(a)[-1]);lb=float(arc(b)[-1]);lo=la-min(2.,la);hi=s+min(2.,lb-s)
 p0=oc.at(a,lo);p3=oc.at(b,hi);t0=oc.tangent_at(a,np.asarray(lo));t1=oc.tangent_at(b,np.asarray(hi));D=float(np.linalg.norm(p3-p0))
 if D<=EPS:raise ValueError('degenerate_chord')
 controls=np.array([p0,p0+h[0]*D*t0,p3-h[1]*D*t1,p3]);N=max(1,int(np.ceil(12*np.max(np.linalg.norm(np.diff(controls,axis=0),axis=1)))))
 if N>128:raise ValueError('sample_cap')
 t=np.linspace(0.,1.,N+1)[:,None];z=(1-t)**3*controls[0]+3*(1-t)**2*t*controls[1]+3*(1-t)*t*t*controls[2]+t**3*controls[3];z[0]=p0;z[-1]=p3
 q=clean(np.vstack([a[arc(a)<lo],z,b[arc(b)>hi]]))
 meta=dict(local_start_a_p=lo,local_end_b_p=hi,chord_p=D,bezier_controls_p=controls.tolist(),sample_segments=N,handles=h.tolist(),seam_p=float(project(oc.at(b,s)[None,:],q)[0][0]),seam_begin_q_p=float(project(p0[None,:],q)[0][0]),seam_end_q_p=float(project(p3[None,:],q)[0][0]),fixed_prefix_and_tail=True,no_fitting=False,representation='MEMBER_TWO_HANDLE',status='ok')
 return q,meta

def witness(x,t,q,rows,meta):
 ss,dist,tan,seg,_=project(x,q);angles=np.degrees(np.arccos(np.clip(abs(np.sum(t*tan,1)),0,1)))
 region=np.where(ss<meta['seam_begin_q_p']-EPS,'prefix',np.where(ss>meta['seam_end_q_p']+EPS,'tail','seam'))
 return dict(rows=np.asarray(rows).tolist(),distance_p=dist.tolist(),angle_deg=angles.tolist(),projection_s_p=ss.tolist(),projection_segment=seg.tolist(),region=region.tolist())

class Budget:
 def __init__(self):self.seconds=0.;self.calls=0;self.evaluations=0;self.cache={}
 def receipt(self):return dict(seconds=self.seconds,calls=self.calls,actual_residual_evaluations=self.evaluations,limit_seconds=200.)

class FitLimit(Exception):pass

def fit(a,b,s,x,t,rows,budget,guard=lambda:None):
 if len(rows)>8192:raise ValueError('member_cap')
 if len(rows)==0 or len(np.unique(rows))!=len(rows):raise ValueError('distinct_members_required')
 key=hashlib.sha256(b''.join(np.asarray(v).tobytes() for v in (a,b,np.array([s]),x,t,rows))).hexdigest()
 if key in budget.cache:return copy.deepcopy(budget.cache[key])
 if budget.seconds>=200.:raise TimeoutError('total_optimizer_budget')
 start=time.monotonic();budget.calls+=1;calls=0;rec=dict(success=False,member_rows=np.asarray(rows).tolist(),member_count=len(rows),single_call=True);n=len(rows)
 def residual(h):
  nonlocal calls
  guard()
  if budget.seconds+time.monotonic()-start>=200.:raise TimeoutError('total_optimizer_budget')
  if calls>=256 or time.monotonic()-start>=5.:raise FitLimit('per_proposal_fit_budget')
  calls+=1;budget.evaluations+=1;q,_=geometry(a,b,s,h);_,dd,tt,_,_=project(x,q);theta=np.degrees(np.arccos(np.clip(abs(np.sum(t*tt,1)),0,1)))
  rr=np.r_[dd/np.sqrt(n),theta/(60*np.sqrt(n)),.01*(np.asarray(h)-1/3)]
  if not np.isfinite(rr).all():raise ValueError('nonfinite_fit_residual')
  return rr
 try:
  result=least_squares(residual,np.array([1/3,1/3]),bounds=([1/6]*2,[1/2]*2),method='trf',jac='2-point',diff_step=1e-4,ftol=1e-8,xtol=1e-8,gtol=1e-8,max_nfev=64)
  if time.monotonic()-start>5.:raise FitLimit('per_proposal_fit_budget')
  q,meta=geometry(a,b,s,result.x);rec.update(success=bool(result.success),status=int(result.status),message=str(result.message),handles=result.x.tolist(),objective=float(2*result.cost),nfev=int(result.nfev),geometry=meta)
  if not result.success:q=None;rec['reason']='optimizer_not_converged'
 except TimeoutError as exc:q=None;rec.update(reason=str(exc),incomplete=True)
 except (FitLimit,ValueError) as exc:q=None;rec.update(reason=str(exc))
 finally:
  dt=time.monotonic()-start;budget.seconds+=dt;rec.update(elapsed_seconds=dt,actual_residual_evaluations=calls)
 budget.cache[key]=(q,rec);return copy.deepcopy((q,rec))

def repair_record(d,state,sid,side,z,budget,guard):
 if z.get('relation')!='overlap' or z.get('reason')!='whole_member_residual_tangent' or z.get('registration',{}).get('status')!='ok':return z
 z=copy.deepcopy(z);oldq=np.asarray(state['curves'][sid]);a=oldq if side else oldq[::-1];cid=z['donor'];rev=z['reverse'];b=d['leaves'][cid].q[::-1] if rev else d['leaves'][cid].q;s=z['attachment_s_oriented_p']
 chain=(state['chains'][sid] if side else oc.reverse_chain(state['chains'][sid]))+[(cid,rev)];canonical=chain if side else oc.reverse_chain(chain)
 rows=np.unique(np.concatenate([d['leaves'][i].rows for i,_ in canonical]));x=d['asset']['means'][rows]/d['p'];t=d['tangents'][rows]
 _,fm=geometry(a,b,s,[1/3,1/3]);fixed=np.asarray(z['proposed_outward_q_p']);z['original_rejection']=dict(reason=z['reason'],validation=copy.deepcopy(z['validation']),registration=copy.deepcopy(z['registration']),witness=witness(x,t,fixed,rows,fm))
 try:q,rec=fit(a,b,s,x,t,rows,budget,guard)
 except TimeoutError as exc:
  z.update(reason='incomplete_repair',repair=dict(success=False,incomplete=True,reason=str(exc)));return z
 z['repair']=rec
 if q is None:z['reason']='seam_repair_'+rec.get('reason','failed');return z
 meta=rec['geometry'];z['repaired_member_witness']=witness(x,t,q,rows,meta);z['registration']=dict(z['registration'],**meta);z['proposed_outward_q_p']=q.tolist();canonical_q=q if side else q[::-1]
 with contact_core.validation_policy('ARC'):ok,why,met=oc.validate(d,canonical,canonical_q,guard)
 z.update(reason=why,validation=met)
 if not ok:return z
 support=oc.outward_support(d,cid,rev,b,s,q,meta['seam_p'],a[-1],np.asarray(state['ports'][sid][side]['axis']));z.update(support)
 if support['outward_kernels']<6 or support['outward_support_p']<2-EPS:z['reason']='outward_support';return z
 inherited=switch_core.remap_connectors(oldq,state['metrics'][sid].get('unsupported_connectors_p',[]),canonical_q);met.update(seed_status='valid',unsupported_connectors_p=inherited)
 z.update(common=True,reason='common_candidate',chain=canonical,q=canonical_q.tolist(),metrics=met,new_ports=oc.current_ports(d,canonical,canonical_q,met['supported_intervals']),history=oc.history(a,oc.slice_q(b,s,float(arc(b)[-1])),0.),connector_intervals_p=inherited)
 return z

def library(d,state,sid,side,index,endpoints,rep,guard,c,budget):
 lib=contact_core.library(d,state,sid,side,index,endpoints,'ARC',guard,c['switch']['max_combined_prefixes'],c['switch']['max_endpoint_donors'])
 if rep=='REPAIR' and lib['status']=='COMPLETE':
  for j,z in enumerate(lib['records']):
   try:
    lib['records'][j]=repair_record(d,state,sid,side,z,budget,guard)
    if lib['records'][j].get('repair',{}).get('incomplete'):raise TimeoutError(lib['records'][j]['repair']['reason'])
   except TimeoutError as exc:
    lib.update(status='NOT_RUN_INCOMPLETE_REPAIR',complete_competition=False,repair_interruption=str(exc),unattempted_record_indices=list(range(j,len(lib['records']))))
    for record in lib['records']:record['common']=False
    break
 return paired_history_core.annotate(d,state,sid,side,lib,guard if lib['status']=='COMPLETE' else lambda:None)
