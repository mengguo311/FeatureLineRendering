"""Cohort checkpoints: unchanged membership computation, truthful expanded scope."""
from frontier_delivery import *
from overlap_core import map_intervals
import copy

def save_stage(out,c,d,state,binding):
 out=Path(out);old=d['membership'];m={k:v.copy() for k,v in old.items()};m['previous_edge_id']=old['edge_id'].copy();m['composite_version']=np.full(len(m['edge_id']),-1,np.int64);groups=[]
 aliases={cid:sid for sid,ch in state['chains'].items() for cid,_ in ch}
 if 'auxiliary_carrier_id' in m:
  raw=m['auxiliary_carrier_id'];aux=raw.copy();owner=d['owner'].copy()
  for cid,sid in aliases.items():aux[raw==cid]=sid;owner[d['owner']==cid]=sid
  aux[aux==owner[:,None]]=-1
  if aux.shape[1]==2:
   aux[:,1][aux[:,0]==aux[:,1]]=-1;move=(aux[:,0]<0)&(aux[:,1]>=0);aux[move,0]=aux[move,1];aux[move,1]=-1
  m['auxiliary_composite_id']=aux
 for sid,ch in sorted(state['chains'].items()):
  met=state['metrics'][sid];rows=np.concatenate([d['leaves'][cid].rows for cid,_ in ch]);activate=met.get('seedlets',0)>=3 and len(rows)>=6 and met.get('supported_length_p',0)>=4-EPS
  if len(ch)>1:
   assert met['seed_status']=='valid';sel=(old['edge_id'][rows]>=0)|activate;rr=rows[sel];m['edge_id'][rr]=sid;m['reason_code'][rr]=0;m['provisional'][rr]=True;m['composite_version'][rr]=state['versions'][sid]
  groups.append(dict(edge_id=sid,version=state['versions'][sid],leaves=[dict(carrier_id=cid,version=d['leaves'][cid].version,reverse=rev) for cid,rev in ch],**met))
 assert not np.any((old['edge_id']>=0)&(m['edge_id']<0))
 for sid,ch in state['chains'].items():
  for cid,_ in ch:
   rows=d['leaves'][cid].rows
   if np.any(old['edge_id'][rows]>=0):assert len(np.unique(m['edge_id'][rows]))==1
 nz(out/'MEMBERSHIP.npz',**m);js(out/'GROWTH_STATE.json',serial(state));js(out/'GROUPS.json',dict(groups=groups,background_reference=c['membership'],scope='pre-frozen expanded protected M5 seed cohort; single-overlap or endpoint-relay frontier',seed_ids=sorted(state['chains']),global_search=False))
 js(out/'LINEAGE.json',dict(events=state['events'],leaf_reference=c['carriers'],accepted_merge_is_ground_truth=False))
 ids=sorted(state['curves']);ko=[0];knots=[]
 for sid in ids:knots.extend(np.asarray(state['curves'][sid])*d['p']);ko.append(len(knots))
 nz(out/'CARRIERS.npz',carrier_id=np.array(ids),version=np.array([state['versions'][sid] for sid in ids]),knot_offsets=np.array(ko),knots=np.asarray(knots),geometry_kind=np.asarray('finite_overlap_auxiliary_composite'))
 leafids=sorted(aliases);ko=[0];knots=[]
 for cid in leafids:knots.extend(d['original_leaves'][cid].q*d['p']);ko.append(len(knots))
 nz(out/'ORIGINAL_LEAF_CARRIERS.npz',carrier_id=np.array(leafids),version=np.array([d['original_leaves'][i].version for i in leafids]),knot_offsets=np.array(ko),knots=np.asarray(knots))
 js(out/'CARRIER_SCHEMA.json',dict(auxiliary_curve_replaced=True,original_leaf_q_unchanged=True,all_original_members_retained=True,no_auxiliary_ink=True,support_coordinate='current auxiliary arc; mapped original support, not new observations',reference=c['carriers'],reference_sha256=c['input_files'][c['carriers']]))
 files=['MEMBERSHIP.npz','GROWTH_STATE.json','GROUPS.json','LINEAGE.json','CARRIERS.npz','ORIGINAL_LEAF_CARRIERS.npz','CARRIER_SCHEMA.json']
 checkpoint(out,files,binding,'COMPLETE_OVERLAP_MEMBERSHIP_TOPOLOGY');verify_checkpoint(out,binding)
 cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
 for k in m:np.testing.assert_array_equal(cold[k],m[k])
 return cold,groups

