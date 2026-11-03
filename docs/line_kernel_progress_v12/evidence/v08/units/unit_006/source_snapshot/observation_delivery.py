"""Full-row atomic topology checkpoints with explicit original/observed leaf provenance."""
from frontier_delivery import *
import copy

def base_save_stage(out,c,d,state,oracle,binding):
 old=d['membership'];m={k:v.copy() for k,v in old.items()};m['previous_edge_id']=old['edge_id'].copy();m['composite_version']=np.full(len(m['edge_id']),-1,np.int64);groups=[]
 for seed,chain in sorted(state['chains'].items()):
  ok,why,met=oracle(chain)
  if not ok:
   # Failed seed is a saved unmodified reference, never promoted.
   groups.append(dict(edge_id=seed,seed_status=why,leaves=[dict(carrier_id=i,version=d['leaves'][i].version,reverse=r) for i,r in chain]));continue
  rows=np.concatenate([d['leaves'][i].rows for i,_ in chain]);activate=met['seedlets']>=3 and len(rows)>=6 and met['supported_length_p']>=4-EPS
  if len(chain)>1:
   selected=(m['edge_id'][rows]>=0)|activate;rr=rows[selected];m['edge_id'][rr]=seed;m['reason_code'][rr]=0;m['composite_version'][rr]=state['versions'][seed];m['provisional'][rr]=True
  groups.append(dict(edge_id=seed,version=state['versions'][seed],seed_status='valid',leaves=[dict(carrier_id=i,version=d['leaves'][i].version,reverse=r) for i,r in chain],**met))
 # Explicit protected-leaf tracer invariant; not a general v08 scientific gate.
 assert not np.any((old['edge_id']>=0)&(m['edge_id']<0))
 for seed,chain in state['chains'].items():
  for i,_ in chain:
   rr=d['leaves'][i].rows
   if np.any(old['edge_id'][rr]>=0):assert len(np.unique(m['edge_id'][rr]))==1
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 nz(out/'MEMBERSHIP.npz',**m);js(out/'GROWTH_STATE.json',serial(state));js(out/'GROUPS.json',dict(groups=groups,background_reference=c['membership'],scope='four protected M5 seed prefixes; complete rows are not complete search'))
 js(out/'LINEAGE.json',dict(events=state['events'],leaf_reference=c['carriers'],accepted_merge_is_ground_truth=False))
 ids=sorted({i for ch in state['chains'].values() for i,_ in ch});offset=[0];knots=[]
 for i in ids:knots.extend(d['leaves'][i].q*d['p']);offset.append(len(knots))
 nz(out/'CARRIERS.npz',carrier_id=np.asarray(ids),version=np.array([d['leaves'][i].version for i in ids]),source_version=np.array([d['original_leaves'][i].version for i in ids]),auxiliary_config_sha256=np.asarray(binding),geometry_kind=np.asarray('support_clipped_q_obs'),knot_offsets=np.asarray(offset),knots=np.asarray(knots))
 js(out/'CARRIER_SCHEMA.json',dict(meaning='support-clipped auxiliary leaves in seed paths; original geometry is a separate bound reference',reference=c['carriers'],reference_sha256=c['input_files'][c['carriers']],ordered_composite_carriers='GROWTH_STATE.json',connectors_observed=False,observation_bank=c.get('observation_bank'),original_leaf_geometry_changed=False,auxiliary_leaf_geometry_changed=True))
 original_offsets=[0];original_knots=[]
 for i in ids:
  original_knots.extend(d['original_leaves'][i].q*d['p']);original_offsets.append(len(original_knots))
 nz(out/'ORIGINAL_LEAF_CARRIERS.npz',carrier_id=np.asarray(ids),version=np.array([d['original_leaves'][i].version for i in ids]),knot_offsets=np.asarray(original_offsets),knots=np.asarray(original_knots))
 checkpoint(out,['MEMBERSHIP.npz','GROWTH_STATE.json','GROUPS.json','LINEAGE.json','CARRIERS.npz','CARRIER_SCHEMA.json','ORIGINAL_LEAF_CARRIERS.npz'],binding,'COMPLETE_MEMBERSHIP_TOPOLOGY')
 verify_checkpoint(out,binding)
 cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
 for k,v in m.items():np.testing.assert_array_equal(cold[k],v)
 return cold,groups

def save_stage(out,c,d,state,oracle,binding):
 # Original auxiliary IDs remain immutable finite-leaf references. Add an explicit
 # current composite resolution, rather than silently changing their semantics.
 aliases={cid:seed for seed,chain in state['chains'].items() for cid,_ in chain}
 dd=dict(d);dd['membership']=dict(d['membership']);m=dd['membership']
 if 'auxiliary_carrier_id' in m:
  raw=m['auxiliary_carrier_id'];resolved=raw.copy()
  for cid,seed in aliases.items():resolved[raw==cid]=seed
  owner=d.get('owner',m.get('carrier_id'))
  if owner is not None:
   current=owner.copy()
   for cid,seed in aliases.items():current[owner==cid]=seed
   resolved[resolved==current[:,None]]=-1
  if resolved.shape[1]==2:
   resolved[:,1][resolved[:,1]==resolved[:,0]]=-1
   move=(resolved[:,0]<0)&(resolved[:,1]>=0);resolved[move,0]=resolved[move,1];resolved[move,1]=-1
  m['auxiliary_composite_id']=resolved
 ss=copy.deepcopy(state)
 ss['auxiliary_reference']=dict(state=c.get('state','fixture'),meaning='original saved row-anchor/finite-leaf alternatives; never newly validated physical identity',leaf_to_composite={str(k):v for k,v in aliases.items()})
 ss['persistent_ports']={seed:dict(left_leaf=chain[0][0],left_port=int(chain[0][1]),right_leaf=chain[-1][0],right_port=1-int(chain[-1][1])) for seed,chain in state['chains'].items()}
 return base_save_stage(out,c,dd,ss,oracle,binding)
