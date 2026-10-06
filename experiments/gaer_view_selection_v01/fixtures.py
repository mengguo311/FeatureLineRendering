"""Small fixtures: independent CPU rays, constant coplanar grid, texture-only color changes."""
import numpy as np
import torch

def settings(m,h=9,w=9):
    eye=torch.eye(4,device='cuda')
    return m.GaussianRasterizationSettings(h,w,1.,1.,torch.zeros(3,device='cuda'),
        1.,eye,eye,0,torch.zeros(3,device='cuda'),False,False)

def cpu_ray_fixture(m):
    z=np.array([.7,1.1,1.4,1.9,2.1,2.3,2.5,2.7,3,3.1,3.2,3.3],np.float32)
    xyz=np.zeros((len(z),3),np.float32);xyz[:,2]=z
    rot=np.zeros((len(z),4),np.float32);rot[:,0]=1
    f=dict(means3D=xyz,means2D=xyz*0,opacities=np.full((len(z),1),.21,np.float32),
           scales=np.repeat((z*.65)[:,None],3,1),rotations=rot,colors_precomp=np.ones((len(z),3),np.float32))
    return {k:torch.tensor(v,device='cuda') for k,v in f.items()},settings(m)

def cpu_weights(f,s):
    # Identity camera/projection, centered isotropic splats. All radii cover the
    # tiny single tile; analytic covariance J*Sigma*J^T + .3I, no proxy depth.
    xyz=f['means3D'].cpu().numpy(); scales=f['scales'].cpu().numpy(); opacity=f['opacities'].cpu().numpy()[:,0]
    h,w=s.image_height,s.image_width; result=np.zeros((h,w,len(xyz)),np.float64)
    for y in range(h):
        for x in range(w):
            T=1.
            for i in np.argsort(xyz[:,2],kind='stable'):
                z=float(xyz[i,2]);var=(w/2*float(scales[i,0])/z)**2+.3
                power=-.5*((x-(w-1)/2)**2+(y-(h-1)/2)**2)/var
                a=min(.99,float(opacity[i])*np.exp(power))
                if a<1/255: continue
                nxt=T*(1-a)
                if nxt<.0001: break
                result[y,x,i]=T*a;T=nxt
    return result

def flat_fixture(m,textured=False):
    x,y=np.meshgrid(np.linspace(-.65,.65,9),np.linspace(-.65,.65,9));n=x.size
    xyz=np.column_stack([x.ravel(),y.ravel(),np.ones(n)])
    rot=np.zeros((n,4));rot[:,0]=1
    color=np.full((n,3),.5)
    if textured: color[:,:]=np.where(x.ravel()[:,None]<0,.05,.95)
    f=dict(means3D=xyz,means2D=xyz*0,opacities=np.full((n,1),.7),
        scales=np.full((n,3),.10),rotations=rot,colors_precomp=color)
    truth=dict(type='analytic coplanar z=1 square patch',interior_geometry_edges=0,
               texture_step_x=0,foreground_half_extent=.65,
               boundary_truth='independent square signed distance; no interior depth/normal discontinuity')
    return {k:torch.tensor(v,dtype=torch.float32,device='cuda') for k,v in f.items()},settings(m,65,65),truth
