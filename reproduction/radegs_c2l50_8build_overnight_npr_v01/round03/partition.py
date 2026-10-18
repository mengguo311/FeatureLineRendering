import numpy as np
from density import predict

def capped(mask,cap):
 ids=np.flatnonzero(mask);return ids[np.linspace(0,len(ids)-1,min(len(ids),cap),dtype=int)] if len(ids) else ids

def dtu_seeds(ar,cap=2048):
 out=np.zeros(ar['valid'].shape,np.uint8)
 bg=ar['valid']&ar['upright']&ar['peripheral'];fg=ar['valid']&(ar['angle']>=35)&ar['central']
 if (bg&fg).any():raise ValueError('seed definitions overlap')
 out.ravel()[capped(bg,cap)]=1;out.ravel()[capped(fg,cap)]=2
 return out

def shuffle_labels(s):
 out=np.asarray(s).copy();ids=np.flatnonzero(out);out.ravel()[ids]=np.random.default_rng(1729).permutation(out.ravel()[ids]);return out

def select_views(v,arm):
 if arm=='dev_only':return v[:1]
 if arm in ['pooled_rgb','shuffled_labels']:return v
 raise ValueError('unsupported arm')

def infer_image(m,rgb,mask):
 l=np.zeros(mask.shape,np.uint8);q=np.zeros((*mask.shape,len(m['hist'])),np.float64);d=np.zeros_like(q)
 l[mask],q[mask],d[mask]=predict(m,rgb[mask]);return l,mask&(l==0),q,d
