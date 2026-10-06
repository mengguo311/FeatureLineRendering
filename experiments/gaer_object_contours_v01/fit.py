"""Box-constrained native joint fit; alpha evidence is an online automatic target."""
import math,time
import numpy as np
import torch
from adapter import query_extension

def certificate(op,x,L,q,allowed):
 R,_,_,geom,binning,img=op.state;s=op.s;ext=query_extension();m=L.numel();a,_,counts=ext.linear64(geom,binning,img,op.n,R,800,800,x.double().contiguous(),False);a=a.reshape(L.shape);r=a-L.double();qr=q.double()*r;g,absg,_=ext.linear64(geom,binning,img,op.n,R,800,800,qr.flatten().contiguous(),True);g/=m;absg/=m
 f=.5*float((q.double()*r*r).sum())/m;dual=-f-float((q.double()*L.double()*r).sum())/m+float(torch.minimum(g[allowed],torch.zeros_like(g[allowed])).sum());eps=2**-52;gamma=m*eps/(1-m*eps);count=int(counts.max());rowgamma=count*eps/(1-count*eps);allowance=gamma*float(absg.sum())+gamma*(abs(f)+abs(dual)+4)+10*rowgamma+3e-5*float(g[allowed].abs().sum())+1e-8;lower=dual-allowance;gap=f-lower
 return dict(primal=f,dual_lower=lower,relative_dual_gap=gap/max(abs(f),1e-20),roundoff_allowance=allowance,max_accepted_per_pixel=count,native_A_FP64_max_error=float((op.A(x).double()-a).abs().max()),status='CERTIFIED_WITH_ROUNDOFF_ALLOWANCE' if gap/max(abs(f),1e-20)<=.005 else 'MAX_BUDGET_UNCERTIFIED')

def solve(op,e,allowed,config,label):
 t0=time.perf_counter();L=torch.as_tensor(e['target'],device='cuda');q=torch.as_tensor(e['q'],device='cuda');alpha=op.A(torch.ones(op.n,device='cuda'));m=L.numel();d=op.AT(q*alpha).clamp(min=1e-12);allowed=allowed.bool();x=torch.zeros(op.n,device='cuda');z=x.clone();tk=1.;scale=1.0001;logs=[];previous=None;status='MAX_ITERATIONS_UNCERTIFIED';restarts=0
 def obj(a):return .5*float((q.double()*(a.double()-L.double())**2).sum())/m
 f=obj(op.A(x));best=x.clone();bestf=f
 for it in range(1,config['maximum_iterations']+1):
  az=op.A(z);fz=obj(az);g=op.AT(q*(az-L));
  for back in range(config['backtracking_max']):
   candidate=(z-g/(scale*d)).clamp(0,1)*allowed;a=op.A(candidate);fc=obj(a);delta=candidate-z;major=fz+(float((g.double()*delta.double()).sum())+.5*scale*float((d.double()*delta.double()**2).sum()))/m
   if fc<=major+1e-10:break
   scale*=config['backtracking_factor']
  else:raise RuntimeError('native majorization/backtracking failure')
  if fc>f+1e-10:
   restarts+=1;z=x.clone();tk=1.;az=op.A(z);g=op.AT(q*(az-L));candidate=(z-g/(scale*d)).clamp(0,1)*allowed;a=op.A(candidate);fc=obj(a)
  old=x;x=candidate;f=fc
  if f<bestf:best=x.clone();bestf=f
  tnext=(1+math.sqrt(1+4*tk*tk))/2;z=x+((tk-1)/tnext)*(x-old);tk=tnext
  if it%config['check_every']==0 or it==config['maximum_iterations']:
   a=op.A(x);r=a-L;g=op.AT(q*r)/m;dual=-obj(a)-float((q.double()*L.double()*r.double()).sum())/m+float(torch.minimum(g[allowed],torch.zeros_like(g[allowed])).double().sum());allowance=3e-5*float(g[allowed].abs().double().sum())+1e-8;gap=(f-dual+allowance)/max(abs(f),1e-20);rel=abs(f-previous)/max(abs(previous),1e-20) if previous is not None else 1.;previous=f;pg=(x-(x-g*m/(scale*d)).clamp(0,1)*allowed)*d/m;pgrel=float(pg.norm())/max(float(g[allowed].norm()),1e-20)
   logs.append(dict(iteration=it,objective=f,estimated_relative_dual_gap=gap,relative_objective_change=rel,projected_gradient_relative=pgrel,diagonal_scale=scale,restarts=restarts,seconds=time.perf_counter()-t0));print('FIT',label,'budget',config['maximum_iterations'],'iteration',it,'loss',round(f,8),'gap',round(gap,6),'seconds',round(time.perf_counter()-t0,2),flush=True)
   if it>=config['minimum_iterations'] and gap<=config['relative_dual_gap_tolerance']:status='NUMERICAL_DUAL_ESTIMATE_CONVERGED';break
   if it>=config['minimum_iterations'] and rel<=config['relative_objective_tolerance'] and pgrel<=config['projected_gradient_relative_tolerance']:status='PG_CONVERGED_UNCERTIFIED';break
 cert=certificate(op,best,L,q,allowed)
 return best,dict(label=label,iterations=it,maximum_iterations=config['maximum_iterations'],start='zero',warm_start=False,seconds=time.perf_counter()-t0,status=cert['status'],optimization_status=status,certificate=cert,log=logs,allowed_ids=int(allowed.sum()),active_ids=int((best>1e-5).sum()),strength_sum=float(best.double().sum()),at_upper_bound=int((best>=1-1e-6).sum()),bound_min=float(best.min()),bound_max=float(best.max()))
