"""Independent RGB finite differences for every affected input on two fixed smooth fixtures."""
import argparse,json
from pathlib import Path
import torch
from gpu_smoke import render

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args();torch.backends.cuda.matmul.allow_tf32=False
 fixtures=[{'name':'thin_isotropic','means':[[.05,.05*32/24,2.]],'scales':[[.01,.01,.01]],'rotations':[[1.,0.,0.,0.]],'opacity':[[.8]],'colors':[[.3,.5,.7]]},{'name':'thin_anisotropic_rotated','means':[[.05,.05*32/24,2.]],'scales':[[.018,.014,.011]],'rotations':[[.98,.06,-.04,.1]],'opacity':[[.8]],'colors':[[.3,.5,.7]]}]
 rows=[];all_pass=True
 for f in fixtures:
  p={k:torch.tensor(v,dtype=torch.float32,device='cuda',requires_grad=True) for k,v in f.items() if k!='name'};out=render(p);loss=out[0][:,12,16].sum();g=torch.autograd.grad(loss,tuple(p.values()));mask=out[4]>0
  for (key,v),gradient in zip(p.items(),g):
   epss=[1e-4,3e-5,1e-5] if key=='scales' else [1e-3,3e-4,1e-4] if key=='means' else [3e-3,1e-3,3e-4]
   for i in range(v.numel()):
    sweep=[]
    for eps in epss:
     ls=[];stable=True
     for sign in [-1,1]:
      pp={k:x.detach().clone() for k,x in p.items()};pp[key].view(-1)[i]+=sign*eps;o=render(pp);ls.append(float(o[0][:,12,16].sum()));stable &= bool(torch.equal(o[4]>0,mask) and torch.equal(o[1],out[1]))
     sweep.append({'eps':eps,'fd':(ls[1]-ls[0])/(2*eps),'stable_support_radius':stable})
    analytic=float(gradient.view(-1)[i]);fd=sweep[1]['fd'];passed=all(x['stable_support_radius'] for x in sweep) and abs(analytic-fd)<=3e-4+1e-3*abs(fd);all_pass &= passed;rows.append({'fixture':f['name'],'key':key,'index':i,'analytic':analytic,'sweep':sweep,'absolute_error_at_middle_eps':abs(analytic-fd),'passed':passed})
 result={'passed':all_pass,'fixtures':fixtures,'checks':rows,'tolerances_fixed_before_run':{'rtol':1e-3,'atol':3e-4},'sorting':'one Gaussian; no order switches','alpha':'all perturbations require unchanged positive support and radius','scientificdone':False};Path(args.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':all_pass,'checks':len(rows),'max_absolute_error':max(r['absolute_error_at_middle_eps'] for r in rows)}),flush=True)
 if not all_pass:raise AssertionError('expanded FD failed; saved all measurements, no tolerance fallback')
if __name__=='__main__':main()
