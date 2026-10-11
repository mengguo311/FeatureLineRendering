import numpy as np
import core

def summarize_votes(votes):
 support=(votes==1).sum(1);counter=(votes<0).sum(1);weight=np.where(counter>0,.4,np.where(support>=2,1.,.7));return support,counter,weight

def density_opacity(opacity,nviews):
 return np.asarray(opacity).copy() if nviews==3 else -np.expm1(np.log1p(-np.asarray(opacity))*3/nviews)

def pair_votes(source,target,maps,c,chunk=65536):
 n=len(source['means']);out=np.empty(n,np.int8);nt=len(target['means']);h,w=maps['z'].shape
 for start in range(0,n,chunk):
  stop=min(n,start+chunk);pts=source['means'][start:stop];uv,z=core.project(pts,c);inside=np.isfinite(uv).all(1)&(z>0)&(uv[:,0]>=0)&(uv[:,0]<=w-1)&(uv[:,1]>=0)&(uv[:,1]<=h-1)
  xy=np.rint(np.nan_to_num(uv,nan=0,posinf=0,neginf=0)).astype(np.int64);x=np.clip(xy[:,0],0,w-1);y=np.clip(xy[:,1],0,h-1);near=maps['nearest_sample'][y,x];idx=np.clip(near,0,max(nt-1,0));d=maps['z'][y,x];tol=np.maximum(.005*d,2*d/np.sqrt(c['fx']*c['fy']))
  if nt:
   nxy=target['uv'][idx];nz=maps['z'][nxy[:,1],nxy[:,0]];tp=nz/np.sqrt(c['fx']*c['fy'])
   comp=(near>=0)&(np.linalg.norm(uv-nxy,axis=1)<=1.5)&target['fit_valid'][idx]&(np.linalg.norm(pts-target['means'][idx],axis=1)<=2.5*np.minimum(source['pixel'][start:stop],tp))&(abs(np.sum(source['tangent'][start:stop]*target['tangent'][idx],axis=1))>=np.sqrt(.5))&(abs(z-nz)<=tol)
  else:comp=np.zeros(stop-start,bool)
  out[start:stop]=core.visibility_class(z,d,maps['alpha'][y,x],inside,comp,tol)
 return out

def assemble_asset(s,votes):
 support,counter,weight=summarize_votes(votes);eligible=s['fit_valid']&(support>=2)&(counter==0);ids=np.flatnonzero(eligible)
 groups=core.group_samples(s['means'][ids],s['source_view'][ids],s['pixel'][ids],s['tangent'][ids],s['darkness'][ids]);n=len(s['means']);mapping=np.full(n,-1,np.int32);means=[];anchors=[];counts=[];opacity=[];viewvotes=[]
 for gid,g in enumerate(groups):
  members=ids[g];anchor=members[0];mapping[members]=gid;means.append(np.average(s['means'][members],weights=s['darkness'][members],axis=0));anchors.append(anchor);counts.append(len(members));opacity.append(min(.95,float(s['darkness'][members].max())));viewvotes.append(np.any(votes[members]==1,axis=0).sum())
 anchors=np.array(anchors,np.int32);other=np.flatnonzero(mapping<0);mapping[other]=np.arange(len(other))+len(groups);src=np.r_[anchors,other].astype(np.int32)
 asset={'means':np.concatenate([np.array(means).reshape(-1,3),s['means'][other]]),'covariance':core.ink_covariance(s['tangent'][src],np.zeros_like(s['tangent'][src]),s['pixel'][src],False),'opacity':np.r_[np.array(opacity),np.minimum(.95,s['darkness'][other])*weight[other]],'view_votes':np.r_[viewvotes,support[other]].astype(np.uint8),'source_count':np.r_[counts,np.ones(len(other))].astype(np.uint16),'source_anchor':src,'colors':np.zeros((len(src),3),np.float32)}
 prov={'source_to_asset':mapping,'source_weight':weight,'source_support_count':support.astype(np.uint8),'source_counter_count':counter.astype(np.uint8),'merge_eligible':eligible}
 assert np.all(mapping>=0) and np.unique(mapping).size==len(src)
 return asset,prov
