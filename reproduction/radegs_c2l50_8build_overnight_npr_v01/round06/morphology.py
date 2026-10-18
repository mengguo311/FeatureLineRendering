"""Source-only projected shape descriptor; not a part classifier or 3D thickness."""
import numpy as np
from scipy.ndimage import distance_transform_edt,gaussian_filter

def describe(candidate,unknown):
 m=np.asarray(candidate);u=np.asarray(unknown)
 if m.dtype!=bool or u.dtype!=bool or m.ndim!=2 or m.shape!=u.shape or np.any(m&u) or not m.any():raise ValueError('nonempty disjoint boolean candidate / UNKNOWN required')
 yy,xx=np.nonzero(m);D=float(np.hypot(yy.max()-yy.min()+1,xx.max()-xx.min()+1));radius=.04*D
 def f(a):
  # Explicit padding defines finite image edge; eligible mask separately rejects clipped neighbourhood.
  edt=distance_transform_edt(np.pad(a,1))[1:-1,1:-1]
  return np.stack([np.minimum(edt/radius,1),gaussian_filter(a.astype(float),.01*D,mode='constant',cval=0,truncate=4),gaussian_filter(a.astype(float),radius,mode='constant',cval=0,truncate=4)],axis=-1)
 lower=f(m);upper=f(m|u);spread=np.max(upper-lower,axis=-1);y,x=np.indices(m.shape);edge=np.minimum.reduce([y,x,m.shape[0]-1-y,m.shape[1]-1-x]);eligible=m&(spread<=.1)&(edge>=4*radius)
 return dict(feature=(lower+upper)/2,lower=lower,upper=upper,spread=spread,eligible=eligible,bbox_diagonal=np.asarray(D),frame_unknown=m&(edge<4*radius))
