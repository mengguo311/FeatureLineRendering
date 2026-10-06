"""Fixed target region and actual rerender metrics. Holes are alpha losses."""
import numpy as np
from scipy.ndimage import map_coordinates

def profile(rgb,p,n):
    offsets=np.arange(-8,9)
    coords=p[:,None,:]+offsets[None,:,None]*n[:,None,:]
    samples=np.stack([map_coordinates(c,[coords[...,0],coords[...,1]],order=1,mode='constant',cval=1.) for c in rgb],axis=-1)
    strength=np.linalg.norm(np.diff(samples,axis=1),axis=2)
    mid=(offsets[:-1]+offsets[1:])/2
    mass=strength.sum(1); active=mass>1e-8
    if not np.any(active): return dict(contrast=0.,location_pixels=0.,width_pixels=0.,active_profiles=0)
    loc=(strength[active]*mid).sum(1)/mass[active]
    width=np.sqrt((strength[active]*(mid[None,:]-loc[:,None])**2).sum(1)/mass[active])
    # +/-4 frozen target contrast; all samples from actual native rerender.
    contrast=np.linalg.norm(samples[:,12]-samples[:,4],axis=1)
    return dict(contrast=float(contrast.mean()),location_pixels=float(loc.mean()),width_pixels=float(width.mean()),
        active_profiles=int(active.sum()))

def causal_metrics(original,deleted,alpha,deleted_alpha,sdf,p,n):
    mse=((original-deleted)**2).mean(0)
    def avg(a,mask): return float(a[mask].mean()) if mask.any() else 0.
    before,after=profile(original,p,n),profile(deleted,p,n)
    out={f'{key}_{label}':val for label,v in [('before',before),('after',after)] for key,val in v.items()}
    for key in ('contrast','location_pixels','width_pixels'): out[key+'_change']=after[key]-before[key]
    for width in (2,4):
        mask=np.abs(sdf)<=width
        out[f'ring{width}_mse']=avg(mse,mask)
        out[f'ring{width}_alpha_loss_mean']=avg(alpha-deleted_alpha,mask)
        out[f'ring{width}_pixels']=int(mask.sum())
    outside=np.abs(sdf)>4; exterior=sdf < -4; interior=sdf>4
    for key,mask in [('outside4',outside),('exterior4',exterior),('interior4',interior)]:
        out[key+'_mse']=avg(mse,mask);out[key+'_pixels']=int(mask.sum())
    out['alpha_foreground_lost_pixels']=int(((alpha>.5)&(deleted_alpha<=.5)).sum())
    out['alpha_loss_sum']=float((alpha-deleted_alpha).sum())
    out['full_image_mse']=float(mse.mean())
    return out

def footprint_stats(contribution,sdf,centers):
    total=float(contribution.sum()); h,w=sdf.shape
    inside=(centers[:,0]>=0)&(centers[:,0]<h)&(centers[:,1]>=0)&(centers[:,1]<w)
    distances=np.full(len(centers),np.inf)
    distances[inside]=np.abs(map_coordinates(sdf,[centers[inside,0],centers[inside,1]],order=1))
    return dict(full_T_selected_mass=total,
        ring2_mass_fraction=float(contribution[np.abs(sdf)<=2].sum()/max(total,1e-12)),
        ring4_mass_fraction=float(contribution[np.abs(sdf)<=4].sum()/max(total,1e-12)),
        outside4_mass_fraction=float(contribution[np.abs(sdf)>4].sum()/max(total,1e-12)),
        interior4_mass_fraction=float(contribution[sdf>4].sum()/max(total,1e-12)),
        exterior4_mass_fraction=float(contribution[sdf< -4].sum()/max(total,1e-12)),
        selected_centers_within4_fraction=float((distances<=4).mean()) if len(centers) else 0.,
        selected_centers_outside_image=int((~inside).sum()))
