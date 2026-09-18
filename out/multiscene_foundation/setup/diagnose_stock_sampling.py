"""Post-result diagnosis only; cannot change frozen eligibility or source."""
from pathlib import Path
import sys,json,math
import numpy as np,cv2,torch
from types import SimpleNamespace
root=Path('/home/u00134/3dgs_line/tier1');out=root/'out/multiscene_foundation'
sys.path[:0]=[str(root),str(out/'vendor/training_site'),str(root/'out/vrss/vendor/official_site'),str(out/'vendor/gaussian-splatting')]
from src.foundation import load_asset,native_render,qualification_metrics,freeze_json
from src.multiscene_qualification import save_grid
from gaussian_renderer import render
from utils.graphics_utils import getProjectionMatrix
cfg=json.loads((out/'config.json').read_text());cam=cfg['scenes']['lego']['cameras']['train_001'];K=np.array(cam['K']);w=np.array(cam['w2c'])
ply=out/'training/lego/seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply';a=load_asset(ply)
t={k:torch.tensor(v,device='cuda') for k,v in a.items()}
pc=SimpleNamespace(get_xyz=t['mu'],get_opacity=t['opacity'],get_scaling=t['scale'],get_rotation=t['quat'],get_features=t['sh'],active_sh_degree=3)
pipe=SimpleNamespace(compute_cov3D_python=False,convert_SHs_python=False,debug=False)
rgba=cv2.imread(cam['path'],cv2.IMREAD_UNCHANGED)[:,:,[2,1,0,3]].astype(float)/255
gt=cv2.resize(rgba[:,:,:3]*rgba[:,:,3:]+1-rgba[:,:,3:],(400,400),interpolation=cv2.INTER_AREA)
roi=cv2.resize(rgba[:,:,3],(400,400),interpolation=cv2.INTER_AREA)>=.5
images={'GT400':gt};metrics={}
for size in [400,800]:
 fov=2*math.atan(400/(2*K[0,0]));view=torch.tensor(w.T.copy(),dtype=torch.float32,device='cuda')
 P=getProjectionMatrix(.01,100.,fov,fov).transpose(0,1).cuda()
 camera=SimpleNamespace(FoVx=fov,FoVy=fov,image_height=size,image_width=size,
   world_view_transform=view,full_proj_transform=view@P,camera_center=torch.tensor(np.linalg.inv(w)[:3,3],dtype=torch.float32,device='cuda'))
 with torch.no_grad():direct=render(camera,pc,pipe,torch.ones(3,device='cuda'))['render'].permute(1,2,0).cpu().numpy()
 key=f'official{size}';images[key]=cv2.resize(direct,(400,400),interpolation=cv2.INTER_AREA)
 metrics[key]=qualification_metrics(gt,images[key],roi)
 if size==400:
  kc=K.copy();kc[:2,2]-=.5;native=native_render(a,kc,w,400,400,1)['stock_rgb']
  metrics['official400_vs_native_canonical_max']=float(np.abs(direct-native).max())
current=np.load(out/'training/lego/seed_1729/quality/measurements/native/train_001.npz')['rgb_1']
images['frozen_K400']=current;metrics['frozen_K400']=qualification_metrics(gt,current,roi)
freeze_json(out/'setup/stock_sampling_diagnosis.json',dict(metrics=metrics,role='diagnostic only; no eligibility override'))
save_grid(out/'setup/stock_sampling_diagnosis.png',list(images.items()),2)
print(json.dumps(metrics))
