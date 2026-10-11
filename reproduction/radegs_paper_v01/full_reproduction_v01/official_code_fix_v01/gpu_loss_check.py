"""Gated GPU test of literal C24 loss semantics with independent double VJP/FD."""
import argparse,json,math
from pathlib import Path
from types import SimpleNamespace
import torch
from gpu_smoke import fixture,render,assert_close
from reference_renderer import reference
from probe_eq24 import branch
from loss_reference import mapped_pairs,normal_consistency
from masked_division import distortion_quotient,expected_depth_quotient
from utils.graphics_utils import depth_double_to_normal

def ref_losses(q,frozen_weights=None,frozen_denom=None):
 r=reference(q);a=r['single_alpha'];trans=torch.ones_like(a[0]);w=[]
 for aa in a:w.append(trans*aa);trans=trans*(1-aa)
 w=torch.stack(w);expected=(w*r['single_depth']).sum(0,keepdim=True)/r['alpha'].clamp_min(1e-30)
 sl=(slice(None),slice(11,13),slice(15,17));weights=w[sl] if frozen_weights is None else frozen_weights
 denom=r['alpha'][sl].square().detach() if frozen_denom is None else frozen_denom
 d=(mapped_pairs(r['single_depth'][sl],weights)/denom[0]).mean()
 n=normal_consistency(r['normal'],expected,r['median'],16.,12.)[11:13,15:17].mean()
 return {'distortion':d,'normal':n},w[sl].detach(),denom

def native_losses(p):
 o=render(p);d=distortion_quotient(o[6],o[4])[:,11:13,15:17].mean()
 cam=SimpleNamespace(image_width=32,image_height=24,FoVx=math.pi/2,FoVy=math.pi/2)
 nd,_=depth_double_to_normal(cam,expected_depth_quotient(o[2],o[4]),o[3]);n=torch.nn.functional.normalize(o[5],dim=0).permute(1,2,0)
 e=1-(n[None]*nd).sum(-1);nl=(.4*e[0]+.6*e[1])[11:13,15:17].mean()
 return {'distortion':d,'normal':nl},o

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args();torch.backends.cuda.matmul.allow_tf32=False
 p=fixture();q={k:v.detach().cpu().double().requires_grad_() for k,v in p.items()};native,o=native_losses(p);ref,w,den=ref_losses(q);keys=tuple(p);records=[];passed=True
 for name in native:
  gn=torch.autograd.grad(native[name],tuple(p.values()),retain_graph=True);g2=torch.autograd.grad(2*native[name],tuple(p.values()),retain_graph=True);gr=torch.autograd.grad(ref[name],tuple(q.values()),allow_unused=True,retain_graph=True)
  for key,a,b,c in zip(keys,gn,gr,g2):
   b=torch.zeros_like(q[key]) if b is None else b
   for i in range(a.numel()):
    av=float(a.flatten()[i]);bv=float(b.flatten()[i]);cv=float(c.flatten()[i]);sweep=[]
    for eps in (1e-3,3e-4,1e-4):
     vals=[]
     for sign in (-1,1):
      pp={k:v.detach().clone() for k,v in q.items()};pp[key].flatten()[i]+=sign*eps
      vals.append(float(ref_losses(pp,w,den)[0][name]))
     sweep.append({'eps':eps,'losses':vals,'fd':(vals[1]-vals[0])/(2*eps)})
    fd=sweep[1]['fd'];ok=abs(av-bv)<=2e-5+2e-3*abs(bv) and abs(cv-2*av)<=1e-6+2e-4*abs(2*av) and abs(bv-fd)<=2e-5+2e-3*abs(fd)
    passed &= ok;records.append({'loss':name,'input':key,'index':i,'analytic':av,'reference':bv,'linear_vjp2':cv,'sweep':sweep,'passed':ok})
 # Zero-support helper is checked by an actual GPU graph, plus its positive branch CPU proof.
 z=torch.tensor([0.,.5],device='cuda',requires_grad=True);s=torch.tensor([0.,1.],device='cuda',requires_grad=True);d=torch.tensor([0.,.03],device='cuda',requires_grad=True)
 zero=expected_depth_quotient(s,z).sum()+distortion_quotient(d,z).sum();zg=torch.autograd.grad(zero,(s,z,d));zero_ok=all(torch.isfinite(x).all() for x in zg)
 center=branch(p);branches=[]
 for key in ('means','scales','rotations','opacity'):
  for i in range(p[key].numel()):
   for sign in (-1,1):
    pp={k:v.detach().clone() for k,v in p.items()};pp[key].flatten()[i]+=sign*.001;b=branch(pp)
    ok=b['median_ids']==center['median_ids'] and b['sort_order']==center['sort_order'] and b['alpha_min']>.02 and b['T_half_margin']>.005
    passed &= ok;branches.append({'key':key,'index':i,'sign':sign,'passed':ok,**b})
 forward={k:{'native':float(native[k]),'reference':float(ref[k])} for k in native}
 for k,v in forward.items():passed &= abs(v['native']-v['reference'])<=8e-6+3e-4*abs(v['reference'])
 result={'status':'PASS' if passed and zero_ok else 'FAIL','method':'C24 original losses + zero-support guard','native_forward':forward,'checks':records,'zero_support_cuda_gradients':[x.cpu().tolist() for x in zg],'branches':branches,'scope':'three well-conditioned Gaussians; stable sorting/median/alpha support; RGB edge held fixed at 1 in fixture; actual scene edge tested separately','distortion_weight_gradients':'detached native alphaT and Python alpha^2; no M-count division','normal':'normalized blended, expected .4 and median .6'}
 Path(args.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'forward':forward,'failed':[(x['loss'],x['input'],x['index'],x['analytic'],x['reference']) for x in records if not x['passed']]}),flush=True)
 if result['status']!='PASS':raise AssertionError('official loss gate failed; full scalar evidence retained')
if __name__=='__main__':main()
