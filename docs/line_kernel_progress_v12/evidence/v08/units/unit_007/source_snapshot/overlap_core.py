"""Deterministic overlap-only frontier transactions; original leaves never mutate."""
import copy
from geometry_base import *
from frontier_core import at,unit,history,initial,reverse_chain,choices
from observation_core import port_evidence
from port_paths import Leaf,parallel

def slice_q(q,a,b):
 ss=arc(q)
 return clean(np.vstack([at(q,a),q[(ss>a)&(ss<b)],at(q,b)]))
def tangent_at(q,ss):
 aa=arc(q);j=np.clip(np.searchsorted(aa,ss,side='left')-1,0,len(q)-2)
 v=q[j+1]-q[j];return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-30)
def register(a,b,s):
 la=float(arc(a)[-1]);lb=float(arc(b)[-1]);w=min(2.,la,float(s))
 meta=dict(status='no_overlap_or_tail',s=float(s),w=w,source_length_p=la,donor_length_p=lb)
 if w<=EPS or lb<=s+EPS:return None,meta
 aa=arc(a);bb=arc(b)
 uu=np.unique(np.r_[0.,w,aa[(aa>la-w)&(aa<la)]-(la-w),bb[(bb>s-w)&(bb<s)]-(s-w),np.linspace(0,w,int(np.ceil(w))+1)])
 x=np.array([at(a,la-w+u) for u in uu]);y=np.array([at(b,s-w+u) for u in uu]);dist=np.linalg.norm(x-y,axis=1)
 angle=np.degrees(np.arccos(np.clip(np.sum(tangent_at(a,la-w+uu)*tangent_at(b,s-w+uu),axis=1),-1,1)))
 meta.update(u_p=uu.tolist(),distances_p=dist.tolist(),angles_deg=angle.tolist())
 if dist.max()>1+EPS:meta['status']='overlap_distance';return None,meta
 if angle.max()>30+EPS:meta['status']='overlap_tangent';return None,meta
 q=clean(np.vstack([a[aa<la-w],(1-uu[:,None]/w)*x+(uu[:,None]/w)*y,b[bb>s]]))
 seam=arc(clean(np.vstack([a[aa<la-w],(1-uu[:,None]/w)*x+(uu[:,None]/w)*y])))[-1]
 meta.update(status='ok',seam_p=float(seam),overlap_replaced_once=True)
 return q,meta

def geometry_guard(q,guard=lambda:None):
 v=np.diff(q,axis=0);ll=np.linalg.norm(v,axis=1)
 if len(v)<1 or not np.isfinite(q).all() or np.any(ll<=EPS):return False,'degenerate_geometry'
 v=v/ll[:,None];turns=np.degrees(np.arccos(np.clip(np.sum(v[:-1]*v[1:],1),-1,1)));pos=np.cumsum(ll)[:-1]
 if turns.max(initial=0)>30+EPS:return False,'vertex_turn'
 if max((turns[(pos>=s-8-EPS)&(pos<=s+EPS)].sum() for s in pos),default=0)>60+EPS:return False,'window_turn'
 cq=[q[0]]
 for k in range(1,len(q)-1):
  a=q[k]-cq[-1];b=q[k+1]-q[k]
  if np.linalg.norm(np.cross(a,b))<=EPS*max(np.linalg.norm(a)*np.linalg.norm(b),1e-30) and a@b>0:continue
  cq.append(q[k])
 cq.append(q[-1])
 if contact_bounded(np.asarray(cq),guard):return False,'self_contact'
 return True,'ok'

def map_intervals(leaf,q):
 if not len(leaf.intervals):return [],dict(out_of_domain_endpoints=0,max_clamp_p=0.)
 pts=np.array([at(leaf.q,float(s)) for s in leaf.intervals.ravel()]);ext=extended_s(pts,q)[0];mapped=project(pts,q)[0].reshape(-1,2);L=arc(q)[-1]
 return mapped.tolist(),dict(out_of_domain_endpoints=int(np.sum((ext < -EPS)|(ext>L+EPS))),max_clamp_p=float(np.max(np.maximum(-ext,ext-L),initial=0.)))

