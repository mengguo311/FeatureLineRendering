"""Per-scene actual initialization FWBW, admitted by the common GPU0 gate."""
import os
from pathlib import Path
def smoke(c):
 import torch,diff_gaussian_rasterization as raster
 from safety import sha256,atomic_json
 from postprocess import load_scene,validate_scene_manifest,report
 from gaussian_renderer import render
 from train import L1_loss_appearance
 from masked_division import distortion_quotient,expected_depth_quotient
 from utils.graphics_utils import depth_double_to_normal
 from utils.loss_utils import ssim
 from checkpointing import PARAMETERS
 assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 assert sha256(raster._C.__file__)==c['inputs']['native']
 model,cameras,pipe,info=load_scene(c,Path(c['model'])/'smoke',False)
 validate_scene_manifest(c,cameras,model,True)
 rows=[]
 for camera in (cameras[0],cameras[len(cameras)//2],cameras[-1]):
  for p in [getattr(model,k) for k in PARAMETERS]+list(model.appearance_network.parameters()):p.grad=None
  o=render(camera,model,pipe,torch.zeros(3,device='cuda'))
  nd,_=depth_double_to_normal(camera,expected_depth_quotient(o['depth'],o['mask']),o['middepth'])
  mixed=torch.nn.functional.normalize(o['normal'],dim=0).permute(1,2,0);error=1-(mixed[None]*nd).sum(-1)
  n=.4*error[0].mean()+.6*error[1].mean();d=(distortion_quotient(o['depth_distortion'],o['mask'])[0]*camera.edge).mean()
  photo=.8*L1_loss_appearance(o['render'],camera.original_image,model,camera.uid)+.2*(1-ssim(o['render'],camera.original_image.unsqueeze(0)))
  total=photo+100*d+.05*n;assert torch.isfinite(total);total.backward();torch.cuda.synchronize()
  grads={}
  for k in PARAMETERS:
   g=getattr(model,k).grad;assert g is not None and torch.isfinite(g).all(),k;grads[k]=float(g.abs().max())
  for p in model.appearance_network.parameters():assert p.grad is not None and torch.isfinite(p.grad).all()
  rows.append({'view':camera.image_name,'loss':float(total),'photo':float(photo),'distortion':float(d),'normal':float(n),'gradient_maxabs':grads,'alpha_ge_half':int((o['mask']>=.5).sum())})
 out=Path(c['state_dir'])/'scene_smoke'/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False)
 details={'scene':c['scene'],'views':len(cameras),'initial_COLMAP_points':len(model._xyz),'rows':rows,'optimizer_steps':0,'GT_geometry_loaded':False,'native_sha256':sha256(raster._C.__file__),'filter_finite':bool(torch.isfinite(model.filter_3D).all())}
 assert details['filter_finite'];atomic_json(out/'result.json',details);report(c,'smoke',[out/'result.json'],details);print(details,flush=True)
