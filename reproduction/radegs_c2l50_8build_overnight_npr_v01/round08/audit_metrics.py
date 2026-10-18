import numpy as np
def compare(a,b,m):
 a=np.asarray(a)[m];b=np.asarray(b)[m]
 return dict(masked_pixels=len(a),known_to_unknown=int(((a>0)&(b==0)).sum()),unknown_to_known=int(((a==0)&(b>0)).sum()),known_changed=int(((a>0)&(b>0)&(a!=b)).sum()),unchanged=int((a==b).sum()))
def overlap(h):
 h=np.asarray(h).reshape(len(h),-1)
 return np.array([[np.minimum(a,b).sum() for b in h] for a in h])
