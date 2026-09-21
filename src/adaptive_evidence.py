"""Separate frozen G1 channels and controls from mass-complete CSR evidence."""
import ctypes
import numpy as np
from scipy import ndimage as ndi
from .adaptive_layers import compress_layers
DIRECTIONS=np.array([[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]])


def pair_fields(e,layers,library):
    shape=layers['local_scale'].shape;off=e['offsets'];pix=np.repeat(np.arange(np.prod(shape)),np.diff(off))
    order=np.lexsort((e['ids'],pix))
    rank=layers['assignment']-layers['layer_offsets'][pix]
    arrays=[np.ascontiguousarray(v,dtype=d) for v,d in [(off,'i8'),(e['z'],'f8'),(e['w'],'f8'),
            (e['ids'][order],'i8'),(e['w'][order],'f8'),(rank[order],'i8'),(layers['retained_mass'],'f8'),
            (layers['retained_depth'],'f8'),(layers['local_scale'],'f8')]]
    out=np.zeros((*shape,8,9),'f4');lib=ctypes.CDLL(str(library));fn=lib.adaptive_pairs
    fn.argtypes=[ctypes.c_int]*2+[ctypes.c_void_p]*10;fn.restype=None
    fn(*shape,*[v.ctypes.data for v in arrays],out.ctypes.data)
    return dict(BC=out[...,0],W1=out[...,1],D_front=out[...,2],support=out[...,3],front_confidence=out[...,4],layer_BC=out[...,5:9])


def matched_hessian(layers,sigma,library):
    shape=layers['local_scale'].shape;index=layers['retained_index']
    seed=np.zeros_like(index,dtype='u1');valid=index>=0
    seed[valid]=layers['layer_seedable'][index[valid]]
    arrays=[np.ascontiguousarray(v,dtype=d) for v,d in [(layers['retained_depth'],'f8'),
            (layers['retained_mass'],'f8'),(layers['local_scale'],'f8'),(seed,'u1')]]
    out=np.zeros((*shape,4,4),'f4');lib=ctypes.CDLL(str(library));fn=lib.adaptive_matched_hessian
    fn.argtypes=[ctypes.c_int]*2+[ctypes.c_double]+[ctypes.c_void_p]*5;fn.restype=None
    fn(*shape,sigma,*[v.ctypes.data for v in arrays],out.ctypes.data)
    return out


def distribution_stats(e,shape):
    off=e['offsets'];sizes=np.diff(off);pix=np.repeat(np.arange(np.prod(shape)),sizes)
    w=e['w'].astype('f8');z=e['z'];s=lambda v:np.bincount(pix,weights=v,minlength=len(sizes)).reshape(shape)
    A=s(w);p=w/np.maximum(A.ravel()[pix],1e-12);mean=s(p*z)
    front=np.zeros(len(sizes));valid=sizes>0;front[valid]=z[off[:-1][valid]]
    cumulative=np.zeros(len(sizes));median=np.zeros(len(sizes));found=np.zeros(len(sizes),bool)
    for rank in range(int(sizes.max(initial=0))):
        rows=np.flatnonzero(sizes>rank);indices=off[rows]+rank;cumulative[rows]+=w[indices]
        take=(~found[rows])&(cumulative[rows]>=.5*A.ravel()[rows]);median[rows[take]]=z[indices[take]];found[rows[take]]=True
    return dict(A=A,z_front=front.reshape(shape),z_mean=mean,z_50=median.reshape(shape),
                z_var=s(p*(z-mean.ravel()[pix])**2),H_id=s(-p*np.log(np.maximum(p,1e-12))))


def eigen_response(hxx,hxy,hyy,polarity):
    trace=(hxx+hyy)/2;radius=np.sqrt(((hxx-hyy)/2)**2+hxy*hxy)
    v0=trace-radius;v1=trace+radius;choose=np.abs(v1)>np.abs(v0)
    large=np.where(choose,v1,v0);small=np.where(choose,v0,v1)
    ratio=np.abs(small)/np.maximum(np.abs(large),1e-15)
    response=np.abs(large)*np.exp(-.5*(ratio/.5)**2)
    response[(ratio>=.5)|(large*polarity<=0)]=0
    normal=.5*np.arctan2(2*hxy,hxx-hyy)+np.where(choose,0,np.pi/2)
    return response,(normal+np.pi/2)%np.pi


def scalar_hessian(field,sigma,polarity=-1):
    xx=sigma*sigma*ndi.gaussian_filter(field,sigma,order=(0,2),mode='nearest')
    xy=sigma*sigma*ndi.gaussian_filter(field,sigma,order=(1,1),mode='nearest')
    yy=sigma*sigma*ndi.gaussian_filter(field,sigma,order=(2,0),mode='nearest')
    return eigen_response(xx,xy,yy,polarity)


