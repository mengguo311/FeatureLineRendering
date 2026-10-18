import numpy as np
from coupling import labels

def pack(q,data):
 mask=data['mask'];lab=np.zeros(mask.shape,np.uint8);prob=np.zeros((*mask.shape,q.shape[1]),np.float64);seed=np.zeros(mask.shape,np.uint8);lab[mask]=labels(q);prob[mask]=q;seed[mask]=data['seeds'];u=(mask&(lab==0))|data['subject_unknown']
 return dict(labels=lab,probability=prob,seeds=seed,unknown=u,source_uv=data['uv'],inference_mask=mask)
