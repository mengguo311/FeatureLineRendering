"""Mass-complete native contributor prefixes; isolated additive CSR API."""
import ctypes
import numpy as np
from .topk_layered_evidence import validate_native_state


def native_csr(state, height, width, tau, kmax, library):
    validate_native_state(state,height,width,kmax)
    t=np.asarray(state['final_T'])
    if not np.isfinite(tau) or not 0<tau<=1:raise ValueError('invalid tau')
    if t.shape!=(height,width) or not np.isfinite(t).all() or np.any((t<0)|(t>1)):
        raise ValueError('invalid native final transmittance')
    lib=ctypes.CDLL(str(library));fn=lib.adaptive_mass_csr
    fn.argtypes=[ctypes.c_int]*3+[ctypes.c_double]+[ctypes.c_void_p]*14
    fn.restype=None
    arrays=[np.ascontiguousarray(state[key],dtype=dtype) for key,dtype in
            [('means2D','f4'),('conic','f4'),('depths','f4'),('rgb','f4'),
             ('point_list','u4'),('ranges','u4'),('final_T','f4')]]
    sizes=np.zeros(height*width,'i8');count=np.zeros_like(sizes)
    args=[height,width,kmax,tau,*[a.ctypes.data for a in arrays],sizes.ctypes.data]
    fn(*args,None,None,None,None,None,count.ctypes.data)
    offsets=np.concatenate([np.zeros(1,'i8'),np.cumsum(sizes)])
    ids=np.empty(offsets[-1],'i8');positions=np.empty_like(ids)
    events=np.empty((len(ids),7),'f4');tail=np.zeros((height,width,5),'f8')
    fn(*args,offsets.ctypes.data,ids.ctypes.data,positions.ctypes.data,
       events.ctypes.data,tail.ctypes.data,count.ctypes.data)
    return dict(offsets=offsets,ids=ids,stream_position=positions,z=events[:,0],
                alpha=events[:,1],T=events[:,2],w=events[:,3],rgb=events[:,4:],
                tail_rgb=tail[...,:3],tail_alpha=tail[...,3],final_T=tail[...,4],
                native_final_T=arrays[-1],count=count.reshape(height,width))


