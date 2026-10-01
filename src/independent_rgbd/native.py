"""Stock vanilla GS RGB rendering; never a Kinect sensor-depth substitute."""
import numpy as np
from pathlib import Path
from .core import project

class StockRenderer:
 def __init__(self,path,site):
  import sys,torch
  from plyfile import PlyData
  sys.path.insert(0,str(site)); import diff_gaussian_rasterization as dr
  if Path(dr.__file__).resolve().parent != Path(site).resolve()/'diff_gaussian_rasterization':raise RuntimeError('wrong rasterizer')
  self.torch=torch; self.dr=dr
  p=PlyData.read(path)['vertex']
  self.mu=np.stack([p[k] for k in ['x','y','z']],1).astype('float32')
  scale=np.exp(np.stack([p[f'scale_{j}'] for j in range(3)],1)); quat=np.stack([p[f'rot_{j}'] for j in range(4)],1);quat/=np.linalg.norm(quat,axis=1,keepdims=True)
  opa=(1/(1+np.exp(-np.array(p['opacity'],float))))[:,None]
  dc=np.stack([p[f'f_dc_{j}'] for j in range(3)],1)[:,None,:]; rest=np.stack([p[f'f_rest_{j}'] for j in range(45)],1).reshape(-1,3,15).transpose(0,2,1)
  self.arr={k:torch.tensor(v,dtype=torch.float32,device='cuda').contiguous() for k,v in dict(mu=self.mu,scale=scale,quat=quat,opacity=opa,sh=np.concatenate([dc,rest],1)).items()}
 def settings(self,K,c2w,shape):
  torch=self.torch; h,w=shape; w2c=np.linalg.inv(c2w); P=np.zeros((4,4),np.float32); near,far=.01,100.
  P[0,0]=2*K[0,0]/w;P[1,1]=2*K[1,1]/h;P[0,2]=(2*K[0,2]+1)/w-1;P[1,2]=(2*K[1,2]+1)/h-1;P[2,2]=far/(far-near);P[2,3]=-far*near/(far-near);P[3,2]=1
  view=torch.tensor(w2c.T.copy(),dtype=torch.float32,device='cuda');proj=view@torch.tensor(P.T.copy(),device='cuda');center=torch.tensor(c2w[:3,3].copy(),dtype=torch.float32,device='cuda')
  return self.dr.GaussianRasterizationSettings(image_height=h,image_width=w,tanfovx=float(w/(2*K[0,0])),tanfovy=float(h/(2*K[1,1])),bg=torch.zeros(3,device='cuda'),scale_modifier=1.,viewmatrix=view,projmatrix=proj,sh_degree=3,campos=center,prefiltered=False,debug=False)
 def render(self,K,c2w,shape,calibrate=False):
  t=self.torch; a=self.arr; s=self.settings(K,c2w,shape)
  with t.no_grad():
   rgb,radii=self.dr.GaussianRasterizer(s)(means3D=a['mu'],means2D=t.zeros_like(a['mu']),shs=a['sh'],opacities=a['opacity'],scales=a['scale'],rotations=a['quat'])
   rgb=rgb.permute(1,2,0).cpu().numpy()
   if not calibrate:return rgb
   empty=t.empty(0,device='cuda')
   result=self.dr._C.rasterize_gaussians(s.bg,a['mu'],empty,a['opacity'],a['scale'],a['quat'],1.,empty,s.viewmatrix,s.projmatrix,s.tanfovx,s.tanfovy,*shape,a['sh'],3,s.campos,False,False)
  direct=result[1].permute(1,2,0).cpu().numpy(); raw=result[3].cpu().numpy(); n=len(self.mu);off=0
  for dtype,count in [('f4',n),('u1',3*n),('i4',n)]:off=(off+127)&~127;off+=np.dtype(dtype).itemsize*count
  off=(off+127)&~127;uv_native=np.frombuffer(raw,dtype='f4',count=n*2,offset=off).reshape(n,2)
  uv,z=project(self.mu,K,c2w);active=(radii.cpu().numpy()>0)&np.isfinite(uv).all(1)
  diff=np.linalg.norm(uv[active]-uv_native[active],axis=1)
  return rgb,dict(wrapper_direct_max_abs=float(abs(rgb-direct).max()),native_projection_max_pixels=float(diff.max()) if len(diff) else None,active_centres=int(active.sum()),passed=bool(abs(rgb-direct).max()<=1/255 and len(diff)>0 and diff.max()<.01))
