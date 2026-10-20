"""Independent projection of prescribed screen coordinates under axial translation."""
import round016_common
import numpy as np

def project_prescribed(points, depth, eye_z):
    p=np.asarray(points,float)
    if p.shape[-1]!=2 or not np.isfinite(p).all() or not np.isfinite([depth,eye_z]).all() or depth<=0 or depth-eye_z<=0:
        raise ValueError('finite 2D coordinates and positive source/camera depth required')
    return 64.+(p-64.)*depth/(depth-eye_z)
