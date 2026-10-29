from runtime import *

def canonical(d):
    d=unit(d); j=int(np.argmax(np.abs(d)))
    return d if d[j]>=0 else -d
def plane(d):
    e=np.eye(3)[int(np.argmin(np.abs(d)))];u=unit(np.cross(d,e))
    return np.stack([u,np.cross(d,u)],axis=1)
def tls(x):
    a=x.mean(0);y=x-a;_,v=np.linalg.eigh(y.T@y)
    return a,canonical(v[:,-1])
def directions(d,angles):
    d=canonical(d);U=plane(d)
    return np.array([canonical(d+np.tan(np.deg2rad(i))*U[:,0]+np.tan(np.deg2rad(j))*U[:,1]) for i in angles for j in angles])
def hough_axis(x,tangent,piece,p,chord):
    """Two genuine sparse offset/direction accumulators; all local kernels vote."""
    n=len(x); origin=(x.min(0)+x.max(0))*.5
    d=canonical(chord);evaluations=0;massmax=0.;peak=0.;selected=np.zeros(n,bool)
    for angles,width in [(CFG['coarse_degrees'],CFG['coarse_bin_p']*p),(CFG['fine_degrees'],CFG['fine_bin_p']*p)]:
        ds=directions(d,angles)
        angle=np.arccos(np.clip(np.abs(tangent@ds.T),0,1))
        mass=np.exp(-.5*(angle/np.deg2rad(CFG['support_angle_deg']))**2)
        mass/=np.maximum(mass.sum(1,keepdims=True),1e-30)
        massmax=max(massmax,float(mass.sum(1).max(initial=0)))
        best=None
        for j,dd in enumerate(ds):
            U=plane(dd);keys=np.floor(((x-origin)@U)/width).astype(np.int64)
            cells,inv=np.unique(keys,axis=0,return_inverse=True)
            votes=np.bincount(inv,weights=mass[:,j]); k=int(votes.argmax())
            # Stable ties: central orientation is preferred, then original index.
            score=(float(votes[k]),float(abs(dd@d)),-j)
            if best is None or score>best[0]:
                best=(score,dd,origin+U@((cells[k]+.5)*width),inv==k)
            evaluations+=n
        _,d,a,selected=best;peak=best[0][0]
    # Offset quantization is removed using only the winning-cell support.
    if selected.any(): a=x[selected].mean(0)
    support=(np.linalg.norm(np.cross(x-a,d),axis=1)<=CFG['support_distance_p']*p)&(np.abs(tangent@d)>=np.cos(np.deg2rad(CFG['support_angle_deg'])))
    count=int(support.sum());pieces=len(np.unique(piece[support]));span=float(np.ptp(x[support]@d)/p) if count else 0.
    valid=count>=CFG['min_kernels'] and pieces>=CFG['min_pieces'] and span>=CFG['min_span_p']
    return dict(axis=d if valid else None,anchor=a,support=support,support_count=count,support_pieces=pieces,span_p=span,
                point_direction_votes=evaluations,max_mass=massmax,peak_vote=peak,ambiguous=not valid)

def corner_mask(P,closed=False):
    n=len(P); corner=np.zeros(n,bool)
    for i in range(1,n-1):
        left=P[i]-P[max(0,i-2)];right=P[min(n-1,i+2)]-P[i]
        corner[i]=np.dot(unit(left),unit(right))<=np.cos(np.deg2rad(CFG['corner_deg']))
    if closed and n>3:
        corner[0]=corner[-1]=np.dot(unit(P[0]-P[-3]),unit(P[2]-P[0]))<=np.cos(np.deg2rad(CFG['corner_deg']))
    return corner,corner[:-1]|corner[1:]
def knot_tangents(P,closed=False):
    T=np.empty_like(P)
    for i in range(len(P)):
        T[i]=unit(P[min(len(P)-1,i+2)]-P[max(0,i-2)])
    if closed and len(P)>4: T[0]=T[-1]=unit(P[2]-P[-3])
    return T
def eval_curve(B,t):
    t=np.asarray(t);a=1-t
    q=a[:,None]**3*B[0]+3*(a*a*t)[:,None]*B[1]+3*(a*t*t)[:,None]*B[2]+t[:,None]**3*B[3]
    d=3*(a*a)[:,None]*(B[1]-B[0])+6*(a*t)[:,None]*(B[2]-B[1])+3*(t*t)[:,None]*(B[3]-B[2])
    return q,d
def sample_poly(P,t):
    ds=np.linalg.norm(np.diff(P,axis=0),axis=1);cum=np.r_[0.,np.cumsum(ds)];L=cum[-1]
    at=np.asarray(t)*L;ind=np.clip(np.searchsorted(cum,at,side='right')-1,0,len(ds)-1)
    u=(at-cum[ind])/np.maximum(ds[ind],1e-30)
    return P[ind]*(1-u[:,None])+P[ind+1]*u[:,None]
