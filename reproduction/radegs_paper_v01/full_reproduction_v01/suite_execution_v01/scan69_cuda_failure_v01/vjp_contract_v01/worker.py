"""Finite-support RGB VJP linearity and independent FD: no optimizer or dataset use."""
import argparse,json,os,sys,time
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();c=json.loads(Path(args.config).read_text());assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 import torch,diff_gaussian_rasterization as raster
 from gpu_smoke import render
 from safety import atomic_json,sha256
 torch.backends.cuda.matmul.allow_tf32=False
 values={'means':[[.05,.05*32/24,2.]],'scales':[[.01,.01,.01]],'rotations':[[1.,0.,0.,0.]],'opacity':[[.8]],'colors':[[.3,.5,.7]]}
 def fixture():return {k:torch.tensor(v,dtype=torch.float32,device='cuda',requires_grad=True) for k,v in values.items()}
 def execute(mult):
  p=fixture();out=render(p);loss=out[0][:,12,16].sum()*mult;grads=torch.autograd.grad(loss,tuple(p.values()));return out,{k:v.detach() for k,v in zip(p,grads)}
 out,g=execute(1.);_,g2=execute(2.);alpha_mask=out[4]>0;assert int(alpha_mask.sum())>0
 rows=[];branch=[]
 for eps in [1e-4,3e-5,1e-5,3e-6]:
  losses=[]
  for sign in [-1,1]:
   pp={k:v.detach().clone() for k,v in fixture().items()};pp['scales'][0,0]+=sign*eps;o=render(pp);losses.append(float(o[0][:,12,16].sum()));same=bool(torch.equal(o[4]>0,alpha_mask) and torch.equal(o[1],out[1]));branch.append({'eps':eps,'sign':sign,'same_alpha_support_and_radius':same})
  rows.append({'eps':eps,'fd':(losses[1]-losses[0])/(2*eps),'analytic':float(g['scales'][0,0]),'loss_minus':losses[0],'loss_plus':losses[1]})
 checks={k:bool(torch.isfinite(g[k]).all() and torch.allclose(g2[k],2*g[k],rtol=2e-4,atol=1e-5)) for k in g}
 valid_branch=all(x['same_alpha_support_and_radius'] for x in branch)
 fd=rows[1]['fd'];analytic=rows[1]['analytic'];fdpass=abs(analytic-fd)<=1e-3+1e-3*abs(fd)
 result={'fixture':values,'native':raster._C.__file__,'native_sha256':sha256(raster._C.__file__),'VJP_linearity_checks':checks,'VJP1':{k:v.cpu().tolist() for k,v in g.items()},'VJP2':{k:v.cpu().tolist() for k,v in g2.items()},'fd_sweep':rows,'branch_checks':branch,'alpha_pixels':int(alpha_mask.sum()),'radius':out[1].cpu().tolist(),'fixed_tolerances':{'linearity_rtol':2e-4,'linearity_atol':1e-5,'FD_rtol':1e-3,'FD_atol':1e-3},'valid_smooth_fixture':valid_branch,'FD_check':fdpass,'original_scan69_NaN_root_cause_proven':False,'scientificdone':False}
 outdir=Path(c['diagnostic_output'])/os.environ['RADEGS_ATTEMPT'];outdir.mkdir(parents=True,exist_ok=False);rf=outdir/'result.json';atomic_json(rf,result);print(json.dumps(result,indent=2),flush=True)
 passed=all(checks.values()) and valid_branch and fdpass
 atomic_json(c['reports']['smoke'],{'status':'PASS' if passed else 'FAIL','stage':'smoke','attempt':os.environ['RADEGS_ATTEMPT'],'inputs':c['inputs'],'outputs':{str(rf):sha256(rf)},'details':{'diagnostic_only':True,'actual_training_success':False,'result':str(rf)},'unix':time.time(),'scientificdone':False})
 if not passed:raise AssertionError('RGB VJP linearity/FD/support gate failed; see saved actual scalars')
if __name__=='__main__':main()
