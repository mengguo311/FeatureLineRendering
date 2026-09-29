"""Bounded direct fixed-world cubic drawing fit. No segment tracks or GS IDs."""
import numpy as np
import torch


def bezier(control,n=32):
    t=torch.linspace(0,1,n,dtype=control.dtype,device=control.device)
    basis=torch.stack([(1-t)**3,3*(1-t)**2*t,3*(1-t)*t*t,t**3],1)
    return torch.einsum('sk,ckd->csd',basis,control)


def project(points,K,w2c):
    q=points@w2c[:3,:3].T+w2c[:3,3]
    h=q@K.T
    return h[...,:2]/h[...,2:].clamp_min(1e-6),q[...,2]


def association(points,tangent,target,target_tangent,sigma,active,visible,known,sides=None,target_sides=None):
    """Latent full-image association. Max is idempotent under duplicate ink."""
    if not len(target):
        zero=points.sum()*0
        return dict(coverage=points.new_zeros(0),nearest=torch.zeros(len(points),device=points.device,dtype=torch.long),
                    unsupported=active*visible,orientation=active*visible,appearance=active*0,distance=active*0+32,compatibility=active*0)
    dist=torch.cdist(points,target,compute_mode='donot_use_mm_for_euclid_dist')
    nearest=dist.argmin(1);nearest_dist=dist.gather(1,nearest[:,None])[:,0]
    valid=torch.isfinite(target_tangent).all(1)
    tt=torch.nan_to_num(target_tangent)
    dot=(tangent@tt.T).abs().clamp(0,1)
    orient=torch.exp(-(1-dot)/.12)*valid[None]
    appearance=torch.ones_like(dist)
    if sides is not None:
        base=(sides.square().sum((-1,-2))[:,None]+target_sides.square().sum((-1,-2))[None])/6
        a=(base-(sides[:,0]@target_sides[:,0].T+sides[:,1]@target_sides[:,1].T)/3).clamp_min(0)
        b=(base-(sides[:,0]@target_sides[:,1].T+sides[:,1]@target_sides[:,0].T)/3).clamp_min(0)
        measurable=(target_sides[:,0]-target_sides[:,1]).norm(dim=-1)>=.03
        appearance=torch.where(measurable[None],torch.exp(-torch.minimum(a,b)/.04),appearance)
    comp=torch.exp(-dist.square()/(2*sigma*sigma))*orient*appearance
    support=(active*visible*known)[:,None]
    coverage=(comp*support).max(0).values
    nc=comp.gather(1,nearest[:,None])[:,0]*known
    o=(1-dot.gather(1,nearest[:,None])[:,0])*known
    ap=1-appearance.gather(1,nearest[:,None])[:,0]
    return dict(coverage=coverage,nearest=nearest,unsupported=active*visible*(1-nc),
                orientation=active*visible*o,appearance=active*visible*ap,distance=nearest_dist,compatibility=nc)


