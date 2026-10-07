import numpy as np
from scipy import ndimage as ndi
import cv2
def measure(mask,e):
 mask=np.asarray(mask,bool);fg=e['foreground'];edge=e['boundary'];d=ndi.distance_transform_edt(~mask);ed=e['distance'];holes=e['holes']
 contours,_=cv2.findContours(edge.astype(np.uint8),cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)
 gaps=[]
 for c in contours:
  xy=c[:,0];bad=d[xy[:,1],xy[:,0]]>3
  if bad.all():gaps.append(int(len(bad)));continue
  seq=np.r_[bad,bad];run=0;best=0
  for b in seq:run=run+1 if b else 0;best=max(best,run)
  gaps.append(min(best,len(bad)))
 hull=cv2.convexHull(np.argwhere(fg)[:,::-1].astype(np.int32));hm=np.zeros_like(fg,np.uint8);cv2.fillConvexPoly(hm,hull,1);negative=hm.astype(bool)&~fg
 ink=max(int(mask.sum()),1);labels,n=ndi.label(mask);counts=np.bincount(labels.ravel())[1:];inside=ndi.distance_transform_edt(mask)
 return dict(coverage3=float((d[edge]<=3).mean()) if edge.any() else 0.,boundary_distance_p95=float(np.quantile(d[edge],.95)) if edge.any() else 0.,longest_gap_px=max(gaps,default=0),ink_pixels=int(mask.sum()),ink_over_foreground=float(mask.sum()/max(fg.sum(),1)),background_far_pixels=int((mask&~fg&(ed>3)).sum()),background_far_fraction=float((mask&~fg&(ed>3)).sum()/ink),deep_interior_pixels=int((mask&fg&(ed>8)).sum()),deep_interior_fraction=float((mask&fg&(ed>8)).sum()/ink),hole_pixels=int(holes.sum()),hole_fill_fraction=float((mask&holes).sum()/max(holes.sum(),1)),negative_space_fill_fraction=float((mask&negative).sum()/max(negative.sum(),1)),ink_components=int(n),largest_ink_component_fraction=float(counts.max()/ink) if len(counts) else 0.,artifact_diameter_p95_px=float(2*np.quantile(inside[mask],.95)) if mask.any() else 0.)
def objective(m):
 return m['coverage3']-.45*m['background_far_fraction']-.30*m['deep_interior_fraction']-.40*m['negative_space_fill_fraction']-.08*m['ink_over_foreground']
