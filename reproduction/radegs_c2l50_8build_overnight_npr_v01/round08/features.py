"""Algebraic scalar-intensity quotient; no albedo or semantic claim."""
import numpy as np
ARMS=['raw_rgb','rgb_floor','chromaticity','shuffled_chromaticity']
def transform(x,arm):
 x=np.asarray(x,dtype=np.float64)
 if arm not in ARMS or x.ndim!=2 or x.shape[1]!=3:raise ValueError('known arm and N x 3 required')
 if arm=='raw_rgb':
  if not np.isfinite(x).all():raise ValueError('raw baseline requires finite input')
  return x.copy(),np.ones(len(x),bool)
 e=np.isfinite(x).all(1)&(x>=0).all(1)&(np.max(x,axis=1)>=.02);out=np.zeros_like(x)
 if arm=='rgb_floor':out[e]=x[e]
 else:out[e]=x[e]/x[e].sum(1,keepdims=True)
 return out,e
