"""Fixed original-row permission endpoint and signed RGB residual accounting.

Saturation is an endpoint, not an optimal residual bound: colors above paper
can cancel other residuals. L1 of components must never be added as attribution.
"""
import runtime
import numpy as np

def saturate(strength):
    s=np.asarray(strength,float)
    if s.ndim!=1 or not np.isfinite(s).all() or (s<0).any() or (s>1).any():
        raise ValueError('one finite [0,1] strength per original row')
    return (s>0).astype(float)

def decompose_residual(colors,strength,trace,samples,paper=(.95,.95,.95)):
    colors=np.asarray(colors,float);s=np.asarray(strength,float);full=saturate(s);p=np.asarray(paper,float)
    if colors.shape!=(len(s),3) or p.shape!=(3,) or not np.isfinite(colors).all():
        raise ValueError('full original-row colors and paper RGB required')
    sid=np.asarray(trace['sample_index']);ids=np.asarray(trace['source_index']);w=np.asarray(trace['weight'])
    if (sid<0).any() or (sid>=samples).any() or (ids<0).any() or (ids>=len(s)).any() or not np.isfinite(w).all() or (w<0).any():
        raise ValueError('valid accepted original-row trace required')
    mass=np.bincount(sid,w,minlength=samples)
    if (mass>1+1e-8).any():raise ValueError('accepted mass exceeds one')
    delta=colors[ids]-p;licensed=full[ids]>0
    def accumulate(weight):
        return np.column_stack([np.bincount(sid,weight*delta[:,j],minlength=samples) for j in range(3)])
    remaining=accumulate(w*licensed*(1-s[ids]))
    unlicensed=accumulate(w*(~licensed))
    background=(1-mass[:,None])*(np.ones(3)-p)
    return dict(licensed_unreplaced=remaining,unlicensed=unlicensed,background=background,
                old_residual=remaining+unlicensed+background,saturated_residual=unlicensed+background,
                accepted_mass=mass)
