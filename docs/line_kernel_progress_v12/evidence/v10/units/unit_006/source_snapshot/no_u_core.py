"""Only the U reward changes; original complete candidates, geometry and legality are reused."""
from runtime_io import *
import copy
import whole_core as base
import scan65_relaxed_core as inherited
ORIGINAL='R2_R4_R6_OFF_TRANSPORT'
POLICIES={ORIGINAL:[2,4,6],'NO_U_REWARD':[2,4,6]}

def without_reward(original):
 new=copy.deepcopy(original)
 for r in new['records']:
  r['policy']='NO_U_REWARD'
  if not r['connectable']:continue
  m=r['metrics'];old=m['score'];U=m['unique_donor_support_p'];score=old+.25*U/(1+U)
  if not np.isfinite(score):raise base.Incomplete('NONFINITE_SCORE')
  m.update(score=score,score_original=old,unique_reward_coefficient=0.)
 new['selected']=base.best(new['records']) if new['complete'] else None
 return new

def libraries(d,objects,gid,index,guard=lambda:None):
 original=inherited.libraries(d,objects,gid,index,guard)[ORIGINAL]
 new=without_reward(original);banks={ORIGINAL:original,'NO_U_REWARD':new}
 new['relation_diagnostics']=inherited.evidence(new,objects,gid)
 for donor in new['relation_diagnostics']['donors']:
  for z in donor['interpretations']:
   if z['score_terms'] is not None:
    z['score_terms']['unique_support']=0.
    z['score_original']=new['records'][z['record_index']]['metrics']['score_original']
 paired={p:b['relation_diagnostics'] for p,b in banks.items()}
 choices={p:dict(complete=b['complete'],selected=b['selected'],donor=None if b['selected'] is None else b['records'][b['selected']]['donor'],reason=b['reason']) for p,b in banks.items()}
 shadow={p:[dict(donor=r['donor'],relation=r['relation'],direction=r['direction'],reason=r['reason'],connectable=r['connectable'],score=r.get('metrics',{}).get('score')) for r in b['records']] for p,b in banks.items()}
 for b in banks.values():
  b['paired_relation_diagnostics']=paired;b['shadow_choices']=choices;b['shadow_records']=shadow
  b['score_comparison']=dict(group=gid,original_policy=ORIGINAL,new_policy='NO_U_REWARD',original_selected=original['selected'],new_selected=new['selected'],same_state=True,complete=all(z['complete'] for z in banks.values()),changed_choice=original['selected']!=new['selected'],original_control_executed=False,all_candidate_geometry_and_legality_identical=True)
 return banks

def library(d,objects,gid,policy,index,guard=lambda:None):return libraries(d,objects,gid,index,guard)[policy]
