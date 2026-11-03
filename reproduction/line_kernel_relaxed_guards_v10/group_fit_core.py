"""Whole-group fitting weights; discovery, balanced score and relaxed guards unchanged."""
from runtime_io import *
import copy
import whole_core as base
import branch_core
import balanced_core as scoring
import scan65_relaxed_core as relation_core
from geometry_base import EPS,arc,project
from scipy.sparse import coo_matrix,vstack,eye,diags
from scipy.sparse.linalg import lsqr
ORIGINAL='GROUP_BALANCED_SCORE'
NEW='GROUP_BALANCED_FIT'
POLICIES={ORIGINAL:[2,4,6],NEW:[2,4,6]}
Incomplete=base.Incomplete

def fit_loss(q,x,template,side):
 dist=project(x,q)[1];rho=np.where(dist<=.5,.5*dist**2,.5*(dist-.25))
 means=[float(np.mean(rho[side==h])) for h in (0,1)]
 smooth=.05*float(np.mean(np.sum(np.diff(q,n=2,axis=0)**2,axis=1))) if len(q)>2 else 0.
 tether=.001*float(np.mean(np.sum((q-template)**2,axis=1)))
 return dict(G_huber_mean=means[0],F_huber_mean=means[1],position=.5*sum(means),smooth=smooth,template=tether,total=.5*sum(means)+smooth+tether)

def partition(g,f):
 gr=np.unique(g['rows']);fr=np.unique(f['rows'])
 if not len(gr) or not len(fr) or np.intersect1d(gr,fr).size:raise Incomplete('MEMBERSHIP_PARTITION')
 rows=np.union1d(gr,fr);side=np.where(np.isin(rows,gr),0,1)
 return rows,side

def libraries(d,objects,gid,index,guard=lambda:None):
 g=objects[gid];neighbors=index.query(g['q'],{gid},guard)
 banks={p:dict(complete=False,neighbors=neighbors,records=[],selected=None,fit_calls=0,evaluate_calls=0) for p in POLICIES}
 calls=d.setdefault('_calls',{});calls.setdefault('fits',0);calls.setdefault('evaluations',0)
 try:
  for fid,distance in neighbors:
   guard();f=objects[fid];rows,side=partition(g,f)
   for bank in banks.values():bank['current_donor']=fid
   if len(rows)>8192:raise Incomplete('MEMBER_CAPACITY')
   for template in base.proposals(g['q'],f['q'],guard):
    for policy,bank in banks.items():
     rec=dict(template,donor=fid,distance_p=distance,connectable=False,branch_diagnostic=dict(status='NOT_REACHED'),policy=policy,relaxed_rule_groups=[2,4,6]);bank['records'].append(rec)
     if template['reason']!='template':continue
     try:
      guard();x=d['asset']['means'][rows]/d['p'];movable=np.ones(len(template['template']),bool)
      q,meta=(base.fit(template['template'],x,movable,guard) if policy==ORIGINAL else fit(template['template'],x,movable,side,rows,guard))
      calls['fits']+=1;bank['fit_calls']+=1
      if '_evidence' in meta:rec['fit_evidence']=meta.pop('_evidence')
      rec['fit']=meta
      ok,why,m,qq,diag=branch_core.evaluate(d,g,f,q.copy(),'TRANSPORT_BRANCH',guard,relaxed=[2,4,6])
      calls['evaluations']+=1;bank['evaluate_calls']+=1
      rec.update(connectable=ok,reason=why,metrics=m,q=qq,branch_diagnostic=diag)
      old_s,_,_,old_seg,old_near=project(g['q'],template['template']);ts=arc(template['template']);u=(old_s-ts[old_seg])/np.diff(ts)[old_seg];mapped=(1-u[:,None])*qq[old_seg]+u[:,None]*qq[old_seg+1]
      rec['old_curve_motion_p']=dict(max=float(np.linalg.norm(mapped-g['q'],axis=1).max()),rms=float(np.sqrt(np.mean(np.sum((mapped-g['q'])**2,1)))),fit_only_max=float(np.linalg.norm(mapped-old_near,axis=1).max()),correspondence='fixed template closest-segment barycentric coordinates')
      if ok:
       old=m['score'];U=m['unique_donor_support_p'];m.update(score=old+.25*U/(1+U),score_original=old,unique_reward_coefficient=0.)
       scoring.balanced_record(d,g,f,rec)
     except Incomplete as exc:
      rec['reason']=str(exc);rec['connectable']=False;rec['branch_diagnostic']=getattr(exc,'branch_diagnostic',dict(status='UNRESOLVED'));bank['policy_incomplete']=str(exc)
  for bank in banks.values():
   if bank.get('policy_incomplete'):bank.update(complete=False,selected=None,reason=bank['policy_incomplete'])
   else:bank.update(complete=True,selected=base.best(bank['records']),reason='complete')
 except (Incomplete,TimeoutError) as exc:
  for bank in banks.values():bank.update(complete=False,selected=None,reason=str(exc),unattempted_donors=[fid for fid,_ in neighbors if fid>=bank.get('current_donor',-10**18)])
 ids=[fid for fid,_ in neighbors];rr=[objects[fid]['rows'] for fid in ids]
 relation_rows=dict(group_rows=g['rows'],donor_ids=np.asarray(ids,np.int64),donor_rows=np.concatenate(rr) if rr else np.empty(0,np.int64),donor_offsets=np.r_[0,np.cumsum([len(r) for r in rr])])
 for policy,bank in banks.items():
  bank['relation_rows']=relation_rows;bank['relation_diagnostics']=relation_core.evidence(bank,objects,gid)
  for donor in bank['relation_diagnostics']['donors']:
   for z in donor['interpretations']:
    m=bank['records'][z['record_index']].get('metrics',{})
    if 'group_balance' in m:z.update(score_terms=m['group_balance']['score_terms'],group_balance=m['group_balance'])
 choices={p:dict(complete=b['complete'],selected=b['selected'],donor=None if b['selected'] is None else b['records'][b['selected']]['donor'],reason=b['reason']) for p,b in banks.items()}
 shadow={p:[dict(donor=r['donor'],relation=r['relation'],direction=r['direction'],reason=r['reason'],connectable=r['connectable'],score=r.get('metrics',{}).get('score')) for r in b['records']] for p,b in banks.items()}
 for bank in banks.values():
  bank['paired_relation_diagnostics']={p:b['relation_diagnostics'] for p,b in banks.items()};bank['shadow_choices']=choices;bank['shadow_records']=shadow
  bank['score_comparison']=dict(group=gid,original_policy=ORIGINAL,new_policy=NEW,original_selected=banks[ORIGINAL]['selected'],new_selected=banks[NEW]['selected'],same_state=True,complete=all(b['complete'] for b in banks.values()),changed_choice=banks[ORIGINAL]['selected']!=banks[NEW]['selected'],original_control_executed=False,all_candidate_geometry_and_legality_identical=False,fit_row_weights_unchanged=False,shared_discovery_and_templates=True)
  pick=banks[NEW]['selected']
  if pick is not None:
   a=banks[ORIGINAL]['records'][pick];b=banks[NEW]['records'][pick]
   bank['score_comparison']['selected_geometry_changed']='q' not in a or not np.array_equal(a['q'],b['q'])
 return banks

