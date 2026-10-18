"""Bounded image-region hierarchy, never a physical surface reconstruction."""
from env import *
from scipy import ndimage as ndi
from skimage.segmentation import watershed
CFG=json.loads((ROOT/'CONFIG_FREEZE.json').read_text())['stageB']

def merge_labels(lab,pairs,weight,thresholds):
 n=int(lab.max())+1;parent=np.arange(n)
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 order=np.argsort(weight,kind='stable');out=[];k=0
 for t in thresholds:
  while k<len(order) and weight[order[k]]<=t:
   a,b=pairs[order[k]];a,b=root(int(a)),root(int(b));parent[max(a,b)]=min(a,b);k+=1
  mapping=np.array([root(i) for i in range(n)]);v=mapping[lab];unique=np.unique(v);remap=np.zeros(n,dtype=np.int32);nonzero=unique[unique>0];remap[nonzero]=np.arange(1,len(nonzero)+1);out.append(remap[v])
 return np.stack(out)

def hierarchical(rgb,z,alpha,mask,c,arm):
 if not mask.any():raise ValueError('No qualified subject')
 h,w=mask.shape;ids=np.arange(h*w).reshape(h,w);i=np.r_[ids[:,:-1].ravel(),ids[:-1].ravel()];j=np.r_[ids[:,1:].ravel(),ids[1:].ravel()];x=rgb.reshape(-1,3);d=z.ravel();al=alpha.ravel();valid=np.isfinite(d)&(d>.2)&(al>=.5);both=valid[i]&valid[j];cost=np.zeros(len(i))
 if arm!='depth_only':cost=np.linalg.norm(x[i]-x[j],axis=1)/CFG['boundary_RGB_sigma']
 if arm!='rgb_only':
  dz=np.full(len(i),np.inf);dz[both]=abs(d[i[both]]-d[j[both]])*np.sqrt(c['fx']*c['fy'])/((d[i[both]]+d[j[both]])*.5)/CFG['boundary_depth_worldpixels'];cost=np.maximum(cost,dz)
 # Unknown depth is a merge barrier, never a hard background label.
 safe=np.minimum(cost,1e6);elev=np.zeros(h*w);np.maximum.at(elev,i,safe);np.maximum.at(elev,j,safe)
 spacing=max(1,round(CFG['grid_marker_spacing_fraction']*min(h,w)));markers=np.zeros((h,w),np.int32);k=0
 for yy in range(spacing//2,h,spacing):
  for xx in range(spacing//2,w,spacing):
   if mask[yy,xx]:k+=1;markers[yy,xx]=k
 comp,nc=ndi.label(mask)
 for compid in range(1,nc+1):
  yy,xx=np.nonzero(comp==compid)
  if not markers[yy,xx].any():
   q=((yy-yy.mean())**2+(xx-xx.mean())**2).argmin();k+=1;markers[yy[q],xx[q]]=k
 lab=watershed(elev.reshape(h,w),markers=markers,mask=mask,connectivity=1).astype(np.int32);l=lab.ravel();a=l[i];b=l[j];ok=(a>0)&(b>0)&(a!=b);pairs=np.sort(np.c_[a[ok],b[ok]],axis=1);unique,inv=np.unique(pairs,axis=0,return_inverse=True);sums=np.bincount(inv,weights=np.maximum(elev[i[ok]],elev[j[ok]]));ct=np.bincount(inv);weight=sums/np.maximum(ct,1);levels=merge_labels(lab,unique,weight,CFG['merge_levels']);unknown=mask&~valid.reshape(h,w)
 assert (levels[:,mask]>0).all() and (levels[:,~mask]==0).all()
 return dict(fine=lab,markers=markers,levels=levels,pairs=unique,boundary_cost=weight,boundary_pixels=ct,unknown_depth=unknown,elevation=elev.reshape(h,w).astype(np.float32))

def mutual_match(ab,ba,threshold):
 return [(i,j) for i,(j,p) in sorted(ab.items()) if p>=threshold and j in ba and ba[j][0]==i and ba[j][1]>=threshold]
