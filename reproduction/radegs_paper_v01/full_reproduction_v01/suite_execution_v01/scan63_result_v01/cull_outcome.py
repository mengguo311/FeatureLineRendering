"""Classify original author mask before any Trimesh mutation; no altered rule."""
import numpy as np
def classify_author_mask(vertex_mask,faces):
 mask=np.asarray(vertex_mask);faces=np.asarray(faces)
 if mask.ndim!=1 or mask.dtype!=np.bool_ or faces.ndim!=2 or faces.shape[1]!=3 or not np.issubdtype(faces.dtype,np.integer):raise ValueError('invalid mask/faces schema')
 if faces.size and (faces.min()<0 or faces.max()>=len(mask)):raise ValueError('invalid original face indices')
 count=int(mask[faces].all(1).sum())
 return {'status':'NONEMPTY_AUTHOR_MASK' if count else 'EMPTY_AFTER_AUTHOR_MASK','kept_vertices':int(mask.sum()),'kept_faces':count,'official_metric_defined':bool(count)}
