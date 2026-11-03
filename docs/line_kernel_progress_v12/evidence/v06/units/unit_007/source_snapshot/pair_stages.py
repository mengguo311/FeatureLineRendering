"""Durable shared model bank and immutable unit004 control replay."""
from runtime_io import *
from overlap_runner import clean_resume
from overlap_model import select_greedy as old_greedy,select_joint as old_joint
from pair_model import fit_engine,fit_pair,build_extra_bank

def prepare_banks(c,d,contexts,lim,binding):
    unit=Path(c['unit']);oldby={};oldall=[];controls={};solver_seconds=0.
    prior=Path(c['prior_unit']);prior_binding=c['previous_config_sha256']
    for ctx in contexts:
        k=ctx['context_id'];p=prior/'scenes/scan24/banks'/('component_%05d'%k);verify_checkpoint(p,prior_binding)
        rec=json.loads((p/'BANK.json').read_text());assert rec['status']=='BANK_COMPLETE';oldby[k]=rec['hypotheses'];oldall.extend(rec['hypotheses'])
    assert len(oldall)==c['expected_old_hypotheses'];assert sorted(h['hid'] for h in oldall)==list(range(len(oldall)))
    # Replay both selectors on the original bank; no fitting here.
    for ctx in contexts:
        k=ctx['context_id'];hs=oldby[k];ids={h['hid'] for h in hs};out=unit/'scenes/scan24/control_replay'/('component_%05d'%k)
        if clean_resume(out,binding):replay=json.loads((out/'REPLAY.json').read_text())
        else:
            expected={arm:sorted(ids&set(np.load(str(Path(path)/'SELECTED_HYPOTHESES.npz'),allow_pickle=False)['hypothesis_id'].tolist())) for arm,path in c['previous_arms'].items()}
            budget=min(c['solver']['per_context_seconds'],c['solver']['total_seconds']-solver_seconds,lim.seconds-600-(time.monotonic()-lim.start))
            selected,receipt=old_joint(hs,budget,lambda:lim.guard('selection'))
            actual=dict(greedy=old_greedy(hs),joint=selected);ok=receipt['status']=='optimal' and actual==expected
            replay=dict(status='EXACT_CONTROL' if ok else 'CONTROL_MISMATCH',expected=expected,actual=actual,solver=receipt)
            js(out/'REPLAY.json',replay);checkpoint(out,['REPLAY.json'],binding,'CONTROL_REPLAY_COMPLETE')
        solver_seconds+=replay['solver'].get('seconds',0.);controls[k]=replay
    models={};engine=None;fit_calls=0;timed_out=False;pair_ctx={rid:ctx['context_id'] for ctx in contexts for rid in ctx['overlap_record_ids']}
    assert len(pair_ctx)==c['expected_selected_pairs'];mi=[str(x) for x in d['candidates']['metric_names']]
    for rid in sorted(pair_ctx,key=lambda r:d['pairs'][r]):
        a,b=d['pairs'][rid];k=pair_ctx[rid];out=unit/'scenes/scan24/models'/('pair_%d_%d'%(a,b))
        if clean_resume(out,binding):model=json.loads((out/'MODEL.json').read_text())
        else:
            if controls[k]['status']!='EXACT_CONTROL':model=dict(status='NOT_RUN_CONTROL_MISMATCH',seed_pair=[a,b],record_id=rid,fit_calls=0)
            elif timed_out:model=dict(status='NOT_RUN_BANK_DEADLINE',seed_pair=[a,b],record_id=rid,fit_calls=0)
            else:
                before_count=engine.fit_count if engine is not None else 0
                try:
                    lim.guard('readiness')
                    if engine is None:engine=fit_engine(c['fit_source'],d)
                    expected={name:float(v) for name,v in zip(mi,d['candidates']['metrics'][rid])};expected['cost']=float(d['candidates']['cost'][rid])
                    model=fit_pair(engine,d,a,b,rid,expected,lambda:lim.guard('readiness'))
                except TimeoutError as exc:
                    if 'PHASE_DEADLINE' not in str(exc):raise
                    timed_out=True;model=dict(status='NOT_RUN_BANK_DEADLINE',seed_pair=[a,b],record_id=rid,fit_calls=(engine.fit_count if engine is not None else 0)-before_count,reason=str(exc))
            model['context_id']=k;js(out/'MODEL.json',model);checkpoint(out,['MODEL.json'],binding,'PAIR_MODEL_ATTEMPT_CLOSED')
        fit_calls+=model['fit_calls'];models[rid]=model
    assert fit_calls<=c['expected_selected_pairs'];banks=list(oldall);bycontext={};statuses=[];next_hid=len(oldall)
    for ctx in contexts:
        k=ctx['context_id'];out=unit/'scenes/scan24/banks'/('component_%05d'%k)
        if clean_resume(out,binding):saved=json.loads((out/'BANK.json').read_text());hs=saved['hypotheses'];status=saved['status']
        else:
            ms=[models[r] for r in ctx['overlap_record_ids']];extra=[];records=[];status='BANK_COMPLETE'
            if controls[k]['status']!='EXACT_CONTROL' or any(m['status']!='RECOVERED' for m in ms):status='BLOCKED_REPRODUCTION'
            else:
                try:extra,records=build_extra_bank(d,ctx,ms,lambda:lim.guard('readiness'))
                except TimeoutError as exc:
                    if 'PHASE_DEADLINE' not in str(exc):raise
                    status='NOT_RUN_BANK_DEADLINE';extra=[];records=[dict(reason=str(exc),partial_bank_not_promoted=True)]
            for i,h in enumerate(extra):h['hid']=next_hid+i;h['context_id']=k
            hs=oldby[k]+extra
            js(out/'BANK.json',dict(context_id=k,status=status,hypotheses=hs,original_hypothesis_ids=[h['hid'] for h in oldby[k]],fallback_selections=controls[k]['expected']));js(out/'REJECTIONS.json',records)
            checkpoint(out,['BANK.json','REJECTIONS.json'],binding,'AUGMENTED_BANK_OR_BLOCKED_COMPONENT')
        originals=[h for h in hs if h['hid']<len(oldall)];assert originals==oldby[k],'OLD_HYPOTHESES_CHANGED'
        extra=[h for h in hs if h['hid']>=len(oldall)];assert [h['hid'] for h in extra]==list(range(next_hid,next_hid+len(extra)))
        next_hid+=len(extra);banks.extend(extra);bycontext[k]=hs;statuses.append(dict(context_id=k,status=status,hypotheses=len(hs),new_hypotheses=len(extra),fallback_selections=controls[k]['expected']))
    return banks,bycontext,statuses,dict(fit_calls=fit_calls,model_count=len(models),recovered_models=sum(m['status']=='RECOVERED' for m in models.values()),control_solver_seconds=solver_seconds,control_seconds_by_context={str(k):v['solver'].get('seconds',0.) for k,v in controls.items()},model_reproduction_failures=[m for m in models.values() if m['status']!='RECOVERED'])