from overlap_delivery import statistics_overlap,diagnostics

def statistics(out,c,d,m,groups,state,starting,guard):
 statistics_overlap(out,c,d,m,groups,state,guard)
 enriched=json.loads((Path(out)/'GROUP_STATISTICS.json').read_text())['groups'];result=[]
 for g in enriched:
  guard();sid=g['edge_id'];base=starting['metrics'][sid]
  if g.get('seed_status')!='valid' or base.get('seed_status')!='valid':
   result.append(dict(seed=sid,status='NOT_RUN_INVALID_SEED',new_accepts=state['accepted'][sid]));continue
  q=np.asarray(state['curves'][sid]);q0=np.asarray(starting['curves'][sid]);dom=project(q0,q)[0];lo,hi=float(min(dom)),float(max(dom))
  outside=sum(max(0.,min(b,lo)-a)+max(0.,b-max(a,hi)) for a,b in g['supported_intervals'])
  from overlap_core import at
  pts=np.array([at(q0,s) for pair in base['supported_intervals'] for s in pair]);union0=union_intervals(project(pts,q)[0].reshape(-1,2))[1]
  result.append(dict(seed=sid,status='evaluated',new_accepts=state['accepted'][sid],support_outside_starting_seed_p=outside,support_union_gain_over_mapped_start_p=g['supported_length_p']-union0,longest_run_before_p=base['longest_continuous_run_p'],longest_run_after_p=g['longest_continuous_run_p'],max_gap_p=g['max_gap_p'],substantial_M4_contributors=sum(x['substantial'] for x in g['M4_contributions']),new_proxy_growth_gate=bool(outside>=4-EPS and sum(x['substantial'] for x in g['M4_contributions'])>=3),physical_identity_verified=False))
 js(Path(out)/'INCREMENTAL_STATISTICS.json',dict(reference=c['initial_stage'],groups=result,scope='unit006 starting cohort curves; old four retain prior composite seams; new seeds use observed M5 q',support_union_is_not_continuous_observation=True))
 return result

def choose_visuals(c,selected,incremental,saved):
 kinds={r['carrier_id']:r['model'] for r in selected};ranking={i:0. for i in kinds};losses={i:0 for i in kinds}
 for arm,rows in incremental.items():
  for r in rows:
   if r['seed'] in kinds:ranking[r['seed']]=max(ranking[r['seed']],r.get('support_outside_starting_seed_p',0.))
 baseline=saved['NO_FURTHER_GROWTH'][0]['edge_id']
 for arm in ('BASE','HISTORY'):
  labels=saved[arm][0]['edge_id']
  for sid in kinds:losses[sid]=max(losses[sid],int(np.sum((baseline==sid)&(labels!=sid))))
 chosen=set(i for i,_ in c['fixed_seeds']);reasons={i:['fixed_prior_seed'] for i in chosen}
 for kind in ('line','polyline'):
  for sid in sorted((i for i in kinds if kinds[i]==kind),key=lambda i:(-ranking[i],i))[:3]:chosen.add(sid);reasons.setdefault(sid,[]).append('top3_'+kind+'_outward_proxy')
 for sid in sorted((i for i in kinds if losses[i]>0),key=lambda i:(-losses[i],i))[:3]:chosen.add(sid);reasons.setdefault(sid,[]).append('top3_membership_damage')
 return sorted(chosen),dict(cases=[dict(seed=i,reasons=reasons[i],outward_proxy_p=ranking.get(i),lost_or_reassigned_start_rows=losses.get(i,0)) for i in sorted(chosen)],zero_damage_no_fabricated_damage_case=not any(losses.values()),zero_growth_cases_are_inherited=True)
