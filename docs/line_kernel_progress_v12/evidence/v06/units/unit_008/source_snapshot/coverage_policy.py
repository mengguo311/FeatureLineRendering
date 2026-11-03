"""Complete competition scope; display changes mean changed indivisible members."""
from runtime_io import *
from overlap_model import select_components

def select_scope(c,d):
 contexts,audit=select_components(dict(c,max_components=len(d['overlaps'])),d)
 covered=[rid for ctx in contexts for rid in ctx['overlap_record_ids']]
 assert len(covered)==len(set(covered)) and sorted(covered)==sorted(e['record_id'] for e in d['overlaps']),'INCOMPLETE_COMPETING_OVERLAP_GRAPH'
 return contexts,audit

def diagnostics(c,d,saved,contexts):
 key=lambda g:tuple(sorted(x['carrier_id'] for x in g['leaves']))
 current={};old={};chosen={};missing=[]
 for _,gs in saved.values():
  for g in gs:
   k=key(g)
   if k not in current or g['supported_length_p']>current[k]['supported_length_p']:current[k]=g
 for p in c['previous_arms'].values():
  for g in json.loads((Path(p)/'GROUPS.json').read_text())['groups']:old[key(g)]=g
 allg=dict(old);allg.update(current)
 rank=lambda k:(-allg[k]['supported_length_p'],allg[k]['edge_id'],k)
 def take(keys,n,label):
  ks=sorted(keys,key=rank)[:n]
  if not ks:missing.append(label)
  for k in ks:chosen.setdefault(k,[]).append(label)
 take(set(current)-set(old),3,'top3_actual_member_changes_vs_unit006')
 take(set(old)-set(current),3,'top3_lost_member_sets_vs_unit006')
 for kind in ('line','polyline'):
  take([k for k,g in current.items() if k not in old and g.get('model_kind',str(d.get('kinds',{}).get(g['anchor'],'')))==kind],1,'largest_new_'+kind+'_member_group')
 for cid in c.get('fixed_member_ids',[51111,51166,113545]):
  take([k for k in allg if cid in k],1,'fixed_'+str(cid))
 incident={}
 for i,(a,b) in enumerate(d['pairs']):incident.setdefault(a,[]).append(i);incident.setdefault(b,[]).append(i)
 def case(name,ids,labels):
  core=sorted(set(ids));records={r for cid in core for r in incident.get(cid,[])};halo=set(core)
  for ctx in contexts:
   if set(core)&set(ctx['carriers']):halo.update(ctx['evidence_carriers']);records.update(ctx['incident_record_ids'])
  for r in records:halo.update(d['pairs'][r])
  return dict(case_id=name,core_carriers=core,evidence_carriers=sorted(halo),incident_record_ids=sorted(records),labels=labels)
 cases=[case('COVERAGE_'+str(allg[k]['edge_id'])+'_'+hashlib.sha256(repr(k).encode()).hexdigest()[:8],k,chosen[k]) for k in sorted(chosen,key=rank)]
 for a,b in c['negative_pairs']:cases.append(case('NEGATIVE_'+str(a)+'_'+str(b),[a,b],['saved_negative_unknown_truth']))
 return dict(cases=cases,missing=missing,selection='actual leaf-set changes, not model-key changes; support descending then ID; complete incident neighborhoods',curved_label_not_visual_evidence=True)
