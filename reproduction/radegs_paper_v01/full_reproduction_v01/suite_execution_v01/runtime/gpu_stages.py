"""One resolved paper-protocol scene chain. Every invocation is behind runner's GPU gate."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from safety import atomic_json,sha256
from suite_scope import validate_config_scope
STAGE2=Path(__file__).resolve().parents[3]/"stage2"


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


def integration_smoke(config):
    import torch
    from gaussian_renderer import render
    from paper_losses import geometry_losses
    from train import L1_loss_appearance
    model,cameras,pipe,info=load_scene(config,Path(config['model'])/'smoke',False)
    validate_scene_manifest(config,cameras,model,True)
    result=render(cameras[0],model,pipe,torch.zeros(3,device='cuda'))
    d,n=geometry_losses(result,cameras[0])
    photo=L1_loss_appearance(result['render'],cameras[0].original_image,model,cameras[0].uid)
    loss=photo+100*d+5*n
    assert torch.isfinite(loss)
    loss.backward()
    for key in ('_xyz','_scaling','_rotation','_opacity','_features_dc','_appearance_embeddings'):
        gradient=getattr(model,key).grad
        assert gradient is not None and torch.isfinite(gradient).all(),key
    assert torch.isfinite(model.filter_3D).all()
    return {'cameras':len(cameras),'initial_colmap_points':len(model._xyz),
            'half_resolution':[777,581],'photo_l1':float(photo),'eq23':float(d),'eq24':float(n),
            'optimizer_steps':0,'purpose':'GPU data/appearance/filter/forward/backward smoke only'}


def smoke(config):
    out=Path(config['state_dir'])/'gpu_validation';out.mkdir(exist_ok=True)
    worker=STAGE2/'gpu_smoke.py'
    base=out/'baseline.pt';variant=out/'variant.pt';comparison=out/'comparison.json'
    env=os.environ.copy()
    env['PYTHONPATH']=config['baseline_python']+os.pathsep+env.get('PYTHONPATH','')
    run([sys.executable,str(worker),'--mode','baseline','--output',str(base)],env=env)
    run([sys.executable,str(worker),'--mode','variant','--output',str(variant)])
    run([sys.executable,str(worker),'--mode','compare','--baseline',str(base),'--variant',str(variant),'--output',str(comparison)])
    extra=out/'independent_eq24.json'
    extra_worker=STAGE2.parent/'gradient_fix_v01/validate_eq24.py'
    run([sys.executable,str(extra_worker),'--output',str(extra)])
    sweep=out/'eq24_eps_sweep.json'
    run([sys.executable,str(extra_worker.with_name('probe_eq24.py')),'--output',str(sweep)])
    details=integration_smoke(config)
    path=out/'integration.json';atomic_json(path,details)
    report(config,'smoke',[base,variant,comparison,extra,sweep,path],details)


def train(config):
    # Group SIGTERM also reaches train.py, which checkpoints at a step boundary.
    # Keep this parent alive until that child finishes so supervision is durable.
    signal.signal(signal.SIGTERM,lambda signum,frame:None)
    signal.signal(signal.SIGINT,lambda signum,frame:None)
    run(config['train_command'])
    model=Path(config['model'])
    complete=model/'train_complete.json';data=json.loads(complete.read_text())
    assert data['iterations']==30000 and data['inputs']==config['inputs']
    from checkpointing import checkpoint_descriptor
    desc=checkpoint_descriptor(model/'restart.json',config['inputs'])
    assert desc['completed_iteration']==30000
    log=model/'iteration_loss.jsonl'
    iterations=set()
    with open(log) as f:
        for line in f:
            value=json.loads(line);iterations.add(value['iteration'])
            assert value['geometry_active']==(value['iteration']>15000)
            assert value['wn']==(5 if value['iteration']>15000 else 0)
    assert iterations==set(range(1,30001))
    ply=model/'point_cloud/iteration_30000/point_cloud.ply'
    from plyfile import PlyData
    vertices=PlyData.read(ply)['vertex']
    assert len(vertices.data)>0 and 'filter_3D' in vertices.data.dtype.names
    report(config,'train',[complete,model/'restart.json',desc['path'],ply,log],
           {'iterations':30000,'unique_iteration_records':len(iterations),'gaussians':len(vertices.data),
            'result_kind':'training completed; geometry evaluation pending'})


def export(config):
    import numpy as np
    import torch
    from gaussian_renderer import render
    from paper_losses import median_depth_normal
    import math
    model,cameras,pipe,info=load_scene(config,config['model'],True)
    directory=Path(config['model'])/'depth_normal';directory.mkdir(exist_ok=True)
    outputs=[];metadata=[]
    with torch.no_grad():
        for camera in cameras:
            result=render(camera,model,pipe,torch.zeros(3,device='cuda'))
            fx=camera.image_width/(2*math.tan(camera.FoVx/2));fy=camera.image_height/(2*math.tan(camera.FoVy/2))
            target=median_depth_normal(result['middepth'],fx,fy)
            values={'median_camera_z':result['middepth'],'alpha':result['mask'],
                    'blended_normal_camera':result['normal'],'median_depth_normal_camera':target,
                    'rgb':result['render']}
            assert all(torch.isfinite(x).all() for x in values.values())
            path=directory/(camera.image_name+'.npz')
            np.savez_compressed(path,**{k:v.cpu().numpy() for k,v in values.items()})
            outputs.append(path)
            metadata.append({'view':camera.image_name,'width':camera.image_width,'height':camera.image_height,
                             'fx':fx,'fy':fy,'extrinsic':camera.extrinsic.cpu().tolist(),
                             'depth_kind':'median affine camera-z; raw, not alpha-normalized'})
    meta=directory/'cameras_and_conventions.json';atomic_json(meta,metadata);outputs.append(meta)
    validate_scene_manifest(config,cameras,model,False)
    report(config,'export',outputs,{'views':len(cameras),'convention':'raw float camera-z/alpha/blended normal and finite-difference median normal'})


def masked_camera_z(depth,alpha,mask,shape):
    import numpy as np
    if any(x.shape!=shape or not np.isfinite(x).all() for x in (depth,alpha,mask)) or depth.dtype!=np.float32:
        raise ValueError('invalid cached depth/alpha/mask')
    out=depth.copy();out[(mask<.5)|(alpha<.5)]=0
    return out


def tsdf(config):
    # Fixed C24 values with the already validated sparse allocation bridge.
    # Native GPU rerender is redundant: export seal covers identical raw arrays.
    import numpy as np
    import open3d as o3d
    from PIL import Image
    from safety import verify_seal
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from tsdf_touch import touch_blocks
    from empty_mesh import extract_mesh
    state=Path(config['state_dir']);model=Path(config['model'])
    for stage in ['train','export']:assert verify_seal(state/(stage+'.seal.json'),stage,config['inputs'])
    out=state/'tsdf_attempts'/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False)
    cams=json.loads((model/'depth_normal/cameras_and_conventions.json').read_text())
    assert len(cams)==config['expected_scene']['views']
    vbg=o3d.t.geometry.VoxelBlockGrid(attr_names=('tsdf','weight'),attr_dtypes=(o3d.core.float32,o3d.core.float32),attr_channels=(1,1),voxel_size=.002,block_resolution=16,block_count=50000,device=o3d.core.Device('CPU:0'))
    rows=[]
    for cam in cams:
        W,H=cam['width'],cam['height'];view=cam['view']
        with np.load(model/'depth_normal'/(view+'.npz')) as z:
            raw=z['median_camera_z'][0];alpha=z['alpha'][0]
            with Image.open(Path(config['data'])/'images'/(view+'.png')) as im:mask=np.asarray(im.split()[3].resize((W,H)))/255
            depth=masked_camera_z(raw,alpha,mask,(H,W))
        k=np.array([[cam['fx'],0,W/2],[0,cam['fy'],H/2],[0,0,1]],np.float64);e=np.asarray(cam['extrinsic'],np.float64)
        coords,info=touch_blocks(vbg,depth,k,e)
        if coords is not None:vbg.integrate(coords,o3d.t.geometry.Image(depth),o3d.core.Tensor(k),o3d.core.Tensor(e),1.,8.)
        row=dict(view=view,integrated=coords is not None,**info);rows.append(row)
        atomic_json(out/'progress.json',{'views':rows,'total_views':len(cams),'scientificdone':False});print(json.dumps(row),flush=True)
    assert any(r['integrated'] for r in rows),'NEGATIVE_GEOMETRY: all views empty under unchanged thresholds'
    vbg.save(str(out/'volume.npz'));mesh,extraction=extract_mesh(vbg)
    detail={'vertices':len(mesh.vertices),'triangles':len(mesh.triangles),'finite_vertices':bool(np.isfinite(np.asarray(mesh.vertices)).all()),'view_records':rows,'native_extraction':extraction,'method':'C24 TSDF fixed values; frozen sparse-allocation bridge; explicitly logged empty views','depth_scale':1.,'depth_max':8.,'voxel_size':.002,'alpha_threshold':.5,'mesh_weight_threshold':3.,'scientificdone':False}
    atomic_json(out/'result.json',detail)
    assert len(mesh.vertices) and len(mesh.triangles) and detail['finite_vertices'],'NEGATIVE_GEOMETRY: no finite mesh at fixed thresholds'
    mesh.compute_vertex_normals();path=model/'recon.ply'
    assert not path.exists(),'existing mesh requires explicit failure review; do not overwrite'
    assert o3d.io.write_triangle_mesh(str(path),mesh)
    report(config,'tsdf',[path,out/'result.json',out/'progress.json',out/'volume.npz'],detail)


def evaluate(config):
    # Author outer launcher uses sys.executable/check=True; mathematical AST
    # and inner DTU metric are unchanged, see evaluator source audit.
    cpus=sorted(os.sched_getaffinity(0))[:4];os.sched_setaffinity(0,cpus)
    run(config['eval_command'])
    import math
    path=Path(config['model'])/'vis/results.json'
    values=json.loads(path.read_text())
    for key in ['mean_d2s','mean_s2d','overall']:
        assert math.isfinite(values[key]) and values[key]>=0
    assert abs(values['overall']-(values['mean_d2s']+values['mean_s2d'])/2)<1e-10
    outputs=[path,Path(config['model'])/'recon_culled.ply',Path(config['model'])/'recon_aligned.ply']
    import open3d as o3d
    import numpy as np
    for mesh_path in outputs[1:]:
        mesh=o3d.io.read_triangle_mesh(str(mesh_path))
        assert len(mesh.vertices)>0 and len(mesh.triangles)>0 and np.isfinite(np.asarray(mesh.vertices)).all()
    report(config,'eval',outputs,{'metrics_mm':values,'GT_role':'evaluation only',
           'claim':'one paper-text scene evaluated; metric agreement and full-suite completion require independent review','outer_evaluator_deviation':'sys.executable subprocess with checked exit status; mathematical AST unchanged','author_inner_metric_unchanged':True})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True)
    parser.add_argument('--stage',required=True,choices=['smoke','train','export','tsdf','eval'])
    args=parser.parse_args();config=json.loads(Path(args.config).read_text())
    validate_config_scope(config)
    # Explicitly configured source path; all outputs and caches stay on HDD.
    sys.path.insert(0,config['cwd'])
    {'smoke':smoke,'train':train,'export':export,'tsdf':tsdf,'eval':evaluate}[args.stage](config)
