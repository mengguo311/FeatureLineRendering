"""Frozen finite-anchor observation hypotheses; no fitting or endpoint topology."""
from runtime_io import *
from geometry_base import EPS,RAD,arc,sample,project,extended_s,union_intervals,contact_bounded,clean
from port_paths import parallel,DSU
from adapter import local_validator
from collections import defaultdict

def successful_overlaps(d):
    z=d['candidates'];mi={str(k):i for i,k in enumerate(z['metric_names'])};result=[]
    for k,(a,b) in enumerate(d['pairs']):
        if z['operation'][k]!='overlap' or z['reason'][k] not in ('accepted','round_conflict','ambiguous'):continue
        met=z['metrics'][k];assert np.isfinite(met).all()
        assert d['leaves'][a].valid and d['leaves'][b].valid
        assert abs(float(z['cost'][k])-float(met[mi['residual_max']]+met[mi['tangent_max']]/30))<=1e-12
        assert met[mi['residual_max']]<=1+EPS and met[mi['residual_q95']]<=.5+EPS and met[mi['tangent_max']]<=30+EPS
        result.append(dict(record_id=k,a=int(a),b=int(b)))
    return result

def select_components(c,d):
    uf=DSU();incident=defaultdict(list)
    for e in d['overlaps']:uf.union(e['a'],e['b'])
    for k,(a,b) in enumerate(d['pairs']):incident[a].append(k);incident[b].append(k)
    groups=defaultdict(list)
    for cid in uf.p:groups[uf.find(cid)].append(cid)
    kinds={int(i):str(k) for i,k in zip(d['arrays']['carrier_id'],d['arrays']['kind'])}
    priority=set(c['overlap_priority_ids'])
    rank=lambda ids:(not bool(set(ids)&priority),not any(kinds[i]=='polyline' for i in ids),-max(union_intervals(d['leaves'][i].intervals)[1] for i in ids),min(ids))
    ordered=sorted([sorted(ids) for ids in groups.values()],key=rank);contexts=[]
    for ids in ordered[:c['max_components']]:
        core=set(ids);records=sorted({i for cid in ids for i in incident[cid]});halo=set(ids)
        for k in records:halo.update(d['pairs'][k])
        edges=[e['record_id'] for e in d['overlaps'] if e['a'] in core]
        assert all((e['a'] in core)==(e['b'] in core) for e in d['overlaps']),'OVERLAP_BOUNDARY'
        contexts.append(dict(context_id=len(contexts),carriers=ids,evidence_carriers=sorted(halo),incident_record_ids=records,overlap_record_ids=edges,status='READY' if len(ids)<=c['decision_carrier_cap'] else 'NOT_RUN_OVERSIZE'))
    return contexts,dict(all_components=len(ordered),selected=len(contexts),not_selected=len(ordered)-len(contexts),closure='all successful overlap including ambiguity; no competitor trimming',priority_without_overlap=sorted(priority-set(uf.p)))

def compatibility(d,anchor,donor,guard=lambda:None):
    guard();a=d['leaves'][anchor];b=d['leaves'][donor]
    if not a.valid or not b.valid:return False,'invalid_leaf',{}
    x=d['asset']['means'][b.rows]/d['p'];s,dist,tan,_,_=project(x,a.q)
    angle=np.degrees(np.arccos(np.clip(abs(np.sum(d['tangents'][b.rows]*tan,axis=1)),0,1)))
    met=dict(residual_max=float(dist.max(initial=0)),residual_q95=float(np.quantile(dist,.95)),tangent_max=float(angle.max(initial=0)))
    if not np.isfinite(list(met.values())).all():return False,'nonfinite',{}
    met['cost']=met['residual_max']+met['tangent_max']/30
    if met['residual_max']>1+EPS or met['residual_q95']>.5+EPS:return False,'residual',met
    if met['tangent_max']>30+EPS:return False,'tangent',met
    xx=sample(b.q);ss=project(xx,a.q)[0];ext=extended_s(xx,a.q)[0];length=arc(a.q)[-1]
    if ext.min()<-EPS or ext.max()>length+EPS:return False,'finite_domain',met
    dif=np.diff(ss)
    if not (np.all(dif>=-EPS) or np.all(dif<=EPS)):return False,'nonmonotone',met
    met['reverse']=bool(ss[-1]<ss[0]);return True,'ok',met

