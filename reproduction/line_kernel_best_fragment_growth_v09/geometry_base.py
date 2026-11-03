"""Exact pure geometry functions from pinned v05 core; no fitting or imports of old runners."""
import numpy as np
EPS=1e-8
RAD=np.pi/180
def clean(q):
    q = np.asarray(q, float)
    return q[np.r_[True, np.linalg.norm(np.diff(q, axis=0), axis=1) > EPS]]

def arc(q):
    return np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]

def sample(q, spacing=1.0):
    ss = arc(q)
    tt = np.linspace(0, ss[-1], max(2, int(np.ceil(ss[-1] / spacing)) + 1))
    return np.stack([np.interp(tt, ss, q[:, k]) for k in range(3)], 1)

def project(x, q):
    """Exact nearest finite segment, deterministic lowest segment on ties."""
    v = np.diff(q, axis=0)
    ll = np.einsum('ij,ij->i', v, v)
    ss = arc(q)
    out = []
    for lo in range(0, len(x), 1024):
        dx = x[lo:lo + 1024, None, :] - q[None, :-1, :]
        u = np.clip(np.einsum('nkj,kj->nk', dx, v) / np.maximum(ll, 1e-30), 0, 1)
        residual = dx - u[:, :, None] * v
        ds = np.einsum('nkj,nkj->nk', residual, residual)
        j = ds.argmin(1)
        ii = np.arange(len(j))
        uu = u[ii, j]
        tangent = v[j] / np.sqrt(np.maximum(ll[j, None], 1e-30))
        out.append((ss[j] + uu * np.sqrt(ll[j]), np.sqrt(ds[ii, j]), tangent, j, q[j] + uu[:, None] * v[j]))
    return tuple((np.concatenate([z[k] for z in out]) for k in range(5)))

def extended_s(x, q):
    s, d, t, j, near = project(x, q)
    ss = arc(q)
    z = (j == 0) & (s < EPS)
    s[z] += np.minimum(0, np.sum((x[z] - q[0]) * t[z], 1))
    z = (j == len(q) - 2) & (s > ss[-1] - EPS)
    s[z] += np.maximum(0, np.sum((x[z] - q[-1]) * t[z], 1))
    return (s, d, t)

def union_intervals(intervals):
    z = sorted(((float(min(a, b)), float(max(a, b))) for a, b in intervals))
    out = []
    for a, b in z:
        if out and a <= out[-1][1] + EPS:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    ar = np.asarray(out, float).reshape(-1, 2)
    length = float(np.diff(ar, axis=1).sum()) if len(ar) else 0.0
    gaps = ar[1:, 0] - ar[:-1, 1] if len(ar) > 1 else np.empty(0)
    return (ar, length, float(np.diff(ar, axis=1).max(initial=0)), float(gaps.max(initial=0)), float(gaps.sum()))

def segment_contact(q):
    n = len(q) - 1
    if n < 3:
        return False
    ii, jj = np.triu_indices(n, 2)
    a = q[ii]
    b = q[jj]
    u = q[ii + 1] - a
    v = q[jj + 1] - b
    w = a - b
    aa = np.sum(u * u, 1)
    bb = np.sum(u * v, 1)
    cc = np.sum(v * v, 1)
    dd = np.sum(u * w, 1)
    ee = np.sum(v * w, 1)
    den = aa * cc - bb * bb
    s = (bb * ee - cc * dd) / np.maximum(den, 1e-30)
    t = (aa * ee - bb * dd) / np.maximum(den, 1e-30)
    interior = (den > 1e-20) & (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1)
    dist = np.where(interior, np.linalg.norm(w + s[:, None] * u - t[:, None] * v, axis=1), np.inf)
    for f in (0.0, 1.0):
        tt = np.clip((ee + f * bb) / np.maximum(cc, 1e-30), 0, 1)
        dist = np.minimum(dist, np.linalg.norm(w + f * u - tt[:, None] * v, axis=1))
        st = np.clip((f * bb - dd) / np.maximum(aa, 1e-30), 0, 1)
        dist = np.minimum(dist, np.linalg.norm(w + st[:, None] * u - f * v, axis=1))
    return bool(np.any(dist < 0.5 - EPS))

def contact_bounded(q,guard=lambda:None):
    """Same nonadjacent segment distance as segment_contact, bounded working memory."""
    n=len(q)-1
    for i in range(n-2):
        guard()
        for lo in range(i+2,n,4096):
            jj=np.arange(lo,min(n,lo+4096));a=q[i];b=q[jj];u=q[i+1]-a;v=q[jj+1]-b;w=a-b
            aa=np.sum(u*u);bb=np.sum(u*v,1);cc=np.sum(v*v,1);dd=np.sum(u*w,1);ee=np.sum(v*w,1);den=aa*cc-bb*bb
            s=(bb*ee-cc*dd)/np.maximum(den,1e-30);t=(aa*ee-bb*dd)/np.maximum(den,1e-30)
            interior=(den>1e-20)&(s>=0)&(s<=1)&(t>=0)&(t<=1)
            dist=np.where(interior,np.linalg.norm(w+s[:,None]*u-t[:,None]*v,axis=1),np.inf)
            for f in (0.,1.):
                tt=np.clip((ee+f*bb)/np.maximum(cc,1e-30),0,1);dist=np.minimum(dist,np.linalg.norm(w+f*u-tt[:,None]*v,axis=1))
                st=np.clip((f*bb-dd)/max(aa,1e-30),0,1);dist=np.minimum(dist,np.linalg.norm(w+st[:,None]*u-f*v,axis=1))
            if np.any(dist<.5-EPS):return True
    return False
