"""Parent-only complete saved-overlap coverage; bounded single recovery per new pair."""
from runtime_io import *
from scene_adapter import load
from overlap_model import successful_overlaps
from coverage_policy import select_scope as select_components
from pair_model import select_greedy,select_joint
from scene_stages import prepare_banks
from scene_delivery import export_overlap,enrich,diagnostics,render_diagnostics
from scene_render import geometry_fingerprint,render_arm
from paired_delivery import evidence_rows,save_pair,restore_pair
import argparse,traceback

class OverlapLimits(Limits):
    def guard(self,phase='delivery'):
        if phase=='readiness':
            if time.monotonic()-self.start>=min(600,self.seconds-600):raise TimeoutError('PHASE_DEADLINE readiness')
            return super().guard('selection')
        return super().guard(phase)

def clean_resume(out,binding):
    out=Path(out)
    if (out/'CHECKPOINT.json').exists():return verify_checkpoint(out,binding)
    if out.exists() and any(out.iterdir()):raise RuntimeError('INCOMPLETE_STAGE_PRESERVED '+str(out))
    return None

def run(c,config_path):
    unit=Path(c['unit']);binding=sha(config_path);lim=OverlapLimits(c);completed=[];error=None
    facts=dict(status='partial',config_sha256=binding,parent_exit_authoritative=True,started_utc=now(),completed=completed,fit_calls=None,new_spatial_candidates=0)
    try:
        if (unit/'RUN_RESULT.json').exists():raise RuntimeError('CLOSED_RUN_EXISTS_NO_OVERWRITE')
        d=load(c,lim.guard);d['overlaps']=successful_overlaps(d)
        assert len(d['pairs'])==c['expected_candidate_records'] and len(d['overlaps'])==c['expected_successful_overlap'],'FROZEN_OVERLAP_COUNTS'
        before=geometry_fingerprint(d['asset'])
        for value in d['asset'].values():value.flags.writeable=False
        contexts,audit=select_components(c,d);selection=dict(contexts=contexts,audit=audit,original_rows=c['kernel_count'],success_overlap=len(d['overlaps']),old_ambiguity_retained_as_provenance=True,endpoint_topology_not_selected=True,proposal_cap_reference=c['candidate_metrics'])
        assert audit['all_components']==c['expected_all_components'] and audit['not_selected']==0,'FULL_SCOPE_COUNT'
        assert len(contexts)==c['expected_all_components']
        if 'expected_decision_leaves' in c:assert sum(len(x['carriers']) for x in contexts)==c['expected_decision_leaves'],'FROZEN_LEAF_COUNT'
        if 'expected_max_component' in c:assert max((len(x['carriers']) for x in contexts),default=0)==c['expected_max_component'],'FROZEN_COMPONENT_SIZE'
        prep=unit/('scenes/'+c['scene']+'/readiness')
        if clean_resume(prep,binding):assert json.loads((prep/'SELECTION.json').read_text())==selection
        else:
            js(prep/'SELECTION.json',selection);nz(prep/'CANDIDATES.npz',**d['candidates']);nz(prep/'ORDERED_CANDIDATES.npz',**d['ordered']);nz(prep/'AMBIGUITY.npz',pairs=np.asarray(sorted(d['ambiguous']),np.int64).reshape(-1,2))
            offsets=[0];rows=[]
            for ctx in contexts:
                rr=evidence_rows(d,ctx['evidence_carriers']);rows.append(rr);offsets.append(offsets[-1]+len(rr))
            nz(prep/'EVIDENCE_ROWS.npz',rows=np.concatenate(rows) if rows else np.empty(0,np.int64),offsets=np.asarray(offsets,np.int64))
            js(prep/'PROVENANCE.json',dict(input_files=c['input_files'],helper_files=c['helper_files'],source_files=c['source_files'],fit_scope='fresh scene; at most%d single recovery attempts; no historical same-method control'%c['model_fit']['maximum_attempts'],original_leaf_geometry_fixed=True))
            checkpoint(prep,['SELECTION.json','CANDIDATES.npz','ORDERED_CANDIDATES.npz','AMBIGUITY.npz','EVIDENCE_ROWS.npz','PROVENANCE.json'],binding,'OVERLAP_SELECTION_FROZEN')
        completed.append('readiness')
        banks,bycontext,bank_status,model_facts=prepare_banks(c,d,contexts,lim,binding);facts.update(model_facts)
        completed.append('hypothesis_banks');facts['bank_status']=bank_status;facts['hypothesis_count']=len(banks)
        choices={a:[] for a in ('greedy','joint')};receipts={a:[] for a in choices};solver_seconds=model_facts['control_solver_seconds']
        for ctx,bs in zip(contexts,bank_status):
            progress=unit/('scenes/'+c['scene']+'/progress')/('component_%05d'%ctx['context_id']);hs=bycontext[ctx['context_id']]
            if clean_resume(progress,binding):selected,recs=restore_pair(progress,binding,ctx['context_id'])
            else:
                budget=min(c['solver']['per_context_seconds']-model_facts['control_seconds_by_context'].get(str(ctx['context_id']),0.),c['solver']['total_seconds']-solver_seconds,lim.seconds-600-(time.monotonic()-lim.start))
                if bs['status']!='BANK_COMPLETE' or budget<=0:
                    selected=bs['fallback_selections'];recs={a:dict(status='FALLBACK_M4',reason=bs['status'] if bs['status']!='BANK_COMPLETE' else 'SOLVER_BUDGET',seconds=0) for a in choices}
                else:
                    selected={'greedy':select_greedy(hs)};recs={'greedy':dict(status='greedy_complete',seconds=0)}
                    try:selected['joint'],recs['joint']=select_joint(hs,budget,lambda:lim.guard('selection'))

                    except TimeoutError as exc:
                        if 'PHASE_DEADLINE' not in str(exc):raise
                        selected=bs['fallback_selections'];recs={a:dict(status='FALLBACK_M4',reason=str(exc),seconds=max(0.,budget)) for a in choices}
                if recs['joint'].get('feasible_incumbent') is False:
                    selected=bs['fallback_selections'];recs['greedy']=dict(status='FALLBACK_M4_NO_JOINT_INCUMBENT',seconds=0)
                save_pair(progress,binding,ctx['context_id'],selected,recs)
            solver_seconds+=recs['joint'].get('seconds',0.)
            valid={h['hid'] for h in hs}
            for arm in choices:
                assert set(selected[arm])<=valid;choices[arm].extend(selected[arm]);receipts[arm].append(dict(context_id=ctx['context_id'],**recs[arm]))
        facts['solver_seconds']=solver_seconds
        version_start=d['next_version'];saved={};outputs={};facts['outputs']=outputs
        for ai,arm in enumerate(choices):
            out=unit/('scenes/'+c['scene']+'/stages')/arm
            if clean_resume(out,binding):
                m=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False));gs=json.loads((out/'GROUPS.json').read_text())['groups'];assert np.load(out/'SELECTED_HYPOTHESES.npz',allow_pickle=False)['hypothesis_id'].tolist()==sorted(choices[arm])
            else:m,gs=export_overlap(out,c,dict(d,next_version=version_start+ai*c['kernel_count']),sorted(choices[arm]),banks,receipts[arm],selection,binding)
            saved[arm]=(m,gs);outputs[arm]=dict(path=str(out),hypotheses=len(gs));completed.append(arm+'_mapping');print('MAPPING_COMPLETE',arm,flush=True)
        after=geometry_fingerprint(d['asset']);assert before==after,'GEOMETRY_MUTATION';assert sha(c['gaussians'])==c['input_files'][c['gaussians']]
        if not (unit/'GEOMETRY_AUDIT.json').exists():js(unit/'GEOMETRY_AUDIT.json',dict(original_count=c['kernel_count'],row_order_exact=True,fields=after,unchanged_before_after=True,source_sha256=c['input_files'][c['gaussians']],carrier_geometry_rendered=False))
        cams_all=json.loads(Path(c['cameras']).read_text())[c['scene']];cams=sorted([x for x in cams_all if x['view'] in c['views']],key=lambda x:c['views'].index(x['view']));assert len(cams)==2
        render=renderer(c)
        for arm,(m,gs) in saved.items():
            out=Path(outputs[arm]['path']);cp=out/'FULL_NATIVE_CHECKPOINT.json'
            if cp.exists():
                rec=json.loads(cp.read_text());assert rec['config_sha256']==binding and rec['complete'];verify({str(out/k):v for k,v in rec['files'].items()});images=[view+'_FULL.png' for view in c['views']]
            else:
                if any((out/p).exists() for p in ['DISPLAY_COLORS.npz','DISPLAY_SOURCE.json']+[v+'_FULL.png' for v in c['views']]):raise RuntimeError('INCOMPLETE_FULL_NATIVE_PRESERVED')
                images=render_arm(out,c,d,m,gs,contexts,render,cams,lambda:lim.guard('delivery'),full_only=True)
                js(cp,dict(complete=True,config_sha256=binding,files={p:sha(out/p) for p in ['DISPLAY_COLORS.npz','DISPLAY_SOURCE.json']+images}))
            outputs[arm]['full_images']=images;completed.append(arm+'_full_native')
        facts['delivery_gate']=True
        for arm,(m,gs) in saved.items():
            out=Path(outputs[arm]['path']);old=d['membership']['edge_id'];ids=m['edge_id'];metrics=dict(assigned=int(np.sum(ids>=0)),unknown=int(np.sum(ids<0)),gained_assigned=int(np.sum((old<0)&(ids>=0))),lost_assigned=int(np.sum((old>=0)&(ids<0))),changed_rows=int(np.sum(old!=ids)),overlap_groups=len(gs),physical_identity_verified=False,carrier_extension_run=False,overlap_pooling_run=True,holdout=False)
            if not (out/'METRICS.json').exists():js(out/'METRICS.json',metrics)
            if not (out/'GROUP_STATISTICS.json').exists():js(out/'GROUP_STATISTICS.json',dict(groups=enrich(d,gs,lambda:lim.guard('delivery')),counts_are_not_accuracy=True))
        comparison=unit/('scenes/'+c['scene']+'/COMPARISON.json')
        if not comparison.exists():js(comparison,dict(greedy_only_hypotheses=sorted(set(choices['greedy'])-set(choices['joint'])),joint_only_hypotheses=sorted(set(choices['joint'])-set(choices['greedy'])),membership_different_rows=int(np.sum(saved['greedy'][0]['edge_id']!=saved['joint'][0]['edge_id'])),physical_correctness_verified=False))
        d['kinds']={int(i):str(k) for i,k in zip(d['arrays']['carrier_id'],d['arrays']['kind'])}
        diag=diagnostics(c,d,saved,contexts);root=unit/('scenes/'+c['scene']+'/diagnostics')
        diagnostic_saved=dict(saved)
        diagnostic_saved['M4_reference']=(d['membership'],[])
        references=unit/('scenes/'+c['scene']+'/diagnostic_references')
        if not clean_resume(references,binding):
            nz(references/'M4_MEMBERSHIP.npz',**d['membership'])
            js(references/'SOURCE.json',dict(M4=c['membership'],original_kernel_source=c['gaussians'],original_kernel_sha256=c['input_files'][c['gaussians']]))
            checkpoint(references,['M4_MEMBERSHIP.npz','SOURCE.json'],binding,'DIAGNOSTIC_REFERENCE_MEMBERSHIPS')
        if root.exists():
            # Resume only fully checkpointed individual cases; never trust orphan images.
            for case in diag['cases']:
                cp=root/(case['case_id']+'_CHECKPOINT.json');existing=[p for a in diagnostic_saved for p in (unit/('scenes/'+c['scene']+'/stages')/a/'diagnostics').glob(case['case_id']+'*.png')]
                if existing:
                    if not cp.exists():raise RuntimeError('INCOMPLETE_DIAGNOSTIC_PRESERVED')
                    rec=json.loads(cp.read_text());assert rec['config_sha256']==binding;verify({str(unit/k):v for k,v in rec['images'].items()})
        images=render_diagnostics(unit,c,d,diagnostic_saved,diag,render,cams,lambda:lim.guard('delivery'),binding)
        for arm in saved:
            out=Path(outputs[arm]['path']);all_images=outputs[arm]['full_images']+images[arm]
            if not (out/'IMAGES.json').exists():js(out/'IMAGES.json',dict(files=all_images,actual_original_kernels=True,held_out=False,missing_cases=diag['missing']))
            outputs[arm]['images']=all_images;completed.append(arm+'_diagnostics')
        verify(c['source_files']);verify(c['helper_files'])
        complete=bool(contexts) and all(x['status']=='BANK_COMPLETE' for x in bank_status) and all(x['status']=='optimal' for x in receipts['joint'])
        facts.update(status='complete' if complete else 'partial',scientific_verdict='PARTIAL_PENDING_VISUAL_REVIEW',zero_hypotheses_is_negative_result=not bool(banks))
    except BaseException as exc:
        error=exc;facts.update(status='partial' if completed else 'blocked',error=repr(exc),traceback=traceback.format_exc())
    finally:
        facts.update(completed=completed,ended_utc=now(),elapsed_seconds=time.monotonic()-lim.start,actual_saved_pngs=[str(p.relative_to(unit)) for p in sorted((unit/'scenes').rglob('*.png'))])
        if not (unit/'RUN_RESULT.json').exists():js(unit/'RUN_RESULT.json',facts)
        lim.close()
    if error is not None:raise error

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();run(json.loads(Path(a.config).read_text()),a.config)
