"""Positive image evidence only. Fixed old reachable vertices, no new graph edges."""
from free_io import *
from scipy.ndimage import gaussian_filter,sobel
import graph_birth_core as g
import free_core as f
import heapq

def project_camera(x,c):
 q=x@np.asarray(c.get('extrinsic',c.get('w2c')))[:3,:3].T+np.asarray(c.get('extrinsic',c.get('w2c')))[:3,3]
 z=q[:,2];den=np.where(abs(z)>1e-15,z,1.)
 return np.c_[c['fx']*q[:,0]/den+c['cx'],c['fy']*q[:,1]/den+c['cy']],z

def gradients(path):
 a=np.asarray(Image.open(path).convert('RGBA'),float)/255.;rgb=a[:,:,:3]*a[:,:,3:]+1-a[:,:,3:];y=rgb@np.array([.2126,.7152,.0722]);y=gaussian_filter(y,1.,mode='reflect')
 return sobel(y,axis=1,mode='reflect')/8.,sobel(y,axis=0,mode='reflect')/8.

def view_support(uv,depth,gx,gy):
 n=len(uv);h,w=gx.shape;v=uv[:,2]-uv[:,0];norm=np.linalg.norm(v,axis=1);valid=(depth>0).all(1)&np.isfinite(uv).all((1,2))&(norm>1e-8)&(uv[:,:,0]>=0).all(1)&(uv[:,:,0]<w).all(1)&(uv[:,:,1]>=0).all(1)&(uv[:,:,1]<h).all(1);v=v/np.maximum(norm[:,None],1e-15);hits=np.zeros((n,3),bool)
 for s in range(3):
  pos=uv[:,s];base=np.floor(np.nan_to_num(pos)).astype(np.int64)
  for dy in range(-2,3):
   for dx in range(-2,3):
    pix=base+[dx,dy];ok=valid&(np.sum((pix-pos)**2,axis=1)<=4+1e-12)&(pix[:,0]>=0)&(pix[:,0]<w)&(pix[:,1]>=0)&(pix[:,1]<h);ii=np.flatnonzero(ok)
    if not len(ii):continue
    x=pix[ii,0];y=pix[ii,1];xx=gx[y,x];yy=gy[y,x];mag=np.hypot(xx,yy);align=np.abs(-yy*v[ii,0]+xx*v[ii,1])/np.maximum(mag,1e-15);hits[ii,s]|=(mag>=.1)&(align>=np.cos(np.pi/6))
 return np.where(~valid,2,np.where(hits.all(1),1,0)).astype(np.uint8)

