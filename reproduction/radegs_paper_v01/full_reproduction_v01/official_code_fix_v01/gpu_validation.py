"""Only run within the independent official shared supervisor's admitted group."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from safety import atomic_json,sha256

def run(script,args=(),env=None):subprocess.run([sys.executable,str(script),*map(str,args)],check=True,env=env)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);a=ap.parse_args();c=json.loads(Path(a.config).read_text());assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 out=Path(c['validation_root'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False)
 import torch,diff_gaussian_rasterization as raster
 assert sha256(raster._C.__file__)==c['inputs']['native'];atomic_json(out/'loaded_native.json',{'path':raster._C.__file__,'sha256':sha256(raster._C.__file__)})
 code=Path(__file__).resolve().parent;stage2=code.parents[1]/'stage2';fix=code.parents[1]/'gradient_fix_v01';rgb=code.parent/'suite_execution_v01/scan69_cuda_failure_v01/rgb_vjp_validation_v02'
 run(rgb/'expanded_reference.py',['--output',out/'expanded_rgb.json'])
 env=os.environ.copy();env['PYTHONPATH']=c['baseline_python']+os.pathsep+env['PYTHONPATH']
 run(stage2/'gpu_smoke.py',['--mode','baseline','--output',out/'baseline.pt'],env)
 run(stage2/'gpu_smoke.py',['--mode','baseline','--output',out/'official.pt'])
 from gpu_smoke import assert_close
 b=torch.load(out/'baseline.pt',map_location='cpu');v=torch.load(out/'official.pt',map_location='cpu');reg={}
 for i,(x,y) in enumerate(zip(b['outputs'],v['outputs'])):
  assert_close(x.float(),y.float(),1e-6,1e-6,'C24 baseline output '+str(i));reg[str(i)]=float((x.float()-y.float()).abs().max())
 for k,x in b['rgb_alpha_gradients'].items():
  y=v['rgb_alpha_gradients'][k];assert_close(x,y,2e-4,2e-5,'C24 baseline large footprint RGBalpha backward '+k);reg['gradient_'+k]=float((x-y).abs().max())
 atomic_json(out/'baseline_regression.json',reg)
 run(fix/'validate_eq24.py',['--output',out/'normal_depth_backend.json'])
 run(code/'gpu_loss_check.py',['--output',out/'official_losses.json'])
 # Actual scan24 initialization, Mip filter, appearance and C24 loss at geometry phase, optimizer0.
 from gpu_stages import load_scene
 from gaussian_renderer import render
 from train import L1_loss_appearance
 from masked_division import distortion_quotient,expected_depth_quotient
 from utils.graphics_utils import depth_double_to_normal
 from utils.loss_utils import ssim
 model,cameras,pipe,info=load_scene(c,Path(c['model'])/'smoke',False)
 assert len(cameras)==49 and len(model._xyz)==31205 and (cameras[0].image_width,cameras[0].image_height)==(777,581)
 o=render(cameras[0],model,pipe,torch.zeros(3,device='cuda'));nd,_=depth_double_to_normal(cameras[0],expected_depth_quotient(o['depth'],o['mask']),o['middepth'])
 mixed=torch.nn.functional.normalize(o['normal'],dim=0).permute(1,2,0);error=1-(mixed[None]*nd).sum(-1);n=.4*error[0].mean()+.6*error[1].mean();d=(distortion_quotient(o['depth_distortion'],o['mask'])[0]*cameras[0].edge).mean()
 photo=.8*L1_loss_appearance(o['render'],cameras[0].original_image,model,cameras[0].uid)+.2*(1-ssim(o['render'],cameras[0].original_image.unsqueeze(0)))
 total=photo+100*d+.05*n;assert torch.isfinite(total);total.backward()
 from checkpointing import PARAMETERS
 grads={}
 for k in PARAMETERS:
  g=getattr(model,k).grad;assert g is not None and torch.isfinite(g).all(),k;grads[k]=float(g.abs().max())
 for k,p in model.appearance_network.named_parameters():assert p.grad is not None and torch.isfinite(p.grad).all(),k
 detail={'cameras':len(cameras),'COLMAP_points':len(model._xyz),'optimizer_steps':0,'photo':float(photo),'distortion':float(d),'normal':float(n),'total':float(total),'wd':100,'wn':.05,'alpha_positive':int((o['mask']>0).sum()),'alpha_ge_half':int((o['mask']>=.5).sum()),'grad_maxabs':grads,'filter_finite':bool(torch.isfinite(model.filter_3D).all()),'GT_geometry_loaded':False}
 atomic_json(out/'actual_scan24.json',detail);torch.cuda.synchronize()
 outputs={str(p):sha256(p) for p in out.iterdir() if p.is_file()}
 atomic_json(c['reports']['smoke'],{'status':'PASS','stage':'smoke','attempt':os.environ['RADEGS_ATTEMPT'],'inputs':c['inputs'],'outputs':outputs,'details':detail,'scientificdone':False});print(json.dumps(detail,indent=2),flush=True)
if __name__=='__main__':main()
