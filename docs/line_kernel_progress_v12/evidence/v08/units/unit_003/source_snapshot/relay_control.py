"""Reproduce saved unit001 one-step decisions; never rerun its renders/producers."""
from runtime_io import *
from frontier_core import candidates,choices

def replay_one_step(c,d,state,index,oracle,guard):
 root=Path(c['prior_visits_root']);receipts=[];expected_paths=sorted(root.glob('*.json'))
 assert len(expected_paths)==8,'PRIOR_VISIT_COUNT'
 expected={}
 for p in expected_paths:
  v=json.loads(p.read_text());key=(v['seed'],v['side']);assert key not in expected;expected[key]=(v,p)
 for seed in sorted(state['chains']):
  for side in (0,1):
   guard();v,p=expected[(seed,side)];assert v['version']==state['versions'][seed]
   records=candidates(d,state,seed,side,index,oracle,guard);shadow=choices(records)
   assert json.loads(json.dumps(records,allow_nan=False))==v['records'],'PRIOR_RECORD_REPLAY'
   assert shadow==v['shadow'],'PRIOR_CHOICE_REPLAY'
   assert shadow['BASE'] is None and shadow['HISTORY'] is None,'PRIOR_ZERO_SELECTION'
   receipts.append(dict(seed=seed,side=side,source=str(p),sha256=sha(p),records=len(records),matched=True,shadow=shadow))
 return dict(status='MATCHED',visits=receipts,scope='Numerical replay of saved one-step queries/reasons/zero choices; no historical rendering replay')
