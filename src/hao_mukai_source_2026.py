"""Source-equation reconstruction of Hao & Mukai (SIGGRAPH Asia 2026 poster).

Copyright/credit: equations and fixed constants are theirs. Raster state is a
vanilla-GS disc proxy, NOT their RaDe-GS renderer; this is not official code.
Only the continuous typed fields are source specified. Display styling below
is our explicitly labelled visualization, not their proprietary compositor.
Source: https://mukai-lab.org/content/SA2026PosterHao.pdf
"""
import numpy as np

K=4
A_MIN=.05
PARAMS={'beta_u':32.,'lambda_u':.72,'lambda_q':.35,'lambda_VN':.70,
        'lambda_C':.70,'lambda_GV':.45,'lambda_LN':.72,'lambda_SN':.52,
        'lambda_TC':.58,'lambda_TL':.34}
THRESH={'rho':(.16,.55),'VD':(.003,.045),'VN':(.08,.45),
        'D':(.006,.055),'A':(.040,.280),'N':(.110,.580),
        'C':(.160,.520),'G':(.10,.45),'L':(.08,.38)}


def smoothstep(x,lo,hi):
    t=np.clip((np.asarray(x)-lo)/(hi-lo),0,1)
    return t*t*(3-2*t)


def _pair_field(value,metric,valid=None):
    H,W=value.shape[:2];out=np.zeros((H,W),np.float32)
    for axis in (0,1):
        a=[slice(None)]*value.ndim;b=a.copy();a[axis]=slice(None,-1);b[axis]=slice(1,None)
        d=metric(value[tuple(a)],value[tuple(b)]).astype(np.float32)
        if valid is not None:
            v1=[slice(None)]*2;v2=v1.copy();v1[axis]=slice(None,-1);v2[axis]=slice(1,None)
            d*=valid[tuple(v1)]&valid[tuple(v2)]
        a2=[slice(None)]*2;b2=a2.copy();a2[axis]=slice(None,-1);b2[axis]=slice(1,None)
        out[tuple(a2)]=np.maximum(out[tuple(a2)],d)
        out[tuple(b2)]=np.maximum(out[tuple(b2)],d)
    return out


def _overlap(ids,weights,valid):
    H,W,K=ids.shape;out=np.zeros((H,W),np.float32)
    for axis in (0,1):
        a=[slice(None)]*3;b=a.copy();a[axis]=slice(None,-1);b[axis]=slice(1,None)
        ia,ib=ids[tuple(a)],ids[tuple(b)]
        wa,wb=weights[tuple(a)],weights[tuple(b)]
        match=(ia[..., :,None]==ib[...,None,:])&(ia[..., :,None]>=0)
        overlap=(match*np.minimum(wa[..., :,None],wb[...,None,:])).sum((-2,-1))
        v1=[slice(None)]*2;v2=v1.copy();v1[axis]=slice(None,-1);v2[axis]=slice(1,None)
        d=np.clip(1-overlap,0,1).astype(np.float32)*(valid[tuple(v1)]&valid[tuple(v2)])
        a2=[slice(None)]*2;b2=a2.copy();a2[axis]=slice(None,-1);b2[axis]=slice(1,None)
        out[tuple(a2)]=np.maximum(out[tuple(a2)],d)
        out[tuple(b2)]=np.maximum(out[tuple(b2)],d)
    return out


def compute_fields(s):
    """Equations 1–5 of Hao–Mukai; state has top-4 by visibility contribution."""
    eps=1e-8
    A=np.nan_to_num(s['alpha'],nan=0).astype(np.float32)
    D=np.nan_to_num(s['depth'],nan=0,posinf=0).astype(np.float32)
    N=np.nan_to_num(s['normal'],nan=0).astype(np.float32)
    C=np.nan_to_num(s['albedo'],nan=0).astype(np.float32)
    ids=s['topk_id'][...,:K];tw=s['topk_w'][...,:K].astype(np.float32)
    # Renderer supplies top-4 normalized weights plus total top-4 mass / all mass.
    mass_fraction=s.get('topk_mass',np.ones_like(A))
    kappa=np.clip(s['normal_coherence'],0,1)
    u=np.clip(PARAMS['beta_u']*s['depth_variance']/(D*D+eps),0,1)
    qs=np.clip(A*kappa*np.sqrt(np.clip(tw[...,0]*mass_fraction,0,1))*(1-PARAMS['lambda_u']*u),0,1)
    q=np.clip(qs*(1-PARAMS['lambda_q']*u),0,1)
    rho=np.divide(tw[...,1],np.maximum(tw[...,0],eps))
    ell=smoothstep(rho,*THRESH['rho'])
    td=s['topk_depth'][...,:K]
    tn=s['topk_normal'][...,:K,:]
    dz12=np.abs(td[...,0]-td[...,1])/np.maximum(np.maximum(td[...,0],td[...,1]),eps)
    dn12=1-np.clip(np.sum(tn[...,0,:]*tn[...,1,:],axis=-1),-1,1)
    valid=(A>A_MIN)&(D>0)&np.isfinite(D)
    EV=qs*ell*np.maximum(smoothstep(dz12,*THRESH['VD']),PARAMS['lambda_VN']*smoothstep(dn12,*THRESH['VN']))
    EV*=valid
    delta_A=_pair_field(A,lambda a,b:np.abs(a-b))
    delta_D=_pair_field(D,lambda a,b:np.abs(a-b)/np.maximum(np.maximum(a,b),eps),valid)
    delta_N=_pair_field(N,lambda a,b:1-np.clip(np.sum(a*b,axis=-1),-1,1),valid)
    delta_C=_pair_field(C,lambda a,b:np.linalg.norm(a-b,axis=-1),valid)
    delta_G=_overlap(ids,tw,valid)
    ED=smoothstep(delta_D,*THRESH['D'])*q
    EA=smoothstep(delta_A,*THRESH['A'])*q
    EN=smoothstep(delta_N,*THRESH['N'])*q
    EC=smoothstep(delta_C,*THRESH['C'])*A*((1-PARAMS['lambda_C'])+PARAMS['lambda_C']*q)
    EG=smoothstep(delta_G,*THRESH['G'])*q*ell*np.maximum.reduce([ED,EA,PARAMS['lambda_GV']*EV])
    L=np.maximum.reduce([ED,EA,EG,PARAMS['lambda_LN']*EN])
    SL=smoothstep(L,*THRESH['L'])*np.maximum.reduce([ED,EA,EG,PARAMS['lambda_SN']*EN])
    ET=np.maximum(PARAMS['lambda_TC']*EC,PARAMS['lambda_TL']*L)
    fields=dict(q_s=qs,q=q,u=u,ell=ell,E_V=EV,delta_A=delta_A,delta_D=delta_D,
                delta_N=delta_N,delta_C=delta_C,delta_G=delta_G,
                E_A=EA,E_D=ED,E_N=EN,E_C=EC,E_G=EG,L=L,S_L=SL,E_T=ET)
    return {k:np.nan_to_num(v,nan=0,posinf=0,neginf=0).astype(np.float32) for k,v in fields.items()}