def build_evidence(e,native_alpha,library,include_ids=True,geometry=None):
    shape=native_alpha.shape
    if geometry is None:
        layers=compress_layers(e,native_alpha);stats=distribution_stats(e,shape)
        hessians=matched_hessians(layers,library)
        geometry=dict(layers=layers,stats=stats,hessians=hessians)
    layers=geometry['layers'];stats=geometry['stats'];pairs=pair_fields(e,layers,library)
    d=layers['local_scale'];A=stats['A'];support=A>=.5
    r=lambda x:np.clip((x-1)/3,0,1)
    pairscale=np.zeros((*shape,8))
    for j,(dy,dx) in enumerate(DIRECTIONS):
        shifted=np.roll(d,(-dy,-dx),(0,1));pairscale[...,j]=np.maximum(d,shifted)
    Dz=pairs['W1']/np.maximum(pairscale,1e-12)
    score=pairs['support']*np.maximum(r(pairs['D_front']),r(Dz))*pairs['front_confidence']
    if include_ids:score*=np.sqrt(np.maximum(0,1-pairs['BC']))
    direction=np.argmax(score,axis=-1);occ=np.max(score,axis=-1)*support
    angle=(np.arctan2(DIRECTIONS[direction,0],DIRECTIONS[direction,1])+np.pi/2)%np.pi
    def field(response,orientation,sigma,depth,layer):
        return dict(response=np.asarray(response,'f4'),orientation=np.asarray(orientation,'f4'),sigma=np.broadcast_to(sigma,shape).astype('f4'),
                    depth=np.asarray(depth,'f4'),layer=np.broadcast_to(layer,shape).astype('i2'))
    channels={'E_occ':field(occ,angle,1.5,layers['retained_depth'][...,0],0)}
    # Directed depth order, oriented by each pixel's strongest front-depth pair.
    strongest=np.argmax(pairs['D_front'],axis=-1);normal=DIRECTIONS[strongest]
    positive=np.zeros(shape);negative=np.zeros(shape)
    for j,(dy,dx) in enumerate(DIRECTIONS):
        difference=np.roll(stats['z_front'],(-dy,-dx),(0,1))-stats['z_front']
        directed=difference*(normal[...,0]*dy+normal[...,1]*dx)
        valid=pairs['support'][...,j]>0
        positive+=(directed>0)&valid;negative+=(directed<0)&valid
    ordering=np.maximum(positive,negative)/np.maximum(positive+negative,1)
    mass=layers['retained_mass'];depth=layers['retained_depth']
    heavy=mass>=.1;two=heavy.sum(-1)>=2
    lo=np.min(np.where(heavy,depth,np.inf),axis=-1);hi=np.max(np.where(heavy,depth,-np.inf),axis=-1)
    separated=two&((hi-lo)>3*d)
    stable=ndi.convolve(separated.astype('i4'),np.ones((3,3),'i4'),mode='constant')>=5
    layer_gate=support&stable&(ordering>=.75)
    layer_response=np.zeros(shape);layer_angle=np.zeros(shape);layer_sigma=np.zeros(shape)
    normalized_variance=stats['z_var']/np.maximum(d*d,1e-24)
    normalized_entropy=stats['H_id']/np.log(np.maximum(np.diff(e['offsets']).reshape(shape),2))
    for sigma in [1.5,2.5,4.]:
        for scalar in [normalized_variance,normalized_entropy]:
            response,tangent=scalar_hessian(scalar,sigma)
            response*=A*layer_gate;win=response>layer_response
            layer_response[win]=response[win];layer_angle[win]=tangent[win];layer_sigma[win]=sigma
    channels['E_layer']=field(layer_response,layer_angle,layer_sigma,depth[...,0],0)
    identity=pairs['layer_BC'].sum(axis=-2)/np.maximum((pairs['support']>0).sum(-1)[...,None],1) if include_ids else np.ones((*shape,4))
    for name,polarity in [('E_shape_ridge',-1),('E_shape_valley',1)]:
        best=np.zeros(shape);orient=np.zeros(shape);scales=np.zeros(shape);which=np.zeros(shape,'i2');zout=np.zeros(shape)
        for sigma,hessian in zip([1.5,2.5,4.],geometry['hessians']):
            response,tangent=eigen_response(hessian[...,0],hessian[...,1],hessian[...,2],polarity)
            response*=mass*identity*support[...,None]
            for l in range(4):
                win=response[...,l]>best;best[win]=response[...,l][win];orient[win]=tangent[...,l][win]
                scales[win]=sigma;which[win]=l;zout[win]=depth[...,l][win]
        channels[name]=field(best,orient,scales,zout,which)
    diagnostics=dict(stats,D_id=np.sqrt(np.maximum(0,1-pairs['BC'])).max(-1),D_zdist=Dz.max(-1),
                     ordering_consistency=ordering,stable_split=stable,
                     layer_count_transition=np.max([np.abs(layers['layer_count']-np.roll(layers['layer_count'],(-dy,-dx),(0,1))) for dy,dx in DIRECTIONS],axis=0),
                     front_mass_transition=np.max([np.abs(mass[...,0]-np.roll(mass[...,0],(-dy,-dx),(0,1))) for dy,dx in DIRECTIONS],axis=0))
    return dict(channels=channels,diagnostics=diagnostics,pairs=pairs,layers=layers,geometry=geometry)


