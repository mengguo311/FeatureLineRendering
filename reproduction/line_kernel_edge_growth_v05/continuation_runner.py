"""One parent-owned M3 topology pass from sealed M2; no initialization/pooling."""
from common import *
import common,argparse,signal,traceback
from pipeline import load_state,restore,checkpoint,verify_checkpoint
from transfer import TransferEngine,reset_level,complete_pass,export_stage,group_figures,render_rows
from transfer_behavior import select_groups,crop_family,scene_contract
from runner import tables,record_arrays,geometry_margin

def verify_predecessor(out,stage,decision_sha,config_sha,checkpoint_sha):
    out=Path(out);assert sha(out/'CHECKPOINT.json')==checkpoint_sha
    cp=json.loads((out/'CHECKPOINT.json').read_text())
    assert cp['complete'] and cp['stage']==stage
    assert cp['decision_sha256']==decision_sha and cp['config_binding']==config_sha
    verify({str(out/k):h for k,h in cp['files'].items()});return cp

def promotion_check(e,base,previous,r):
    ids,reason,aux,owner=e.primary(base)
    if np.any(ids[previous>=0]<0):raise RuntimeError('INCUMBENT_LOST_REJECT_M3_PROMOTION')
    if np.any(ids[r['kernel_rep']<0]>=0):raise RuntimeError('INVALID_SOURCE_ACTIVATED')
    if np.any((ids>=0)&(ids!=owner)):raise RuntimeError('MEMBERSHIP_OWNER_MISMATCH_REJECT_M3_PROMOTION')
    for cid,c in e.carriers.items():
        z=np.unique(ids[c.rows])
        if len(z)!=1 or z[0] not in (-1,cid):raise RuntimeError('PARTIAL_CARRIER_ASSIGNMENT_REJECT_M3_PROMOTION')
    return ids

def load_predecessor(c):
    old=json.loads(Path(c['predecessor_config']).read_text())
    assert sha(c['predecessor_config'])==c['predecessor_config_sha256']
    assert sha(old['decision_path'])==old['decision_sha256']
    verify_predecessor(Path(c['previous_checkpoint']).parent,'S2_MERGE_COMPLETE',old['decision_sha256'],c['predecessor_config_sha256'],c['input_files'][c['previous_checkpoint']])
    a=dict(np.load(c['gaussians']));r=dict(np.load(c['representatives']));base=dict(np.load(c['baseline_membership']));prev=dict(np.load(c['previous_membership']))
    cams=json.loads(Path(c['cameras']).read_text())[c['scene']];scene_contract(c,a,cams)
    with np.load(c['controls']) as z:d=(z['control'][z['control_index']]*z['derivative_basis'][:,:,None]).sum(1)
    norm=np.linalg.norm(d,axis=1);t=d/np.maximum(norm[:,None],1e-15)
    e=TransferEngine(a,r,t,c['p']);restore(e,load_state(c['previous_state']))
    arrays=dict(np.load(c['previous_carriers']));owner=np.full(len(a['means']),-1,np.int64)
    np.testing.assert_array_equal(arrays['carrier_id'],np.array(sorted(e.carriers)))
    for k,cid in enumerate(arrays['carrier_id']):
        if k%512==0:guard()
        cc=e.carriers[int(cid)];assert np.all(owner[cc.rows]<0);owner[cc.rows]=cc.cid
        for field in ('version','valid','baseline','kind'):assert getattr(cc,field)==arrays[field][k]
        for field,key,off in [('reps','seedlets','seed_offsets'),('rows','rows','row_offsets'),('origins','origins','origin_offsets')]:
            np.testing.assert_array_equal(getattr(cc,field),arrays[key][arrays[off][k]:arrays[off][k+1]])
        np.testing.assert_array_equal(cc.q*e.p,arrays['knots'][arrays['knot_offsets'][k]:arrays['knot_offsets'][k+1]])
        np.testing.assert_array_equal(e.rows_for(cc.reps),cc.rows)
        assert not cc.valid or (np.isfinite(t[cc.rows]).all() and np.all(norm[cc.rows]>0))
        z=np.unique(prev['edge_id'][cc.rows]);assert len(z)==1 and z[0] in (-1,cc.cid)
    np.testing.assert_array_equal(owner,prev['carrier_id']);np.testing.assert_array_equal(prev['line_kernel_id'],np.arange(len(owner)))
    assert sum(len(z.rows) for z in e.carriers.values())==np.count_nonzero(r['kernel_rep']>=0)
    np.testing.assert_array_equal(promotion_check(e,base['edge_id'],prev['edge_id'],r),prev['edge_id'])
    return a,r,base,prev,e,cams

