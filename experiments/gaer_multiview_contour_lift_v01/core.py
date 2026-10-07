"""Frozen 1D contour geometry. Depths and cross-view identities remain proxies."""
import hashlib
import numpy as np
import cv2

def project(p,c):
 p=np.asarray(p,float).reshape(-1,3);V=np.asarray(c['w2c']);q=p@V[:3,:3].T+V[:3,3];uv=q@np.asarray(c['K']).T
 return uv[:,:2]/uv[:,2,None],q[:,2]

def rays(uv,c):
 uv=np.asarray(uv,float).reshape(-1,2);C=np.linalg.inv(c['w2c']);r=np.c_[uv,np.ones(len(uv))]@np.linalg.inv(c['K']).T;r=r@C[:3,:3].T;r/=np.linalg.norm(r,axis=1)[:,None]
 return np.broadcast_to(C[:3,3],r.shape).copy(),r

def lift(uv,z,c):
 C=np.linalg.inv(c['w2c']);r=np.c_[uv,np.ones(len(uv))]@np.linalg.inv(c['K']).T;r=r/r[:,2,None]*np.asarray(z)[:,None]
 return r@C[:3,:3].T+C[:3,3]

def triangulate(ua,ca,ub,cb,min_angle_deg=3.):
 oa,ra=rays([ua],ca);ob,rb=rays([ub],cb);a=ra[0];b=rb[0]
 if np.degrees(np.arccos(np.clip(abs(a@b),0,1)))<min_angle_deg:return None,'near_parallel'
 M=np.c_[a,-b];t=np.linalg.lstsq(M,ob[0]-oa[0],rcond=None)[0]
 if np.min(t)<=0:return None,'behind_camera'
 q=(oa[0]+t[0]*a+ob[0]+t[1]*b)/2
 return q,'accepted'

def epipolar_error(ua,ca,ub,cb):
 oa,ra=rays([ua],ca);ob,rb=rays([ub],cb)
 # Distance to epipolar line in target image, and its reverse.
 errs=[]
 for o,r,c,u in [(oa[0],ra[0],cb,ub),(ob[0],rb[0],ca,ua)]:
  V=np.asarray(c['w2c']);K=np.asarray(c['K']);a=K@(V[:3,:3]@o+V[:3,3]);b=K@(V[:3,:3]@r);l=np.cross(a,b)
  errs.append(abs(l@np.r_[u,1])/max(np.linalg.norm(l[:2]),1e-20))
 return max(errs)

def contours(alpha,step=2.,min_perimeter=16.):
 fg=(np.asarray(alpha)>=.5).astype(np.uint8)
 cs,h=cv2.findContours(fg,cv2.RETR_TREE,cv2.CHAIN_APPROX_NONE);out=[]
 if h is None:return out
 for i,c in enumerate(cs):
  p=c[:,0];lens=np.linalg.norm(np.roll(p,-1,axis=0)-p,axis=1);arc=np.r_[0,np.cumsum(lens)]
  if arc[-1]<min_perimeter:continue
  ids=np.unique(np.searchsorted(arc[:-1],np.arange(0,arc[-1],step),side='left').clip(0,len(p)-1));p=p[ids]
  if len(p)<4:continue
  depth=0;parent=int(h[0,i,3])
  while parent>=0:depth+=1;parent=int(h[0,parent,3])
  out.append(dict(pixels=p.astype(np.int32),kind='hole' if depth%2 else 'outer',hierarchy_depth=depth,original_contour=i,perimeter=float(arc[-1])))
 return out

def depth_summary(z,w):
 z=np.asarray(z,float);w=np.asarray(w,float);good=np.isfinite(z)&np.isfinite(w)&(z>0)&(w>0);z=z[good];w=w[good]
 if not len(z):return dict(median=float('nan'),q10=float('nan'),q90=float('nan'),mean=float('nan'),mass=0.)
 order=np.argsort(z,kind='stable');z=z[order];w=w[order];cw=np.cumsum(w);mass=cw[-1]
 q=z[np.searchsorted(cw,np.array([.1,.5,.9])*mass).clip(0,len(z)-1)]
 return dict(median=float(q[1]),q10=float(q[0]),q90=float(q[2]),mean=float(z@w/mass),mass=float(mass))

def can_match(pa,pb,ta,tb,tolerance,support_overlap,epi,reproj):
 return bool(np.linalg.norm(np.asarray(pa)-pb)<=tolerance and abs(np.asarray(ta)@tb)>=.92 and support_overlap>=.1 and epi<=1.0 and reproj<=2.0)

def support_overlap(ida,wa,idb,wb):
 _,a,b=np.intersect1d(ida,idb,return_indices=True)
 return float(np.minimum(wa[a]/max(wa.sum(),1e-20),wb[b]/max(wb.sum(),1e-20)).sum())

def fuse_tracks(xyz,edges,clusters,centers,min_sources,views):
 mapping=np.empty(len(xyz),np.int32);counts=[]
 for k,ids in enumerate(clusters):mapping[ids]=k;counts.append(len(set(views[ids].tolist())))
 centers=np.asarray(centers,np.float32);groups={};rejected=[]
 for i,(a,b) in enumerate(edges):
  u,v=int(mapping[a]),int(mapping[b])
  if u==v or min(counts[u],counts[v])<min_sources:rejected.append(i);continue
  key=tuple(sorted((u,v)));groups.setdefault(key,[]).append(i)
 keys=list(groups);used=np.unique(np.asarray(keys,dtype=np.int32)) if keys else np.array([],np.int32);remap=np.full(len(clusters),-1,np.int32);remap[used]=np.arange(len(used))
 return dict(xyz=centers[used],edges=remap[np.array(keys,np.int32).reshape(-1,2)],edge_sources=[groups[k] for k in keys],node_sources=[clusters[k] for k in used],rejected_edges=np.array(rejected,np.int32),cluster_map=mapping,used_clusters=used)

def geometry_hash(xyz,edges,radius):
 h=hashlib.sha256();h.update(np.asarray(xyz,dtype='<f4').tobytes());h.update(np.asarray(edges,dtype='<i4').tobytes());h.update(np.asarray([radius],dtype='<f8').tobytes());return h.hexdigest()
