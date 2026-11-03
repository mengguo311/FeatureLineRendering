"""Fresh-scene displays selected by actual indivisible membership differences."""
from runtime_io import *
from paired_delivery import evidence_rows

def diagnostics(c,d,saved,contexts):
 key=lambda g:tuple(sorted(x['carrier_id'] for x in g['leaves']))
 current={};byarm={};chosen={};missing=[]
 for arm,(m,gs) in saved.items():
  byarm[arm]=set()
  for g in gs:
   k=key(g);rr=evidence_rows(d,k)
   if np.array_equal(m['edge_id'][rr],d['membership']['edge_id'][rr]):continue
   byarm[arm].add(k)
   if k not in current or g['supported_length_p']>current[k]['supported_length_p']:current[k]=g
 rank=lambda k:(-current[k]['supported_length_p'],current[k]['edge_id'],k)
 def take(keys,n,label):
  ks=sorted(keys,key=rank)[:n]
  if not ks:missing.append(label)
  for k in ks:chosen.setdefault(k,[]).append(label)
 take(byarm.get('greedy',set())^byarm.get('joint',set()),3,'top3_actual_arm_member_differences')
 take(set(current),3,'top3_actual_member_changes_vs_M4')
 for kind in ('line','polyline'):
  take([k for k,g in current.items() if g.get('model_kind',d.get('kinds',{}).get(g['anchor']))==kind],1,'largest_new_'+kind+'_member_group')
 for cid in c['fixed_member_ids']:take([k for k in current if cid in k],1,'fixed_descendant_'+str(cid))
 incident={}
 for i,(a,b) in enumerate(d['pairs']):incident.setdefault(a,[]).append(i);incident.setdefault(b,[]).append(i)
 def case(name,ids,labels):
  core=sorted(set(ids));assert all(i in d['leaves'] for i in core),'MISSING_FIXED_REFERENCE_LEAF'
  records={r for cid in core for r in incident.get(cid,[])};halo=set(core)
  for ctx in contexts:
   if set(core)&set(ctx['carriers']):halo.update(ctx['evidence_carriers']);records.update(ctx['incident_record_ids'])
  for r in records:halo.update(d['pairs'][r])
  return dict(case_id=name,core_carriers=core,evidence_carriers=sorted(halo),incident_record_ids=sorted(records),labels=labels)
 cases=[case('SCENE_'+str(current[k]['edge_id'])+'_'+hashlib.sha256(repr(k).encode()).hexdigest()[:8],k,chosen[k]) for k in sorted(chosen,key=rank)]
 for ids in c.get('reference_leaf_sets',[[cid] for cid in c['fixed_member_ids']]):
  cases.append(case('REFERENCE_'+'_'.join(map(str,ids)),ids,['inherited_M5_reference_not_new_growth']))
 for a,b in c['negative_pairs']:cases.append(case('NEGATIVE_'+str(a)+'_'+str(b),[a,b],['saved_negative_unknown_truth']))
 return dict(cases=cases,missing=missing,selection='member-set differences and changes versus M4; support descending then ID; complete incident neighborhoods',curved_label_not_visual_evidence=True)
