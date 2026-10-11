"""Read-only exact30k checkpoint/appearance full-loss gradients on49 train views."""
import argparse,json,os,math
from pathlib import Path
import numpy as np,torch
from safety import atomic_json,sha256,verify_seal
from gpu_stages import load_scene,report
from checkpointing import restore_checkpoint
from arguments import ModelParams,PipelineParams,OptimizationParams
from gaussian_renderer import render
from paper_losses import geometry_losses
from train import L1_loss_appearance
from utils.loss_utils import ssim

def stats(g):
 return {'l2':float(torch.linalg.vector_norm(g)),'sum':float(g.double().sum()),'positive_fraction':float((g>0).float().mean()),'negative_fraction':float((g<0).float().mean())}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args();c=json.loads(Path(args.config).read_text());assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 parent=json.loads(Path(c['parent_config']).read_text())
 assert verify_seal(Path(parent['state_dir'])/'train.seal.json','train',parent['inputs'])
 model,cameras,pipe,_=load_scene(c,c['model'],False)
 p=argparse.ArgumentParser();mp=ModelParams(p);pp=PipelineParams(p);op=OptimizationParams(p);options,_=p.parse_known_args(parent['train_command'][2:]);opt=op.extract(options)
 it,_=restore_checkpoint(Path(c['model'])/'restart.json',model,opt,parent['inputs']);assert it==30000
 out=Path(c['diagnostic_output'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False)
 rows=[];opa=model._opacity
 assert abs(opt.lambda_dssim-.2)<1e-12
 for cam in cameras:
  r=render(cam,model,pipe,torch.zeros(3,device='cuda'));d,n=geometry_losses(r,cam)
  photo=(1-opt.lambda_dssim)*L1_loss_appearance(r['render'],cam.original_image,model,cam.uid)+opt.lambda_dssim*(1-ssim(r['render'],cam.original_image.unsqueeze(0)))
  terms={'photo':photo,'Eq23':100*d,'Eq24':5*n,'full':photo+100*d+5*n}
  grads={k:torch.autograd.grad(v,opa,retain_graph=True)[0] for k,v in terms.items()};assert all(torch.isfinite(g).all() for g in grads.values());assert torch.count_nonzero(grads['Eq23'])==0
  # This is a directional first-order diagnostic, not an optimizer step or
  # a finite difference across discrete median/visibility branches.
  alpha=torch.sigmoid(opa).detach();alpha_prime=alpha*(1-alpha)
  row={'view':cam.image_name,'losses':{k:float(v) for k,v in terms.items()},'opacity_logit_gradients':{k:stats(v) for k,v in grads.items()},'plain_SGD_unit_step_first_order_mean_raw_opacity_change':{k:float((-alpha_prime*g).mean()) for k,g in grads.items()},'photo_Eq24_cosine':float((grads['photo']*grads['Eq24']).sum()/(torch.linalg.vector_norm(grads['photo'])*torch.linalg.vector_norm(grads['Eq24'])).clamp_min(1e-20))}
  if cam.image_name in ['0000','0012','0024','0036','0048']:
   with np.load(Path(c['model'])/'depth_normal'/f'{cam.image_name}.npz') as z:
    row['checkpoint_PLY_export_regression']={k:float(abs(r[field].detach().cpu().numpy()-z[k]).max()) for k,field in [('rgb','render'),('alpha','mask'),('median_camera_z','middepth'),('blended_normal_camera','normal')]}
   assert max(row['checkpoint_PLY_export_regression'].values())<=1e-6
  rows.append(row);atomic_json(out/'progress.json',{'rows':rows,'optimizer_steps':0,'appearance_restored':True});print(json.dumps(row),flush=True)
  del r,d,n,terms,grads,photo
 path=out/'full_loss_diagnostic.json';atomic_json(path,{'rows':rows,'optimizer_steps':0,'checkpoint_iteration':it,'actual_appearance_and_optimizer_restored':True,'provenance':parent['inputs'],'scope':'30k train-view instantaneous derivatives, not complete historical causal proof; no15k appearance checkpoint available','scientificdone':False});report(c,'checkpoint_diagnostic',[path],{'views':49,'optimizer_steps':0,'result':str(path)})
if __name__=='__main__':main()
