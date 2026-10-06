"""Reference-only classes and fixed samplers, independent of kernel scores."""
from collections import Counter
import numpy as np
from scipy import ndimage as ndi
import legacy_evidence as legacy

def profile_vector(im,sample,linear=True):
    values = legacy.srgb_to_linear(im) if linear else np.asarray(im,dtype=np.float64)
    return legacy._sample_profile(values,sample)[1]

def signed_map(sample,shape):
    """Exact transpose of the bilinear fixed two-end-region sampler."""
    center=np.asarray(sample['center']); normal=np.asarray(sample['normal'],float)
    normal=normal/np.linalg.norm(normal); tangent=np.array([-normal[1],normal[0]])
    r=sample.get('radius',12); t=np.linspace(-r,r,sample.get('samples',97))
    p=center[None,None,:]+t[:,None,None]*normal+np.array([-1,0,1])[None,:,None]*tangent
    end=np.abs(t)>=.8*r
    points=p[end].reshape(-1,2)
    coeff=np.repeat(np.sign(t[end]),3)/((end.sum()/2)*3)
    result=np.zeros(shape,np.float64)
    x,y=points[:,0],points[:,1]; x0=np.floor(x).astype(int);y0=np.floor(y).astype(int)
    dx,dy=x-x0,y-y0
    for ix,iy,w in [(0,0,(1-dx)*(1-dy)),(1,0,dx*(1-dy)),(0,1,(1-dx)*dy),(1,1,dx*dy)]:
        xx,yy=x0+ix,y0+iy
        if np.any(xx<0) or np.any(xx>=shape[1]) or np.any(yy<0) or np.any(yy>=shape[0]):
            raise ValueError('fixed sample outside image')
        np.add.at(result,(yy,xx),coeff*w)
    return result.astype(np.float32)

def sample_band(sample,shape,width):
    yy,xx=np.indices(shape)
    n=np.asarray(sample['normal']);n=n/np.linalg.norm(n);cx,cy=sample['center']
    d=(xx-cx)*n[0]+(yy-cy)*n[1]
    tangent=-(xx-cx)*n[1]+(yy-cy)*n[0]
    return ((np.abs(d)<=width)&(np.abs(tangent)<=3)).astype(np.float32)

def classify_contrast(contrast,expected_visible=True):
    if not expected_visible and contrast<.02: return 'no_visible_edge'
    if contrast<.02: return 'low_contrast'
    return 'clear_color_transition'

def enrich(sample,rgb,aa,scene,key,kind,arc_length):
    s=dict(sample)
    s.update(id=f'{scene}/{key}/{kind}/{sample["id"]}',class_name=kind,
             gt_provenance='original TRAIN reference PNG; algorithmic profile quality, no human semantics',
             confidence='algorithmic_reference_only',semantic_internal_certified=False,
             surface_or_texture_type='unknown',arc_unique_id=f'{key}/{kind}/{sample.get("segment",sample["id"])}',
             arc_length_reference_pixels=float(arc_length),two_sides={'minus':'offset <= -0.8 radius', 'plus':'offset >= +0.8 radius'})
    p=profile_vector(rgb,s,False);t=np.linspace(-s.get('radius',12),s.get('radius',12),s.get('samples',97))
    lo=p[t<=-.8*s.get('radius',12)].mean(0);hi=p[t>=.8*s.get('radius',12)].mean(0)
    delta=hi-lo;norm=float(np.linalg.norm(delta))
    s.update(reference_native_profile=p.tolist(),reference_linear_profile=profile_vector(rgb,s,True).tolist(),
             reference_alpha_profile=profile_vector(np.repeat(aa[...,None],3,2),s,False)[:,0].tolist(),
             u=(delta/norm).tolist() if norm>.01 else None,c_star=((lo+hi)/2).tolist(),
             native_endpoint_contrast=norm,allow_rgb_score=norm>.01,
             fixed_evaluation_bands_px=[2,4])
    return s

def find_outline(rgb,aa,scene,key,maximum=3):
    strength,nx,ny,coherence=legacy._tensor_normals(aa,.8)
    ridge=legacy._nms(strength,nx,ny)&(strength>.02)&(coherence>.65)&(aa>.05)&(aa<.95)
    candidates=np.argwhere(ridge)
    order=sorted(candidates.tolist(),key=lambda yx:(-strength[tuple(yx)],yx[0],yx[1]))
    result=[]; rejects=Counter()
    for y,x in order:
        if any(np.linalg.norm(np.array([x,y])-s['center'])<24 for s in result):continue
        s=dict(id=f'alpha_{y:04d}_{x:04d}',center=[float(x),float(y)],normal=[float(nx[y,x]),float(ny[y,x])],
               radius=12.,samples=97,kind='outline',segment=0)
        offsets,p,error=legacy._sample_profile(np.repeat(aa[...,None],3,2),s)
        if error:rejects[error]+=1;continue
        if p[-1,0]<p[0,0]:s['normal']=(-np.array(s['normal'])).tolist()
        met=legacy._profile_metrics_linear(np.repeat(aa[...,None],3,2),[s])[0]
        if not met['valid'] or met['contrast']<.85 or abs(met.get('x50',99))>3:
            rejects[met['reason'] or 'alpha_quality']+=1;continue
        s['reference_width']=met['width'];s['reference_contrast']=met['contrast']
        # Arc scale is the nearby independently extracted AA ridge pixel count.
        length=int(ridge[max(0,y-12):y+13,max(0,x-12):x+13].sum())
        result.append(enrich(s,rgb,aa,scene,key,'outline',max(length,1)))
        if len(result)>=maximum:break
    return result,dict(rejects)

