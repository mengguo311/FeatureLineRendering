"""Complete bounded outward relay prefixes; same frozen geometry/history policy."""
from frontier_core import *
from geometry_base import union_intervals

class RelayOverflow(Exception):pass

def half_intervals(leaf,point,tangent):
 """Exact positive-halfspace portions in this leaf's original arc coordinate."""
 q=leaf.q;aa=arc(q);out=[]
 for x,y in union_intervals(leaf.intervals)[0]:
  for i in range(len(q)-1):
   a=max(x,aa[i]);b=min(y,aa[i+1])
   if b<=a:continue
   va=float((at(q,a)-point)@tangent)-EPS;vb=float((at(q,b)-point)@tangent)-EPS
   if va>=0 and vb>=0:out.append([a,b])
   elif va<0 and vb<0:continue
   else:
    split=a+(b-a)*(-va)/(vb-va);out.append([split,b] if vb>va else [a,split])
 return union_intervals(out)[0]

def relay_support(d,relay,point,tangent):
 iv=[];offset=0.;previous=None;rows=[]
 for cid,rev in relay:
  leaf=d['leaves'][cid];q=leaf.q[::-1] if rev else leaf.q;L=arc(q)[-1]
  if previous is not None:offset+=float(np.linalg.norm(q[0]-previous))
  clipped=half_intervals(leaf,point,tangent)
  # Verify exact consistency with the inherited unit001 half-support measure.
  assert abs(union_intervals(clipped)[1]-half_support(leaf,point,tangent))<=1e-8
  if rev:clipped=L-clipped[:,::-1]
  iv.extend((clipped+offset).tolist());offset+=L;previous=q[-1];rows.extend(leaf.rows.tolist())
 rr=np.unique(np.asarray(rows,np.int64));outside=(d['asset']['means'][rr]/d['p']-point)@tangent>EPS
 ar,length,run,gap,total=union_intervals(iv)
 return dict(outward_kernels=int(np.sum(outside)),outward_support_p=float(length),outward_intervals_relay_p=ar.tolist(),relay_observed_longest_p=run,relay_observed_max_gap_p=gap)

def relay_sort_key(z):
 return (z['gap'],z['total_gap'],len(z['relay']),tuple((int(i),int(r)) for i,r in z['relay']))

def relay_candidates(d,state,seed,side,index,oracle,guard,max_prefixes=256,max_donors=3):
 leaves=d['leaves'];chain=state['chains'][seed];outchain=chain if side==1 else reverse_chain(chain);q=chain_q(leaves,outchain);point=q[-1];tangent=unit(q[-1]-q[-2]);tree,ids=index
 records=[];queries=[];prefixes=0;pending=[]
 def walk(prefix,first_gap,total_gap):
  nonlocal prefixes
  guard();lastq=q if not prefix else (leaves[prefix[-1][0]].q[::-1] if prefix[-1][1] else leaves[prefix[-1][0]].q)
  endpoint=lastq[-1];ta=unit(lastq[-1]-lastq[-2]);keys=sorted(tree.query_ball_point(endpoint,1.5+EPS),key=lambda k:ids[k]);qid=len(queries)
  queries.append(dict(query_id=qid,prefix=prefix,endpoint=endpoint.tolist(),neighbors=[list(ids[k]) for k in keys],complete_radius=True))
  frame=dict(prefix=prefix,remaining_links=[]);pending.append(frame)
  for position,k in enumerate(keys):
   guard();frame['remaining_links']=[list(ids[z]) for z in keys[position+1:]];cid,port=ids[k];leaf=leaves[cid];r=leaf.q if port==0 else leaf.q[::-1];gap=float(np.linalg.norm(r[0]-endpoint));newrelay=prefix+[(cid,bool(port))]
   fg=gap if not prefix else first_gap;tg=total_gap+gap
   z=dict(query_id=qid,donor=cid,donor_version=int(leaf.version),port=port,step_gap=gap,gap=fg,total_gap=tg,relay=newrelay,common=False,reason='pending',history=dict(eligible=False,reason='not_evaluated'));records.append(z)
   if cid in state['used'] or cid in {i for i,_ in prefix}:z['reason']='used_or_seed_or_cycle';continue
   if not leaf.valid:z['reason']='invalid_leaf';continue
   tb=unit(r[1]-r[0]);v=r[0]-endpoint
   if ta is None or tb is None:z['reason']='degenerate_tangent';continue
   if ta@tb<np.cos(30*RAD)-EPS:z['reason']='endpoint_tangent';continue
   if gap>EPS and min(v@ta/gap,v@tb/gap)<np.cos(35*RAD)-EPS:z['reason']='connector';continue
   prefixes+=1;z['prefix_number']=prefixes
   if prefixes>max_prefixes:
    z['reason']='prefix_cap';z['unexpanded_prefix']=newrelay;raise RelayOverflow()
   support=relay_support(d,newrelay,point,tangent);z.update(support)
   newout=outchain+newrelay;newchain=newout if side==1 else reverse_chain(newout)
   if sum(len(leaves[i].rows) for i,_ in newchain)>8192:ok,why,met=False,'member_cap',{}
   else:ok,why,met=oracle(newchain)
   z.update(geometry_pass=bool(ok),geometry_reason=why)
   adequate=support['outward_kernels']>=6 and support['outward_support_p']>=2-EPS
   if adequate and ok:
    relayq=chain_q(leaves,newrelay);z.update(common=True,reason='minimal_relay',chain=newchain,metrics=met,donors=[i for i,_ in newrelay],donor_versions=[int(leaves[i].version) for i,_ in newrelay],history=history(q,relayq,fg))
    continue
   z['reason']=why if not ok else 'relay_support'
   if len(newrelay)<max_donors:walk(newrelay,fg,tg)
  pending.pop()
 status='COMPLETE'
 try:walk([],None,0.)
 except RelayOverflow:
  status='NOT_RUN_OVERSIZE'
  for z in records:
   if z['common']:z['would_be_common_before_overflow']=True
   z['common']=False
 return dict(status=status,records=sorted(records,key=relay_sort_key),queries=queries,prefixes_seen=prefixes,max_prefixes=max_prefixes,max_donors=max_donors,unexplored_frontiers=copy.deepcopy(pending),complete_competition=status=='COMPLETE',minimal_relays=sum(z['common'] for z in records))

def commit_relay(state,seed,record,save):
 assert record['common'] and not (set(record['donors'])&state['used'])
 trial=copy.deepcopy(state);trial['chains'][seed]=record['chain'];trial['versions'][seed]=trial['next_version'];trial['next_version']+=1;trial['used'].update(record['donors']);trial['accepted'][seed]+=1
 trial['events'].append(dict(seed=seed,version=trial['versions'][seed],operation='atomic_fragment_relay',donors=record['donors'],donor_versions=record['donor_versions'],relay=record['relay'],gap=record['gap'],total_gap=record['total_gap'],chain=record['chain'],history=record['history'],outward_support_p=record['outward_support_p'],outward_kernels=record['outward_kernels'],metrics=record['metrics']))
 save(trial)
 return trial
