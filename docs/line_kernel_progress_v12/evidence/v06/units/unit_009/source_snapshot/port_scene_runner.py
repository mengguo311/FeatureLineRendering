"""Parent-owned paired port selector; no subprocess, fitting or new candidates."""
from runtime_io import *
from scene_adapter import load,local_validator
from port_scene_policy import select,diagnostic_cases
from port_paths import greedy,joint,PathOracle
from scene_render import export_arm,geometry_fingerprint,render_arm,enrich_groups
from paired_delivery import save_pair,restore_pair,evidence_rows
from scene_delivery import render_diagnostics
from port_scene_references import reference_views,reference_comparisons
import argparse,traceback

def run(c,config_path):
    unit=Path(c['unit']);binding=sha(config_path);lim=Limits(c);completed=[]
    facts=dict(status='partial',completed=completed,parent_exit_authoritative=True,config_sha256=binding,science_claim='UNASSESSED',started_utc=now());exit_error=None
    try:
        if (unit/'RUN_RESULT.json').exists():raise RuntimeError('CLOSED_RUN_EXISTS_NO_OVERWRITE')
        if datetime.datetime.now(datetime.timezone.utc).timestamp()>datetime.datetime.fromisoformat(c['parent_launch_latest_jst']).timestamp():raise TimeoutError('PARENT_LAUNCH_WINDOW_EXPIRED')
        d=load(c,lim.guard)
        assert len(d['pairs'])==c['expected_candidate_records'],'FROZEN_RECORD_COUNT'
        assert len(d['all_endpoint'])==c['expected_successful_endpoints'] and len(d['edges'])==c['expected_eligible_endpoints'],'FROZEN_GRAPH_COUNTS'
        before=geometry_fingerprint(d['asset'])
        for v in d['asset'].values():v.flags.writeable=False
        seeds,contexts=select(c,d)
        assert len(contexts)==c['expected_endpoint_components'],'FROZEN_COMPONENT_COUNT'
        lim.guard('readiness');prep=unit/'scenes'/c['scene']/'readiness';prep.mkdir(parents=True,exist_ok=True)
        selection=dict(seeds=[dict(label=k,carriers=v) for k,v in seeds],contexts=contexts,closure='Eligible decision components; nonrecursive complete incident-record evidence halos',candidate_caps_reference=c['candidate_metrics'],ambiguous_pairs=len(d['ambiguous']),eligible_endpoint_edges=len(d['edges']),successful_endpoint_edges=len(d['all_endpoint']),source_rows=len(d['asset']['means']),scope_status='READY' if contexts else 'NO_ELIGIBLE_GRAPH',cross_component_physical_identity_verified=False)
        if (prep/'CHECKPOINT.json').exists():
            verify_checkpoint(prep,binding);assert json.loads((prep/'SELECTION.json').read_text())==selection
        else:
            if any(prep.iterdir()):raise RuntimeError('INCOMPLETE_READINESS_PRESERVED')
            js(prep/'SELECTION.json',selection);nz(prep/'CANDIDATES.npz',**d['candidates']);nz(prep/'ORDERED_CANDIDATES.npz',**d['ordered'])
            nz(prep/'AMBIGUOUS_PAIRS.npz',pairs=np.asarray(sorted(d['ambiguous']),np.int64).reshape(-1,2))
            evidence=[];offset=[0]
            for ctx in contexts:
                lim.guard('readiness');rr=evidence_rows(d,ctx['evidence_carriers']);evidence.append(rr);offset.append(offset[-1]+len(rr))
            nz(prep/'EVIDENCE_ROWS.npz',rows=np.concatenate(evidence) if evidence else np.empty(0,np.int64),offsets=np.array(offset,np.int64),context_id=np.array([x['context_id'] for x in contexts],np.int64))
            js(prep/'PROVENANCE.json',dict(inputs=c['input_files'],helpers=c['helper_files'],source_files=c['source_files'],no_refit=True,new_candidate_generation=False,primitive_id='source parent, never truth',constraint_dependency='Unchanged unit001 oracle checks a single selected path only; no eligible edge crosses components'))
            checkpoint(prep,['SELECTION.json','CANDIDATES.npz','ORDERED_CANDIDATES.npz','AMBIGUOUS_PAIRS.npz','EVIDENCE_ROWS.npz','PROVENANCE.json'],binding,'READINESS_COMPLETE')
        completed.append('readiness');print('READINESS_COMPLETE',len(contexts),flush=True)
        oracles={a:PathOracle(d['leaves'],d['representatives']['x']/c['p'],d['representatives']['t'],local_validator(d,c['p']),lambda:lim.guard('selection')) for a in ('greedy','joint')}
        selected={a:[] for a in oracles};receipts={a:[] for a in oracles};solver_seconds=0.;processed=[];stopped=False
        for ctx in contexts:
            idx=ctx['context_id'];progress=unit/'scenes'/c['scene']/'progress'/('component_%05d'%idx)
            if ctx['status']!='READY':
                for arm in oracles:receipts[arm].append(dict(context_id=idx,status=ctx['status']))
                continue
            if stopped:
                for arm in oracles:receipts[arm].append(dict(context_id=idx,status='NOT_RUN_BUDGET'))
                continue
            try:
                if (progress/'CHECKPOINT.json').exists():choices,recs=restore_pair(progress,binding,idx)
                else:
                    if progress.exists() and any(progress.iterdir()):raise RuntimeError('INCOMPLETE_PAIR_PRESERVED '+str(idx))
                    lim.guard('selection');budget=min(c['solver']['per_context_seconds'],c['solver']['total_seconds']-solver_seconds,lim.seconds-600-(time.monotonic()-lim.start))
                    if budget<=0:raise TimeoutError('SOLVER_TOTAL_BUDGET')
                    subset=set(ctx['eligible_edge_ids']);edges=[e for e in d['edges'] if e.eid in subset]
                    choices={};recs={}
                    choices['greedy'],recs['greedy']=greedy(edges,oracles['greedy'],lambda:lim.guard('selection'))
                    budget=min(budget,lim.seconds-600-(time.monotonic()-lim.start))
                    choices['joint'],recs['joint']=joint(edges,oracles['joint'],budget,lambda:lim.guard('selection'),c['solver']['max_cut_rounds'])
                    for arm in recs:recs[arm]['context_id']=idx
                    save_pair(progress,binding,idx,choices,recs)
                processed.append(idx);solver_seconds+=recs['joint'].get('seconds',0.)
                for arm in oracles:selected[arm].extend(choices[arm]);receipts[arm].append(recs[arm])
            except TimeoutError as exc:
                stopped=True
                for arm in oracles:receipts[arm].append(dict(context_id=idx,status='NOT_RUN_DEADLINE',reason=str(exc)))
        facts['processed_paired_components']=processed;facts['solver_seconds']=solver_seconds
        prior=dict(status='NOT_APPLICABLE_FRESH_SCENE',reference='Unit002 numerical policy, not historical ficus replay')
        if not (unit/'PRIOR_SCOPE_REPLAY.json').exists():js(unit/'PRIOR_SCOPE_REPLAY.json',prior)
        outputs={};saved={};facts['outputs']=outputs
        for arm in oracles:
            out=unit/'scenes'/c['scene']/'stages'/arm;oracles[arm].guard=lambda:lim.guard('delivery')
            if (out/'CHECKPOINT.json').exists():
                verify_checkpoint(out,binding);m=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False));gs=json.loads((out/'GROUPS.json').read_text())['groups']
                assert np.load(out/'SELECTED_LINKS.npz')['record_index'].tolist()==sorted(selected[arm])
            else:
                if out.exists() and any(out.iterdir()):raise RuntimeError('INCOMPLETE_ARM_PRESERVED '+arm)
                m,gs=export_arm(out,c,d,sorted(selected[arm]),oracles[arm],receipts[arm],dict(**selection,processed_paired_components=processed),binding)
            saved[arm]=(m,gs);outputs[arm]=dict(path=str(out),selected_links=len(selected[arm]),paths=len(gs),solver=receipts[arm]);completed.append(arm+'_mapping');print('MAPPING_COMPLETE',arm,flush=True)
        after=geometry_fingerprint(d['asset']);assert before==after,'GEOMETRY_MUTATION'
        audit=dict(original_count=c['kernel_count'],row_order_exact=True,fields=after,unchanged_before_after=True,source_sha256=c['input_files'][c['gaussians']],source_hash_after=sha(c['gaussians']),geometry_never_exported_as_fitted_model=True)
        assert audit['source_sha256']==audit['source_hash_after']
        if not (unit/'GEOMETRY_AUDIT.json').exists():js(unit/'GEOMETRY_AUDIT.json',audit)
        cams_all=json.loads(Path(c['cameras']).read_text())[c['scene']];cams=[v for v in cams_all if v['view'] in c['views']];assert len(cams)==2
        cams=sorted(cams,key=lambda x:c['views'].index(x['view']));render=renderer(c)
        for arm,(m,gs) in saved.items():
            out=Path(outputs[arm]['path']);images=render_arm(out,c,d,m,gs,contexts,render,cams,lambda:lim.guard('delivery'),full_only=True)
            fullcp=out/'FULL_NATIVE_CHECKPOINT.json'
            if fullcp.exists():verify({str(out/k):v for k,v in json.loads(fullcp.read_text())['files'].items()})
            else:js(fullcp,dict(complete=True,config_sha256=binding,files={p:sha(out/p) for p in ['DISPLAY_COLORS.npz','DISPLAY_SOURCE.json']+images}))
            outputs[arm]['full_images']=images;completed.append(arm+'_full_native')
        facts['delivery_gate']=True
        for arm,(m,gs) in saved.items():
            out=Path(outputs[arm]['path']);enriched=enrich_groups(d,gs,lambda:lim.guard('delivery'))
            if not (out/'GROUP_STATISTICS.json').exists():js(out/'GROUP_STATISTICS.json',dict(groups=enriched,counts_are_not_accuracy=True))
            old=d['membership']['edge_id'];ids=m['edge_id']
            metrics=dict(assigned=int(np.sum(ids>=0)),unknown=int(np.sum(ids<0)),changed_rows=int(np.sum(ids!=old)),gained_assigned=int(np.sum((old<0)&(ids>=0))),lost_assigned=int(np.sum((old>=0)&(ids<0))),composite_paths=len(gs),physical_identity_verified=False,duplicate_pooling_run=False,holdout=False)
            if not (out/'METRICS.json').exists():js(out/'METRICS.json',metrics)
        compare=unit/'scenes'/c['scene']/'COMPARISON.json'
        if not compare.exists():js(compare,dict(greedy_only_links=sorted(set(selected['greedy'])-set(selected['joint'])),joint_only_links=sorted(set(selected['joint'])-set(selected['greedy'])),same_selected_links=sorted(set(selected['greedy'])&set(selected['joint'])),membership_different_rows=int(np.sum(saved['greedy'][0]['edge_id']!=saved['joint'][0]['edge_id'])),physical_correctness_verified=False))
        diag=diagnostic_cases(c,d,saved,contexts,seeds)
        refs=reference_views(c,d)
        refcompare=unit/'scenes'/c['scene']/'REFERENCE_COMPARISON.json'
        if not refcompare.exists():js(refcompare,reference_comparisons(saved,refs))
        images=render_diagnostics(unit,c,d,{**saved,**refs},diag,render,cams,lambda:lim.guard('delivery'),binding)
        for arm in saved:
            out=Path(outputs[arm]['path']);all_images=outputs[arm]['full_images']+images[arm]
            if not (out/'IMAGES.json').exists():js(out/'IMAGES.json',dict(files=all_images,actual_original_kernels=True,held_out=False,missing_cases=diag['missing']))
            if not (out/'NATIVE_CHECKPOINT.json').exists():js(out/'NATIVE_CHECKPOINT.json',dict(complete=True,config_sha256=binding,files={p:sha(out/p) for p in ['DISPLAY_COLORS.npz','DISPLAY_SOURCE.json','IMAGES.json','METRICS.json','GROUP_STATISTICS.json']+all_images}))
            outputs[arm]['images']=all_images;completed.append(arm+'_native_images')
        verify(c['helper_files']);verify(c['source_files'])
        complete=all(r['status'] in ('greedy_complete','optimal','no_edges') for arm in receipts.values() for r in arm)
        facts.update(status='complete' if contexts and complete else 'partial',scope_status=selection['scope_status'],scientific_verdict='PARTIAL_PENDING_VISUAL_REVIEW')
    except BaseException as exc:
        facts.update(status='partial' if completed else 'blocked',error=repr(exc),traceback=traceback.format_exc());exit_error=exc
    finally:
        facts.update(completed=completed,ended_utc=now(),elapsed_seconds=time.monotonic()-lim.start,actual_saved_pngs=[str(p.relative_to(unit)) for p in sorted((unit/'scenes').rglob('*.png'))],fit_calls=0,new_candidates=0)
        if not (unit/'RUN_RESULT.json').exists():js(unit/'RUN_RESULT.json',facts)
        lim.close()
    if exit_error is not None:raise exit_error

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args();run(json.loads(Path(args.config).read_text()),args.config)
