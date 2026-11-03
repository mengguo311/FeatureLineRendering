"""Cold saved-state restoration and unit005-only delivery."""
from runtime_io import *
from geometry_base import *
from frontier_delivery import serial
from overlap_delivery import save_stage,statistics_overlap,diagnostics
import overlap_core as oc
from switch_core import hydrate

def restore(c,d,guard):
 guard('readiness');root=Path(c['initial_stage']);cp=verify_checkpoint(root,c['prior_config_sha256']);state=hydrate(json.loads((root/'GROWTH_STATE.json').read_text()));m=dict(np.load(root/'MEMBERSHIP.npz',allow_pickle=False))
 assert len(m['edge_id'])==c['kernel_count'] and int(np.sum(m['edge_id']>=0))==c['initial_assigned'];np.testing.assert_array_equal(m['line_kernel_id'],np.arange(c['kernel_count']))
 assert state['next_version']==c['initial_next_version'];assert sorted(state['chains'])==sorted(x[0] for x in c['seeds'])
 assert state['used']=={i for chain in state['chains'].values() for i,_ in chain}
 arr=np.load(root/'CARRIERS.npz',allow_pickle=False)
 for j,sid in enumerate(arr['carrier_id']):
  sid=int(sid);assert state['versions'][sid]==int(arr['version'][j]);np.testing.assert_array_equal(np.asarray(state['curves'][sid])*d['p'],arr['knots'][arr['knot_offsets'][j]:arr['knot_offsets'][j+1]])
  for cid,_ in state['chains'][sid]:assert cid in d['leaves']
 groups=json.loads((root/'GROUPS.json').read_text())['groups']
 for g in groups:
  assert [(v['carrier_id'],bool(v['reverse'])) for v in g['leaves']]==state['chains'][g['edge_id']]
  for v in g['leaves']:assert v['version']==d['leaves'][v['carrier_id']].version
 return state,m,groups,cp

def copy_control(out,c,state,m,groups,cp,binding):
 out=Path(out);source=Path(c['initial_stage'])
 for name in list(cp['files'])+['CHECKPOINT.json']:
  blob=(source/name).read_bytes();atomic(out/name,lambda f,b=blob:f.write(b))
 verify_checkpoint(out,c['prior_config_sha256'])
 cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
 for k in m:np.testing.assert_array_equal(cold[k],m[k])
 js(out/'COPY_RECEIPT.json',dict(exact_saved_state_copy=True,source=str(source),source_checkpoint_sha256=sha(source/'CHECKPOINT.json'),current_config_sha256=binding,no_recompetition=True))
 return cold,groups

def replay_deadends(c,d,state,index,guard):
 receipts=[];contexts={sid:set(cid for cid,_ in ch) for sid,ch in state['chains'].items()}
 for path in c['deadend_visits']:
  guard();old=json.loads(Path(path).read_text());sid=old['seed'];side=old['side'];assert old['version']==state['versions'][sid]
  lib=oc.candidates(d,state,sid,side,index,guard,c['switch']['max_combined_prefixes'])
  for key,val in lib.items():assert json.loads(json.dumps(val,allow_nan=False))==old[key],'DEADEND_REPLAY '+key
  choice=oc.choices(lib['records']);assert choice==old['shadow'] and choice['BASE'] is None and choice['HISTORY'] is None
  for query in lib['queries']:contexts[sid].update(x[0] for x in query['neighbors'])
  receipts.append(dict(seed=sid,side=side,matched=True,path=path,sha256=sha(path)))
 return dict(status='MATCHED',visits=receipts),contexts

def statistics(out,c,d,m,groups,state,initial,guard):
 statistics_overlap(out,c,d,m,groups,state,guard)
 cumulative=json.loads((Path(out)/'GROUP_STATISTICS.json').read_text());result=[]
 for g in cumulative['groups']:
  guard();sid=g['edge_id']
  if g.get('seed_status')!='valid':continue
  q=np.asarray(state['curves'][sid]);q0=np.asarray(initial['curves'][sid]);dom=project(q0,q)[0];lo,hi=float(min(dom)),float(max(dom));ivs=g['supported_intervals'];outside=sum(max(0.,min(b,lo)-a)+max(0.,b-max(a,hi)) for a,b in ivs)
  oldiv=initial['metrics'][sid]['supported_intervals'];pts=np.array([oc.at(q0,s) for pair in oldiv for s in pair]);mapped=project(pts,q)[0].reshape(-1,2);union0=union_intervals(mapped)[1]
  result.append(dict(seed=sid,new_accepts=state.get('accepted',{}).get(sid,0),support_outside_unit004_seed_p=outside,support_union_gain_over_mapped_unit004_p=g['supported_length_p']-union0,internal_fill_or_pooling_proxy_p=g['supported_length_p']-union0-outside,longest_run_before_p=initial['metrics'][sid]['longest_continuous_run_p'],longest_run_after_p=g['longest_continuous_run_p'],original_M5_outward_support_p=g['support_outside_seed_domain_p'],substantial_M4_contributors=sum(z['substantial'] for z in g['M4_contributions']),new_proxy_growth_gate=bool(outside>=4-EPS and sum(z['substantial'] for z in g['M4_contributions'])>=3),physical_identity_verified=False))
 js(Path(out)/'INCREMENTAL_STATISTICS.json',dict(reference=c['initial_stage'],groups=result,scope='unit004 starting auxiliary curve; cumulative old-M5 statistics separate',support_union_is_not_continuous_observation=True))
