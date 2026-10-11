import numpy as np
def paired_thumbnail(first,second):
    return np.ma.concatenate([first,second],axis=1)
def valid_depth(depth, alpha):
    if depth.shape != alpha.shape:raise ValueError('depth/alpha shape mismatch')
    return np.isfinite(depth) & (depth>0) & np.isfinite(alpha) & (alpha>=.5)
def compare_cameras(first, second):
    if len(first)!=len(second):raise ValueError('camera count mismatch')
    for a,b in zip(first,second):
        for key in ('view','width','height','fx','fy','extrinsic'):
            if a[key]!=b[key]:raise ValueError('changed camera '+key)
