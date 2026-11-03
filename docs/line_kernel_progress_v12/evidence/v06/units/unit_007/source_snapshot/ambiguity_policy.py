"""Frozen unit003: complete endpoint-only components and counterfactual abstention."""
from runtime_io import *
from port_paths import DSU,greedy,joint,check_selection
from collections import defaultdict

def validate_successful_records(d):
    z=d['candidates'];names={str(k):i for i,k in enumerate(z['metric_names'])}
    assert {'residual_max','residual_q95','tangent_max'}<=names.keys()
    good=np.isin(z['reason'],['accepted','round_conflict','ambiguous'])
    assert np.all(np.isin(z['operation'][good],['endpoint','overlap'])),'UNMODELED_SUCCESSFUL_OPERATION'
    metrics=z['metrics'][good];cost=z['cost'][good]
    assert np.isfinite(metrics).all() and np.isfinite(cost).all(),'NONFINITE_SUCCESSFUL_METRICS'
    expected=metrics[:,names['residual_max']]+metrics[:,names['tangent_max']]/30
    assert np.all(abs(cost-expected)<=1e-12),'SUCCESSFUL_COST_BINDING'
    assert np.all(metrics[:,names['residual_max']]<=1+1e-8) and np.all(metrics[:,names['residual_q95']]<=.5+1e-8) and np.all(metrics[:,names['tangent_max']]<=30+1e-8),'INVALID_SUCCESSFUL_GUARD'
    for cid in set(z['a'][good].tolist()+z['b'][good].tolist()):assert d['leaves'][int(cid)].valid,'INVALID_SUCCESSFUL_LEAF'
    return dict(candidate_records=len(z['a']),successful_overlap=int(np.sum(good&(z['operation']=='overlap'))))

def select_ambiguity(c,d):
    uf=DSU();incident=defaultdict(list)
    for e in d['all_endpoint']:uf.union(e.a,e.b)
    groups=defaultdict(list)
    for cid in uf.p:groups[uf.find(cid)].append(cid)
    successful={'accepted','round_conflict','ambiguous'};z=d['candidates'];overlap=set()
    for k,(a,b) in enumerate(d['pairs']):
        incident[a].append(k);incident[b].append(k)
        if z['operation'][k]=='overlap' and z['reason'][k] in successful:overlap.update((a,b))
    contexts=[];excluded=[];blocked=0;pure=0;pure_edges=0;pure_masked=0
    for ids in sorted((sorted(v) for v in groups.values()),key=lambda v:(-len(v),v[0])):
        core=set(ids);ee=[e for e in d['all_endpoint'] if e.a in core]
        assert all((e.a in core)==(e.b in core) for e in d['all_endpoint']),'FULL_ENDPOINT_BOUNDARY'
        masked=[e.eid for e in ee if (e.a,e.b) in d['ambiguous']]
        reason='overlap_competition_unmodeled' if core&overlap else ('no_masked_endpoint' if not masked else None)
        if core&overlap:blocked+=1
        else:pure+=1;pure_edges+=len(ee);pure_masked+=len(masked)
        if reason:
            excluded.append(dict(carriers=ids,reason=reason,successful_endpoint_edges=len(ee),masked_edge_ids=masked,overlap_incident_carriers=sorted(core&overlap)));continue
        records=sorted({k for cid in ids for k in incident[cid]});halo=set(ids)
        for k in records:halo.update(d['pairs'][k])
        contexts.append(dict(context_id=len(contexts),carriers=ids,evidence_carriers=sorted(halo),incident_record_ids=records,eligible_edge_ids=[e.eid for e in ee],masked_edge_ids=masked,status='READY' if len(ids)<=c.get('decision_carrier_cap',128) else 'NOT_RUN_OVERSIZE',visual_truth='UNKNOWN_NOT_LABELED'))
    coverage=[e for ctx in contexts for e in ctx['eligible_edge_ids']];assert len(coverage)==len(set(coverage))
    audit=dict(full_endpoint_components=len(groups),overlap_blocked_components=blocked,overlap_free_components=pure,overlap_free_edges=pure_edges,overlap_free_masked=pure_masked,selected_components=len(contexts),excluded=excluded)
    return contexts,audit

class IncompleteCertificate(Exception):pass

def certify_component(edges,oracle,previous,seconds,guard=lambda:None,max_rounds=32):
    start=time.monotonic();deadline=start+seconds
    rec=dict(status='fallback_partial',raw={},certificates=[],counterfactuals=[],policy='delta > .15*max(edge_benefit,1e-8)+1e-8',postfilter_guard_passed=False)
    def bounded():
        guard()
        if time.monotonic()>=deadline:raise TimeoutError('COMPONENT_CERTIFICATE_BUDGET')
    try:
        bounded();gx,gr=greedy(edges,oracle,bounded);rec['raw']['greedy']=dict(selected=gx,receipt=gr)
        # Preserve even nonoptimal solver receipts, including failed counterfactuals.
        def recorded_solve(es,slot):
            bounded();x,r=joint(es,oracle,max(0.,deadline-time.monotonic()),bounded,max_rounds)
            slot.update(selected=x,receipt=r)
            if r['status'] not in ('optimal','no_edges'):raise IncompleteCertificate('SOLVER_'+r['status'])
            ok,why,_,_=check_selection(es,x,oracle)
            if not ok:raise IncompleteCertificate('UNCHECKED_OPTIMUM '+why)
            return x,r
        rec['raw']['joint']={};jx,jr=recorded_solve(edges,rec['raw']['joint']);fstar=float(jr['benefit']);rec['F_star']=fstar
        byid={e.eid:e for e in edges};certified=set()
        for e in sorted(edges,key=lambda x:x.key):
            bounded()
            if e.eid not in jx:
                rec['certificates'].append(dict(edge=e.eid,certified=False,delta=0.,reason='OPTIMAL_COUNTEREXAMPLE_ALREADY_OMITS_EDGE'));continue
            cf=dict(forbidden_edge=e.eid);rec['counterfactuals'].append(cf)
            cx,cr=recorded_solve([x for x in edges if x.eid!=e.eid],cf)
            delta=fstar-float(cr['benefit']);threshold=.15*max(e.benefit,1e-8)+1e-8
            assert delta>=-1e-7,'COUNTERFACTUAL_EXCEEDS_PROVEN_OPTIMUM'
            cert=bool(e.benefit>0 and delta>threshold)
            rec['certificates'].append(dict(edge=e.eid,certified=cert,delta=delta,threshold=threshold,benefit=e.benefit,F_without_e=float(cr['benefit']),reason='GLOBAL_EXCHANGE_CERTIFIED' if cert else 'GLOBAL_NEAR_ALTERNATIVE'))
            if cert:certified.add(e.eid)
        out={a:sorted(set(x)&certified) for a,x in [('greedy',gx),('joint',jx)]}
        for arm,x in out.items():
            bounded();ok,why,_,_=check_selection(edges,x,oracle)
            if not ok:raise IncompleteCertificate('POSTFILTER_PATH_'+arm+'_'+why)
        rec.update(status='certified_complete',postfilter_guard_passed=True,certified_edges=sorted(certified),selected=out)
    except (TimeoutError,IncompleteCertificate) as exc:
        out={a:list(previous[a]) for a in ('greedy','joint')};rec.update(status='fallback_partial',reason=str(exc),selected=out)
    rec['seconds']=time.monotonic()-start
    return out,rec
