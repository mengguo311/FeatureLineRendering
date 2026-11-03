"""Select only actual new member changes; retain fixed small/negative cases honestly."""
import numpy as np
from geometry_base import EPS

def choose_visuals(c,d,incremental,saved):
 arms=c['arms'];start=saved['NO_FURTHER_GROWTH'][0]['edge_id'];kinds={int(k):v for k,v in c['seed_kinds'].items()}
 ranking={i:0. for i in kinds};loss={i:0 for i in kinds};changed={i:False for i in kinds}
 for arm in arms:
  labels=saved[arm][0]['edge_id']
  for sid in kinds:
   changed[sid]|=bool(np.any((labels==sid)!=(start==sid)));loss[sid]=max(loss[sid],int(np.sum((start==sid)&(labels!=sid))))
  for r in incremental[arm]:
   sid=r['seed'];ranking[sid]=max(ranking[sid],r.get('support_outside_starting_seed_p',0.))
 chosen=set(c['focus_carriers'])|{i for i,_ in c['fixed_seeds']};reasons={i:['fixed_case'] for i in chosen}
 for kind in ('line','polyline'):
  for sid in sorted((i for i in kinds if kinds[i]==kind and changed[i]),key=lambda i:(-ranking[i],i))[:3]:chosen.add(sid);reasons.setdefault(sid,[]).append('top3_actual_'+kind+'_member_change')
 for sid in sorted((i for i in kinds if loss[i]>0),key=lambda i:(-loss[i],i))[:3]:chosen.add(sid);reasons.setdefault(sid,[]).append('top3_damage')
 return sorted(chosen),dict(cases=[dict(seed=i,reasons=reasons[i],outward_proxy_p=ranking.get(i),lost_start_rows=loss.get(i,0)) for i in sorted(chosen)],zero_new_curves=not any(changed[i] and kinds[i]=='polyline' for i in kinds),zero_damage=not any(loss.values()),unchanged_or_tiny_cases_not_success=True)
