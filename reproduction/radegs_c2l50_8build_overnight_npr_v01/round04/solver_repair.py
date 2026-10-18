from env import *

def repair(A,rhs,x,maxiter=5000):
 """Same M-matrix system. Project an initial numerical guess, then Jacobi;
 acceptance requires original residual and probability tolerances, not clipping.
 """
 d=A.diagonal();assert np.all(d>0)
 assert np.allclose(rhs.sum(1),np.asarray(A@np.ones(A.shape[0])).ravel(),rtol=0,atol=1e-10),'rhs is not a partition of unity'
 x=np.maximum(x,0);ss=x.sum(1);x[ss>0]/=ss[ss>0,None];x[ss==0]=1/rhs.shape[1];norm=np.maximum(np.linalg.norm(rhs,axis=0),1e-30)
 for k in range(maxiter):
  residual=rhs-A@x
  if k%20==0:
   rel=np.linalg.norm(residual,axis=0)/norm
   if rel.max()<=1.01e-8 and x.min()>-1e-5 and x.max()<1+1e-5 and np.allclose(x.sum(1),1,atol=1e-5):return x,dict(iterations=k,relative_residual=rel.tolist(),method='same_matrix_Jacobi_after_projected_initial_guess')
  x=x+residual/d[:,None]
 rel=np.linalg.norm(rhs-A@x,axis=0)/norm
 raise RuntimeError(('same_system_repair_not_converged',maxiter,rel.tolist(),float(x.min()),float(x.max())))