def mapped_intervals(leaf,anchor):
    if leaf.cid==anchor.cid:return leaf.intervals.copy()
    ss=arc(leaf.q);tt=leaf.intervals.reshape(-1)
    points=np.stack([np.interp(tt,ss,leaf.q[:,k]) for k in range(3)],1)
    return project(points,anchor.q)[0].reshape(-1,2)

def group_guard(d,anchor,ids,guard=lambda:None):
    guard();cs=[d['leaves'][i] for i in ids];a=d['leaves'][anchor]
    if any(not cc.valid for cc in cs):return False,'invalid_leaf',{}
    if sum(len(cc.rows) for cc in cs)>8192:return False,'kernel_cap',{}
    for i,cc in enumerate(cs):
        for other in cs[i+1:]:
            if parallel(cc,other):return False,'parallel',{}
    reps=np.concatenate([cc.reps for cc in cs]);assert len(set(reps.tolist()))==len(reps);xx=d['representatives']['x'][reps]/d['p'];tt=d['representatives']['t'][reps]
    if len(reps)>=9:
        for center in a.q:
            guard();dx=xx-center;rr=np.linalg.norm(dx,axis=1);sel=np.flatnonzero((rr>EPS)&(rr<=4.))
            if len(sel)<9:continue
            dirs=tt[sel]*np.where(np.sum(tt[sel]*dx[sel],axis=1)>=0,1.,-1.)[:,None];clusters=[]
            for z,v in zip(sel,dirs):
                for axis,members in clusters:
                    if np.dot(axis,v)>=np.cos(20*RAD):members.append(z);break
                else:clusters.append((v,[z]))
            if sum(len(zz)>=3 and np.ptp(rr[zz])>=2.-EPS for _,zz in clusters)>=3:return False,'branch',{}
    q=clean(a.q);v=np.diff(q,axis=0);length=np.linalg.norm(v,axis=1);v/=np.maximum(length[:,None],1e-30)
    turn=np.degrees(np.arccos(np.clip(np.sum(v[:-1]*v[1:],axis=1),-1,1)));pos=np.cumsum(length)[:-1]
    if turn.max(initial=0)>30+EPS:return False,'vertex_turn',{}
    if max((turn[(pos>=s-8-EPS)&(pos<=s+EPS)].sum() for s in pos),default=0)>60+EPS:return False,'window_turn',{}
    cq=[q[0]]
    for k in range(1,len(q)-1):
        va=q[k]-cq[-1];vb=q[k+1]-q[k]
        if np.linalg.norm(np.cross(va,vb))<=EPS*max(np.linalg.norm(va)*np.linalg.norm(vb),1e-30) and va@vb>0:continue
        cq.append(q[k])
    cq.append(q[-1])
    if contact_bounded(np.asarray(cq),guard):return False,'self_contact',{}
    mapped=[mapped_intervals(cc,a) for cc in cs];iv,support,run,gap,total=union_intervals([x for z in mapped for x in z]);extent=arc(q)[-1]
    if gap>1.5+EPS:return False,'unsupported_gap',{}
    summed=sum(union_intervals(z)[1] for z in mapped)
    return True,'ok',dict(supported_intervals=iv.tolist(),supported_length_p=support,longest_continuous_run_p=run,max_gap_p=gap,total_gap_p=total,carrier_length_p=float(extent),coverage=support/max(extent,EPS),sum_leaf_observed_support_p=summed,duplicate_observed_support_p=max(0.,summed-support),anchor_outward_support_p=0.,kernels=sum(len(cc.rows) for cc in cs),seedlets=len(reps),bbox_p=[q.min(0).tolist(),q.max(0).tolist()],extent_p=(q.max(0)-q.min(0)).tolist(),unsupported_connectors_p=[],pooling_not_extension=True)

