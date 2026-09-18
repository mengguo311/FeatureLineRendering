"""Canonical native rasterization and area measurements for the corrected run.

Pixel coordinates denote centers. Stock ndc2Pix(v,S)=((v+1)*S-1)/2.
An area-resize maps centers u to (u+.5)*destination/source-.5.
"""
import numpy as np
from .foundation import native_render


def resize_intrinsics(K, source_hw, destination_hw):
    K=np.asarray(K,dtype=np.float64)
    sy,sx=np.asarray(destination_hw,dtype=float)/source_hw
    if K.shape!=(3,3) or not np.isfinite(K).all() or min(sx,sy)<=0:
        raise ValueError('invalid camera or dimensions')
    A=np.array([[sx,0,(sx-1)/2],[0,sy,(sy-1)/2],[0,0,1.]])
    return A@K


def stock_intrinsics(fovx,fovy,height=800,width=800):
    # Inverse of the exact centered stock NDC-to-pixel mapping, not W/2.
    pixel_from_ndc=np.array([[width/2,0,(width-1)/2],
                             [0,height/2,(height-1)/2],[0,0,1.]])
    perspective=np.diag([1/np.tan(fovx/2),1/np.tan(fovy/2),1.])
    return pixel_from_ndc@perspective


def area_downsample(image):
    """Exact 2x2 area mean, fixed row-major float64 addition order, no clipping."""
    a=np.asarray(image,dtype=np.float64)
    if a.ndim not in (2,3) or a.shape[0]%2 or a.shape[1]%2 or not np.isfinite(a).all():
        raise ValueError('finite, even-sized image required')
    return ((a[0::2,0::2]+a[0::2,1::2])+a[1::2,0::2]+a[1::2,1::2])*.25


def render_measurement(asset,K,w2c,background):
    return area_downsample(native_render(asset,K,w2c,800,800,background)['stock_rgb'])


def stock_reference(asset,w2c,fovx,fovy,background):
    """Independent top-level stock Gaussian renderer, original centered camera."""
    import sys
    from pathlib import Path
    from types import SimpleNamespace
    import torch
    from .foundation import STOCK_SITE
    upstream=Path(__file__).resolve().parents[1]/'out/multiscene_foundation/vendor/gaussian-splatting'
    sys.path[:0]=[str(STOCK_SITE),str(upstream)]
    from gaussian_renderer import render
    from utils.graphics_utils import getProjectionMatrix
    t={k:torch.tensor(v,device='cuda') for k,v in asset.items()}
    pc=SimpleNamespace(get_xyz=t['mu'],get_opacity=t['opacity'],get_scaling=t['scale'],
        get_rotation=torch.nn.functional.normalize(t['quat'],dim=1),get_features=t['sh'],active_sh_degree=3)
    pipe=SimpleNamespace(compute_cov3D_python=False,convert_SHs_python=False,debug=False)
    view=torch.tensor(np.asarray(w2c).T.copy(),dtype=torch.float32,device='cuda')
    P=getProjectionMatrix(.01,100.,fovx,fovy).transpose(0,1).cuda()
    camera=SimpleNamespace(FoVx=fovx,FoVy=fovy,image_height=800,image_width=800,
        world_view_transform=view,full_proj_transform=view@P,
        camera_center=torch.tensor(np.linalg.inv(w2c)[:3,3],dtype=torch.float32,device='cuda'))
    with torch.no_grad():
        rgb=render(camera,pc,pipe,torch.full((3,),float(background),device='cuda'))['render']
    return rgb.permute(1,2,0).cpu().numpy()
