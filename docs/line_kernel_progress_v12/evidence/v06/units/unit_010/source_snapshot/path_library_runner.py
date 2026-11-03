"""Parent-owned four-arm path-library computation; no child processes."""
from runtime_io import *
from scene_adapter import load
from port_scene_policy import select
from path_library import *
from path_library_delivery import export,enrich,diagnostics
from scene_render import geometry_fingerprint,render_arm
from scene_delivery import render_diagnostics
from paired_delivery import evidence_rows
from port_scene_references import reference_views,reference_comparisons
import argparse,traceback
ARMS=('concat_greedy','concat_joint','common_greedy','common_joint')

def complete(path,binding):
    path=Path(path)
    if (path/'CHECKPOINT.json').exists():verify_checkpoint(path,binding);return True
    if path.exists() and any(path.iterdir()):raise RuntimeError('INCOMPLETE_STAGE_PRESERVED '+str(path))
    return False

def run(c,config_path):
    unit=Path(c['unit']);binding=sha(config_path);lim=Limits(c);done=[];error=None;fit_calls=0
    facts=dict(status='partial',completed=done,parent_exit_authoritative=True,config_sha256=binding,started_utc=now(),new_candidates=0)
    def guard(phase='delivery'):
        lim.guard(phase)
        if phase=='models' and time.monotonic()-lim.start>=c['stage_budgets']['models_by']:raise TimeoutError('MODEL_STAGE_DEADLINE')
    try:
        if (unit/'RUN_RESULT.json').exists():raise RuntimeError('CLOSED_RUN_EXISTS')
        if time.time()>datetime.datetime.fromisoformat(c['parent_launch_latest_jst']).timestamp():raise TimeoutError('LAUNCH_WINDOW_EXPIRED')
        d=load(c,lambda:guard('readiness'));before=geometry_fingerprint(d['asset'])
        for v in d['asset'].values():v.flags.writeable=False
        assert len(d['pairs'])==c['expected_candidate_records'] and len(d['all_endpoint'])==c['expected_successful_endpoints'] and len(d['edges'])==c['expected_eligible_endpoints'],'GRAPH_COUNT'
        seeds,contexts=select(c,d)
        assert len(contexts)==c['expected_endpoint_components'] and max(len(x['carriers']) for x in contexts)==c['expected_max_component'],'COMPONENT_COUNT'
        assert len(d['all_endpoint'])-len(d['edges'])==c['expected_masked_endpoints'],'MASK_COUNT'
        prep=unit/'scenes'/c['scene']/'readiness';scope=dict(contexts=contexts,complete_saved_graph=True,masked_endpoint_pairs=c['expected_masked_endpoints'])
        if not complete(prep,binding):
            js(prep/'SELECTION.json',scope);nz(prep/'CANDIDATES.npz',**d['candidates']);nz(prep/'ORDERED_CANDIDATES.npz',**d['ordered']);nz(prep/'AMBIGUOUS_PAIRS.npz',pairs=np.asarray(sorted(d['ambiguous']),np.int64).reshape(-1,2))
            rr=[];offset=[0]
            for ctx in contexts:
                z=evidence_rows(d,ctx['evidence_carriers']);rr.append(z);offset.append(offset[-1]+len(z))
            nz(prep/'EVIDENCE_ROWS.npz',rows=np.concatenate(rr),offsets=np.array(offset));js(prep/'PROVENANCE.json',dict(inputs=c['input_files'],helpers=c['helper_files'],sources=c['source_files']))
            checkpoint(prep,['SELECTION.json','CANDIDATES.npz','ORDERED_CANDIDATES.npz','AMBIGUOUS_PAIRS.npz','EVIDENCE_ROWS.npz','PROVENANCE.json'],binding,'READINESS_COMPLETE')
        done.append('readiness');engine=fit_engine(c['fit_source'],d);banks={'concat':[],'common':[]};statuses=[];choices={a:[] for a in ARMS};receipts={a:[] for a in ARMS};solver_seconds=0.;next_hid=0
        for ctx in contexts:
            idx=ctx['context_id'];p=unit/'scenes'/c['scene']/'components'/('%05d'%idx)
            if complete(p,binding):rec=json.loads((p/'RESULT.json').read_text())
            else:
                rec=dict(context_id=idx,status='NOT_RUN',banks={'concat':[],'common':[]},choices={a:[] for a in ARMS},receipts={a:dict(status='FALLBACK_M4') for a in ARMS},fit_calls=0,next_hid=next_hid)
                count_before=engine.fit_count
                try:
                    guard('models')
                    if ctx['status']!='READY':raise PathOverflow(ctx['status'])
                    es=[e for e in d['edges'] if e.eid in set(ctx['eligible_edge_ids'])];hs=enumerate_paths(es,c['path_cap'],lambda:guard('models'))
                    for h in hs:h['hid']+=next_hid
                    rec['paths']=hs;rec['next_hid']=next_hid+len(hs)
                    bb,checks=build_banks(d,hs,engine,lambda:guard('models'));rec.update(banks=bb,model_checks=checks)
                    for rep in bb:
                        for h in bb[rep]:h['representation']=rep
                    context_seconds=0.
                    for rep in ('concat','common'):
                        guard('selection');budget=min(c['solver']['per_context_seconds']-context_seconds,c['solver']['total_seconds']-solver_seconds-context_seconds,lim.seconds-600-(time.monotonic()-lim.start))
                        if budget<=0:raise TimeoutError('SOLVER_BUDGET')
                        a=rep+'_greedy';rec['choices'][a]=select_greedy(bb[rep]);rec['receipts'][a]=dict(status='greedy_complete')
                        a=rep+'_joint';rec['choices'][a],rec['receipts'][a]=select_joint(bb[rep],budget,lambda:guard('selection'));context_seconds+=rec['receipts'][a].get('seconds',0)
                        if rec['receipts'][a].get('feasible_incumbent') is False:raise TimeoutError('NO_FEASIBLE_INCUMBENT')
                    rec['status']='COMPLETE' if all(rec['receipts'][r+'_joint']['status']=='optimal' for r in ('concat','common')) else 'PARTIAL_INCUMBENT'
                except (TimeoutError,PathOverflow) as exc:
                    rec.update(status='FALLBACK_M4',reason=str(exc),choices={a:[] for a in ARMS})
                    for a in ARMS:rec['receipts'][a]=dict(status='FALLBACK_M4',reason=str(exc),seconds=rec['receipts'][a].get('seconds',0))
                rec['fit_calls']=engine.fit_count-count_before
                js(p/'RESULT.json',rec);checkpoint(p,['RESULT.json'],binding,'COMPLETE_COMPONENT_RESULT')
            fit_calls+=rec['fit_calls'];next_hid=rec['next_hid'];statuses.append(dict(context_id=idx,status=rec['status'],reason=rec.get('reason')))
            for rep in banks:banks[rep].extend(rec['banks'][rep])
            for a in ARMS:choices[a].extend(rec['choices'][a]);receipts[a].append(dict(context_id=idx,**rec['receipts'][a]))
            solver_seconds+=sum(rec['receipts'][r+'_joint'].get('seconds',0) for r in ('concat','common'))
        facts.update(component_status=statuses,fit_calls=fit_calls,solver_seconds=solver_seconds);saved={};outputs={};facts['outputs']=outputs
        for ai,a in enumerate(ARMS):
            guard('delivery');out=unit/'scenes'/c['scene']/'stages'/a;rep=a.split('_')[0]
            if complete(out,binding):
                m=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False));gs=json.loads((out/'GROUPS.json').read_text())['groups'];assert np.load(out/'SELECTED_HYPOTHESES.npz')['hypothesis_id'].tolist()==sorted(choices[a])
            else:m,gs=export(out,c,dict(d,next_version=d['next_version']+ai*c['kernel_count']),choices[a],banks[rep],receipts[a],scope,binding)
            saved[a]=(m,gs);outputs[a]=dict(path=str(out),groups=len(gs));done.append(a+'_mapping')
        after=geometry_fingerprint(d['asset']);assert before==after;assert sha(c['gaussians'])==c['input_files'][c['gaussians']]
        if not (unit/'GEOMETRY_AUDIT.json').exists():js(unit/'GEOMETRY_AUDIT.json',dict(original_count=c['kernel_count'],row_order_exact=True,unchanged_before_after=True,fields=after,source_sha256=c['input_files'][c['gaussians']],auxiliary_geometry_rendered=False))
        cams=sorted([x for x in json.loads(Path(c['cameras']).read_text())[c['scene']] if x['view'] in c['views']],key=lambda x:c['views'].index(x['view']));assert len(cams)==2;render=renderer(c)
        for a,(m,gs) in saved.items():
            out=Path(outputs[a]['path']);cp=out/'FULL_NATIVE_CHECKPOINT.json'
            if cp.exists():
                cr=json.loads(cp.read_text());assert cr['complete'] and cr['config_sha256']==binding;verify({str(out/k):v for k,v in cr['files'].items()});images=[v+'_FULL.png' for v in c['views']]
            else:
                if any((out/f).exists() for f in ['DISPLAY_COLORS.npz','DISPLAY_SOURCE.json']+[v+'_FULL.png' for v in c['views']]):raise RuntimeError('INCOMPLETE_NATIVE_PRESERVED')
                images=render_arm(out,c,d,m,gs,contexts,render,cams,guard,full_only=True);js(cp,dict(complete=True,config_sha256=binding,files={f:sha(out/f) for f in ['DISPLAY_COLORS.npz','DISPLAY_SOURCE.json']+images}))
            outputs[a]['full_images']=images;done.append(a+'_full_native')
        facts['delivery_gate']=True
        for a,(m,gs) in saved.items():
            out=Path(outputs[a]['path']);old=d['membership']['edge_id'];ids=m['edge_id']
            if not (out/'METRICS.json').exists():js(out/'METRICS.json',dict(assigned=int(np.sum(ids>=0)),unknown=int(np.sum(ids<0)),gained_assigned=int(np.sum((old<0)&(ids>=0))),lost_assigned=int(np.sum((old>=0)&(ids<0))),changed_rows=int(np.sum(ids!=old)),physical_identity_verified=False,overlap_pooling_run=False))
            if not (out/'GROUP_STATISTICS.json').exists():js(out/'GROUP_STATISTICS.json',dict(groups=enrich(d,gs,guard),support_is_proxy=True))
        refs=reference_views(c,d);diag=diagnostics(c,d,saved,contexts)
        comparison=unit/'scenes'/c['scene']/'REFERENCE_COMPARISON.json'
        if not comparison.exists():js(comparison,reference_comparisons(saved,{**refs,**saved}))
        diagnostic_saved={**saved,**refs};diagnostic_root=unit/'scenes'/c['scene']/'diagnostics'
        for case in diag['cases']:
            cp=diagnostic_root/(case['case_id']+'_CHECKPOINT.json')
            existing=[p for a in diagnostic_saved for p in (unit/'scenes'/c['scene']/'stages'/a/'diagnostics').glob(case['case_id']+'*.png')]
            if existing:
                if not cp.exists():raise RuntimeError('INCOMPLETE_DIAGNOSTIC_PRESERVED')
                cr=json.loads(cp.read_text());assert cr['complete'] and cr['config_sha256']==binding
                verify({str(unit/k):v for k,v in cr['images'].items()})
                assert sha(diagnostic_root/(case['case_id']+'_ROWS.npz'))==cr['rows_sha256']
        images=render_diagnostics(unit,c,d,diagnostic_saved,diag,render,cams,guard,binding)
        for a in saved:
            out=Path(outputs[a]['path']);all_images=outputs[a]['full_images']+images[a]
            if not (out/'IMAGES.json').exists():js(out/'IMAGES.json',dict(files=all_images,missing_cases=diag['missing'],actual_original_kernels=True,held_out=False))
            done.append(a+'_diagnostics')
        verify(c['source_files']);verify(c['helper_files']);facts['status']='complete' if all(x['status']=='COMPLETE' for x in statuses) else 'partial'
    except BaseException as exc:error=exc;facts.update(status='partial' if done else 'blocked',error=repr(exc),traceback=traceback.format_exc())
    finally:
        facts.update(fit_calls=fit_calls,completed=done,elapsed_seconds=time.monotonic()-lim.start,ended_utc=now(),actual_saved_pngs=[str(p.relative_to(unit)) for p in sorted((unit/'scenes').rglob('*.png'))])
        if not (unit/'RUN_RESULT.json').exists():js(unit/'RUN_RESULT.json',facts)
        lim.close()
    if error is not None:raise error

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();run(json.loads(Path(a.config).read_text()),a.config)
