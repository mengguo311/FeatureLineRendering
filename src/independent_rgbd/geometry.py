"""F sensor-only point fusion, visibility-filtered world-space depth contours."""
import numpy as np
import cv2
from .core import project,unproject,visibility

def valid_depth(d):
 return cv2.erode(((d>=.3)&(d<=4)).astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)

def depth_edges(d):
 valid=valid_depth(d); e=np.zeros(d.shape,bool)
 for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
  neighbour=np.roll(d,(dy,dx),(0,1)); e|=(neighbour-d>.06)
 e &= valid; e[:2]=False;e[-2:]=False;e[:,:2]=False;e[:,-2:]=False
 return e

def simplify(p,eps=.005):
 if len(p)<3:return p
 a,b=p[0],p[-1]; ab=b-a; l=np.dot(ab,ab)
 t=np.clip((p-a)@ab/max(l,1e-20),0,1); dist=np.linalg.norm(p-(a+t[:,None]*ab),axis=1); j=int(np.argmax(dist))
 if dist[j]<=eps:return p[[0,-1]]
 return np.concatenate([simplify(p[:j+1],eps)[:-1],simplify(p[j:],eps)])

def support(points,depths,poses,K):
 consistent=np.zeros(len(points),int); known=np.zeros(len(points),int); contradiction=np.zeros(len(points),int)
 for d,c in zip(depths,poses):
  uv,z=project(points,K,c); lab=visibility(uv,z,d)
  consistent+=lab=='consistent'; known+=lab!='unknown'; contradiction+=lab=='contradiction'
 return consistent,known,contradiction

def fused_cloud(depths,poses,K):
 points=[]; frames=[]
 for i,(d,c) in enumerate(zip(depths,poses)):
  yy,xx=np.mgrid[0:d.shape[0]:4,0:d.shape[1]:4]; ok=valid_depth(d)[yy,xx]; uv=np.c_[xx[ok],yy[ok]]
  p=unproject(uv,d[yy[ok],xx[ok]],K,c); points.append(p);frames.append(np.full(len(p),i))
 p=np.concatenate(points); fi=np.concatenate(frames); key=np.rint(p/.01).astype('int32'); _,inv=np.unique(key,axis=0,return_inverse=True)
 count=np.bincount(inv); centre=np.stack([np.bincount(inv,weights=p[:,j])/count for j in range(3)],1)
 pair=np.unique(np.c_[inv,fi],axis=0); views=np.bincount(pair[:,0],minlength=len(count))
 return centre[views>=3],dict(input_points=len(p),voxels=len(count),retained_voxels=int((views>=3).sum()),criterion='>=3 distinct F views per .01 m voxel')

def extract_curves(depths,poses,K,frame_ids):
 candidates=[]; candidate_length=0.; rejected_short=0
 for fi,d in enumerate(depths):
  contours,_=cv2.findContours(depth_edges(d).astype('uint8'),cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)
  for ci,contour in enumerate(contours):
   uv=contour[:,0,:][::2]
   if len(uv)<5:rejected_short+=1;continue
   p=unproject(uv,d[uv[:,1],uv[:,0]],K,poses[fi]); length=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
   if length<.05:rejected_short+=1;continue
   candidate_length+=length; candidates.append((fi,ci,p,length))
 curves=[]; total_surviving_length=0.; survival=[]
 for fi,ci,p,length in candidates:
  cons,known,bad=support(p,depths,poses,K); ok=(cons>=3)&(bad<=.2*np.maximum(known,1)); frac=float(ok.mean())
  survival.append(dict(frame=frame_ids[fi],contour=ci,points=len(p),fraction=frac,length=length))
  if frac<.6:continue
  # Break at rejected vertices, including the cyclic-contour endpoints; no gap bridges.
  groups=np.split(np.flatnonzero(ok),np.flatnonzero(np.diff(np.flatnonzero(ok))>1)+1)
  for si,g in enumerate(groups):
   if len(g)<5:continue
   q=p[g]; l=float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum())
   if l<.05:continue
   q=simplify(q)
   if len(q)<5:continue
   total_surviving_length+=l
   if len(curves)<500:
    curves.append(dict(id=f'{frame_ids[fi]}_contour_{ci:04d}_part_{si:03d}',points=q.tolist(),width=.007,edges=[[j,j+1] for j in range(len(q)-1)],source_frame=frame_ids[fi],F_support_fraction=frac))
 return dict(schema=1,coordinate_frame='TUM mocap world, metres',curves=curves),dict(proposed_contours=len(candidates),rejected_short=rejected_short,proposed_length=candidate_length,surviving_length=total_surviving_length,surviving_length_ratio=total_surviving_length/max(candidate_length,1e-10),retained_curves=len(curves),curve_cap=500,visibility_survival=survival)

def cloud_zbuffer(points,K,c2w,shape):
 uv,z=project(points,K,c2w); finite=np.isfinite(uv).all(1)&(z>0); ij=np.zeros((len(z),2),int);ij[finite]=np.rint(uv[finite]).astype(int)
 ok=finite&(ij[:,0]>=0)&(ij[:,0]<shape[1])&(ij[:,1]>=0)&(ij[:,1]<shape[0]);flat=np.full(shape[0]*shape[1],np.inf,np.float32)
 np.minimum.at(flat,ij[ok,1]*shape[1]+ij[ok,0],z[ok]); d=flat.reshape(shape)
 d=cv2.erode(d,np.ones((5,5),np.uint8)); d[~np.isfinite(d)]=0
 return d
