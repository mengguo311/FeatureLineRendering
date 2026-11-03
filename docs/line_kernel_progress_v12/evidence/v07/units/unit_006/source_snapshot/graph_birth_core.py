"""Unit005 observation graph proposals; graph states are not kernel labels."""
import heapq
import numpy as np
from scipy.spatial import cKDTree
import free_core as f
import merge_core as m
from overlap_core import compatibility

def build_modes(d,labels,guard=lambda:None):
 rows=np.flatnonzero(d['valid']);keys,inv=np.unique(np.floor(d['x'][rows]).astype(np.int64),axis=0,return_inverse=True)
 order=np.argsort(inv,kind='stable');starts=np.r_[0,np.flatnonzero(np.diff(inv[order]))+1,len(order)] if len(order) else np.array([0])
 members=[];reps=[];vox=[];pos=[];tt=[];unknown=[];offsets=[0];cos=np.cos(np.deg2rad(15))
 for vi,(begin,end) in enumerate(zip(starts[:-1],starts[1:])):
  if vi%256==0:guard()
  rr=rows[order[begin:end]];local=[];directions=[]
  for row in rr:
   t=d['t'][row];dot=np.abs(np.asarray(directions)@t) if directions else np.empty(0);j=int(np.argmax(dot)) if len(dot) else -1
   if j<0 or dot[j]<cos-f.EPS:
    t=t.copy();t*=1 if t[np.argmax(np.abs(t))]>=0 else -1;directions.append(t);local.append([int(row)])
   else:local[j].append(int(row))
  for r,t in zip(local,directions):
   members.extend(r);offsets.append(len(members));reps.append(r[0]);vox.append(int(inv[order[begin]]));pos.append(d['x'][r].mean(0));tt.append(t);unknown.append(bool(np.any(labels[r]<0)))
 return dict(position=np.asarray(pos,float).reshape(-1,3),tangent=np.asarray(tt,float).reshape(-1,3),voxel=np.asarray(vox,np.int64),voxel_keys=keys,representative=np.asarray(reps,np.int64),has_unknown=np.asarray(unknown,bool),offsets=np.asarray(offsets,np.int64),members=np.asarray(members,np.int64))

def build_graph(z,guard=lambda:None):
 guard();x=z['position'];t=z['tangent'];tree=cKDTree(x);src=[];dst=[];weights=[];lengths=[];total=0
 for begin in range(0,len(x),256):
  guard();neighbors=tree.query_ball_point(x[begin:begin+256],1.5+f.EPS,workers=1)
  for ii,near in enumerate(neighbors,begin):
   jj=np.asarray(sorted(j for j in near if j>ii and z['voxel'][j]!=z['voxel'][ii]),np.int64)
   if not len(jj):continue
   v=x[jj]-x[ii];dist=np.linalg.norm(v,axis=1);ok=dist>f.EPS;jj=jj[ok];v=v[ok];dist=dist[ok]
   if not len(jj):continue
   direction=v/dist[:,None];di=direction@t[ii];dj=np.sum(direction*t[jj],1);si=np.where(di>=0,1,-1);sj=np.where(dj>=0,1,-1)
   ai=np.degrees(np.arccos(np.clip(np.abs(di),0,1)));aj=np.degrees(np.arccos(np.clip(np.abs(dj),0,1)));at=np.degrees(np.arccos(np.clip((t[jj]@t[ii])*si*sj,-1,1)))
   ok=(ai<=35+f.EPS)&(aj<=35+f.EPS)&(at<=30+f.EPS);jj=jj[ok];dist=dist[ok];si=si[ok];sj=sj[ok];ai=ai[ok];aj=aj[ok];at=at[ok]
   if not len(jj):continue
   a=2*ii+(si<0).astype(int);b=2*jj+(sj<0).astype(int);w=dist*(1+(at/30)**2+.25*(ai*ai+aj*aj)/(35**2))
   src.extend([a,b^1]);dst.extend([b,a^1]);weights.extend([w,w]);lengths.extend([dist,dist]);total+=2*len(jj)
   if total>4000000:raise RuntimeError('GRAPH_EDGE_CAP_COMPLETE_GRAPH_NOT_AVAILABLE')
 if total:
  source=np.concatenate(src);target=np.concatenate(dst);weight=np.concatenate(weights);length=np.concatenate(lengths);order=np.lexsort((target,source));source=source[order];target=target[order];weight=weight[order];length=length[order]
 else:source=np.array([],np.int64);target=source.copy();weight=np.array([],float);length=weight.copy()
 n=2*len(x);indptr=np.r_[0,np.cumsum(np.bincount(source,minlength=n))]
 return dict(source=source,target=target,weight=weight,length=length,indptr=indptr,state_count=n)

