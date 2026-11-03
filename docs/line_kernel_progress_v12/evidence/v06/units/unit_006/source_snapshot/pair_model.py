"""Bounded recovery of frozen pair models; no kernel or leaf mutation."""
from runtime_io import *
from geometry_base import EPS,RAD,arc,sample,project,extended_s,union_intervals,contact_bounded,clean
from port_paths import parallel
from adapter import local_validator
from types import SimpleNamespace
from collections import Counter,defaultdict
from dataclasses import dataclass

def fit_engine(path,d):
    from scipy.linalg import solve_banded
    tree=ast.parse(Path(path).read_text());allowed={'__init__','support','branch','validate','fit','proposal'};nodes=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef):nodes.append(node)
        elif isinstance(node,ast.ClassDef) and node.name=='Carrier':nodes.append(node)
        elif isinstance(node,ast.ClassDef) and node.name=='Engine':
            node.body=[x for x in node.body if isinstance(x,ast.FunctionDef) and x.name in allowed];nodes.append(node)
    ns=dict(np=np,RAD=RAD,EPS=EPS,dataclass=dataclass,Counter=Counter,defaultdict=defaultdict,solve_banded=solve_banded,__name__='pair_model')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
    return ns['Engine'](d['asset'],d['representatives'],d['tangents'],d['p'])

def fit_pair(engine,d,a,b,record_id,expected,guard=lambda:None):
    assert a<b;guard();aa=d['leaves'][a];bb=d['leaves'][b]
    template,op,host,donor=engine.proposal(aa,bb,False)
    rec=dict(model_key=[1,a,b],seed_pair=[a,b],input_versions=[aa.version,bb.version],record_id=record_id,anchor=host.cid,status='REPRODUCTION_MISMATCH',fit_calls=0)
    if template is None or op!='overlap':return dict(rec,reason='PROPOSAL_MISMATCH',operation=op)
    fit,why,met=engine.fit(np.r_[aa.rows,bb.rows],np.r_[aa.reps,bb.reps],template);guard();rec.update(fit_calls=1,fit_reason=why,metrics=met)
    if fit is None:return dict(rec,reason='FIT_FAILED')
    cost=met['residual_max']+met['tangent_max']/30
    rec.update(q=fit[0].tolist(),kind=fit[1],cost=float(cost))
    mismatch={k:dict(expected=float(v),actual=met.get(k)) for k,v in (expected or {}).items() if k!='cost' and (k not in met or not np.isfinite(met[k]) or abs(met[k]-v)>1e-10)}
    if expected and 'cost' in expected and abs(cost-expected['cost'])>1e-10:mismatch['cost']=dict(expected=expected['cost'],actual=cost)
    if mismatch:return dict(rec,reason='METRIC_MISMATCH',mismatches=mismatch)
    return dict(rec,status='RECOVERED')

def model_compatibility(d,donor,q,guard=lambda:None):
    guard();a=SimpleNamespace(q=q,valid=True);b=d['leaves'][donor]
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

def map_support(leaf,q):
    ss=arc(leaf.q);tt=leaf.intervals.reshape(-1)
    points=np.stack([np.interp(tt,ss,leaf.q[:,k]) for k in range(3)],1)
    return project(points,q)[0].reshape(-1,2)

def model_group_guard(d,q,ids,guard=lambda:None):
    guard();cs=[d['leaves'][i] for i in ids];a=SimpleNamespace(q=q)
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
    mapped=[map_support(cc,a.q) for cc in cs];iv,support,run,gap,total=union_intervals([x for z in mapped for x in z]);extent=arc(q)[-1]
    if gap>1.5+EPS:return False,'unsupported_gap',{}
    summed=sum(union_intervals(z)[1] for z in mapped)
    return True,'ok',dict(supported_intervals=iv.tolist(),supported_length_p=support,longest_continuous_run_p=run,max_gap_p=gap,total_gap_p=total,carrier_length_p=float(extent),coverage=support/max(extent,EPS),sum_leaf_observed_support_p=summed,duplicate_observed_support_p=max(0.,summed-support),anchor_outward_support_p=0.,kernels=sum(len(cc.rows) for cc in cs),seedlets=len(reps),bbox_p=[q.min(0).tolist(),q.max(0).tolist()],extent_p=(q.max(0)-q.min(0)).tolist(),unsupported_connectors_p=[],pooling_not_extension=True)


