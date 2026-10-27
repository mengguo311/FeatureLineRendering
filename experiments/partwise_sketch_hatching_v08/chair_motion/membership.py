"""Exposure and UNKNOWN-aware authored-region evidence, not semantic probability."""
import runtime
import json
from pathlib import Path
import numpy as np

def accumulate(n,trace,regions,proxy_z,sample_ok,sampling_weight,depth_tolerance):
    sid=trace['sample_index'];ids=trace['source_index'];w=trace['weight']*sampling_weight[sid]
    region=np.asarray(regions)[sid]
    valid=np.asarray(sample_ok)[sid] & (region>0) & np.isfinite(trace['depth'])
    depth_ok=np.abs(trace['depth']-np.asarray(proxy_z)[sid])<=depth_tolerance
    accepted=valid&depth_ok
    labels=np.where(accepted,region,0)
    score=np.zeros((n,6),np.float64)
    np.add.at(score,(ids,labels),w)
    return score,score.sum(1),dict(total_mass=float(w.sum()),known_mass=float(w[accepted].sum()),
        unknown_mass=float(w[~accepted].sum()),depth_rejected_mass=float(w[valid&~depth_ok].sum()),
        sample_rejected_mass=float(w[~valid].sum()))

def resolve(per_view,min_exposure,min_views,min_fraction,view_mass):
    score=per_view.sum(0);exposure=score.sum(1)
    q=np.divide(score,exposure[:,None],out=np.zeros_like(score),where=exposure[:,None]>0)
    q[exposure==0,0]=1.
    known_view_mass=per_view[:,:,1:].sum(2)
    views=(known_view_mass>=view_mass).sum(0)
    vm=per_view.sum(2);vq=np.divide(per_view,vm[:,:,None],out=np.zeros_like(per_view),where=vm[:,:,None]>0)
    winner=vq[:,:,1:].argmax(2)+1
    confident=(vq[:,:,1:].max(2)>=.8)&(vm>=min_exposure)
    conflict=np.zeros(len(exposure),bool)
    for i in range(len(per_view)):
        for j in range(i):conflict|=confident[i]&confident[j]&(winner[i]!=winner[j])
    label=q[:,1:].argmax(1)+1
    good=(exposure>=min_exposure)&(views>=min_views)&(q[:,1:].max(1)>=min_fraction)&~conflict
    reason=np.full(len(exposure),'mixed_or_unknown',dtype='<U20')
    reason[views<min_views]='few_views';reason[exposure<min_exposure]='low_exposure'
    reason[exposure==0]='unobserved';reason[conflict]='view_conflict';reason[good]='supported'
    return dict(source_index=np.arange(len(exposure),dtype=np.int64),membership=q,score=score,
                exposure=exposure,distinct_views=views.astype(np.uint8),conflict=conflict,
                unknown=~good,region_id=np.where(good,label,0).astype(np.uint8),reason=reason)

def save_binding(path,arrays,metadata):
    np.savez_compressed(path,**arrays,metadata_json=np.array(json.dumps(metadata,sort_keys=True,default=runtime.json_default)))

def load_binding(path,source_sha,n):
    with np.load(path,allow_pickle=False) as z:
        meta=json.loads(str(z['metadata_json']));a={k:z[k] for k in z.files if k!='metadata_json'}
    if meta['source_sha256']!=source_sha or meta['source_count']!=n:raise ValueError('source identity mismatch')
    if not np.array_equal(a['source_index'],np.arange(n)):raise ValueError('original source row order mismatch')
    if a['membership'].shape!=(n,6) or not np.isfinite(a['membership']).all():raise ValueError('bad membership')
    if not np.allclose(a['membership'].sum(1),1.,rtol=0,atol=1e-12):raise ValueError('membership mass mismatch')
    return a,meta

def tint_copy(a,strength,tint):
    """Blend ALL SH coefficients with a constant-color SH in a private copy.

    Original means/cov/opacity/order unchanged. At full strength higher SH=0;
    at partial strength higher SH is scaled by 1-strength. No PLY write.
    """
    strength=np.asarray(strength,float)
    if strength.shape!=(len(a['means']),) or not np.isfinite(strength).all() or (strength<0).any() or (strength>1).any():
        raise ValueError('strength must be one [0,1] value per original row')
    sh=a['SH'].copy();sh*=1-strength[:,None,None]
    sh[:,:,0]+=strength[:,None]*(np.asarray(tint)-.5)/.28209479177387814
    return dict(a,SH=sh)

def evaluated_tint_copy(a,c,strength,tint):
    """Reversible per-original-row color override AFTER full SH3 evaluation.

    SH arrays remain untouched. Higher-order view appearance remains in the
    (1-strength) portion. This is a source-kernel render-time diagnostic.
    """
    from base_model import source_colors
    colors=source_colors(a,c)
    colors=colors*(1-strength[:,None])+np.asarray(tint)*strength[:,None]
    return {**{k:v for k,v in a.items() if k!='SH'},'colors':colors}
