"""CPU-only mesh-attached P0 primitives. No learned reconstruction is performed."""
import hashlib
import numpy as np
from scipy import ndimage
from PIL import Image


def unit(x):
    return np.asarray(x, float) / max(np.linalg.norm(x), 1e-15)


def camera(azimuth, elevation, distance, size, focal):
    a, e = np.deg2rad([azimuth, elevation])
    target = np.array([0., 1.17, 0.])
    eye = target + distance*np.array([np.sin(a)*np.cos(e), np.sin(e), np.cos(a)*np.cos(e)])
    forward = unit(target-eye)
    right = unit(np.cross(forward, [0,1,0]))
    down = np.cross(forward, right)
    R = np.stack([right, down, forward])
    return {"R": R, "t": -R@eye, "eye": eye, "size": size,
            "focal": focal, "center": np.array([size/2.,size/2.])}


def project(x, c):
    xc = np.asarray(x)@c["R"].T+c["t"]
    return xc[...,:2]/xc[...,2:3]*c["focal"]+c["center"], xc[...,2]


def backproject(uv, depth, c, convention="z"):
    ray = np.concatenate(((np.asarray(uv)-c["center"])/c["focal"],
                          np.ones((*np.asarray(uv).shape[:-1],1))), axis=-1)
    if convention == "ray":
        ray /= np.linalg.norm(ray,axis=-1,keepdims=True)
    elif convention != "z":
        raise ValueError("depth convention must be z or ray")
    return (ray*np.asarray(depth)[...,None]-c["t"])@c["R"]


def tangent(n, a):
    n = unit(n)
    t = np.asarray(a)-np.dot(a,n)*n
    if np.linalg.norm(t) < 1e-8:
        fallback = np.eye(3)[np.argmin(np.abs(n))]
        t = fallback-np.dot(fallback,n)*n
    return unit(t)


def line_mean(vectors, normal):
    """Principal eigenvector of dyadic line tensors: invariant to every sign."""
    ts = np.array([tangent(normal,v) for v in vectors])
    _, vec = np.linalg.eigh(ts.T@ts)
    return tangent(normal,vec[:,-1])


