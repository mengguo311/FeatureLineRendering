"""Stock renderer diagnostics via same native traversal (no dense N*H*W tensors).

Object colours are unit one-hot features. Colour Jacobian of a pixel sum gives
exact sum(alpha*T) per UID. There is no top-k approximation or opacity reweight.
Depth is an alpha-weighted centre proxy, explicitly not geometric ground truth.
"""
import json
import math
from types import SimpleNamespace
import numpy as np
import torch
from native import install_stock
install_stock()
from gaussian_renderer import render as official_render
from scene.gaussian_model import GaussianModel
from utils.graphics_utils import getProjectionMatrix
from runtime import OUT, ART, atomic_json, resource_guard
from edge_profiles import linear_to_srgb

PIPE=SimpleNamespace(compute_cov3D_python=False,convert_SHs_python=False,debug=False)

def make_camera(frame,resolution=512,fov=.8):
    c2w=np.asarray(frame['transform_matrix']).copy();c2w[:3,1:3]*=-1
    w2c=np.linalg.inv(c2w)
    view=torch.tensor(w2c.T,dtype=torch.float32,device='cuda')
    proj=getProjectionMatrix(.01,100.,fov,fov).T.cuda()
    return SimpleNamespace(image_height=resolution,image_width=resolution,FoVx=fov,FoVy=fov,
        world_view_transform=view,full_proj_transform=view@proj,
        camera_center=torch.tensor(c2w[:3,3],dtype=torch.float32,device='cuda'))

def load_checkpoint(path):
    cap,step=torch.load(path,map_location='cuda')
    m=GaussianModel(0)
    for name,value in zip(('_xyz','_features_dc','_features_rest','_scaling','_rotation','_opacity'),cap[1:7]):
        setattr(m,name,torch.nn.Parameter(value.detach().clone(),requires_grad=False))
    m.active_sh_degree=cap[0];m.max_radii2D=cap[7].clone();m.spatial_lr_scale=cap[-1]
    return m

def rgb(m,camera,colors=None):
    return official_render(camera,m,PIPE,torch.zeros(3,device='cuda'),override_color=colors)['render']

def contribution(m,camera,labels,band=None):
    labels=torch.as_tensor(labels,device='cuda')
    feat=torch.zeros((len(labels),3),device='cuda')
    for ch,k in enumerate((1,2,-1)):feat[:,ch]=(labels==k).float()
    # Background/other labels must remain represented in accumulated alpha.
    feat[:,2]=((labels!=1)&(labels!=2)).float()
    with torch.no_grad():
        objects=rgb(m,camera,feat)
        alpha=objects.sum(0)
        z=torch.cat([m.get_xyz,torch.ones_like(m.get_xyz[:,:1])],dim=1)@camera.world_view_transform
        depth_feature=z[:,2:3].expand(-1,3).contiguous()
        depth=rgb(m,camera,depth_feature)[0]/alpha.clamp_min(1e-8)
    # Colour derivative never changes geometry, labels or original SH values.
    c=torch.zeros((len(labels),3),device='cuda',requires_grad=True)
    image=rgb(m,camera,c)
    total=torch.autograd.grad(image[0].sum(),c,retain_graph=band is not None)[0][:,0]
    mass=total if band is None else torch.autograd.grad((image[0]*band).sum(),c)[0][:,0]
    return {'objects':objects.detach(),'alpha':alpha.detach(),'depth_center_proxy':depth.detach(),
            'depth_reliable':False,'band_mass':mass.detach(),'total_mass':total.detach(),
            'top_k':None,'truncated_mass':0.0}

def support(m,camera,pixels):
    c=torch.zeros((len(m.get_xyz),3),device='cuda',requires_grad=True)
    image=rgb(m,camera,c)
    return torch.autograd.grad((image[0]*pixels).sum(),c)[0][:,0].detach()

def small_model(xyz,opacity,colors,scale=.12):
    m=GaussianModel(0);N=len(xyz)
    m._xyz=torch.nn.Parameter(torch.tensor(xyz,dtype=torch.float32,device='cuda'))
    m._scaling=torch.nn.Parameter(torch.full((N,3),math.log(scale),device='cuda'))
    m._rotation=torch.nn.Parameter(torch.tensor([[1.,0,0,0]]*N,device='cuda'))
    p=torch.tensor(opacity,dtype=torch.float32,device='cuda')[:,None]
    m._opacity=torch.nn.Parameter(torch.logit(p))
    m._features_dc=torch.nn.Parameter((torch.tensor(colors,dtype=torch.float32,device='cuda')-.5)[:,None,:]/.28209479177387814)
    m._features_rest=torch.nn.Parameter(torch.empty((N,0,3),device='cuda'))
    return m

