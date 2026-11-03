"""Atomic auxiliary-reference/port materialization around the frozen leaf exporter."""
import copy
import numpy as np
from frontier_delivery import save_stage as inherited_save_stage

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
 return inherited_save_stage(out,c,dd,ss,oracle,binding)