def evidence(rgb,depth,alpha,front=None):
    import cv2
    from scipy import ndimage as ndi
    from src.multiscene_probe import edge_field
    cfg={'detector':dict(sigma=1.2,canny=[50,120],aperture=3,L2gradient=False,tangent_window=5,min_tangent_pixels=3,tangent_eigen_ratio_max=.25)}
    rgb=np.asarray(rgb,np.float32);small=rgb.reshape(400,2,400,2,3).mean((1,3))
    f=edge_field(small,cfg);y,x=np.nonzero(f['edge']);xy=np.c_[x,y].astype(float)
    def package(xy,tangent,native_edge):
        smooth=cv2.GaussianBlur(small,(0,0),1.2);normal=np.c_[-tangent[:,1],tangent[:,0]];normal=np.nan_to_num(normal)
        sides=[]
        for sign in [-1,1]:
            values=[]
            for offset in [2,4]:
                uv=xy+sign*offset*normal
                values.append(np.stack([ndi.map_coordinates(smooth[:,:,c],[uv[:,1],uv[:,0]],order=1,mode='nearest') for c in range(3)],1))
            sides.append(np.mean(values,axis=0))
        return dict(xy=((xy+.5)*2-.5).astype('f4'),tangent=tangent.astype('f4'),sides=np.stack(sides,1).astype('f4'),native_edge=native_edge)
    native=np.zeros((800,800),bool);native[np.clip(np.rint((y+.5)*2-.5).astype(int),0,799),np.clip(np.rint((x+.5)*2-.5).astype(int),0,799)]=True
    out={'I':package(xy,f['tangent'][y,x],native)}
    z=np.asarray(depth,float);gx=ndi.gaussian_filter(z,1.5,order=(0,1));gy=ndi.gaussian_filter(z,1.5,order=(1,0))
    local=depth_scale(z if front is None else front)
    strength=np.hypot(gx,gy)/local
    yy,xx=np.indices(z.shape);norm=np.maximum(np.hypot(gx,gy),1e-30);nx=gx/norm;ny=gy/norm
    minus=ndi.map_coordinates(strength,[yy-ny,xx-nx],order=1,mode='nearest');plus=ndi.map_coordinates(strength,[yy+ny,xx+nx],order=1,mode='nearest')
    roi=alpha>=.5;nms=(strength>=minus)&(strength>=plus)&(strength>0)&roi
    positive=strength[nms];mask=np.zeros(z.shape,bool)
    if len(positive):
        hi,lo=np.percentile(positive,[95,70]);weak=nms&(strength>=lo);labels,n=ndi.label(weak,np.ones((3,3)));keep=np.unique(labels[nms&(strength>=hi)]);keep=keep[keep>0];mask=np.isin(labels,keep)
    outline=roi&~ndi.binary_erosion(roi,border_value=1);mask|=outline
    # Collapse native depth boundary to area400 occupancy, preserving all occupied cells.
    edge=mask.reshape(400,2,400,2).any((1,3));y,x=np.nonzero(edge);xy=np.c_[x,y].astype(float)
    dx=cv2.resize(gx,(400,400),interpolation=cv2.INTER_AREA);dy=cv2.resize(gy,(400,400),interpolation=cv2.INTER_AREA)
    # Alpha outlines have a tangent even with constant foreground depth.
    ay,ax=np.gradient(ndi.gaussian_filter(alpha.astype(float),1.5));ax=cv2.resize(ax,(400,400));ay=cv2.resize(ay,(400,400));use=np.hypot(dx,dy)<1e-10;dx[use]=ax[use];dy[use]=ay[use]
    tangent=np.c_[-dy[y,x],dx[y,x]];norm=np.linalg.norm(tangent,axis=1);tangent/=np.maximum(norm[:,None],1e-30);tangent[norm<1e-10]=np.nan
    native=np.zeros((800,800),bool);native[(2*y+1).clip(0,799),(2*x+1).clip(0,799)]=True
    out['D']=package(xy,tangent,native)
    return out


def sample_map(maps,uv):
    h,w=maps.shape[-2:];shape=uv.shape[:-1]
    q=uv.reshape(-1,2);x=q[:,0].clamp(0,w-1);y=q[:,1].clamp(0,h-1)
    x0=x.floor().long();y0=y.floor().long();x1=(x0+1).clamp(max=w-1);y1=(y0+1).clamp(max=h-1)
    dx=(x-x0).unsqueeze(1);dy=(y-y0).unsqueeze(1)
    a=maps[0,:,y0,x0].T;b=maps[0,:,y0,x1].T;c=maps[0,:,y1,x0].T;d=maps[0,:,y1,x1].T
    return (a+dx*(b-a)+dy*(c-a)+dx*dy*(a-b-c+d)).reshape(*shape,-1)



def visibility(uv,z,maps,diagonal):
    """0 visible, 1 unknown, 2 occluded, 3 outside. No learned visibility."""
    h,w=maps.shape[-2:];v=sample_map(maps,uv.detach()).detach();a,q10,q50,q90=v.unbind(-1)
    inside=(uv[...,0]>=0)&(uv[...,0]<w)&(uv[...,1]>=0)&(uv[...,1]<h)&(z>0)
    hidden=(a>=.5)&(z.detach()>q90+.01*diagonal)
    unknown=((a>=.1)&(a<.5))|((a>=.5)&((q90-q10>.05*diagonal)|((z.detach()>q10+.01*diagonal)&(z.detach()<=q90+.01*diagonal))))
    state=torch.zeros_like(z,dtype=torch.int8);state[unknown]=1;state[hidden]=2;state[~inside]=3
    return ((state==0)|(state==1)).to(z.dtype),state==0,state


