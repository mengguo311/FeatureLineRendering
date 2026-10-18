from env import *
def correspond(X,source_uv,c,tc,z,a):
 uv,d=project(X,tc);finite=np.isfinite(uv).all(1)&np.isfinite(d)&(d>.2);q=np.rint(np.nan_to_num(uv)).astype(int);inside=finite&(q[:,0]>=0)&(q[:,0]<tc['width'])&(q[:,1]>=0)&(q[:,1]<tc['height']);state=np.zeros(len(X),np.uint8);state[~inside]=3;ids=np.flatnonzero(inside);dz=z[q[ids,1],q[ids,0]];alpha=a[q[ids,1],q[ids,0]];good=np.isfinite(dz)&(dz>.2)&(alpha>=.5);p=dz/np.sqrt(tc['fx']*tc['fy']);delta=d[ids]-dz;state[ids[good&(delta>2*p)]]=2;state[ids[good&(delta< -2*p)]]=4;ok=ids[good&(abs(delta)<=2*p)]
 if len(ok):
  pt=z[q[ok,1],q[ok,0]]/np.sqrt(tc['fx']*tc['fy']);Y=unproject(q[ok],z[q[ok,1],q[ok,0]],tc);back,_=project(Y,c);cycle=np.linalg.norm(back-source_uv[ok],axis=1);world=np.linalg.norm(X[ok]-Y,axis=1);accept=(cycle<=1.5)&(world<=3*pt);state[ok[accept]]=1;state[ok[~accept]]=5
 return state,q
def local_edges(mask,X,p):
 ids=np.full(mask.shape,-1,int);ids[mask]=np.arange(mask.sum());ii=[];jj=[]
 for a,b in [(ids[:,:-1],ids[:,1:]),(ids[:-1],ids[1:])]:
  g=(a>=0)&(b>=0);ii.append(a[g]);jj.append(b[g])
 i=np.concatenate(ii);j=np.concatenate(jj);d=np.linalg.norm(X[i]-X[j],axis=1)/np.maximum((p[i]+p[j])/2,1e-20);g=np.isfinite(d)&(d<=4);return i[g],j[g],d[g]
def normal_evidence(z,a,c,up):
 h,w=z.shape;y,x=np.mgrid[:h,:w];uv=np.c_[x.ravel(),y.ravel()];X=unproject(uv,z.ravel(),c).reshape(h,w,3);valid=np.isfinite(z)&(z>.2)&(a>=.5);safe=np.zeros_like(valid);safe[2:-2,2:-2]=True;good=valid&safe;p=z/np.sqrt(c['fx']*c['fy']);east=np.roll(X,-2,1);west=np.roll(X,2,1);south=np.roll(X,-2,0);north=np.roll(X,2,0);n=np.cross(east-west,south-north);length=np.linalg.norm(n,axis=2);n/=np.maximum(length[...,None],1e-30);good&=np.isfinite(n).all(2)&(length>1e-20);res=np.zeros_like(z);extent=np.zeros_like(z)
 for dy in [-2,0,2]:
  for dx in [-2,0,2]:
   Y=np.roll(np.roll(X,dy,0),dx,1);v=np.roll(np.roll(valid,dy,0),dx,1);delta=Y-X;rr=abs((delta*n).sum(2))/p;dist=np.linalg.norm(delta,axis=2)/p;good&=v&np.isfinite(rr)&np.isfinite(dist);res=np.maximum(res,rr);extent=np.maximum(extent,dist)
 good&=(res<=2)&(extent<=8);ang=np.degrees(np.arccos(np.clip(abs(n@np.asarray(up)),0,1)));ang[~good]=np.nan
 return dict(valid=good,angle=ang,planarity_p=res,extent_p=extent,normal=n,upright=good&(ang<=20))
