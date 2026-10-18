"""Local RGB structure tensor; image-coordinate texture, not semantic geometry."""
import numpy as np
from scipy.ndimage import gaussian_filter

def describe(rgb,scale=None):
 a=np.asarray(rgb,dtype=np.float64)
 if a.ndim!=3 or a.shape[-1]!=3 or not np.isfinite(a).all():raise ValueError('finite HWC RGB required')
 s=min(a.shape[:2])/581 if scale is None else float(scale)
 if s<=0:raise ValueError('positive scale')
 xx=np.zeros(a.shape[:2]);yy=xx.copy();xy=xx.copy()
 for k in range(3):
  gx=s*gaussian_filter(a[...,k],s,order=(0,1),mode='reflect',truncate=3);gy=s*gaussian_filter(a[...,k],s,order=(1,0),mode='reflect',truncate=3);xx+=gx*gx/3;yy+=gy*gy/3;xy+=gx*gy/3
 xx=gaussian_filter(xx,3*s,mode='reflect',truncate=3);yy=gaussian_filter(yy,3*s,mode='reflect',truncate=3);xy=gaussian_filter(xy,3*s,mode='reflect',truncate=3);t=xx+yy;out=np.stack([.5+.5*(xx-yy)/(t+1e-12),.5+xy/(t+1e-12),np.sqrt(t)/(np.sqrt(t)+.05)],axis=-1)
 return np.clip(out,0,1)

def block_shuffle(rgb,block=None):
 a=np.asarray(rgb)
 if a.ndim!=3 or a.shape[-1]!=3:raise ValueError('HWC RGB')
 b=max(1,int(round(33*min(a.shape[:2])/581))) if block is None else int(block)
 if b<1:raise ValueError('positive block')
 out=a.copy();rng=np.random.default_rng(1729)
 for y in range(0,a.shape[0],b):
  for x in range(0,a.shape[1],b):
   tile=a[y:y+b,x:x+b];out[y:y+b,x:x+b]=tile.reshape(-1,3)[rng.permutation(tile.shape[0]*tile.shape[1])].reshape(tile.shape)
 return out
