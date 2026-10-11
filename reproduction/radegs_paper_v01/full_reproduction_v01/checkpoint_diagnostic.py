"""Read-only CUDA render/normal-loss diagnosis, invoked only by gated runner.

No optimizer, parameter write, GT point cloud, retraining or alternate loss.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import numpy as np
import torch
from gpu_stages import load_scene,report
from gaussian_renderer import render
from paper_losses import geometry_losses,median_depth_normal
from safety import atomic_json,sha256,verify_seal


def quantiles(x):
    a=x.detach().cpu().numpy().ravel()
    return {'q':np.quantile(a,[0,.1,.5,.9,1]).tolist(),
            'positive_fraction':float((a>0).mean()),'negative_fraction':float((a<0).mean()),
            'mean':float(a.mean()),'sum':float(a.astype(np.float64).sum())}


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args()
    c=json.loads(Path(args.config).read_text())
    assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
    parent=json.loads(Path(c['parent_config']).read_text())
    for stage in ['train','export']:
        assert verify_seal(Path(parent['state_dir'])/(stage+'.seal.json'),stage,parent['inputs'])
    out=Path(c['diagnostic_output'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False)
    model,cameras,pipe,info=load_scene(c,c['model'],False)
    old_dir=Path(c['model'])/'depth_normal'
    results=[];outputs=[]
    for iteration in [15000,30000]:
        ply=Path(c['model'])/f'point_cloud/iteration_{iteration}/point_cloud.ply'
        model.load_ply(str(ply))
        for camera in cameras:
            view=camera.image_name
            if iteration==30000 and view not in ['0000','0012','0024','0036','0048']:continue
            with torch.no_grad():
                r=render(camera,model,pipe,torch.zeros(3,device='cuda'))
                d,n=geometry_losses(r,camera)
                assert all(torch.isfinite(r[k]).all() for k in ['render','mask','normal','middepth'])
                valid=(r['mask']>=.5)&(camera.gt_mask>=.5)&(r['middepth']>0)&(r['middepth']<8)
                row={'iteration':iteration,'view':view,'alpha':quantiles(r['mask']),
                     'valid_original_threshold_pixels':int(valid.sum()),'eq23_mean':float(d),'eq24_mean':float(n)}
                if iteration==30000:
                    with np.load(old_dir/(view+'.npz')) as z:
                        row['sealed_export_regression_max_abs']={key:float(abs(r[field].cpu().numpy()-z[key]).max())
                            for key,field in [('rgb','render'),('alpha','mask'),('median_camera_z','middepth'),('blended_normal_camera','normal')]}
                    assert max(row['sealed_export_regression_max_abs'].values())<=1e-6
                if view in ['0000','0012','0024','0036','0048']:
                    import math
                    fx=camera.image_width/(2*math.tan(camera.FoVx/2));fy=camera.image_height/(2*math.tan(camera.FoVy/2))
                    path=out/f'{iteration}_{view}.npz'
                    np.savez_compressed(path,rgb=r['render'].cpu().numpy(),alpha=r['mask'].cpu().numpy(),
                        median_camera_z=r['middepth'].cpu().numpy(),blended_normal_camera=r['normal'].cpu().numpy(),
                        median_depth_normal_camera=median_depth_normal(r['middepth'],fx,fy).cpu().numpy())
                    outputs.append(path)
            if view=='0000':
                # True existing Eq24 analytic gradient on an actual trained scene.
                r=render(camera,model,pipe,torch.zeros(3,device='cuda'))
                d,n=geometry_losses(r,camera)
                grad=torch.autograd.grad(5*n,model._opacity)[0]
                assert torch.isfinite(grad).all()
                row['weighted_Eq24_opacity_logit_gradient']=quantiles(grad)
                row['gradient_interpretation']='positive means gradient descent lowers this opacity logit; no optimizer step performed'
                del r,d,n,grad
            results.append(row);atomic_json(out/'progress.json',{'rows':results,'optimizer_steps':0})
            print(json.dumps(row),flush=True)
    result=out/'checkpoint_diagnostic.json'
    atomic_json(result,{'rows':results,'optimizer_steps':0,'scope':'training views; not held-out evaluation',
        'training_method_unchanged':True,'negative_training_result_not_repaired':True})
    outputs.append(result)
    report(c,'checkpoint_diagnostic',outputs,{'views_15000':49,'views_30000':5,'optimizer_steps':0,
        'official_eval_executed':False,'result_path':str(result)})


if __name__=='__main__':main()
