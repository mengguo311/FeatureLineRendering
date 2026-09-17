"""Reusable Gaussian-disc raster state, extracted from poster_repro's fragment logic.

This is a full-K diagnostic proxy, NOT the official anisotropic CUDA rasterizer.
All statistics share the same front-to-back fragments. IDs always address original
PLY rows. No image, mesh or dataset IO. Historical render_gbuffer stays unchanged.
"""
import cv2
import numpy as np
import torch


def remap_ids(keep_mask, frustum_mask, bucket_mask, local_index):
    return np.flatnonzero(keep_mask)[np.asarray(frustum_mask)][np.asarray(bucket_mask)][local_index]


def fragment_topk(pix, weights, ids, n_pixels, k):
    """Stable per-pixel top-k by contribution, with original ID as tie breaker."""
    order=torch.argsort(ids,stable=True)
    order=order[torch.argsort(-weights[order],stable=True)]
    order=order[torch.argsort(pix[order],stable=True)]
    p,w,g=pix[order],weights[order],ids[order]
    outid=torch.full((n_pixels*k,),-1,device=p.device,dtype=torch.int64)
    outw=torch.zeros(n_pixels*k,device=p.device,dtype=weights.dtype)
    if len(p):
        start=torch.ones_like(p,dtype=torch.bool);start[1:]=p[1:]!=p[:-1]
        sid=start.long().cumsum(0)-1;ar=torch.arange(len(p),device=p.device)
        rank=ar-ar[start][sid];ok=(rank<k)&(w>1e-12)
        dst=p[ok]*k+rank[ok];outid[dst]=g[ok];outw[dst]=w[ok]
    outw=outw.reshape(n_pixels,k);mass=outw.sum(-1)
    return outid.reshape(n_pixels,k),outw/mass[:,None].clamp(min=1e-12),mass


