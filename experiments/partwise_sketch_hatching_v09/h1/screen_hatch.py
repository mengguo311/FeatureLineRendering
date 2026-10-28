"""Deterministic per-view image-space streamlines; no persistent stroke anchors."""
import runtime
import numpy as np
from geometry import project,backproject

def projected_field(mesh,raw,depth,faces,camera):
    h,w=depth.shape;y,x=np.mgrid[:h,:w];hit=faces>=0
    uv=np.column_stack([x[hit],y[hit]]);world=backproject(uv,depth[hit],camera)
    E=np.asarray(camera['extrinsic']);p=world@E[:3,:3].T+E[:3,3];v=raw[faces[hit]]@E[:3,:3].T
    tangent=np.column_stack([camera['fx']*(v[:,0]*p[:,2]-p[:,0]*v[:,2])/p[:,2]**2,
                             camera['fy']*(v[:,1]*p[:,2]-p[:,1]*v[:,2])/p[:,2]**2])
    norm=np.linalg.norm(tangent,axis=1);out=np.zeros((h,w,2));out[hit]=np.divide(tangent,norm[:,None],out=np.zeros_like(tangent),where=norm[:,None]>1e-8)
    return out,int((norm<1e-8).sum())

def at(a,p):
    x,y=np.floor(np.asarray(p)+.5).astype(int)
    if x<0 or y<0 or x>=a.shape[1] or y>=a.shape[0]:return None
    return a[y,x]

def integrate(seed,sign,length,field,mask,depth,step,jump):
    p=np.asarray(seed,float);t=at(field,p)
    if t is None or not at(mask,p):return p[None,:],'invalid_seed'
    t=t*sign;last=t.copy();points=[p.copy()];remaining=length
    for _ in range(10000):
        if remaining<=1e-8:return np.asarray(points),'requested_length'
        t=at(field,p);norm=np.linalg.norm(t)
        if norm<1e-8:return np.asarray(points),'projected_field_degeneracy'
        t=t/norm
        if t@last<0:t=-t
        travel=min(step,remaining);mid=p+t*travel/2;tm=at(field,mid)
        if tm is not None and np.linalg.norm(tm)>1e-8:
            tm=tm/np.linalg.norm(tm)
            if tm@t<0:tm=-tm
            t=tm
        q=p+travel*t
        if at(mask,q) is None or not at(mask,q):return np.asarray(points),'mask_boundary'
        if abs(float(at(depth,q))-float(at(depth,p)))>jump:return np.asarray(points),'depth_discontinuity'
        points.append(q.copy());p=q;last=t;remaining-=travel
    return np.asarray(points),'step_limit'

def generate(field,mask,depth,anchor,basis,cfg):
    anchor=np.asarray(anchor);basis=np.asarray(basis,float);basis/=np.linalg.norm(basis)
    cross=np.array([-basis[1],basis[0]]);period=cfg['length_px']+cfg['gap_px'];spacing=cfg['spacing_px']
    y,x=np.nonzero(mask)
    if not len(x):return [],dict(seeds=0,paths=0,stops={},screen_length=0.,seed_rule='deterministic image lattice')
    uv=np.column_stack([x,y])-anchor;along=uv@basis;across=uv@cross
    lo=np.floor([along.min()/period,across.min()/spacing]).astype(int)-1
    hi=np.ceil([along.max()/period,across.max()/spacing]).astype(int)+1
    paths=[];records=[];stops={};seeds=0
    for j in range(lo[1],hi[1]+1):
        for i in range(lo[0],hi[0]+1):
            center=anchor+(i+cfg['phase'][0])*period*basis+(j+cfg['phase'][1])*spacing*cross
            # Cover every intended lattice segment intersecting the mask, including
            # segments whose center is outside. Each disjoint image/depth run gets
            # its own seed; no bridge through a hole or another visible sheet.
            offsets=np.linspace(-cfg['length_px']/2,cfg['length_px']/2,max(2,int(np.ceil(cfg['length_px']/.25))+1))
            probes=center+offsets[:,None]*basis;valid=np.asarray([at(mask,p) is not None and bool(at(mask,p)) for p in probes])
            runs=[];run=[];last=None
            for k,ok in enumerate(valid):
                split=ok and last is not None and abs(float(at(depth,probes[k]))-float(at(depth,probes[last])))>cfg['depth_jump']
                if (not ok or split) and run:runs.append(run);run=[]
                if ok:run.append(k);last=k
                else:last=None
            if run:runs.append(run)
            for run in runs:
                k=min(run,key=lambda k:abs(offsets[k]));seed=probes[k];shift=offsets[k]
                tangent=at(field,seed)
                if np.linalg.norm(tangent)<1e-8:continue
                direction_sign=1 if tangent@basis>=0 else -1
                seeds+=1;parts=[];why=[]
                for sign,requested in ((-direction_sign,cfg['length_px']/2+shift),(direction_sign,cfg['length_px']/2-shift)):
                    p,s=integrate(seed,sign,max(0.,requested),field,mask,depth,cfg['step_px'],cfg['depth_jump'])
                    parts.append(p);why.append(s);stops[s]=stops.get(s,0)+1
                p=np.concatenate([parts[0][::-1],parts[1][1:]])
                ll=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
                records.append(dict(lattice=[i,j],seed_uv=seed.tolist(),center_outside=not bool(at(mask,center)) if at(mask,center) is not None else True,seed_offset_px=float(shift),length_px=ll,stops=why))
                if ll>=.5:paths.append(p)
    return paths,dict(seeds=seeds,paths=len(paths),stops=stops,screen_length=sum(float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()) for p in paths),
        seed_rule='Fixed phase rectangular image lattice; projected single frozen part anchor/basis; no per-stroke 3D history',records=records)

def raster(paths,mask,width,aa):
    h,w=mask.shape;ink=np.zeros((h*aa,w*aa),bool);radius=width*aa/2
    for p in paths:
        for endpoints in zip(p[:-1],p[1:]):
            q=(np.asarray(endpoints)+.5)*aa-.5;d=q[1]-q[0];den=d@d
            if den<1e-14:continue
            lo=np.maximum(0,np.ceil(q.min(0)-radius)).astype(int);hi=np.minimum([w*aa-1,h*aa-1],np.floor(q.max(0)+radius)).astype(int)
            if (hi<lo).any():continue
            y,x=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];t=np.clip(((x-q[0,0])*d[0]+(y-q[0,1])*d[1])/den,0,1)
            ink[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=(x-q[0,0]-t*d[0])**2+(y-q[0,1]-t*d[1])**2<=radius**2
    return ink&np.repeat(np.repeat(mask,aa,0),aa,1)
