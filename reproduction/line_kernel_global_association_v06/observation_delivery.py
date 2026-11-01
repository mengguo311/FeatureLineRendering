"""Unchanged native-kernel display plus fixed, changed and damaged comparisons."""
from runtime_io import *

def diagnostics(c,d,saved,contexts):
    prior=json.loads(Path(c['prior_diagnostics']).read_text()) if c.get('prior_diagnostics') else dict(cases=[],missing=[])
    cases=[dict(x,labels=x['labels']+['unit005_fixed_reference']) for x in prior['cases']];missing=[];chosen={};current={};old={}
    key=lambda g:(tuple(g.get('model_key',[0,g['anchor']])),tuple(x['carrier_id'] for x in g['leaves']))
    for arm,(_,gs) in saved.items():
        for g in gs:current[key(g)]=g
    for p in c.get('previous_arms',{}).values():
        for g in json.loads((Path(p)/'GROUPS.json').read_text())['groups']:old[key(g)]=g
    allgroups=dict(old);allgroups.update(current)
    rank=lambda k:(-allgroups[k]['supported_length_p'],allgroups[k]['edge_id'],k)
    def take(keys,n,label):
        ks=sorted(keys,key=rank)[:n]
        if not ks:missing.append(label)
        for k in ks:chosen.setdefault(k,[]).append(label)
    take(set(current)-set(old),3,'top3_changed_vs_unit005')
    damaged=set()
    for arm,(m,gs) in saved.items():
        armkeys={key(g) for g in gs}
        for g in json.loads((Path(c['previous_arms'][arm])/'GROUPS.json').read_text())['groups']:
            if key(g) not in armkeys:damaged.add(key(g))
    take(damaged,3,'top3_damaged_or_replaced_unit005_groups')
    for kind in ('line','polyline'):take([k for k,g in current.items() if k not in old and g.get('model_kind')==kind],1,'largest_new_'+kind+'_model_group')
    for k in sorted(chosen,key=rank):
        core=list(k[1]);cc=[x for x in contexts if set(core)&set(x['carriers'])]
        cases.append(dict(case_id='OBS_DOMAIN_'+str(allgroups[k]['edge_id'])+'_'+hashlib.sha256(repr(k).encode()).hexdigest()[:8],core_carriers=core,evidence_carriers=sorted({i for x in cc for i in x['evidence_carriers']}),incident_record_ids=sorted({i for x in cc for i in x['incident_record_ids']}),labels=chosen[k]))
    return dict(cases=cases,missing=missing,selection='unit005 fixed cases plus changed/damaged same-row union; complete evidence; support then ID',curved_label_not_visual_evidence=True)