def statistics_m3(out,e,ids,pre,baseids,l1owner):
    if (out/'STATS_CHECKPOINT.json').exists():
        cp=json.loads((out/'STATS_CHECKPOINT.json').read_text());verify({str(out/k):v for k,v in cp['files'].items()});return json.loads((out/'GROUPS.json').read_text())['groups']
    groups=tables(e,ids,pre,baseids)
    for g in groups:
        g['immediate_predecessor']='M2';g['M2_contributions']=g.pop('L1_contributions');g['gain_over_largest_M2_p']=g.pop('gain_over_largest_L1_p')
        for part in g['M2_contributions']:part['assigned_M2']=part.pop('assigned_L1')
        c=e.carriers[g['edge_id']];parts=[]
        for cid in np.unique(l1owner[c.rows]):
            reps=c.reps[l1owner[e.r['mid'][c.reps]]==cid]
            for rid in reps:assert np.all(l1owner[e.rows_for([rid])]==cid),'seed ownership must be exact'
            parts.append(dict(carrier_id=int(cid),kernels=int(np.count_nonzero(l1owner[c.rows]==cid)),seedlets=len(reps),mapped_supported_length_p=e.support(reps,c.q)[1] if len(reps) else 0))
        g['L1_contributions']=parts
        g['substantial_L1_fragments']=sum(z['carrier_id']>=0 and z['kernels']>=6 and z['mapped_supported_length_p']>=2 for z in parts)
        g['substantial_original_parents']=sum(z['kernels']>=6 and z['supported_length_p']>=2 for z in g['parent_contributions'])
    js(out/'GROUPS.json',dict(scene='scan24',stage='M3_MERGE_ONLY',p=e.p,immediate_predecessor='M2',groups=groups))
    gates=[g for g in groups if g['growth_gate']]
    metrics=dict(stage='M3_MERGE_ONLY',kernels=len(ids),assigned=int((ids>=0).sum()),UNKNOWN=int((ids<0).sum()),coverage=float(np.mean(ids>=0)),groups=len(groups),fit_attempts=e.fit_count,reasons=dict(e.stats),accepted_events=len(e.events),growth_gate_groups=[g['edge_id'] for g in gates],growth_with_three_substantial_L1=[g['edge_id'] for g in gates if g['substantial_L1_fragments']>=3],growth_with_two_substantial_original_parents=[g['edge_id'] for g in gates if g['substantial_original_parents']>=2],physical_identity_verified=False,all_unknown_seedlets_eligible=True)
    js(out/'METRICS.json',metrics);record_arrays(out/'CANDIDATE_STATUS.npz',e)
    js(out/'STATS_CHECKPOINT.json',dict(complete=True,files={n:sha(out/n) for n in ('GROUPS.json','METRICS.json','CANDIDATE_STATUS.npz')}));return groups

def diagnostics_m3(c,out,e,a,ids,groups,pre,base,prev,l1,render,cams):
    if (out/'CHECKPOINT.json').exists():verify_checkpoint(out,'M3_DIAGNOSTICS');return
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise RuntimeError('INCOMPLETE_DIAGNOSTICS_PRESERVED')
    chosen={g['edge_id']:g for g in select_groups(groups)};descendants={}
    for oldid in c['tracked_M2_groups']:
        matches=[g for g in groups if any(z['carrier_id']==oldid for z in g['M2_contributions'])]
        descendants[str(oldid)]=[g['edge_id'] for g in matches]
        chosen.update({g['edge_id']:g for g in matches})
    chosen=list(chosen.values())
    js(out/'VISUAL_SELECTION.json',dict(rule=c['visual_selection'],edge_ids=[g['edge_id'] for g in chosen],growth_edge_ids=[g['edge_id'] for g in chosen if g['growth_gate']],tracked_M2_descendants=descendants,missing_models=[k for k in ('line','polyline') if not any(g['growth_gate'] and g['model']==k for g in chosen)]))
    js(out/'CANDIDATE_PROVENANCE.json',dict(predecessor_state=c['previous_state'],sha256=c['input_files'][c['previous_state']],input_versions='immutable M2 carriers; one disjoint round',original_lineage=c['previous_lineage']))
    group_figures(out,a,{g['edge_id']:e.carriers[g['edge_id']].rows for g in chosen},dict(L0=base['edge_id'],L1=l1['edge_id'],M2=prev['edge_id'],M3=ids,PARENTS=a['primitive_id']),render,cams,ids)
    contexts=[];crops=[]
    for name,reasons in [('parallel',('parallel',)),('branch',('branch',)),('crossing_tangent',('tangent','endpoint_tangent')),('gap',('endpoint_gap','unsupported_gap')),('ambiguity',('ambiguous',)),('accepted_worst_margin',('accepted',))]:
        rr=[r for r in e.records if r['reason'] in reasons]
        if not rr:contexts.append(dict(category=name,status='NO_RECORDED_CASE'));continue
        rec=min(rr,key=lambda r:(geometry_margin(e,r,pre),r['cost'],r['a'],r['b']));aa,bb=pre[rec['a']],pre[rec['b']];rows=np.r_[aa.rows,bb.rows];labels=np.r_[np.full(len(aa.rows),aa.cid),np.full(len(bb.rows),bb.cid)]
        nz(out/f'CONTEXT_{name}.npz',rows=rows,input_ids=np.array([aa.cid,bb.cid]),input_versions=np.array([aa.version,bb.version]),row_labels=labels)
        contexts.append(dict(category=name,record=rec,input_versions=[[aa.cid,aa.version],[bb.cid,bb.version]],ranking_value=geometry_margin(e,rec,pre),rows_file=f'CONTEXT_{name}.npz'))
        for cam in cams:
            file=out/f"CONTEXT_{name}_{cam['view']}.png";render_rows(a,rows,labels,render,cam,file);crops.append(crop_family([file],out/f"CROP_CONTEXT_{name}_{cam['view']}"))
    js(out/'CONTEXT_SELECTION.json',contexts);js(out/'CONTEXT_CROPS.json',crops);checkpoint(out,[str(p.relative_to(out)) for p in sorted(out.rglob('*')) if p.is_file()],'M3_DIAGNOSTICS')

