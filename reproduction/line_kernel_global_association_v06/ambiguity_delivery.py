"""Unit003 complete-row delivery with explicit immutable unit002 inheritance."""
from runtime_io import *
from delivery import membership_for
from paired_delivery import evidence_rows
from copy import deepcopy

def group_key(g):return tuple((int(x['carrier_id']),bool(x['reverse'])) for x in g['leaves'])

def load_prior(c):
    result={}
    for arm,path in c['previous_arms'].items():
        out=Path(path);verify_checkpoint(out,c['previous_config_sha256'])
        m=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False));g=json.loads((out/'GROUPS.json').read_text())['groups'];lineage=json.loads((out/'LINEAGE.json').read_text())
        result[arm]=dict(membership=m,groups=g,lineage=lineage,selected=np.load(out/'SELECTED_LINKS.npz',allow_pickle=False)['record_index'].tolist(),path=str(out))
    return result

def merge_membership(d,selected,oracle,prior,affected_ids,version_start):
    m,groups,events=membership_for(d,selected,oracle)
    n=len(m['edge_id']);inside=np.zeros(n,bool)
    for cid in affected_ids:inside[d['leaves'][cid].rows]=True
    pm=prior['membership'];np.testing.assert_array_equal(pm['line_kernel_id'],m['line_kernel_id'])
    for k,v in pm.items():
        if v.ndim and len(v)==n:
            if k not in m:m[k]=v.copy()
            else:m[k][~inside]=v[~inside]
    oldgroups={group_key(g):g for g in prior['groups']};newgroups=[];new_events=[];version=int(version_start)
    for g in groups:
        ids={int(x['carrier_id']) for x in g['leaves']};rows=evidence_rows(d,ids)
        assert not (np.any(inside[rows]) and not np.all(inside[rows])),'PREVIOUS_COMPONENT_SPLIT_BOUNDARY'
        if not np.any(inside[rows]):
            assert group_key(g) in oldgroups,'OUTSIDE_GROUP_CHANGED';newgroups.append(deepcopy(oldgroups[group_key(g)]));continue
        g['version']=version;version+=1;newgroups.append(g)
        assigned=rows[m['edge_id'][rows]>=0];m['composite_version'][assigned]=g['version']
        new_events.append(dict(output_edge_id=g['edge_id'],output_version=g['version'],input_leaves=[[x['carrier_id'],x['version']] for x in g['leaves']],operation='counterfactual_certified_composite_identity',leaf_geometry_unchanged=True))
    for k,v in pm.items():
        if v.ndim and len(v)==n:np.testing.assert_array_equal(m[k][~inside],v[~inside],err_msg='OUTSIDE_MEMBERSHIP_'+k)
    old=d['membership']['edge_id'];assert not np.any((old>=0)&(m['edge_id']<0)),'M4_INCUMBENT_LOSS'
    for leaf in d['leaves'].values():
        if np.any(old[leaf.rows]>=0):assert len(np.unique(m['edge_id'][leaf.rows]))==1,'M4_GROUP_SPLIT'
    lineage=dict(predecessor_M4_reference=True,unit002_lineage_reference=prior['path']+'/LINEAGE.json',inherited_events=prior['lineage'],events=new_events,source_parent_not_identity=True)
    return m,newgroups,lineage,inside

