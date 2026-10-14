"""RGB-only image-space boundary profiles and continuous soft ink.

Classic Gaussian derivatives/structure tensor are existing components. This is
an independent prototype, not a reproduction of CLD/FDoG. No 3D inputs exist in
the core API. Normal signs use nx >= 0; the field itself is unoriented.
"""
import cv2
import numpy as np
from scipy.ndimage import label
from skimage.morphology import skeletonize
cv2.setNumThreads(2)

DEFAULT=dict(scales=[.7,1.4,2.8],tensor_sigma=2.,gradient_floor=.0007,
             response_scale=.035,profile_radius=9,contrast_min=.025,
             plateau_max=.045,residual_max=.055,backtrack_max=.4,
             coherence_min=.22,weak=.075,strong=.22,ink_sigma=.5,
             temporal_mix=.3,temporal_delta=.12,flow_fb_max=1.5,
             flow_photo_max=.08,control_delta=.08)

def blur(a,s): return cv2.GaussianBlur(a,(0,0),s,borderType=cv2.BORDER_REFLECT101)
def grid(shape):
    y,x=np.mgrid[:shape[0],:shape[1]]
    return x.astype(np.float32),y.astype(np.float32)
def remap(a,x,y):
    if x.shape[0]>=30000:
        return np.concatenate([remap(a,x[i:i+16000],y[i:i+16000]) for i in range(0,x.shape[0],16000)],axis=0)
    return cv2.remap(a,x.astype(np.float32),y.astype(np.float32),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT101)
def deriv(a):
    return cv2.Scharr(a,cv2.CV_32F,1,0)/32.,cv2.Scharr(a,cv2.CV_32F,0,1)/32.

def tensor_field(rgb,cfg,color=True):
    if color:
        # Orthonormal opponents plus a Rec.709 luminance channel.
        channels=np.stack([rgb@np.array([.2126,.7152,.0722],np.float32),
                           (rgb[...,0]-rgb[...,1])*.70710678,
                           (rgb[...,0]+rgb[...,1]-2*rgb[...,2])*.40824829],-1)
    else: channels=(rgb@np.array([.2126,.7152,.0722],np.float32))[...,None]
    tensors=[]; angles=[]; mags=[]
    for s in cfg['scales']:
        g=blur(channels,s)
        if g.ndim==2:g=g[...,None]
        gx,gy=deriv(g)
        if gx.ndim==2:gx=gx[...,None];gy=gy[...,None]
        jxx=blur(np.sum(gx*gx,-1),cfg['tensor_sigma'])
        jxy=blur(np.sum(gx*gy,-1),cfg['tensor_sigma'])
        jyy=blur(np.sum(gy*gy,-1),cfg['tensor_sigma'])
        tensors.append((jxx,jxy,jyy))
        angles.append(np.arctan2(2*jxy,jxx-jyy))
        mags.append(np.sqrt(np.sum(gx*gx+gy*gy,-1)))
    # Spatial tensor integration regularizes the double-angle orientation.
    jxx,jxy,jyy=[sum(t[k] for t in tensors)/len(tensors) for k in range(3)]
    d=np.sqrt((jxx-jyy)**2+4*jxy*jxy)
    coh=d/(jxx+jyy+1e-10)
    phi=np.arctan2(2*jxy,jxx-jyy); ang=phi*.5
    normal=np.stack([np.cos(ang),np.sin(ang)],-1).astype(np.float32)
    weights=np.stack(mags); phis=np.stack(angles)
    agreement=np.sqrt(np.sum(weights*np.cos(phis),0)**2+np.sum(weights*np.sin(phis),0)**2)/(weights.sum(0)+1e-9)
    mag=np.max(weights,axis=0)
    x,y=grid(mag.shape); tx=-normal[...,1];ty=normal[...,0]
    orient_support=np.zeros_like(mag); magnitude_support=np.zeros_like(mag)
    for s in [-3,-2,-1,1,2,3]:
        cx=x+s*tx;cy=y+s*ty
        orient_support+=.5+.5*(remap(np.cos(phi),cx,cy)*np.cos(phi)+remap(np.sin(phi),cx,cy)*np.sin(phi))
        magnitude_support+=np.minimum(remap(mag,cx,cy)/(mag+1e-8),1.)
    support=(orient_support/6)*(magnitude_support/6)
    confidence=np.clip(coh*agreement*(.35+.65*support),0,1)
    return dict(normal=normal,magnitude=mag,coherence=coh,agreement=agreement,
                support=support,confidence=confidence)

