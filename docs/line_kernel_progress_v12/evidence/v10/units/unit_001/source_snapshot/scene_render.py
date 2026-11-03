"""Complete-row exports precede any actual-kernel picture; no fitted geometry export."""
from runtime_io import *
from port_paths import paths
from geometry_base import EPS,union_intervals,project,arc

def geometry_fingerprint(asset):
    return {k:dict(dtype=str(v.dtype),shape=list(v.shape),sha256=hashlib.sha256(v.tobytes()).hexdigest()) for k,v in asset.items()}

def membership_for(d,selected,oracle):
    old=d['membership'];m={k:v.copy() for k,v in old.items()};ids=m['edge_id'];groups=[];lineage=[]
    for path_index,chain in enumerate(paths(d['edges'],selected)):
        ok,why,metrics=oracle(chain);assert ok,why
        cs=[d['leaves'][cid] for cid,_ in chain];rows=np.concatenate([c.rows for c in cs]);gid=min(c.cid for c in cs)
        activation=metrics['seedlets']>=3 and len(rows)>=6 and metrics['supported_length_p']>=4-EPS
        before=ids[rows].copy();assign=(before>=0)|activation
        ids[rows[assign]]=gid
        # Dormant insufficient support stays UNKNOWN; no incumbent can be lost.
        if 'reason_code' in m:m['reason_code'][rows[assign]]=0
        item=dict(edge_id=gid,version=int(d.get('next_version',0)+path_index),leaves=[dict(carrier_id=c.cid,version=c.version,reverse=rev) for c,(_,rev) in zip(cs,chain)],rows=len(rows),activated_unknown=int(np.sum((before<0)&assign)),unknown_retained=int(np.sum(~assign)),**metrics)
        item['physical_identity_verified']=False;item['provisional']=True
        groups.append(item);lineage.append(dict(output_edge_id=gid,output_version=item['version'],input_leaves=[[c.cid,c.version] for c in cs],operation='composite_path_identity',leaf_geometry_unchanged=True))
    assert not np.any((old['edge_id']>=0)&(ids<0))
    for cid,c in d['leaves'].items():
        if np.any(old['edge_id'][c.rows]>=0):assert len(np.unique(ids[c.rows]))==1,'INCUMBENT_SPLIT'
    m['previous_edge_id']=old['edge_id'].copy();m['provisional']=np.ones(len(ids),bool)
    m['composite_version']=np.full(len(ids),-1,np.int64)
    for g in groups:
        rr=np.concatenate([d['leaves'][z['carrier_id']].rows for z in g['leaves']]);rr=rr[ids[rr]>=0];m['composite_version'][rr]=g['version']
    return m,groups,lineage

def export_arm(out,c,d,selected,oracle,receipts,scope,binding):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    m,groups,lineage=membership_for(d,selected,oracle)
    nz(out/'MEMBERSHIP.npz',**m)
    # Exact finite leaf arrays, not synthetic connecting segments.
    nz(out/'CARRIERS.npz',**d['arrays'])
    js(out/'GROUPS.json',dict(scene=c['scene'],representation='ordered_finite_leaf_composite',groups=groups,untouched_groups_reference=c['membership']))
    js(out/'LINEAGE.json',dict(predecessor=c['state'],predecessor_sha256=c['input_files'][c['state']],events=lineage,source_parent_not_identity=True))
    js(out/'SOLVER.json',receipts)
    nz(out/'SELECTED_LINKS.npz',record_index=np.asarray(selected,np.int64))
    js(out/'SCOPE.json',scope)
    checkpoint(out,['MEMBERSHIP.npz','CARRIERS.npz','GROUPS.json','LINEAGE.json','SOLVER.json','SELECTED_LINKS.npz','SCOPE.json'],binding,'MAPPING_COMPLETE')
    verify_checkpoint(out,binding)
    cold=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False))
    for k in m:np.testing.assert_array_equal(cold[k],m[k])
    return cold,groups

