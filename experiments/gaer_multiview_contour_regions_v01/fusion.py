"""Full accepted-alphaT silhouette participation; original ID domain, no topK."""
import numpy as np
from scipy import ndimage as ndi
def evidence(alpha):
 fg=np.asarray(alpha)>.5
 labels,n=ndi.label(fg,np.ones((3,3)));counts=np.bincount(labels.ravel());keep=counts>=32;keep[0]=False;fg=keep[labels]
 holes=ndi.binary_fill_holes(fg)&~fg
 boundary=fg&~ndi.binary_erosion(fg,np.ones((3,3)))
 filled=fg|holes;outer=filled&~ndi.binary_erosion(filled,np.ones((3,3)))
 hole_boundary=boundary&ndi.binary_dilation(holes,np.ones((3,3)))
 distance=ndi.distance_transform_edt(~boundary)
 maps=np.stack([np.exp(-.5*(distance/1.5)**2),np.exp(-.5*(distance/3.)**2),hole_boundary],-1).astype(np.float32)
 return dict(foreground=fg,holes=holes,boundary=boundary,outer=outer,hole_boundary=hole_boundary,distance=distance.astype(np.float32),maps=maps)
def fuse(masses,rims,views):
 masses=np.asarray(masses,dtype=np.float64);rims=np.asarray(rims,dtype=np.float64)
 if len(set(views))!=len(views) or masses.shape!=rims.shape or masses.shape[0]!=len(views):raise ValueError('unique actual source views required')
 valid=(masses>=.1)&(rims>=.01)
 relative=np.divide(rims,masses,out=np.zeros_like(rims),where=masses>0)
 # Absolute mass regularization prevents almost invisible unit ratios from dominating.
 soft=np.where(valid,relative*np.sqrt(rims/(rims+.05)),0.)
 high_per=valid&(relative>=.35)&(rims>=.05)
 weak_per=valid&(relative>=.12)
 return dict(score=soft.max(0).astype(np.float32),relative=relative.astype(np.float32),perview_score=soft.astype(np.float32),high=high_per.any(0),weak=weak_per.any(0),distinct_views=weak_per.sum(0).astype(np.uint8),high_distinct_views=high_per.sum(0).astype(np.uint8),rim_mass=rims.sum(0).astype(np.float32),visible_views=(masses>=.1).sum(0).astype(np.uint8))
def select_support(model,stats):
 from scipy.spatial import cKDTree
 xyz=model['xyz'];scales=model['scales'];seed=np.flatnonzero(stats['high']);weak=np.flatnonzero(stats['weak']&~stats['high'])
 diag=float(np.linalg.norm(np.ptp(np.quantile(xyz,[.005,.995],axis=0),axis=0)))
 # One local hysteresis hop only; no arbitrary transitive bridge growth.
 if len(seed) and len(weak):
  dist,nn=cKDTree(xyz[seed]).query(xyz[weak],workers=2)
  radius=np.minimum(2*scales.max(1),.025*diag)
  accept=dist<=radius[weak]+radius[seed[nn]]
  accepted=weak[accept];parent=seed[nn[accept]]
 else:accepted=np.empty(0,int);parent=np.empty(0,int);dist=np.empty(0);accept=np.zeros(len(weak),bool)
 selected=np.union1d(seed,accepted)
 return selected,dict(seed_ids=seed,weak_ids=weak,weak_accepted=accept,weak_nearest_distance=dist,accepted_ids=accepted,parent_ids=parent,diag=np.asarray(diag))
