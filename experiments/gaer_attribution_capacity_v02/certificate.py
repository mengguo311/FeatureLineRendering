"""Independent FP64 Fenchel bound for native accepted FP32 weights."""
import numpy as np
import torch
from operators import query_extension

def replay(op,x,adjoint=False,qext=None):
 qext=qext or query_extension();R,_,_,g,b,i=op.state;s=op.s
 return qext.linear64(g,b,i,op.n,R,s.image_height,s.image_width,x.double().contiguous(),adjoint)

def certify(pool,x):
 qext=query_extension();m=pool.m;q=torch.zeros(pool.n,device='cuda',dtype=torch.float64);absq=q.clone();rawloss=0.;yr=0.;native_errors=[];counts=[];row_error=0.
 for op,y in zip(pool.ops,pool.y):
  ax,_,count=replay(op,x,False,qext);ax=ax.reshape(y.shape);r=ax-y.double();adj,absadj,_=replay(op,r,True,qext);q+=adj/m;absq+=absadj/m;rawloss+=.5*float((r*r).sum())/m;yr+=float((y.double()*r).sum())/m;native_errors.append(float((op.A(x).double()-ax).abs().max()));counts.append(int(count.max()))
 primal=rawloss+pool.constants;dual=-rawloss-yr+float(torch.minimum(q,torch.zeros_like(q)).sum())+pool.constants
 # Each ID gets at most m pixel additions. FP64 positive absolute sums bound
 # signed atomic roundoff. FP64 dot/row accumulation <= maxaccepted additions.
 eps=2**-52;gamma=(m*eps)/(1-m*eps);adjoint_roundoff=gamma*float(absq.sum());rowgamma=max(counts)*eps/(1-max(counts)*eps);scalar_roundoff=gamma*(abs(rawloss)+abs(yr)+float(q.abs().sum())+4)+10*rowgamma
 # Keep the preregistered FP32 allowance as an extra conservative margin.
 preregistered=3e-5*float(q.abs().sum())+1e-8;allowance=adjoint_roundoff+scalar_roundoff+preregistered;lower=dual-allowance;gap=primal-lower
 return dict(primal_feasible_objective=primal,dual_lower_bound=lower,dual_gap=gap,relative_dual_gap=gap/max(abs(primal),1e-20),atomic_allowance=allowance,FP64_atomic_roundoff_bound=adjoint_roundoff,FP64_scalar_roundoff_bound=scalar_roundoff,preregistered_extra_allowance=preregistered,native_vs_FP64_accepted_weight_A_max_abs=native_errors,max_accepted_per_pixel=counts,certified_domain='real linear operator from original forward-accepted FP32 T*alpha; FP64 sums, bounded roundoff; native RGB agreement separately measured',bounds_min=float(x.min()),bounds_max=float(x.max()),active_gt_1e_5=int((x>1e-5).sum()),at_upper_bound=int((x>=1-1e-6).sum()),strength_sum=float(x.double().sum()),status='CERTIFIED_WITH_ROUNDOFF_ALLOWANCE' if gap/max(abs(primal),1e-20)<=.005 else 'MAX_BUDGET_UNCERTIFIED')
