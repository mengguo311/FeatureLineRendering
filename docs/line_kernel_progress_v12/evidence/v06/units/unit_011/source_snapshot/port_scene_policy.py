"""Ficus scene routing; unchanged complete endpoint decision closure."""
from scene_adapter import *
def select(c,d):
    seeds=[('fixed_carrier_'+str(cid),[cid]) for cid in c['priority_carrier_ids']]
    seeds += [('negative_'+str(a)+'_'+str(b),[a,b]) for a,b in c['negative_pairs']]
    priorities=set(c['priority_carrier_ids'])
    uf=DSU()
    for e in d['edges']:uf.union(e.a,e.b)
    groups=defaultdict(list)
    for cid in uf.p:groups[uf.find(cid)].append(cid)
    incident=defaultdict(list)
    for k,(a,b) in enumerate(d['pairs']):incident[a].append(k);incident[b].append(k)
    contexts=[];covered=[]
    for ids in sorted((sorted(v) for v in groups.values()),key=lambda v:(not bool(set(v)&priorities),v[0])):
        core=set(ids);ee=[e.eid for e in d['edges'] if e.a in core]
        assert all((e.a in core)==(e.b in core) for e in d['edges']),'ELIGIBLE_BOUNDARY'
        records=sorted({k for cid in ids for k in incident[cid]});halo=set(ids)
        for k in records:halo.update(d['pairs'][k])
        covered.extend(ee)
        contexts.append(dict(context_id=len(contexts),labels=[tag for tag,ss in seeds if core.intersection(ss)],carriers=ids,evidence_carriers=sorted(halo),incident_record_ids=records,eligible_edge_ids=ee,all_successful_endpoint_edges=sum(e.a in core and e.b in core for e in d['all_endpoint']),incident_record_count=len(records),status='READY' if len(ids)<=c.get('decision_carrier_cap',128) else 'NOT_RUN_OVERSIZE',visual_truth='UNKNOWN_NOT_LABELED',proposal_scope='Complete eligible decision component; one-hop full incident-record evidence; saved capped v05 proposals only'))
    assert sorted(covered)==sorted(e.eid for e in d['edges']),'ELIGIBLE_COVERAGE'
    assert len(covered)==len(set(covered)),'DUPLICATE_DECISION_EDGE'
    return seeds,contexts

def diagnostic_cases(c,d,saved,contexts,seeds):
    # Selection is symmetric in both arms; no images are consulted.
    bykey={};keys={};missing=[]
    def key(g):return tuple(sorted(int(z['carrier_id']) for z in g['leaves']))
    for arm,(_,groups) in saved.items():
        keys[arm]={key(g) for g in groups}
        for g in groups:bykey.setdefault(key(g),g)
    rank=lambda k:(-bykey[k]['supported_length_p'],bykey[k]['edge_id'],k)
    chosen={}
    def take(ks,n,label):
        ranked=sorted(ks,key=rank)[:n]
        if not ranked:missing.append(label)
        for k in ranked:chosen.setdefault(k,[]).append(label)
    for tag,ids in seeds[:len(c['seed_groups'])]:
        for arm in ('greedy','joint'):take([k for k in keys[arm] if set(k)&set(ids)],1,tag+'_'+arm)
    actual={arm:{} for arm in saved}
    for arm,(membership,groups) in saved.items():
        for g in groups:
            k=key(g);rr=np.concatenate([d['leaves'][cid].rows for cid in k]);rr=rr[membership['edge_id'][rr]==g['edge_id']]
            actual[arm][k]=tuple(sorted(rr.tolist()))
    different=set()
    for arm,other in [('greedy','joint'),('joint','greedy')]:
        other_members=set(actual[other].values())
        different.update(k for k,rows in actual[arm].items() if rows and rows not in other_members)
    take(different,3,'top3_actual_arm_member_differences')
    take(bykey,3,'top3_supported_paths')
    take([k for k in bykey if len(k)>=3],1,'largest_three_leaf_path')
    kinds={int(cid):str(kind) for cid,kind in zip(d['arrays']['carrier_id'],d['arrays']['kind'])}
    take([k for k in bykey if any(kinds[x]=='polyline' for x in k)],1,'largest_polyline_leaf_path')
    take([k for k in bykey if all(kinds[x]=='line' for x in k)],1,'largest_line_leaf_path')
    incident={}
    for i,(a,b) in enumerate(d['pairs']):incident.setdefault(a,[]).append(i);incident.setdefault(b,[]).append(i)
    component={cid:ctx for ctx in contexts for cid in ctx['carriers']}
    cases=[]
    for k in sorted(chosen,key=rank):
        core=list(k);comp_ids=sorted({component[x]['context_id'] for x in core})
        comps=[ctx for ctx in contexts if ctx['context_id'] in comp_ids]
        halo=sorted({cid for ctx in comps for cid in ctx['evidence_carriers']})
        cases.append(dict(case_id='PATH_'+str(bykey[k]['edge_id'])+'_'+hashlib.sha256(repr(k).encode()).hexdigest()[:8],labels=chosen[k],core_carriers=core,evidence_carriers=halo,component_ids=comp_ids,incident_record_ids=sorted({i for ctx in comps for i in ctx['incident_record_ids']})))
    for a,b in c['negative_pairs']:
        core=[a,b];records=sorted(set(incident.get(a,[])+incident.get(b,[])));halo=set(core)
        for i in records:halo.update(d['pairs'][i])
        # Include full decision components and their evidence if either seed participates.
        comps={component[x]['context_id']:component[x] for x in core if x in component}
        for ctx in comps.values():halo.update(ctx['evidence_carriers']);records=sorted(set(records)|set(ctx['incident_record_ids']))
        cases.append(dict(case_id='NEGATIVE_'+str(a)+'_'+str(b),labels=['saved_negative_unknown_truth'],core_carriers=core,evidence_carriers=sorted(halo),component_ids=sorted(comps),incident_record_ids=records))
    fixed=[('REFERENCE_'+'_'.join(map(str,ids)),ids) for ids in c.get('reference_leaf_sets',[])]
    fixed += [('FIXED_'+str(cid),[cid]) for cid in c.get('fixed_carrier_ids',[])]
    for name,core in fixed:
        if any(cid not in d['leaves'] for cid in core):missing.append(name);continue
        records=sorted({r for cid in core for r in incident.get(cid,[])})
        halo=set(core)
        for r in records:halo.update(d['pairs'][r])
        comps={component[x]['context_id']:component[x] for x in core if x in component}
        for ctx in comps.values():halo.update(ctx['evidence_carriers']);records=sorted(set(records)|set(ctx['incident_record_ids']))
        cases.append(dict(case_id=name,labels=['fixed_reference_not_claimed_new'],core_carriers=core,evidence_carriers=sorted(halo),component_ids=sorted(comps),incident_record_ids=records))
    return dict(cases=cases,missing=missing,selection='symmetric union over both arms; support descending then ID; not physical labels')