def validate(d,chain,q,guard=lambda:None):
 guard();leaves=d['leaves'];rows=np.concatenate([leaves[i].rows for i,_ in chain]);reps=np.unique(np.concatenate([leaves[i].reps for i,_ in chain]));L=float(arc(q)[-1]);meta={}
 if len(rows)>8192:return False,'member_cap',meta
 if not all(leaves[i].valid for i,_ in chain):return False,'invalid_leaf',meta
 x=d['asset']['means'][rows]/d['p'];ss,dist,tan,_,_=project(x,q);angle=np.degrees(np.arccos(np.clip(abs(np.sum(d['tangents'][rows]*tan,1)),0,1)))
 meta['all_member_check']=dict(max_residual_p=float(dist.max(initial=0)),q95_residual_p=float(np.quantile(dist,.95)),max_tangent_deg=float(angle.max(initial=0)))
 if not np.isfinite(angle).all() or dist.max(initial=0)>1+EPS or np.quantile(dist,.95)>.5+EPS or angle.max(initial=0)>30+EPS:return False,'whole_member_residual_tangent',meta
 ex=extended_s(x,q)[0];meta['kernel_domain']=dict(left_excess_p=float(np.maximum(-ex,0).max(initial=0)),right_excess_p=float(np.maximum(ex-L,0).max(initial=0)))
 if np.any((ex < -EPS)|(ex>L+EPS)):return False,'kernel_outside_finite_domain',meta
 ivs=[];domains=[];maps=[]
 for cid,rev in chain:
  guard();leaf=leaves[cid];old=d.get('original_leaves',leaves)[cid];samp=sample(old.q[::-1] if rev else old.q,1.);ps=project(samp,q)[0]
  if np.any(np.diff(ps)<-EPS):return False,'leaf_nonmonotone',meta
  mapped,clamp=map_intervals(leaf,q);ivs.extend(mapped);maps.append(dict(carrier_id=cid,intervals_p=mapped,**clamp));ends=project(leaf.q[[0,-1]],q)[0]
  domains.append(dict(carrier_id=cid,start=float(min(ends)),end=float(max(ends)),reverse=bool(rev)))
 ok,why=geometry_guard(q,guard)
 if not ok:return False,why,meta
 for j,(cid,_) in enumerate(chain):
  for other,_ in chain[j+1:]:
   if parallel(leaves[cid],leaves[other]):return False,'parallel',meta
 if len(reps)>=9:
  rx=d['representatives']['x'][reps]/d['p'];rt=d['representatives']['t'][reps]
  centers=np.vstack([q]+[d.get('original_leaves',leaves)[cid].q for cid,_ in chain])
  for center in centers:
   guard();dx=rx-center;rr=np.linalg.norm(dx,axis=1);sel=np.flatnonzero((rr>EPS)&(rr<=4.))
   if len(sel)<9:continue
   dirs=rt[sel]*np.where(np.sum(rt[sel]*dx[sel],1)>=0,1.,-1.)[:,None];clusters=[]
   for z,axis in zip(sel,dirs):
    for ax,members in clusters:
     if ax@axis>=np.cos(20*RAD):members.append(z);break
    else:clusters.append((axis,[z]))
   if sum(len(zz)>=3 and np.ptp(rr[zz])>=2-EPS for _,zz in clusters)>=3:return False,'branch',meta
 iv,length,run,gap,total=union_intervals(ivs)
 if gap>1.5+EPS:return False,'unsupported_gap',meta
 meta.update(leaf_domains_p=domains,support_maps=maps,supported_intervals=iv.tolist(),supported_length_p=length,longest_continuous_run_p=run,max_gap_p=gap,total_gap_p=total,carrier_length_p=L,coverage=length/max(L,EPS),kernels=len(rows),seedlets=len(reps),unsupported_connectors_p=[],bbox_p=[q.min(0).tolist(),q.max(0).tolist()],extent_p=(q.max(0)-q.min(0)).tolist())
 return True,'ok',meta

def current_ports(d,chain,q,intervals):
 rows=np.concatenate([d['leaves'][i].rows for i,_ in chain]);reps=np.unique(np.concatenate([d['leaves'][i].reps for i,_ in chain]));leaf=Leaf(-1,0,rows,reps,q,True,True,np.asarray(intervals).reshape(-1,2));ss=project(d['asset']['means'][rows]/d['p'],q)[0]
 return [port_evidence(leaf,p,ss,d['tangents'][rows]) for p in (0,1)]

def initial_overlap(d,seeds,oracle):
 state=initial(seeds,d['next_version']);state['curves']={};state['metrics']={};state['ports']={}
 for sid in seeds:
  q=d['leaves'][sid].q;ok,why,met=oracle(state['chains'][sid]);state['curves'][sid]=q.tolist();state['metrics'][sid]=dict(seed_status='valid' if ok else why,**met);state['ports'][sid]=[d['ports'][(sid,p)] for p in (0,1)]
 return state

class SegmentIndex:
 def __init__(self,leaves):
  aa=[];bb=[];ids=[]
  for cid,leaf in sorted(leaves.items()):
   if not leaf.valid:continue
   aa.extend(leaf.q[:-1]);bb.extend(leaf.q[1:]);ids.extend([cid]*(len(leaf.q)-1))
  self.a=np.asarray(aa,float).reshape(-1,3);self.b=np.asarray(bb,float).reshape(-1,3);self.ids=np.asarray(ids,np.int64);self.v=self.b-self.a;self.ll=np.sum(self.v*self.v,1)
 def query(self,point):
  t=np.clip(np.sum((point-self.a)*self.v,1)/np.maximum(self.ll,1e-30),0,1);dist=np.linalg.norm(point-self.a-t[:,None]*self.v,axis=1)
  return sorted(set(self.ids[dist<=1.5+EPS].tolist()))