def ridge_mask(mag,normal):
    x,y=grid(mag.shape); nx,ny=normal[...,0],normal[...,1]
    return (mag>=remap(mag,x+nx,y+ny))&(mag>remap(mag,x-nx,y-ny))

def fit_profiles(rgb,field,ridge,cfg):
    radius=cfg['profile_radius']; h,w=rgb.shape[:2]
    allowed=ridge&(field['magnitude']>cfg['gradient_floor'])
    allowed[:radius+2]=False;allowed[-radius-2:]=False
    allowed[:,:radius+2]=False;allowed[:,-radius-2:]=False
    yy,xx=np.nonzero(allowed); xy=np.stack([xx,yy],1).astype(np.float32)
    n=field['normal'][yy,xx]; offsets=np.arange(-radius,radius+1,dtype=np.float32)
    count=len(xy)
    if count:
        sample=remap(rgb,xx[:,None]+n[:,0,None]*offsets,yy[:,None]+n[:,1,None]*offsets)
        minus=np.median(sample[:,:3],axis=1);plus=np.median(sample[:,-3:],axis=1)
        delta=plus-minus; d2=np.sum(delta*delta,1); contrast=np.sqrt(d2/3.)
        plateau=np.sqrt((np.mean((sample[:,:3]-minus[:,None])**2,(1,2))+np.mean((sample[:,-3:]-plus[:,None])**2,(1,2)))/2.)
        fraction=np.sum((sample-minus[:,None])*delta[:,None],2)/(d2[:,None]+1e-12)
        # A bounded monotone logistic family, fit in local normal coordinates.
        centers=np.arange(-2,2.01,.5,dtype=np.float32)
        widths=np.array([.7,1.,1.5,2.,3.,4.5,6.,8.,11.],np.float32)
        params=np.array([(c,v) for c in centers for v in widths],np.float32)
        templates=1/(1+np.exp(np.clip(-(offsets[None]-params[:,0,None])*4.394449/params[:,1,None],-60,60)))
        best=np.empty(count,int)
        for start in range(0,count,2048):
            f=fraction[start:start+2048]
            errors=np.mean((f[:,None,:]-templates[None])**2,2)
            best[start:start+len(f)]=errors.argmin(1)
        center,width=params[best,0],params[best,1]
        fitted=minus[:,None]+delta[:,None]*templates[best,:,None]
        residual=np.sqrt(np.mean((sample-fitted)**2,(1,2)))
        diff=np.diff(fraction,axis=1)
        backtrack=np.sum(np.maximum(-diff,0),axis=1)
        confidence=field['confidence'][yy,xx]
        valid=(contrast>=cfg['contrast_min'])&(plateau<=cfg['plateau_max'])&(residual<=cfg['residual_max'])&(backtrack<=cfg['backtrack_max'])&(abs(center)<=1.75)&(confidence>=cfg['coherence_min'])
        quality=confidence*(1-np.exp(-contrast/.08))*np.exp(-plateau/.035-residual/.06-backtrack)
        # Rejection codes are evidence categories, never semantic "bad detail".
        reason=np.zeros(count,np.uint8)
        reason[confidence<cfg['coherence_min']]=1
        reason[abs(center)>1.75]=2
        reason[backtrack>cfg['backtrack_max']]=3
        reason[residual>cfg['residual_max']]=4
        reason[plateau>cfg['plateau_max']]=5
        reason[contrast<cfg['contrast_min']]=6
    else:
        sample=np.empty((0,len(offsets),3),np.float32);minus=plus=delta=np.empty((0,3),np.float32)
        contrast=plateau=center=width=residual=backtrack=quality=np.empty(0,np.float32)
        valid=np.empty(0,bool);reason=np.empty(0,np.uint8)
    return dict(xy=xy,normal=n,offsets=offsets,samples=sample,minus=minus,plus=plus,
                signed_contrast=delta,contrast=contrast,plateau_variance=plateau**2,
                center=center,width=width,residual=residual,backtrack=backtrack,
                quality=quality,valid=valid,rejection=reason)

