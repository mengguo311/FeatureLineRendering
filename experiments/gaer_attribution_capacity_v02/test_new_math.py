"""Only new operator/diagnostic math: adjoint, white ink, dual and cancellation."""
import itertools,json
import numpy as np
import torch
from runtime import *
from binding import backend
from operators import NativeWeights

def main():
 guard('new_math');torch.set_num_threads(2);m=backend();eye=torch.eye(4,device='cuda');s=m.GaussianRasterizationSettings(13,13,1.,1.,torch.ones(3,device='cuda'),1.,eye,eye,0,torch.zeros(3,device='cuda'),False,False)
 xyz=torch.tensor([[0,0,1.],[.16,.08,1.5],[-.12,0,2.]],device='cuda');rot=torch.zeros((3,4),device='cuda');rot[:,0]=1;model=dict(means3D=xyz,means2D=xyz*0,scales=torch.ones_like(xyz)*.25,opacities=torch.tensor([[.4],[.6],[.3]],device='cuda'),rotations=rot,shs=torch.zeros((3,1,3),device='cuda'));op=NativeWeights(m,s,model)
 gen=torch.Generator(device='cuda');gen.manual_seed(19);x=torch.rand(3,device='cuda',generator=gen);y=torch.randn((13,13),device='cuda',generator=gen);ax=op.A(x);aty=op.AT(y);lhs=float((ax.double()*y.double()).sum());rhs=float((x.double()*aty.double()).sum());adj=abs(lhs-rhs)/max(abs(lhs),abs(rhs),1e-12);formula=float((op.ink_rgb(x)-(1-ax)[None]).abs().max());assert adj<3e-5 and formula<3e-6
 # Independent exact dense box optimum enumeration for diagonal fixture and dual.
 A=np.array([[1.,.2],[.1,.9],[.4,.3]]);target=np.array([.7,.4,.2]);grid=np.array(list(itertools.product(np.linspace(0,1,501),repeat=2)));loss=.5*((grid@A.T-target)**2).sum(1);best=loss.min();feasible=np.array([.2,.8]);r=A@feasible-target;q=A.T@r;dual=-.5*r@r-target@r+np.minimum(q,0).sum();primal=.5*r@r;assert dual<=best+1e-12 and best<=primal
 # Equal IDs/weights, no RGB edge with equal foreground/background color,
 # or full-opacity complementary weights: D remains large and cannot cancel.
 dw=np.array([.5,-.5]);same=np.array([[.5,.5,.5],[.5,.5,.5]]);different=np.array([[0.,0,0],[1.,1,1]]);assert np.linalg.norm(dw@same)==0 and np.abs(dw).sum()==1 and np.linalg.norm(dw@different)>0
 # Explicit BG term for changing total alpha.
 dw2=np.array([.2,-.1]);dt=-dw2.sum();delta=dw2@same+dt*np.ones(3);assert np.allclose(delta,dw2@(same-1))
 rec=dict(passed=True,adjoint_relative_error=adj,white_ink_formula_max_abs=formula,dual_fixture=dict(lower=dual,grid_optimum_upper=best,feasible_upper=primal),analytic=dict(equal_colors_RGB_delta=(dw@same).tolist(),different_colors_RGB_delta=(dw@different).tolist(),sum_abs_D=float(np.abs(dw).sum()),background_required=True),scope='new math only; no old interface/full-buffer/vote campaign')
 atomic_json(ART/'tests/NEW_MATH.json',rec);print(json.dumps(rec))
if __name__=='__main__':main()
