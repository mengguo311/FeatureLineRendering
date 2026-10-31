"""Progressive protected continuation with durable same-pass controls."""
from common import *
import common,argparse,signal,traceback
from pipeline import load_state,restore,checkpoint,verify_checkpoint
from transfer import TransferEngine,reset_level,complete_pass,export_stage,group_figures,render_rows
from transfer_behavior import select_groups,crop_family,scene_contract
from runner import tables,record_arrays,geometry_margin
from progressive_engine import ProtectedEngine as TransferEngine,complete_pass,verify_preservation,load_control,control_dir
from transfer import carrier_arrays
from core import project
from progressive_compare import compare_control
from progressive_visuals import supplemental_contexts,lost_control_figures,new_model_selection

def level_contract(c):
    c=c or {};level=int(c.get('level',3));assert level in (3,4,5)
    label=f'M{level}';pred=c.get('predecessor_label',f'M{level-1}')
    assert pred==f'M{level-1}'
    return level,label,pred

def verify_predecessor(out,stage,decision_sha,config_sha,checkpoint_sha):
    out=Path(out);assert sha(out/'CHECKPOINT.json')==checkpoint_sha
    cp=json.loads((out/'CHECKPOINT.json').read_text())
    assert cp['complete'] and cp['stage']==stage
    assert cp['decision_sha256']==decision_sha and cp['config_binding']==config_sha
    verify({str(out/k):h for k,h in cp['files'].items()});return cp

def promotion_check(e,base,previous,r):
    ids,reason,aux,owner=e.primary(base)
    if np.any(ids[previous>=0]<0):raise RuntimeError('INCUMBENT_LOST_REJECT_'+level_contract(common.CFG)[1]+'_PROMOTION')
    if np.any(ids[r['kernel_rep']<0]>=0):raise RuntimeError('INVALID_SOURCE_ACTIVATED')
    if np.any((ids>=0)&(ids!=owner)):raise RuntimeError('MEMBERSHIP_OWNER_MISMATCH_REJECT_'+level_contract(common.CFG)[1]+'_PROMOTION')
    for cid,c in e.carriers.items():
        z=np.unique(ids[c.rows])
        if len(z)!=1 or z[0] not in (-1,cid):raise RuntimeError('PARTIAL_CARRIER_ASSIGNMENT_REJECT_'+level_contract(common.CFG)[1]+'_PROMOTION')
    if common.CFG and e.level==level_contract(common.CFG)[0]:
        prefix=load_control(common.CFG,e,'prefix')
        e.protected_input_ids={cid for ev in prefix.events for cid,_ in ev['inputs']}
        e.protected_output_ids={ev['output'][0] for ev in prefix.events}
        verify_preservation(e,prefix,base)
    for oldid in np.unique(previous[previous>=0]):
        z=np.unique(ids[previous==oldid])
        if len(z)!=1 or z[0]<0:raise RuntimeError('INCUMBENT_SPLIT_REJECT_PROMOTION')
    return ids

def load_predecessor(c):
    old=json.loads(Path(c['predecessor_config']).read_text())
    assert sha(c['predecessor_config'])==c['predecessor_config_sha256']
    assert sha(old['decision_path'])==old['decision_sha256']
    verify_predecessor(Path(c['previous_checkpoint']).parent,c['previous_checkpoint_stage'],old['decision_sha256'],c['predecessor_config_sha256'],c['input_files'][c['previous_checkpoint']])
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

def mapped_contributions(e,c,owner):
    parts=[]
    for cid in np.unique(owner[c.rows]):
        reps=c.reps[owner[e.r['mid'][c.reps]]==cid]
        for rid in reps:assert np.all(owner[e.rows_for([rid])]==cid),'seed ownership must be exact'
        parts.append(dict(carrier_id=int(cid),kernels=int(np.count_nonzero(owner[c.rows]==cid)),seedlets=len(reps),mapped_supported_length_p=e.support(reps,c.q)[1] if len(reps) else 0))
    return parts

