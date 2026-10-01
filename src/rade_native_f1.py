"""Independent Hao–Mukai-compatible fields from one patched RaDe-GS forward pass.
RaDe-GS base: Zhang et al.; poster equations: Weiren Hao & Tomohiko Mukai.
Frozen vanilla PLY SH0, not either author's official implementation/trained model.
"""
import numpy as np
from src.rade_state_calibration import camera_matrices


def render_native_f1(g, cam):
    import torch
    from diff_gaussian_rasterization import _C
    view, full = camera_matrices(cam)
    t = lambda x: torch.as_tensor(np.asarray(x), dtype=torch.float32, device='cuda').contiguous()
    xyz,sc,rot=t(g['mu']),t(g['scale']),t(g['quat'])
    rot=rot/rot.norm(dim=1,keepdim=True).clamp(min=1e-12)
    h,w=cam.H,cam.W
    ids=torch.full((h,w,4),-1,device='cuda',dtype=torch.int32)
    weight=torch.zeros((h,w,4),device='cuda')
    depth=torch.zeros_like(weight)
    normal=torch.zeros((h,w,4,3),device='cuda')
    moment2=torch.zeros((h,w),device='cuda')
    normal_len=torch.zeros_like(moment2)
    empty=torch.empty(0,device='cuda')
    with torch.no_grad():
        _,rgb,alpha,nrm,dep,_,radii,*_ = _C.rasterize_gaussians(
            torch.ones(3,device='cuda'),xyz,t(g['albedo']),t(g['opacity']).reshape(-1,1),
            sc,rot,1.,empty,t(view),t(full),
            w/(2*float(cam.K[0,0])),h/(2*float(cam.K[1,1])),0.,h,w,
            empty,0,t(cam.center),False,True,False,
            ids,weight,depth,normal,moment2,normal_len)
    numpy=lambda x:x.detach().cpu().numpy()
    return dict(rgb=np.moveaxis(numpy(rgb),0,-1),alpha=numpy(alpha[0]),
                depth=numpy(dep[0]),normal=np.moveaxis(numpy(nrm),0,-1),
                radii=numpy(radii),topk_id=numpy(ids),topk_w=numpy(weight),
                topk_depth=numpy(depth),topk_normal=numpy(normal),
                moment2=numpy(moment2),normal_len=numpy(normal_len))


def build_source_state(r):
    """Normalize top-4 visible mass; full-pass depth variance and normal coherence."""
    alpha=r['alpha']; mass=r['topk_w'].sum(-1)
    valid=alpha>0
    denom=np.maximum(alpha,1e-8)
    depth=r['depth']
    variance=np.maximum(r['moment2']/denom-depth**2,0).astype(np.float32)
    albedo=np.clip((r['rgb']-(1-alpha)[...,None])/denom[...,None],0,1)
    albedo[~valid]=0
    return dict(alpha=alpha,depth=depth,normal=r['normal'],albedo=albedo,
                topk_id=r['topk_id'],topk_w=r['topk_w']/np.maximum(mass[...,None],1e-8),
                topk_mass=np.clip(mass/denom,0,1),topk_depth=r['topk_depth'],
                topk_normal=r['topk_normal'],depth_variance=variance,
                normal_coherence=np.clip(r['normal_len']/denom,0,1))
