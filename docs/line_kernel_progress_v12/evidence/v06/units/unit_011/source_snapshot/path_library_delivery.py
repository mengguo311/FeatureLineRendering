from runtime_io import *
from pair_delivery import membership_for,enrich as enrich_common
from scene_render import enrich_groups
from paired_delivery import evidence_rows

def export(out,c,d,selected,bank,receipts,scope,binding):
    out=Path(out);chosen=[h for h in bank if h['hid'] in selected]
    m,groups,lineage=membership_for(d,chosen,bank)
    m['path_hypothesis_id']=m.pop('overlap_hypothesis_id');m['path_aux_hypotheses']=m.pop('overlap_aux_hypotheses')
    byid={h['hid']:h for h in chosen}
    for g,ev in zip(groups,lineage):
        h=byid[g['hypothesis_id']];g['leaves']=[dict(carrier_id=cid,version=d['leaves'][cid].version,reverse=flip) for cid,flip in h['chain']]
        g.update(path_edge_record_ids=h['edge_ids'],representation=h['representation'],ordered_leaf_chain=h['chain'])
        ev.update(operation='finite_path_identity',topology_edges_added=len(h['edge_ids']),ordered_leaf_chain=h['chain'],edge_record_ids=h['edge_ids'],representation=h['representation'])
    nz(out/'MEMBERSHIP.npz',**m);nz(out/'CARRIERS.npz',**d['arrays']);js(out/'GROUPS.json',dict(scene=c['scene'],groups=groups,original_leaf_arrays=True))
    js(out/'LINEAGE.json',dict(predecessor=c['state'],events=lineage,source_parent_not_identity=True));js(out/'SOLVER.json',receipts);js(out/'SCOPE.json',scope)
    nz(out/'SELECTED_HYPOTHESES.npz',hypothesis_id=np.array(sorted(selected),np.int64))
    checkpoint(out,['MEMBERSHIP.npz','CARRIERS.npz','GROUPS.json','LINEAGE.json','SOLVER.json','SCOPE.json','SELECTED_HYPOTHESES.npz'],binding,'PATH_MAPPING_COMPLETE')
    verify_checkpoint(out,binding);cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
    for k in m:np.testing.assert_array_equal(m[k],cold[k])
    return cold,groups

def enrich(d,groups,guard):
    out=[]
    for g in groups:
        if g['representation']=='concat':out.extend(enrich_groups(d,[g],guard))
        else:
            z=enrich_common(d,[g],guard)[0];z['pooled_between_carriers']=False
            z['outward_support_note']='Remapped support proxy on auxiliary path q; not new observed geometry.'
            out.append(z)
    return out

def diagnostics(c,d,saved,contexts):
    groups={};members={};chosen={};missing=[]
    for arm,(m,gs) in saved.items():
        members[arm]={}
        for g in gs:
            key=tuple(sorted(x['carrier_id'] for x in g['leaves']));groups.setdefault(key,g)
            rr=evidence_rows(d,key);members[arm][key]=tuple(rr[m['edge_id'][rr]==g['edge_id']].tolist())
    rank=lambda k:(-groups[k]['supported_length_p'],groups[k]['edge_id'],k)
    def take(ks,n,label):
        keys=sorted(set(ks),key=rank)[:n]
        if not keys:missing.append(label)
        for k in keys:chosen.setdefault(k,[]).append(label)
    for label,pairs in [('representation',[('concat_greedy','common_greedy'),('concat_joint','common_joint')]),('selection',[('concat_greedy','concat_joint'),('common_greedy','common_joint')])]:
        diff=set()
        for a,b in pairs:
            for x,y in [(a,b),(b,a)]:diff.update(k for k,r in members[x].items() if r and r not in set(members[y].values()))
        take(diff,3,'top3_'+label+'_member_differences')
    take([k for k in groups if len(k)>=3],1,'largest_three_leaf_path')
    kinds={int(i):str(k) for i,k in zip(d['arrays']['carrier_id'],d['arrays']['kind'])}
    for kind in ['line','polyline']:
        take([k for k,g in groups.items() if g.get('model_kind')==kind or ('model_kind' not in g and (any(kinds[i]=='polyline' for i in k) if kind=='polyline' else all(kinds[i]=='line' for i in k)))],1,'largest_'+kind)
    cases=[]
    fixed=[(list(k),chosen[k],'PATH_'+str(min(k))) for k in sorted(chosen,key=rank)]
    fixed += [(x,['fixed_reference_not_truth'],'REFERENCE_'+'_'.join(map(str,x))) for x in c['reference_leaf_sets']]
    fixed += [(x,['saved_negative_unknown_truth'],'NEGATIVE_'+'_'.join(map(str,x))) for x in c['negative_pairs']]
    for core,labels,name in fixed:
        if any(cid not in d['leaves'] for cid in core):missing.append(name);continue
        comps=[ctx for ctx in contexts if set(core)&set(ctx['carriers'])];records={i for i,pair in enumerate(d['pairs']) if set(pair)&set(core)};halo=set(core)
        for i in records:halo.update(d['pairs'][i])
        for ctx in comps:halo.update(ctx['evidence_carriers']);records.update(ctx['incident_record_ids'])
        cases.append(dict(case_id=name,core_carriers=core,evidence_carriers=sorted(halo),incident_record_ids=sorted(records),labels=labels))
    return dict(cases=cases,missing=missing,selection='Actual assigned member-set differences; complete evidence; fixed views')