def hysteresis(soft,weak,strong):
    labels,num=label(soft>=weak,np.ones((3,3)))
    live=np.unique(labels[soft>=strong]);live=live[live!=0]
    return np.isin(labels,live)

def tangent_support(soft,normal,confidence):
    x,y=grid(soft.shape); tx=-normal[...,1];ty=normal[...,0]
    neighbors=(remap(soft,x+tx,y+ty)+remap(soft,x-tx,y-ty))*.5
    # Only small current-evidence gaps may be joined; no fragment-count voting.
    return np.maximum(soft,neighbors*.5*confidence)

def analyze(rgb,cfg=None):
    cfg={**DEFAULT,**(cfg or {})};rgb=np.asarray(rgb,np.float32)
    field=tensor_field(rgb,cfg); ridge=ridge_mask(field['magnitude'],field['normal'])
    raw=(1-np.exp(-field['magnitude']/cfg['response_scale'])).astype(np.float32)
    detail=raw*ridge*(.55+.45*field['confidence'])
    detail=tangent_support(detail,field['normal'],field['confidence'])
    profiles=fit_profiles(rgb,field,ridge,cfg)
    structural=np.zeros(rgb.shape[:2],np.float32);quality_map=structural.copy();width_map=structural.copy()
    if len(profiles['xy']):
        xy=profiles['xy'].astype(int);xs,ys=xy.T
        quality_map[ys,xs]=profiles['quality'];width_map[ys,xs]=profiles['width']
        structural[ys,xs]=np.sqrt(profiles['quality'])*profiles['valid']
    structural=tangent_support(structural,field['normal'],field['confidence'])
    structural*=hysteresis(structural,cfg['weak'],cfg['strong'])
    # Generous detail remains visible even if it has no trustworthy plateau fit.
    union=np.maximum(detail,structural)
    unknown=raw*(1-np.clip(blur(structural,1.)*3,0,1))
    classmap=np.zeros(rgb.shape[:2],np.uint8)
    classmap[detail>=cfg['weak']]=2; classmap[structural>=cfg['weak']]=1
    return dict(**field,raw=raw,detail=detail.astype(np.float32),structural=structural,
                union=union.astype(np.float32),unknown=unknown.astype(np.float32),
                classmap=classmap,profile_confidence=quality_map,width_map=width_map,profiles=profiles)

def classic_response(rgb,cfg=None):
    """Simple existing multiscale luminance tensor-gradient control (not FDoG)."""
    cfg={**DEFAULT,**(cfg or {})};f=tensor_field(rgb,cfg,color=False)
    raw=1-np.exp(-f['magnitude']/cfg['response_scale'])
    ridge=ridge_mask(f['magnitude'],f['normal'])
    soft=tangent_support(raw*ridge*(.55+.45*f['confidence']),f['normal'],f['confidence'])
    return soft.astype(np.float32),raw.astype(np.float32)

def canny_response(rgb,threshold=45):
    lum=rgb@np.array([.2126,.7152,.0722],np.float32)
    return cv2.Canny(np.uint8(np.clip(lum*255,0,255)),threshold*.4,threshold,L2gradient=True).astype(np.float32)/255.

