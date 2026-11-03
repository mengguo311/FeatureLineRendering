"""Compact complete observation evidence and exact prior-relay replay receipts."""
from runtime_io import *
from collections import Counter
from frontier_core import choices
from relay_core import relay_candidates

def replay_prior(c,d,state,index,oracle,guard):
 root=Path(c['prior_relay_visits_root']);paths=sorted(root.glob('*.json'));assert len(paths)==8
 expected={};receipts=[];contexts={sid:{sid} for sid in state['chains']}
 for p in paths:
  v=json.loads(p.read_text());key=(v['seed'],v['side']);assert key not in expected;expected[key]=(v,p)
 for sid in sorted(state['chains']):
  for side in (0,1):
   guard();v,p=expected[(sid,side)];assert v['version']==state['versions'][sid]
   lib=relay_candidates(d,state,sid,side,index,oracle,guard,256,3)
   for key,value in lib.items():assert json.loads(json.dumps(value,allow_nan=False))==v[key],'PRIOR_RELAY_REPLAY '+key
   choice=choices(lib['records']);assert choice==v['shadow'] and choice['BASE'] is None and choice['HISTORY'] is None
   contexts[sid].update(z['donor'] for z in lib['records']);receipts.append(dict(seed=sid,side=side,path=str(p),sha256=sha(p),records=len(lib['records']),matched=True))
 return dict(status='MATCHED',visits=receipts),contexts

def export_bank(out,c,d,binding):
 out=Path(out);ids=sorted(d['leaves']);ko=[0];knots=[];io=[0];iv=[];original_ko=[0];original_knots=[]
 for cid in ids:
  leaf=d['leaves'][cid];knots.extend(leaf.q);ko.append(len(knots));iv.extend(leaf.intervals);io.append(len(iv));original_knots.extend(d['original_leaves'][cid].q);original_ko.append(len(original_knots))
 nz(out/'OBSERVED_CARRIERS.npz',carrier_id=np.array(ids),version=np.array([d['leaves'][i].version for i in ids]),valid=np.array([d['leaves'][i].valid for i in ids]),knot_offsets=np.array(ko),knots_p=np.asarray(knots),interval_offsets=np.array(io),intervals_p=np.asarray(iv).reshape(-1,2),original_knot_offsets=np.array(original_ko),original_knots_p=np.asarray(original_knots))
 keys=sorted(d['ports']);off=[0];rows=[];bins=[];distance=[]
 for key in keys:
  v=d['ports'][key];rows.extend(v['rows']);bins.extend(v['bins']);distance.extend(v.get('distance_from_port_p',[]));off.append(len(rows))
 def field(name):return np.asarray([d['ports'][k].get(name) if d['ports'][k].get(name) is not None else [np.nan]*3 for k in keys],float)
 nz(out/'PORT_EVIDENCE.npz',carrier_id=np.array([k[0] for k in keys]),port=np.array([k[1] for k in keys]),known=np.array([d['ports'][k]['known'] for k in keys]),reason=np.array([d['ports'][k]['reason'] for k in keys]),axis=field('axis'),q_obs_outward=field('q_obs_outward'),original_q_outward=field('original_q_outward'),eigenvalues=field('eigenvalues'),window_offsets=np.array(off),rows=np.array(rows,np.int64),bins=np.array(bins,np.int64),distance_from_port_p=np.array(distance),sign=np.array([d['ports'][k].get('sign',0) for k in keys]))
 js(out/'LEAF_CHECKS.json',dict(records=d['observation_receipts'],reasons=dict(Counter(x['status'] for x in d['observation_receipts'])),port_reasons=dict(Counter(v['reason'] for v in d['ports'].values()))))
 js(out/'SCHEMA.json',dict(original_carriers=c['carriers'],original_sha256=c['input_files'][c['carriers']],units='p normalized',all_members_preserved=True,unknown_axis_nan=True,old_q_preserved=True,auxiliary_never_rendered=True))
 checkpoint(out,['OBSERVED_CARRIERS.npz','PORT_EVIDENCE.npz','LEAF_CHECKS.json','SCHEMA.json'],binding,'COMPLETE_OBSERVATION_BANK');verify_checkpoint(out,binding)
