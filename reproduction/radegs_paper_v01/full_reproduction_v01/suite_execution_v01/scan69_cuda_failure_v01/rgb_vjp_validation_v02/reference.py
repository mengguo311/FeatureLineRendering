"""CPU float64 differentiable scalar C24 forward, independent of native backward.

Identity camera, one Gaussian, interior unclamped FoV. Includes C24 det cutoff,
normalized quaternion, projection's 1e-7, alpha cutoff/cap. No depth loss here.
"""
import torch

FIXTURES=[
 {'name':'thin_isotropic','means':[[.05,.05*32/24,2.]],'scales':[[.01,.01,.01]],'rotations':[[1.,0.,0.,0.]],'opacity':[[.8]],'colors':[[.3,.5,.7]]},
 {'name':'thin_anisotropic_rotated','means':[[.05,.05*32/24,2.]],'scales':[[.018,.014,.011]],'rotations':[[.98,.06,-.04,.1]],'opacity':[[.8]],'colors':[[.3,.5,.7]]},
 {'name':'below_det_cutoff','means':[[.0625,1/12,2.]],'scales':[[.004,.004,.004]],'rotations':[[1.,0.,0.,0.]],'opacity':[[.8]],'colors':[[.3,.5,.7]]},
]

def parameters(f,dtype=torch.float64):
    return {k:torch.tensor(v,dtype=dtype,requires_grad=True) for k,v in f.items() if k!='name'}

def pixel(p,objective='rgb'):
    x,y,z=p['means'][0];zero=z*0
    q=torch.nn.functional.normalize(p['rotations'][0],dim=0);r,a,b,c=q
    R=torch.stack([1-2*(b*b+c*c),2*(a*b-r*c),2*(a*c+r*b),
                   2*(a*b+r*c),1-2*(a*a+c*c),2*(b*c-r*a),
                   2*(a*c-r*b),2*(b*c+r*a),1-2*(a*a+b*b)]).reshape(3,3)
    cov3=R@torch.diag(p['scales'][0]**2)@R.T
    J=torch.stack([16/z,zero,-16*x/z**2,zero,12/z,-12*y/z**2]).reshape(2,3)
    cov=J@cov3@J.T;det=cov[0,0]*cov[1,1]-cov[0,1]**2
    # forward.cu 265..270 zeros coef at/below det cutoff; not sqrt(1/2).
    clamped=det.clamp_min(1e-6)
    coef=torch.where(det>1e-6,torch.sqrt(clamped/(clamped+1e-6)+1e-6),zero)
    reciprocal=1/(z+1e-7)
    xy=torch.stack([((x*reciprocal+1)*32-1)/2,((y*reciprocal+1)*24-1)/2])
    delta=xy-torch.tensor([16.,12.],dtype=x.dtype)
    power=-.5*(delta@torch.linalg.inv(cov)@delta)
    alpha=(p['opacity'][0,0]*coef*torch.exp(power)).clamp_max(.99)
    alpha=torch.where((alpha>=1/255)&(power<=0),alpha,zero)
    bg=torch.tensor([.1,.2,.3],dtype=x.dtype)
    rgb=alpha*p['colors'][0]+(1-alpha)*bg
    loss=rgb.sum() if objective=='rgb' else alpha+rgb.sum()*0
    return loss,{'det':float(det.detach()),'condition':float(torch.linalg.cond(cov).detach()),'coef':float(coef.detach()),'alpha':float(alpha.detach()),'power':float(power.detach()),'xy':xy.detach().tolist()}
