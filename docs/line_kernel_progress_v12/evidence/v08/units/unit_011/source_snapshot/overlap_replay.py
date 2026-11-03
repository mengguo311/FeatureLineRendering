"""Exact saved observation/initial-visit control replay; no historical writes."""
from runtime_io import *
from frontier_core import initial,endpoint_index,choices
from frontier_loader import local_validator
from observation_core import ObservationOracle
from observation_relay import observed_candidates

def replay(c,raw,d,newbank,guard):
 old=Path(c['prior_observation_bank']);verify_checkpoint(old,c['prior_config_sha256']);receipts=[]
 for name in ['OBSERVED_CARRIERS.npz','PORT_EVIDENCE.npz']:
  a=np.load(old/name,allow_pickle=False);b=np.load(Path(newbank)/name,allow_pickle=False);assert a.files==b.files
  for key in a.files:np.testing.assert_array_equal(a[key],b[key],err_msg='OBSERVATION_REPLAY '+name+':'+key)
  receipts.append(dict(file=name,matched=True,sha256=sha(old/name)))
 assert json.loads((old/'LEAF_CHECKS.json').read_text())==json.loads((Path(newbank)/'LEAF_CHECKS.json').read_text())
 seeds=sorted(x[0] for x in c['seeds']);state=initial(seeds,d['next_version']);index=endpoint_index(d['leaves']);oldindex=endpoint_index(raw['leaves']);oracle=ObservationOracle(d['leaves'],d['ports'],d['representatives']['x']/d['p'],d['representatives']['t'],local_validator(d,d['p']),guard)
 paths=sorted(Path(c['prior_observed_visits_root']).glob('*.json'));assert len(paths)==8;visits=[];contexts={sid:{sid} for sid in seeds}
 for path in paths:
  guard();oldv=json.loads(path.read_text());sid=oldv['seed'];side=oldv['side'];assert oldv['version']==state['versions'][sid]
  lib=observed_candidates(d,state,sid,side,index,oracle,guard,256,3,oldindex)
  for key,value in lib.items():assert json.loads(json.dumps(value,allow_nan=False))==oldv[key],'OBSERVED_VISIT_REPLAY '+key
  choice=choices(lib['records']);assert choice==oldv['shadow'] and choice['BASE'] is None and choice['HISTORY'] is None
  for query in lib['queries']:
   contexts[sid].update(x[0] for x in query['neighbors']);contexts[sid].update(x[0] for x in query.get('original_endpoint_neighbors',[]))
  visits.append(dict(seed=sid,side=side,matched=True,sha256=sha(path)))
 return dict(status='MATCHED',bank=receipts,visits=visits),contexts