def outward_support(d,cid,reverse,b,s,q,seam,point,axis):
 leaf=d['leaves'][cid];L=float(arc(b)[-1]);ivs=leaf.intervals.copy()
 if reverse:ivs=L-ivs[:,::-1]
 clipped=[]
 for lo,hi in ivs:
  lo=max(float(lo),s)
  if hi<=lo:continue
  aa=arc(b)
  for j in range(len(b)-1):
   l=max(lo,float(aa[j]));h=min(float(hi),float(aa[j+1]))
   if h<=l:continue
   vl=float((at(b,l)-point)@axis)-EPS;vh=float((at(b,h)-point)@axis)-EPS
   if vl<0 and vh<0:continue
   if vl<0 or vh<0:
    cut=l+(h-l)*(-vl)/(vh-vl)
    if vl<0:l=cut
    else:h=cut
   pp=project(np.array([at(b,l),at(b,h)]),q)[0];a=max(seam,float(min(pp)));z=float(max(pp))
   if z>a:clipped.append([a,z])
 rows=leaf.rows;x=d['asset']['means'][rows]/d['p'];ps=project(x,b)[0];picked=rows[(ps>s+EPS)&(((x-point)@axis)>EPS)]
 iv,length,run,gap,total=union_intervals(clipped)
 return dict(outward_kernels=len(np.unique(picked)),outward_rows=picked.tolist(),outward_support_p=length,outward_intervals_p=iv.tolist(),outward_longest_run_p=run,outward_max_gap_p=gap)

def candidates(d,state,seed,side,index,guard=lambda:None,max_proposals=256,register_fn=None):
 q=np.asarray(state['curves'][seed]);a=q if side else q[::-1];outchain=state['chains'][seed] if side else reverse_chain(state['chains'][seed]);point=a[-1];neighbors=index.query(point);records=[]
 donors=[cid for cid in neighbors if cid not in state['used']];count=2*len(donors)
 for cid in donors:
  leaf=d['leaves'][cid];ps,ds,_,seg,_=project(point[None,:],leaf.q)
  for rev in (False,True):records.append(dict(donor=cid,donor_version=int(leaf.version),port=int(rev),reverse=rev,gap=float(ds[0]),projection_segment=int(seg[0]),projection_s_original_p=float(ps[0]),common=False,reason='not_evaluated',history=dict(eligible=False,reason='not_evaluated')))
 records.sort(key=lambda z:(z['gap'],z['donor'],z['port']))
 lib=dict(status='COMPLETE',records=records,queries=[dict(endpoint=point.tolist(),neighbors=[[cid,p] for cid in neighbors for p in (0,1)],complete_finite_segment_radius=True)],proposals_seen=count,max_proposals=max_proposals,complete_competition=True)
 if count>max_proposals:
  lib['status']='NOT_RUN_OVERSIZE'
  for z in records:z['reason']='whole_frontier_capacity'
  return lib
 if state['metrics'][seed]['seed_status']!='valid':
  for z in records:z['reason']='invalid_seed'
  return lib
 port=state['ports'][seed][side]
 if not port['known']:
  for z in records:z['reason']='observed_port_unknown'
  return lib
 for z in records:
  guard();cid=z['donor'];rev=z['reverse'];leaf=d['leaves'][cid];b=leaf.q[::-1] if rev else leaf.q;s=float(arc(b)[-1]-z['projection_s_original_p'] if rev else z['projection_s_original_p'])
  newq,reg=(register if register_fn is None else register_fn)(a,b,s);z['registration']=reg;z['attachment_s_oriented_p']=s;z['outward_side']=side
  if newq is None:z['reason']=reg['status'];continue
  z['proposed_outward_q_p']=newq.tolist()
  ch=outchain+[(cid,rev)];canonical=ch if side else reverse_chain(ch);canonical_q=newq if side else newq[::-1]
  ok,why,met=validate(d,canonical,canonical_q,guard);z['reason']=why;z['validation']=met
  if not ok:continue
  support=outward_support(d,cid,rev,b,s,newq,reg['seam_p'],point,np.asarray(port['axis']));z.update(support)
  if support['outward_kernels']<6 or support['outward_support_p']<2-EPS:z['reason']='outward_support';continue
  tail=slice_q(b,s,float(arc(b)[-1]));hist=history(a,tail,0.)
  met['seed_status']='valid';ports=current_ports(d,canonical,canonical_q,met['supported_intervals'])
  z.update(common=True,reason='common_candidate',chain=canonical,q=canonical_q.tolist(),metrics=met,new_ports=ports,history=hist)
 return lib

def commit(state,seed,z,save):
 trial=copy.deepcopy(state);trial['chains'][seed]=z['chain'];trial['curves'][seed]=z['q'];trial['metrics'][seed]=z['metrics'];trial['ports'][seed]=z['new_ports'];trial['used'].add(z['donor']);trial['versions'][seed]=trial['next_version'];trial['next_version']+=1;trial['accepted'][seed]+=1
 trial['events'].append(dict(seed=seed,version=trial['versions'][seed],donor=z['donor'],donor_version=z['donor_version'],gap=z['gap'],operation='finite_overlap_frontier',chain=z['chain'],registration=z['registration'],outward_support_p=z['outward_support_p'],outward_rows=z['outward_rows'],history=z['history'],support_maps=z['metrics']['support_maps']))
 save(trial)
 return trial
