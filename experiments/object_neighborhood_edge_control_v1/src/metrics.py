"""Pilot metrics. Unavailable LPIPS/FLIP or temporal quantities remain null."""
import numpy as np
from scipy.ndimage import binary_dilation, binary_erosion, map_coordinates
from edge_profiles import measure

def visible_band(ids,radius=12):
    a=ids==1;b=ids==2
    interface=(a & binary_dilation(b))|(b & binary_dilation(a))
    # Remove object/background and image-border junctions.
    interface &= binary_erosion(ids>0,iterations=4)
    return binary_dilation(interface,iterations=radius),interface

def profiles(rgb,ids,contrast_min=.02):
    result=[];h,w=ids.shape;t=np.linspace(-24,24,193)
    for y in np.linspace(h*.36,h*.64,17).astype(int):
        edge=np.flatnonzero(((ids[y,:-1]==1)&(ids[y,1:]==2)))
        if len(edge)!=1:continue
        x=float(edge[0])+.5
        if x<25 or x>w-26:continue
        p=np.stack([map_coordinates(rgb[...,ch],[np.full_like(t,y),x+t],order=1,mode='nearest') for ch in range(3)],axis=1)
        result.append(measure(t,p,contrast_min=contrast_min))
    return result

def boundary_iou(a,b,ratio=.02):
    # R18 distance-to-interior-boundary band (mask & ~eroded-mask), not colour band.
    r=max(1,int(round(ratio*np.hypot(*a.shape))))
    import cv2
    def boundary(mask):
        mask=mask.astype(np.uint8)
        pad=cv2.copyMakeBorder(mask,1,1,1,1,cv2.BORDER_CONSTANT,value=0)
        return mask-cv2.erode(pad,np.ones((3,3),np.uint8),iterations=r)[1:-1,1:-1]
    x=boundary(a).astype(bool);y=boundary(b).astype(bool)
    return float((x&y).sum()/max((x|y).sum(),1))

def evaluate_frame(image,reference,ids,objects,alpha,depth_proxy,depth_gt,baseline=None):
    band,_=visible_band(ids);fg=ids>0
    reliable=binary_erosion(fg,iterations=4)&~binary_dilation(band,iterations=3)
    p=profiles(image,ids);q=profiles(reference,ids)
    widths=[abs(a['width_px']-b['width_px']) for a,b in zip(p,q) if a['width_px'] is not None and b['width_px'] is not None]
    dc=[abs(a['deltaE76_D65_2deg']-b['deltaE76_D65_2deg']) for a,b in zip(p,q) if a['deltaE76_D65_2deg'] is not None and b['deltaE76_D65_2deg'] is not None]
    pred=np.argmax(objects,axis=-1)+1
    pred[alpha<.5]=0;pred[pred==3]=-1
    total=objects.sum(-1);foreign=np.zeros_like(alpha)
    for k in (1,2):
        reliable_k=binary_erosion(ids==k,iterations=4)&~band
        foreign[reliable_k]=total[reliable_k]-objects[...,k-1][reliable_k]
    internal=(binary_erosion(ids==1,iterations=4)|binary_erosion(ids==2,iterations=4))&~band
    mse=float(np.mean((image-reference)**2))
    from skimage.metrics import structural_similarity
    out={'psnr_linear_db':float(-10*np.log10(max(mse,1e-15))),
        'ssim_linear':float(structural_similarity(reference,image,data_range=1,channel_axis=2)),
        'edge_mse_linear':float(np.mean((image[band]-reference[band])**2)) if band.any() else None,
        'W_abs_error_px':float(np.mean(widths)) if widths else None,
        'D_deltaE76_abs_error':float(np.mean(dc)) if dc else None,
        'profile_measurement_fraction':sum(x['width_px'] is not None for x in p)/max(len(p),1),
        'reference_measurement_fraction':sum(x['width_px'] is not None for x in q)/max(len(q),1),
        'profile_refusal_reasons':{s:sum(x['reason']==s for x in p) for s in ('low_contrast','complex_profile','crossing_missing')},
        'foreground_holes_alpha_lt_095':float(np.mean(alpha[reliable]<.95)) if reliable.any() else None,
        'foreign_contribution_ratio':float(foreign[internal].sum()/max(total[internal].sum(),1e-8)),
        'mask_iou':float(np.mean([(np.logical_and(pred==k,ids==k)).sum()/max(np.logical_or(pred==k,ids==k).sum(),1) for k in (1,2)])),
        'boundary_iou':float(np.mean([boundary_iou(pred==k,ids==k) for k in (1,2)])),
        'depth_center_proxy_abs_error':float(np.abs(depth_proxy[reliable]-depth_gt[reliable]).mean()) if reliable.any() else None,
        'depth_proxy_is_surface_accuracy':False,
        'outside_rgb_change_mse':float(np.mean((image[~band]-baseline[~band])**2)) if baseline is not None else 0.,
        'LPIPS':None,'FLIP':None,'pixel_temporal_residual':None}
    return out,p,q
