"""Complete component model recovery. Partial banks never become competition."""
from runtime_io import *
from observation_runner import clean_resume
from coverage_control import prepare_banks as replay_control
from overlap_model import build_bank
from observation_model import build_extra_bank
from pair_model import fit_engine,fit_pair

def prepare_banks(c,d,contexts,lim,binding):
 n=c['control_contexts'];banks,bycontext,statuses,facts=replay_control(c,d,contexts[:n],lim,binding)
 assert len(banks)==c['expected_control_hypotheses']
 for bs in statuses:
  p=Path(c['unit'])/'scenes/scan24/control_replay'/('component_%05d'%bs['context_id'])/'REPLAY.json'
  bs['fallback_selections']=json.loads(p.read_text())['actual']
 facts['fit_calls']=0;facts['reused_models']=c['expected_selected_pairs'];facts['attempted_new_models']=0;facts['model_reproduction_failures']=[]
 unit=Path(c['unit']);engine=None;next_hid=max((h['hid'] for h in banks),default=-1)+1;timed_out=False
 names=d['candidates']['metric_names'].tolist()
 for ctx in contexts[n:]:
  k=ctx['context_id'];out=unit/'scenes/scan24/banks'/('component_%05d'%k);hs=[];records=[];status='BANK_COMPLETE';fits=0;model_count=0;failures=[]
  if clean_resume(out,binding):
   rec=json.loads((out/'BANK.json').read_text());hs=rec['hypotheses'];status=rec['status'];fits=rec['fit_calls'];model_count=rec['models'];failures=rec['model_failures']
  else:
   try:
    if ctx['status']!='READY':status=ctx['status']
    elif timed_out:status='NOT_RUN_BANK_DEADLINE'
    else:
     lim.guard('readiness');original,old_records=build_bank(d,ctx,lambda:lim.guard('readiness'));models=[]
     for h in original:h['context_id']=k
     for rid in sorted(ctx['overlap_record_ids'],key=lambda r:d['pairs'][r]):
      a,b=d['pairs'][rid];mp=unit/'scenes/scan24/models'/('pair_%d_%d'%(a,b))
      if clean_resume(mp,binding):m=json.loads((mp/'MODEL.json').read_text())
      else:
       lim.guard('readiness')
       if engine is None:engine=fit_engine(c['fit_source'],d)
       expected={name:float(v) for name,v in zip(names,d['candidates']['metrics'][rid])};expected['cost']=float(d['candidates']['cost'][rid])
       before=engine.fit_count
       try:m=fit_pair(engine,d,a,b,rid,expected,lambda:lim.guard('readiness'))
       except TimeoutError as exc:
        if 'PHASE_DEADLINE' not in str(exc):raise
        m=dict(status='NOT_RUN_BANK_DEADLINE',seed_pair=[a,b],record_id=rid,input_versions=[d['leaves'][a].version,d['leaves'][b].version],fit_calls=engine.fit_count-before,reason=str(exc))
       m['context_id']=k
       js(mp/'MODEL.json',m);checkpoint(mp,['MODEL.json'],binding,'PAIR_MODEL_ATTEMPT_CLOSED')
      fits+=m['fit_calls'];model_count+=1;models.append(m)
      if m['status']!='RECOVERED':failures.append(m)
      if m['status']=='NOT_RUN_BANK_DEADLINE':raise TimeoutError('PHASE_DEADLINE readiness after attempted fit')
     if failures:status='BLOCKED_REPRODUCTION';records=old_records
     else:
      extra,new_records=build_extra_bank(d,ctx,models,lambda:lim.guard('readiness'));hs=original+extra;records=old_records+new_records
      for i,h in enumerate(hs):h.update(hid=next_hid+i,context_id=k)
   except TimeoutError as exc:
    if 'PHASE_DEADLINE' not in str(exc):raise
    timed_out=True;status='NOT_RUN_BANK_DEADLINE';hs=[];records.append(dict(reason=str(exc),partial_bank_not_promoted=True))
   if status!='BANK_COMPLETE':hs=[]
   rec=dict(context_id=k,status=status,hypotheses=hs,fit_calls=fits,models=model_count,model_failures=failures,fallback_selections={'greedy':[],'joint':[]})
   js(out/'BANK.json',rec);js(out/'REJECTIONS.json',records);checkpoint(out,['BANK.json','REJECTIONS.json'],binding,'COMPLETE_OR_UNPROMOTED_COMPONENT')
  assert [h['hid'] for h in hs]==list(range(next_hid,next_hid+len(hs)))
  next_hid+=len(hs);banks.extend(hs);bycontext[k]=hs;statuses.append(dict(context_id=k,status=status,hypotheses=len(hs),fallback_selections={'greedy':[],'joint':[]}))
  facts['fit_calls']+=fits;facts['attempted_new_models']+=model_count;facts['model_reproduction_failures'].extend(failures)
  assert facts['fit_calls']<=c['model_fit']['maximum_attempts']
 facts['model_count']=facts['reused_models']+facts['attempted_new_models'];facts['recovered_models']=facts['model_count']-len(facts['model_reproduction_failures']);facts['coverage_components']=len(contexts)
 return banks,bycontext,statuses,facts
