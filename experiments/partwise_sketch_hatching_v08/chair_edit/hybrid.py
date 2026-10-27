"""Original-row paper substrate and explicitly proxy-carried ink."""
import runtime
import numpy as np
from scipy import ndimage
from membership import evaluated_tint_copy

def region_strength(binding, region=4):
    n=len(binding['source_index'])
    if not np.array_equal(binding['source_index'],np.arange(n)):
        raise ValueError('binding must preserve complete original PLY row order')
    q=np.asarray(binding['membership'],float)
    if q.shape!=(n,6) or not np.isfinite(q).all() or (q<0).any() or (q>1+1e-12).any():
        raise ValueError('invalid membership')
    good=(binding['region_id']==region)&~binding['unknown']
    return np.where(good,q[:,region],0.)

def paper_copy(a,c,strength,paper):
    s=np.asarray(strength,float)
    if s.shape!=(len(a['means']),) or not np.isfinite(s).all() or (s<0).any() or (s>1).any():
        raise ValueError('one finite [0,1] strength per original row')
    return evaluated_tint_copy(a,c,s,paper)

def compose(paper,ink,support,gated,scale=1.,ink_color=.03):
    paper=np.asarray(paper);ink=np.asarray(ink);support=np.asarray(support)
    if paper.shape!=ink.shape+(3,) or support.shape!=ink.shape:
        raise ValueError('same-camera source / ink / support shapes required')
    if not all(np.isfinite(x).all() for x in (paper,ink,support)):
        raise ValueError('nonfinite compositor input')
    if (ink<0).any() or (ink>1+1e-6).any() or (support<0).any() or (support>1+1e-6).any() or not 0<=scale<=1:
        raise ValueError('invalid alpha or scale')
    alpha=ink*np.clip(support,0,1)*scale if gated else ink*scale
    result=paper*(1-alpha[:,:,None])+ink_color*alpha[:,:,None]
    return result,alpha

def edit_metrics(original,edited,regions,region=4,band=2):
    raw=np.abs(edited-original).sum(2)
    clipped=np.abs(np.clip(edited,0,1)-np.clip(original,0,1)).sum(2)
    target=regions==region
    inner=ndimage.binary_erosion(target,iterations=band)
    near=ndimage.binary_dilation(target,iterations=band)
    masks=dict(target_full=target,target_interior=inner,boundary=near&~inner,
               far_other=(regions>0)&~near,far_background=(regions==0)&~near)
    out=dict(raw_total_L1=float(raw.sum()),clipped_total_L1=float(clipped.sum()))
    for name,mask in masks.items():
        count=int(mask.sum())
        out[name]=dict(pixels=count,raw_L1_sum=float(raw[mask].sum()),clipped_L1_sum=float(clipped[mask].sum()),
            raw_L1_mean=float(raw[mask].mean()) if count else None,
            clipped_L1_mean=float(clipped[mask].mean()) if count else None,
            visible_fraction_1_255=float((clipped[mask]>1/255).mean()) if count else None,
            useful_fraction_0_05=float((clipped[mask]>=.05).mean()) if count else None)
    far=masks['far_other']|masks['far_background']
    out['far_raw_fraction']=float(raw[far].sum()/max(raw.sum(),1e-30))
    out['far_clipped_fraction']=float(clipped[far].sum()/max(clipped.sum(),1e-30))
    return out

def ink_metrics(paper,hybrid,ink_alpha,reference_ink,regions):
    target=regions==4; near=ndimage.binary_dilation(target,iterations=2)
    raw=np.abs(hybrid-paper).sum(2)
    return dict(alpha_mass=float(ink_alpha.sum()),target_alpha_mass=float(ink_alpha[target].sum()),
        retained_target_ink_fraction=float(ink_alpha[target].sum()/max(reference_ink[target].sum(),1e-30)),
        raw_visible_ink_L1=float(raw.sum()),target_visible_ink_L1=float(raw[target].sum()),
        far_visible_ink_L1=float(raw[~near].sum()),
        target_reference_ink_pixels=int((reference_ink[target]>1/255).sum()),
        target_visible_ink_pixels=int((ink_alpha[target]>1/255).sum()))
