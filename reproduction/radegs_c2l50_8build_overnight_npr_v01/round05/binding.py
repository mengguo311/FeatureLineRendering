import numpy as np
from policy import withdraw
def apply_seed_policy(data,evidence,training_view,mode):
 out=dict(data);mask=data['mask'];seed=np.zeros(mask.shape,data['seeds'].dtype);seed[mask]=data['seeds']
 if evidence is None:
  if seed.any():raise ValueError('build seed needs frozen other-view evidence')
  out['seeds']=data['seeds'].copy();return out,np.zeros(mask.shape,bool)
 kept,remove=withdraw(seed,evidence['target_uv'],evidence['target_seed_labels'],evidence['predicted'],training_view,data['view'],mode)
 out['seeds']=kept[mask];return out,remove
