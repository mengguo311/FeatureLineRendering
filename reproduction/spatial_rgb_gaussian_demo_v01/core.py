from pathlib import Path
import ctypes
import numpy as np
from scipy.spatial import cKDTree
TASK=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/spatial_rgb_gaussian_demo_v01')
BUILD=('0000','0024','0048')
def assert_build_views(views):
 if any(v not in BUILD for v in views):raise ValueError('Heldout creation/fusion forbidden')
def valid_depth(z):return np.isfinite(z)&(z>0)
def backproject(uv,z,c):
 uv=np.asarray(uv,dtype=np.float64);z=np.asarray(z,dtype=np.float64);E=np.asarray(c['extrinsic'],dtype=np.float64)
 p=np.stack([(uv[:,0]-(c['width']-1)/2)*z/c['fx'],(uv[:,1]-(c['height']-1)/2)*z/c['fy'],z],-1)
 return (p-E[:3,3])@np.linalg.inv(E[:3,:3]).T

def project(x,c):
 E=np.asarray(c['extrinsic'],dtype=np.float64);p=np.asarray(x)@E[:3,:3].T+E[:3,3];z=p[:,2]
 with np.errstate(divide='ignore',invalid='ignore'):
  uv=np.stack([c['fx']*p[:,0]/z+(c['width']-1)/2,c['fy']*p[:,1]/z+(c['height']-1)/2],-1)
 return uv,z

def normalize(x):return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-30)
def ink_covariance(tangent,normal,pixel,anisotropic):
 if not anisotropic:return np.eye(3)[None]*(.45*np.asarray(pixel)[:,None,None])**2
 t=normalize(tangent);n=normalize(normal);b=normalize(np.cross(n,t));n=normalize(np.cross(t,b));B=np.stack([t,b,n],-1)
 s=np.asarray(pixel)[:,None]*np.array([.70,.35,.18])[None];return (B*s[:,None,:]**2)@B.transpose(0,2,1)

def project_cov(x,C,c,filter_sigma=.12):
 E=np.asarray(c['extrinsic'],dtype=np.float64);R=E[:3,:3];p=x@R.T+E[:3,3];z=p[:,2];uv,_=project(x,c);J=np.zeros((len(x),2,3))
 with np.errstate(divide='ignore',invalid='ignore'):
  J[:,0,0]=c['fx']/z;J[:,1,1]=c['fy']/z;J[:,0,2]=-c['fx']*p[:,0]/z**2;J[:,1,2]=-c['fy']*p[:,1]/z**2
 A=J@R;S=A@C@A.transpose(0,2,1)+np.eye(2)*filter_sigma**2
 return uv,z,S
_lib=None
def render(asset,c,depth=None,alpha=None,filter_sigma=.12):
 global _lib
 if _lib is None:
  _lib=ctypes.CDLL(str(TASK/'build/libewa.so'));_lib.ewa.argtypes=[ctypes.c_int]*3+[ctypes.c_void_p]*7+[ctypes.c_double,ctypes.c_void_p];_lib.ewa.restype=None
 uv,z,S=project_cov(np.asarray(asset['means']),np.asarray(asset['covariance']),c,filter_sigma)
 n=len(z);h=c['height'];w=c['width'];out=np.empty((h,w,3),np.float64)
 vals=[uv,z,S,asset['opacity'],asset.get('colors',np.zeros((n,3))),depth,alpha];arr=[np.ascontiguousarray(a,dtype=np.float64) if a is not None else None for a in vals]
 _lib.ewa(n,h,w,*[a.ctypes.data if a is not None else None for a in arr],float(np.sqrt(c['fx']*c['fy'])),out.ctypes.data)
 return out.astype(np.float32)

# codes: unknown0, compatible1, hidden2, visible_non_line-1, in_front_depth_conflict-2
# compatibility includes actual marked-pixel, depth, distance and tangent checks.
def visibility_class(z,depth,alpha,inside,compatible,tol):
 z=np.asarray(z);d=np.asarray(depth);out=np.zeros(z.shape,np.int8);known=inside&valid_depth(z)&valid_depth(d)&np.isfinite(alpha)&(alpha>=.5)
 out[known&(z>d+tol)]=2;out[known&(z<d-tol)]=-2;visible=known&(abs(z-d)<=tol);out[visible]=-1;out[visible&compatible]=1
 return out

def group_samples(points,views,pixel,tangents,confidence):
 # bounded anchor groups, no transitive union; single sample per view.
 n=len(points)
 if not n:return []
 tree=cKDTree(points);assigned=np.zeros(n,bool);groups=[]
 for i in np.argsort(-np.asarray(confidence),kind='stable'):
  if assigned[i]:continue
  ids=tree.query_ball_point(points[i],1.25*pixel[i]);ids=sorted(ids,key=lambda j:(np.linalg.norm(points[j]-points[i]),j));g=[int(i)];seen={int(views[i])};assigned[i]=True
  for j in ids:
   if assigned[j] or int(views[j]) in seen:continue
   if np.linalg.norm(points[j]-points[i])>1.25*min(pixel[i],pixel[j]):continue
   if any(np.linalg.norm(points[j]-points[k])>2*min(pixel[j],pixel[k]) or abs(tangents[j]@tangents[k])<np.sqrt(.5) for k in g):continue
   g.append(int(j));assigned[j]=True;seen.add(int(views[j]))
  groups.append(g)
 return groups