def view_loss(control,active,data,arm,sigma,diagonal):
    points=bezier(control);uv,z=project(points,data['K'],data['w2c'])
    derivative=torch.gradient(uv,dim=1)[0];t=derivative/derivative.norm(dim=-1,keepdim=True).clamp_min(1e-8)
    length=derivative.norm(dim=-1);length=length.clone();length[:,[0,-1]]*=.5
    visible,known,state=visibility(uv,z,data['maps'],diagonal)
    sides=None
    if data['rgb'] is not None and arm!='D':
        n=torch.stack([-t[...,1],t[...,0]],-1)
        sides=torch.stack([sum(sample_map(data['rgb'],uv+sign*offset*n) for offset in [4.,8.])/2 for sign in [-1,1]],-2).reshape(-1,2,3)
    act=active[:,None].expand_as(z).reshape(-1)
    a=association(uv.reshape(-1,2),t.reshape(-1,2),data['xy'],data['tangent'],sigma,act,visible.reshape(-1),known.reshape(-1),sides,data['sides'] if sides is not None else None)
    denom=max(1,len(data['xy'])*2)*data.get('scale',1.)
    weight=length.reshape(-1)/denom
    unsupported=(a['unsupported']*weight).sum();orientation=(a['orientation']*weight).sum();appearance=(a['appearance']*weight).sum()
    missed=(1-a['coverage']).mean() if len(data['xy']) else control.sum()*0
    attraction=(1-act*visible.reshape(-1)*(1-a['distance'].clamp(max=32)/32)).reshape(len(control),-1).mean(1).sum()/128
    value=(missed if arm!='L' else attraction)+.5*unsupported+.1*orientation+.1*appearance
    return dict(data=value,missed=missed,unsupported=unsupported,orientation=orientation,appearance=appearance,attraction=attraction,coverage=a['coverage'],state=state)


def regularization(control,active,arm,diagonal):
    samples=bezier(control,8);length=torch.diff(samples,dim=1).norm(dim=-1).sum(1)
    count=active.sum()/128;size=(length*active).sum()/(128*diagonal)
    bend=(torch.diff(control,n=2,dim=1)/diagonal).square().mean((1,2));smooth=(bend*active).sum()/128
    redundancy=control.sum()*0
    if arm!='L' and len(control)>1:
        pair=torch.cdist(samples.reshape(-1,3),samples.reshape(-1,3),compute_mode='donot_use_mm_for_euclid_dist').reshape(len(control),8,len(control),8).permute(0,2,1,3)
        d=(pair.min(-1).values.square().mean(-1)+pair.min(-2).values.square().mean(-1))/2
        sim=torch.exp(-d/(.01*diagonal)**2)*active[:,None]*active[None,:]
        mask=torch.triu(torch.ones_like(sim,dtype=torch.bool),diagonal=1)
        redundancy=sim[mask].mean()
    return dict(regularization=.01*count+.02*size+.01*smooth+.05*redundancy,count=count,length=size,smooth=smooth,redundancy=redundancy)


def fit(initial,data,box,arm,device='cuda',max_seconds=1800):
    import time
    started=time.monotonic();diagonal=float(np.linalg.norm(np.diff(box,axis=0)))
    control=torch.tensor(initial,dtype=torch.float32,device=device,requires_grad=True)
    gate=torch.full((len(initial),),4.,device=device,requires_grad=True)
    opt=torch.optim.Adam([dict(params=[control],lr=.002*diagonal),dict(params=[gate],lr=.02)])
    lo=torch.tensor(box[0],dtype=control.dtype,device=device);hi=torch.tensor(box[1],dtype=control.dtype,device=device)
    sets=[]
    for coarse in [True,False]:
        rows=[]
        for d in data:
            row={k:(v.to(device) if torch.is_tensor(v) else v) for k,v in d.items()}
            if coarse:
                xy=row['xy'].detach().cpu().numpy();bins=np.floor((xy+.5)/4).astype(int)
                _,ix=np.unique(bins,axis=0,return_index=True);ix=np.sort(ix)
                for k in ['xy','tangent','sides']:
                    if row[k] is not None:row[k]=row[k][ix]
                row['scale']=len(xy)/max(1,len(ix))
            rows.append(row)
        sets.append(rows)
    history=[];binary=None
    for step in range(300):
        if time.monotonic()-started>max_seconds:raise TimeoutError('COMPUTE_BUDGET_EXHAUSTED')
        if step==250:binary=(gate.detach().sigmoid()>=.5).float()
        opt.zero_grad();records=[]
        for d in sets[step>=150]:
            active=gate.sigmoid() if binary is None else binary
            parts=view_loss(control,active,d,arm,8. if step<150 else 2.,diagonal)
            (parts['data']/len(data)).backward()
            records.append({k:float(v.detach()) for k,v in parts.items() if k not in ['state','coverage']})
        active=gate.sigmoid() if binary is None else binary
        prior=regularization(control,active,arm,diagonal);prior['regularization'].backward()
        torch.nn.utils.clip_grad_norm_([control,gate],10.)
        if not torch.isfinite(control.grad).all():raise ValueError('ENGINEERING_INVALID nonfinite gradient')
        opt.step()
        with torch.no_grad():control.clamp_(lo,hi)
        row={k:sum(r[k] for r in records)/len(records) for k in records[0]}
        row.update({k:float(v.detach()) for k,v in prior.items()});row['step']=step;history.append(row)
    with torch.no_grad():
        records=[view_loss(control,binary,d,arm,2.,diagonal) for d in sets[1]]
        final={k:sum(float(r[k]) for r in records)/len(records) for k in ['data','missed','unsupported','orientation','appearance','attraction']}
        final.update({k:float(v) for k,v in regularization(control,binary,arm,diagonal).items()})
    return dict(control=control.detach().cpu().numpy(),active=binary.cpu().numpy().astype(bool),gate=gate.detach().sigmoid().cpu().numpy(),history=history,final=final,seconds=time.monotonic()-started)