def render_state(g,keep_mask,cam,device='cuda',K=8,r_min=1.,r_max=15.,frag_alpha_min=.01):
    dev=torch.device(device);H,W=cam.H,cam.W;P=H*W
    gids=np.flatnonzero(keep_mask);mu=g['mu'][gids];n=g['normal'][gids].copy()
    n[np.sum(n*(cam.center-mu),axis=1)<0]*=-1
    xyz=torch.as_tensor(mu,dtype=torch.float32,device=dev)
    w2c=torch.as_tensor(cam.w2c,dtype=torch.float32,device=dev)
    xyz=xyz@w2c[:3,:3].T+w2c[:3,3];z=xyz[:,2]
    intr=torch.as_tensor(cam.K,dtype=torch.float32,device=dev);h=xyz@intr.T
    uv=h[:,:2]/h[:,2:].clamp(min=1e-6);u,v=uv.T
    radius=(torch.as_tensor(g['scale_max'][gids],device=dev,dtype=torch.float32)*float(cam.K[0,0])/z.clamp(min=1e-6)).clamp(r_min,r_max)
    ok=(z>.01)&(u>-radius)&(u<W-1+radius)&(v>-radius)&(v<H-1+radius)
    u,v,z,radius=u[ok],v[ok],z[ok],radius[ok]
    opa=torch.as_tensor(g['opacity'][gids],device=dev,dtype=torch.float32)[ok]
    normals=torch.as_tensor(n,device=dev,dtype=torch.float32)[ok]
    color=torch.as_tensor(g['albedo'][gids],device=dev,dtype=torch.float32)[ok]
    ids=torch.as_tensor(gids,device=dev,dtype=torch.int64)[ok]
    ri=radius.ceil().long().clamp(1,int(r_max));pieces=[]
    for R in torch.unique(ri).tolist():
        b=ri==R;us,vs,rs=u[b],v[b],radius[b]
        off=torch.arange(-R,R+1,device=dev);dx,dy=torch.meshgrid(off,off,indexing='xy')
        px=us.round()[:,None]+dx.flatten();py=vs.round()[:,None]+dy.flatten()
        d2=(px-us[:,None])**2+(py-vs[:,None])**2
        alpha=opa[b,None]*torch.exp(-.5*d2/(rs[:,None]/2).square().clamp(min=.25))
        hit=(d2<=(rs[:,None]+.5)**2)&(alpha>frag_alpha_min)&(px>=0)&(px<W)&(py>=0)&(py<H)
        gi,pi=hit.nonzero(as_tuple=True)
        if len(gi):pieces.append(((py[gi,pi].long()*W+px[gi,pi].long()),z[b][gi],alpha[gi,pi],ids[b][gi],normals[b][gi],color[b][gi]))
    zero=lambda *shape:torch.zeros(shape,device=dev)
    if not pieces:
        return dict(depth= torch.full((H,W),float('inf'),device=dev),depth_median=torch.full((H,W),float('inf'),device=dev),
            normal=zero(H,W,3),alpha=zero(H,W),albedo=zero(H,W,3),topk_id=torch.full((H,W,K),-1,device=dev,dtype=torch.int64),
            topk_w=zero(H,W,K),topk_mass=zero(H,W),entropy=zero(H,W),margin=zero(H,W),depth_variance=zero(H,W),normal_dispersion=zero(H,W),coverage=zero(H,W).bool(),n_frag=0)
    pix,fz,fa,fg,fn,fc=[torch.cat([p[j] for p in pieces]) for j in range(6)];del pieces
    order=torch.argsort(fz,stable=True);order=order[torch.argsort(pix[order],stable=True)]
    pix,fz,fa,fg,fn,fc=[a[order] for a in (pix,fz,fa,fg,fn,fc)]
    fa=fa.double().clamp(max=.999)
    start=torch.ones_like(pix,dtype=torch.bool);start[1:]=pix[1:]!=pix[:-1]
    sid=start.long().cumsum(0)-1
    log=torch.log1p(-fa);ex=log.cumsum(0)-log;T=torch.exp(ex-ex[start][sid]);w=T*fa
    def accumulate(x):
        a=torch.zeros((P,)+x.shape[1:],dtype=torch.float64,device=dev)
        return a.index_add_(0,pix,x.double())
    mass=accumulate(w);hit=mass>1e-6;den=mass.clamp(min=1e-12)
    mean=accumulate(w*fz)/den
    var=(accumulate(w*fz.double().square())/den-mean.square()).clamp(min=0)
    normmean=accumulate(w[:,None]*fn)/den[:,None];norm=normmean.norm(dim=1)
    normal=normmean/norm[:,None].clamp(min=1e-12)
    alb=accumulate(w[:,None]*fc)/den[:,None]
    entropy=(den.log()-accumulate(w*w.clamp(min=1e-30).log())/den).clamp(min=0)
    cw=w.cumsum(0);exclusive=cw-w;within=cw-exclusive[start][sid]
    eligible=within>=.5*mass[pix]
    median=torch.full((P,),float('inf'),device=dev)
    median.scatter_reduce_(0,pix[eligible],fz[eligible],reduce='amin',include_self=True)
    topid,topw,topmass=fragment_topk(pix,w,fg,P,K)
    margin=(topw[:,0]-(topw[:,1] if K>1 else 0))*topmass/den
    mean[~hit]=float('inf');median[~hit]=float('inf')
    result=dict(depth=mean,depth_median=median,normal=normal,alpha=mass.clamp(max=1),albedo=alb,
        topk_id=topid,topk_w=topw,topk_mass=topmass/den,entropy=entropy,
        margin=margin,depth_variance=var,normal_dispersion=(1-norm).clamp(0,1))
    for name,a in result.items():
        if name not in ('depth','depth_median','topk_id'):a[~hit]=0
        result[name]=a.reshape((H,W)+a.shape[1:]) if name=='topk_id' else a.float().reshape((H,W)+a.shape[1:])
    result.update(coverage=(mass.reshape(H,W)>.01),n_frag=len(pix))
    return result


def numpy_state(state):
    return {k:v.detach().cpu().numpy() if torch.is_tensor(v) else v for k,v in state.items()}


def exact_n(field,eligible,n):
    """Exactly min(n, positive eligible count), stable raster-index tie breaking."""
    ids=np.flatnonzero(eligible & np.isfinite(field) & (field>0))
    order=np.lexsort((ids,-field.ravel()[ids]));out=np.zeros(field.shape,bool)
    out.flat[ids[order[:max(0,int(n))]]]=True
    return out


