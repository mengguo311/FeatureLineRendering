"""Full original native weights, no N x H x W tensor, no Gaussian deletion."""
import numpy as np
import torch
from runtime import *
from binding import backend,scene_io

def raw_forward(module,s,model,colors=None,bg=None):
 empty=torch.empty(0,device='cuda');pre=empty if colors is None else colors.contiguous();sh=model['shs'] if colors is None else empty
 return module._C.rasterize_gaussians(s.bg if bg is None else bg,model['means3D'],pre,model['opacities'],model['scales'],model['rotations'],s.scale_modifier,empty,s.viewmatrix,s.projmatrix,s.tanfovx,s.tanfovy,s.image_height,s.image_width,sh,s.sh_degree if colors is None else 0,s.campos,False,False)

def query_extension():
 from torch.utils.cpp_extension import load
 guard('isolated_query_build')
 m=load(name='capacity_query_C',sources=[str(EXP/'query.cu')],extra_include_paths=[str(SOURCE)],extra_cuda_cflags=['-include','cstdint'],verbose=False)
 atomic_json(ART/'BUILD_QUERY.json',dict(binary=str(m.__file__),binary_sha256=sha(m.__file__),source_sha256=sha(EXP/'query.cu'),pinned_header_sha256=sha(SOURCE/'cuda_rasterizer/rasterizer_impl.h'),production_binary_reused=True))
 return m

class NativeWeights:
 def __init__(self,module,s,model):
  self.module=module;self.s=s;self.model=model;self.n=len(model['means3D']);self.zero=torch.zeros((self.n,3),device='cuda');self.empty=torch.empty(0,device='cuda')
  self.state=raw_forward(module,s,model,self.zero,torch.zeros(3,device='cuda'))
 def A(self,x):
  colors=x[:,None].expand(-1,3).contiguous()
  return raw_forward(self.module,self.s,self.model,colors,torch.zeros(3,device='cuda'))[1][0]
 def AT(self,y):
  R,_,radii,geom,binning,img=self.state;s=self.s;m=self.model
  grad=torch.zeros((3,s.image_height,s.image_width),device='cuda');grad[0]=y
  # All geometric gradients returned by upstream are discarded. Color gradient
  # sums every RGB-accepted original weight; it is independent of colors and BG.
  out=self.module._C.rasterize_gaussians_backward(torch.zeros(3,device='cuda'),m['means3D'],radii,self.zero,m['scales'],m['rotations'],s.scale_modifier,self.empty,s.viewmatrix,s.projmatrix,s.tanfovx,s.tanfovy,grad,self.empty,0,s.campos,geom,R,binning,img,False)
  return out[1][:,0]
 def ink_rgb(self,x):return raw_forward(self.module,self.s,self.model,(1-x)[:,None].expand(-1,3).contiguous(),torch.ones(3,device='cuda'))[1]
 def original(self):return raw_forward(self.module,self.s,self.model)[1]

def rank(b,B):return np.lexsort((np.arange(len(b)),-b))[:B].astype(np.int32)
def binary(n,ids):
 x=torch.zeros(n,device='cuda');x[torch.as_tensor(ids.astype(np.int64),device='cuda')]=1;return x

def dual_bound(Ax,x,ATr,y,constant=0.):
 # f=.5||Ax-y||^2 / m + c; dual q=r/m so q has objective units.
 r=Ax-y;m=r.numel();q=ATr/m
 primal=.5*float(torch.sum(r.double()**2))/m+constant
 dual=(-.5*float(torch.sum(r.double()**2))-float(torch.sum(y.double()*r.double())))/m+float(torch.minimum(q,torch.zeros_like(q)).double().sum())+constant
 # Bound FP32 native atomic uncertainty conservatively, absolute floor included.
 allowance=3e-5*float(q.abs().double().sum())+1e-8
 return primal,dual-allowance,allowance
