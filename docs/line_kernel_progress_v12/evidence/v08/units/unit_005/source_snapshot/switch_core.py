"""Complete union of unchanged overlap proposals and bounded endpoint relays."""
import copy
import overlap_core as oc
from geometry_base import *
from frontier_core import endpoint_index,choices,reverse_chain,history,chain_q
from relay_core import half_intervals,RelayOverflow

def sort_key(z):
 return (z['gap'],z['total_gap'],len(z['relay']),tuple((int(i),int(r)) for i,r in z['relay']),z['relation'])

def remap_connectors(q,intervals,newq):
 if not intervals:return []
 pts=np.array([oc.at(q,float(s)) for pair in intervals for s in pair]);ss=project(pts,newq)[0].reshape(-1,2)
 return sorted([sorted(pair) for pair in ss.tolist()])

def assemble(d,a,relay):
 qs=[a];offset=float(arc(a)[-1]);connectors=[]
 for cid,rev in relay:
  q=d['leaves'][cid].q[::-1] if rev else d['leaves'][cid].q
  gap=float(np.linalg.norm(q[0]-qs[-1][-1]));connectors.append([offset,offset+gap]);offset+=gap+float(arc(q)[-1]);qs.append(q)
 return clean(np.vstack(qs)),connectors

def mapped_support(d,relay,point,axis,q):
 intervals=[];rows=[]
 for cid,_ in relay:
  leaf=d['leaves'][cid];iv=half_intervals(leaf,point,axis)
  if len(iv):
   pts=np.array([oc.at(leaf.q,float(s)) for s in iv.ravel()]);intervals.extend(project(pts,q)[0].reshape(-1,2).tolist())
  rows.extend(leaf.rows.tolist())
 rows=np.unique(np.asarray(rows,np.int64));picked=rows[((d['asset']['means'][rows]/d['p']-point)@axis)>EPS]
 iv,length,run,gap,total=union_intervals(intervals)
 return dict(outward_kernels=len(picked),outward_rows=picked.tolist(),outward_support_p=length,outward_intervals_p=iv.tolist(),outward_longest_run_p=run,outward_max_gap_p=gap)

def hop(point,source,target,entry):
 v=entry-point;gap=float(np.linalg.norm(v));meta=dict(gap=gap)
 if not source['known'] or not target['known']:return False,'observed_port_unknown',meta
 ta=np.asarray(source['axis']);tb=-np.asarray(target['axis']);dot=float(ta@tb)
 meta['observed_tangent_angle_deg']=float(np.degrees(np.arccos(np.clip(dot,-1,1))))
 if dot<np.cos(30*RAD)-EPS:return False,'observed_endpoint_tangent',meta
 if gap>EPS:
  dots=[float(v@ta/gap),float(v@tb/gap)];meta['observed_connector_angles_deg']=[float(np.degrees(np.arccos(np.clip(z,-1,1)))) for z in dots]
  if min(dots)<np.cos(35*RAD)-EPS:return False,'observed_connector',meta
 return True,'ok',meta

