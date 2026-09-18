import json,hashlib,os
import numpy as np
from src.multiscene_probe import infer_queries
from src.corrected_probe import _json
from src.corrected_layers import AreaLayers
cfg=json.load(open('out/multiscene_foundation_corrected/config.json'))
K=np.array([[200.,0,199.5],[0,200.,199.5],[0,0,1]]);y,x=np.indices((400,400));cameras={};fields={}
for i,cy in enumerate([0,1,-1,.5]):
 w=np.eye(4);w[1,3]=-cy;cameras[i]=dict(K=K,w2c=w)
 nearest_y=np.where(abs(y-(199.5-200*cy/2))<=abs(y-(199.5-200*cy/4)),199.5-200*cy/2,199.5-200*cy/4)
 t=np.zeros((400,400,2));t[:,:,0]=1
 fields[i]=dict(dt=abs(y-nearest_y),nearest_uv=np.stack([x,nearest_y],axis=2),nearest_tangent=t,domain=np.ones((400,400),bool))
r=infer_queries([dict(query=str(i),view=0,pixel=[190+i,199.5]) for i in range(8)],cameras,fields,None,[[-1,-1.5,1],[1,1.5,5]],.1,cfg)
l=AreaLayers.from_native_arrays(np.array([0,1,2,2,3]),np.array([2,4,6],'f4'),np.array([.9,.5,.6],'f4'),2,2)
rng=np.random.default_rng(42);uv=rng.uniform(-.5,.5,(2300,2));z=rng.uniform(1,7,2300);f,s=l.query(uv,z,.02)
r['native_front']=f;r['native_support']=s
print(hashlib.sha256(json.dumps(_json(r),sort_keys=True,allow_nan=False).encode()).hexdigest())
