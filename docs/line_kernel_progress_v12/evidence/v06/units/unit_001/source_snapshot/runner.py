"""Parent-owned plain numerical runner. No subprocess, fit, training or new candidates."""
from runtime_io import *
from adapter import load,select,local_validator
from port_paths import greedy,joint,PathOracle
from delivery import export_arm,geometry_fingerprint,render_arm,enrich_groups
import argparse,traceback

def run(c,config_path):
    unit=Path(c['unit']);binding=sha(config_path);lim=Limits(c);completed=[];facts=dict(status='partial',completed=completed,parent_exit_authoritative=True,config_sha256=binding,science_claim='UNASSESSED',started_utc=now());exit_error=None
    try:
        if (unit/'RUN_RESULT.json').exists():raise RuntimeError('CLOSED_RUN_EXISTS_NO_OVERWRITE')
        d=load(c,lim.guard);before=geometry_fingerprint(d['asset'])
        for v in d['asset'].values():v.flags.writeable=False
        seeds,contexts=select(c,d);lim.guard('readiness')
        prep=unit/'scenes/scan24/readiness';prep.mkdir(parents=True,exist_ok=True)
        selection=dict(seeds=[dict(label=k,carriers=v) for k,v in seeds],contexts=contexts,closure='Recursive closure of all incident saved records; no competitor trimming',candidate_caps_reference=c['candidate_metrics'],ambiguous_pairs=len(d['ambiguous']),eligible_endpoint_edges=len(d['edges']),successful_endpoint_edges=len(d['all_endpoint']),source_rows=len(d['asset']['means']),scope_status='READY' if any(x['status']=='READY' for x in contexts) else 'NO_BOUNDED_COMPLETE_CONTEXT')
        if (prep/'CHECKPOINT.json').exists():
            verify_checkpoint(prep,binding);assert json.loads((prep/'SELECTION.json').read_text())==selection
        else:
            if any(prep.iterdir()):raise RuntimeError('INCOMPLETE_READINESS_PRESERVED')
            js(prep/'SELECTION.json',selection)
            nz(prep/'CANDIDATES.npz',**d['candidates'])
            nz(prep/'ORDERED_CANDIDATES.npz',**d['ordered'])
            nz(prep/'AMBIGUOUS_PAIRS.npz',pairs=np.asarray(sorted(d['ambiguous']),np.int64).reshape(-1,2))
            js(prep/'PROVENANCE.json',dict(inputs=c['input_files'],helpers=c['helper_files'],source_files=c['source_files'],no_refit=True,new_candidate_generation=False,primitive_id='old source parent, never ground truth'))
            checkpoint(prep,['SELECTION.json','CANDIDATES.npz','ORDERED_CANDIDATES.npz','AMBIGUOUS_PAIRS.npz','PROVENANCE.json'],binding,'READINESS_COMPLETE')
        completed.append('readiness');print('READINESS_COMPLETE',selection['scope_status'],flush=True)
        solver_seconds=0;outputs={};saved={};facts['outputs']=outputs
        for arm in ('greedy','joint'):
            out=unit/'scenes/scan24/stages'/arm
            oracle=PathOracle(d['leaves'],d['representatives']['x']/c['p'],d['representatives']['t'],local_validator(d,c['p']),lambda:lim.guard('selection'))
            if (out/'CHECKPOINT.json').exists():
                verify_checkpoint(out,binding);m=dict(np.load(out/'MEMBERSHIP.npz',allow_pickle=False));gs=json.loads((out/'GROUPS.json').read_text())['groups'];rec=json.loads((out/'SOLVER.json').read_text());selected=np.load(out/'SELECTED_LINKS.npz')['record_index'].tolist()
            else:
                if out.exists() and any(out.iterdir()):raise RuntimeError('INCOMPLETE_ARM_PRESERVED '+arm)
                selected=[];rec=[]
                for ctx in contexts:
                    if ctx['status']!='READY':rec.append(dict(context_id=ctx['context_id'],status=ctx['status']));continue
                    try:
                        lim.guard('selection');scope=set(ctx['eligible_edge_ids']);edges=[e for e in d['edges'] if e.eid in scope]
                        if arm=='greedy':chosen,receipt=greedy(edges,oracle,lambda:lim.guard('selection'))
                        else:
                            budget=min(c['solver']['per_context_seconds'],c['solver']['total_seconds']-solver_seconds,lim.seconds-600-(time.monotonic()-lim.start))
                            if budget<=0:raise TimeoutError('SOLVER_TOTAL_BUDGET')
                            chosen,receipt=joint(edges,oracle,budget,lambda:lim.guard('selection'),c['solver']['max_cut_rounds']);solver_seconds+=receipt['seconds']
                        receipt['context_id']=ctx['context_id'];rec.append(receipt);selected.extend(chosen)
                    except TimeoutError as exc:
                        rec.append(dict(context_id=ctx['context_id'],status='NOT_RUN_DEADLINE',reason=str(exc)))
                        # Do not promote interrupted in-memory prefixes; earlier complete contexts survive.
                oracle.guard=lambda:lim.guard('delivery')
                m,gs=export_arm(out,c,d,sorted(selected),oracle,rec,selection,binding)
            saved[arm]=(m,gs);outputs[arm]=dict(path=str(out),selected_links=len(selected),paths=len(gs),solver=rec)
            completed.append(arm+'_mapping');print('MAPPING_COMPLETE',arm,flush=True)
        # Both complete mappings now durable. Rendering failures cannot destroy them.
        after=geometry_fingerprint(d['asset']);assert before==after,'GEOMETRY_MUTATION'
        audit=dict(original_count=c['kernel_count'],row_order_exact=True,fields=after,unchanged_before_after=True,source_sha256=c['input_files'][c['gaussians']],source_hash_after=sha(c['gaussians']),geometry_never_exported_as_fitted_model=True)
        assert audit['source_sha256']==audit['source_hash_after']
        if not (unit/'GEOMETRY_AUDIT.json').exists():js(unit/'GEOMETRY_AUDIT.json',audit)
        cams_all=json.loads(Path(c['cameras']).read_text())['scan24'];cams=[v for v in cams_all if v['view'] in c['views']];assert len(cams)==2
        cams=sorted(cams,key=lambda x:c['views'].index(x['view']));render=renderer(c)
        # Full native views of BOTH arms precede any local diagnostics.
        for arm,(m,gs) in saved.items():
            out=Path(outputs[arm]['path']);images=render_arm(out,c,d,m,gs,contexts,render,cams,lambda:lim.guard('delivery'),full_only=True)
            fullcp=out/'FULL_NATIVE_CHECKPOINT.json'
            if fullcp.exists():verify({str(out/k):v for k,v in json.loads(fullcp.read_text())['files'].items()})
            else:js(fullcp,dict(complete=True,config_sha256=binding,files={p:sha(out/p) for p in ['DISPLAY_COLORS.npz','DISPLAY_SOURCE.json']+images}))
            outputs[arm]['full_images']=images;completed.append(arm+'_full_native')
        facts['delivery_gate']=True
        for arm,(m,gs) in saved.items():
            out=Path(outputs[arm]['path'])
            enriched=enrich_groups(d,gs,lambda:lim.guard('delivery'))
            if not (out/'GROUP_STATISTICS.json').exists():js(out/'GROUP_STATISTICS.json',dict(groups=enriched,counts_are_not_accuracy=True))
            images=render_arm(out,c,d,m,gs,contexts,render,cams,lambda:lim.guard('delivery'))
            outputs[arm]['images']=images;completed.append(arm+'_native_images')
            metrics=dict(assigned=int(np.sum(m['edge_id']>=0)),unknown=int(np.sum(m['edge_id']<0)),changed_rows=int(np.sum(m['edge_id']!=d['membership']['edge_id'])),lost_assigned=int(np.sum((d['membership']['edge_id']>=0)&(m['edge_id']<0))),composite_paths=len(gs),physical_identity_verified=False,duplicate_pooling_run=False,holdout=False)
            if not (out/'METRICS.json').exists():js(out/'METRICS.json',metrics)
            if not (out/'NATIVE_CHECKPOINT.json').exists():js(out/'NATIVE_CHECKPOINT.json',dict(complete=True,config_sha256=binding,files={p:sha(out/p) for p in ['DISPLAY_COLORS.npz','DISPLAY_SOURCE.json','IMAGES.json','METRICS.json','GROUP_STATISTICS.json']+images}))
        verify(c['helper_files']);verify(c['source_files'])
        facts.update(status='complete' if any(ctx['status']=='READY' for ctx in contexts) and all(r.get('status') in ('greedy_complete','optimal','no_edges','NOT_RUN_OVERSIZE') for a in outputs.values() for r in a['solver']) else 'partial',scope_status=selection['scope_status'],outputs=outputs,solver_seconds=solver_seconds,delivery_gate=True,scientific_verdict='PARTIAL_PENDING_VISUAL_REVIEW')
    except BaseException as exc:
        facts.update(status='partial' if completed else 'blocked',error=repr(exc),traceback=traceback.format_exc());exit_error=exc
    finally:
        facts.update(completed=completed,ended_utc=now(),elapsed_seconds=time.monotonic()-lim.start,actual_saved_pngs=[str(p.relative_to(unit)) for p in sorted((unit/'scenes').rglob('*.png'))],fit_calls=0,new_candidates=0)
        if not (unit/'RUN_RESULT.json').exists():js(unit/'RUN_RESULT.json',facts)
        lim.close()
    if exit_error is not None:raise exit_error

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();config=json.loads(Path(args.config).read_text());run(config,args.config)