def statistics_level(out,e,ids,pre,baseids,l1owner,history_owners=None,disputed_override=None):
    level,label,pred=level_contract(common.CFG)
    if (out/'STATS_CHECKPOINT.json').exists():
        cp=json.loads((out/'STATS_CHECKPOINT.json').read_text());verify({str(out/k):v for k,v in cp['files'].items()});saved=json.loads((out/'GROUPS.json').read_text())
        assert saved['stage']==label+'_MERGE_ONLY' and saved['immediate_predecessor']==pred
        return saved['groups']
    groups=tables(e,ids,pre,baseids)
    owners={'L1':l1owner,**(history_owners or {})}
    assert pred not in owners and all(k in ('L1','M2','M3') for k in owners)
    if disputed_override is None:
        protected=json.loads((Path(common.CFG['unit'])/'scenes'/common.CFG['scene']/'states'/label/'PROTECTION.json').read_text())
        disputed=set(protected['disputed_outputs'])
    else:disputed=set(disputed_override)
    previous_protection=json.loads(Path(common.CFG['previous_protection']).read_text()) if common.CFG.get('previous_protection') else {}
    inherited=set(previous_protection.get('disputed_outputs',[]))|set(previous_protection.get('inherited_disputed_outputs',[]))
    inherited_rows=np.zeros(len(ids),bool)
    for cid in inherited:
        if cid in pre:inherited_rows[pre[cid].rows]=True
    inherited_descendants={cid for cid,cc in e.carriers.items() if np.any(inherited_rows[cc.rows])}
    disputed.update(inherited_descendants)
    for g in groups:
        g['inherited_dispute']=g['edge_id'] in inherited_descendants
        g['disputed_prefix']=g['edge_id'] in disputed
        g['eligible_new_growth']=bool(g['growth_gate'] and not g['disputed_prefix'])
        g['immediate_predecessor']=pred;g[pred+'_contributions']=g.pop('L1_contributions');g['gain_over_largest_'+pred+'_p']=g.pop('gain_over_largest_L1_p')
        for part in g[pred+'_contributions']:part['assigned_'+pred]=part.pop('assigned_L1')
        c=e.carriers[g['edge_id']]
        for name,owner in owners.items():
            parts=mapped_contributions(e,c,owner);g[name+'_contributions']=parts
            g['substantial_'+name+'_fragments']=sum(z['carrier_id']>=0 and z['kernels']>=6 and z['mapped_supported_length_p']>=2 for z in parts)
        g['substantial_original_parents']=sum(z['kernels']>=6 and z['supported_length_p']>=2 for z in g['parent_contributions'])
    js(out/'GROUPS.json',dict(scene=common.CFG['scene'] if common.CFG else 'fixture',stage=label+'_MERGE_ONLY',p=e.p,immediate_predecessor=pred,groups=groups))
    gates=[g for g in groups if g['growth_gate']]
    metrics=dict(stage=label+'_MERGE_ONLY',kernels=len(ids),assigned=int((ids>=0).sum()),UNKNOWN=int((ids<0).sum()),coverage=float(np.mean(ids>=0)),groups=len(groups),fit_attempts=e.fit_count,reasons=dict(e.stats),accepted_events=len(e.events),growth_gate_groups=[g['edge_id'] for g in gates],growth_with_three_substantial_L1=[g['edge_id'] for g in gates if g['substantial_L1_fragments']>=3],growth_with_two_substantial_original_parents=[g['edge_id'] for g in gates if g['substantial_original_parents']>=2],physical_identity_verified=False,all_unknown_seedlets_eligible=True)
    if level>=4:
        metrics.update(growth_with_three_L1_and_two_original_parents=[g['edge_id'] for g in gates if g['substantial_L1_fragments']>=3 and g['substantial_original_parents']>=2],growth_outward_ge4p=[g['edge_id'] for g in gates if g['outward_support_p']>=4],substantial_cross_parent_growth_outward_ge4p=[g['edge_id'] for g in gates if g['outward_support_p']>=4 and g['substantial_original_parents']>=2])
    metrics['inherited_disputed_outputs']=sorted(inherited_descendants)
    metrics['disputed_prefix_groups']=sorted(disputed)
    metrics['eligible_new_growth_groups']=[g['edge_id'] for g in gates if g['eligible_new_growth']]
    nz(out/'PROTECTION_MEMBERSHIP.npz',line_kernel_id=np.arange(len(ids)),disputed_prefix=np.isin(ids,list(disputed)),provisional=np.ones(len(ids),bool))
    js(out/'METRICS.json',metrics);record_arrays(out/'CANDIDATE_STATUS.npz',e)
    js(out/'STATS_CHECKPOINT.json',dict(complete=True,files={n:sha(out/n) for n in ('GROUPS.json','METRICS.json','CANDIDATE_STATUS.npz','PROTECTION_MEMBERSHIP.npz')}));return groups

