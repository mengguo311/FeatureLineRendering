"""Depth-only raw export. No TSDF, mesh, culling, or GT evaluation functions.
"""
import json,os,sys,math,time,subprocess
from pathlib import Path
from safety import atomic_json,sha256
def run(command,env=None):
    result=subprocess.run(command,env=env)
    if result.returncode:
        raise SystemExit(result.returncode if result.returncode>0 else 75)

def report(config,stage,outputs,details):
    atomic_json(config['reports'][stage],{'status':'PASS','stage':stage,'inputs':config['inputs'],
                'attempt':os.environ['RADEGS_ATTEMPT'],'outputs':{str(Path(p).resolve()):sha256(p) for p in outputs},
                'details':details,'unix':time.time(),'scientificdone':False})

def load_scene(config,model_path,load_model):
    from argparse import ArgumentParser
    from arguments import ModelParams,PipelineParams
    from scene import GaussianModel
    from scene.dataset_readers import sceneLoadTypeCallbacks
    from utils.camera_utils import cameraList_from_camInfos
    p=ArgumentParser();mp=ModelParams(p);pp=PipelineParams(p)
    args=p.parse_args(['-s',config['data'],'-m',str(model_path),'-r','2','--use_decoupled_appearance'])
    dataset=mp.extract(args);pipe=pp.extract(args)
    info=sceneLoadTypeCallbacks['Colmap'](dataset.source_path,dataset.images,False)
    cameras=cameraList_from_camInfos(info.train_cameras,1.,dataset)
    model=GaussianModel(dataset.sh_degree)
    if load_model:model.load_ply(str(Path(config['model'])/'point_cloud/iteration_30000/point_cloud.ply'))
    else:
        model.create_from_pcd(info.point_cloud,info.nerf_normalization['radius'])
        model.compute_3D_filter(cameras)
    return model,cameras,pipe,info

def validate_scene_manifest(config,cameras,model,initial):
    expected=config['expected_scene']
    assert len(cameras)==expected['views'],'camera count differs from sealed data manifest'
    assert all([c.image_width,c.image_height]==expected['half_resolution'] for c in cameras),'resolution mismatch'
    if initial:assert len(model._xyz)==expected['initial_colmap_points'],'COLMAP initialization count mismatch'



def export(c):
 import numpy as np,torch
 from gaussian_renderer import render
 from loss_reference import depth_normal
 model,cameras,pipe,info=load_scene(c,c['model'],True);validate_scene_manifest(c,cameras,model,False)
 outputs=[];summary=[]
 for iteration in (15000,30000):
  ply=Path(c['model'])/'completed_step_ply'/str(iteration)/'point_cloud.ply';model.load_ply(str(ply))
  directory=Path(c['model'])/('depth_normal' if iteration==30000 else 'depth_normal_15000');directory.mkdir(exist_ok=True)
  metadata=[]
  with torch.no_grad():
   for camera in cameras:
    o=render(camera,model,pipe,torch.zeros(3,device='cuda'));fx=camera.image_width/(2*math.tan(camera.FoVx/2));fy=camera.image_height/(2*math.tan(camera.FoVy/2))
    values={'median_camera_z':o['middepth'],'expected_camera_z':__import__('masked_division').expected_depth_quotient(o['depth'],o['mask']),'alpha':o['mask'],'blended_normal_camera':o['normal'],'median_depth_normal_camera':depth_normal(o['middepth'],fx,fy).permute(2,0,1),'rgb':o['render']}
    assert all(torch.isfinite(v).all() for v in values.values());p=directory/(camera.image_name+'.npz');np.savez_compressed(p,**{k:v.cpu().numpy() for k,v in values.items()});outputs.append(p)
    metadata.append({'view':camera.image_name,'width':camera.image_width,'height':camera.image_height,'fx':fx,'fy':fy,'extrinsic':camera.extrinsic.cpu().tolist(),'depth_kind':'median affine camera-z; raw','iteration':iteration})
    summary.append({'iteration':iteration,'view':camera.image_name,'alpha_ge_half':int((o['mask']>=.5).sum()),'pixels':o['mask'].numel(),'positive_depth':int((o['middepth']>0).sum())})
  meta=directory/'cameras_and_conventions.json';atomic_json(meta,metadata);outputs.append(meta)
 stat=Path(c['model'])/'export_summary.json';atomic_json(stat,summary);outputs.append(stat)
 assert len(summary)==2*c['expected_scene']['views']
 report(c,'export',outputs,{'views_per_checkpoint':c['expected_scene']['views'],'checkpoints':[15000,30000],'raw_camera_z':True,'method_variant':'official_code_fix_v01','training_view_diagnostic_not_heldout_NVS':True})


