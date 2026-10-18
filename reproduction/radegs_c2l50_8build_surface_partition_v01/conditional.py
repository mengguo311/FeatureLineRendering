from env import *
def restrict_ray(mu,cov,rays):
 n=len(mu);z=np.full(n,np.nan);sigma=z.copy();q=z.copy();good=np.isfinite(mu).all(1)&np.isfinite(cov).all((1,2))&np.isfinite(rays).all(1);ix=np.flatnonzero(good)
 if len(ix):
  ev=np.linalg.eigvalsh(cov[ix]);ix=ix[(ev>0).all(1)]
  if len(ix):
   P=np.linalg.inv(cov[ix]);r=rays[ix];m=mu[ix];den=np.einsum('ni,nij,nj->n',r,P,r);zz=np.einsum('ni,nij,nj->n',r,P,m)/den;delta=zz[:,None]*r-m;qq=np.einsum('ni,nij,nj->n',delta,P,delta);z[ix]=zz;sigma[ix]=np.sqrt(1/den);q[ix]=np.maximum(qq,0)
 valid=np.isfinite(z)&np.isfinite(sigma)&(z>.2)&(q<=9);return z,sigma,q,valid
def weighted_quantile(x,w,p):
 good=np.isfinite(x)&np.isfinite(w)&(w>0)
 if not good.any():return float('nan')
 x=x[good];w=w[good];i=np.argsort(x,kind='stable');return float(x[i[min(np.searchsorted(np.cumsum(w[i]),p*w.sum()),len(i)-1)]])
def enrich(e,a,c):
 E=np.asarray(c['extrinsic']);R=E[:3,:3];ids=e['source_index'];mu=a['means'][ids]@R.T+E[:3,3];cov=R@a['covariance'][ids]@R.T;rows=np.repeat(np.arange(len(e['query_uv'])),np.diff(e['csr_offsets']));uv=e['query_uv'][rows];rays=np.c_[(uv[:,0]-c['cx'])/c['fx'],(uv[:,1]-c['cy'])/c['fy'],np.ones(len(rows))];z,sigma,q,valid=restrict_ray(mu,cov,rays)
 stats=np.full((len(e['query_uv']),7),np.nan)
 for i,(lo,hi) in enumerate(zip(e['csr_offsets'][:-1],e['csr_offsets'][1:])):
  w=e['weight'][lo:hi];ok=valid[lo:hi];total=w.sum();kept=(w*ok).sum()/total if total>0 else 0.;ww=w*ok;quant=[weighted_quantile(z[lo:hi],ww,t) for t in [.1,.5,.9]];sig=weighted_quantile(sigma[lo:hi],ww,.5);stats[i]=[*quant,sig,kept,max(quant[2]-quant[0],2.563103*sig),total]
 return dict(conditional_z=z,conditional_sigma=sigma,conditional_qmin=q,conditional_valid=valid,conditional_row=rows,conditional_stats=stats)
