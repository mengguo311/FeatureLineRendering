"""Symmetric actual-image correspondence; identical proxy reference for both arms."""
import runtime
import numpy as np
from scipy import ndimage
from geometry import project,backproject

def sample(image,uv,order=1,cval=0.):
    shape=uv.shape[:-1];p=uv.reshape(-1,2)
    return ndimage.map_coordinates(image,[p[:,1],p[:,0]],order=order,mode='constant',cval=cval).reshape(shape)

def correspondence(depth_a,mask_a,ca,depth_b,mask_b,cb,tolerance=.004):
    h,w=depth_a.shape;y,x=np.mgrid[:h,:w];valid=mask_a&np.isfinite(depth_a)
    uv=np.full((h,w,2),-100.,float);z=np.zeros((h,w))
    p=backproject(np.column_stack([x[valid],y[valid]]),depth_a[valid],ca);q,zz=project(p,cb);uv[valid]=q;z[valid]=zz
    inside=valid&(uv[:,:,0]>=0)&(uv[:,:,0]<=w-1)&(uv[:,:,1]>=0)&(uv[:,:,1]<=h-1)&(z>.2)
    # Bilinear interpolation only on an all-finite footprint; do not blend through holes.
    finite=np.isfinite(depth_b);safe=np.where(finite,depth_b,0.)
    support=sample(finite.astype(float),uv)>1-1e-8
    label=sample(mask_b.astype(float),uv,0)>.5
    dz=np.abs(sample(safe,uv)-z)
    ok=inside&support&label&(dz<=tolerance)
    return uv,ok,dict(source_target_pixels=int(valid.sum()),inside=int(inside.sum()),target_label=int((inside&label).sum()),
        common_visible_pixels=int(ok.sum()),depth_or_hole_rejected=int((inside&label&~(support&(dz<=tolerance))).sum()),tolerance=tolerance)

def compare(a,b,uv,ok):
    warped=sample(b,uv);delta=np.abs(a-warped);den=float(np.maximum(a,warped)[ok].sum())
    am=a>1/255;bm=warped>1/255
    # Symmetric directions are evaluated separately by the caller, never nearest match to B1.
    distance=ndimage.distance_transform_edt(b<=1/255)
    dist=sample(distance,uv,cval=float(max(b.shape)))
    selected=ok&am
    return dict(common_pixels=int(ok.sum()),own_mass=float(a[ok].sum()),warped_mass=float(warped[ok].sum()),
        L1=float(delta[ok].sum()),L1_per_common_pixel=float(delta[ok].mean()) if ok.any() else None,
        L1_per_union_ink= float(delta[ok].sum()/den) if den>0 else None,
        source_ink_pixels=int(selected.sum()),ink_to_empty_pixels=int((selected&~bm).sum()),empty_to_ink_pixels=int((ok&~am&bm).sum()),
        own_ink_distance_mean_px=float(dist[selected].mean()) if selected.any() else None,
        own_ink_distance_p95_px=float(np.quantile(dist[selected],.95)) if selected.any() else None,
        scope='Actual AA own-ink footprint distance and symmetric proxy-warp L1; not independent physical GT or stable stroke ID')