def alpha_outline(alpha):
    """Separate silhouette auxiliary; zero information enters RGB-only analyze."""
    a=np.asarray(alpha,np.float32);mask=a>=.5
    er=cv2.erode(mask.astype(np.uint8),np.ones((3,3),np.uint8))
    edge=mask.astype(np.float32)-er
    return edge

def ink(soft,gain=1.,sigma=.5):
    # Identical black-on-white presentation for all arms. Soft maps remain saved.
    a=np.clip(soft*gain,0,1)
    if sigma:a=np.maximum(a,blur(a,sigma)*.8)
    return np.repeat((1-a)[...,None],3,axis=2).astype(np.float32)

def overlay(rgb,soft,gain=1.,sigma=.5):
    a=1-ink(soft,gain,sigma)[...,0]
    return rgb*(1-.8*a[...,None])

def chains(soft,normal,weak=.075,strong=.22):
    """Skeleton graph traced through junctions. All supported chains retained."""
    mask=skeletonize(hysteresis(soft,weak,strong));yy,xx=np.nonzero(mask)
    pixels={(int(x),int(y)) for x,y in zip(xx,yy)}
    def neighbors(p):
        x,y=p;return sorted((x+dx,y+dy) for dy in [-1,0,1] for dx in [-1,0,1] if (dx or dy) and (x+dx,y+dy) in pixels)
    adjacency={p:neighbors(p) for p in sorted(pixels)}
    visited=set();paths=[]
    def edge(a,b):return tuple(sorted((a,b)))
    def walk(a,b):
        path=[a,b];visited.add(edge(a,b))
        while len(adjacency[b])==2:
            c=next(p for p in adjacency[b] if p!=a)
            if edge(b,c) in visited:break
            visited.add(edge(b,c));path.append(c);a,b=b,c
        xy=np.asarray(path);d=np.diff(xy,axis=0)
        length=float(np.sqrt(np.sum(d*d,1)).sum())
        tangents=np.stack([-normal[xy[:,1],xy[:,0],1],normal[xy[:,1],xy[:,0],0]],-1)
        v=d/(np.linalg.norm(d,axis=1)[:,None]+1e-9)
        coh=float(np.mean(abs(np.sum(v*tangents[:-1],1)))) if len(d) else 0.
        paths.append(dict(xy=xy.tolist(),arc_length=length,coherence=coh,
                          confidence=float(np.mean(soft[xy[:,1],xy[:,0]]))))
    for a in adjacency:
        if len(adjacency[a])!=2:
            for b in adjacency[a]:
                if edge(a,b) not in visited:walk(a,b)
    for a in adjacency:
        for b in adjacency[a]:
            if edge(a,b) not in visited:walk(a,b)
    return paths

def flow_pair(previous,current,cfg=None):
    cfg={**DEFAULT,**(cfg or {})}
    def gray(im):return np.uint8(np.clip((im@np.array([.2126,.7152,.0722],np.float32))*255,0,255))
    a,b=gray(previous),gray(current)
    # Deterministic lightweight CPU flow; no network/model install.
    args=(None,.5,4,19,4,7,1.5,0)
    forward=cv2.calcOpticalFlowFarneback(a,b,*args)
    backward=cv2.calcOpticalFlowFarneback(b,a,*args)
    x,y=grid(a.shape);mx=x+backward[...,0];my=y+backward[...,1]
    warped_forward=remap(forward,mx,my)
    fb=np.linalg.norm(backward+warped_forward,axis=2)
    photo=np.mean(abs(remap(previous,mx,my)-current),axis=2)
    inside=(mx>=0)&(mx<a.shape[1]-1)&(my>=0)&(my<a.shape[0]-1)
    valid=inside&(fb<cfg['flow_fb_max'])&(photo<cfg['flow_photo_max'])
    confidence=np.exp(-fb*fb/2.-photo/.04)*valid
    return dict(mx=mx,my=my,valid=valid,confidence=confidence,fb=fb,photo=photo,
                forward=forward,backward=backward)

