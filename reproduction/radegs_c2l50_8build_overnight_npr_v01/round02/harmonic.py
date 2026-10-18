from env import *
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import cg,splu
def edge_weight(a,b,d,color=True):
 return np.maximum(np.exp(-np.sum((a-b)**2,axis=1)/(2*.12**2)) if color else np.ones(len(a)),1e-5)/np.maximum(d,1)
def labels(q):
 order=np.sort(q,axis=1);out=np.argmax(q,axis=1).astype(np.uint8)+1;out[(order[:,-1]<.65)|(order[:,-1]-order[:,-2]<.2)]=0;return out
def solve(n,i,j,w,seeds,gamma=None,prior=None):
 i=np.asarray(i,int);j=np.asarray(j,int);w=np.asarray(w,float);seeds=np.asarray(seeds,int)
 assert len(i)==len(j)==len(w) and np.all(w>0) and np.isfinite(w).all() and np.all((seeds>=0)&(seeds<=3))
 gamma=np.zeros(n) if gamma is None else np.asarray(gamma,float);prior=np.zeros((n,3)) if prior is None else np.asarray(prior,float)
 W=sparse.coo_matrix((np.r_[w,w],(np.r_[i,j],np.r_[j,i])),shape=(n,n)).tocsr();W.sum_duplicates();nc,comp=connected_components(W,directed=False)
 touched=np.zeros(nc,bool);touched[comp[(seeds>0)|(gamma>0)]]=True;active=touched[comp];fixed=np.flatnonzero(seeds>0);free=np.flatnonzero(active&(seeds==0));q=np.zeros((n,3),float);q[fixed,seeds[fixed]-1]=1
 meta=dict(nodes=n,edges=len(i),components=int(nc),unanchored_nodes=int((~active).sum()),fixed=len(fixed),free=len(free),iterations=[],relative_residual=[])
 if not len(free):return q,meta
 L=sparse.diags(np.asarray(W.sum(1)).ravel()+gamma)-W;A=L[free][:,free].tocsr();rhs=W[free][:,fixed]@q[fixed]+gamma[free,None]*prior[free];M=sparse.diags(1/A.diagonal())
 invalid=[]
 for k in range(3):
  steps=[0]
  def callback(x):steps[0]+=1
  x,info=cg(A,rhs[:,k],M=M,rtol=1e-8,atol=0,maxiter=3000,callback=callback)
  rel=float(np.linalg.norm(A@x-rhs[:,k])/max(np.linalg.norm(rhs[:,k]),1e-30))
  if info!=0 or rel>1.01e-8:invalid.append(['CG',k,int(info),rel])
  q[free,k]=x;meta['iterations'].append(steps[0]);meta['relative_residual'].append(rel)
 if q.min()<=-1e-5 or q.max()>=1+1e-5 or not np.allclose(q[active].sum(1),1,atol=1e-5):invalid.append(['probability',float(q.min()),float(q.max())])
 if invalid:
  lu=splu(A.tocsc(),permc_spec='MMD_AT_PLUS_A');x=lu.solve(rhs);res=[float(np.linalg.norm(A@x[:,k]-rhs[:,k])/max(np.linalg.norm(rhs[:,k]),1e-30)) for k in range(3)];assert max(res)<=1.01e-8,('LU_INVALID',res);q[free]=x;meta['cg_invalid_preserved']=invalid;meta['direct_fallback_relative_residual']=res;meta['LU_nonzeros']=int(lu.L.nnz+lu.U.nnz)
 assert q.min()>-1e-5 and q.max()<1+1e-5,('maximum_principle',q.min(),q.max())
 q=np.clip(q,0,1);ss=q.sum(1);assert np.allclose(ss[active],1,atol=1e-5),('sum_invalid',ss[active].min(),ss[active].max());q[active]/=ss[active,None]
 return q,meta