def select_progression_groups(groups):
    """Frozen display union; never changes fitting, membership or growth gates."""
    selected={g['edge_id']:g for g in select_groups(groups)}
    three=[g for g in groups if g['growth_gate'] and g['substantial_L1_fragments']>=3]
    if three:
        chosen=min(three,key=lambda g:(-g['supported_length_p'],g['edge_id']))
        selected[chosen['edge_id']]=chosen
    return list(selected.values())

def diagnostics_level(c,out,e,a,ids,groups,pre,base,prev,l1,render,cams,history=None):
    level,label,pred=level_contract(c)
    if (out/'CHECKPOINT.json').exists():verify_checkpoint(out,label+'_DIAGNOSTICS');return
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise RuntimeError('INCOMPLETE_DIAGNOSTICS_PRESERVED')
    chosen={g['edge_id']:g for g in select_progression_groups(groups)};descendants={}
    for oldid in c.get('tracked_predecessor_groups',c.get('tracked_M2_groups',[])):
        matches=[g for g in groups if any(z['carrier_id']==oldid for z in g[pred+'_contributions'])]
        descendants[str(oldid)]=[g['edge_id'] for g in matches]
        chosen.update({g['edge_id']:g for g in matches})
    comparison=json.loads((out.parent/'CONTROL_COMPARISON.json').read_text())
    changed={z['edge_id'] for z in comparison['changed_groups']}
    more=sorted((g for g in groups if g['edge_id'] in changed),key=lambda g:(-g['supported_length_p'],g['edge_id']))[:3]
    for oldid in c.get('changed_tracked_groups',[]):
        more.extend(g for g in groups if g['edge_id'] in changed and any(z['carrier_id']==oldid for z in g[pred+'_contributions']))
    chosen.update({g['edge_id']:g for g in more})
    chosen.update({g['edge_id']:g for g in new_model_selection(groups,comparison,out)})
    chosen=list(chosen.values())
    js(out/'VISUAL_SELECTION.json',dict(rule=c['visual_selection'],edge_ids=[g['edge_id'] for g in chosen],growth_edge_ids=[g['edge_id'] for g in chosen if g['growth_gate']],**{'tracked_'+pred+'_descendants':descendants},three_fragment_growth_edge_ids=[g['edge_id'] for g in chosen if g['growth_gate'] and g['substantial_L1_fragments']>=3],missing_models=[k for k in ('line','polyline') if not any(g['growth_gate'] and g['model']==k for g in chosen)]))
    js(out/'CANDIDATE_PROVENANCE.json',dict(predecessor_state=c['previous_state'],sha256=c['input_files'][c['previous_state']],input_versions='immutable '+pred+' carriers; one disjoint round',original_lineage=c['previous_lineage']))
    display_ids=dict(L0=base['edge_id'],L1=l1['edge_id'])
    display_ids.update({name:member['edge_id'] for name,member in (history or {}).items()})
    display_ids.update({pred:prev['edge_id'],label:ids,'PARENTS':a['primitive_id']})
    display_ids[label+'_PREFIX']=np.load(c['prefix_membership'])['edge_id'];display_ids[label+'_VARIANT']=ids
    display_ids[label+'_JOINT']=np.load(c['joint_membership'])['edge_id']
    group_figures(out,a,{g['edge_id']:e.carriers[g['edge_id']].rows for g in chosen},display_ids,render,cams,ids)
    contexts=[];crops=[]
    for name,reasons in [('parallel',('parallel',)),('branch',('branch',)),('crossing_tangent',('tangent','endpoint_tangent')),('gap',('endpoint_gap','unsupported_gap')),('ambiguity',('ambiguous',)),('accepted_worst_margin',('accepted',))]:
        rr=[r for r in e.records if r['reason'] in reasons]
        if not rr:contexts.append(dict(category=name,status='NO_RECORDED_CASE'));continue
        rec=min(rr,key=lambda r:(geometry_margin(e,r,pre),r['cost'],r['a'],r['b']));aa,bb=pre[rec['a']],pre[rec['b']];rows=np.r_[aa.rows,bb.rows];labels=np.r_[np.full(len(aa.rows),aa.cid),np.full(len(bb.rows),bb.cid)]
        nz(out/f'CONTEXT_{name}.npz',rows=rows,input_ids=np.array([aa.cid,bb.cid]),input_versions=np.array([aa.version,bb.version]),row_labels=labels)
        contexts.append(dict(category=name,record=rec,input_versions=[[aa.cid,aa.version],[bb.cid,bb.version]],ranking_value=geometry_margin(e,rec,pre),rows_file=f'CONTEXT_{name}.npz'))
        for cam in cams:
            file=out/f"CONTEXT_{name}_{cam['view']}.png";render_rows(a,rows,labels,render,cam,file);crops.append(crop_family([file],out/f"CROP_CONTEXT_{name}_{cam['view']}"))
    supplemental_contexts(c,out,e,pre,a,groups,display_ids,render,cams,ids)
    lost_control_figures(c,out,comparison,a,display_ids,render,cams,ids)
    js(out/'CONTEXT_SELECTION.json',contexts);js(out/'CONTEXT_CROPS.json',crops);checkpoint(out,[str(p.relative_to(out)) for p in sorted(out.rglob('*')) if p.is_file()],label+'_DIAGNOSTICS')


