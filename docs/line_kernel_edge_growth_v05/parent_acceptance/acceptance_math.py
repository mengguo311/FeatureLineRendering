import numpy as np

def project(points,knots):
 points=np.asarray(points,float);knots=np.asarray(knots,float);v=np.diff(knots,axis=0);length=np.linalg.norm(v,axis=1);length2=np.sum(v*v,axis=1);arc=np.r_[0.,np.cumsum(length)];ss=[];dd=[];tt=[]
 for start in range(0,len(points),512):
  delta=points[start:start+512,None,:]-knots[None,:-1,:]
  u=np.clip(np.sum(delta*v[None,:,:],axis=2)/np.maximum(length2,1e-30),0,1)
  dist2=np.sum((delta-u[:,:,None]*v[None,:,:])**2,axis=2);idx=np.argmin(dist2,axis=1);row=np.arange(len(idx))
  ss.append(arc[idx]+u[row,idx]*length[idx]);dd.append(np.sqrt(dist2[row,idx]));tt.append(v[idx]/np.maximum(length[idx,None],1e-15))
 return np.concatenate(ss),np.concatenate(dd),np.concatenate(tt)

def interval_union(intervals):
 z=np.sort(np.asarray(intervals,float).reshape(-1,2),axis=1);z=z[np.lexsort((z[:,1],z[:,0]))];merged=[]
 for a,b in z:
  if merged and a<=merged[-1][1]+1e-8:merged[-1][1]=max(merged[-1][1],float(b))
  else:merged.append([float(a),float(b)])
 a=np.array(merged,float).reshape(-1,2);lengths=a[:,1]-a[:,0];gaps=a[1:,0]-a[:-1,1]
 return a,float(lengths.sum()),float(lengths.max(initial=0)),float(gaps.max(initial=0)),float(gaps.sum())