def build_extra_bank(d,ctx,models,guard=lambda:None):
    local=local_validator(d,d['p']);neighbors=defaultdict(set);bank=[];records=[]
    for e in d['overlaps']:
        neighbors[e['a']].add(e['b']);neighbors[e['b']].add(e['a'])
    for model in sorted(models,key=lambda x:tuple(x['model_key'])):
        if model['status']!='RECOVERED':continue
        q=np.array(model['q']);anchor=model['anchor'];partner=next(i for i in model['seed_pair'] if i!=anchor)
        if not local(d['leaves'][anchor])[0]:records.append(dict(model_key=model['model_key'],reason='anchor_local_invalid'));continue
        ok,why,hostmet=model_compatibility(d,anchor,q,guard)
        records.append(dict(model_key=model['model_key'],member=anchor,role='host',compatible=ok,reason=why,metrics=hostmet))
        if not ok:continue
        compatible=[]
        for donor in sorted(neighbors[anchor]):
            assert donor in ctx['carriers'],'COMPETITOR_OMITTED'
            if not local(d['leaves'][donor])[0]:ok,why,met=False,'donor_local_invalid',{}
            else:ok,why,met=model_compatibility(d,donor,q,guard)
            records.append(dict(model_key=model['model_key'],member=donor,compatible=ok,reason=why,metrics=met))
            if ok:compatible.append((met['cost'],donor,met))
        members=[anchor];costs=[];benefit=0.
        for cost,donor,met in sorted(compatible,key=lambda z:(z[0],z[1])):
            members.append(donor);costs.append(dict(carrier_id=donor,**met));benefit+=2-cost
            if partner not in members:continue
            ok,why,metrics=model_group_guard(d,q,members,guard)
            records.append(dict(model_key=model['model_key'],prefix_leaves=members.copy(),reason=why,benefit=float(benefit)))
            if ok and benefit>EPS:
                domain=project(d['leaves'][anchor].q[[0,-1]],q)[0];lo,hi=sorted(domain.tolist())
                outward=sum(max(0.,min(b,lo)-a)+max(0.,b-max(a,hi)) for a,b in metrics['supported_intervals'])
                metrics.update(anchor_outward_support_p=float(outward),model_outward_support_p=0.,outward_reference='old host endpoints projected to recovered model; not physical extension')
                bank.append(dict(hid=len(bank),anchor=anchor,model_key=model['model_key'],model_q=model['q'],model_kind=model['kind'],seed_pair=model['seed_pair'],leaves=sorted(members),prefix_order=members.copy(),benefit=float(benefit),costs=costs.copy(),host_metrics=hostmet,metrics=metrics))
    return bank,records

def model_key(h):return tuple(h.get('model_key',[0,h['anchor']]))

def select_greedy(bank):
    used=set();chosen=[]
    for h in sorted(bank,key=lambda z:(-z['benefit'],model_key(z),tuple(z['leaves']))):
        if not used.intersection(h['leaves']):chosen.append(h['hid']);used.update(h['leaves'])
    return sorted(chosen)

def select_joint(bank,seconds,guard=lambda:None):
    if seconds<=0:return [],dict(status='partial',reason='NO_SOLVER_BUDGET',seconds=0.,feasible_incumbent=False)
    if not bank:return [],dict(status='optimal',objective=0.,bound=0.,gap=0.,seconds=0.,empty=True)
    from scipy.optimize import milp,Bounds,LinearConstraint
    from scipy.sparse import csc_matrix
    start=time.monotonic();guard();hs=sorted(bank,key=lambda z:(model_key(z),tuple(z['leaves']),z['hid']));ids=sorted({i for h in hs for i in h['leaves']});idx={cid:k for k,cid in enumerate(ids)}
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
