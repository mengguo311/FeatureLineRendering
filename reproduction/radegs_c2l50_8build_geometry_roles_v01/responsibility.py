"""Complete finite-EWA source responsibility; never nearest-center/top-K attribution."""
from env import *
class ProjectedSource:
 def __init__(self,uv,z,S,opacity,color,ids,groups=None):
  if groups is not None and np.any(groups!=0):raise ValueError('Only original source group=0 allowed; ink cannot self-support')
  if not all(np.isfinite(x).all() for x in [uv,z,S,opacity,color]):raise ValueError('Nonfinite activated projection')
  self.uv=np.asarray(uv);self.z=np.asarray(z);self.S=np.asarray(S);self.opacity=np.asarray(opacity);self.color=np.asarray(color);self.ids=np.asarray(ids)
  self.det=S[:,0,0]*S[:,1,1]-S[:,0,1]**2;assert (self.det>1e-18).all();assert np.all((opacity>=0)&(opacity<=1));assert len(np.unique(ids))==len(ids)
  self.radius=3*np.sqrt(np.stack([S[:,0,0],S[:,1,1]],1))
 @classmethod
 def from_asset(cls,a,c,s):
  uv,z,S=project_cov(a['means'],a['covariance'],c,.3 if s=='ficus' else .0144);det=np.linalg.det(S);valid=(z>.2)&np.isfinite(uv).all(1)&np.isfinite(S).all((1,2))&(det>1e-18)
  p=cls(uv[valid],z[valid],S[valid],a['opacity'][valid],colors(a,c)[valid],np.flatnonzero(valid));p.invalid_source_ids=np.flatnonzero(~valid);p.camera=c;return p
 def query(self,pixel,all_N=False):
  pixel=np.asarray(pixel);d=pixel-self.uv
  ix=np.arange(len(self.z)) if all_N else np.flatnonzero((abs(d)<=self.radius).all(1))
  d=d[ix];S=self.S[ix];q=(S[:,1,1]*d[:,0]**2-2*S[:,0,1]*d[:,0]*d[:,1]+S[:,0,0]*d[:,1]**2)/self.det[ix];good=(q<=9)&(self.z[ix]>.2);ix=ix[good];q=q[good];order=np.argsort(self.z[ix],kind='stable');ix=ix[order];q=q[order]
  al=np.clip(self.opacity[ix]*np.exp(-.5*q),0,.999);T=np.r_[1.,np.cumprod(1-al)[:-1]] if len(al) else np.empty(0);active=T>=1e-5;al=al*active;T=np.r_[1.,np.cumprod(1-al)[:-1]] if len(al) else np.empty(0);w=al*T;total=float(w.sum());alpha=float(1-np.prod(1-al));cross=np.flatnonzero((T>.5)&(T*(1-al)<=.5));median=float(self.z[ix[cross[0]]]) if len(cross) else 0.
  quant=[]
  for t in [.1,.5,.9]:quant.append(float(self.z[ix[min(np.searchsorted(np.cumsum(w),t*total),len(ix)-1)]]) if total>0 else 0.)
  return dict(ids=self.ids[ix],weight=w,alpha_i=al,T=T,z=self.z[ix],q=q,alpha=alpha,median=median,expected=float(np.dot(w,self.z[ix])/total) if total else 0.,z_quantiles=np.array(quant),rgb=np.sum(w[:,None]*self.color[ix],axis=0),trans=1-alpha)
def mass(rows):
 ids=np.unique(np.concatenate([r['ids'] for r in rows])) if rows else np.empty(0,dtype=int);values=np.zeros(len(ids))
 for r in rows:np.add.at(values,np.searchsorted(ids,r['ids']),r['weight'])
 return ids,values/max(len(rows),1)
def measure_difference(left,right):
 ia,wa=mass(left);ib,wb=mass(right);ids=np.union1d(ia,ib);a=np.zeros(len(ids));b=a.copy();a[np.searchsorted(ids,ia)]=wa;b[np.searchsorted(ids,ib)]=wb
 pa=a/max(a.sum(),1e-15);pb=b/max(b.sum(),1e-15)
 return dict(ids=ids,left=a,right=b,left_normalized=pa,right_normalized=pb,difference=pa-pb,L1=float(abs(pa-pb).sum()),overlap=float(np.minimum(pa,pb).sum()),left_alpha=float(a.sum()),right_alpha=float(b.sum()))
