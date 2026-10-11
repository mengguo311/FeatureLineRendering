"""Official-route export/TSDF/eval. C24 TSDF values remain fixed.
TSDF helper is the independently tested sparse allocation bridge, not upstream.
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
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
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
  outputs.extend(view_panels(c,directory,iteration))
 stat=Path(c['model'])/'export_summary.json';atomic_json(stat,summary);outputs.append(stat)
 assert len(summary)==98
 report(c,'export',outputs,{'views_per_checkpoint':49,'checkpoints':[15000,30000],'raw_camera_z':True,'method_variant':'official_code_fix_v01','training_view_diagnostic_not_heldout_NVS':True})

def view_panels(c,directory,iteration):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 import numpy as np
 from PIL import Image
 metas=json.loads((directory/'cameras_and_conventions.json').read_text());chosen=[metas[i] for i in (0,24,48)];fig,axes=plt.subplots(3,6,figsize=(18,8));titles=['Input RGB (training view)','Rendered RGB','Alpha [0,1]','Median camera-z [0,8]','Mixed normal (display normalized)','Depth normal']
 for row,cam in enumerate(chosen):
  z=np.load(directory/(cam['view']+'.npz'));rgb=np.asarray(Image.open(Path(c['data'])/'images'/(cam['view']+'.png')).convert('RGB').resize((cam['width'],cam['height'])))/255.;mix=z['blended_normal_camera'];mix=mix/np.maximum(np.linalg.norm(mix,axis=0),1e-12)
  arrays=[rgb,z['rgb'].transpose(1,2,0).clip(0,1),z['alpha'][0],np.ma.masked_where(z['alpha'][0]<.5,z['median_camera_z'][0]),(mix.transpose(1,2,0)+1)/2,(z['median_depth_normal_camera'].transpose(1,2,0)+1)/2]
  for col,x in enumerate(arrays):
   ax=axes[row,col];kw={'cmap':'gray','vmin':0,'vmax':1} if col==2 else {'cmap':'viridis','vmin':0,'vmax':8} if col==3 else {};ax.imshow(x,**kw);ax.set_axis_off()
   if row==0:ax.set_title(titles[col],fontsize=9)
  axes[row,0].text(0,.02,'view '+cam['view'],transform=axes[row,0].transAxes,color='yellow')
 fig.suptitle('official_code_fix_v01 / '+c['scene']+' / completed step '+str(iteration)+' (not held-out quality evaluation)');fig.tight_layout();out=Path(c['model'])/('VIEWS_'+str(iteration)+'.png');fig.savefig(out,dpi=150);plt.close(fig);return [out]

def evaluate(c):
 cpus=sorted(os.sched_getaffinity(0))[:4];os.sched_setaffinity(0,cpus);run(c['eval_command'])
 path=Path(c['model'])/'vis/results.json';v=json.loads(path.read_text())
 assert all(math.isfinite(v[k]) and v[k]>=0 for k in ('mean_d2s','mean_s2d','overall'));assert abs(v['overall']-(v['mean_d2s']+v['mean_s2d'])/2)<1e-10
 import open3d as o3d,numpy as np
 outputs=[path];details=[]
 for name in ('recon.ply','recon_culled.ply','recon_aligned.ply'):
  p=Path(c['model'])/name;m=o3d.io.read_triangle_mesh(str(p));vertices=np.asarray(m.vertices);assert len(vertices) and len(m.triangles) and np.isfinite(vertices).all();outputs.append(p);details.append({'path':str(p),'vertices':len(vertices),'triangles':len(m.triangles)})
 report(c,'eval',outputs,{'metrics_mm':v,'meshes':details,'GT_role':'evaluation only','method_variant':'official_code_fix_v01','author_evaluator_unchanged':True,'claim':'one independently corrected C24 configuration scene; paper agreement and full suite still require review'})
