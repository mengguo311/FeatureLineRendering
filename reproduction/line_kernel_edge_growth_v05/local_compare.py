"""Saved-control comparisons and original-kernel contexts; no fitting."""
from common import *
from core import project
from pipeline import load_state
from transfer import render_rows
from transfer_behavior import crop_family

def compare_control(c,out,e,ids,groups):
    target=out/'CONTROL_COMPARISON.json'
    if (out/'CONTROL_COMPARISON_CHECKPOINT.json').exists():
        receipt=json.loads((out/'CONTROL_COMPARISON_CHECKPOINT.json').read_text());verify({str(out/k):v for k,v in receipt['files'].items()});return
    control=dict(np.load(c['control_membership']));old=json.loads(Path(c['control_groups']).read_text())['groups'];oldstate=load_state(c['control_state']);owner=control['edge_id']
    values,counts=np.unique(owner,return_counts=True);countmap=dict(zip(values,counts));changed=[]
    for g in groups:
        cc=e.carriers[g['edge_id']];labels=np.unique(owner[cc.rows])
        if len(labels)==1 and labels[0]>=0 and countmap[labels[0]]==len(cc.rows):continue
        iv=e.support(cc.reps,cc.q)[0];parts=[]
        for cid in np.unique(control['carrier_id'][cc.rows]):
            pc=oldstate['carriers'][int(cid)];reps=cc.reps[control['carrier_id'][e.r['mid'][cc.reps]]==cid]
            dom=project(pc.q,cc.q)[0];lo,hi=float(dom.min()),float(dom.max());outside=float(sum(max(0,min(b,lo)-a)+max(0,b-max(a,hi)) for a,b in iv))
            parts.append(dict(carrier_id=int(cid),version=pc.version,kernels=int(np.count_nonzero(control['carrier_id'][cc.rows]==cid)),intersection_seedlets=len(reps),intersection_mapped_support_p=e.support(reps,cc.q)[1] if len(reps) else 0,entire_control_support_p=e.support(pc.reps,pc.q)[1],mapped_finite_domain_p=[lo,hi],support_outside_domain_p=outside))
        largest=max(parts,key=lambda z:(z['entire_control_support_p'],-z['carrier_id']))
        changed.append(dict(edge_id=g['edge_id'],model=g['model'],kernels=g['kernels'],growth_gate=g['growth_gate'],supported_length_p=g['supported_length_p'],outward_over_M3_p=g['outward_support_p'],control_contributions=parts,gain_over_largest_entire_control_p=g['supported_length_p']-largest['entire_control_support_p'],outward_over_largest_control_p=largest['support_outside_domain_p'],substantial_original_parents=g['substantial_original_parents'],substantial_L1_fragments=g['substantial_L1_fragments']))
    lost=[];modified=[]
    for g in old:
        if not g['growth_gate']:continue
        rows=oldstate['carriers'][g['edge_id']].rows;new=np.unique(ids[rows])
        if len(new)!=1 or new[0]<0:lost.append(g['edge_id'])
        if len(new)!=1 or new[0]<0 or len(e.carriers[int(new[0])].rows)!=len(rows):modified.append(g['edge_id'])
    result=dict(assigned_gained_vs_control=int(np.count_nonzero((ids>=0)&(owner<0))),assigned_lost_vs_control=int(np.count_nonzero((ids<0)&(owner>=0))),changed_primary_id_rows=int(np.count_nonzero(ids!=owner)),control=c['control_membership'],control_sha256=c['input_files'][c['control_membership']],changed_groups=changed,control_growth_groups_members_not_preserved_together=lost,control_growth_groups_modified_partition=modified,control_growth_gate_ids=[g['edge_id'] for g in old if g['growth_gate']],variant_growth_gate_ids=[g['edge_id'] for g in groups if g['growth_gate']],changed_growth_gate_ids=[g['edge_id'] for g in changed if g['growth_gate']],changed_growth_gain_and_outward_ge4_over_control=[g['edge_id'] for g in changed if g['growth_gate'] and g['gain_over_largest_entire_control_p']>=4 and g['outward_over_largest_control_p']>=4],physical_identity_verified=False,contribution_rule='Kernel counts and mapped support use exact intersection; conservative gain compares entire old group support; no sum of overlapping contributions.')
    js(target,result);js(out/'CONTROL_COMPARISON_CHECKPOINT.json',dict(complete=True,files={target.name:sha(target)}))

def changed_contexts(c,out,pre,a,render,cams):
    path=Path(c['unit'])/'scenes'/c['scene']/'states/M4/EQUIVALENCE_CHOICES.npz';z=dict(np.load(path));ix=np.flatnonzero(z['old_equivalent']!=z['local_equivalent']);ix=sorted(ix,key=lambda k:(z['cid'][k],z['port'][k]))[:3];cases=[]
    for rank,k in enumerate(ix):
        ids=list(dict.fromkeys([int(z['cid'][k])]+z['others'][z['other_offsets'][k]:z['other_offsets'][k+1]].tolist()))
        rows=np.concatenate([pre[cid].rows for cid in ids]);labels=np.concatenate([np.full(len(pre[cid].rows),cid) for cid in ids]);name=f'CHANGED_EQ_{rank:02d}'
        nz(out/(name+'.npz'),rows=rows,labels=labels,input_ids=np.asarray(ids),input_versions=np.asarray([pre[cid].version for cid in ids]))
        cases.append(dict(rank=rank,owner=int(z['cid'][k]),port=int(z['port'][k]),old_equivalent=bool(z['old_equivalent'][k]),local_equivalent=bool(z['local_equivalent'][k]),rows_file=name+'.npz'))
        for cam in cams:
            image=out/f"{name}_{cam['view']}.png";render_rows(a,rows,labels,render,cam,image);crop_family([image],out/f"CROP_{name}_{cam['view']}")
    js(out/'CHANGED_EQ_SELECTION.json',dict(total_changed_choices=len(np.flatnonzero(z['old_equivalent']!=z['local_equivalent'])),rule='First3 by owner ID then port',cases=cases,missing='NO_CHANGED_EQUIVALENCE' if not cases else None))
