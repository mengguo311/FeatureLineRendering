"""CPU sparse differentiable projected-covariance Gaussian renderer."""
from common import np,core
import torch
torch.set_num_threads(2)
torch.set_num_interop_threads(2)

def tensor(x,like):return torch.as_tensor(np.asarray(x),dtype=like.dtype,device=like.device)
def norm(x):return x/torch.linalg.vector_norm(x,dim=-1,keepdim=True).clamp_min(1e-15)
def derive(control,width,opacity,graph,layout):
    ids,ts,B,D,step=layout
    ix=torch.as_tensor(ids,dtype=torch.long);cc=control[ix];bb=tensor(B,cc);dd=tensor(D,cc)
    means=(bb[:,:,None]*cc).sum(1);tan=norm((dd[:,:,None]*cc).sum(1));pixel=tensor([g['pixel'] for g in graph],cc)[ix]
    normal=tensor([g.get('normal',[0,0,1]) for g in graph],cc)[ix];side=norm(torch.linalg.cross(normal,tan));bad=torch.linalg.vector_norm(side,dim=1)<.1
    axis=torch.eye(3,dtype=cc.dtype)[torch.argmin(abs(tan.detach()),dim=1)];side=torch.where(bad[:,None],norm(torch.linalg.cross(axis,tan)),side);other=norm(torch.linalg.cross(tan,side));F=torch.stack([tan,side,other],-1)
    scales=torch.stack([tensor(step,cc)*.65,width[ix]*pixel,.25*pixel],1)
    cov=(F*scales[:,None,:]**2)@F.transpose(1,2);point=torch.as_tensor([g['type']=='point' for g in graph])[ix]
    cov=torch.where(point[:,None,None],torch.eye(3,dtype=cc.dtype)[None]*(.45*pixel[:,None,None])**2,cov)
    return {'means':means,'covariance':cov,'opacity':opacity[ix]}

def project_torch(a,c):
    x=a['means'];R=tensor(np.asarray(c['extrinsic'])[:3,:3],x);t=tensor(np.asarray(c['extrinsic'])[:3,3],x);p=x@R.T+t;z=p[:,2]
    # Input behind camera is rejected in candidate generation, safe denominator here.
    zz=z.clamp_min(1e-8);uv=torch.stack([c['fx']*p[:,0]/zz+(c['width']-1)/2,c['fy']*p[:,1]/zz+(c['height']-1)/2],1)
    zero=torch.zeros_like(z);J=torch.stack([c['fx']/zz,zero,-c['fx']*p[:,0]/zz**2,zero,c['fy']/zz,-c['fy']*p[:,1]/zz**2],1).reshape(-1,2,3);A=J@R
    S=A@a['covariance']@A.transpose(1,2)+torch.eye(2,dtype=x.dtype)*.12**2
    return uv,z,S

def candidate_pairs(uv,z,S,c,depth=None,alpha=None,window=None):
    u=uv.detach().numpy();zz=z.detach().numpy();ss=S.detach().numpy();h,w=c['height'],c['width'];window=window or [0,0,w,h];x0,y0,x1,y1=window
    r=3*np.sqrt(np.maximum(np.diagonal(ss,axis1=1,axis2=2),0))+1
    ok=np.isfinite(u).all(1)&np.isfinite(r).all(1)&(zz>1e-8)&(u[:,0]+r[:,0]>=x0)&(u[:,0]-r[:,0]<x1)&(u[:,1]+r[:,1]>=y0)&(u[:,1]-r[:,1]<y1)
    ids=np.flatnonzero(ok);lo=np.floor(u[ids]-r[ids]).astype(np.int64);hi=np.ceil(u[ids]+r[ids]).astype(np.int64)
    lo[:,0]=np.clip(lo[:,0],x0,x1);lo[:,1]=np.clip(lo[:,1],y0,y1);hi[:,0]=np.clip(hi[:,0],x0,x1-1);hi[:,1]=np.clip(hi[:,1],y0,y1-1)
    dx=np.maximum(hi[:,0]-lo[:,0]+1,0);dy=np.maximum(hi[:,1]-lo[:,1]+1,0);count=dx*dy
    assert count.sum()<40_000_000,('bounded CPU footprint exceeded',int(count.sum()))
    ix=np.repeat(ids,count);base=np.repeat(np.r_[0,np.cumsum(count[:-1])],count);offset=np.arange(len(ix))-base;nx=np.repeat(dx,count);xx=np.repeat(lo[:,0],count)+offset%np.maximum(nx,1);yy=np.repeat(lo[:,1],count)+offset//np.maximum(nx,1)
    # Remove guaranteed-zero pairs before autograd. The ACTUAL Gaussian cutoff
    # remains q<=9 in render_sparse. The .001 guard retains floating-boundary
    # candidates; it does not alter opacity, thickness, or final support.
    dxp=xx-u[ix,0];dyp=yy-u[ix,1];a=ss[ix,0,0];b=ss[ix,0,1];d=ss[ix,1,1]
    q=(dxp*dxp*d-2*dxp*dyp*b+dyp*dyp*a)/np.maximum(a*d-b*b,1e-30);keep=q<=9.001
    ix,xx,yy=ix[keep],xx[keep],yy[keep]
    if depth is not None:
        d=depth[yy,xx];al=alpha[yy,xx];known=np.isfinite(d)&(d>0)&np.isfinite(al)&(al>=.5);hide=known&(zz[ix]>d+np.maximum(.005*d,2*d/np.sqrt(c['fx']*c['fy'])))
        ix,xx,yy=ix[~hide],xx[~hide],yy[~hide]
    return ix,xx,yy

def render_sparse(a,c,depth=None,alpha=None,window=None):
    uv,z,S=project_torch(a,c);ids,x,y=candidate_pairs(uv,z,S,c,depth,alpha,window);window=window or [0,0,c['width'],c['height']];x0,y0,x1,y1=window;h=y1-y0;w=x1-x0
    if len(ids)==0:return torch.zeros((h,w),dtype=uv.dtype)+a['means'].sum()*0
    ix=torch.as_tensor(ids,dtype=torch.long);d=tensor(np.stack([x,y],1),uv)-uv[ix];s=S[ix];det=s[:,0,0]*s[:,1,1]-s[:,0,1]**2
    q=(d[:,0]**2*s[:,1,1]-2*d[:,0]*d[:,1]*s[:,0,1]+d[:,1]**2*s[:,0,0])/det.clamp_min(1e-30)
    g=torch.where(q<=9,torch.exp(-q*.5),torch.zeros_like(q));aij=(a['opacity'][ix]*g).clamp(0,.999)
    pixels=torch.as_tensor((y-y0)*w+x-x0,dtype=torch.long);logT=torch.zeros(h*w,dtype=uv.dtype).scatter_add(0,pixels,torch.log1p(-aij));return -torch.expm1(logT.reshape(h,w))

def class_loss(rendered,target,known):
    pos=target>.2;neg=(target<.05)&known;mid=(target>=.05)&(target<=.2)&known;err=(rendered-target)**2
    return sum(weight*(err[m].mean() if m.any() else err.sum()*0) for m,weight in [(pos,1),(neg,1),(mid,.2)])
