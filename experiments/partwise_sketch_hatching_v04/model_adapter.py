"""Frozen vanilla-GS CPU adapter, vendored from depth_guided_stroke_v01.

No historical run helpers or output roots are imported. Median covariance-plane
z is an exploratory depth estimate, not independently measured geometry.
"""
import runtime
from runtime import sha
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.special import expit
from plyfile import PlyData
import ctypes, ast
from geometry import project, normalize
SH_PATH = Path(__file__).with_name('sh_utils_cpu.py')
_sl = None
LIB_PATH = None
def camera_from_gl(c2w,angle,w,h,key,split):
 C=np.asarray(c2w,float).copy();C[:3,1:3]*=-1;E=np.linalg.inv(C);f=w/(2*np.tan(angle/2))
 return dict(view=key,split=split,width=w,height=h,fx=float(f),fy=float(f),cx=(w-1)/2,cy=(h-1)/2,extrinsic=E.tolist(),original_c2w_gl=np.asarray(c2w).tolist(),coordinate='OpenGL c2w y/z column sign flip -> x-right/y-down/z-forward; integer pixel centers',units='NeRF Synthetic scene units, not meters')

def load_source(ply, expected_sha):
 p=Path(ply);assert sha(p)==expected_sha;d=PlyData.read(p)['vertex'].data;v=lambda names:np.stack([d[n] for n in names],-1).astype(float)
 means=v(['x','y','z']);sc=np.exp(v(['scale_'+str(i) for i in range(3)]));q=v(['rot_'+str(i) for i in range(4)]);q/=np.linalg.norm(q,axis=1,keepdims=True);R=Rotation.from_quat(q[:,[1,2,3,0]]).as_matrix();C=(R*sc[:,None,:]**2)@R.transpose(0,2,1);op=expit(d['opacity'].astype(float));dc=v(['f_dc_'+str(i) for i in range(3)]);rest=v(['f_rest_'+str(i) for i in range(45)]).reshape(-1,3,15);SH=np.concatenate([dc[:,:,None],rest],-1)
 assert np.isfinite(means).all() and np.isfinite(C).all() and np.isfinite(op).all() and np.isfinite(SH).all()
 vals,vec=np.linalg.eigh(C);assert vals.min()>0;good=vals[:,0]>1e-8;iv=np.zeros_like(vals);iv[good]=1/vals[good];iv[~good,0]=1;precision=(vec*iv[:,None,:])@vec.transpose(0,2,1)
 audit=dict(count=len(means),fields=list(d.dtype.names),sh_degree=3,filter3D=False,minimum_cov_eigenvalue=float(vals.min()),raw_opacity_inf=int(np.isinf(d['opacity']).sum()),raw_opacity_nan=int(np.isnan(d['opacity']).sum()),activated_finite=True,eigen_normal_fallback_count=int((~good).sum()),geometry_unchanged=True)
 return dict(means=means,covariance=C,opacity=op,SH=SH,precision=precision,audit=audit)

def source_colors(a,c):
 tree=ast.parse(SH_PATH.read_text());nodes=[n for n in tree.body if isinstance(n,ast.Assign) or isinstance(n,ast.FunctionDef) and n.name=='eval_sh'];scope={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SH_PATH),'exec'),scope)
 E=np.asarray(c['extrinsic']);center=-np.linalg.solve(E[:3,:3],E[:3,3]);return np.maximum(0,scope['eval_sh'](3,a['SH'],normalize(a['means']-center))+.5)

def project_cov(x,C,c,floor_variance=.3):
 E=np.asarray(c['extrinsic']);R=E[:3,:3];p=np.asarray(x)@R.T+E[:3,3];uv,z=project(x,c);J=np.zeros((len(x),2,3))
 with np.errstate(divide='ignore',invalid='ignore'):
  tx=np.clip(p[:,0]/z,-1.3*c['width']/(2*c['fx']),1.3*c['width']/(2*c['fx']));ty=np.clip(p[:,1]/z,-1.3*c['height']/(2*c['fy']),1.3*c['height']/(2*c['fy']));J[:,0,0]=c['fx']/z;J[:,1,1]=c['fy']/z;J[:,0,2]=-c['fx']*tx/z;J[:,1,2]=-c['fy']*ty/z
 A=J@R;return uv,z,A@C@A.transpose(0,2,1)+np.eye(2)*floor_variance

def covariance_plane(p,C,precision=None):
 # C24 computeCov2D lines140-197, NumPy row/column semantics made explicit.
 if precision is None:
  val,vec=np.linalg.eigh(C);good=val[:,0]>1e-8;iv=np.zeros_like(val);iv[good]=1/val[good];iv[~good,0]=1;precision=(vec*iv[:,None,:])@vec.transpose(0,2,1)
 r=p/p[:,2,None];m=np.einsum('nij,nj->ni',precision,r);mn=normalize(m);vb=np.maximum((mn*r).sum(1),1e-7);mn=mn/vb[:,None];u,v=r[:,0],r[:,1];factor=p[:,2]/(1+u*u+v*v)
 return np.stack([(1+v*v)*mn[:,0]-u*v*mn[:,1]-u*mn[:,2],-u*v*mn[:,0]+(1+u*u)*mn[:,1]-v*mn[:,2]],1)*factor[:,None]

def clamped_plane(p,C,c,precision=None):
 q=p.copy();q[:,0]=np.clip(q[:,0]/q[:,2],-1.3*c['width']/(2*c['fx']),1.3*c['width']/(2*c['fx']))*q[:,2];q[:,1]=np.clip(q[:,1]/q[:,2],-1.3*c['height']/(2*c['fy']),1.3*c['height']/(2*c['fy']))*q[:,2]
 return covariance_plane(q,C,precision)

def render_source(a,c):
 global _sl
 if _sl is None:
  _sl=ctypes.CDLL(str(LIB_PATH));_sl.source_ewa.argtypes=[ctypes.c_int]*3+[ctypes.c_void_p]*6+[ctypes.c_double]*2+[ctypes.c_void_p]*5
 uv,z,S=project_cov(a['means'],a['covariance'],c);E=np.asarray(c['extrinsic']);R=E[:3,:3];p=a['means']@R.T+E[:3,3];ok=(z>.2)&np.isfinite(S).all((1,2));prec=a.get('precision');prec=R@prec[ok]@R.T if prec is not None else None
 plane=clamped_plane(p[ok],R@a['covariance'][ok]@R.T,c,prec);col=source_colors(a,c) if 'SH' in a else a['colors'];h,w=c['height'],c['width'];rgb=np.empty((h,w,3));alpha=np.empty((h,w));depth=np.empty((h,w));center=np.empty((h,w));expected=np.empty((h,w));ar=[np.ascontiguousarray(v,np.float64) for v in [uv[ok],z[ok],S[ok],plane,a['opacity'][ok],col[ok]]]
 _sl.source_ewa(int(ok.sum()),h,w,*[v.ctypes.data for v in ar],c['fx'],c['fy'],*[v.ctypes.data for v in [rgb,alpha,depth,center,expected]])
 return {k:v.astype(np.float32) for k,v in dict(rgb=rgb,alpha=alpha,median_camera_z=depth,center_depth_proxy=center,expected_camera_z=expected).items()}