def blend_temporal(previous_soft,current_soft,flow,cfg=None):
    cfg={**DEFAULT,**(cfg or {})}
    warped=remap(previous_soft,flow['mx'],flow['my'])
    delta=np.clip(warped-current_soft,-cfg['temporal_delta'],cfg['temporal_delta'])
    # Birth/death and disocclusions reset. A temporal edge needs CURRENT evidence.
    evidence=np.clip(current_soft/.12,0,1)
    blended=current_soft+cfg['temporal_mix']*flow['confidence']*evidence*delta
    blended=np.clip(blended,np.maximum(0,current_soft-cfg['temporal_delta']),np.minimum(1,current_soft+cfg['temporal_delta']))
    blended[current_soft==0]=0
    return blended.astype(np.float32),warped

def temporal_pair(previous,current,previous_soft,current_soft,cfg=None):
    f=flow_pair(previous,current,cfg);out,warped=blend_temporal(previous_soft,current_soft,f,cfg)
    return out,dict(valid_fraction=float(f['valid'].mean()),warped=warped,flow=f)

def control_width(rgb,result,factor,cfg=None):
    """Conservative screen-space transition stylization, never geometric repair.

    Overlap is averaged by profile confidence, bounded to each two-side color
    interval. Corrections are inverse compositions: C_new = C + fit_new-fit_old.
    Only finite profile bands change; plateaus, non-band pixels are exact.
    """
    cfg={**DEFAULT,**(cfg or {})};p=result['profiles'];h,w=rgb.shape[:2]
    acc=np.zeros_like(rgb);weight=np.zeros((h,w),np.float32)
    keep=np.flatnonzero(p['valid']&(p['quality']>.35)&(p['width']>=1.5)&(p['residual']<.035)&(p['plateau_variance']<.0005))
    for j in keep:
        center=p['xy'][j]+p['normal'][j]*p['center'][j]
        n=p['normal'][j];rad=min(8.,max(2.,p['width'][j]*1.25))
        x0=max(0,int(center[0]-rad-2));x1=min(w,int(center[0]+rad+3))
        y0=max(0,int(center[1]-rad-2));y1=min(h,int(center[1]+rad+3))
        yy,xx=np.mgrid[y0:y1,x0:x1];dx=xx-center[0];dy=yy-center[1]
        s=dx*n[0]+dy*n[1];t=-dx*n[1]+dy*n[0]
        window=(abs(s)<rad)&(abs(t)<1.1)
        taper=np.maximum(0,1-(abs(s)/rad)**4)*np.maximum(0,1-abs(t)/1.1)*window
        a=1/(1+np.exp(np.clip(-s*4.394449/p['width'][j],-60,60)))
        b=1/(1+np.exp(np.clip(-s*4.394449/(p['width'][j]*factor),-60,60)))
        correction=(b-a)[...,None]*p['signed_contrast'][j]
        original=rgb[y0:y1,x0:x1]
        lo=np.minimum(p['minus'][j],p['plus'][j]);hi=np.maximum(p['minus'][j],p['plus'][j])
        correction=np.clip(original+correction,lo,hi)-original
        ww=taper*p['quality'][j]
        acc[y0:y1,x0:x1]+=correction*ww[...,None]
        weight[y0:y1,x0:x1]+=ww
    delta=acc/np.maximum(weight[...,None],1.)
    delta=np.clip(delta,-cfg['control_delta'],cfg['control_delta'])
    out=rgb+delta
    band=weight>0
    out[~band]=rgb[~band]
    return out.astype(np.float32),dict(band=band,profiles_used=len(keep),outside_max=float(abs(out[~band]-rgb[~band]).max(initial=0)),
                                      max_delta=float(abs(delta).max(initial=0)),clipped_fraction=float(((out<0)|(out>1)).mean()),
                                      alpha='unchanged; separate alpha data never modified')
