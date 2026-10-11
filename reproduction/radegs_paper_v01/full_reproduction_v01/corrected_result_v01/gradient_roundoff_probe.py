"""Reproduce independent-VJP sum failure; compare fused adjoints without training."""
import argparse,json,os,math
from pathlib import Path
import numpy as np
import torch
from safety import atomic_json,sha256,verify_seal
from gpu_stages import load_scene,report
from gaussian_renderer import render
from gradient_decomposition import eq24_diagnostic_parts

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();c=json.loads(Path(a.config).read_text())
 assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 from diff_gaussian_rasterization import _C
 assert sha256(_C.__file__)==c['inputs']['candidate_native']
 out=Path(c['diagnostic_output'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False)
 m,cams,pipe,_=load_scene(c,c['model'],False);m.load_ply(str(Path(c['model'])/'point_cloud/iteration_15000/point_cloud.ply'));cam=cams[0];assert cam.image_name=='0000'
 r=render(cam,m,pipe,torch.zeros(3,device='cuda'));fx=cam.image_width/(2*math.tan(cam.FoVx/2));fy=cam.image_height/(2*math.tan(cam.FoVy/2))
 parts=eq24_diagnostic_parts(r['mask'],r['normal'],r['middepth'],fx,fy)
 keys=['_opacity','_scaling','_rotation','_xyz'];params=[getattr(m,k) for k in keys];renders=[r[k] for k in ['mask','normal','middepth']]
 grads={k:torch.autograd.grad(5*v,params,retain_graph=True) for k,v in parts.items()}
 adj={k:torch.autograd.grad(5*v,renders,retain_graph=True,allow_unused=True) for k,v in parts.items()}
 for k in adj:adj[k]=[torch.zeros_like(x) if v is None else v for x,v in zip(renders,adj[k])]
 combined=[sum(adj[k][j] for k in ['alpha','normal','depth']) for j in range(3)]
 adj_errors=[]
 for x,y in zip(combined,adj['full']):
  adj_errors.append(float((x-y).abs().max()));torch.testing.assert_close(x,y,rtol=1e-6,atol=1e-9)
 fused=torch.autograd.grad(renders,params,grad_outputs=combined,retain_graph=True)
 repeats=[torch.autograd.grad(parts['full']*5,params,retain_graph=True) for _ in range(3)]
 rows={};arrays={};failures=[]
 for j,key in enumerate(keys):
  full=grads['full'][j];ind=sum(grads[k][j] for k in ['alpha','normal','depth']);den=torch.linalg.vector_norm(full).clamp_min(1e-20)
  def err(x):return {'max_abs':float((x-full).abs().max()),'relative_l2':float(torch.linalg.vector_norm(x-full)/den)}
  f=err(fused[j]);row={'independent_sum':err(ind),'fused_adjoint_sum':f,'full_repeat_errors':[err(rep[j]) for rep in repeats],'full_gradient_l2':float(den),'part_l2':{k:float(torch.linalg.vector_norm(grads[k][j])) for k in ['alpha','normal','depth']},'cancellation_condition_l2':float(sum(torch.linalg.vector_norm(grads[k][j]) for k in ['alpha','normal','depth'])/den)}
  if not (f['relative_l2']<1e-4 or f['max_abs']<1e-7):failures.append(key)
  rows[key]=row
  for k in grads:arrays[key+'_'+k]=grads[k][j].detach().cpu().numpy()
  arrays[key+'_fused']=fused[j].detach().cpu().numpy()
 path=out/'probe.json';atomic_json(path,{'rows':rows,'adjoint_max_abs_errors':adj_errors,'failures':failures,'independent_original_gate_preserved':{'relative_l2':1e-4,'max_abs':1e-7},'same_forward_graph_no_branch_changes':True,'optimizer_steps':0,'purpose':'diagnostic rounding/conditioning audit, no production or tolerance modification'})
 arr=out/'actual_gradients.npz';np.savez_compressed(arr,**arrays)
 print(json.dumps(json.loads(path.read_text()),indent=2),flush=True)
 assert not failures,failures
 report(c,'checkpoint_diagnostic',[path,arr],{'optimizer_steps':0,'probe':str(path),'independent_sum_failure_not_erased':True})
if __name__=='__main__':main()
