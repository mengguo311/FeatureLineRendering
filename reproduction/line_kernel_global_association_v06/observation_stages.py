"""Replay closed unit005 models and controls; never fits or generates candidates."""
from runtime_io import *
from pair_runner import clean_resume
from pair_model import build_extra_bank as legacy_bank,select_greedy,select_joint
from pair_delivery import membership_for
from observation_model import build_extra_bank

def load_models(c,d,contexts,unit,binding):
    prior=Path(c['prior_unit']);models={};pairs={rid:ctx['context_id'] for ctx in contexts for rid in ctx['overlap_record_ids']}
    assert len(pairs)==c['expected_selected_pairs']
    names=d['candidates']['metric_names'].tolist()
    for rid in sorted(pairs,key=lambda r:d['pairs'][r]):
        a,b=d['pairs'][rid];src=prior/'scenes/scan24/models'/('pair_%d_%d'%(a,b));verify_checkpoint(src,c['previous_config_sha256'])
        m=json.loads((src/'MODEL.json').read_text());assert m['status']=='RECOVERED' and m['seed_pair']==[a,b] and m['record_id']==rid and m['context_id']==pairs[rid]
        assert m['input_versions']==[d['leaves'][a].version,d['leaves'][b].version] and m['anchor'] in (a,b)
        assert m['model_key']==[1,a,b] and d['candidates']['operation'][rid]=='overlap'
        q=np.asarray(m['q']);assert q.ndim==2 and q.shape[1]==3 and 2<=len(q)<=128 and np.isfinite(q).all()
        for name,v in zip(names,d['candidates']['metrics'][rid]):assert abs(m['metrics'][name]-float(v))<=1e-10,'SAVED_MODEL_METRIC_BINDING'
        assert abs(m['cost']-float(d['candidates']['cost'][rid]))<=1e-10
        out=unit/'scenes/scan24/models'/src.name
        if clean_resume(out,binding):assert json.loads((out/'MODEL.json').read_text())==m
        else:
            js(out/'MODEL.json',m);js(out/'SOURCE.json',dict(path=str(src/'MODEL.json'),sha256=sha(src/'MODEL.json'),historical_fit_calls=m['fit_calls'],current_fit_calls=0))
            checkpoint(out,['MODEL.json','SOURCE.json'],binding,'SAVED_PAIR_MODEL_RELOADED')
        models[rid]=m
    return models