def proposals(views,box):
    rng=np.random.default_rng(20260922);box=np.asarray(box);starts=[[],[],[]];records=[]
    for view in views:
        camera=view['camera'];K=np.asarray(camera['native_K']);pose=np.linalg.inv(camera['w2c'])
        rgb=view['evidence']['I'];dep=view['evidence']['D'];xy=np.concatenate([rgb['xy'],dep['xy']]);tangent=np.concatenate([rgb['tangent'],dep['tangent']])
        pix=np.rint(xy).astype(int).clip(0,799);good=view['alpha'][pix[:,1],pix[:,0]]>=.5
        xy=xy[good];tangent=tangent[good]
        for row in range(4):
            for col in range(4):
                ix=np.flatnonzero((xy[:,0]>=col*200)&(xy[:,0]<(col+1)*200)&(xy[:,1]>=row*200)&(xy[:,1]<(row+1)*200))
                if len(ix):
                    j=int(rng.choice(ix));q=xy[j];t=tangent[j];source='boundary'
                else:
                    y,x=np.nonzero(view['alpha'][row*200:(row+1)*200,col*200:(col+1)*200]>=.5)
                    if len(x):
                        j=int(rng.integers(len(x)));q=np.array([x[j]+col*200,y[j]+row*200],float);source='foreground_fallback'
                    else:q=np.array([col*200+99.5,row*200+99.5]);source='empty_cell'
                    t=np.array([1.,0.])
                if not np.isfinite(t).all():t=np.array([1.,0.])
                ix,iy=np.rint(q).astype(int).clip(0,799);depth=float(view['depth'][iy,ix])
                if depth<=0 or not np.isfinite(depth):depth=float((np.asarray(camera['w2c'])@np.r_[box.mean(0),1])[2])
                uv=q[None]+np.linspace(-24,24,4)[:,None]*t[None]
                rays=np.c_[uv,np.ones(4)]@np.linalg.inv(K).T
                for k,m in enumerate([.9,1.,1.1]):
                    world=(rays*depth*m)@pose[:3,:3].T+pose[:3,3];starts[k].append(np.clip(world,box[0],box[1]))
                records.append(dict(id=len(records),view=view['view'],cell=row*4+col,pixel=q.tolist(),source=source,initial_depth=depth,tangent=t.tolist()))
    return dict(starts=np.asarray(starts,'f4'),provenance=records)


def native_quantiles(state,h,w,library='out/direct_curve_global_fit_probe/setup/quantiles_cuda_v1.so'):
    import ctypes
    lib=ctypes.CDLL(str(__import__('pathlib').Path(library).resolve()))
    cuda=hasattr(lib,'direct_curve_quantiles_cuda')
    fn=lib.direct_curve_quantiles_cuda if cuda else lib.direct_curve_quantiles
    fn.argtypes=[ctypes.c_int,ctypes.c_int]+[ctypes.c_void_p]*8+[ctypes.c_float,ctypes.c_void_p]
    fn.restype=ctypes.c_int if cuda else None
    n=len(state['depths']);arrays=[np.ascontiguousarray(state[k],dtype=d) for k,d in zip(['means2D','conic','rgb','depths','point_list','ranges'],['f4']*4+['u4']*2)]
    arrays.extend([np.zeros(n,'u1'),np.zeros(n,'u1')]);result=np.zeros((h,w,10),'f4')
    status=fn(h,w,*[a.ctypes.data for a in arrays],1.,result.ctypes.data)
    if cuda and status:raise RuntimeError('ENGINEERING_INVALID CUDA replay error '+str(status))
    return dict(rgb=result[:,:,:3],alpha=result[:,:,3],quantiles=result[:,:,6:9],front=result[:,:,9])


def depth_scale(front):
    front=np.asarray(front,float);padded=np.pad(front,2,mode='edge')
    neighbors=np.lib.stride_tricks.sliding_window_view(padded,(5,5)).reshape(*front.shape,25)
    delta=abs(neighbors[:,:,[k for k in range(25) if k!=12]]-front[:,:,None])
    return np.maximum.reduce([.002*front,np.median(delta,axis=-1),np.full(front.shape,1e-12)])
