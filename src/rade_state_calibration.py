"""Isolated RaDe-GS CUDA geometry baseline on a *frozen vanilla* GS PLY.

RaDe-GS rasterizer: Zhang et al. (TOG 2026), HKUST-SAIL/RaDe-GS@d72f207.
Author poster pipeline: Hao & Mukai (SA 2026). This wrapper is ours, not
an official RaDe-GS training pipeline or a line rendering result.
"""
import numpy as np


def camera_matrices(cam):
    """RaDe-GS column-major matrices for centered-pinhole NeRF Synthetic cameras."""
    H,W=cam.H,cam.W;fx,fy=float(cam.K[0,0]),float(cam.K[1,1])
    assert abs(cam.K[0,2]-W/2)<1e-5 and abs(cam.K[1,2]-H/2)<1e-5
    assert fx>0 and fy>0
    P=np.zeros((4,4),dtype=np.float32)
    P[0,0]=2*fx/W;P[1,1]=2*fy/H
    P[2,2]=100.0/(100.0-.01);P[2,3]=-(100.0*.01)/(100.0-.01)
    P[3,2]=1.
    view=np.asarray(cam.w2c,dtype=np.float32).T.copy()
    return view,(view@P.T).copy()


def render_rade_frozen(g,cam):
    """Official CUDA kernel; raw vanilla parameters; SH0 RGB only; NO RaDe training."""
    import torch
    from diff_gaussian_rasterization import GaussianRasterizationSettings,GaussianRasterizer
    view,full=camera_matrices(cam)
    dev='cuda'
    t=lambda x:torch.as_tensor(np.asarray(x),dtype=torch.float32,device=dev).contiguous()
    xyz=t(g['mu']);sc=t(g['scale']);rot=t(g['quat'])
    rot=rot/rot.norm(dim=1,keepdim=True).clamp(min=1e-12)
    opacity=t(g['opacity']).reshape(-1,1)
    col=t(g['albedo'])
    campt=t(cam.center)
    settings=GaussianRasterizationSettings(image_height=cam.H,image_width=cam.W,
        tanfovx=cam.W/(2*float(cam.K[0,0])),tanfovy=cam.H/(2*float(cam.K[1,1])),
        kernel_size=0.,bg=torch.ones(3,device=dev),scale_modifier=1.,viewmatrix=t(view),
        projmatrix=t(full),sh_degree=0,campos=campt,prefiltered=False,require_depth=True,debug=False)
    with torch.no_grad():
        rgb,radii,depth,mdepth,alpha,normal=GaussianRasterizer(raster_settings=settings)(
            means3D=xyz,means2D=torch.zeros_like(xyz),opacities=opacity,
            colors_precomp=col,scales=sc,rotations=rot)
    result={}
    for name,value in [('rgb',rgb),('alpha',alpha),('expected_depth',depth),
                       ('median_depth',mdepth),('normal',normal),('radii',radii)]:
        x=value.detach().cpu().numpy()
        if name in ('rgb','normal'):x=np.moveaxis(x,0,-1)
        elif name!='radii':x=np.squeeze(x)
        result[name]=x
    return result
