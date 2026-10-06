"""New FP64 replay/adjoint tested against an explicit tiny native matrix."""
import json
import numpy as np
import torch
from runtime import *
from binding import backend
from operators import NativeWeights,query_extension
from certificate import replay

def main():
 guard('new_FP64_certificate_fixture');torch.set_num_threads(2);m=backend();qext=query_extension();eye=torch.eye(4,device='cuda');s=m.GaussianRasterizationSettings(13,13,1.,1.,torch.ones(3,device='cuda'),1.,eye,eye,0,torch.zeros(3,device='cuda'),False,False);xyz=torch.tensor([[0,0,1.],[.16,.08,1.5],[-.12,0,2.]],device='cuda');rot=torch.zeros((3,4),device='cuda');rot[:,0]=1;model=dict(means3D=xyz,means2D=xyz*0,scales=torch.ones_like(xyz)*.25,opacities=torch.tensor([[.4],[.6],[.3]],device='cuda'),rotations=rot,shs=torch.zeros((3,1,3),device='cuda'));op=NativeWeights(m,s,model)
 pixels=torch.tensor([[y,x] for y in range(13) for x in range(13)],device='cuda',dtype=torch.int32);R,_,_,g,b,i=op.state;off,ids,weights,T=[t.cpu().numpy() for t in qext.query(g,b,i,3,R,13,13,pixels)];A=np.zeros((169,3),np.float64)
 for j in range(169):A[j,ids[off[j]:off[j+1]]]=weights[off[j]:off[j+1]]
 x=torch.tensor([.2,.5,.8],device='cuda',dtype=torch.float64);y=torch.linspace(-1,1,169,device='cuda',dtype=torch.float64);ax=replay(op,x,False,qext)[0];aty=replay(op,y,True,qext)[0];forwarderr=float(np.abs(ax.cpu().numpy()-A@x.cpu().numpy()).max());adjerr=float(np.abs(aty.cpu().numpy()-A.T@y.cpu().numpy()).max());assert forwarderr<1e-12 and adjerr<1e-12
 target=np.linspace(0,.5,169);xx=x.cpu().numpy();r=A@xx-target;q=A.T@r;primal=.5*r@r;lower=-.5*r@r-target@r+np.minimum(q,0).sum()
 from scipy.optimize import lsq_linear
 sol=lsq_linear(A,target,bounds=(0,1),tol=1e-12);optimum=.5*np.sum((A@sol.x-target)**2);assert lower<=optimum+1e-12 and optimum<=primal+1e-12
 atomic_json(ART/'tests/FP64_CERTIFICATE.json',dict(passed=True,forward_vs_explicit_CSR_max_abs=forwarderr,adjoint_vs_explicit_CSR_max_abs=adjerr,dual_lower=lower,independent_dense_box_optimum=optimum,feasible_upper=primal,scope='new FP64 accepted-weight operator and Fenchel bound; tiny explicit matrix only'))
 print('FP64_CERTIFICATE_PASS',forwarderr,adjerr,flush=True)
if __name__=='__main__':main()
