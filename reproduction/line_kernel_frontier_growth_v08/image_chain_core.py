"""Ordered real-image support; no image or asset reads at import."""
import json,heapq
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,sobel
import overlap_core as oc
import paired_history_core as ph
EPS=1e-8

def ordered_path(xy,s,edges,start,middle,end,guard=lambda:None):
 adj=[[] for _ in xy];middle=set(middle);end=set(end)
 for i,j,w in edges:adj[i].append((j,w))
 for neighbors in adj:neighbors.sort()
 dist={};prev={};queue=[]
 for node in sorted(start):
  state=(node,int(node in middle),(node,));dist[state]=0.;prev[state]=None;heapq.heappush(queue,(0.,state))
 target=None
 iterations=0
 while queue:
  iterations+=1
  if iterations%256==0:guard()
  cost,state=heapq.heappop(queue)
  if cost!=dist[state]:continue
  node,seen,tag=state
  if seen and node in end and tag==(-1,):target=state;break
  for nxt,w in adj[node]:
   nt=tag if tag==(-1,) else tuple(sorted(set(tag)|{nxt}))
   if len(nt)>=3:nt=(-1,)
   ns=(nxt,int(seen or nxt in middle),nt);nd=cost+w
   if nd<dist.get(ns,float('inf')) or (nd==dist.get(ns) and prev.get(ns) is not None and state<prev[ns]):
    dist[ns]=nd;prev[ns]=state;heapq.heappush(queue,(nd,ns))
 if target is None:return []
 path=[]
 while target is not None:path.append(target[0]);target=prev[target]
 return path[::-1]

def project_camera(x,cam):
 e=np.asarray(cam.get('extrinsic',cam.get('w2c')),float);q=np.asarray(x)@e[:3,:3].T+e[:3,3]
 z=q[:,2];den=np.where(z!=0,z,1.)
 return np.c_[cam['fx']*q[:,0]/den+cam['cx'],cam['fy']*q[:,1]/den+cam['cy']],z

def load_evidence(c,guard):
 guard('readiness');frames=json.loads(Path(c['image_calibration']).read_text());cams=json.loads(Path(c['cameras']).read_text())[c['scene']];out={};receipt=[]
 for view in c['views']:
  guard('readiness');cam=next(x for x in cams if x['view']==view);stem=Path(c['image_inputs'][view]).stem
  frame=next(x for x in frames['frames'] if Path(x['file_path']).stem==stem)
  gl=np.asarray(frame['transform_matrix'],float);np.testing.assert_array_equal(gl,np.asarray(cam['original_c2w_gl']))
  assert np.isfinite(gl).all() and gl.shape==(4,4),'CALIBRATION_MATRIX'
  cv=gl.copy();cv[:3,1:3]*=-1;extr=np.linalg.inv(cv)
  np.testing.assert_allclose(extr,np.asarray(cam.get('extrinsic',cam.get('w2c'))),rtol=0,atol=1e-8)
  a=np.asarray(Image.open(c['image_inputs'][view]).convert('RGBA'),float)/255.
  assert a.shape==(800,800,4),'IMAGE_SIZE';f=.5*800/np.tan(float(frames['camera_angle_x'])/2)
  np.testing.assert_allclose([cam['fx'],cam['fy'],cam['cx'],cam['cy']],[f,f,399.5,399.5],rtol=0,atol=1e-8)
  for key in ('width','height'):
   if key in cam:assert cam[key]==800
  rgb=a[:,:,:3]*a[:,:,3:]+1-a[:,:,3:];lum=rgb@np.array([.2126,.7152,.0722]);smooth=gaussian_filter(lum,1,mode='reflect')
  out[view]=dict(camera=cam,gx=sobel(smooth,axis=1,mode='reflect')/8,gy=sobel(smooth,axis=0,mode='reflect')/8)
  receipt.append(dict(view=view,image=c['image_inputs'][view],frame=frame['file_path'],size=[800,800],c2w_and_intrinsics_verified=True,OpenGL_conversion_verified=True))
 guard('readiness');return out,receipt

