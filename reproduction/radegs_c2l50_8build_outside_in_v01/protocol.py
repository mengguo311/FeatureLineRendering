from env import *
from scipy import ndimage as ndi
# 0 unknown, 1 comparable-visible, 2 occluded, 3 outside, 4 front-inconsistent

def visibility(uv,z,depth,alpha,c):
 uv=np.asarray(uv);z=np.asarray(z);finite=np.isfinite(uv).all(1)&np.isfinite(z)&(z>.2);xy=np.rint(np.nan_to_num(uv)).astype(int);inside=finite&(xy[:,0]>=0)&(xy[:,0]<c['width'])&(xy[:,1]>=0)&(xy[:,1]<c['height']);r=np.zeros(len(z),np.uint8);r[~inside]=3;ix=np.flatnonzero(inside);d=depth[xy[ix,1],xy[ix,0]];a=alpha[xy[ix,1],xy[ix,0]];ok=np.isfinite(d)&(d>.2)&(a>=.5);tol=np.maximum(.01*d,6*d/np.sqrt(c['fx']*c['fy']));diff=z[ix]-d;r[ix[ok&(abs(diff)<=tol)]]=1;r[ix[ok&(diff>tol)]]=2;r[ix[ok&(diff< -tol)]]=4;return r

def transfer(mask,depth,alpha,c,target_mask,target_depth,target_alpha,tc):
 stride=json.loads((ROOT/'CONFIG_FREEZE.json').read_text())['transfer']['pixel_stride'];yy,xx=np.mgrid[:mask.shape[0]:stride,:mask.shape[1]:stride];valid=mask[yy,xx]&np.isfinite(depth[yy,xx])&(depth[yy,xx]>.2)&(alpha[yy,xx]>=.5);uv=np.c_[xx[valid],yy[valid]];d=depth[uv[:,1],uv[:,0]];X=unproject(uv,d,c);pv,z=projection(X,tc);s=visibility(pv,z,target_depth,target_alpha,tc);hit=np.zeros(len(s),bool);idx=np.flatnonzero(s==1);q=np.rint(pv[idx]).astype(int);target=ndi.binary_dilation(target_mask,iterations=1);hit[idx]=target[q[:,1],q[:,0]]
 r=dict(sample_count=len(s),visible=int((s==1).sum()),occluded=int((s==2).sum()),outside=int((s==3).sum()),front_inconsistent=int((s==4).sum()),unknown=int((s==0).sum()),comparable_fraction=float((s==1).sum()/max(len(s),1)),visible_inside_fraction=float(hit[idx].mean()) if len(idx) else None,semantic_accuracy=False)
 return r,dict(source_uv=uv,world=X,target_uv=pv,target_z=z,state=s,inside_candidate=hit)

def containment(fine,coarse):
 if fine.shape!=coarse.shape:return False
 for k in np.unique(fine):
  if k and len(np.unique(coarse[fine==k]))!=1:return False
 return True

def require_source_ids(ids,groups):
 if (np.asarray(groups)!=0).any():raise ValueError('ink/line parent IDs cannot enter source responsibility')
 if (np.asarray(ids)<0).any():raise ValueError('invalid source index')

def gate(flags):
 if not flags['engineering']:return 'ENGINEERING_INVALID'
 return 'GO' if all(flags.get(k,False) for k in ['nonempty','visual','transfer']) else 'NO_GO'
