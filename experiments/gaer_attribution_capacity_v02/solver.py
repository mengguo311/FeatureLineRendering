"""Feasible monotone FISTA for fixed native linear footprints and box strengths."""
import math,time
import numpy as np
import torch
from runtime import *
from operators import dual_bound

class Pool:
 def __init__(self,ops,fields):
  self.ops=ops;self.n=ops[0].n;self.m=len(ops)*800*800
  self.y=[torch.tensor(a['ink']*a['line_binary'],device='cuda') for a in fields]
  self.constants=sum(float(np.square(a['ink'][~a['line_binary']]).sum(dtype=np.float64)) for a in fields)/(2*self.m)
 def A(self,x):return [o.A(x) for o in self.ops]
 def AT(self,imgs):return sum(o.AT(a) for o,a in zip(self.ops,imgs))
 def objective(self,imgs):return sum(float(((a-y).double()**2).sum()) for a,y in zip(imgs,self.y))/(2*self.m)+self.constants
 def fg(self,x):
  a=self.A(x);g=self.AT([a-y for a,y in zip(a,self.y)])/self.m;return self.objective(a),g,a
 def certificate(self,x,a,g,lip):
  r=[a-y for a,y in zip(a,self.y)];q=g
  raw=(-.5*sum(float((z.double()**2).sum()) for z in r)-sum(float((y.double()*z.double()).sum()) for y,z in zip(self.y,r)))/self.m+float(torch.minimum(q,torch.zeros_like(q)).double().sum())+self.constants
  allowance=3e-5*float(q.abs().double().sum())+1e-8;lower=raw-allowance;f=self.objective(a);gap=max(f-lower,0)
  pg=lip*(x-(x-g/lip).clamp(0,1));norm=float(pg.norm());ref=max(float(g.norm()),1e-12)
  return dict(primal_feasible_objective=f,dual_lower_bound=lower,dual_gap=gap,relative_dual_gap=gap/max(abs(f),1e-12),atomic_allowance=allowance,projected_gradient_norm=norm,projected_gradient_relative=norm/ref,bounds_min=float(x.min()),bounds_max=float(x.max()),active_gt_1e_5=int((x>1e-5).sum()),at_upper_bound=int((x>=1-1e-6).sum()),strength_sum=float(x.double().sum()))

def solve(pool,start,config,label):
 t0=time.perf_counter();x=start.clone();n=pool.n;gen=torch.Generator(device='cuda');gen.manual_seed(20261006);v=torch.rand(n,device='cuda',generator=gen);v/=v.norm()
 for _ in range(config['power_iterations']):
  v=pool.AT(pool.A(v))/pool.m;v/=v.norm().clamp(min=1e-20)
 Lv=pool.AT(pool.A(v))/pool.m;lip=max(float(torch.dot(v,Lv))*1.1,1e-12)
 f,g,a=pool.fg(x);best=x.clone();bestf=f;z=x.clone();tk=1.;log=[];previous=f;limit=config['max_iterations'] if label=='zero' else config['second_start_max_iterations'];status='MAX_ITERATIONS_UNCERTIFIED'
 for it in range(1,limit+1):
  fz,gz,_=pool.fg(z)
  for back in range(config['backtracking_max']):
   candidate=(z-gz/lip).clamp(0,1);imgs=pool.A(candidate);fc=pool.objective(imgs);d=candidate-z
   major=fz+float(torch.dot(gz.double(),d.double()))+.5*lip*float(torch.dot(d.double(),d.double()))
   if fc<=major+1e-10:break
   lip*=config['backtracking_factor']
  else:raise RuntimeError('backtracking failed')
  if fc>f+1e-10:
   z=x.clone();tk=1.;continue
  old=x;x=candidate;f=fc
  if f<bestf:best=x.clone();bestf=f
  tnext=(1+math.sqrt(1+4*tk*tk))/2;z=x+((tk-1)/tnext)*(x-old);tk=tnext
  if it%config['check_every']==0 or it==limit:
   f,g,a=pool.fg(x);cert=pool.certificate(x,a,g,lip);rel=abs(previous-f)/max(abs(previous),1e-12);previous=f
   row=dict(iteration=it,start=label,lipschitz=lip,relative_objective_change=rel,wall_seconds=time.perf_counter()-t0,**cert);log.append(row);print('FIT',label,it,round(f,7),'gap',round(cert['relative_dual_gap'],5),flush=True)
   if it>=config['min_iterations'] and cert['relative_dual_gap']<=config['dual_relative_gap_tolerance']:
    status='NUMERICAL_DUAL_CERTIFIED';break
   if it>=config['min_iterations'] and rel<=config['relative_objective_tolerance'] and cert['projected_gradient_relative']<=config['projected_gradient_relative_tolerance']:
    status='PG_CONVERGED_DUAL_UNCERTIFIED';break
 f,g,a=pool.fg(best);cert=pool.certificate(best,a,g,lip)
 if cert['relative_dual_gap']<=config['dual_relative_gap_tolerance']:status='NUMERICAL_DUAL_CERTIFIED'
 return best,dict(start=label,status=status,iterations=it,seconds=time.perf_counter()-t0,certificate=cert,log=log),a