def find_flat(rgb,aa,samples,maximum=3):
    lum=legacy.srgb_to_linear(rgb)
    strength,*_=legacy._tensor_normals(lum,.8)
    dist=ndi.distance_transform_edt(aa>.995)
    mask=(dist>=16)&(ndi.maximum_filter(strength,size=13)<.006)
    ys,xs=np.nonzero(mask);order=np.lexsort((xs,ys))
    result=[]
    for j in order:
        x,y=int(xs[j]),int(ys[j])
        if any(np.linalg.norm(np.array([x,y])-s['center'])<24 for s in samples):continue
        if any(np.linalg.norm(np.array([x,y])-s['center'])<24 for s in result):continue
        patch=lum[y-6:y+7,x-6:x+7]
        if patch.std((0,1)).max()>.015:continue
        p=profile_vector(rgb,dict(center=[x,y],normal=[1,0],radius=12,samples=97),False)
        result.append(dict(id=f'flat_{y:04d}_{x:04d}',center=[x,y],normal=[1.,0.],radius=12.,samples=97,
                           class_name='flat_negative',roi=[x-6,y-6,x+7,y+7],confidence='algorithmic_reference_only',
                           gt_provenance='fixed low-gradient/low-variance original TRAIN RGB patch',
                           native_endpoint_contrast=float(np.linalg.norm(p[-8:].mean(0)-p[:8].mean(0)))))
        if len(result)>=maximum:break
    return result

def maps_from_samples(samples,shape,weighting='arc'):
    z=np.zeros(shape,np.float64)
    if not samples:return z.astype(np.float32)
    counts=Counter(s['arc_unique_id'] for s in samples)
    for s in samples:
        b=sample_band(s,shape,4)
        # Same band geometry in segment-equal and arc weighting ablation.
        w=(s['arc_length_reference_pixels'] if weighting=='arc' else 1.)/counts[s['arc_unique_id']]
        z += b*w/max(float(b.sum()),1.)
    return (z/max(float(z.sum()),1.)).astype(np.float32)

def build_reference(rgb,aa,scene,key):
    old=legacy.build_evidence(rgb,aa)
    internal=[]
    lengths={x['label']:x['ridge_pixels'] for x in old['segments'] if x['scale']==.8}
    for s in old['profiles']:
        if s['kind']=='internal':
            internal.append(enrich(s,rgb,aa,scene,key,'clear_color_transition',lengths.get(s['segment'],1)))
            if len(internal)>=2:break
    outline,rejects=find_outline(rgb,aa,scene,key)
    samples=outline+internal
    flat=find_flat(rgb,aa,samples)
    trusted=maps_from_samples(samples,aa.shape,'arc');equal=maps_from_samples(samples,aa.shape,'segment_equal')
    unknown=old['internal_band'].copy();unknown[trusted>0]=0
    narrow={str(w):np.max(np.stack([sample_band(s,aa.shape,w) for s in samples]),axis=0) if samples else np.zeros(aa.shape,np.float32) for w in (2,4)}
    meta=dict(old_metadata=old['metadata'],outline_alpha_rejections=rejects,classes={'outline':len(outline),'clear_color_transition':len(internal),'texture_detail_certified':0,'unknown_pixels':int((unknown>0).sum())},
              semantic_internal_status='UNCERTIFIED_NO_HUMAN_ANNOTATION',accepted_samples=len(samples),flat_negative_patches=len(flat),
              fixed_rules='v1 internal quality unchanged; AA profile contrast>=.85, coherence>.65, centered crossing<=3px; 24px spacing',
              broad_nonzero_area_fraction=float((old['internal_band']>0).sum()/max((aa>=.995).sum(),1)),
              broad_weighted_mass=float(np.mean(old['balanced_maps'],axis=0).sum()),
              weighted_mass_is_not_nonzero_area=True)
    return dict(samples=samples,flat=flat,metadata=meta),dict(rgb=rgb,aa=aa,broad=np.mean(old['balanced_maps'],axis=0),
         broad_band=old['internal_band'],trusted=trusted,trusted_equal=equal,unknown=unknown,band2=narrow['2'],band4=narrow['4'])
