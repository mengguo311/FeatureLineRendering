"""Fixed RGB histogram conditional likelihood; no geometry, graph or target fitting."""
import numpy as np
from scipy.ndimage import gaussian_filter
BINS=16

def indices(x):
 x=np.asarray(x,dtype=np.float64)
 if x.ndim!=2 or x.shape[1]!=3 or not np.isfinite(x).all():raise ValueError('finite RGB N x 3 required')
 return np.clip(np.floor(x*BINS).astype(np.int64),0,BINS-1)
def lookup(hist,x):
 i=indices(x);return hist[:,i[:,0],i[:,1],i[:,2]].T

def fit_density(views,classes):
 if not views:raise ValueError('no views')
 hs=[]
 for x,y in views:
  x=np.asarray(x);y=np.asarray(y);i=indices(x)
  if len(y)!=len(x):raise ValueError('label length')
  h=np.zeros((classes,BINS,BINS,BINS),np.float64)
  for k in range(classes):
   ids=i[y==k+1]
   if not len(ids):raise ValueError('missing seed class')
   np.add.at(h[k],tuple(ids.T),1);h[k]/=len(ids)
  hs.append(h)
 hist=np.mean(hs,axis=0)
 for k in range(classes):
  hist[k]=gaussian_filter(hist[k],.75,mode='reflect');hist[k]=np.maximum(hist[k],1e-12);hist[k]/=hist[k].sum()
 # Per-view quantiles, then arithmetic mean: equal view calibration mass.
 thresholds=[]
 for x,y in views:
  d=lookup(hist,x);thresholds.append([float(np.quantile(d[np.asarray(y)==k+1,k],.05)) for k in range(classes)])
 return dict(hist=hist,threshold=np.mean(thresholds,axis=0),classes=np.asarray(classes,np.int64))

def predict(model,x):
 d=lookup(model['hist'],x);q=d/d.sum(1,keepdims=True);order=np.argsort(q,axis=1);winner=order[:,-1];maxq=q[np.arange(len(q)),winner];margin=maxq-q[np.arange(len(q)),order[:,-2]]
 known=(maxq>=.65)&(margin>=.2)&(d[np.arange(len(q)),winner]>=model['threshold'][winner]);labels=np.where(known,winner+1,0).astype(np.uint8)
 return labels,q,d