def export_certified(out,c,d,selected,oracle,prior,affected_ids,version_start,receipts,scope,binding):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    m,gs,lineage,inside=merge_membership(d,selected,oracle,prior,affected_ids,version_start)
    nz(out/'MEMBERSHIP.npz',**m);nz(out/'CARRIERS.npz',**d['arrays']);nz(out/'SELECTED_LINKS.npz',record_index=np.asarray(sorted(selected),np.int64))
    js(out/'GROUPS.json',dict(scene='scan24',representation='ordered_finite_leaf_composite',groups=gs,untouched_groups_reference=prior['path']+'/GROUPS.json'))
    js(out/'LINEAGE.json',lineage);js(out/'SOLVER.json',receipts);js(out/'SCOPE.json',scope)
    previous=prior['membership']['edge_id'];ids=m['edge_id'];splits=[]
    for g in prior['groups']:
        rr=evidence_rows(d,[x['carrier_id'] for x in g['leaves']]);oldrows=rr[previous[rr]>=0]
        if len(oldrows) and len(np.unique(ids[oldrows]))>1:splits.append(g['edge_id'])
    comparison=dict(affected_rows=int(inside.sum()),assigned=int(np.sum(ids>=0)),unknown=int(np.sum(ids<0)),changed_rows_vs_unit002=int(np.sum(ids!=previous)),gained_assigned_vs_unit002=int(np.sum((previous<0)&(ids>=0))),lost_assigned_vs_unit002=int(np.sum((previous>=0)&(ids<0))),split_unit002_composite_ids=splits,gained_assigned_vs_M4=int(np.sum((d['membership']['edge_id']<0)&(ids>=0))),lost_assigned_vs_M4=int(np.sum((d['membership']['edge_id']>=0)&(ids<0))),outside_all_membership_fields_exact=True,all_physical_identity_provisional=True)
    js(out/'REFERENCE_COMPARISON.json',comparison)
    checkpoint(out,['MEMBERSHIP.npz','CARRIERS.npz','SELECTED_LINKS.npz','GROUPS.json','LINEAGE.json','SOLVER.json','SCOPE.json','REFERENCE_COMPARISON.json'],binding,'CERTIFIED_MAPPING_COMPLETE')
    verify_checkpoint(out,binding);cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
    for k in m:np.testing.assert_array_equal(m[k],cold[k])
    return cold,gs

def ambiguity_diagnostics(c,d,saved,prior,contexts):
    # Same final row sets in both arms; rank before seeing any pixels.
    groups={};current={};previous={};missing=[];labels={}
    for arm,(_,gg) in saved.items():
        current[arm]={group_key(g) for g in gg}
        for g in gg:groups.setdefault(group_key(g),g)
    for arm,pr in prior.items():
        previous[arm]={group_key(g) for g in pr['groups']}
        for g in pr['groups']:groups.setdefault(group_key(g),g)
    rank=lambda k:(-groups[k]['supported_length_p'],groups[k]['edge_id'],k)
    def take(keys,n,label):
        kk=sorted(set(keys),key=rank)[:n]
        if not kk:missing.append(label)
        for k in kk:labels.setdefault(k,[]).append(label)
    new=set().union(*(current[a]-previous[a] for a in current));damaged=set().union(*(previous[a]-current[a] for a in current))
    take(new,3,'top3_new_certified_paths');take(damaged,3,'top3_damaged_unit002_paths')
    kinds={int(x):str(y) for x,y in zip(d['arrays']['carrier_id'],d['arrays']['kind'])}
    take([k for k in new if all(kinds[x[0]]=='line' for x in k)],1,'largest_new_line_leaf_path')
    take([k for k in new if any(kinds[x[0]]=='polyline' for x in k)],1,'largest_new_polyline_leaf_path')
    for gid in c.get('reference_groups',[53254,201906,10975]):take([k for k,g in groups.items() if g['edge_id']==gid],1,'reference_'+str(gid))
    # Always expose the largest frozen ambiguity neighborhood, even after zero benefit.
    incident={}
    for i,(a,b) in enumerate(d['pairs']):incident.setdefault(a,[]).append(i);incident.setdefault(b,[]).append(i)
    def context(core):
        comps=[ctx for ctx in contexts if set(core)&set(ctx['carriers'])];expanded=set(core)
        for ctx in comps:expanded.update(ctx['carriers'])
        records=sorted({i for cid in expanded for i in incident.get(cid,[]) });halo=set(expanded)
        for i in records:halo.update(d['pairs'][i])
        return dict(evidence_carriers=sorted(halo),incident_record_ids=records,component_ids=[ctx['context_id'] for ctx in comps])
    cases=[]
    for k in sorted(labels,key=rank):
        core=sorted(x[0] for x in k);cases.append(dict(case_id='PATH_'+str(groups[k]['edge_id'])+'_'+hashlib.sha256(repr(k).encode()).hexdigest()[:8],labels=labels[k],core_carriers=core,**context(core)))
    if contexts:
        core=contexts[0]['carriers'];cases.append(dict(case_id='AMBIGUITY_CONTEXT_'+str(min(core)),labels=['largest_frozen_ambiguity_context'],core_carriers=core,**context(core)))
    for a,b in c['negative_pairs']:
        core=[a,b];cases.append(dict(case_id='NEGATIVE_'+str(a)+'_'+str(b),labels=['saved_negative_unknown_truth'],core_carriers=core,**context(core)))
    return dict(cases=cases,missing=missing,selection='symmetric final rows and complete incident evidence; no image-based selection',polyline_label_is_not_visible_curve_evidence=True)