def csr_metrics(e, state, black, tau, kmax):
    """Validate native semantics and quantify absolute mass, never renormalize tail."""
    off=e['offsets'];sizes=np.diff(off);shape=e['final_T'].shape;pixels=sizes.size
    ids=e['ids'];z=e['z'];w=e['w'].astype('f8');a=e['alpha'];T=e['T'];n=len(ids)
    csr_ok=off.shape==(np.prod(shape)+1,) and off[0]==0 and off[-1]==n and np.all(sizes>=0)
    if not csr_ok:return dict(passed=False,checks={'csr':False},failed=['csr']),{}
    pix=np.repeat(np.arange(pixels),sizes);valid=sizes>0;start=off[:-1][valid];end=off[1:][valid]-1
    same=np.ones(n,dtype=bool);same[start]=False
    previous=np.maximum(np.arange(n)-1,0)
    sum_pixel=lambda v:np.bincount(pix,weights=v,minlength=pixels).reshape(shape)
    A=sum_pixel(w);native=1-e['native_final_T'].astype('f8');roi=native>=.5
    p=w/np.maximum(A.ravel()[pix],1e-12);mean=sum_pixel(p*z)
    front=np.zeros(pixels);front[valid]=z[start]
    median=np.zeros(pixels)
    # Segmented cumulative sum computed per native pixel, bounded by Kmax.
    running=np.zeros(pixels);found=np.zeros(pixels,bool)
    for rank in range(kmax):
        rows=np.flatnonzero(sizes>rank);index=off[rows]+rank
        running[rows]+=w[index]
        take=(~found[rows])&(running[rows]>=.5*A.ravel()[rows])
        median[rows[take]]=z[index[take]];found[rows[take]]=True
    d=dict(A=A,z_front=front.reshape(shape),z_mean=mean,z_50=median.reshape(shape),
           z_var=sum_pixel(p*(z-mean.ravel()[pix])**2),H_id=sum_pixel(-p*np.log(np.maximum(p,1e-12))),
           K=sizes.reshape(shape),missing=native-A,reached=A>=tau*native)
    replay=np.stack([sum_pixel(w*e['rgb'][:,c]) for c in range(3)],axis=-1)+e['tail_rgb']
    maxabs=lambda v:float(np.max(np.abs(v),initial=0))
    expected=np.ones(n);expected[same]=(T[previous[same]]*(1-a[previous[same]]))
    after=np.ones(pixels);after[valid]=T[end]*(1-a[end])
    ids_ok=bool(np.all((ids>=0)&(ids<len(state['depths']))))
    positions=e['stream_position'];pos_ok=bool(np.all((positions>=0)&(positions<len(state['point_list']))))
    tile=(np.arange(pixels)//shape[1]//16)*((shape[1]+15)//16)+(np.arange(pixels)%shape[1]//16)
    ranges=state['ranges'][tile[pix]]
    before=A.ravel()[valid]-w[end]
    checks=dict(csr=bool(csr_ok),finite=all(np.isfinite(v).all() for v in e.values()),
        ids=ids_ok,original_depth=ids_ok and bool(np.all(np.abs(z-state['depths'][np.clip(ids,0,len(state['depths'])-1)])<=1e-5*(1+np.abs(z)))),
        unique_ids=len(np.unique(pix*len(state['depths'])+ids))==n,
        depth_order=bool(np.all((z-z[previous])[same]>=-1e-6*np.maximum(1,np.abs(z[previous[same]])))),
        stream_provenance=pos_ok and bool(np.all(state['point_list'][np.clip(positions,0,len(state['point_list'])-1)]==ids)),
        stream_order=bool(np.all((positions-positions[previous])[same]>0)),
        stream_ranges=bool(np.all((positions>=ranges[:,0])&(positions<ranges[:,1]))),
        ranges=bool(np.all((a>=1/255)&(a<=.99)) and np.all((T>0)&(T<=1)) and np.all(w>=0)),
        incoming_T=maxabs(T-expected)<=2e-6,weight_product=maxabs(w-T*a)<=2e-6,
        prefix_alpha=maxabs(A.ravel()-(1-after))<=2e-6,
        count=bool(np.all((sizes<=kmax)&(sizes<=e['count'].ravel()))),
        shortest_prefix=bool(np.all(before<tau*native.ravel()[valid])),
        stopping=bool(np.all((A>=tau*native)|(sizes.reshape(shape)==kmax)|(sizes.reshape(shape)==e['count']))))
    errors=dict(white_rgb=maxabs(replay+e['final_T'][...,None]-state['stock_rgb']),
                black_rgb=maxabs(replay-black),alpha=maxabs(A+e['tail_alpha']-native),
                final_T=maxabs(e['final_T']-e['native_final_T']),
                white_black_alpha=maxabs(1-(state['stock_rgb']-black)-native[...,None]),
                wrapper=maxabs(state['wrapper_rgb']-state['stock_rgb']),
                alpha_conservation=maxabs(A+e['tail_alpha']+e['final_T']-1))
    checks.update({key:value<=(2e-6 if key=='alpha_conservation' else 1/255) for key,value in errors.items()})
    quant=lambda x:dict(zip(['p50','p75','p90','p95','p99','max'],np.quantile(x,[.5,.75,.9,.95,.99,1]).tolist())) if len(x) else {}
    coverage=dict(roi_pixels=int(roi.sum()),mass_capture=float(A[roi].sum()/native[roi].sum()) if roi.any() else 0,
                  fraction_pixels_ge_90=float(np.mean(A[roi]>=.9*native[roi])) if roi.any() else 0,
                  reached_target_fraction=float(np.mean(A[roi]>=tau*native[roi])) if roi.any() else 0,
                  K_roi=quant(sizes.reshape(shape)[roi]),K_all=quant(sizes),
                  missing_alpha_mean=float(np.mean((native-A)[roi])) if roi.any() else 0)
    checks['coverage']=coverage['mass_capture']>=.9 and coverage['fraction_pixels_ge_90']>=.8
    memory=dict(stored_events=n,total_accepted_events=int(e['count'].sum()),
                csr_event_bytes=int(n*(8+8+7*4)),csr_offset_bytes=off.nbytes,
                csr_total_bytes=sum(v.nbytes for v in e.values()),dense_equivalent_event_bytes=int(pixels*kmax*(8+8+7*4)))
    metrics=dict(passed=all(checks.values()),checks=checks,errors=errors,coverage=coverage,memory=memory,
                 tau=tau,kmax=kmax,failed=[k for k,v in checks.items() if not v])
    return metrics,d
