"""Independent interventions, signed accounting and conservative acceptance."""
import numpy as np

def centered_identity(dw,colors,dtbg,bg,u,center):
    terms=np.asarray(dw)*((np.asarray(colors)-center)@np.asarray(u))
    b=float(dtbg*np.dot(np.asarray(bg)-center,u))
    return terms,b,float(np.sum(dw)+dtbg)

def analytic_rays():
    # Front alpha=.6; rear conditional compositing yields .28/.72.
    def ray(a,lo,hi):return a*.5+(1-a)*(lo*.1+hi*.9+(1-lo-hi)*.5)
    left=ray(.6,.75,.2);right=ray(.6,.2,.75)
    colors=np.array([.5,.1,.9]); dw=np.array([0,-.22,.22]); terms=dw*(colors-.5)
    h=1e-5;logit=np.log(.6/.4)
    sigmoid=lambda x:1/(1+np.exp(-x))
    f=lambda a:ray(a,.2,.75)-ray(a,.75,.2)
    fd=(f(sigmoid(logit+h))-f(sigmoid(logit-h)))/(2*h)
    return dict(left=left,right=right,contrast=right-left,signed_terms=terms.tolist(),
                without_front=f(0),pixel_alpha_derivative=(f(.6+h)-f(.6-h))/(2*h),
                opacity_logit_fd=fd,same_color_response=abs(.5*.3+(1-.3)*.5-.5),
                zero_additive_contrast_does_not_imply_zero_causal_response=True)

def decide_gates(values):
    return dict(gates=[bool(v) for v in values],optimization='AUTHORIZED' if all(values) else 'NOT_RUN',
                scientific_claim='exploratory only; no formal blind TEST')

def features(profile):
    # Whole-profile RGB plus its spatial variation; no endpoint-only scoring.
    p=np.asarray(profile,float)
    return np.concatenate([p.ravel(),(2*np.diff(p,axis=0)).ravel()])

def intervention_metrics(base,changed,a0,a1,reference,sample,band,flatmask,baseline_profile,changed_profile):
    from evidence import profile_vector
    import legacy_evidence as legacy
    d=changed-base;den=max(float(band.sum())*3,1)
    edge_rms=float(np.sqrt((d*d*band[...,None]).sum()/den))
    outside=1-band;outside_rms=float(np.sqrt((d*d*outside[...,None]).sum()/max(float(outside.sum())*3,1)))
    flat_rms=float(np.sqrt((d*d*flatmask[...,None]).sum()/max(float(flatmask.sum())*3,1)))
    p0=np.asarray(baseline_profile);p1=np.asarray(changed_profile);t=np.linspace(-12,12,len(p0))
    endpoint_delta=(p1[t>=9.6].mean(0)-p1[t<=-9.6].mean(0))-(p0[t>=9.6].mean(0)-p0[t<=-9.6].mean(0))
    u=np.asarray(sample.get('u') or [1.,0,0]); ref=features(profile_vector(reference,sample,True))
    z0=features(profile_vector(base,sample,True));z1=features(profile_vector(changed,sample,True))
    r=ref-z0;dz=z1-z0;improvement=float(2*np.dot(r,dz)-np.dot(dz,dz))
    bmet=legacy.profile_metrics(base,[sample])[0];cmet=legacy.profile_metrics(changed,[sample])[0]
    return dict(edge_rms=edge_rms,outside_rms=outside_rms,flat_rms=flat_rms,
                signed_endpoint_delta=float(endpoint_delta@u),profile_change_l2=float(np.linalg.norm(features(p1)-features(p0))),
                platform_rms=float(np.sqrt(np.mean((p1[np.abs(t)>=9.6]-p0[np.abs(t)>=9.6])**2))),
                derivative_variation_l1=float(np.abs(np.diff(p1-p0,axis=0)).sum()),
                ringing_overshoot=float(max(0,p1.min(0).min()-p0.min(0).min(),p1.max(0).max()-p0.max(0).max())),
                width_before=bmet.get('width'),width_after=cmet.get('width'),x50_before=bmet.get('x50'),x50_after=cmet.get('x50'),
                profile_valid_before=bmet['valid'],profile_valid_after=cmet['valid'],
                linear_profile_squared_error_improvement=improvement,
                alpha_max_abs=float(np.max(np.abs(a1-a0))),
                new_coverage_holes=int(((a0>.95)&(a1<.5)).sum()),
                outline_binary_changed_pixels=int(((a0>=.5)!=(a1>=.5)).sum()))

def rank_correlation(a,b):
    from scipy.stats import spearmanr
    if len(a)<3 or np.ptp(a)==0 or np.ptp(b)==0:return None
    r=float(spearmanr(a,b).statistic)
    return r if np.isfinite(r) else None

def paired_bootstrap(deltas,seed=1729):
    d=np.asarray(deltas,float)
    if len(d)==0:return dict(n=0,mean=None,ci95=None)
    rng=np.random.default_rng(seed);b=rng.choice(d,(2000,len(d)),replace=True).mean(1)
    return dict(n=len(d),mean=float(d.mean()),ci95=np.quantile(b,[.025,.975]).tolist(),
                unit='paired target groups; dependent views, exploratory confidence only')