def run(c):
    common.configure(c);unit=Path(c['unit']);root=unit/'scenes'/c['scene'];stage='VERIFY';start=time.time()
    level,label,pred=level_contract(c)
    facts=dict(variant='prefix_protected_endpoint',control_membership=c['previous_membership'],scene=c['scene'],status='error',completed=[],delivery_gate=False,physical_identity_verified=False,science_claim='PENDING_VISUAL_ANALYSIS',last_valid_predecessor=c['previous_membership'])
    try:
        common.PHASE='input';guard();verify(c['input_files']);verify(c['source_files']);verify(c['helper_files']);assert sha(c['decision_path'])==c['decision_sha256']
        a,r,base,prev,e,cams=load_predecessor(c);pre=dict(e.carriers);l1=dict(np.load(c['L1_membership']));history={}
        for name,path in c.get('history_memberships',{}).items():
            assert name in ('M2','M3') and int(name[1:])<level-1
            saved=dict(np.load(path));np.testing.assert_array_equal(saved['line_kernel_id'],np.arange(len(a['means'])))
            assert len(saved['carrier_id'])==len(a['means']);history[name]=saved
        reference=root/'S0'
        if (reference/'CHECKPOINT.json').exists():verify_checkpoint(reference,pred+'_RESTORE_VERIFIED')
        else:
            js(reference/'INPUT_REFERENCE.json',dict(files=c['input_files'],previous_config=c['predecessor_config'],previous_state=c['previous_state'],no_refitting=True,baseline_flags_unchanged=True));checkpoint(reference,['INPUT_REFERENCE.json'],pred+'_RESTORE_VERIFIED')
        facts['completed'].append(pred+'_RESTORE_VERIFIED');stage=label+'_TOPOLOGY';common.PHASE=label;reset_level(e,level)
        complete_pass(e,root/'states'/label,label+'_STATE',False);facts['completed'].append(label+'_STATE')
        common.PHASE='final';stage=label+'_PROMOTION'
        try:promotion_check(e,base['edge_id'],prev['edge_id'],r)
        except RuntimeError as exc:
            target=root/'PROMOTION_REJECTED.json'
            if not target.exists():js(target,dict(reason=str(exc),retained_predecessor=c['previous_membership'],candidate_state=str(root/'states'/label/'STATE.pkl'),promoted=False))
            raise
        stage=label+'_EXPORT';out=root/'stages'/(label+'_MERGE_ONLY');render=helpers(c)['render']
        m,_=export_stage(c,out,e,a,r,base,prev,pre,render,cams,label+'_MERGE_ONLY',c['previous_lineage'])
        facts['completed'].append(label+'_NATIVE');facts['delivery_gate']=True;facts['output_stage']=str(out)
        stage=label+'_STATISTICS';groups=statistics_level(out,e,m['edge_id'],pre,base['edge_id'],l1['carrier_id'],{name:z['carrier_id'] for name,z in history.items()})
        runtime=dict(c);runtime['input_files']=dict(c['input_files'])
        for kind in ('prefix','joint'):
            ce=load_control(c,e,kind);directory=control_dir(c,kind)
            statistics_level(directory,ce,ce.primary(base['edge_id'])[0],pre,base['edge_id'],l1['carrier_id'],{name:z['carrier_id'] for name,z in history.items()},disputed_override=set())
            for key,file in [('state','STATE.pkl'),('membership','MEMBERSHIP.npz'),('groups','GROUPS.json')]:
                runtime[kind+'_'+key]=str(directory/file);runtime['input_files'][str(directory/file)]=sha(directory/file)
        for key in ('state','membership','groups'):runtime['control_'+key]=c['previous_'+key]
        compare_control(runtime,out,e,m['edge_id'],groups)
        for kind in ('prefix','joint'):
            cc=dict(runtime)
            for key in ('state','membership','groups'):cc['control_'+key]=runtime[kind+'_'+key]
            compare_control(cc,out/(kind.upper()+'_COMPARISON'),e,m['edge_id'],groups)
        stage=label+'_DIAGNOSTICS';diagnostics_level(runtime,out/'diagnostics',e,a,m['edge_id'],groups,pre,base,prev,l1,render,cams,history)
        facts['completed'].append(label+'_DIAGNOSTICS')
        compare={label:json.loads((out/'METRICS.json').read_text()),'references':c['reference_results'],'largest_contributor':pred,'total_rounds':level-1,'fit_caps_by_round':c['fit_caps_by_round'],'control_fit_limit':c['control_fit_limit'],'same_round_count_vs_control':False,'only_fit_budget_changed':False,'only_proposal_coverage_changed':False,'only_commit_priority_changed':False,'only_round_count_and_total_fit_opportunity_changed':True,'internal_controls':'New same-pass prefix/joint; no historical M5 replay','supplement':json.loads((root/'states'/label/'SUPPLEMENT_STATS.json').read_text())}
        if not (root/'COMPARISONS.json').exists():js(root/'COMPARISONS.json',compare)
        verify(c['input_files']);verify(c['source_files']);verify(c['helper_files']);facts.update(status='complete',comparisons=compare)
    except BaseException as exc:
        facts.update(status='partial' if facts['completed'] else 'error',failed_stage=stage,error=repr(exc),traceback=traceback.format_exc());raise
    finally:
        facts['missing_requested_stages']=[s for s in (pred+'_RESTORE_VERIFIED',label+'_STATE',label+'_NATIVE',label+'_DIAGNOSTICS') if s not in facts['completed']]
        facts.update(not_requested=['initialization','pooling',f'M{level+1}']+[s for s in ('scan24','ficus','scan65') if s!=c['scene']],utc=now(),elapsed_seconds=time.time()-start,parent_exit_authoritative=True,config_sha256=c['_config_sha256'])
        target=unit/'RUN_RESULT.json'
        if target.exists():target=unit/f'RUN_RESULT_REENTRY_{time.time_ns()}.json'
        js(target,facts)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);arg=parser.parse_args();c=json.loads(Path(arg.config).read_text());c['_config_sha256']=sha(arg.config)
    def terminate(signum,frame):raise InterruptedError('parent signal '+str(signum))
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate);run(c)
