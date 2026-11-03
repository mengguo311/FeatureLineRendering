"""Matched R2/R4 and R2/R4/R6 policy evaluations; common finite proposals and all-member fit."""
from runtime_io import *
import whole_core as base
import branch_core
from geometry_base import project,arc
POLICIES={'R2_R4_OFF_TRANSPORT':[2,4], 'R2_R4_R6_OFF_TRANSPORT':[2,4,6]}

def libraries(d,objects,gid,index,guard=lambda:None):
 g=objects[gid];neighbors=index.query(g['q'],{gid},guard)
 result={p:dict(complete=False,neighbors=neighbors,records=[],selected=None,fit_calls=0,evaluate_calls=0) for p in POLICIES}
 try:
  for fid,distance in neighbors:
   guard();f=objects[fid]
   for bank in result.values():bank['current_donor']=fid
   rows=np.union1d(g['rows'],f['rows'])
   if len(rows)>8192:raise base.Incomplete('MEMBER_CAPACITY')
   for template in base.proposals(g['q'],f['q'],guard):
    if template['reason']=='template':
     q,fitmeta=base.fit(template['template'],d['asset']['means'][rows]/d['p'],np.ones(len(template['template']),bool),guard)
     d.setdefault('_calls',dict(fits=0,evaluations=0))['fits']+=1
    for policy,relaxed in POLICIES.items():
     bank=result[policy];rec=dict(template,donor=fid,distance_p=distance,connectable=False,branch_diagnostic=dict(status='NOT_REACHED'),policy=policy,relaxed_rule_groups=relaxed);bank['records'].append(rec)
     if template['reason']!='template':continue
     bank['fit_calls']+=1;rec['fit']=fitmeta
     try:ok,why,met,qq,diag=branch_core.evaluate(d,g,f,q.copy(),'TRANSPORT_BRANCH',guard,relaxed=relaxed)
     except base.Incomplete as exc:
      rec['branch_diagnostic']=getattr(exc,'branch_diagnostic',dict(status='UNRESOLVED'));rec['reason']=str(exc);bank['policy_incomplete']=str(exc);continue
     bank['evaluate_calls']+=1;d['_calls']['evaluations']+=1
     rec.update(connectable=ok,reason=why,metrics=met,q=qq,branch_diagnostic=diag)
     old_s,_,_,old_seg,old_near=project(g['q'],template['template']);ts=arc(template['template']);u=(old_s-ts[old_seg])/np.diff(ts)[old_seg];mapped=(1-u[:,None])*qq[old_seg]+u[:,None]*qq[old_seg+1]
     rec['old_curve_motion_p']=dict(max=float(np.linalg.norm(mapped-g['q'],axis=1).max()),rms=float(np.sqrt(np.mean(np.sum((mapped-g['q'])**2,1)))),fit_only_max=float(np.linalg.norm(mapped-old_near,axis=1).max()),correspondence='fixed template closest-segment barycentric coordinates')
  for bank in result.values():
   if bank.get('policy_incomplete'):bank.update(complete=False,selected=None,reason=bank['policy_incomplete'])
   else:bank.update(complete=True,selected=base.best(bank['records']),reason='complete')
 except (base.Incomplete,TimeoutError) as exc:
  for bank in result.values():bank.update(reason=str(exc),unattempted_donors=[fid for fid,_ in neighbors if fid>=bank.get('current_donor',-10**18)])
 return result

def library(d,objects,gid,policy,index,guard=lambda:None):
 banks=libraries(d,objects,gid,index,guard);chosen=banks[policy]
 chosen['shadow_choices']={p:dict(complete=b['complete'],selected=b['selected'],donor=None if b['selected'] is None else b['records'][b['selected']]['donor'],reason=b['reason']) for p,b in banks.items()}
 # Keep both policies' rejects/scores at identical geometry, without duplicating fits.
 chosen['shadow_records']={p:[dict(donor=r['donor'],relation=r['relation'],direction=r['direction'],reason=r['reason'],connectable=r['connectable'],score=r.get('metrics',{}).get('score')) for r in b['records']] for p,b in banks.items()}
 return chosen
