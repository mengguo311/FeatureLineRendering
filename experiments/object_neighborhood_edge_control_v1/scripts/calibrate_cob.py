"""RGB agreement and real mask-signal audit for isolated official B4 native code."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,EXP,ART,resource_guard,atomic_json,sha

def audit():
    guard=resource_guard()
    import torch
    import math
    import numpy as np
    from renderer_adapter import load_checkpoint,make_camera,rgb,small_model
    cfg=json.loads((EXP/'configs/pilot.json').read_text())
    frame=json.loads((EXP/'data/manifests/cameras.json').read_text())['splits']['train'][0]
    camera=make_camera(frame,512,cfg['camera_angle_x'])
    m=load_checkpoint(OUT/'models/panels_high/chkpnt7000.pth')
    with torch.no_grad():before=rgb(m,camera)
    from native import install_cob
    cob=install_cob()
    def raster(model,cam,include=True):
        N=len(model.get_xyz)
        settings=cob.GaussianRasterizationSettings(image_height=cam.image_height,image_width=cam.image_width,
            tanfovx=math.tan(cam.FoVx*.5),tanfovy=math.tan(cam.FoVy*.5),bg=torch.zeros(3,device='cuda'),
            scale_modifier=1.,viewmatrix=cam.world_view_transform,projmatrix=cam.full_proj_transform,
            sh_degree=0,campos=cam.camera_center,prefiltered=False,debug=False,antialiasing=False,include_mask=include)
        signals=torch.zeros((N,2),device='cuda',requires_grad=True)
        mask=torch.zeros(N,device='cuda',requires_grad=True)
        values=cob.GaussianRasterizer(settings)(means3D=model.get_xyz,means2D=torch.zeros_like(model.get_xyz),
            shs=model.get_features,colors_precomp=None,mask_precomp=mask,mask_signals=signals,
            opacities=model.get_opacity,scales=model.get_scaling,rotations=model.get_rotation,cov3D_precomp=None)
        return values,signals
    (after,mask,radii,depth),signals=raster(m,camera)
    maxdiff=float((before-after).abs().max());mean=float((before-after).abs().mean())
    # Native signs at a single accepted centre pixel: foreground vs rest.
    sample=small_model([[0,0,0],[0,0,-1]],[.5,.8],[[1,0,0],[0,0,1]])
    cam=make_camera({'transform_matrix':[[1,0,0,0],[0,1,0,0],[0,0,1,3],[0,0,0,1]]},65)
    vals,signal=raster(sample,cam);mask_image=vals[1]
    grad=torch.zeros_like(mask_image);grad[...,32,32]=-1
    signal_grad=torch.autograd.grad((mask_image*grad).sum(),signal)[0].cpu().numpy()
    out={'guard':guard,'native_RGB_max_abs':maxdiff,'native_RGB_mean_abs':mean,
         'tolerance':2e-6,'qualified':maxdiff<2e-6,'mask_foreground_signals':signal_grad.tolist(),
         'expected_unweighted_foreground_rest_counts':[[1.,0.],[1.,0.]],
         'count_max_abs_error':float(np.max(np.abs(signal_grad-[[1,0],[1,0]]))),
         'same_initial_checkpoint':sha(OUT/'models/panels_high/chkpnt7000.pth'),
         'mask_kernel':'official COB native backward sign counts, not RGB error proxy',
         'antialiasing':False,'RGB_algorithm_claim':'native dr_aa without AA calibrated to stock; upstream COB wrapper clamps RGB to [0,1]'}
    atomic_json(ART/'environment/cob_calibration.json',out)
    if not out['qualified'] or out['count_max_abs_error']>1e-6:raise RuntimeError('B4 calibration failed')

if __name__=='__main__':audit()
