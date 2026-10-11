"""CPU-only candidate; not installed in production CUDA."""
from eigen_probe import legacy_eigh
import numpy as np

def geometry_eigh(matrix):
    a=np.asarray(matrix,np.float32).reshape(-1,3,3)
    scale=np.max(np.abs(a),axis=(1,2))
    if not np.isfinite(a).all() or (scale<=0).any():raise ValueError('invalid covariance')
    values,vectors=legacy_eigh(a/scale[:,None,None])
    return values*scale[:,None],vectors
