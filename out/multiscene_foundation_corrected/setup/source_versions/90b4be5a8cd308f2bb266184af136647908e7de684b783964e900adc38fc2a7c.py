"""Corner-preserving, conservative trust-region simplification. Main epsilon=0."""
import numpy as np

def segment_distance(points,a,b):
    v=b-a;u=np.clip((points-a)@v/max(float(v@v),1e-15),0,1)
    return np.linalg.norm(points-(a+u[:,None]*v),axis=1)

def simplify(p,epsilon,trust,corner_deg=35):
    p=np.asarray(p)
    if epsilon<=0 or len(p)<=2:return p.copy(),np.arange(len(p))
    v=np.diff(p,axis=0);v/=np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-12)
    angles=np.degrees(np.arccos(np.clip((v[:-1]*v[1:]).sum(1),-1,1)))
    pins=np.r_[0,np.flatnonzero(angles>=corner_deg)+1,len(p)-1];kept=set(pins.tolist())
    def rec(a,b):
        if b-a<=1:return
        distance=segment_distance(p[a:b+1],p[a],p[b]);j=int(np.argmax(distance))+a
        # Lipschitz upper bound on reverse chord -> original polyline distance.
        samples=np.linspace(p[a],p[b],33)
        reverse=np.min(np.stack([segment_distance(samples,p[k],p[k+1]) for k in range(a,b)]),axis=0).max()
        bound=reverse+np.linalg.norm(p[b]-p[a])/64
        if distance.max()<=epsilon and bound<=trust:return
        if j==a or j==b:j=(a+b)//2
        kept.add(j);rec(a,j);rec(j,b)
    for a,b in zip(pins[:-1],pins[1:]):rec(int(a),int(b))
    indices=np.array(sorted(kept));return p[indices].copy(),indices

def budget_prefix(order,measure,target):
    """Match an ACTUAL monotone rendered cost, not path count or nominal length."""
    memo={}
    def at(n):
        if n not in memo:memo[n]=float(measure(order[:n]))
        return memo[n]
    lo,hi=0,len(order)
    if at(hi)<target:return hi,at(hi),dict(under_capacity=True,evaluations=len(memo))
    while hi-lo>1:
        mid=(lo+hi)//2
        if at(mid)<target:lo=mid
        else:hi=mid
    best=min([lo,hi],key=lambda n:(abs(at(n)-target),n))
    return best,at(best),dict(under_capacity=False,evaluations=len(memo))
