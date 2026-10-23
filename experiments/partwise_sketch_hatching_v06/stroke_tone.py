"""Fixed per-stroke two-sided orientation tone on unchanged proxy paths.

Capsule/visibility arithmetic is copied from v06 render._coverage. Only the
value stored in a visible fragment changes; max is applied before 2x resolve.
The scalar tone is stylized, not measured illumination or surface truth.
"""
import runtime
import numpy as np
from geometry import ray_surface,project
from hatching import layer_ids,visibility_masks,validate_style

ARMS=('constant','tone','shuffled')
LIGHT=np.array([-.4,-.6,.7])


def stroke_tones(mesh,paths,light=LIGHT,seed=1729):
    light=np.asarray(light,float);light=light/np.linalg.norm(light)
    ids,inverse=np.unique(paths['stroke_id'],return_inverse=True)
    lengths=np.linalg.norm(paths['points'][:,1]-paths['points'][:,0],axis=1)
    if not np.isfinite(lengths).all():raise ValueError('nonfinite path')
    normals=np.asarray(mesh['normals'][paths['face']],float)
    norm=np.linalg.norm(normals,axis=1);valid=np.isfinite(normals).all(1)&(norm>1e-12)
    response=np.zeros(len(lengths),float)
    response[valid]=np.clip(np.abs((normals[valid]/norm[valid,None])@light),0,1)
    total=np.bincount(inverse,weights=lengths,minlength=len(ids))
    mean=np.divide(np.bincount(inverse,weights=lengths*response,minlength=len(ids)),total,
                   out=np.zeros(len(ids)),where=total>1e-12)
    tau=.2+.8*(1-mean);layers=layer_ids(paths);stroke_layers=[]
    for i in range(len(ids)):
        unique=np.unique(layers[inverse==i])
        if len(unique)!=1:raise ValueError('stroke identity spans direction layers')
        stroke_layers.append(unique[0])
    stroke_layers=np.asarray(stroke_layers,np.uint8)
    rng=np.random.default_rng(seed);shuffle=np.arange(len(ids))
    for layer in np.unique(stroke_layers):
        ii=np.flatnonzero(stroke_layers==layer);shuffle[ii]=rng.permutation(ii)
    weights=dict(stroke_id=ids,layer_id=stroke_layers,stroke_length=total,orientation_response=mean,
        constant_tau=np.ones(len(ids)),tone_tau=tau,shuffled_tau=tau[shuffle],
        shuffle_source_stroke_id=ids[shuffle],segment_stroke_index=inverse,segment_length=lengths,
        segment_face_response=response,degenerate_segment=~valid,light=light)
    stats=dict(strokes=len(ids),segments=len(lengths),degenerate_normal_segments=int((~valid).sum()),
        degenerate_world_length=float(lengths[~valid].sum()),zero_length_strokes=int((total<=1e-12).sum()),
        tau_min=float(tau.min()),tau_max=float(tau.max()),tau_mean=float(tau.mean()),
        tau_length_mean=float(np.average(tau,weights=total)),seed=seed,
        rule='tau_s=1-.8*length_mean(abs(unit_face_normal dot unit_world_light)); invalid normal response=0; zero-length stroke tau=1',
        scope='Fixed proxy stroke attribute; not Gaussian ID, physical illumination, or independent surface truth.')
    return weights,stats


def render_tones(mesh,paths,meta,camera,weights):
    style=meta['styles']['4'];validate_style(style);scale=2
    depth,face_image,regions,c=ray_surface(mesh,camera,scale)
    region_bits=np.left_shift(np.uint64(1),regions.astype(np.uint64))
    size=c['width'];E=np.asarray(c['extrinsic']);R=E[:3,:3]
    nc=mesh['normals']@np.linalg.inv(R);pc=mesh['tri'][:,0]@R.T+E[:3,3]
    plane=np.einsum('ij,ij->i',nc,pc)
    ids,inverse=np.unique(paths['stroke_id'],return_inverse=True)
    np.testing.assert_array_equal(ids,weights['stroke_id'])
    subink={arm:np.zeros((size,size),np.float32) for arm in ARMS}
    values={arm:np.asarray(weights[arm+'_tau']) for arm in ARMS}
    for arm,v in values.items():
        if v.shape!=(len(ids),) or not np.isfinite(v).all() or (v<0).any() or (v>1).any():raise ValueError('invalid stroke weight '+arm)
    accepted=np.zeros(len(ids),np.int64);covered_count=0;behind=0
    width=style['width']*scale;strength=style.get('ink_strength',.8)
    for j,(points,face,layer,support) in enumerate(zip(paths['points'],paths['face'],layer_ids(paths),visibility_masks(paths,4))):
        if layer==1 and not style.get('cross_enabled',False):continue
        uv,z=project(points,c)
        if (z<=.2).any():behind+=1;continue
        direction=uv[1]-uv[0];length2=float(direction@direction)
        if length2<1e-14:continue
        radius=width/2
        lo=np.maximum(0,np.ceil(np.min(uv,axis=0)-radius)).astype(int)
        hi=np.minimum(size-1,np.floor(np.max(uv,axis=0)+radius)).astype(int)
        if (hi<lo).any():continue
        yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        t=np.clip(((xx-uv[0,0])*direction[0]+(yy-uv[0,1])*direction[1])/length2,0,1)
        covered=(xx-uv[0,0]-t*direction[0])**2+(yy-uv[0,1]-t*direction[1])**2<=radius**2
        normal=nc[face]
        denominator=normal[0]*(xx-c['cx'])/c['fx']+normal[1]*(yy-c['cy'])/c['fy']+normal[2]
        zz=np.divide(plane[face],denominator,out=np.full_like(denominator,np.inf),where=np.abs(denominator)>1e-12)
        dd=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        support_bits=region_bits[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        visible=covered & np.isfinite(dd) & ((support_bits & support)!=0)
        difference=np.full_like(dd,np.inf)
        np.subtract(zz,dd,out=difference,where=np.isfinite(zz)&np.isfinite(dd))
        visible &= np.abs(difference)<=.004
        for arm in ARMS:
            target=subink[arm][lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            target[visible]=np.maximum(target[visible],np.float32(strength*values[arm][inverse[j]]))
        accepted[inverse[j]]+=int(visible.sum());covered_count+=int(covered.sum())
    low=lambda x:x.reshape(camera['height'],scale,camera['width'],scale).mean((1,3))
    hit=np.isfinite(depth);n=np.zeros((*face_image.shape,3));n[hit]=mesh['normals'][face_image[hit]]
    light=LIGHT/np.linalg.norm(LIGHT);shade=np.ones_like(depth);shade[hit]=.6+.35*np.abs(n[hit]@light)
    hi=dict(regions=regions[scale//2::scale,scale//2::scale].copy(),proxy=low(shade),
        stroke_visible_fragments=accepted,diagnostics=dict(accepted_fragments=int(accepted.sum()),
        covered_fragments=covered_count,behind_segments=behind,visible_strokes=int((accepted>0).sum()),
        scope='Fragment counts before max/resolve; overlaps count repeatedly and are not independent visibility truth.'))
    return {arm:low(a) for arm,a in subink.items()},hi