def nms(field,nx,ny,eligible):
    y,x=np.indices(field.shape,dtype=np.float32);norm=np.hypot(nx,ny)
    dx=np.divide(nx,norm,out=np.zeros_like(nx),where=norm>1e-9).astype('float32')
    dy=np.divide(ny,norm,out=np.zeros_like(ny),where=norm>1e-9).astype('float32')
    a=cv2.remap(field.astype('float32'),x+dx,y+dy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    b=cv2.remap(field.astype('float32'),x-dx,y-dy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    return eligible&(field>=a)&(field>b)&(norm>1e-9)


def pair_field(horizontal,vertical,coverage):
    h=horizontal*(coverage[:,:-1]|coverage[:,1:]);v=vertical*(coverage[:-1]|coverage[1:])
    dx=np.zeros(coverage.shape,np.float32);dy=dx.copy()
    dx[:,:-1]=np.maximum(dx[:,:-1],h);dx[:,1:]=np.maximum(dx[:,1:],h)
    dy[:-1]=np.maximum(dy[:-1],v);dy[1:]=np.maximum(dy[1:],v)
    # Axis of strongest set-valued discontinuity; avoid inventing signed gradients.
    field=np.maximum(dx,dy);return field,(dx>=dy).astype('float32'),(dy>dx).astype('float32')


def overlap_field(ids,weights,coverage,k):
    ids=ids[...,:k];w=weights[...,:k];w=w/np.maximum(w.sum(-1,keepdims=True),1e-12)
    def diff(ai,aw,bi,bw):
        out=[]
        for start in range(0,len(ai),32):
            a=ai[start:start+32];b=bi[start:start+32]
            same=(a[..., :,None]==b[...,None,:])&(a[..., :,None]>=0)
            out.append(1-np.sum(same*np.minimum(aw[start:start+32,...,:,None],bw[start:start+32,...,None,:]),axis=(-2,-1)))
        return np.concatenate(out).clip(0,1)
    return pair_field(diff(ids[:,:-1],w[:,:-1],ids[:,1:],w[:,1:]),
                      diff(ids[:-1],w[:-1],ids[1:],w[1:]),coverage)


def gradients(x):
    gx=cv2.Sobel(x.astype('float32'),cv2.CV_32F,1,0,ksize=3)/8
    gy=cv2.Sobel(x.astype('float32'),cv2.CV_32F,0,1,ksize=3)/8
    if x.ndim==2:return np.hypot(gx,gy),gx,gy
    a=(gx*gx).sum(-1);b=(gx*gy).sum(-1);c=(gy*gy).sum(-1)
    theta=.5*np.arctan2(2*b,a-c);mag=np.sqrt(np.maximum(0,.5*(a+c+np.sqrt((a-c)**2+4*b*b))))
    return mag,np.cos(theta).astype('float32'),np.sin(theta).astype('float32')


def channel_fields(state,cfg):
    cov=state['coverage'];covered=state['alpha']>=.5
    fields={}
    for k in (4,8):fields[f'topk{k}']=overlap_field(state['topk_id'],state['topk_w'],cov,k)
    fields['topk']=fields['topk8']
    alb=state['albedo'].copy();alb[~cov]=1
    fields['rgb']=gradients(cv2.cvtColor(alb.clip(0,1).astype('float32'),cv2.COLOR_RGB2Lab))
    depth=state['depth'].copy();depth[~cov]=0
    fields['depth']=gradients(depth);fields['depth']=(fields['depth'][0]/np.maximum(depth,1e-3),*fields['depth'][1:])
    for name,key in [('entropy','entropy'),('margin','margin'),('alpha','alpha'),('dispersion','normal_dispersion')]:fields[name]=gradients(state[key])
    fields['variance']=gradients(state['depth_variance']/np.maximum(depth,1e-3)**2)
    nr=state['normal']
    hx=np.rad2deg(np.arccos(np.clip(np.abs((nr[:,:-1]*nr[:,1:]).sum(-1)),0,1)))
    hy=np.rad2deg(np.arccos(np.clip(np.abs((nr[:-1]*nr[1:]).sum(-1)),0,1)))
    fields['normal']=pair_field(hx,hy,cov)
    # Responses next to coverage are valid; all-empty neighborhoods are not.
    neighborhood=cv2.dilate(cov.astype('uint8'),np.ones((3,3),np.uint8))>0
    out={}
    for name,(field,nx,ny) in fields.items():
        field=np.nan_to_num(field,nan=0,posinf=0).astype('float32');field[~neighborhood]=0
        threshold=cfg['min_response'][name if not name.startswith('topk') else 'topk']
        eligible=nms(field,nx,ny,covered)&(field>=threshold)
        mask=exact_n(field,eligible,cfg['max_pixels_per_channel'])
        tangent=np.stack([-ny,nx],axis=-1);tangent/=np.maximum(np.linalg.norm(tangent,axis=-1,keepdims=True),1e-12)
        out[name]=dict(response=field,tangent=tangent,mask=mask,nms=eligible)
    return out