def library(d,objects,gid,policy,index,guard=lambda:None):
 banks=libraries(d,objects,gid,index,guard);chosen=banks[policy]
 if policy==NEW:chosen['fit_control_library']=banks[ORIGINAL]
 return chosen

def fit(template,x,movable,side,rows,guard=lambda:None):
 q=np.array(template,float,copy=True);k=len(q);n=len(x);move=np.flatnonzero(movable);fixed=np.flatnonzero(~np.asarray(movable,bool));receipts=[]
 side=np.asarray(side,np.int8);rows=np.asarray(rows,np.int64);assert len(side)==n and len(rows)==n and set(side)=={0,1}
 counts=np.bincount(side,minlength=2);base_weights=1./(2*counts[side]);history=[];evidence=dict(rows=rows.copy(),side=side.copy(),base_weights=base_weights.copy())
 if n>8192 or k>257:raise Incomplete('FIT_CAPACITY')
 if not len(move):return q,dict(iterations=5,lsqr=[],fixed_all=True)
 D=coo_matrix((np.tile([1.,-2.,1.],max(0,k-2)),(np.repeat(np.arange(max(0,k-2)),3),np.ravel(np.arange(max(0,k-2))[:,None]+[0,1,2]))),shape=(max(0,k-2),k)).tocsr()
 for it in range(5):
  guard();ss,dist,_,seg,near=project(x,q);lens=np.linalg.norm(np.diff(q,axis=0),axis=1);u=(ss-arc(q)[seg])/np.maximum(lens[seg],1e-30)
  H=coo_matrix((np.c_[1-u,u].ravel(),(np.repeat(np.arange(n),2),np.c_[seg,seg+1].ravel())),shape=(n,k)).tocsr()
  # Huber rho=0.5*r^2 inside delta; normalized derivative weights.
  robust=np.minimum(1.,.5/np.maximum(dist,1e-30));weight=np.sqrt(robust/(4*counts[side]))
  evidence[f'round_{it}_robust_weights']=robust.copy();evidence[f'round_{it}_matrix_weights']=weight.copy()
  before_loss=fit_loss(q,x,template,side)
  matrix=vstack([diags(weight)@H,np.sqrt(.05/max(1,k-2))*D,np.sqrt(.001/k)*eye(k)],format='csr')
  rhs=np.vstack([weight[:,None]*x,np.zeros((max(0,k-2),3)),np.sqrt(.001/k)*template]);rhs-=matrix[:,fixed]@template[fixed]
  for dim in range(3):
   guard();res=lsqr(matrix[:,move],rhs[:,dim],atol=1e-8,btol=1e-8,iter_lim=2000)
   if res[1] not in (0,1,2,4,5):raise Incomplete('LSQR_NOT_CONVERGED '+str(res[1]))
   q[move,dim]=res[0];receipts.append([it,dim,int(res[1]),int(res[2]),float(res[3])])
  q[fixed]=template[fixed]
  history.append(dict(iteration=it,before=before_loss,after=fit_loss(q,x,template,side)))
  if not np.isfinite(q).all() or np.any(np.linalg.norm(np.diff(q,axis=0),axis=1)<=EPS):return q,dict(iterations=it+1,lsqr=receipts,degenerate=True,group_weighting=dict(G_count=int(counts[0]),F_count=int(counts[1]),position_weights=[.5,.5]),round_losses=history,_evidence=evidence)
 return q,dict(iterations=5,lsqr=receipts,old_fixed_exact=bool(np.array_equal(q[fixed],template[fixed])),max_knot_displacement_p=float(np.linalg.norm(q-template,axis=1).max()),group_weighting=dict(G_count=int(counts[0]),F_count=int(counts[1]),position_weights=[.5,.5],matrix_factor='sqrt(h_i/(4*n_H))',all_union_rows=True),round_losses=history,_evidence=evidence)
