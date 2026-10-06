from pathlib import Path
import numpy as np

def writable_path(path):
    from runtime import EXP,ART,OUT
    p=Path(path).resolve()
    if not any(p==r or r in p.parents for r in (EXP,ART,OUT)):raise ValueError('write outside new v2 subtrees')
    return p

def validate_roles(roles):
    seen=set();ids=set()
    for role,frames in roles.items():
        for f in frames:
            k=tuple(np.round(np.asarray(f['transform_matrix']).ravel(),10))
            if k in seen or f['id'] in ids:raise ValueError('camera/transform role overlap')
            seen.add(k);ids.add(f['id'])

def angle_status(theta,train):
    lo,hi=min(train),max(train)
    return {'status':'interpolation' if lo<=theta<=hi else 'extrapolation','nearest_training_angle_deg':min(abs(theta-t) for t in train),'training_range_deg':[lo,hi]}

def ls_certificate(residual,b,y,aty,observations,margin):
    # Reductions in float64. Margin must cover native A/A^T finite precision.
    def arr(x):return np.asarray(x,dtype=np.float64)
    r,b,y,g=map(arr,(residual,b,y,aty))
    P=.5*float(np.sum(r*r));D=-.5*float(np.sum(y*y))-float(np.sum(b*y))+float(np.minimum(g,0).sum())
    return {'P':P,'D_raw':D,'numerical_margin':margin,'D':D-margin,'gap':P-D+margin,'scalar_observations':observations,'mse_upper':2*P/observations,'mse_lower':2*(D-margin)/observations}