EVENT_KEYS=('ids','z','w','rgb','alpha','T','stream_position')


def prefix_control(e,native_alpha,tau,kmax):
    off=e['offsets'];sizes=np.diff(off);pixels=len(sizes);total=np.zeros(pixels);counts=np.zeros(pixels,'i8')
    for rank in range(kmax):
        valid=sizes>rank
        if tau is not None:valid &= total<tau*native_alpha.ravel()
        rows=np.flatnonzero(valid);idx=off[rows]+rank;total[rows]+=e['w'][idx];counts[rows]+=1
    pix=np.repeat(np.arange(pixels),sizes);keep=np.arange(len(e['w']))-off[pix]<counts[pix]
    out={k:(v[keep].copy() if k in EVENT_KEYS else v.copy()) for k,v in e.items()}
    out['offsets']=np.r_[0,np.cumsum(counts)]
    out['tail_alpha']=e['tail_alpha']+np.bincount(pix[~keep],weights=e['w'][~keep],minlength=pixels).reshape(native_alpha.shape)
    out['tail_rgb']=e['tail_rgb']+np.stack([np.bincount(pix[~keep],weights=e['w'][~keep].astype('f8')*e['rgb'][~keep,c],minlength=pixels).reshape(native_alpha.shape) for c in range(3)],axis=-1)
    return out


def transform_control(e,kind,seed):
    out=dict(e);rng=np.random.default_rng(seed);off=e['offsets'];sizes=np.diff(off)
    pix=np.repeat(np.arange(len(sizes)),sizes)
    if kind=='uniform':
        A=np.bincount(pix,weights=e['w'],minlength=len(sizes));out['w']=A[pix]/sizes[pix]
    elif kind=='shuffled_ids':out['ids']=rng.permutation(e['ids'])
    elif kind=='shuffled_depths':
        z=rng.permutation(e['z']);order=np.lexsort((z,pix))
        out={k:(v[order].copy() if k in EVENT_KEYS else v) for k,v in e.items()};out['z']=z[order]
    else:raise ValueError('unknown control')
    return out


def hysteresis_bands(field,BC,local_scale,library,high,low):
    response=np.ascontiguousarray(field['response'],'f4');angle=field['orientation'];yy,xx=np.indices(response.shape)
    nx=-np.sin(angle);ny=np.cos(angle)
    plus=ndi.map_coordinates(response,[yy+ny,xx+nx],order=1,mode='constant',prefilter=False)
    minus=ndi.map_coordinates(response,[yy-ny,xx-nx],order=1,mode='constant',prefilter=False)
    nms=(response>=plus)&(response>=minus)&((response>plus)|(response>minus))
    anchors=np.ascontiguousarray(nms&(response>=high)&(response>0),'u1')
    arrays=[response,*[np.ascontiguousarray(field[k],'f8') for k in ['orientation','sigma','depth']],
            np.ascontiguousarray(local_scale,'f8'),np.ascontiguousarray(BC,'f4'),anchors]
    center=np.zeros(response.shape,'u1');band=np.zeros_like(center);lib=ctypes.CDLL(str(library));fn=lib.adaptive_hysteresis
    fn.argtypes=[ctypes.c_int]*2+[ctypes.c_double]+[ctypes.c_void_p]*9;fn.restype=None
    fn(*response.shape,low,*[v.ctypes.data for v in arrays],center.ctypes.data,band.ctypes.data)
    return dict(nms=nms,anchors=anchors.astype(bool),center=center.astype(bool),band=band.astype(bool))


def finalize_channel(field,BC,local_scale,normalization,library):
    result=dict(field,normalized_soft=field['response']/max(normalization,1e-12));thresholds=[]
    positive=field['response'][field['response']>0]
    for high_p,low_p in [(95,70),(90,60)]:
        high,low=np.percentile(positive,[high_p,low_p]) if len(positive) else (0.,0.)
        thresholds.append([high,low]);bands=hysteresis_bands(field,BC,local_scale,library,float(high),float(low))
        result.update({f'{k}_{high_p}_{low_p}':v for k,v in bands.items()})
    result['thresholds']=np.asarray(thresholds)
    return result


def matched_hessians(layers,library):
    shape=layers['local_scale'].shape;index=layers['retained_index'];seed=np.zeros_like(index,dtype='u1');valid=index>=0
    seed[valid]=layers['layer_seedable'][index[valid]]
    arrays=[np.ascontiguousarray(v,dtype=d) for v,d in [(layers['retained_depth'],'f8'),(layers['retained_mass'],'f8'),(layers['local_scale'],'f8'),(seed,'u1')]]
    out=np.zeros((*shape,4,3,4),'f4');lib=ctypes.CDLL(str(library));fn=lib.adaptive_matched_hessians
    fn.argtypes=[ctypes.c_int]*2+[ctypes.c_void_p]*5;fn.restype=None
    fn(*shape,*[v.ctypes.data for v in arrays],out.ctypes.data)
    return [out[...,i,:] for i in range(3)]