def build_bank(d,ctx,guard=lambda:None):
    ids=set(ctx['carriers']);neighbors=defaultdict(list);records=[];bank=[];local=local_validator(d,d['p'])
    for e in d['overlaps']:
        if e['a'] in ids:
            assert e['b'] in ids
            neighbors[e['a']].append(e['b']);neighbors[e['b']].append(e['a'])
    valid={}
    for cid in sorted(ids):
        guard();valid[cid]=local(d['leaves'][cid])[0];guard()
    for anchor in sorted(ids):
        guard()
        if not valid[anchor]:records.append(dict(anchor=anchor,reason='anchor_local_invalid'));continue
        compatible=[]
        for donor in sorted(neighbors[anchor]):
            guard()
            if not valid[donor]:ok,why,met=False,'donor_local_invalid',{}
            else:ok,why,met=compatibility(d,anchor,donor,guard)
            records.append(dict(anchor=anchor,donor=donor,reason=why,compatible=ok,metrics=met))
            if ok:compatible.append((met['cost'],donor,met))
        compatible.sort(key=lambda z:(z[0],z[1]));members=[anchor];benefit=0.;costs=[]
        for cost,donor,met in compatible:
            members.append(donor);costs.append(dict(carrier_id=donor,**met));benefit+=2-cost
            # Original representative order follows deterministic anchor/donor prefix, not parent IDs.
            ok,why,metrics=group_guard(d,anchor,members,guard)
            records.append(dict(anchor=anchor,prefix_leaves=members.copy(),reason=why,benefit=float(benefit)))
            if ok and benefit>EPS:
                bank.append(dict(hid=len(bank),anchor=anchor,leaves=sorted(members),prefix_order=members.copy(),benefit=float(benefit),costs=costs.copy(),metrics=metrics))
    return bank,records

def select_greedy(bank):
    selected=[];used=set()
    for h in sorted(bank,key=lambda z:(-z['benefit'],z['anchor'],tuple(z['leaves']))):
        if not used.intersection(h['leaves']):selected.append(h['hid']);used.update(h['leaves'])
    return sorted(selected)

def select_joint(bank,seconds,guard=lambda:None):
    if seconds<=0:return [],dict(status='partial',reason='NO_SOLVER_BUDGET',seconds=0.,feasible_incumbent=False)
    if not bank:return [],dict(status='optimal',objective=0.,bound=0.,gap=0.,seconds=0.,empty=True)
    from scipy.optimize import milp,Bounds,LinearConstraint
    from scipy.sparse import csc_matrix
    start=time.monotonic();guard();hs=sorted(bank,key=lambda z:(z['anchor'],tuple(z['leaves']),z['hid']));ids=sorted({i for h in hs for i in h['leaves']});idx={cid:k for k,cid in enumerate(ids)}
    rr=[];cc=[]
    for j,h in enumerate(hs):
        for i in h['leaves']:rr.append(idx[i]);cc.append(j)
    mat=csc_matrix((np.ones(len(rr)),(rr,cc)),shape=(len(ids),len(hs)))
    result=milp(c=-np.array([h['benefit'] for h in hs]),integrality=np.ones(len(hs)),bounds=Bounds(0,1),constraints=LinearConstraint(mat,-np.inf,1),options={'time_limit':max(.001,seconds),'mip_rel_gap':0.,'threads':2,'parallel':False})
    guard();chosen=[]
    if result.x is not None:
        assert np.all(abs(result.x-np.rint(result.x))<1e-6) and np.all(mat@np.rint(result.x)<=1+EPS),'INVALID_INCUMBENT'
        chosen=sorted(h['hid'] for h,x in zip(hs,result.x) if x>.5)
    finite=lambda v:float(v) if v is not None and np.isfinite(v) else None
    return chosen,dict(status='optimal' if result.status==0 else 'partial',scipy_status=int(result.status),message=str(result.message),objective=sum(h['benefit'] for h in hs if h['hid'] in chosen),bound=finite(-result.mip_dual_bound) if getattr(result,'mip_dual_bound',None) is not None else None,gap=finite(getattr(result,'mip_gap',None)),seconds=time.monotonic()-start,feasible_incumbent=result.x is not None)
