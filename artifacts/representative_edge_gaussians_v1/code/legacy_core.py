"""Frozen, visibility weighted Gaussian edge-contributor attribution.

Scores describe participation in independent rendered evidence, not geometric
edge identity. Cached raw alpha*T is never normalized within a ray. K=4 data
produce a TOP4-TRUNCATED estimator, even when full-render alpha is available.
All routines are CPU-only and perform no filesystem, camera, or model writes.
"""
import hashlib
import json

import numpy as np
from scipy import ndimage as ndi


CLASSES = ('color', 'geometry', 'outline', 'union')


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def asset_hash(asset):
    """Content hash includes original ID order, dtype, shape, and every field."""
    digest = hashlib.sha256()
    for key in sorted(asset):
        digest.update(key.encode() + b'\0')
        value = asset[key]
        if isinstance(value, np.ndarray):
            value = np.ascontiguousarray(value)
            if value.dtype.hasobject:
                raise ValueError('object arrays cannot be sealed')
            digest.update(str(value.dtype).encode())
            digest.update(str(value.shape).encode())
            digest.update(value.tobytes())
        else:
            digest.update(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
    return digest.hexdigest()


def verify_asset(asset, expected_hash):
    if asset_hash(asset) != expected_hash:
        raise ValueError('sealed Gaussian attribution asset mutated')
    return True


def validate_raw(raw, n_gaussians=None):
    alpha = np.asarray(raw['alpha'])
    if alpha.ndim != 2 or min(alpha.shape) < 1:
        raise ValueError('alpha must be a nonempty HxW grid')
    ids, weights = np.asarray(raw['topk_id']), np.asarray(raw['topk_w'])
    if ids.ndim != 3 or ids.shape[:2] != alpha.shape or ids.shape[-1] < 1:
        raise ValueError('topk_id must be HxWxK')
    shapes = dict(alpha=alpha.shape, rgb=(*alpha.shape, 3), depth=alpha.shape,
                  median_depth=alpha.shape, topk_id=ids.shape,
                  topk_w=ids.shape, topk_depth=ids.shape)
    for key, shape in shapes.items():
        arr = np.asarray(raw[key])
        if arr.shape != shape or not np.issubdtype(arr.dtype, np.number) or not np.isfinite(arr).all():
            raise ValueError('corrupt native channel: ' + key)
    if not np.issubdtype(ids.dtype, np.integer) or np.any(ids < -1):
        raise ValueError('original Gaussian ID must be integer with -1 sentinel')
    if n_gaussians is not None and np.any(ids >= n_gaussians):
        raise ValueError('original Gaussian ID outside checkpoint namespace')
    if np.any(weights < 0) or np.any(alpha < 0) or np.any(alpha > 1 + 5e-6):
        raise ValueError('invalid alpha or raw alpha*T')
    if np.any(weights[ids < 0] != 0) or np.any(weights[ids >= 0] <= 0):
        raise ValueError('empty/nonempty Gaussian ID weight mismatch')
    if np.any(weights.sum(-1, dtype=np.float64) > alpha + 5e-6):
        raise ValueError('raw alpha*T exceeds full alpha; do not normalize topK')
    if np.any(np.asarray(raw['topk_depth'])[ids >= 0] <= 0):
        raise ValueError('visible contributor depth must be positive')
    sources = raw.get('channel_source_ids')
    if sources is not None and any(sources.get(key) != raw.get('source_id') for key in shapes):
        raise ValueError('native channel traversal provenance mismatch')
    return alpha.shape


def _nms(magnitude, nx, ny, step):
    yy, xx = np.indices(magnitude.shape, dtype=np.float32)
    left = ndi.map_coordinates(magnitude, [yy-step*ny, xx-step*nx], order=1, mode='nearest')
    right = ndi.map_coordinates(magnitude, [yy+step*ny, xx+step*nx], order=1, mode='nearest')
    return (magnitude > 1e-12) & (magnitude >= left) & (magnitude >= right)


def evidence_fields(raw, cfg):
    """Independent soft RGB/log-depth/alpha gradients; never inspects IDs.

    Geometry is rendered depth evidence. It is not a ground-truth surface label.
    RGB orientation is the principal RGB gradient tensor direction; scalar
    depth/alpha use their own gradient directions. Flat pixels have zero direction.
    """
    rgb = np.asarray(raw['rgb'], np.float64)
    alpha = np.asarray(raw['alpha'], np.float64)
    depth = np.asarray(raw[cfg['depth_field']], np.float64)
    if rgb.shape != (*alpha.shape, 3) or depth.shape != alpha.shape:
        raise ValueError('independent evidence channel shape mismatch')
    if not all(np.isfinite(x).all() for x in (rgb, alpha, depth)):
        raise ValueError('nonfinite independent evidence input')
    sigma = float(cfg['gaussian_sigma'])
    gx = np.stack([ndi.gaussian_filter(rgb[..., c], sigma, order=(0, 1)) for c in range(3)], axis=-1)
    gy = np.stack([ndi.gaussian_filter(rgb[..., c], sigma, order=(1, 0)) for c in range(3)], axis=-1)
    xx, yy, xy = (gx*gx).sum(-1), (gy*gy).sum(-1), (gx*gy).sum(-1)
    angle = .5*np.arctan2(2*xy, xx-yy)
    color_mag = np.sqrt(np.maximum(.5*(xx+yy+np.sqrt((xx-yy)**2+4*xy*xy)), 0))
    color_nx, color_ny = np.cos(angle), np.sin(angle)
    color_nx[color_mag <= 1e-12] = 0
    color_ny[color_mag <= 1e-12] = 0
    depth_valid = (depth > 0) & (alpha >= cfg['interior_alpha'])
    depth_mask = depth_valid.astype(np.float64)
    logz = np.zeros_like(depth)
    logz[depth_valid] = np.log(depth[depth_valid])
    smoothed = ndi.gaussian_filter(logz*depth_mask, sigma) / np.maximum(ndi.gaussian_filter(depth_mask, sigma), 1e-12)
    depth_gx, depth_gy = ndi.gaussian_filter(smoothed, sigma, order=(0,1)), ndi.gaussian_filter(smoothed, sigma, order=(1,0))
    alpha_gx, alpha_gy = ndi.gaussian_filter(alpha, sigma, order=(0,1)), ndi.gaussian_filter(alpha, sigma, order=(1,0))
    geometry_mag, outline_mag = np.hypot(depth_gx,depth_gy), np.hypot(alpha_gx,alpha_gy)
    magnitude = np.stack([color_mag,geometry_mag,outline_mag],axis=-1)
    orientation_x = np.stack([color_nx,depth_gx/np.maximum(geometry_mag,1e-30),alpha_gx/np.maximum(outline_mag,1e-30)],axis=-1)
    orientation_y = np.stack([color_ny,depth_gy/np.maximum(geometry_mag,1e-30),alpha_gy/np.maximum(outline_mag,1e-30)],axis=-1)
    interior = alpha >= cfg['interior_alpha']
    iterations = int(cfg['interior_erosion_pixels'])
    if iterations:
        interior = ndi.binary_erosion(interior, iterations=iterations, border_value=0)
        depth_valid = ndi.binary_erosion(depth_valid, iterations=iterations, border_value=0)
    roi = np.stack([interior,depth_valid,alpha >= cfg['foreground_alpha']],axis=-1)
    nms = np.stack([_nms(magnitude[...,c],orientation_x[...,c],orientation_y[...,c],cfg['nms_step_pixels']) for c in range(3)],axis=-1) & roi
    return dict(magnitude=magnitude.astype(np.float32), orientation_x=orientation_x.astype(np.float32),
                orientation_y=orientation_y.astype(np.float32), nms=nms, roi=roi,
                alpha=alpha.astype(np.float32), config_hash=canonical_hash(cfg))


def fit_normalization(list_fields, cfg):
    list_fields = list(list_fields)
    if not list_fields:
        raise ValueError('normalization requires F evidence fields')
    scales, counts = {}, {}
    for c, name in enumerate(CLASSES[:3]):
        values=[]
        for fields in list_fields:
            if fields['config_hash'] != canonical_hash(cfg):
                raise ValueError('evidence config mismatch')
            if fields.get('split','F') != 'F':
                raise ValueError('normalization restricted to F')
            mag = fields['magnitude'][...,c]
            values.append(mag[(mag > 1e-12) & fields['roi'][...,c]])
        counts[name] = sum(len(v) for v in values)
        scales[name] = max(float(np.percentile(np.concatenate(values), cfg['normalization_positive_percentile'])),1e-12) if counts[name] else 1.
    return dict(scales=scales,positive_counts=counts,frame_count=len(list_fields),config_hash=canonical_hash(cfg),scope='Mic F only; inherited unchanged by secondary')


def compute_evidence(fields, normalization, cfg):
    if fields['config_hash'] != canonical_hash(cfg) or normalization['config_hash'] != canonical_hash(cfg):
        raise ValueError('normalization/config seal mismatch')
    result = {}
    for c,name in enumerate(CLASSES[:3]):
        scale = normalization['scales'][name]
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError('invalid F-only normalization scale')
        result[name] = (np.clip(fields['magnitude'][...,c]/scale,0,1)*fields['nms'][...,c]).astype(np.float32)
    result['union'] = np.maximum.reduce([result[c] for c in CLASSES[:3]])
    result.update(orientation_x=fields['orientation_x'],orientation_y=fields['orientation_y'],
                  nms=fields['nms'],roi=fields['roi'])
    return result


def contributor_overlap(left_ids,left_weights,right_ids,right_weights):
    """Raw-weight Jaccard, coalescing repeated IDs on each side first."""
    def coalesce(ids, weights):
        ids=np.asarray(ids)
        weights=np.array(weights,np.float64,copy=True)
        for j in range(ids.shape[-1]):
            for k in range(j+1,ids.shape[-1]):
                same=(ids[...,j]>=0)&(ids[...,j]==ids[...,k])
                weights[...,j]+=np.where(same,weights[...,k],0)
                weights[...,k]=np.where(same,0,weights[...,k])
        return weights
    lw=coalesce(left_ids,left_weights)
    rw=coalesce(right_ids,right_weights)
    inter=np.zeros(lw.shape[:-1],np.float64)
    for j in range(lw.shape[-1]):
        for k in range(rw.shape[-1]):
            same=(left_ids[...,j]>=0)&(left_ids[...,j]==right_ids[...,k])
            inter+=np.where(same,np.minimum(lw[...,j],rw[...,k]),0)
    union=lw.sum(-1)+rw.sum(-1)-inter
    return np.divide(inter,union,out=np.zeros_like(inter),where=union>0).astype(np.float32)


def _front_slots(raw,cfg):
    """Nearest depth among retained topK slots, not guaranteed full-ray front."""
    ids,depths=np.asarray(raw['topk_id']),np.asarray(raw['topk_depth'])
    valid=(ids>=0)&(np.asarray(raw['topk_w'])>0)&(depths>0)
    front=np.min(np.where(valid,depths,np.inf),axis=-1)
    allowed=valid&(depths<=front[...,None]*(1+cfg['front_relative_depth_tolerance']))
    front=np.where(np.isfinite(front),front,0)
    return allowed,front.astype(np.float32)


def side_evidence(raw,evidence,cfg):
    """Return per-slot side evidence HxWxKx3 with original-ID provenance.

    Independent edge pixels choose orientations. Side rays contribute only their
    nearest retained topK slots; outline deposits only on the larger-alpha foreground
    side. Max collision reduction bounds evidence at one per slot per offset.
    ID switching alone never creates an edge: the independent center E is needed.
    """
    ids=np.asarray(raw['topk_id'])
    weights=np.asarray(raw['topk_w'])
    alpha=np.asarray(raw['alpha'])
    h,w,k=ids.shape
    fronts,front_depth=_front_slots(raw,cfg)
    accumulated=np.zeros((h,w,k,3),np.float32)
    overlap_map=np.zeros((h,w,3),np.float32)
    depth_map=np.zeros((h,w,3),np.float32)
    valid_map=np.zeros((h,w,3),np.float32)
    side_count=np.zeros((h,w,3),np.uint16)
    offsets=cfg['side_offsets_pixels']
    for offset in offsets:
        offset_evidence=np.zeros_like(accumulated)
        for c,name in enumerate(CLASSES[:3]):
            ey,ex=np.nonzero(evidence[name]>0)
            if not len(ey):
                continue
            nx=evidence['orientation_x'][ey,ex,c]
            ny=evidence['orientation_y'][ey,ex,c]
            lx=np.rint(ex-offset*nx).astype(np.int32);ly=np.rint(ey-offset*ny).astype(np.int32)
            rx=np.rint(ex+offset*nx).astype(np.int32);ry=np.rint(ey+offset*ny).astype(np.int32)
            inbounds=(lx>=0)&(lx<w)&(rx>=0)&(rx<w)&(ly>=0)&(ly<h)&(ry>=0)&(ry<h)
            ey,ex,lx,ly,rx,ry=[v[inbounds] for v in (ey,ex,lx,ly,rx,ry)]
            if not len(ey):
                continue
            overlap=contributor_overlap(ids[ly,lx],weights[ly,lx],ids[ry,rx],weights[ry,rx])
            zl,zr=front_depth[ly,lx],front_depth[ry,rx]
            both=(zl>0)&(zr>0)&(alpha[ly,lx]>=cfg['foreground_alpha'])&(alpha[ry,rx]>=cfg['foreground_alpha'])
            relative=np.divide(np.abs(zl-zr),np.maximum(zl,zr),out=np.zeros_like(zl),where=both)
            depth_strength=np.clip(relative/cfg['side_relative_depth_scale'],0,1)
            amp=evidence[name][ey,ex]*.5*(1-overlap+depth_strength)
            overlap_map[ey,ex,c]+=overlap/len(offsets)
            depth_map[ey,ex,c]+=depth_strength/len(offsets)
            valid_map[ey,ex,c]+=both.astype(np.float32)/len(offsets)
            side_count[ey,ex,c]+=1
            for sy,sx,oy,ox in ((ly,lx,ry,rx),(ry,rx,ly,lx)):
                allowed=alpha[sy,sx]>=cfg['foreground_alpha']
                if name=='outline':
                    allowed &= alpha[sy,sx]>=alpha[oy,ox]
                for slot in range(k):
                    a=allowed&fronts[sy,sx,slot]
                    np.maximum.at(offset_evidence[...,slot,c],(sy[a],sx[a]),amp[a])
        accumulated+=offset_evidence/len(offsets)
    return accumulated,dict(side_overlap=overlap_map,side_depth_contrast=depth_map,
                             side_both_foreground=valid_map,side_offset_count=side_count,
                             front_slot=fronts,front_depth=front_depth)


def _bincount(ids,weights,n):
    valid=ids>=0
    return np.bincount(ids[valid].ravel(),weights=np.asarray(weights)[valid].ravel(),minlength=n).astype(np.float64)


def view_statistics(raw,evidence,n_gaussians,cfg,with_side=True):
    validate_raw(raw,n_gaussians)
    ids=np.asarray(raw['topk_id'])
    weights=np.asarray(raw['topk_w'],np.float64)
    denominator=_bincount(ids,weights,n_gaussians)
    channels=np.stack([evidence[c] for c in CLASSES],axis=-1)
    if channels.shape[:2]!=ids.shape[:2] or not np.isfinite(channels).all() or np.any(channels<0) or np.any(channels>1):
        raise ValueError('invalid independent evidence maps')
    numerator=np.stack([_bincount(ids,weights*channels[...,c,None],n_gaussians) for c in range(4)],axis=-1)
    positive_mass=np.stack([_bincount(ids,weights*(channels[...,c,None]>=cfg['positive_evidence_threshold']),n_gaussians) for c in range(4)],axis=-1)
    # Visible nonedge is explicit counterevidence; unobserved IDs have zero mass.
    nonedge_mass=denominator[:,None]-positive_mass
    soft_nonedge_mass=denominator[:,None]-numerator
    fronts,front_depth=_front_slots(raw,cfg)
    front_mass=_bincount(ids,weights*fronts,n_gaussians)
    foreground=np.asarray(raw['alpha'])>=cfg['foreground_alpha']
    foreground_mass=_bincount(ids,weights*foreground[...,None],n_gaussians)
    interior=np.asarray(raw['alpha'])>=cfg['interior_alpha']
    erosion=int(cfg['interior_erosion_pixels'])
    if erosion:
        interior=ndi.binary_erosion(interior,iterations=erosion,border_value=0)
    interior_mass=_bincount(ids,weights*interior[...,None],n_gaussians)
    if with_side:
        side,diagnostics=side_evidence(raw,evidence,cfg)
        side=np.concatenate([side,np.max(side,axis=-1,keepdims=True)],axis=-1)
        side_numerator=np.stack([_bincount(ids,weights*side[...,c],n_gaussians) for c in range(4)],axis=-1)
    else:
        side_numerator=np.zeros_like(numerator)
        diagnostics={}
    raw_mass=float(weights.sum(dtype=np.float64))
    alpha_mass=float(np.asarray(raw['alpha']).sum(dtype=np.float64))
    out=dict(numerator=numerator,side_numerator=side_numerator,denominator=denominator,
             positive_mass=positive_mass,nonedge_mass=nonedge_mass,soft_nonedge_mass=soft_nonedge_mass,
             front_mass=front_mass,deeper_mass=denominator-front_mass,
             foreground_mass=foreground_mass,interior_mass=interior_mass,
             outline_mass=positive_mass[:,2],raw_cached_mass=raw_mass,cached_mass=raw_mass,
             alpha_mass=alpha_mass,omitted_mass=max(alpha_mass-raw_mass,0),
             topk=int(ids.shape[-1]),diagnostics=diagnostics)
    for key in ('frame_id','split','source_id'):
        if key in raw:
            out[key]=raw[key]
    return out


def aggregate_views(list_stats,cfg,min_views=None):
    list_stats=list(list_stats)
    if not list_stats:
        raise ValueError('F aggregation requires at least one view')
    for view in list_stats:
        if view.get('split','F')!='F':
            raise ValueError('C/arc evaluation cannot modify fixed F scores')
        if 'frame_id' in view and int(view['frame_id']) not in cfg['fixed_frame_ids']:
            raise ValueError('non-F frame attempted score update')
    denominator=np.stack([s['denominator'] for s in list_stats])
    numerator=np.stack([s['numerator'] for s in list_stats])
    side=np.stack([s['side_numerator'] for s in list_stats])
    masses=np.maximum(np.array([s['raw_cached_mass'] for s in list_stats],np.float64),1e-30)
    normalized_denom=(denominator/masses[:,None]).sum(0)
    normalized_num=(numerator/masses[:,None,None]).sum(0)
    normalized_side=(side/masses[:,None,None]).sum(0)
    baseline=np.divide(normalized_num,normalized_denom[:,None],out=np.zeros_like(normalized_num),where=normalized_denom[:,None]>0)
    side_rate=np.divide(normalized_side,normalized_denom[:,None],out=np.zeros_like(normalized_side),where=normalized_denom[:,None]>0)
    baseline=np.clip(baseline,0,1);side_rate=np.clip(side_rate,0,1)
    raw_denom=denominator.sum(0)
    raw_numerator=numerator.sum(0)
    unbalanced=np.divide(raw_numerator,raw_denom[:,None],out=np.zeros_like(raw_numerator),where=raw_denom[:,None]>0)
    support=(denominator>0).sum(0).astype(np.int16)
    min_views=cfg['min_visible_views'] if min_views is None else min_views
    eligible=(raw_denom>=cfg['min_raw_visibility_mass'])&(support>=min_views)
    front_mass=np.stack([s['front_mass'] for s in list_stats]).sum(0)
    front_fraction=np.divide(front_mass,raw_denom,out=np.zeros_like(raw_denom),where=raw_denom>0)
    # 0 unknown, 1 cached-front-dominant, 2 mixed, 3 cached-deeper-dominant.
    # Front/deeper are relative to retained topK, never full-ray surface GT.
    depth_class=np.where(raw_denom==0,0,np.where(front_fraction>=.8,1,np.where(front_fraction<=.2,3,2))).astype(np.uint8)
    out=dict(original_ids=np.arange(len(raw_denom),dtype=np.int32),raw_denominator=raw_denom,
             normalized_denominator=normalized_denom,support_view_count=support,
             positive_support_view_count=(numerator>0).sum(0).astype(np.int16),
             eligible=eligible,unknown=raw_denom==0,unreliable=(raw_denom>0)&~eligible,
             front_fraction=front_fraction,depth_class=depth_class,
             perview_denominator=denominator,perview_numerator=numerator,perview_side_numerator=side,
             perview_normalization_mass=masses,config_hash=canonical_hash(cfg),
             attribution_estimator='TOP%d-TRUNCATED'%max(s['topk'] for s in list_stats),
             classes=list(CLASSES))
    for key in ('positive_mass','nonedge_mass','soft_nonedge_mass','front_mass','deeper_mass','foreground_mass','interior_mass','outline_mass'):
        arr=np.stack([s[key] for s in list_stats])
        out['perview_'+key]=arr
        out[key]=arr.sum(0)
    for c,name in enumerate(CLASSES):
        out['baseline_'+name]=baseline[:,c]
        out['baseline_raw_'+name]=unbalanced[:,c]
        out['side_'+name]=side_rate[:,c]
        out['enhanced_'+name]=.5*baseline[:,c]+.5*side_rate[:,c]
    return out


def rank_tiers(asset,cfg,score_key='enhanced_union'):
    eligible=np.flatnonzero(asset['eligible'])
    scores=np.asarray(asset[score_key])
    order=eligible[np.lexsort((eligible,-scores[eligible]))]
    return {str(int(p)):order[:int(np.ceil(len(order)*p/100))].astype(np.int32) for p in cfg['tiers_percent']}


def visibility_bins(asset,cfg):
    """F-only strata: visible-view count plus equal-rank raw visibility decile."""
    eligible=np.flatnonzero(asset['eligible'])
    bins=np.full(len(asset['eligible']),-1,np.int32)
    q=int(cfg['random_visibility_quantile_bins'])
    for count in np.unique(np.asarray(asset['support_view_count'])[eligible]):
        subset=eligible[np.asarray(asset['support_view_count'])[eligible]==count]
        order=subset[np.lexsort((subset,np.asarray(asset['raw_denominator'])[subset]))]
        bins[order]=int(count)*q+np.minimum(np.arange(len(order))*q//max(len(order),1),q-1)
    return bins


def visibility_matched_random(asset,selected_ids,seed,cfg):
    selected=np.asarray(selected_ids,dtype=np.int64)
    if len(np.unique(selected))!=len(selected) or np.any(~np.asarray(asset['eligible'])[selected]):
        raise ValueError('matched control needs unique eligible Gaussian IDs')
    bins=visibility_bins(asset,cfg)
    rng=np.random.default_rng(seed)
    control=[]
    for b in np.unique(bins[selected]):
        count=int((bins[selected]==b).sum())
        candidates=np.flatnonzero(bins==b)
        control.extend(rng.choice(candidates,size=count,replace=False).tolist())
    return np.sort(np.asarray(control,np.int32))


def project(raw,scores=None,selected_ids=None,n_gaussians=None):
    """Original visibility attribute P=sum(raw alpha*T*score), Q for fixed IDs.

    Missing topK contributors stay omitted. Conditional attribute divides by
    original full alpha (not by cached alpha); omitted contributors are unknown.
    This is not subset recomposition, which would expose hidden layers.
    """
    if scores is not None:
        scores=np.asarray(scores)
        n_gaussians=len(scores) if n_gaussians is None else n_gaussians
    validate_raw(raw,n_gaussians)
    ids=np.asarray(raw['topk_id'])
    weights=np.asarray(raw['topk_w'],np.float64)
    valid=ids>=0
    safe_ids=np.maximum(ids,0)
    attribute=np.zeros(ids.shape[:2],np.float64)
    if scores is not None:
        if scores.ndim!=1 or not np.isfinite(scores).all() or np.any(scores<0) or np.any(scores>1):
            raise ValueError('score must be finite [0,1] per original Gaussian')
        if len(scores):
            attribute=(weights*np.where(valid,scores[safe_ids],0)).sum(-1)
        elif np.any(valid):
            raise ValueError('nonempty IDs with empty asset')
    selected_mass=np.zeros_like(attribute)
    if selected_ids is not None:
        selected=np.asarray(selected_ids,dtype=np.int64)
        if np.any(selected<0) or len(np.unique(selected))!=len(selected):
            raise ValueError('selected IDs must be unique original nonnegative IDs')
        if n_gaussians is not None and np.any(selected>=n_gaussians):
            raise ValueError('selected ID outside checkpoint namespace')
        selected_mass=(weights*np.isin(ids,selected)).sum(-1)
    alpha=np.asarray(raw['alpha'],np.float64)
    conditional=np.divide(attribute,alpha,out=np.zeros_like(attribute),where=alpha>0)
    mass=weights.sum(-1)
    return dict(attribute=attribute.astype(np.float32),conditional_attribute=conditional.astype(np.float32),
                selected_mass=selected_mass.astype(np.float32),alpha=alpha.astype(np.float32),
                cached_mass=mass.astype(np.float32),omitted_mass=np.maximum(alpha-mass,0).astype(np.float32))


def null_evidence(evidence,cfg,kind='shift'):
    """One frozen null realization; channels and their orientations move together."""
    result={key:np.array(value,copy=True) for key,value in evidence.items()}
    if kind=='shift':
        dy,dx=cfg['null_shift_pixels']
        for key in result:
            value=result[key]
            h,w=value.shape[:2]
            shifted=np.zeros_like(value)
            sy0,sy1=max(0,-dy),min(h,h-dy)
            sx0,sx1=max(0,-dx),min(w,w-dx)
            if sy1>sy0 and sx1>sx0:
                shifted[sy0+dy:sy1+dy,sx0+dx:sx1+dx]=value[sy0:sy1,sx0:sx1]
            result[key]=shifted
    elif kind=='shuffle':
        h,w=result['union'].shape
        permutation=np.random.default_rng(cfg['null_shuffle_seed']).permutation(h*w)
        for key,value in result.items():
            result[key]=value.reshape((h*w,)+value.shape[2:])[permutation].reshape(value.shape)
    else:
        raise ValueError('unknown preregistered null')
    return result