def enrich_groups(d,groups,guard=lambda:None):
    import copy
    result=copy.deepcopy(groups)
    for item in result:
        guard();cs=[d['leaves'][z['carrier_id']] for z in item['leaves']];metrics=item
        rows=np.concatenate([cc.rows for cc in cs]);parents,counts=np.unique(d['asset']['primitive_id'][rows],return_counts=True)
        item['parent_contributions']=[]
        for parent,count in zip(parents,counts):
            intervals=[]
            for cc,domain in zip(cs,metrics['leaf_domains_p']):
                rep=cc.reps[d['asset']['primitive_id'][d['representatives']['mid'][cc.reps]]==parent]
                if not len(rep):continue
                ss=project(d['representatives']['endpoints'][rep].reshape(-1,3)/d['p'],cc.q)[0].reshape(-1,2)
                if domain['reverse']:ss=arc(cc.q)[-1]-ss
                intervals.extend((ss+domain['start']).tolist())
            pl=union_intervals(intervals)[1]
            item['parent_contributions'].append(dict(parent=int(parent),kernels=int(count),supported_length_p=pl,substantial=bool(count>=6 and pl>=2-EPS)))
        item['physical_identity_verified']=False;item['provisional']=True;item['pooled_between_carriers']=False
        item['largest_leaf_support_p']=max(union_intervals(c.intervals)[1] for c in cs)
        item['support_gain_over_largest_leaf_p']=metrics['supported_length_p']-item['largest_leaf_support_p']
        largest=max(range(len(cs)),key=lambda k:(union_intervals(cs[k].intervals)[1],-cs[k].cid));dom=metrics['leaf_domains_p'][largest]
        item['support_outside_largest_leaf_domain_p']=sum(max(0.,min(b,dom['start'])-a)+max(0.,b-max(a,dom['end'])) for a,b in metrics['supported_intervals'])
        item['outward_support_note']='Composite path coordinate, not proof of physical extension; unsupported connectors excluded.'
    return result


def render_arm(out,c,d,m,groups,contexts,render,cams,guard,full_only=False):
    out=Path(out);a=d['asset'];ids=m['edge_id'];cols=colors(ids)
    if not (out/'DISPLAY_COLORS.npz').exists():nz(out/'DISPLAY_COLORS.npz',colors=cols)
    if not (out/'DISPLAY_SOURCE.json').exists():js(out/'DISPLAY_SOURCE.json',dict(gaussians=c['gaussians'],sha256=c['input_files'][c['gaussians']],rows='all%d original rows unchanged'%c['kernel_count'],color_file='DISPLAY_COLORS.npz',background=[1,1,1],floor=.0144,cameras=c['cameras'],camera_sha256=c['input_files'][c['cameras']],no_source_surface_occlusion=True,carrier_and_connectors_rendered=False))
    asset={k:a[k] for k in ('means','covariance','opacity')};asset['colors']=cols
    images=[]
    for cam in cams:
        guard();path=out/(cam['view']+'_FULL.png')
        if not path.exists():save_image(path,render(asset,cam,(1,1,1),.0144)['rgb'])
        images.append(path.name)
    if full_only:return images
    diag=out/'diagnostics';diag.mkdir(exist_ok=True)
    # Whole original competing contexts, including oversized NOT_RUN ones.
    for ctx in contexts:
        guard();rr=np.sort(np.concatenate([d['leaves'][k].rows for k in ctx['carriers']]))
        if not len(rr):continue
        rows_path=diag/f"CONTEXT_{ctx['context_id']}_ROWS.npz"
        if not rows_path.exists():nz(rows_path,rows=rr,carriers=np.asarray(ctx['carriers'],np.int64))
        sub={k:a[k][rr] for k in ('means','covariance','opacity')};sub['colors']=cols[rr]
        for cam in cams:
            guard();path=diag/f"CONTEXT_{ctx['context_id']}_{cam['view']}.png"
            if not path.exists():save_image(path,render(sub,cam,(1,1,1),.0144)['rgb'])
            images.append(str(path.relative_to(out)))
    # Every changed path within bounded contexts, preserve all its original members.
    for g in groups:
        guard();rr=np.sort(np.concatenate([d['leaves'][z['carrier_id']].rows for z in g['leaves']]))
        rows_path=diag/f"GROUP_{g['edge_id']}_ROWS.npz"
        if not rows_path.exists():nz(rows_path,rows=rr)
        sub={k:a[k][rr] for k in ('means','covariance','opacity')};sub['colors']=cols[rr]
        for cam in cams:
            guard();path=diag/f"GROUP_{g['edge_id']}_{cam['view']}.png"
            if not path.exists():save_image(path,render(sub,cam,(1,1,1),.0144)['rgb'])
            images.append(str(path.relative_to(out)))
    if not (out/'IMAGES.json').exists():js(out/'IMAGES.json',dict(files=images,actual_original_kernels=True,held_out=False,visual_verdict='PENDING_ACTUAL_IMAGE_REVIEW'))
    return images
