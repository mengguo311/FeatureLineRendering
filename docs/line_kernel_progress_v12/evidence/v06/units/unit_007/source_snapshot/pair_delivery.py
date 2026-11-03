"""Finite anchor identity export. Original leaf arrays and original kernels retained."""
from runtime_io import *
from geometry_base import EPS,project,union_intervals
from paired_delivery import evidence_rows
from pair_model import model_key

def membership_for(d,chosen,bank):
    old=d['membership'];m={k:v.copy() for k,v in old.items()};ids=m['edge_id'];groups=[];lineage=[];used=set()
    m['overlap_hypothesis_id']=np.full(len(ids),-1,np.int64);m['overlap_aux_hypotheses']=np.full((len(ids),2),-1,np.int64)
    for index,h in enumerate(sorted(chosen,key=lambda h:h['hid'])):
        cs=[d['leaves'][cid] for cid in h['leaves']];assert not used.intersection(h['leaves']);used.update(h['leaves'])
        rows=np.concatenate([cc.rows for cc in cs]);gid=min(h['leaves']);metrics=h['metrics'];activation=metrics['seedlets']>=3 and len(rows)>=6 and metrics['supported_length_p']>=4-EPS
        before=ids[rows].copy();assign=(before>=0)|activation;ids[rows[assign]]=gid
        if 'reason_code' in m:m['reason_code'][rows[assign]]=0
        m['overlap_hypothesis_id'][rows]=h['hid']
        orient={z['carrier_id']:z['reverse'] for z in h.get('costs',[])}
        item=dict(edge_id=gid,version=int(d['next_version']+index),hypothesis_id=h['hid'],anchor=h['anchor'],leaves=[dict(carrier_id=cc.cid,version=cc.version,reverse=bool(orient.get(cc.cid,False))) for cc in cs],rows=len(rows),activated_unknown=int(np.sum((before<0)&assign)),unknown_retained=int(np.sum(~assign)),**metrics,physical_identity_verified=False,provisional=True)
        item.update({k:h[k] for k in ('model_key','model_q','model_kind','seed_pair','host_metrics') if k in h})
        if 'host_metrics' in h:
            for leaf in item['leaves']:
                if leaf['carrier_id']==h['anchor']:leaf['reverse']=bool(h['host_metrics'].get('reverse',False))
        groups.append(item);lineage.append(dict(output_edge_id=gid,output_version=item['version'],anchor=[h['anchor'],d['leaves'][h['anchor']].version],input_leaves=[[cc.cid,cc.version] for cc in cs],operation='fixed_finite_anchor_overlap_identity',leaf_geometry_unchanged=True,topology_edges_added=0))
        lineage[-1].update(operation='finite_model_overlap_identity' if 'model_key' in h else 'fixed_finite_anchor_overlap_identity',model_key=list(model_key(h)),model_seed_pair=h.get('seed_pair'),model_q=h.get('model_q'))
    # Auxiliary hypothesis references are separate from preserved predecessor aux IDs.
    byleaf={cid:[] for cid in d['leaves']}
    for h in bank:
        for cid in h['leaves']:byleaf[cid].append(h)
    for cid,hs in byleaf.items():
        if not hs:continue
        rows=d['leaves'][cid].rows;primary=int(m['overlap_hypothesis_id'][rows[0]])
        alternatives=[h['hid'] for h in sorted(hs,key=lambda z:(-z['benefit'],model_key(z),tuple(z['leaves']))) if h['hid']!=primary][:2]
        for j,hid in enumerate(alternatives):m['overlap_aux_hypotheses'][rows,j]=hid
    assert not np.any((old['edge_id']>=0)&(ids<0))
    for cid,leaf in d['leaves'].items():
        if np.any(old['edge_id'][leaf.rows]>=0):assert len(np.unique(ids[leaf.rows]))==1,'INCUMBENT_SPLIT'
    m['previous_edge_id']=old['edge_id'].copy();m['provisional']=np.ones(len(ids),bool);m['composite_version']=np.full(len(ids),-1,np.int64)
    for g in groups:
        rows=evidence_rows(d,[x['carrier_id'] for x in g['leaves']]);m['composite_version'][rows[ids[rows]>=0]]=g['version']
    return m,groups,lineage