def view_chain(uv,depth,mid,gx,gy,guard=lambda:None):
 uv=np.asarray(uv,float);depth=np.asarray(depth);h,w=gx.shape
 result=dict(status='UNKNOWN',eligible=False,polyline_px=uv.tolist(),middle_index=int(mid),nodes=[],edges=[],path=[])
 if not np.isfinite(uv).all() or not np.isfinite(depth).all() or np.any(depth<=0):return dict(result,reason='nonpositive_or_nonfinite_projection')
 if np.any((uv[:,0]<0)|(uv[:,0]>w-1)|(uv[:,1]<0)|(uv[:,1]>h-1)):return dict(result,reason='out_of_frame')
 vec=np.diff(uv,axis=0);lens=np.linalg.norm(vec,axis=1)
 if np.any(lens<=EPS):return dict(result,reason='degenerate_projection')
 arc=np.r_[0.,np.cumsum(lens)];result['half_lengths_px']=[float(arc[mid]),float(arc[-1]-arc[mid])]
 if min(result['half_lengths_px'])<2:return dict(result,reason='insufficient_projected_resolution')
 lo=np.maximum(np.ceil(uv.min(0)-2).astype(int),0);hi=np.minimum(np.floor(uv.max(0)+2).astype(int),[w-1,h-1])
 yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];xy=np.c_[xx.ravel(),yy.ravel()];best=np.full(len(xy),np.inf);seg=np.zeros(len(xy),int);ss=np.zeros(len(xy))
 for j,(a,v,ll) in enumerate(zip(uv[:-1],vec,lens)):
  guard();t=np.clip((xy-a)@v/(ll*ll),0,1);ds=np.sum((xy-a-t[:,None]*v)**2,1);take=ds<best
  best[take]=ds[take];seg[take]=j;ss[take]=arc[j]+t[take]*ll
 grad=np.c_[gx[xy[:,1],xy[:,0]],gy[xy[:,1],xy[:,0]]];mag=np.linalg.norm(grad,axis=1);perp=np.c_[-grad[:,1],grad[:,0]]
 cos=np.abs(np.sum(perp*(vec[seg]/lens[seg,None]),1))/np.maximum(mag,1e-30)
 keep=(best<=4+EPS)&(mag>=.1)&(cos>=np.cos(np.pi/6)-EPS)
 xy=xy[keep];ss=ss[keep];seg=seg[keep];grad=grad[keep];lookup={tuple(v):i for i,v in enumerate(xy)};edges=[]
 for i,(x,y) in enumerate(xy):
  if i%256==0:guard()
  for dy in (-1,0,1):
   for dx in (-1,0,1):
    if dx==dy==0:continue
    j=lookup.get((x+dx,y+dy))
    if j is not None and ss[j]>=ss[i]-EPS:edges.append([i,j,float(np.hypot(dx,dy))])
 start=np.flatnonzero((np.linalg.norm(xy-uv[0],axis=1)<=2+EPS)&(ss<=1+EPS)).tolist()
 middle=np.flatnonzero(np.linalg.norm(xy-uv[mid],axis=1)<=2+EPS).tolist()
 end=np.flatnonzero((np.linalg.norm(xy-uv[-1],axis=1)<=2+EPS)&(ss>=arc[-1]-1-EPS)).tolist()
 path=ordered_path(xy,ss,edges,start,middle,end,guard)
 result.update(nodes=[dict(pixel=v.tolist(),gradient=g.tolist(),segment=int(j),arc_px=float(s)) for v,g,j,s in zip(xy,grad,seg,ss)],edges=edges,start=start,middle=middle,end=end,path=path)
 result.update(status='PASS' if path else 'ABSTAIN',eligible=bool(path),reason='ordered_chain' if path else 'no_ordered_chain',visibility_verified=False)
 return result

def candidate_evidence(d,state,sid,side,z,evidence,guard=lambda:None):
 q=np.asarray(z['q'],float);a=np.asarray(state['curves'][sid],float)
 if side==0:q=q[::-1];a=a[::-1]
 f=float(oc.project(a[-1:],q)[0][0]);ss=oc.arc(q);L=float(ss[-1])
 result=dict(eligible=False,status='UNKNOWN',frontier_s_p=f,length_p=L,views={})
 if f<2-EPS or L-f<2-EPS:return dict(result,reason='insufficient_finite_domain')
 lo=max(0.,f-2);hi=min(L,f+2);coords=np.unique(np.r_[lo,ss[(ss>lo)&(ss<hi)],f,hi]);clip=np.asarray([oc.at(q,s) for s in coords]);mid=int(np.flatnonzero(coords==f)[0])
 result['clip_q_p']=clip.tolist()
 for name,v in evidence.items():
  guard();uv,dep=project_camera(clip*d['p'],v['camera']);result['views'][name]=view_chain(uv,dep,mid,v['gx'],v['gy'],guard)
 ok=all(v['eligible'] for v in result['views'].values()) and len(result['views'])==2
 result.update(eligible=ok,status='PASS' if ok else 'ABSTAIN',reason='both_view_chains' if ok else 'missing_two_view_chain',visibility_verified=False)
 return result

def annotate(d,state,sid,side,lib,evidence,guard=lambda:None):
 for z in lib['records']:
  guard();z['image_chain']=candidate_evidence(d,state,sid,side,z,evidence,guard) if z['common'] else dict(eligible=False,status='NOT_COMMON_GEOMETRY')
 return lib

def choices(records):
 old=ph.choices(records);result=dict(BASE=old['BASE'],PAIRED=old['PAIRED_HISTORY'],IMAGE_CHAIN=None,reason=old['reason'])
 if old['BASE'] is not None:
  result['IMAGE_CHAIN']=next((i for i,z in enumerate(records) if z['common'] and z['image_chain']['eligible']),None)
 return result

def scientific(value):
 """Compare exact scientific receipts; exclude only nondeterministic wall time."""
 if isinstance(value,dict):return {k:scientific(v) for k,v in value.items() if k!='elapsed_seconds'}
 if isinstance(value,(list,tuple)):return [scientific(v) for v in value]
 return value
