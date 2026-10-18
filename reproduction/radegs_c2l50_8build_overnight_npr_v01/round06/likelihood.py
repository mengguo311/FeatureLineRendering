"""Equal-view/equal-class conditional appearance times projected morphology proxy."""
import sys
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
sys.path.append(str(Path(__file__).resolve().parent.parent/'round03'))
from density import fit_density as fit_rgb,lookup as rgb_lookup,predict as rgb_predict

def midx(f):
 f=np.asarray(f)
 if f.ndim!=2 or f.shape[1]!=3 or not np.isfinite(f).all():raise ValueError('finite N x 3 shape features')
 return np.clip(np.floor(f*8).astype(int),0,7)
def lookup(h,f):
 i=midx(f);return h[:,i[:,0],i[:,1],i[:,2]].T

def shuffle(f,e):
 order=np.random.default_rng(1729).permutation(len(f));return f[order].copy(),e[order].copy()

def fit(views,classes):
 rgb=fit_rgb([(x,y) for x,y,f,e in views],classes);hs=[]
 for x,y,f,e in views:
  if not (len(x)==len(y)==len(f)==len(e)):raise ValueError('length')
  idx=midx(f);h=np.zeros((classes,8,8,8))
  for k in range(classes):
   i=idx[(y==k+1)&e]
   if len(i)<8:raise ValueError('fewer than 8 reliable shape seeds in class')
   np.add.at(h[k],tuple(i.T),1);h[k]/=len(i)
  hs.append(h)
 h=np.mean(hs,0)
 for k in range(classes):h[k]=np.maximum(gaussian_filter(h[k],.75,mode='reflect'),1e-12);h[k]/=h[k].sum()
 threshold=[]
 for x,y,f,e in views:
  d=lookup(h,f);threshold.append([np.quantile(d[(y==k+1)&e,k],.05) for k in range(classes)])
 return dict(rgb_hist=rgb['hist'],rgb_threshold=rgb['threshold'],classes=rgb['classes'],shape_hist=h,shape_threshold=np.mean(threshold,0))

def predict(m,x,f,eligible,use_shape=True):
 rgbm=dict(hist=m['rgb_hist'],threshold=m['rgb_threshold'],classes=m['classes']);lab,q,rd=rgb_predict(rgbm,x)
 if not use_shape:return lab,q,rd
 sd=lookup(m['shape_hist'],f);ids=np.flatnonzero(eligible);d=rd[ids]*sd[ids];qq=d/d.sum(1,keepdims=True);order=np.argsort(qq,axis=1);w=order[:,-1];ar=np.arange(len(ids));known=(qq[ar,w]>=.65)&((qq[ar,w]-qq[ar,order[:,-2]])>=.2)&(rd[ids,w]>=m['rgb_threshold'][w])&(sd[ids,w]>=m['shape_threshold'][w]);lab[ids]=np.where(known,w+1,0);q[ids]=qq
 return lab,q,rd
