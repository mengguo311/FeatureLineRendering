"""Ranking-only equal G/F score; fits, candidates and relaxed legality are inherited."""
from runtime_io import *
import copy
import whole_core as base
import no_u_core as inherited
import scan65_relaxed_core as relation_core
from geometry_base import project,EPS
ORIGINAL='NO_U_REWARD'
NEW='GROUP_BALANCED_SCORE'
POLICIES={ORIGINAL:[2,4,6],NEW:[2,4,6]}

def side_evidence(d,rows,q):
 rows=np.unique(np.asarray(rows,np.int64))
 if not len(rows):raise base.Incomplete('EMPTY_GROUP_SCORE')
 s,dist,tan,segment,_=project(d['asset']['means'][rows]/d['p'],q)
 t=d['tangents'][rows];valid=np.isfinite(t).all(1)&(np.linalg.norm(t,axis=1)>EPS)
 theta=np.degrees(np.arccos(np.clip(abs(np.sum(t[valid]*tan[valid],1)),0,1)))
 if not np.isfinite(dist).all() or not np.isfinite(theta).all():raise base.Incomplete('NONFINITE_MEMBER_EVIDENCE')
 meta=dict(count=len(rows),valid_count=int(valid.sum()),direction_status='AVAILABLE' if valid.any() else 'UNKNOWN',position_mean_square=float(np.mean(dist**2)),tangent_mean_square=float(np.mean((theta/90)**2)) if valid.any() else None,position_weight=.5)
 arrays=dict(rows=rows,distance_p=dist,valid_direction=valid,angle_rows=rows[valid],angle_deg=theta,projection_s_p=s,projection_segment=segment)
 return meta,arrays

def balanced_record(d,g,f,record):
 a,aa=side_evidence(d,g['rows'],record['q']);b,bb=side_evidence(d,f['rows'],record['q'])
 avail=[z for z in [a,b] if z['valid_count']]
 if not avail:raise base.Incomplete('BALANCED_DIRECTION_UNREACHABLE_AFTER_COMMON_UNKNOWN')
 for z in [a,b]:z['direction_weight']=1./len(avail) if z['valid_count'] else 0.
 position=.5*(a['position_mean_square']+b['position_mean_square']);direction=float(np.mean([z['tangent_mean_square'] for z in avail]));m=record['metrics']
 terms=dict(position=position,direction=.25*direction,turn=.05*m['turn_mean_square'],gap=.1*m['max_gap_p']**2,complexity=.02*len(record['q'])/(m['length_p']+1),unique_support=0.)
 score=float(sum(terms.values()))
 if not np.isfinite(score):raise base.Incomplete('NONFINITE_SCORE')
 calls=d.setdefault('_calls',{});calls['balanced_scores']=calls.get('balanced_scores',0)+1
 m.update(score_no_u_reward=m['score'],score=score,balanced_position_mean_square=position,balanced_tangent_mean_square=direction,group_balance=dict(G=a,F=b,score_terms=terms,evidence_file='SCORE_EVIDENCE.npz',ranking_only=True))
 record['score_evidence']={**{'G_'+k:v for k,v in aa.items()},**{'F_'+k:v for k,v in bb.items()}}

def libraries(d,objects,gid,index,guard=lambda:None):
 original=inherited.libraries(d,objects,gid,index,guard)[ORIGINAL]
 new=copy.deepcopy(original)
 try:
  for r in new['records']:
   r['policy']=NEW
   if r['connectable']:
    guard();balanced_record(d,objects[gid],objects[r['donor']],r)
  new['selected']=base.best(new['records']) if new['complete'] else None
 except (base.Incomplete,TimeoutError) as exc:new.update(complete=False,selected=None,reason=str(exc))
 banks={ORIGINAL:original,NEW:new}
 new['relation_diagnostics']=relation_core.evidence(new,objects,gid)
 for donor in new['relation_diagnostics']['donors']:
  for z in donor['interpretations']:
   m=new['records'][z['record_index']].get('metrics',{})
   if 'group_balance' in m:z.update(score_terms=m['group_balance']['score_terms'],score_no_u_reward=m['score_no_u_reward'],group_balance=m['group_balance'])
 paired={p:b['relation_diagnostics'] for p,b in banks.items()}
 choices={p:dict(complete=b['complete'],selected=b['selected'],donor=None if b['selected'] is None else b['records'][b['selected']]['donor'],reason=b['reason']) for p,b in banks.items()}
 shadow={p:[dict(donor=r['donor'],relation=r['relation'],direction=r['direction'],reason=r['reason'],connectable=r['connectable'],score=r.get('metrics',{}).get('score')) for r in b['records']] for p,b in banks.items()}
 for b in banks.values():
  b['paired_relation_diagnostics']=paired;b['shadow_choices']=choices;b['shadow_records']=shadow
  b['score_comparison']=dict(group=gid,original_policy=ORIGINAL,new_policy=NEW,original_selected=original['selected'],new_selected=new['selected'],same_state=True,complete=all(z['complete'] for z in banks.values()),changed_choice=original['selected']!=new['selected'],original_control_executed=False,all_candidate_geometry_and_legality_identical=True,fit_row_weights_unchanged=True)
 return banks

def library(d,objects,gid,policy,index,guard=lambda:None):return libraries(d,objects,gid,index,guard)[policy]
