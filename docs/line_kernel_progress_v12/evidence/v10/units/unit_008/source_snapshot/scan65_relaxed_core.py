"""Unchanged R6 policy evaluator with same-donor, all-relation diagnostic accounting."""
from runtime_io import *
import r6_core as inherited
POLICIES=inherited.POLICIES

def evidence(bank,objects,gid):
 donors=[]
 for fid,distance in bank['neighbors']:
  interpretations=[]
  for i,r in enumerate(bank['records']):
   if r['donor']!=fid:continue
   m=r.get('metrics',{});terms=None
   if 'score' in m:
    U=m['unique_donor_support_p'];terms=dict(position=m['position_mean_square'],direction=.25*m['tangent_mean_square'],turn=.05*m['turn_mean_square'],gap=.1*m['max_gap_p']**2,complexity=.02*len(r['q'])/(m['length_p']+1),unique_support=-.25*U/(1+U))
   interpretations.append(dict(record_index=i,relation=r['relation'],direction=r['direction'],reason=r['reason'],connectable=r['connectable'],selected=bank['selected']==i,score=m.get('score'),score_terms=terms,unique_donor_support_p=m.get('unique_donor_support_p'),contact=m.get('contact'),max_gap_p=m.get('max_gap_p'),old_curve_motion_p=r.get('old_curve_motion_p'),rule6_status='REACHED' if 'rule6' in m else 'NOT_REACHED',rule6=m.get('rule6'),branch_status=r.get('branch_diagnostic',{}).get('status','NOT_REACHED')))
  donors.append(dict(donor=fid,distance_p=distance,rows_index=len(donors),donor_count=len(objects[fid]['rows']),union_count=len(np.union1d(objects[gid]['rows'],objects[fid]['rows'])),interpretations=interpretations))
 return dict(group=gid,group_count=len(objects[gid]['rows']),rows_file='RELATION_ROWS.npz',union_definition='unique(group_rows union donor_rows[offsets[index]:offsets[index+1]])',complete=bank['complete'],donors=donors,diagnostic_only=True,score_missing_is_NOT_REACHED=True,remapped_support_is_not_new_observation=True)

def libraries(d,objects,gid,index,guard=lambda:None):
 banks=inherited.libraries(d,objects,gid,index,guard)
 ids=[fid for fid,_ in next(iter(banks.values()))['neighbors']];rr=[objects[fid]['rows'] for fid in ids]
 rows=dict(group_rows=objects[gid]['rows'],donor_ids=np.asarray(ids,np.int64),donor_rows=np.concatenate(rr) if rr else np.empty(0,np.int64),donor_offsets=np.r_[0,np.cumsum([len(r) for r in rr])])
 for b in banks.values():b['relation_diagnostics']=evidence(b,objects,gid);b['relation_rows']=rows
 paired={p:b['relation_diagnostics'] for p,b in banks.items()}
 for b in banks.values():b['paired_relation_diagnostics']=paired
 return banks

def library(d,objects,gid,policy,index,guard=lambda:None):
 banks=libraries(d,objects,gid,index,guard);chosen=banks[policy]
 chosen['shadow_choices']={p:dict(complete=b['complete'],selected=b['selected'],donor=None if b['selected'] is None else b['records'][b['selected']]['donor'],reason=b['reason']) for p,b in banks.items()}
 chosen['shadow_records']={p:[dict(donor=r['donor'],relation=r['relation'],direction=r['direction'],reason=r['reason'],connectable=r['connectable'],score=r.get('metrics',{}).get('score')) for r in b['records']] for p,b in banks.items()}
 return chosen