def finalize_mesh(vertices, faces, parts):
    v, f = np.asarray(vertices,float), np.asarray(faces,np.int32)
    tri = v[f]
    cross = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    areas = np.linalg.norm(cross,axis=1)/2
    if np.any(areas <= 1e-14):
        raise ValueError("degenerate triangles")
    normals = cross/(2*areas[:,None])
    basis = np.stack((tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=2)
    pinv = np.linalg.pinv(basis)
    adj = np.full((len(f),3),-1,np.int32)
    edges = {}
    for fi, face in enumerate(f):
        for k in range(3):
            key=tuple(sorted((int(face[(k+1)%3]),int(face[(k+2)%3]))))
            if key in edges:
                other,j=edges[key];adj[fi,k]=other;adj[other,j]=fi
            else: edges[key]=(fi,k)
    return {"vertices":v,"faces":f,"parts":np.asarray(parts,np.int32),
            "tri":tri,"normals":normals,"areas":areas,"pinv":pinv,"adj":adj}


def make_lamp(asset):
    vertices, faces, parts, lookup = [], [], [], {}
    def vertex(x):
        key=tuple(np.round(x,12))
        if key not in lookup:
            lookup[key]=len(vertices);vertices.append(x)
        return lookup[key]
    N=asset["angular_segments"]
    for part, profile in asset["profiles_ry"].items():
        rings=[]
        for r,y in profile:
            rings.append([vertex([r*np.cos(2*np.pi*i/N),y,r*np.sin(2*np.pi*i/N)]) for i in range(N)])
        for j in range(len(rings)-1):
            for i in range(N):
                a,b=rings[j][i],rings[j][(i+1)%N]
                c,d=rings[j+1][i],rings[j+1][(i+1)%N]
                for face in ([a,c,b],[b,c,d]):
                    if len(set(face))==3:
                        faces.append(face);parts.append(int(part))
    return finalize_mesh(vertices,faces,parts)


def barycentric(mesh, face, x):
    b12=mesh["pinv"][face]@(x-mesh["tri"][face,0])
    return np.array([1-b12.sum(),b12[0],b12[1]])


def anchor_points(mesh,s):
    return np.einsum("ni,nij->nj",s["bary"],mesh["tri"][s["faces"]])


def field(mesh,face,x,style,part,layer,angle):
    n=mesh["normals"][face]
    axial=tangent(n,[0,1,0])
    circum=tangent(n,[-x[2],0,x[0]])
    base=circum if (style=="mixed" and part in (1,3)) else axial
    theta=angle
    if style=="cross" or (style=="mixed" and part==3):
        theta += 40 if layer==0 else -40
    a=np.deg2rad(theta)
    return unit(np.cos(a)*base+np.sin(a)*np.cross(n,base))


def walk(mesh,face,bary,part,style,layer,angle,length,step,sign):
    ff,bb=[face],[bary.copy()]
    remain=length
    previous=None
    for _ in range(800):
        if remain < 1e-7: break
        x=bary@mesh["tri"][face]
        t=field(mesh,face,x,style,part,layer,angle)*sign
        if previous is not None and np.dot(t,previous)<0: t=-t
        previous=t
        db12=mesh["pinv"][face]@t
        db=np.array([-db12.sum(),db12[0],db12[1]])
        h=min(step,remain)
        negative=db < -1e-10
        times=np.full(3,np.inf)
        times[negative]=-bary[negative]/db[negative]
        edge=int(np.argmin(times))
        travel=times[edge]
        if travel < h:
            travel=max(0.,travel)
            new=bary+travel*db
            new=np.maximum(new,0);new/=new.sum()
            ff.append(face);bb.append(new)
            remain-=travel
            neighbor=int(mesh["adj"][face,edge])
            if neighbor<0 or mesh["parts"][neighbor]!=part: break
            edge_point=new@mesh["tri"][face]
            face=neighbor
            bary=barycentric(mesh,face,edge_point)
            # Numerical interior nudge stays on this triangle, never floats.
            bary=np.maximum(bary,0);bary/=bary.sum()
            bary=bary*(1-1e-7)+1e-7/3
            ff.append(face);bb.append(bary.copy())
            remain-=1e-7
        else:
            bary=bary+h*db
            bary=np.maximum(bary,0);bary/=bary.sum()
            ff.append(face);bb.append(bary.copy())
            remain-=h
    return ff,bb


def generate_strokes(mesh,cfg,style="mixed",only_part=None,angle=0.,counts=None):
    strokes=[]
    counts=counts or cfg["strokes"]["counts_by_part"]
    for part in (1,2,3):
        if only_part is not None and only_part!=part: continue
        rng=np.random.default_rng(np.random.SeedSequence([cfg["seed"],part]))
        candidates=np.flatnonzero(mesh["parts"]==part)
        prob=mesh["areas"][candidates];prob=prob/prob.sum()
        layers=2 if style=="cross" or (style=="mixed" and part==3) else 1
        for i in range(int(counts[str(part)])):
            face=int(rng.choice(candidates,p=prob))
            q=rng.random(2);sq=np.sqrt(q[0])
            bary=np.array([1-sq,sq*(1-q[1]),sq*q[1]])
            length=cfg["strokes"]["length_by_part"][str(part)]
            for layer in range(layers):
                fa,ba=walk(mesh,face,bary,part,style,layer,angle,length/2,cfg["strokes"]["step_world"],-1)
                fb,bb=walk(mesh,face,bary,part,style,layer,angle,length/2,cfg["strokes"]["step_world"],1)
                faces=np.array(fa[::-1]+fb[1:],np.int32)
                barys=np.array(ba[::-1]+bb[1:])
                n=mesh["normals"][face]
                light=unit([-1,2,1])
                ink=.30+.55*(1-max(0.,float(n@light)))
                strokes.append({"id":f"p{part}:seed{i:04d}:layer{layer}",
                                "part":part,"style":style,"angle":angle,"layer":layer,
                                "faces":faces,"bary":barys,"ink":ink})
    return strokes


def edit_part(mesh,strokes,cfg,part,angle,counts=None):
    old=[s for s in strokes if s["part"]!=part]
    return sorted(old+generate_strokes(mesh,cfg,"mixed",part,angle,counts),key=lambda s:s["id"])


def stroke_digest(strokes):
    h=hashlib.sha256()
    for s in sorted(strokes,key=lambda s:s["id"]):
        h.update(s["id"].encode());h.update(s["faces"].tobytes());h.update(s["bary"].tobytes())
    return h.hexdigest()


def raster_surface(mesh,c):
    size=c["size"]
    depth=np.full((size,size),np.inf)
    parts=np.zeros((size,size),np.int32)
    uv,z=project(mesh["vertices"],c)
    for face,part in zip(mesh["faces"],mesh["parts"]):
        p=uv[face];zz=z[face]
        if np.min(zz)<=0: continue
        lo=np.maximum(np.floor(p.min(axis=0)).astype(int),0)
        hi=np.minimum(np.ceil(p.max(axis=0)).astype(int),size-1)
        if np.any(hi<lo): continue
        a,b,d=p
        den=(b[1]-d[1])*(a[0]-d[0])+(d[0]-b[0])*(a[1]-d[1])
        if abs(den)<1e-12: continue
        yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        w0=((b[1]-d[1])*(xx-d[0])+(d[0]-b[0])*(yy-d[1]))/den
        w1=((d[1]-a[1])*(xx-d[0])+(a[0]-d[0])*(yy-d[1]))/den
        w2=1-w0-w1
        inside=(w0>=-1e-9)&(w1>=-1e-9)&(w2>=-1e-9)
        inv=w0/zz[0]+w1/zz[1]+w2/zz[2]
        dd=np.divide(1,inv,out=np.full_like(inv,np.inf),where=inv>0)
        view=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        take=inside&(dd<view)
        view[take]=dd[take]
        parts[lo[1]:hi[1]+1,lo[0]:hi[0]+1][take]=part
    return depth,parts


def visible_points(x,c,depth,tolerance):
    uv,z=project(x,c)
    pix=np.rint(uv).astype(int)
    inside=(pix[:,0]>=0)&(pix[:,0]<c["size"])&(pix[:,1]>=0)&(pix[:,1]<c["size"])&(z>0)
    visible=np.zeros(len(x),bool)
    p=pix[inside]
    visible[inside]=z[inside]<=depth[p[:,1],p[:,0]]+tolerance
    return visible


def analytic_reference(asset,c):
    """Independent continuous lathe ray intersection, no triangle raster reuse."""
    size=c["size"];yy,xx=np.mgrid[:size,:size]
    camray=np.stack(((xx-c["center"][0])/c["focal"],
                     (yy-c["center"][1])/c["focal"],np.ones_like(xx)),axis=-1)
    ray=camray@c["R"];o=c["eye"]
    best=np.full((size,size),np.inf);parts=np.zeros((size,size),np.int32)
    def submit(t,valid,part):
        take=valid&np.isfinite(t)&(t>0)&(t<best)
        best[take]=t[take];parts[take]=part
    for part,profile in asset["profiles_ry"].items():
        part=int(part)
        for (r0,y0),(r1,y1) in zip(profile[:-1],profile[1:]):
            if abs(y1-y0)<1e-12:
                t=np.divide(y0-o[1],ray[...,1],out=np.full_like(best,np.inf),where=abs(ray[...,1])>1e-12)
                with np.errstate(invalid="ignore"):
                    rho=np.hypot(o[0]+t*ray[...,0],o[2]+t*ray[...,2])
                submit(t,(rho>=min(r0,r1)-1e-10)&(rho<=max(r0,r1)+1e-10),part)
            else:
                slope=(r1-r0)/(y1-y0);intercept=r0-slope*y0
                ro=slope*o[1]+intercept;rd=slope*ray[...,1]
                A=ray[...,0]**2+ray[...,2]**2-rd**2
                B=2*(o[0]*ray[...,0]+o[2]*ray[...,2]-ro*rd)
                C=o[0]**2+o[2]**2-ro**2
                disc=B**2-4*A*C
                root=np.sqrt(np.maximum(disc,0))
                for sign in (-1,1):
                    t=np.divide(-B+sign*root,2*A,out=np.full_like(best,np.inf),where=abs(A)>1e-12)
                    linear=(abs(A)<=1e-12)&(abs(B)>1e-12)
                    t[linear]=-C/B[linear]
                    with np.errstate(invalid="ignore"):
                        y=o[1]+t*ray[...,1]
                    submit(t,(disc>=0)&(y>=min(y0,y1)-1e-10)&(y<=max(y0,y1)+1e-10),part)
    return best,parts


def analytic_distance(points,profile):
    p=np.column_stack((np.hypot(points[:,0],points[:,2]),points[:,1]))
    best=np.full(len(p),np.inf)
    for a,b in zip(profile[:-1],profile[1:]):
        a,b=np.array(a),np.array(b)
        d=b-a
        t=np.clip(((p-a)@d)/(d@d),0,1)
        best=np.minimum(best,np.linalg.norm(p-(a+t[:,None]*d),axis=1))
    return best


def dense_path(points,c,max_step=.45):
    uv,_=project(points,c)
    lengths=np.linalg.norm(np.diff(uv,axis=0),axis=1)
    allpoints=[]
    for a,b,l in zip(points[:-1],points[1:],lengths):
        n=max(1,int(np.ceil(l/max_step)))
        allpoints.append(a+(b-a)*np.linspace(0,1,n+1)[:,None])
    return np.concatenate(allpoints) if allpoints else points


def contour_mask(parts):
    edge=np.zeros(parts.shape,bool)
    edge[1:]|=parts[1:]!=parts[:-1]
    edge[:-1]|=parts[:-1]!=parts[1:]
    edge[:,1:]|=parts[:,1:]!=parts[:,:-1]
    edge[:,:-1]|=parts[:,:-1]!=parts[:,1:]
    return edge&(parts>0)


def render(mesh,strokes,cfg,azimuth=30,elevation=20,distance=4.5,structure=True):
    scale=cfg["renderer"]["supersample"]
    size=cfg["renderer"]["resolution"][0]
    c=camera(azimuth,elevation,distance,size*scale,cfg["renderer"]["focal_px"]*scale)
    depth,parts=raster_surface(mesh,c)
    hatch=np.zeros(depth.shape,float)
    tol=cfg["renderer"]["visibility_tolerance_world"]
    visible_count,total_count=0,0
    for s in strokes:
        points=dense_path(anchor_points(mesh,s),c)
        uv,z=project(points,c);pix=np.rint(uv).astype(int)
        visible=visible_points(points,c,depth,tol)
        q=pix[visible]
        foreground=parts[q[:,1],q[:,0]]>0
        q=q[foreground]
        total_count+=len(points);visible_count+=len(q)
        if len(q): np.maximum.at(hatch,(q[:,1],q[:,0]),s["ink"])
    hatch=ndimage.maximum_filter(hatch,size=max(1,round(cfg["strokes"]["screen_width_px"]*scale)))
    hatch[parts==0]=0
    allink=hatch.copy();allink[contour_mask(parts)]=.92
    if structure:
        for part,profile in cfg["asset"]["profiles_ry"].items():
            for r,y in profile:
                if r<.1: continue
                theta=np.linspace(0,2*np.pi,385)
                points=np.column_stack((r*np.cos(theta),np.full_like(theta,y),r*np.sin(theta)))
                points=dense_path(points,c)
                uv,_=project(points,c);pix=np.rint(uv).astype(int)
                good=visible_points(points,c,depth,tol)
                q=pix[good];q=q[parts[q[:,1],q[:,0]]>0]
                if len(q): allink[q[:,1],q[:,0]]=.85
    def down(x):
        return np.array(Image.fromarray(np.uint8(np.clip(x,0,1)*255)).resize((size,size),Image.Resampling.LANCZOS))/255.
    return {"image":down(1-allink),"hatch":down(hatch),
            "parts":parts[::scale,::scale],"depth":depth[::scale,::scale],
            "visible_samples":visible_count,"total_samples":total_count,
            "camera":camera(azimuth,elevation,distance,size,cfg["renderer"]["focal_px"])}


def edit_metrics(before,after,parts,target,band):
    delta=np.abs(np.asarray(after,float)-np.asarray(before,float))
    if delta.ndim==3: delta=delta.sum(axis=2)
    mask=parts==target
    distance=ndimage.distance_transform_edt(~mask)
    outside=~mask;near=outside&(distance<=band)
    other=outside&(distance>band)&(parts>0)
    background=outside&(distance>band)&(parts==0)
    total=float(delta.sum())
    def fraction(m): return float(delta[m].sum())/max(total,1e-15)
    return {"total_delta":total,"inside_delta":float(delta[mask].sum()),
            "nonzero_edit":bool(delta[mask].sum()>10),
            "outside_fraction":fraction(outside),"boundary_band_fraction":fraction(near),
            "far_other_parts_fraction":fraction(other),"far_background_fraction":fraction(background),
            "inside_mean_delta":float(delta[mask].mean()) if mask.any() else 0.,
            "mask_pixels":int(mask.sum()),"band_px":band}


def support_error(ink,uv):
    uv=np.rint(uv).astype(int)
    inside=(uv[:,0]>=0)&(uv[:,0]<ink.shape[1])&(uv[:,1]>=0)&(uv[:,1]<ink.shape[0])
    uv=uv[inside]
    d=ndimage.distance_transform_edt(~np.asarray(ink,bool))
    values=d[uv[:,1],uv[:,0]]
    return {"samples":len(values),"mean_px":float(values.mean()) if len(values) else None,
            "p95_px":float(np.percentile(values,95)) if len(values) else None}


def label_image(parts):
    palette=np.array([[255,255,255],[79,138,173],[213,144,67],[114,160,103]],np.uint8)
    return palette[parts]


def save_strokes(path,strokes):
    lengths=np.array([len(s["faces"]) for s in strokes])
    np.savez_compressed(path,ids=np.array([s["id"] for s in strokes]),
                        parts=np.array([s["part"] for s in strokes]),
                        offsets=np.r_[0,np.cumsum(lengths)],
                        faces=np.concatenate([s["faces"] for s in strokes]),
                        bary=np.concatenate([s["bary"] for s in strokes]),
                        inks=np.array([s["ink"] for s in strokes]))