def evidence(c,z,a,guard=lambda:None):
 cams={q['view']:q for q in json.loads(Path(c['cameras']).read_text())[c['scene']]};tr=json.loads(Path(c['image_transforms']).read_text());frames={q['file_path'].split('/')[-1]:q for q in tr['frames']};all_status=[]
 for view,path in c['evidence_images'].items():
  guard();cam=cams[view];frame=frames[view.replace('test_','')];np.testing.assert_array_equal(cam['original_c2w_gl'],frame['transform_matrix']);assert cam['width']==800 and cam['height']==800;focal=.5*800/np.tan(.5*tr['camera_angle_x']);assert abs(cam['fx']-focal)<1e-8 and abs(cam['fy']-focal)<1e-8;assert cam['cx']==399.5 and cam['cy']==399.5
  gx,gy=gradients(path);assert gx.shape==(800,800);ss=[]
  for lo in range(0,len(a['source']),4096):
   guard();sl=slice(lo,lo+4096);x=z['position'][a['source'][sl]//2]*c['p'];y=z['position'][a['target'][sl]//2]*c['p'];pts=np.stack([x,(x+y)/2,y],1);uv,depth=project_camera(pts.reshape(-1,3),cam);ss.append(view_support(uv.reshape(-1,3,2),depth.reshape(-1,3),gx,gy))
  all_status.append(np.concatenate(ss))
 status=np.stack(all_status,1);supported=(status==1).all(1)
 pairs={(int(x),int(y)):i for i,(x,y) in enumerate(zip(a['source'],a['target']))}
 for i,(x,y) in enumerate(zip(a['source'],a['target'])):
  if i%4096==0:guard()
  j=pairs[int(y)^1,int(x)^1];assert supported[i]==supported[j],'REVERSE_EVIDENCE_MISMATCH'
 return status,supported

def shortest(a,source,guard=lambda:None):
 old=dict(a,weight=a['base_weight']);od,_=g.shortest(old,source,guard);allowed=np.isfinite(od)
 if 'save_R' in a:a['save_R'](source,np.flatnonzero(allowed))
 n=int(a['state_count']);src=a['source'];dst=a['target'];weight=a['weight'];ptr=a.get('indptr')
 if ptr is None:
  order=np.lexsort((dst,src));src=src[order];dst=dst[order];weight=weight[order];ptr=np.r_[0,np.cumsum(np.bincount(src,minlength=n))]
 dist=np.full(n,np.inf);prev=np.full(n,-1,np.int64);dist[source]=0.;queue=[(0.,int(source))];count=0
 while queue:
  dd,u=heapq.heappop(queue)
  if dd!=dist[u]:continue
  count+=1
  if count%256==0:guard()
  for k in range(ptr[u],ptr[u+1]):
   v=int(dst[k]);nd=dd+float(weight[k])
   if not allowed[v] or nd>64:continue
   if nd<dist[v]:dist[v]=nd;prev[v]=u;heapq.heappush(queue,(nd,v))
   elif nd==dist[v] and (prev[v]<0 or u<prev[v]):prev[v]=u
 assert not np.any(np.isfinite(dist)&~allowed)
 return dist,prev

def best_path(z,a,source,guard=lambda:None):
 dist,prev=shortest(a,source,guard);best=None;best_rank=None
 unknown_voxels=set(map(int,z['voxel'][z['has_unknown']]))
 for j,end in enumerate(np.flatnonzero(np.isfinite(dist))):
  if j%256==0:guard()
  path=[];cur=int(end)
  while cur>=0:
   path.append(cur)
   if cur==source:break
   cur=int(prev[cur])
  if path[-1]!=source:raise AssertionError('BROKEN_DIJKSTRA_PREDECESSOR')
  path=path[::-1];mm=np.asarray(path,np.int64)//2;vv=set(map(int,z['voxel'][mm]));count=len(vv&unknown_voxels);length=float(f.arc(z['position'][mm])[-1]);rank=(-count,-length,float(dist[end]),int(end))
  if best_rank is None or rank<best_rank:best_rank=rank;best=path
 return best,dict(source=int(source),endpoint=int(best[-1]),unknown_voxels=-best_rank[0],length=-best_rank[1],cost=best_rank[2],reachable_states=int(np.isfinite(dist).sum()),states=best)

def propose(z,a,seeds,guard=lambda:None):
 paths=[];receipts=[];seen=set()
 for index,seed in enumerate(seeds):
  guard();plus,rp=best_path(z,a,2*seed,guard);minus,rm=best_path(z,a,2*seed+1,guard)
  states=[s^1 for s in minus[::-1]]+plus[1:];reverse=[s^1 for s in states[::-1]];canonical=min(tuple(states),tuple(reverse));modes=np.array(canonical,np.int64)//2;vv=z['voxel'][modes];q=z['position'][modes];length=float(f.arc(q)[-1]);reason='eligible'
  if len(np.unique(vv))!=len(vv):reason='repeated_spatial_voxel'
  elif len(vv)<6:reason='fewer_than_six_voxels'
  elif length>128+f.EPS:reason='length_cap'
  elif canonical in seen:reason='duplicate_path'
  else:seen.add(canonical);paths.append(dict(seed_index=index,seed_mode=int(seed),states=list(canonical),modes=modes.tolist(),length=length,q=q))
  receipts.append(dict(seed_index=index,seed_mode=int(seed),positive=rp,negative=rm,reason=reason,length=length))
 return paths,receipts