def prepare_banks(c,d,contexts,lim,binding):
    unit=Path(c['unit']);prior=Path(c['prior_unit']);base=Path(c['base_bank_unit']);oldby={};priorby={};original=[];historical=[]
    for ctx in contexts:
        k=ctx['context_id'];name='component_%05d'%k
        p=base/'scenes/scan24/banks'/name;verify_checkpoint(p,c['base_bank_config_sha256']);oldby[k]=json.loads((p/'BANK.json').read_text())['hypotheses'];original.extend(oldby[k])
        p=prior/'scenes/scan24/banks'/name;verify_checkpoint(p,c['previous_config_sha256']);priorby[k]=json.loads((p/'BANK.json').read_text())['hypotheses'];historical.extend(priorby[k])
    assert len(original)==c['expected_old_hypotheses'] and len(historical)==c['expected_control_hypotheses']
    models=load_models(c,d,contexts,unit,binding);control_seconds=0.;control_times={};control_choices={a:[] for a in ('greedy','joint')};replayed=[];next_hid=len(original)
    for ctx in contexts:
        lim.guard('readiness');k=ctx['context_id'];out=unit/'scenes/scan24/control_replay'/('component_%05d'%k)
        if clean_resume(out,binding):rec=json.loads((out/'REPLAY.json').read_text());hs=json.loads((out/'BANK.json').read_text())
        else:
            extra,rejections=legacy_bank(d,ctx,[models[r] for r in ctx['overlap_record_ids']],lambda:lim.guard('readiness'))
            for i,h in enumerate(extra):h.update(hid=next_hid+i,context_id=k)
            hs=oldby[k]+extra;expected_rej=json.loads((prior/'scenes/scan24/banks'/('component_%05d'%k)/'REJECTIONS.json').read_text())
            bank_exact=hs==priorby[k] and rejections==expected_rej
            ids={h['hid'] for h in hs};expected={a:sorted(ids&set(np.load(Path(p)/'SELECTED_HYPOTHESES.npz',allow_pickle=False)['hypothesis_id'].tolist())) for a,p in c['previous_arms'].items()}
            remaining=min(c['solver']['per_context_seconds'],c['solver']['total_seconds']-control_seconds,lim.seconds-600-(time.monotonic()-lim.start))
            chosen,solver=select_joint(hs,remaining,lambda:lim.guard('readiness'))
            actual=dict(greedy=select_greedy(hs),joint=chosen)
            rec=dict(status='EXACT_CONTROL' if bank_exact and actual==expected and solver['status']=='optimal' else 'CONTROL_MISMATCH',bank_and_rejections_exact=bank_exact,actual=actual,expected=expected,solver=solver)
            js(out/'BANK.json',hs);js(out/'REJECTIONS.json',rejections);js(out/'REPLAY.json',rec)
            checkpoint(out,['BANK.json','REJECTIONS.json','REPLAY.json'],binding,'UNIT005_CONTROL_REPLAY')
        assert rec['status']=='EXACT_CONTROL','CONTROL_MISMATCH_PRESERVED'
        next_hid+=len(hs)-len(oldby[k]);replayed.extend(hs);control_seconds+=rec['solver'].get('seconds',0.);control_times[str(k)]=rec['solver'].get('seconds',0.)
        for a in control_choices:control_choices[a].extend(rec['actual'][a])
    assert sorted(h['hid'] for h in replayed)==list(range(c['expected_control_hypotheses']))
    full=unit/'scenes/scan24/control_replay/full'
    if clean_resume(full,binding):assert json.loads((full/'REPLAY.json').read_text())['exact']
    else:
        checks={}
        for a in control_choices:
            p=Path(c['previous_arms'][a]);verify_checkpoint(p,c['previous_config_sha256']);prior_groups=json.loads((p/'GROUPS.json').read_text())['groups']
            start=min((g['version'] for g in prior_groups),default=d['next_version'])
            chosen=[h for h in replayed if h['hid'] in set(control_choices[a])];m,gs,lin=membership_for(dict(d,next_version=start),chosen,replayed)
            with np.load(p/'MEMBERSHIP.npz',allow_pickle=False) as expected:
                assert set(m)==set(expected.files),'CONTROL_MAPPING_SCHEMA'
                for key in m:np.testing.assert_array_equal(m[key],expected[key],err_msg='CONTROL_MAPPING '+a+' '+key)
            assert gs==prior_groups,'CONTROL_GROUPS_MISMATCH'
            checks[a]=dict(all_membership_fields_exact=True,groups_exact=True,rows=len(m['edge_id']),source_membership_sha256=sha(p/'MEMBERSHIP.npz'))
        js(full/'REPLAY.json',dict(exact=True,arms=checks));checkpoint(full,['REPLAY.json'],binding,'UNIT005_FULL_MAPPING_REPLAY')
    banks=list(original);bycontext={};statuses=[];next_hid=len(original)
    for ctx in contexts:
        k=ctx['context_id'];out=unit/'scenes/scan24/banks'/('component_%05d'%k)
        if clean_resume(out,binding):hs=json.loads((out/'BANK.json').read_text())['hypotheses']
        else:
            extra,records=build_extra_bank(d,ctx,[models[r] for r in ctx['overlap_record_ids']],lambda:lim.guard('readiness'))
            for i,h in enumerate(extra):h.update(hid=next_hid+i,context_id=k)
            hs=oldby[k]+extra
            js(out/'BANK.json',dict(status='BANK_COMPLETE',context_id=k,hypotheses=hs,original_hypothesis_ids=[h['hid'] for h in oldby[k]],domain_witness='all_original_kernel_centers'))
            js(out/'REJECTIONS.json',records);checkpoint(out,['BANK.json','REJECTIONS.json'],binding,'OBSERVATION_DOMAIN_BANK_COMPLETE')
        extra=[h for h in hs if h['hid']>=len(original)];assert [h['hid'] for h in extra]==list(range(next_hid,next_hid+len(extra)))
        assert [h for h in hs if h['hid']<len(original)]==oldby[k]
        next_hid+=len(extra);banks.extend(extra);bycontext[k]=hs;statuses.append(dict(context_id=k,status='BANK_COMPLETE',hypotheses=len(hs),new_hypotheses=len(extra),fallback_selections={'greedy':[],'joint':[]}))
    return banks,bycontext,statuses,dict(fit_calls=0,model_count=len(models),recovered_models=len(models),models_reloaded=len(models),control_solver_seconds=control_seconds,control_seconds_by_context=control_times,model_reproduction_failures=[],control_replay_exact=True)