def export_overlap(out,c,d,selected,bank,receipts,scope,binding):
    out=Path(out);chosen=[h for h in bank if h['hid'] in set(selected)];assert len(chosen)==len(selected)
    m,gs,lin=membership_for(d,chosen,bank)
    nz(out/'MEMBERSHIP.npz',**m);nz(out/'CARRIERS.npz',**d['arrays'])
    js(out/'GROUPS.json',dict(groups=gs,representation='immutable_observation_leaves_with_original_or_recovered_finite_model',CARRIERS_contents='original_M4_leaves_only; auxiliary model_q in GROUPS and LINEAGE',untouched_groups_reference=c['membership']))
    js(out/'LINEAGE.json',dict(predecessor=c['state'],predecessor_sha256=c['input_files'][c['state']],events=lin,source_parent_not_identity=True))
    nz(out/'SELECTED_HYPOTHESES.npz',hypothesis_id=np.asarray(selected,np.int64));js(out/'SOLVER.json',receipts);js(out/'SCOPE.json',scope)
    checkpoint(out,['MEMBERSHIP.npz','CARRIERS.npz','GROUPS.json','LINEAGE.json','SELECTED_HYPOTHESES.npz','SOLVER.json','SCOPE.json'],binding,'OVERLAP_MAPPING_COMPLETE')
    verify_checkpoint(out,binding);cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
    for k in m:np.testing.assert_array_equal(m[k],cold[k])
    return cold,gs

def enrich(d,groups,guard=lambda:None):
    import copy
    result=copy.deepcopy(groups)
    for g in result:
        guard();cs=[d['leaves'][x['carrier_id']] for x in g['leaves']];a=d['leaves'][g['anchor']];q=np.asarray(g.get('model_q',a.q));rows=np.concatenate([cc.rows for cc in cs]);parents,counts=np.unique(d['asset']['primitive_id'][rows],return_counts=True);g['parent_contributions']=[]
        for parent,count in zip(parents,counts):
            reps=np.concatenate([cc.reps for cc in cs]);reps=reps[d['asset']['primitive_id'][d['representatives']['mid'][reps]]==parent]
            iv=project(d['representatives']['endpoints'][reps].reshape(-1,3)/d['p'],q)[0].reshape(-1,2) if len(reps) else []
            length=union_intervals(iv)[1];g['parent_contributions'].append(dict(parent=int(parent),kernels=int(count),supported_length_p=length,substantial=bool(count>=6 and length>=2-EPS)))
        g['pooled_between_carriers']=True;g['physical_extension_verified']=False;g['outward_support_note']='All intervals lie on the chosen finite auxiliary model; original leaf carriers are unchanged. Model extent is not physical observed extension.'
    return result

def diagnostics(c,d,saved,contexts):
    prior=json.loads(Path(c['prior_diagnostics']).read_text()) if c.get('prior_diagnostics') else dict(cases=[],missing=[])
    cases=[dict(x,labels=x['labels']+['unit004_fixed_reference']) for x in prior['cases']];missing=[];bykey={};chosen={}
    key=lambda g:(tuple(g.get('model_key',[0,g['anchor']])),tuple(x['carrier_id'] for x in g['leaves']))
    for arm,(_,gs) in saved.items():
        for g in gs:bykey[key(g)]=g
    oldkeys=set()
    for path in c.get('previous_arms',{}).values():
        for g in json.loads((Path(path)/'GROUPS.json').read_text())['groups']:oldkeys.add(tuple(x['carrier_id'] for x in g['leaves']))
    rank=lambda k:(-bykey[k]['supported_length_p'],bykey[k]['edge_id'],k)
    def take(ks,n,label):
        z=sorted(ks,key=rank)[:n]
        if not z:missing.append(label)
        for k in z:chosen.setdefault(k,[]).append(label)
    take([k for k in bykey if k[1] not in oldkeys],3,'top3_changed_identities_vs_unit004')
    for kind in ['line','polyline']:take([k for k,g in bykey.items() if g.get('model_kind')==kind and k[0][0]==1],1,'largest_new_'+kind+'_model_group')
    for k in sorted(chosen,key=rank):
        core=list(k[1]);cc=[x for x in contexts if set(core)&set(x['carriers'])]
        cases.append(dict(case_id='PAIR_MODEL_'+str(bykey[k]['edge_id'])+'_'+hashlib.sha256(repr(k).encode()).hexdigest()[:8],core_carriers=core,evidence_carriers=sorted({i for x in cc for i in x['evidence_carriers']}),incident_record_ids=sorted({i for x in cc for i in x['incident_record_ids']}),labels=chosen[k]))
    return dict(cases=cases,missing=missing,selection='unit004 fixed cases plus augmented-model same-row union; complete evidence; support then ID',curved_label_not_visual_evidence=True)