def candidates(d,state,seed,side,index,endpoints,guard=lambda:None,max_prefixes=256,max_donors=3):
 old=oc.candidates(d,state,seed,side,index,guard,max_prefixes);records=old['records'];queries=old['queries'];count=old['proposals_seen'];pending=[]
 for z in records:
  z.update(relation='overlap',relay=[(z['donor'],z['reverse'])],total_gap=z['gap'],donors=[z['donor']],donor_versions=[z['donor_version']])
  if z['common']:
   inherited=remap_connectors(np.asarray(state['curves'][seed]),state['metrics'][seed].get('unsupported_connectors_p',[]),np.asarray(z['q']))
   z['metrics']['unsupported_connectors_p']=inherited;z['connector_intervals_p']=inherited
 q=np.asarray(state['curves'][seed]);a=q if side else q[::-1];outchain=state['chains'][seed] if side else reverse_chain(state['chains'][seed]);point=a[-1];rootport=state['ports'][seed][side];tree,ids=endpoints
 def walk(prefix,first_gap,total_gap):
  nonlocal count
  guard();lastq=a if not prefix else (d['leaves'][prefix[-1][0]].q[::-1] if prefix[-1][1] else d['leaves'][prefix[-1][0]].q)
  source=rootport if not prefix else d['ports'][(prefix[-1][0],0 if prefix[-1][1] else 1)]
  endpoint=lastq[-1];keys=sorted(tree.query_ball_point(endpoint,1.5+EPS),key=lambda k:ids[k]);qid=len(queries)
  queries.append(dict(relation='endpoint_relay',query_id=qid,prefix=prefix,endpoint=endpoint.tolist(),neighbors=[list(ids[k]) for k in keys],complete_radius=True))
  frame=dict(prefix=prefix,remaining_links=[list(ids[k]) for k in keys]);pending.append(frame)
  for pos,k in enumerate(keys):
   guard();frame['remaining_links']=[list(ids[z]) for z in keys[pos+1:]];cid,port=ids[k];leaf=d['leaves'][cid];r=leaf.q if port==0 else leaf.q[::-1];gap=float(np.linalg.norm(r[0]-endpoint));relay=prefix+[(cid,bool(port))];fg=gap if not prefix else first_gap;tg=total_gap+gap
   z=dict(relation='endpoint_relay',query_id=qid,donor=cid,donor_version=int(leaf.version),port=port,reverse=bool(port),step_gap=gap,gap=fg,total_gap=tg,relay=relay,donors=[i for i,_ in relay],donor_versions=[int(d['leaves'][i].version) for i,_ in relay],common=False,reason='pending',history=dict(eligible=False,reason='not_evaluated'));records.append(z)
   if cid in state['used'] or cid in {i for i,_ in prefix}:z['reason']='used_or_seed_or_cycle';continue
   if not leaf.valid:z['reason']='invalid_leaf';continue
   ok,why,hm=hop(endpoint,source,d['ports'][(cid,port)],r[0]);z['observed_hop']=hm
   if not ok:z['reason']=why;continue
   count+=1;z['combined_prefix_number']=count
   if count>max_prefixes:z['reason']='combined_prefix_cap';raise RelayOverflow()
   nq,connectors=assemble(d,a,relay);ch=outchain+relay;canonical=ch if side else reverse_chain(ch);canonical_q=nq if side else nq[::-1]
   ok,why,met=oc.validate(d,canonical,canonical_q,guard);z.update(geometry_pass=bool(ok),geometry_reason=why,validation=met)
   support=mapped_support(d,relay,point,np.asarray(rootport['axis']),nq);z.update(support)
   if ok and support['outward_kernels']>=6 and support['outward_support_p']>=2-EPS:
    L=float(arc(nq)[-1]);canonical_connectors=connectors if side else [[L-b,L-a] for a,b in connectors[::-1]]
    canonical_connectors=sorted(canonical_connectors+remap_connectors(q,state['metrics'][seed].get('unsupported_connectors_p',[]),canonical_q))
    met.update(seed_status='valid',unsupported_connectors_p=canonical_connectors)
    z.update(common=True,reason='minimal_relay',chain=canonical,q=canonical_q.tolist(),metrics=met,new_ports=oc.current_ports(d,canonical,canonical_q,met['supported_intervals']),history=history(a,chain_q(d['leaves'],relay),fg),connector_intervals_p=canonical_connectors)
    continue
   z['reason']=why if not ok else 'relay_support'
   if len(relay)<max_donors:walk(relay,fg,tg)
  pending.pop()
 status=old['status']
 if status=='COMPLETE' and state['metrics'][seed]['seed_status']=='valid' and rootport['known']:
  try:walk([],None,0.)
  except RelayOverflow:status='NOT_RUN_OVERSIZE'
 if status!='COMPLETE':
  for z in records:
   if z['common']:z['would_be_common_before_overflow']=True
   z['common']=False
 unique={}
 for z in records:unique.setdefault((z['relation'],tuple((i,bool(r)) for i,r in z['relay'])),z)
 return dict(status=status,records=sorted(unique.values(),key=sort_key),queries=queries,combined_prefixes_seen=count,max_prefixes=max_prefixes,max_donors=max_donors,unexplored_frontiers=copy.deepcopy(pending),complete_competition=status=='COMPLETE')

def commit(state,seed,z,save):
 assert z['common'] and not(set(z['donors'])&state['used'])
 trial=copy.deepcopy(state);trial['chains'][seed]=z['chain'];trial['curves'][seed]=z['q'];trial['metrics'][seed]=z['metrics'];trial['ports'][seed]=z['new_ports'];trial['used'].update(z['donors']);trial['versions'][seed]=trial['next_version'];trial['next_version']+=1;trial['accepted'][seed]+=1
 trial['events'].append(dict(seed=seed,version=trial['versions'][seed],operation=z['relation'],donors=z['donors'],donor_versions=z['donor_versions'],relay=z['relay'],gap=z['gap'],total_gap=z['total_gap'],chain=z['chain'],history=z['history'],outward_support_p=z['outward_support_p'],outward_rows=z['outward_rows'],support_maps=z['metrics']['support_maps'],registration=z.get('registration'),unsupported_connectors_p=z['metrics']['unsupported_connectors_p']))
 save(trial)
 return trial

def hydrate(saved):
 state=copy.deepcopy(saved)
 for key in ['chains','versions','accepted','curves','metrics','ports']:state[key]={int(k):v for k,v in state[key].items()}
 state['chains']={k:[(int(i),bool(r)) for i,r in v] for k,v in state['chains'].items()};state['used']=set(state['used']);state['stopped']={tuple(z) for z in state['stopped']}
 return state
def reopen(saved):
 state=copy.deepcopy(saved);state['prior_accepts']=copy.deepcopy(state['accepted']);state['initial_event_count']=len(state['events']);state['accepted']={sid:0 for sid in state['chains']};state['attempts']=0;state['stopped']=set()
 return state
