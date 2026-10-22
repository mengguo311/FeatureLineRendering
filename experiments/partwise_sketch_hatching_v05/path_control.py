"""Bounded authored paths to original-row control; no physical attachment claim."""
import runtime
import numpy as np
from scipy import ndimage
from geometry import project

def aggregate_path(n,ps):
    """Count a pixel/source event once per view, retaining every raw anchor in CSR."""
    anchor=np.repeat(np.arange(len(ps['sample_index'])),np.diff(ps['offsets']))
    sid=ps['sample_index'][anchor];ids=ps['source_index']
    if not len(ids):return np.zeros(n),np.zeros(n)
    key=sid.astype(np.int64)*n+ids
    unique,first,inverse=np.unique(key,return_index=True,return_inverse=True)
    eligible=np.zeros(len(unique),bool)
    np.logical_or.at(eligible,inverse,ps['eligible'])
    weights=ps['weight'][first];source=ids[first]
    total=np.bincount(source,weights,minlength=n)
    accepted=np.bincount(source,weights*eligible,minlength=n)
    return total,accepted

def resolve_path(per_view_total,per_view_accepted,binding):
    total=per_view_total.sum(0);accepted=per_view_accepted.sum(0)
    fraction=np.divide(accepted,total,out=np.zeros_like(total),where=total>0)
    views=(per_view_accepted>=.002).sum(0)
    good=(accepted>=.02)&(views>=2)&(fraction>=.7)&(binding['region_id']==4)&~binding['unknown']
    reason=np.full(len(total),'path_depth_mixed',dtype='<U24')
    reason[views<2]='path_few_views';reason[accepted<.02]='path_low_exposure'
    reason[total==0]='path_unobserved'
    reason[(binding['region_id']!=4)&~binding['unknown']]='other_region'
    reason[binding['unknown']]='region_unknown';reason[good]='supported'
    strength=np.where(good,fraction*np.minimum(accepted/.1,1.),0.)
    return dict(source_index=np.arange(len(total)),per_view_total=per_view_total,
                per_view_accepted=per_view_accepted,total=total,accepted=accepted,
                rejected=total-accepted,fraction=fraction,distinct_views=views,
                unknown=~good,reason=reason,strength=strength)

def opacity_copy(a,strength,scale=1.):
    s=np.asarray(strength,float)
    if s.shape!=a['opacity'].shape or not np.isfinite(s).all() or (s<0).any() or (s>1).any() or not 0<=scale<=1:
        raise ValueError('opacity attenuation needs one [0,1] strength per original row and [0,1] scale')
    return dict(a,opacity=a['opacity']*(1-scale*s))

def match_nonlinear(arms,effect):
    """Actual BUILD RGB L1, bounded bisection; never tune on evaluation views.

    RGB L1 need not be globally monotone. Only observed brackets are used and
    the final error is validated. A failed match stays invalid, not a new gate.
    """
    history={k:[] for k in arms}
    def value(k,x):
        y=float(effect(k,x));history[k].append(dict(scale=x,L1=y));return y
    upper={k:value(k,.85) for k in arms}
    target=.7*min(upper.values())
    if not np.isfinite(target) or target<=1e-10:
        return {k:0. for k in arms},dict(target=target,valid=False,reason='zero visible headroom',history=history)
    scales={};actual={}
    for k in arms:
        lo=0.;hi=.85;best=(abs(upper[k]-target),hi,upper[k])
        for _ in range(10):
            mid=(lo+hi)/2;y=value(k,mid)
            if abs(y-target)<best[0]:best=(abs(y-target),mid,y)
            if y<target:lo=mid
            else:hi=mid
        scales[k]=best[1];actual[k]=best[2]
    error=max(abs(x-target)/target for x in actual.values())
    return scales,dict(target=target,full_scale=.85,upper_effect=upper,actual=actual,
                       maximum_relative_error=error,valid=error<=.01,history=history,
                       scope='actual complete-source renders, fixed BUILD grid RGB L1; no evaluation matching')

def path_mask(mesh_depth,regions,paths,c,radius=3.,depth_tolerance=.02):
    """Fixed visible 3px-radius capsules around chosen saved 3D segments."""
    mask=np.zeros_like(regions,bool)
    for points in paths['points']:
        uv,z=project(points,c)
        if (z<=.2).any():continue
        d=uv[1]-uv[0];length2=float(d@d)
        if length2<1e-14:continue
        lo=np.maximum(0,np.ceil(np.min(uv,axis=0)-radius)).astype(int)
        hi=np.minimum([c['width']-1,c['height']-1],np.floor(np.max(uv,axis=0)+radius)).astype(int)
        if (hi<lo).any():continue
        yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        t=np.clip(((xx-uv[0,0])*d[0]+(yy-uv[0,1])*d[1])/length2,0,1)
        inside=(xx-uv[0,0]-t*d[0])**2+(yy-uv[0,1]-t*d[1])**2<=radius**2
        zz=1/((1-t)/z[0]+t/z[1])
        dep=mesh_depth[yy,xx]
        inside &= (regions[yy,xx]==4)&np.isfinite(dep)&(np.abs(zz-dep)<=depth_tolerance)
        mask[yy,xx]|=inside
    return mask
