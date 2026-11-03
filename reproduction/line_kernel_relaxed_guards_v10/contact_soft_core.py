"""Finite ranking-only contact cost; shared unchanged whole-group fitted candidates."""
from runtime_io import *
import copy
import whole_core as base
import group_fit_core as fitted
import scan65_relaxed_core as relation_core
ORIGINAL='BASE_J'
NEW='CONTACT_SOFT_J'
POLICIES={ORIGINAL:[2,4,6],NEW:[2,4,6]}
COEFFICIENT=.01

def score_bank(original,coefficient):
 bank=copy.deepcopy(original);bank.pop('fit_control_library',None)
 for rec in bank['records']:
  if not rec['connectable']:continue
  m=rec['metrics'];flag=m.get('rule6',{}).get('self_contact')
  if not isinstance(flag,(bool,np.bool_)):
   bank.update(complete=False,selected=None,reason='MISSING_CONTACT_DIAGNOSTIC');return bank
  old=float(m['score']);term=float(coefficient*bool(flag));value=old+term
  if not np.isfinite(value):
   bank.update(complete=False,selected=None,reason='NONFINITE_CONTACT_SOFT_SCORE');return bank
  m['score']=value;m['contact_soft']=dict(base_score=old,coefficient=coefficient,indicator=bool(flag),finite_increment=term,score=value,hard_veto=False)
  if 'group_balance' in m:m['group_balance']['score_terms']['contact_soft']=term
 if bank['complete']:bank['selected']=base.best(bank['records'])
 else:bank['selected']=None
 return bank

def libraries(d,objects,gid,index,guard=lambda:None):
 original=fitted.libraries(d,objects,gid,index,guard);raw=original[fitted.NEW];row=original[fitted.ORIGINAL]
 banks={ORIGINAL:score_bank(raw,0.),NEW:score_bank(raw,COEFFICIENT)}
 for policy,bank in banks.items():
  for rec in bank['records']:rec['score_policy']=policy
  bank['relation_diagnostics']=relation_core.evidence(bank,objects,gid)
  for donor in bank['relation_diagnostics']['donors']:
   for z in donor['interpretations']:
    m=bank['records'][z['record_index']].get('metrics',{})
    if 'group_balance' in m:z.update(score_terms=m['group_balance']['score_terms'],group_balance=m['group_balance'])
    if 'contact_soft' in m:z['contact_soft']=m['contact_soft']
 choices={p:dict(complete=b['complete'],selected=b['selected'],donor=None if b['selected'] is None else b['records'][b['selected']]['donor'],reason=b['reason']) for p,b in banks.items()}
 shadow={p:[dict(donor=r['donor'],relation=r['relation'],direction=r['direction'],reason=r['reason'],connectable=r['connectable'],score=r.get('metrics',{}).get('score')) for r in b['records']] for p,b in banks.items()}
 for bank in banks.values():
  bank['shadow_choices']=choices;bank['shadow_records']=shadow;bank['paired_relation_diagnostics']={p:b['relation_diagnostics'] for p,b in banks.items()}
  bank['score_comparison']=dict(group=gid,original_policy=ORIGINAL,new_policy=NEW,original_selected=banks[ORIGINAL]['selected'],new_selected=banks[NEW]['selected'],same_state=True,complete=all(b['complete'] for b in banks.values()),changed_choice=banks[ORIGINAL]['selected']!=banks[NEW]['selected'],original_control_executed=True,all_candidate_geometry_and_legality_identical=True,fit_row_weights_unchanged=True,shared_discovery_and_templates=True,selected_geometry_changed=False,contact_coefficient=COEFFICIENT,row_fit_shadow_only=True)
  bank['fit_control_library']=row
 banks[ORIGINAL]['baseline_fit_library']=raw
 return banks

def library(d,objects,gid,policy,index,guard=lambda:None):return libraries(d,objects,gid,index,guard)[policy]
