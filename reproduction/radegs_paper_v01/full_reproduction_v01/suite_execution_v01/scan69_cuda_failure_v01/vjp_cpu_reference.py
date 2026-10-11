"""Independent one-pixel scalar forward from C24 projection/covariance/filter/RGB blend."""
import json
from pathlib import Path
import torch

def evaluate(dtype):
 means=torch.tensor([.05,.05*32/24,2.],dtype=dtype,requires_grad=True);scales=torch.tensor([.01,.01,.01],dtype=dtype,requires_grad=True);opacity=torch.tensor(.8,dtype=dtype,requires_grad=True)
 x,y,z=means;zero=torch.zeros((),dtype=dtype);J=torch.stack([torch.stack([16/z,zero,-16*x/z**2]),torch.stack([zero,12/z,-12*y/z**2])]);cov=J@torch.diag(scales**2)@J.T;det=cov[0,0]*cov[1,1]-cov[0,1]**2;coef=torch.sqrt(det/(det+1e-6)+1e-6)
 xy=torch.stack([((x/z+1)*32-1)/2,((y/z+1)*24-1)/2]);delta=xy-torch.tensor([16.,12.],dtype=dtype);power=-.5*(delta@torch.linalg.inv(cov)@delta);alpha=opacity*coef*torch.exp(power);assert 1/255<float(alpha)<.99
 rgb=alpha*torch.tensor([.3,.5,.7],dtype=dtype)+(1-alpha)*torch.tensor([.1,.2,.3],dtype=dtype);loss=rgb.sum();g=torch.autograd.grad(loss,(means,scales,opacity));return {'dtype':str(dtype),'cov':cov.detach().tolist(),'det':float(det),'coef':float(coef),'alpha':float(alpha),'loss':float(loss),'means_gradient':g[0].tolist(),'scales_gradient':g[1].tolist(),'opacity_gradient':float(g[2]),'RGB_formula':'alpha*color+(1-alpha)*background; positive support; det>1e-6; no capping branch'}
if __name__=='__main__':
 out=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01/VJP_CPU_REFERENCE.json');r={'reference':[evaluate(torch.float64),evaluate(torch.float32)],'independent_torch_autograd_CPU':True,'original_NaN_cause_claim':False};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