def tube_distance(x,P):
    a=P[:-1];d=np.diff(P,axis=0);den=np.sum(d*d,axis=1)
    f=np.clip(np.einsum('nmi,mi->nm',x[:,None]-a[None],d)/np.maximum(den,1e-30)[None],0,1)
    return np.linalg.norm(x[:,None]-(a[None]+f[:,:,None]*d[None]),axis=2).min(1)
def macro(q):
    chord=unit(q[-1]-q[0]);v=q-q[0];off=v-(v@chord)[:,None]*chord
    bend=float(np.degrees(np.arccos(np.clip(unit(q[len(q)//2]-q[0])@unit(q[-1]-q[len(q)//2]),-1,1))))
    return bend,off,np.linalg.norm(off,axis=1)
def fit_cubic(P,t,x,t0,t1,p,axis=None,anchor=None):
    """Same two-handle endpoint/tangent-constrained fitter in both arms."""
    origin=P[0];Y=(x-origin)/p;E=(P[-1]-origin)/p
    L=np.linalg.norm(np.diff(P,axis=0),axis=1).sum()/p
    a=1-t;b1=3*a*a*t;b2=3*a*t*t
    base=(b2+t**3)[:,None]*E
    A=np.stack([b1[:,None]*t0,-b2[:,None]*t1],axis=2)
    target=Y-base;h=np.array([L/3,L/3]);w=np.ones(len(t))
    if axis is not None:
        proj=np.eye(3)-np.outer(axis,axis);G=np.einsum('ij,njk->nik',proj,A)
        gy=((anchor-origin)/p-base)@proj.T
        GH=np.einsum('nik,nil->kl',G,G);gb=np.einsum('nik,ni->k',G,gy)
    for _ in range(CFG['irls_steps']):
        H=np.einsum('n,nik,nil->kl',w,A,A);rhs=np.einsum('n,nik,ni->k',w,A,target)
        if axis is not None: H+=CFG['axis_weight']*GH;rhs+=CFG['axis_weight']*gb
        H+=np.eye(2)*1e-12
        h=np.clip(np.linalg.solve(H,rhs),0,CFG['handle_max_length']*L)
        residual=np.linalg.norm(base+np.einsum('nik,k->ni',A,h)-Y,axis=1)
        w=np.minimum(1.,CFG['huber_p']/np.maximum(residual,1e-30))
    return np.array([P[0],P[0]+p*h[0]*t0,P[-1]-p*h[1]*t1,P[-1]])
def fidelity(B,P,t,x,oldt,pixel,p):
    q,d=eval_curve(B,t);newt=unit(d)
    if not np.isfinite(q).all() or (np.linalg.norm(d,axis=1)<1e-15*p).any(): return False,'degenerate',{}
    move=float((np.linalg.norm(q-x,axis=1)/pixel).max(initial=0))
    angle=float(np.degrees(np.arccos(np.clip(np.sum(newt*oldt,axis=1),-1,1))).max(initial=0))
    grid=np.linspace(0,1,CFG['check_sites']);qq,dd=eval_curve(B,grid);old=sample_poly(P,grid)
    L=float(np.linalg.norm(np.diff(P,axis=0),axis=1).sum());newL=float(np.linalg.norm(np.diff(qq,axis=0),axis=1).sum())
    ratio=newL/max(L,1e-30);tube=float(max(tube_distance(qq,P).max(),tube_distance(old,qq).max())/p)
    bo,offo,so=macro(old);bn,offn,sn=macro(qq)
    met=dict(max_move_p=move,max_angle_deg=angle,length_ratio=ratio,tube_p=tube,old_bend_deg=bo,new_bend_deg=bn,old_sag_p=float(so.max()/p),new_sag_p=float(sn.max()/p))
    if move>CFG['move_p']+1e-10: return False,'displacement',met
    if angle>CFG['angle_deg']+1e-8: return False,'angle',met
    if not CFG['length_ratio'][0]<=ratio<=CFG['length_ratio'][1]: return False,'length',met
    if tube>CFG['move_p']+1e-10: return False,'support_tube',met
    if bo>=CFG['bend_trigger_deg'] and not CFG['bend_ratio'][0]<=bn/bo<=CFG['bend_ratio'][1]: return False,'bend',met
    if so.max()>=CFG['sag_trigger_p']*p:
        sr=sn.max()/max(so.max(),1e-30);active=so>=CFG['sag_trigger_p']*p
        if not CFG['bend_ratio'][0]<=sr<=CFG['bend_ratio'][1] or (np.sum(offo[active]*offn[active],axis=1)<0).any(): return False,'sag_or_bend_sign',met
    return True,'accepted',met
