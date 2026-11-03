"""Frozen four-seed local frontier prior; no fitting, pooling, or MILP calls."""
from geometry_base import *
from scipy.spatial import cKDTree
import copy

def unit(v):
 n=np.linalg.norm(v)
 return v/n if n>EPS else None

def at(q,s):
 a=arc(q);return np.array([np.interp(s,a,q[:,k]) for k in range(3)])

def history(q,r,gap):
 if len(q)<2 or len(r)<2 or arc(q)[-1]<2-EPS or arc(r)[-1]<2-EPS:return dict(eligible=False,reason='insufficient_history')
 L=arc(q)[-1];tm=unit(at(q,L-1)-at(q,L-2));t0=unit(at(q,L)-at(q,L-1));u0=unit(at(r,1)-at(r,0));u1=unit(at(r,2)-at(r,1))
 if any(t is None for t in (tm,t0,u0,u1)):return dict(eligible=False,reason='degenerate_history')
 k=t0-tm;pred=unit(t0+gap*k)
 if pred is None:return dict(eligible=False,reason='degenerate_prediction')
 angle=float(np.degrees(np.arccos(np.clip(pred@u0,-1,1))));delta=float(np.linalg.norm(u1-u0-k))
 ok=angle<=15+EPS and delta<=2*np.sin(7.5*RAD)+EPS
 return dict(eligible=bool(ok),reason='history_pass' if ok else 'history_reject',predicted_angle_deg=angle,curvature_difference=delta,t_minus=tm.tolist(),t0=t0.tolist(),k=k.tolist(),u0=u0.tolist(),u1=u1.tolist())

def half_support(leaf,point,tangent):
 q=leaf.q;aa=arc(q);length=0.
 for x,y in union_intervals(leaf.intervals)[0]:
  for i in range(len(q)-1):
   a=max(x,aa[i]);b=min(y,aa[i+1])
   if b<=a:continue
   va=float((at(q,a)-point)@tangent)-EPS;vb=float((at(q,b)-point)@tangent)-EPS
   if va>=0 and vb>=0:length+=b-a
   elif va<0 and vb<0:continue
   else:
    split=a+(b-a)*(-va)/(vb-va)
    length+=(b-split if vb>va else split-a)
 return float(length)

def endpoint_index(leaves):
 ids=[];points=[]
 for cid,c in sorted(leaves.items()):
  if len(c.q)<2 or not np.isfinite(c.q).all():continue
  for p in (0,1):ids.append((cid,p));points.append(c.q[0 if p==0 else -1])
 return cKDTree(np.asarray(points)),ids

def reverse_chain(chain):return [(i,not r) for i,r in chain[::-1]]
def chain_q(leaves,chain):return clean(np.vstack([leaves[i].q[::-1] if r else leaves[i].q for i,r in chain]))
def initial(seeds,version):return dict(chains={i:[(i,False)] for i in seeds},versions={i:version+k for k,i in enumerate(seeds)},next_version=version+len(seeds),accepted={i:0 for i in seeds},events=[],used=set(seeds),stopped=set(),attempts=0)

def candidates(d,state,seed,side,index,oracle,guard):
 leaves=d['leaves'];chain=state['chains'][seed];outchain=chain if side==1 else reverse_chain(chain);q=chain_q(leaves,outchain);point=q[-1];t=unit(q[-1]-q[-2]);tree,ids=index
 result=[]
 for k in sorted(tree.query_ball_point(point,1.5+EPS),key=lambda k:ids[k]):
  guard();cid,port=ids[k];leaf=leaves[cid];r=leaf.q if port==0 else leaf.q[::-1];gap=float(np.linalg.norm(r[0]-point))
  record=dict(donor=cid,donor_version=int(leaf.version),port=port,gap=gap,common=False,history=dict(eligible=False,reason='not_evaluated'))
  result.append(record)
  if cid in state['used']:record['reason']='used_or_seed';continue
  if not leaf.valid:record['reason']='invalid_leaf';continue
  if len(leaf.rows)<6:record['reason']='donor_kernel_count';continue
  rt=unit(r[1]-r[0]);v=r[0]-point
  if t is None or rt is None:record['reason']='degenerate_tangent';continue
  if t@rt<np.cos(30*RAD)-EPS:record['reason']='endpoint_tangent';continue
  if gap>EPS and min(v@t/gap,v@rt/gap)<np.cos(35*RAD)-EPS:record['reason']='connector';continue
  support=half_support(leaf,point,t);outrows=int(np.sum((d['asset']['means'][leaf.rows]/d['p']-point)@t>EPS))
  record.update(outward_support_p=support,outward_kernels=outrows)
  if support<2-EPS or outrows<6:record['reason']='outward_support';continue
  newout=outchain+[(cid,bool(port))];newchain=newout if side==1 else reverse_chain(newout)
  if sum(len(leaves[i].rows) for i,_ in newchain)>8192:record['reason']='member_cap';continue
  ok,why,met=oracle(newchain);record['reason']=why
  if not ok:continue
  record.update(common=True,chain=newchain,metrics=met,history=history(q,r,gap))
 return sorted(result,key=lambda z:(z['gap'],z['donor'],z['port']))

def choices(records):
 eligible=[i for i,x in enumerate(records) if x['common']]
 out=dict(BASE=None,HISTORY=None,reason='no_common_candidate')
 if not eligible:return out
 if len(eligible)>1 and records[eligible[1]]['gap']-records[eligible[0]]['gap']<=.15+EPS:return dict(BASE=None,HISTORY=None,reason='ambiguous_gap')
 out.update(BASE=eligible[0],HISTORY=next((i for i in eligible if records[i]['history']['eligible']),None),reason='selected')
 return out

def commit(state,seed,record,save):
 trial=copy.deepcopy(state);trial['chains'][seed]=record['chain'];trial['versions'][seed]=trial['next_version'];trial['next_version']+=1;trial['used'].add(record['donor']);trial['accepted'][seed]+=1
 trial['events'].append(dict(seed=seed,version=trial['versions'][seed],donor=record['donor'],donor_version=record['donor_version'],gap=record['gap'],chain=record['chain'],history=record['history'],metrics=record['metrics']))
 save(trial)
 return trial
