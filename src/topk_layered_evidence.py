"""G0 calibration of front-to-back events from the pinned vanilla CUDA buffers.

No line detector may be implemented/run until this prerequisite passes.
"""
import ctypes
import numpy as np


def native_prefix(state, height, width, k, library):
    """Read first k accepted native events; preserve the omitted tail explicitly."""
    validate_native_state(state,height,width,k)
    lib=ctypes.CDLL(str(library));fn=lib.topk_prefix
    fn.argtypes=[ctypes.c_int]*3+[ctypes.c_void_p]*10;fn.restype=None
    arrays=[np.ascontiguousarray(state[key],dtype=dtype) for key,dtype in
            [('means2D','f4'),('conic','f4'),('depths','f4'),('rgb','f4'),('point_list','u4'),('ranges','u4')]]
    ids=np.full((height,width,k),-1,'i8');events=np.zeros((height,width,k,7),'f4')
    tail=np.zeros((height,width,5),'f4');count=np.zeros((height,width),'i8')
    fn(height,width,k,*[a.ctypes.data for a in arrays],ids.ctypes.data,events.ctypes.data,tail.ctypes.data,count.ctypes.data)
    return dict(ids=ids,z=events[...,0],alpha=events[...,1],T=events[...,2],w=events[...,3],rgb=events[...,4:7],tail_rgb=tail[...,:3],tail_alpha=tail[...,3],final_T=tail[...,4],count=count)


def validate_native_state(state, height, width, k):
    if any(not isinstance(v,(int,np.integer)) or v<=0 for v in [height,width,k]):
        raise ValueError('positive integer dimensions and k required')
    n=len(state['depths']);tiles=((width+15)//16)*((height+15)//16)
    shapes=dict(means2D=(n,2),conic=(n,4),depths=(n,),rgb=(n,3),ranges=(tiles,2))
    for key,shape in shapes.items():
        a=np.asarray(state[key])
        if a.shape!=shape or not np.isfinite(a).all():raise ValueError('invalid '+key)
    ids=np.asarray(state['point_list']);ranges=np.asarray(state['ranges'])
    if ids.ndim!=1 or not np.issubdtype(ids.dtype,np.integer) or np.any(ids<0) or np.any(ids>=n):raise ValueError('invalid point_list')
    if not np.issubdtype(ranges.dtype,np.integer) or np.any(ranges<0) or np.any(ranges>len(ids)) or np.any(ranges[:,0]>ranges[:,1]):raise ValueError('invalid ranges')


def prefix_calibration(e, state, black):
    """All G0 event/replay/tail checks. Coverage uses native alpha, never top-k ROI."""
    ids=e['ids'];valid=ids>=0;z=e['z'];a=e['alpha'];T=e['T'];w=e['w']
    n=len(state['depths']);depth=state['depths'][np.clip(ids,0,max(0,n-1))]
    maxabs=lambda x:float(np.max(np.abs(x),initial=0))
    finite=all(np.isfinite(v).all() for v in e.values())
    expected_T=np.concatenate([np.ones_like(a[...,:1]),np.cumprod(1-a[...,:-1],axis=-1)],axis=-1)
    checks=dict(finite=finite,ids=bool(np.all((ids==-1)|((ids>=0)&(ids<n)))),
        contiguous=bool(np.all(~valid[...,1:]|valid[...,:-1])),
        original_depth=bool(np.all(np.abs(z[valid]-depth[valid])<=1e-5*(1+np.abs(depth[valid])))),
        depth_order=bool(np.all((~valid[...,1:])|(np.diff(z,axis=-1)>=-1e-6*np.maximum(1,np.abs(z[...,:-1]))))),
        unique_ids=all(not np.any((ids[...,i]==ids[...,j])&valid[...,i]&valid[...,j]) for i in range(ids.shape[-1]) for j in range(i)),
        padding=all(np.all(e[key][~valid]==0) for key in ['z','alpha','T','w','rgb']),
        ranges=bool(np.all((a[valid]>=1/255)&(a[valid]<=.99)) and np.all((T[valid]>0)&(T[valid]<=1)) and np.all(w>=0)),
        incoming_T=maxabs((T-expected_T)[valid])<=2e-6,
        weight_product=maxabs(w-T*a)<=2e-6,
        prefix_alpha=maxabs(w.sum(-1)-(1-np.prod(1-a,axis=-1)))<=2e-6)
    replay=(w[...,None]*e['rgb']).sum(-2)+e['tail_rgb']
    native_alpha=1-state['final_T'];full_alpha=w.sum(-1)+e['tail_alpha']
    errors=dict(white_rgb=maxabs(replay+e['final_T'][...,None]-state['stock_rgb']),
        black_rgb=maxabs(replay-black),alpha=maxabs(full_alpha-native_alpha),
        white_black_alpha=maxabs(1-(state['stock_rgb']-black)-native_alpha[...,None]),
        final_T=maxabs(e['final_T']-state['final_T']),wrapper=maxabs(state['wrapper_rgb']-state['stock_rgb']))
    checks.update({key:bool(np.isfinite(value) and value<=1/255) for key,value in errors.items()})
    roi=native_alpha>=.5;coverage={}
    for k in [4,8,16]:
        captured=w[...,:k].sum(-1);ratios=captured[roi]/native_alpha[roi]
        coverage[str(k)]=dict(roi_pixels=int(roi.sum()),mass_capture=float(captured[roi].sum(dtype='f8')/native_alpha[roi].sum(dtype='f8')) if roi.any() else 0.,fraction_pixels_ge_90=float(np.mean(ratios>=.9)) if roi.any() else 0.,ratio_quantiles=np.quantile(ratios,[0,.1,.5,.9,1]).tolist() if roi.any() else [],missing_alpha_mean=float(np.mean(native_alpha[roi]-captured[roi])) if roi.any() else 0.)
    checks['coverage_k8']=coverage['8']['mass_capture']>=.9 and coverage['8']['fraction_pixels_ge_90']>=.8
    return dict(passed=all(checks.values()),checks=checks,errors=errors,coverage=coverage,failed=[k for k,v in checks.items() if not v])


def prefix_diagnostics(e, k):
    w=np.asarray(e['w'][...,:k],dtype='f8');z=e['z'][...,:k]
    A=w.sum(-1);p=w/np.maximum(A[...,None],1e-12);valid=A>0
    mean=(p*z).sum(-1);median_index=np.argmax(np.cumsum(p,axis=-1)>=.5,axis=-1)
    median=np.take_along_axis(z,median_index[...,None],axis=-1)[...,0]
    return dict(A=A,z_mean=mean,z_front=np.where(valid,z[...,0],0),z_50=np.where(valid,median,0),z_var=(p*(z-mean[...,None])**2).sum(-1),H_id=-(p*np.log(np.maximum(p,1e-12))).sum(-1),valid=valid)