def run(c):
    common.configure(c);unit=Path(c['unit']);root=unit/'scenes'/c['scene'];stage='VERIFY';start=time.time()
    facts=dict(status='error',completed=[],delivery_gate=False,physical_identity_verified=False,science_claim='PENDING_VISUAL_ANALYSIS',last_valid_predecessor=c['previous_membership'])
    try:
        common.PHASE='input';guard();verify(c['input_files']);verify(c['source_files']);verify(c['helper_files']);assert sha(c['decision_path'])==c['decision_sha256']
        a,r,base,prev,e,cams=load_predecessor(c);pre=dict(e.carriers);l1=dict(np.load(c['L1_membership']));reference=root/'S0'
        if (reference/'CHECKPOINT.json').exists():verify_checkpoint(reference,'M2_RESTORE_VERIFIED')
        else:
            js(reference/'INPUT_REFERENCE.json',dict(files=c['input_files'],previous_config=c['predecessor_config'],previous_state=c['previous_state'],no_refitting=True,baseline_flags_unchanged=True));checkpoint(reference,['INPUT_REFERENCE.json'],'M2_RESTORE_VERIFIED')
        facts['completed'].append('M2_RESTORE_VERIFIED');stage='M3_TOPOLOGY';common.PHASE='M3';reset_level(e,3)
        complete_pass(e,root/'states/M3','M3_STATE',False);facts['completed'].append('M3_STATE')
        common.PHASE='final';stage='M3_PROMOTION'
        try:promotion_check(e,base['edge_id'],prev['edge_id'],r)
        except RuntimeError as exc:
            target=root/'PROMOTION_REJECTED.json'
            if not target.exists():js(target,dict(reason=str(exc),retained_predecessor=c['previous_membership'],candidate_state=str(root/'states/M3/STATE.pkl'),promoted=False))
            raise
        stage='M3_EXPORT';out=root/'stages/M3_MERGE_ONLY';render=helpers(c)['render']
        m,_=export_stage(c,out,e,a,r,base,prev,pre,render,cams,'M3_MERGE_ONLY',c['previous_lineage'])
        facts['completed'].append('M3_NATIVE');facts['delivery_gate']=True;facts['output_stage']=str(out)
        stage='M3_STATISTICS';groups=statistics_m3(out,e,m['edge_id'],pre,base['edge_id'],l1['carrier_id'])
        stage='M3_DIAGNOSTICS';diagnostics_m3(c,out/'diagnostics',e,a,m['edge_id'],groups,pre,base,prev,l1,render,cams)
        facts['completed'].append('M3_DIAGNOSTICS')
        compare=dict(M3=json.loads((out/'METRICS.json').read_text()),references=c['reference_results'],largest_contributor='M2',total_rounds=2,fit_cap_each_round=30000,round_count_total_work_confounded=True)
        if not (root/'COMPARISONS.json').exists():js(root/'COMPARISONS.json',compare)
        verify(c['input_files']);verify(c['source_files']);verify(c['helper_files']);facts.update(status='complete',comparisons=compare)
    except BaseException as exc:
        facts.update(status='partial' if facts['completed'] else 'error',failed_stage=stage,error=repr(exc),traceback=traceback.format_exc());raise
    finally:
        facts['missing_requested_stages']=[s for s in ('M2_RESTORE_VERIFIED','M3_STATE','M3_NATIVE','M3_DIAGNOSTICS') if s not in facts['completed']]
        facts.update(not_requested=['initialization','pooling','M4','ficus','scan65'],utc=now(),elapsed_seconds=time.time()-start,parent_exit_authoritative=True,config_sha256=c['_config_sha256'])
        target=unit/'RUN_RESULT.json'
        if target.exists():target=unit/f'RUN_RESULT_REENTRY_{time.time_ns()}.json'
        js(target,facts)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);arg=parser.parse_args();c=json.loads(Path(arg.config).read_text());c['_config_sha256']=sha(arg.config)
    def terminate(signum,frame):raise InterruptedError('parent signal '+str(signum))
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate);run(c)
