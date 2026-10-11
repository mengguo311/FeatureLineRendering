"""Read-only original/candidate rendering comparison, no model update."""
import argparse
import json
import math
import os
from pathlib import Path
import numpy as np
import torch
from gaussian_renderer import render
from gpu_stages import load_scene,report
from paper_losses import geometry_losses,median_depth_normal
from safety import atomic_json,verify_seal,sha256


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args()
    c=json.loads(Path(args.config).read_text())
    assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
    from diff_gaussian_rasterization import _C
    assert sha256(_C.__file__)==c['inputs']['candidate_native']
    parent=json.loads(Path(c['original_training_config']).read_text())
    for stage in ['train','export']:
        assert verify_seal(Path(parent['state_dir'])/(stage+'.seal.json'),stage,parent['inputs'])
    out=Path(c['state_dir'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(exist_ok=False)
    model,cameras,pipe,_=load_scene(c,c['model'],False)
    selected=['0000','0012','0024','0036','0048'];rows=[];outputs=[];failures=[]
    with torch.no_grad():
        for iteration in [15000,30000]:
            model.load_ply(str(Path(c['existing_model'])/f'point_cloud/iteration_{iteration}/point_cloud.ply'))
            for camera in cameras:
                view=camera.image_name
                if iteration==15000 and view not in selected:continue
                r=render(camera,model,pipe,torch.zeros(3,device='cuda'))
                d,n=geometry_losses(r,camera)
                arrays={key:r[field].cpu().numpy() for key,field in [('rgb','render'),('alpha','mask'),
                    ('median_camera_z','middepth'),('blended_normal_camera','normal')]}
                assert all(np.isfinite(a).all() for a in arrays.values())
                base=Path(c['existing_model'])/'depth_normal'/f'{view}.npz' if iteration==30000 else Path(c['reference_15k'])/f'15000_{view}.npz'
                with np.load(base) as b:
                    errors={key:float(abs(arrays[key]-b[key]).max()) for key in arrays}
                row={'iteration':iteration,'view':view,'max_abs_difference':errors,'eq23_mean':float(d),'eq24_mean':float(n),
                     'valid_original_threshold_pixels':int(((r['mask']>=.5)&(camera.gt_mask>=.5)&(r['middepth']>0)&(r['middepth']<8)).sum())}
                if max(errors['rgb'],errors['alpha'])>1e-6:failures.append([iteration,view,'RGB_ALPHA_DIFFERENCE_REQUIRES_REVIEW'])
                # Depth/normal are the corrected geometry outputs: measure and
                # preserve changes, do not demand equality with a known defect.
                if view in selected:
                    fx=camera.image_width/(2*math.tan(camera.FoVx/2));fy=camera.image_height/(2*math.tan(camera.FoVy/2))
                    arrays['median_depth_normal_camera']=median_depth_normal(r['middepth'],fx,fy).cpu().numpy()
                    f=out/f'{iteration}_{view}.npz';np.savez_compressed(f,**arrays);outputs.append(f)
                rows.append(row);print(json.dumps(row),flush=True)
                atomic_json(out/'progress.json',{'rows':rows,'optimizer_steps':0})
    result=out/'scene_regression.json'
    atomic_json(result,{'status':'FAIL' if failures else 'PASS','failures':failures,'rows':rows,
                       'optimizer_steps':0,'training_views_not_heldout':True,'depth_normal_changes_expected_and_recorded':True})
    assert not failures,str(failures)
    report(c,'checkpoint_diagnostic',[result,*outputs],{'operation':'fixed trained-scene RGB/alpha regression and geometry differences',
                                                      'optimizer_steps':0,'rows':len(rows),'result_path':str(result)})


if __name__=='__main__':main()
