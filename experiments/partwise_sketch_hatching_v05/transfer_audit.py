"""Finite fresh-view diagnostics; neither semantic nor native certification."""
import runtime
import numpy as np


def membership_projection(trace,binding,samples):
    """Normalize accepted alpha*T over source rows, retaining abstention explicitly.

    soft_q includes the original evidence histogram even for an abstained row.
    abstaining_q maps that row's entire mass to UNKNOWN. Neither is calibrated.
    Empty rays are UNKNOWN and excluded from source-covered statistics.
    """
    ids=trace['source_index'];sid=trace['sample_index'];w=trace['weight']
    q=binding['membership'];unknown=binding['unknown']
    if (ids<0).any() or (ids>=len(q)).any() or (sid<0).any() or (sid>=samples).any():
        raise ValueError('trace must use valid original-row and sample IDs')
    if not np.isfinite(w).all() or (w<0).any():raise ValueError('invalid responsibility')
    mass=np.bincount(sid,w,minlength=samples)
    soft=np.zeros((samples,q.shape[1]));abstain=np.zeros_like(soft)
    for k in range(q.shape[1]):
        soft[:,k]=np.bincount(sid,w*q[ids,k],minlength=samples)
        weight=np.where(unknown[ids],float(k==0),q[ids,k])
        abstain[:,k]=np.bincount(sid,w*weight,minlength=samples)
    for arr in (soft,abstain):
        np.testing.assert_allclose(arr.sum(1),mass,rtol=1e-12,atol=1e-12)
        np.divide(arr,mass[:,None],out=arr,where=mass[:,None]>0)
        arr[mass==0,0]=1.
    return dict(soft_q=soft,abstaining_q=abstain,mass=mass,
        unknown_kernel_mass=np.bincount(sid,w*unknown[ids],minlength=samples))


def coverage_assessment(ps,strength,gate):
    weight=ps['weight']*ps['eligible']*np.asarray(strength)[ps['source_index']]
    per=np.array([weight[lo:hi].sum() for lo,hi in zip(ps['offsets'][:-1],ps['offsets'][1:])])
    supported=(~ps['unknown'])&ps['proxy_visible']&(ps['retained_mass']>.01)
    count=int(supported.sum());edited=(per>gate['edit_mass_threshold'])&supported
    denominator=float(ps['retained_mass'][supported].sum())
    fraction=float(edited.sum()/count) if count else None
    retained=float(per[supported].sum()/denominator) if denominator else None
    scorable=count>=gate['min_supported_anchors']
    passed=bool(scorable and fraction>=gate['min_edited_anchor_fraction'] and retained>=gate['min_retained_mass_fraction'])
    return dict(attempted=len(per),proxy_visible=int(ps['proxy_visible'].sum()),
        supported_anchors=count,unknown_anchors=int(ps['unknown'].sum()),
        edited_supported_anchors=int(edited.sum()),edited_mass_per_anchor=per,
        edited_anchor_fraction=fraction,retained_mass_fraction=retained,
        weighted_retained_mass=float(per[supported].sum()),original_retained_mass=denominator,
        coverage_scorable=bool(scorable),coverage_gate=passed)


def kernel_damage_bound(footprint_mass,colors,strength,tint):
    """Per-ID far mass times color L1; triangle bound, not exact pixel attribution."""
    return footprint_mass[:,3]*np.asarray(strength)*np.abs(np.asarray(tint)-colors).sum(1)
