"""Unit002 relay enumeration with observed support ports at every hop."""
from relay_core import *
from observation_oracle import port_join

def observed_candidates(d,state,seed,side,index,oracle,guard,max_prefixes=256,max_donors=3,old_index=None):
 leaves=d['leaves'];chain=state['chains'][seed];outchain=chain if side==1 else reverse_chain(chain);q=chain_q(leaves,outchain);point=q[-1];rootleaf,rootreverse=outchain[-1];rootport=d['ports'][(rootleaf,0 if rootreverse else 1)];tangent=np.asarray(rootport['axis']) if rootport['known'] else None;tree,ids=index
 records=[];queries=[];prefixes=0;pending=[]
 def walk(prefix,first_gap,total_gap):
  nonlocal prefixes
  guard();lastq=q if not prefix else (leaves[prefix[-1][0]].q[::-1] if prefix[-1][1] else leaves[prefix[-1][0]].q)
  endpoint=lastq[-1];ta=unit(lastq[-1]-lastq[-2]);keys=sorted(tree.query_ball_point(endpoint,1.5+EPS),key=lambda k:ids[k]);qid=len(queries)
  last=outchain[-1] if not prefix else prefix[-1]
  shadow=[]
  if old_index is not None:
   ot,oi=old_index;oc=d['original_leaves'][last[0]];op=oc.q[0 if last[1] else -1]
   shadow=[list(oi[k]) for k in sorted(ot.query_ball_point(op,1.5+EPS),key=lambda k:oi[k])]
  queries.append(dict(query_id=qid,prefix=prefix,endpoint=endpoint.tolist(),neighbors=[list(ids[k]) for k in keys],original_endpoint_neighbors=shadow,complete_radius=True))
  frame=dict(prefix=prefix,remaining_links=[]);pending.append(frame)
  for position,k in enumerate(keys):
   guard();frame['remaining_links']=[list(ids[z]) for z in keys[position+1:]];cid,port=ids[k];leaf=leaves[cid];r=leaf.q if port==0 else leaf.q[::-1];gap=float(np.linalg.norm(r[0]-endpoint));newrelay=prefix+[(cid,bool(port))]
   fg=gap if not prefix else first_gap;tg=total_gap+gap
   z=dict(query_id=qid,donor=cid,donor_version=int(leaf.version),port=port,step_gap=gap,gap=fg,total_gap=tg,relay=newrelay,common=False,reason='pending',history=dict(eligible=False,reason='not_evaluated'));records.append(z)
   if cid in state['used'] or cid in {i for i,_ in prefix}:z['reason']='used_or_seed_or_cycle';continue
   if not leaf.valid:z['reason']='invalid_leaf';continue
   hop_ok,hop_reason,hop_metrics=port_join(leaves,d['ports'],last,(cid,bool(port)));z['observed_hop']=hop_metrics
   if not hop_ok:z['reason']=hop_reason;continue
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
