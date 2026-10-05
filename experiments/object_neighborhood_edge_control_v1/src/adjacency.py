"""Centre radius and convex ellipsoid proximity proxies, never physical contact."""
import numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import minimize

def center_pairs(mu,labels,radius):
    mu=np.asarray(mu);labels=np.asarray(labels)
    return [(i,j) for i,j in sorted(cKDTree(mu).query_pairs(radius))
            if labels[i]>0 and labels[j]>0 and labels[i]!=labels[j]]

def ellipsoid_distance(a,L_a,b,L_b,k=3):
    a,b,L_a,L_b=[np.asarray(v,dtype=np.float64) for v in (a,b,L_a,L_b)]
    # Scale world distances and use unit balls to avoid ill-conditioned tiny GS.
    scale=max(np.linalg.norm(b-a),k*np.linalg.norm(L_a),k*np.linalg.norm(L_b),1e-8)
    b=(b-a)/scale;a=np.zeros(3);L_a=L_a*k/scale;L_b=L_b*k/scale
    def fun(x):
        d=a+L_a@x[:3]-b-L_b@x[3:]
        return d@d
    def jac(x):
        d=a+L_a@x[:3]-b-L_b@x[3:]
        return 2*np.r_[L_a.T@d,-L_b.T@d]
    cons=[{'type':'ineq','fun':lambda x:1-x[:3]@x[:3]},
          {'type':'ineq','fun':lambda x:1-x[3:]@x[3:]}]
    r=minimize(fun,np.zeros(6),jac=jac,constraints=cons,method='SLSQP',
               options={'ftol':1e-12,'maxiter':150})
    def project(x):
        x=x.reshape(2,3);return (x/np.maximum(np.linalg.norm(x,axis=1,keepdims=True),1)).ravel()
    def certificate(x):
        x=project(x);d=b+L_b@x[3:]-L_a@x[:3];upper=float(np.linalg.norm(d))
        direction=d/max(upper,1e-15)
        lower=max(0,float(direction@b-np.linalg.norm(L_a.T@direction)-np.linalg.norm(L_b.T@direction)))
        return lower,upper
    x=project(r.x);lower,upper=certificate(x)
    if (upper-lower)*scale>1e-5:
        # Projected accelerated gradient is a convex fallback; certificate checks
        # the feasible primal distance against a separating-plane lower bound.
        A=np.concatenate([L_a,-L_b],axis=1);step=1/(2*np.linalg.norm(A,ord=2)**2+1e-15)
        y=x.copy();momentum=1.
        for _ in range(3000):
            new=project(y-step*jac(y));next_momentum=(1+np.sqrt(1+4*momentum*momentum))/2
            y=new+(momentum-1)/next_momentum*(new-x);x=new;momentum=next_momentum
            lower,upper=certificate(x)
            if (upper-lower)*scale<=1e-5:break
    if (upper-lower)*scale>1e-5:
        raise RuntimeError(f'uncertified ellipsoid distance interval [{lower*scale},{upper*scale}]')
    return float(upper*scale)

def ellipsoid_pairs(mu,L,labels,k=3,epsilon=.05):
    mu,L,labels=map(np.asarray,(mu,L,labels))
    ext=k*np.sqrt((L*L).sum(axis=2));bounding=np.linalg.norm(ext,axis=1)
    tree=cKDTree(mu);result=[]
    # Radius expands by the largest ellipsoid; no small centre-only prefilter.
    for i in range(len(mu)):
        if labels[i]<=0:continue
        for j in tree.query_ball_point(mu[i],bounding[i]+bounding.max()+epsilon):
            if j<=i or labels[j]<=0 or labels[i]==labels[j]:continue
            if np.any(np.abs(mu[i]-mu[j])>ext[i]+ext[j]+epsilon):continue
            if ellipsoid_distance(mu[i],L[i],mu[j],L[j],k)<=epsilon:result.append((i,j))
    return result

def surface_relation(distance,epsilon_contact,epsilon_near):
    return 'contact_GT' if distance<=epsilon_contact else 'near_noncontact' if distance<=epsilon_near else 'separated_GT'
