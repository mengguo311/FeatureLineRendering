"""Normalized finite-support RGB texture; alpha is coverage, not a semantic mask."""
import numpy as np
from scipy.ndimage import gaussian_filter

def describe_supported(rgb,weight,scale=None):
 a=np.asarray(rgb,np.float64);w=np.asarray(weight,np.float64)
 if a.ndim!=3 or a.shape[-1]!=3 or w.shape!=a.shape[:2] or not np.isfinite(a).all() or not np.isfinite(w).all() or np.any((w<0)|(w>1)):raise ValueError('finite HWC RGB and matching [0,1] weights required')
 s=min(w.shape)/581 if scale is None else float(scale)
 if s<=0:raise ValueError('positive scale')
 def G(x,sigma,order=0):return gaussian_filter(x,sigma,order=order,mode='reflect',truncate=3)
 D=G(w,s);Dx=G(w,s,(0,1));Dy=G(w,s,(1,0));valid=D>1e-6;safe=np.where(valid,D,1)
 xx=np.zeros(w.shape);xy=xx.copy();yy=xx.copy()
 for k in range(3):
  N=G(w*a[...,k],s);gx=s*(G(w*a[...,k],s,(0,1))*D-N*Dx)/safe**2;gy=s*(G(w*a[...,k],s,(1,0))*D-N*Dy)/safe**2
  gx=np.where(valid,gx,0);gy=np.where(valid,gy,0);xx+=gx*gx/3;xy+=gx*gy/3;yy+=gy*gy/3
 W=G(w,3*s);valid&=W>1e-6;den=np.where(W>1e-6,W,1);xx=G(w*xx,3*s)/den;xy=G(w*xy,3*s)/den;yy=G(w*yy,3*s)/den;t=xx+yy
 f=np.stack([.5+.5*(xx-yy)/(t+1e-12),.5+xy/(t+1e-12),np.sqrt(t)/(np.sqrt(t)+.05)],axis=-1);f=np.clip(f,0,1);f[~valid]=[.5,.5,0]
 return f,valid,np.stack([D,W],axis=-1)

def shift_support(weight,scale=None):
 w=np.asarray(weight)
 if w.ndim!=2:raise ValueError('2D weights')
 s=min(w.shape)/581 if scale is None else float(scale)
 return np.roll(w,max(1,int(round(3*s))),axis=1).copy()
