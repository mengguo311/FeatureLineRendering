"""Read-only import of tested native ops through an isolated, stage-local shim."""
import importlib.util,sys,types,json
import runtime as rt

def read_api(name,path,shim,bindings=None):
 replacements={'runtime':shim};replacements.update(bindings or {});saved={k:sys.modules.get(k) for k in replacements}
 try:
  sys.modules.update(replacements);spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 finally:
  for k,v in saved.items():
   if v is None:sys.modules.pop(k,None)
   else:sys.modules[k]=v
shim=types.ModuleType('runtime');shim.__dict__.update(rt.__dict__);shim.OUT=rt.ATTR/'out/gaer_attribution_buffer_v01';shim.SOURCE=rt.NATIVE/'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization';shim.DATA_FREEZE=rt.ATTR/'artifacts/edge_control_lego_chair_v1/DATA_FREEZE.json'
native=read_api('contours_pinned_native',rt.ATTR/'experiments/gaer_attribution_buffer_v01/src/native.py',shim)
scene_io=read_api('contours_pinned_scene_io',rt.ATTR/'experiments/gaer_attribution_buffer_v01/src/scene_io.py',shim)
def backend():return native.load_backend('patched')
bs=types.ModuleType('binding');bs.backend=backend;bs.scene_io=scene_io
stage=types.ModuleType('runtime');stage.__dict__.update(rt.__dict__)
ops=read_api('contours_capacity_ops',rt.ROOT/'experiments/gaer_attribution_capacity_v02/operators.py',stage,{'binding':bs})
NativeWeights=ops.NativeWeights;raw_forward=ops.raw_forward

def load_existing(name):
 record=json.loads((rt.CAP/'artifacts/gaer_attribution_capacity_v02'/('BUILD_'+name.upper()+'.json')).read_text());p=record['binary']
 if rt.sha(p)!=record['binary_sha256']:raise RuntimeError('pinned binary mismatch')
 binary_name='capacity_'+name.lower()+'_C'
 if binary_name in sys.modules:return sys.modules[binary_name]
 import torch
 spec=importlib.util.spec_from_file_location(binary_name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);sys.modules[binary_name]=m;return m

def query_extension():return load_existing('QUERY')
def shape_extension():return types.SimpleNamespace(_C=load_existing('SHAPE'))

class ShapeWeights(NativeWeights):
 def __init__(self,module,s,model,cov):
  import torch
  self.module=module;self.s=s;self.model=dict(model,scales=torch.empty(0,device='cuda'),rotations=torch.empty(0,device='cuda'));self.cov=cov.contiguous();self.n=len(model['means3D']);self.zero=torch.zeros((self.n,3),device='cuda');self.empty=torch.empty(0,device='cuda');self.state=self.forward(self.zero,torch.zeros(3,device='cuda'))
 def forward(self,colors,bg):
  s=self.s;m=self.model
  return self.module._C.rasterize_gaussians(bg,m['means3D'],colors.contiguous(),m['opacities'],m['scales'],m['rotations'],s.scale_modifier,self.cov,s.viewmatrix,s.projmatrix,s.tanfovx,s.tanfovy,s.image_height,s.image_width,self.empty,0,s.campos,False,False)
 def A(self,x):
  import torch
  return self.forward(x[:,None].expand(-1,3).contiguous(),torch.zeros(3,device='cuda'))[1][0]
 def ink_rgb(self,x):
  import torch
  return self.forward((1-x)[:,None].expand(-1,3).contiguous(),torch.ones(3,device='cuda'))[1]
 def AT(self,y):
  import torch
  R,_,radii,geom,binning,img=self.state;s=self.s;m=self.model;grad=torch.zeros((3,s.image_height,s.image_width),device='cuda');grad[0]=y
  result=self.module._C.rasterize_gaussians_backward(torch.zeros(3,device='cuda'),m['means3D'],radii,self.zero,m['scales'],m['rotations'],s.scale_modifier,self.cov,s.viewmatrix,s.projmatrix,s.tanfovx,s.tanfovy,grad,self.empty,0,s.campos,geom,R,binning,img,False)
  return result[1][:,0]