def select_seeds(z,a,guard=lambda:None):
 n=len(z['position']);inc=np.bincount(a['target'],minlength=2*n);out=np.bincount(a['source'],minlength=2*n);both=((inc>0)&(out>0)).reshape(n,2).any(1);candidates=np.flatnonzero(z['has_unknown']&both)
 unknown=np.flatnonzero(z['has_unknown']);tree=cKDTree(z['position'][unknown]);covers=[];offsets=[0];heap=[]
 for start in range(0,len(candidates),256):
  guard();queries=tree.query_ball_point(z['position'][candidates[start:start+256]],8+f.EPS,workers=1)
  for mid,near in zip(candidates[start:start+256],queries):
   vv=np.unique(z['voxel'][unknown[np.asarray(near,np.int64)]]);j=len(covers);covers.append(vv);offsets.append(offsets[-1]+len(vv));heapq.heappush(heap,(-len(vv),int(z['representative'][mid]),int(mid),j))
 covered=np.zeros(int(z['voxel'].max())+1 if n else 0,bool);selected=[];receipts=[]
 while heap and len(selected)<64:
  guard();neg,rep,mid,j=heapq.heappop(heap);gain=int(np.sum(~covered[covers[j]]))
  if gain!= -neg:heapq.heappush(heap,(-gain,rep,mid,j));continue
  if gain==0:break
  covered[covers[j]]=True;selected.append(mid);receipts.append(dict(mode=mid,representative=rep,marginal_voxels=gain))
 bank=dict(candidate_modes=candidates,offsets=np.array(offsets,np.int64),voxel_ids=np.concatenate(covers) if covers else np.array([],np.int64))
 meta=dict(complete_coverage_bank=True,candidate_count=len(candidates),selected=receipts,unselected_seed_count=len(candidates)-len(selected),covered_unknown_voxels=int(covered.sum()),all_unknown_voxels=int(len(np.unique(z['voxel'][unknown]))),coverage_distance='within8p of any UNKNOWN-containing mode centroid, deduplicated by spatial voxel',capped=len(selected)==64 and bool(heap))
 return selected,bank,meta

def shortest(a,source,guard=lambda:None):
 n=int(a['state_count']);ptr=a.get('indptr');src=a['source'];dst=a['target'];weight=a['weight']
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
   if nd>64:continue
   if nd<dist[v]:dist[v]=nd;prev[v]=u;heapq.heappush(queue,(nd,v))
   elif nd==dist[v] and (prev[v]<0 or u<prev[v]):prev[v]=u
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

def trial(d,models,a,next_id,path_q,guard=lambda:None,progress=lambda phase,r:None):
 guard();before=m.energy(d,models,a,guard);r=dict(accepted=False,reason=None,before=before,after=None,model_id=next_id,next_id=next_id,models=None,assignment=None,raw=None,events=[],template=None,q=None,fit_rows=np.array([],np.int64),surviving_children=[])
 try:r['template']=f.resample(path_q)
 except ValueError as exc:r['reason']='template:'+str(exc);return r
 progress('template',r);tab=compatibility(d,{next_id:r['template']},{},guard)[next_id];rr=tab['rows'];r['fit_rows']=rr
 if len(rr)>8192:r['reason']='member_cap';return r
 if not len(rr):r['reason']='no_fit_members';return r
 try:r['q']=f.irls_update(d['x'][rr],r['template']);ok,why=f.geometry_ok(r['q'])
 except (ValueError,np.linalg.LinAlgError) as exc:r['reason']='fit:'+str(exc);return r
 progress('fitted',r)
 if not ok:r['reason']='geometry:'+why;return r
 mm={mid:q.copy() for mid,q in models.items()};mm[next_id]=r['q'].copy();aa=f.assign(d['x'],d['t'],d['valid'],mm,guard);r['raw']={k:v.copy() for k,v in aa.items()};progress('raw',r)
 mm,aa,events,nxt=f.validate_support(d['x'],d['half'],mm,aa,next_id+1,guard);r.update(models=mm,assignment=aa,events=events,next_id=nxt);progress('validated',r);r['after']=m.energy(d,mm,aa,guard)
 children=[mid for mid in mm if mid==next_id or any(e.get('operation')=='gap_split' and e.get('parent')==next_id and e.get('child')==mid for e in events)];r['surviving_children']=children
 if len(children)!=1:r['reason']='birth_support_not_one_piece';return r
 if len(mm)>704:r['reason']='active_model_cap';return r
 if before['total']-r['after']['total']<=f.EPS:r['reason']='no_energy_decrease';return r
 r['accepted']=True;r['reason']='energy_decrease';return r
