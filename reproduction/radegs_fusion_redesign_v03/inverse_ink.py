import numpy as np
from scipy.sparse import coo_matrix
from common import core

def kernel_matrix(a,c,depth=None,alpha=None):
 uv,z,S=core.project_cov(a['means'],a['covariance'],c,.12);h=c['height'];w=c['width'];rows=[];cols=[];vals=[];focal=np.sqrt(c['fx']*c['fy'])
 for i in range(len(z)):
  if not np.isfinite(z[i]) or z[i]<=1e-8:continue
  aa,b,cc=S[i,0,0],S[i,0,1],S[i,1,1];det=aa*cc-b*b
  if not np.isfinite(det) or det<=1e-18:continue
  u,v=uv[i];rx=3*np.sqrt(aa);ry=3*np.sqrt(cc)
  if not np.isfinite([u,v]).all() or u+rx<0 or v+ry<0 or u-rx>w-1 or v-ry>h-1:continue
  x0=int(max(0,np.ceil(u-rx)));x1=int(min(w-1,np.floor(u+rx)));y0=int(max(0,np.ceil(v-ry)));y1=int(min(h-1,np.floor(v+ry)))
  yy,xx=np.mgrid[y0:y1+1,x0:x1+1];dx=xx-u;dy=yy-v;q=(cc*dx*dx-2*b*dx*dy+aa*dy*dy)/det;valid=q<=9
  if depth is not None and alpha is not None:
   d=depth[yy,xx];al=alpha[yy,xx];known=np.isfinite(d)&(d>0)&np.isfinite(al)&(al>=.5);tol=np.maximum(.005*d,2*d/focal);valid&=~(known&(z[i]>d+tol))
  rows.extend((yy[valid]*w+xx[valid]).tolist());cols.extend([i]*int(valid.sum()));vals.extend(np.exp(-q[valid]/2).tolist())
 return coo_matrix((np.array(vals),(np.array(rows,dtype=np.int32),np.array(cols,dtype=np.int32))),shape=(h*w,len(z))).tocsr()

def forward(a,G):
 g=G.tocoo(copy=False);logT=np.bincount(g.row,weights=np.log1p(-a[g.col]*g.data),minlength=G.shape[0]);return -np.expm1(logT)

def one_loss(a,obs):
 G=obs['G'];g=G.tocoo(copy=False);D=obs['target'];region=obs['region'];p=forward(a,G);res=p-D;gradpix=np.zeros(len(D));loss=0
 known=obs.get('negative_known',np.ones(len(D),bool))
 for mask,weight in [(region&(D>.2),1.),(region&known&(D<.05),1.),(region&known&(D>=.05)&(D<=.2),.2)]:
  n=int(mask.sum())
  if n:loss+=weight*float(np.mean(res[mask]**2));gradpix[mask]=2*weight*res[mask]/n
 grad=np.bincount(g.col,weights=gradpix[g.row]*(1-p[g.row])*g.data/(1-a[g.col]*g.data),minlength=len(a))
 return loss,grad

def objective(a,observations,sparsity=1e-4):
 # Contributions first averaged inside camera ID, then across distinct cameras.
 groups={}
 for o in observations:groups.setdefault(o['view'],[]).append(o)
 loss=0.;grad=np.zeros_like(a)
 for group in groups.values():
  for o in group:
   f,g=one_loss(a,o);loss+=f/len(group)/len(groups);grad+=g/len(group)/len(groups)
 loss+=sparsity*float(np.mean(a));grad+=sparsity/len(a)
 return loss,grad
