"""TRAIN evidence -> foreground-layer Gaussian-ID weighted 3D anchors.
No depth backprojection in the method; backprojection is a diagnostic comparator.
"""
import numpy as np
from .common import project


def anchor_samples(g,cam,pixels,tangent,ids,weights,median_depth,cfg,spacing):
    n=len(pixels);safe=np.maximum(ids,0);xyz=g['mu'][safe]
    z=(xyz@cam.w2c[2,:3])+cam.w2c[2,3]
    tolerance=np.maximum(cfg['layer_spacing']*spacing,cfg['layer_rel_tol']*median_depth)
    layer=(ids>=0)&(abs(z-median_depth[:,None])<=tolerance[:,None])
    layer_mass=(weights*layer).sum(1);w=weights*layer/np.maximum(layer_mass[:,None],1e-12)
    anchor=(w[:,:,None]*xyz).sum(1)
    dominant=np.argmax(w,axis=1);center=xyz[np.arange(n),dominant]
    distance=np.linalg.norm(anchor-center,axis=1)
    uv,az=project(anchor,cam);error=np.linalg.norm(uv-pixels,axis=1)
    Kinv=np.linalg.inv(cam.K);ray=np.c_[pixels,np.ones(n)]@Kinv.T;ray/=ray[:,2:3]
    ray2=np.c_[pixels+tangent,np.ones(n)]@Kinv.T;ray2/=ray2[:,2:3]
    plane=np.cross(ray,ray2)@cam.w2c[:3,:3]
    plane/=np.maximum(np.linalg.norm(plane,axis=1,keepdims=True),1e-12)
    lift=(ray2-ray)@cam.w2c[:3,:3];lift/=np.maximum(np.linalg.norm(lift,axis=1,keepdims=True),1e-12)
    bp=(ray*median_depth[:,None]-cam.w2c[:3,3])@cam.w2c[:3,:3]
    buv,_=project(bp,cam)
    valid=(np.isfinite(median_depth)&(median_depth>0)&(layer_mass>=cfg['min_layer_mass'])&
        (distance<=cfg['max_dominant_distance_spacing']*spacing)&(error<=cfg['max_reprojection_px'])&(az>0))
    reason=np.full(n,'accepted',dtype='<U32')
    reason[error>cfg['max_reprojection_px']]='reprojection'
    reason[distance>cfg['max_dominant_distance_spacing']*spacing]='dominant_neighborhood'
    reason[layer_mass<cfg['min_layer_mass']]='cross_depth_layer'
    reason[~np.isfinite(median_depth)|(median_depth<=0)]='background'
    return dict(anchor=anchor,plane=plane,lift=lift,ids=np.where(layer,ids,-1),weights=w,
        valid=valid,reason=reason,layer_mass=layer_mass,reprojection_error=error,
        depth_relative_error=abs(az-median_depth)/np.maximum(median_depth,1e-9),
        backprojection=bp,backprojection_error=np.linalg.norm(buv-pixels,axis=1),
        reprojection=uv,anchor_backprojection_distance=np.linalg.norm(anchor-bp,axis=1))


def merge_observations(parts):
    if not parts:return {}
    return {k:np.concatenate([p[k] for p in parts]) for k in parts[0]}


def subset(obs,keep):return {k:v[keep] for k,v in obs.items()}
