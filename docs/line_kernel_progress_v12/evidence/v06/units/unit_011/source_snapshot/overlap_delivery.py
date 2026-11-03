"""Finite anchor identity export. Original leaf arrays and original kernels retained."""
from runtime_io import *
from geometry_base import EPS,project,union_intervals
from paired_delivery import evidence_rows

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
        groups.append(item);lineage.append(dict(output_edge_id=gid,output_version=item['version'],anchor=[h['anchor'],d['leaves'][h['anchor']].version],input_leaves=[[cc.cid,cc.version] for cc in cs],operation='fixed_finite_anchor_overlap_identity',leaf_geometry_unchanged=True,topology_edges_added=0))
    # Auxiliary hypothesis references are separate from preserved predecessor aux IDs.
    byleaf={cid:[] for cid in d['leaves']}
    for h in bank:
        for cid in h['leaves']:byleaf[cid].append(h)
    for cid,hs in byleaf.items():
        if not hs:continue
        rows=d['leaves'][cid].rows;primary=int(m['overlap_hypothesis_id'][rows[0]])
        alternatives=[h['hid'] for h in sorted(hs,key=lambda z:(-z['benefit'],z['anchor'],tuple(z['leaves']))) if h['hid']!=primary][:2]
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
    js(out/'GROUPS.json',dict(groups=gs,representation='fixed_finite_anchor_and_immutable_observation_leaves',untouched_groups_reference=c['membership']))
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
        guard();cs=[d['leaves'][x['carrier_id']] for x in g['leaves']];a=d['leaves'][g['anchor']];rows=np.concatenate([cc.rows for cc in cs]);parents,counts=np.unique(d['asset']['primitive_id'][rows],return_counts=True);g['parent_contributions']=[]
        for parent,count in zip(parents,counts):
            reps=np.concatenate([cc.reps for cc in cs]);reps=reps[d['asset']['primitive_id'][d['representatives']['mid'][reps]]==parent]
            iv=project(d['representatives']['endpoints'][reps].reshape(-1,3)/d['p'],a.q)[0].reshape(-1,2) if len(reps) else []
            length=union_intervals(iv)[1];g['parent_contributions'].append(dict(parent=int(parent),kernels=int(count),supported_length_p=length,substantial=bool(count>=6 and length>=2-EPS)))
        g['pooled_between_carriers']=True;g['physical_extension_verified']=False;g['outward_support_note']='No extrapolation; all intervals on fixed finite anchor. Extra coverage is pooling, not carrier extension.'
    return result

def diagnostics(c,d,saved,contexts):
    bykey={};keys={};chosen={};missing=[]
    key=lambda g:(g['anchor'],tuple(x['carrier_id'] for x in g['leaves']))
    for arm,(_,gs) in saved.items():
        keys[arm]={key(g) for g in gs}
        for g in gs:bykey[key(g)]=g
    rank=lambda k:(-bykey[k]['supported_length_p'],bykey[k]['edge_id'],k)
    def take(ks,n,label):
        z=sorted(ks,key=rank)[:n]
        if not z:missing.append(label)
        for k in z:chosen.setdefault(k,[]).append(label)
    different={k[1] for k in keys['greedy']}^{k[1] for k in keys['joint']}
    take([k for k in bykey if k[1] in different],3,'top3_different_identities')
    kinds={int(i):str(k) for i,k in zip(d['arrays']['carrier_id'],d['arrays']['kind'])}
    for kind in ('line','polyline'):take([k for k in bykey if kinds[k[0]]==kind],1,'largest_'+kind+'_anchor')
    incident={}
    for k,(a,b) in enumerate(d['pairs']):incident.setdefault(a,[]).append(k);incident.setdefault(b,[]).append(k)
    def case(name,core,labels):
        core=sorted(set(core));records={i for cid in core for i in incident.get(cid,[])};halo=set(core)
        for ctx in contexts:
            if set(core)&set(ctx['carriers']):halo.update(ctx['evidence_carriers']);records.update(ctx['incident_record_ids'])
        for k in records:halo.update(d['pairs'][k])
        return dict(case_id=name,core_carriers=core,evidence_carriers=sorted(halo),incident_record_ids=sorted(records),labels=labels)
    cases=[case('OVERLAP_'+str(bykey[k]['edge_id'])+'_'+hashlib.sha256(repr(k).encode()).hexdigest()[:8],k[1],chosen[k]) for k in sorted(chosen,key=rank)]
    for name,ids in c['reference_leaf_groups'].items():cases.append(case('REFERENCE_'+name,ids,['sealed_reference_not_new_growth']))
    for a,b in c['negative_pairs']:cases.append(case('NEGATIVE_'+str(a)+'_'+str(b),[a,b],['saved_negative_unknown_truth']))
    return dict(cases=cases,missing=missing,selection='same rows both arms; complete competition plus nonrecursive incident evidence; support then ID',curved_label_not_visual_evidence=True)
