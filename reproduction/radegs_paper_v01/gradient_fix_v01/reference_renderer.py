"""Independent float64 Torch reference for the well-conditioned smoke fixture.

Identity camera only; no tile culling. Tests restrict to interior active pixels,
stable order/median and unsaturated alpha. Not a replacement production renderer.
"""
import torch
import torch.nn.functional as F


def reference(p):
    y,x=torch.meshgrid(torch.arange(24,dtype=p['means'].dtype,device=p['means'].device),
                       torch.arange(32,dtype=p['means'].dtype,device=p['means'].device),indexing='ij')
    trans=torch.ones_like(x);median=torch.zeros_like(x);normal=torch.zeros((3,24,32),dtype=x.dtype,device=x.device)
    alpha_list=[];depth_list=[];normal_list=[]
    for i in range(3):
        t=p['means'][i];u,v=t[:2]/t[2];z=t[2];zero=z*0
        q=F.normalize(p['rotations'][i],dim=0);r,a,b,c=q
        rot=torch.stack((1-2*(b*b+c*c),2*(a*b-r*c),2*(a*c+r*b),
                         2*(a*b+r*c),1-2*(a*a+c*c),2*(b*c-r*a),
                         2*(a*c-r*b),2*(b*c+r*a),1-2*(a*a+b*b))).reshape(3,3)
        cov=rot@torch.diag(p['scales'][i]**2)@rot.T
        j=torch.stack((16/z,zero,-16*u/z,zero,12/z,-12*v/z)).reshape(2,3)
        cov2=j@cov@j.T
        det=cov2.det().clamp_min(1e-6)
        coef=torch.sqrt(det/(det+1e-6)+1e-6)  # C24 kernel_size=0
        conic=torch.linalg.inv(cov2)
        d=torch.stack((16*u+15.5-x,12*v+11.5-y),dim=-1)
        power=-.5*torch.einsum('...i,ij,...j->...',d,conic,d)
        alpha=(p['opacity'][i,0]*coef*power.exp()).clamp_max(.99)
        uvh=torch.stack((u,v,z*0+1))
        precision_ray=torch.linalg.solve(cov,uvh)
        # Equivalent to C24 Jn*ray_normal then normalize, on b>0 branch.
        n=-F.normalize(precision_ray,dim=0)
        inv_j=torch.stack((1+v*v,-u*v,-u,-u*v,1+u*u,-v,zero,zero,zero)).reshape(3,3)
        plane=(inv_j@precision_ray)/(precision_ray@uvh)*z/(1+u*u+v*v)
        depth=z+plane[0]*d[:,:,0]/16+plane[1]*d[:,:,1]/12
        active=(alpha>=1/255)&(depth>=.2)&(power<=0)&(trans*(1-alpha)>=.0001)
        alpha=torch.where(active,alpha,zero)
        median=torch.where(active&(trans>.5),depth,median)
        weight=alpha*trans
        normal=normal+weight.unsqueeze(0)*n[:,None,None]
        trans=trans*(1-alpha)
        alpha_list.append(alpha);depth_list.append(depth);normal_list.append(n)
    return {'alpha':(1-trans).unsqueeze(0),'normal':normal,'median':median.unsqueeze(0),
            'single_alpha':torch.stack(alpha_list),'single_depth':torch.stack(depth_list),
            'single_normal':torch.stack(normal_list)}
