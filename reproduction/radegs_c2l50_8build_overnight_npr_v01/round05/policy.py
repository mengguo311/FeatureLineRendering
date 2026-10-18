import numpy as np
def withdraw(seed_image,target_uv,target_labels,predicted,training_view,target_view,mode,rng_seed=1729):
 s=np.asarray(seed_image);uv=np.asarray(target_uv);y=np.asarray(target_labels);p=np.asarray(predicted)
 if training_view==target_view:raise ValueError('self-view training forbidden for contradiction evidence')
 if s.ndim!=2 or uv.shape!=(len(y),2) or p.shape!=y.shape:raise ValueError('shape')
 if len(np.unique(uv,axis=0))!=len(uv):raise ValueError('duplicate observation')
 if (uv<0).any() or (uv[:,0]>=s.shape[1]).any() or (uv[:,1]>=s.shape[0]).any():raise ValueError('out of image')
 if len(y)!=np.count_nonzero(s) or (y<=0).any() or not np.array_equal(s[uv[:,1],uv[:,0]],y):raise ValueError('not exact original seed coverage/identity')
 if (p<0).any() or (p>s.max()).any():raise ValueError('invalid class')
 conflict=(p>0)&(p!=y)
 if mode=='withdraw_conflict':chosen=conflict
 elif mode=='withdraw_random':
  rng=np.random.default_rng(rng_seed);chosen=np.zeros(len(y),bool)
  for k in np.unique(y):
   ids=np.flatnonzero(y==k);ids=ids[np.argsort(uv[ids,1]*s.shape[1]+uv[ids,0])];n=int(((y==k)&conflict).sum());chosen[rng.choice(ids,n,replace=False)]=True
 else:raise ValueError('unsupported seed policy')
 remove=np.zeros(s.shape,bool);remove[uv[chosen,1],uv[chosen,0]]=True;out=s.copy();out[remove]=0
 return out,remove
