"""Continuous authored-profile oracle used ONLY by scoring, never render arms."""
import numpy as np

def ray_depth(asset, origins, directions):
    o, ray = np.broadcast_arrays(np.asarray(origins,float),np.asarray(directions,float))
    depth=np.full(o.shape[:-1],np.inf); labels=np.zeros(depth.shape,np.int32)
    def submit(t,valid,part):
        good=valid & np.isfinite(t) & (t>0) & (t<depth)
        depth[good]=t[good]; labels[good]=int(part)
    for part,profile in asset['profiles_ry'].items():
        for (r0,y0),(r1,y1) in zip(profile[:-1],profile[1:]):
            if abs(y1-y0)<1e-12:
                t=np.divide(y0-o[...,1],ray[...,1],out=np.full_like(depth,np.inf),where=np.abs(ray[...,1])>1e-12)
                with np.errstate(invalid='ignore'):
                    rho=np.hypot(o[...,0]+t*ray[...,0],o[...,2]+t*ray[...,2])
                submit(t,(rho>=min(r0,r1)-1e-10)&(rho<=max(r0,r1)+1e-10),part)
            else:
                m=(r1-r0)/(y1-y0); b=r0-m*y0
                r=m*o[...,1]+b; dr=m*ray[...,1]
                a=ray[...,0]**2+ray[...,2]**2-dr**2
                bb=2*(o[...,0]*ray[...,0]+o[...,2]*ray[...,2]-r*dr)
                c=o[...,0]**2+o[...,2]**2-r**2
                disc=bb**2-4*a*c
                for sign in (-1,1):
                    t=np.divide(-bb+sign*np.sqrt(np.maximum(disc,0)),2*a,out=np.full_like(depth,np.inf),where=np.abs(a)>1e-12)
                    linear=(np.abs(a)<=1e-12)&(np.abs(bb)>1e-12)
                    t[linear]=-c[linear]/bb[linear]
                    with np.errstate(invalid='ignore'): yy=o[...,1]+t*ray[...,1]
                    submit(t,(disc>=0)&(yy>=min(y0,y1)-1e-10)&(yy<=max(y0,y1)+1e-10),part)
    return depth,labels

def screen_depth(asset,camera,uv):
    direction=np.concatenate(((np.asarray(uv)-camera['center'])/camera['focal'],np.ones((*np.asarray(uv).shape[:-1],1))),axis=-1)@camera['R']
    return ray_depth(asset,np.asarray(camera['eye']),direction)

def mask_regions(labels,part,band_px=2):
    from scipy import ndimage
    target=labels==part
    distance=ndimage.distance_transform_edt(~target)
    return dict(target=target,aa_band=(~target)&(distance<=band_px),
                far_other=(labels>0)&(~target)&(distance>band_px),
                far_background=(labels==0)&(distance>band_px))

def part_leakage(hatch,labels,part):
    masks=mask_regions(labels,part)
    masses={key:float(hatch[mask].sum()) for key,mask in masks.items()}
    return dict(ink_mass=float(hatch.sum()),region_ink=masses,
                region_pixels={key:int(mask.sum()) for key,mask in masks.items()},
                far_wrong_part_fraction=masses['far_other']/max(float(hatch.sum()),1e-15),
                far_background_fraction=masses['far_background']/max(float(hatch.sum()),1e-15),
                scope='Isolated part hatch against continuous analytic GT labels. AA band fixed2px; no hidden-surface attribution from aggregate pixel overlap.')
