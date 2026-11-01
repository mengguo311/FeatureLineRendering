"""Parent-owned unit003 computation. Complete checkpoint before any rendering."""
from free_io import *
import argparse,traceback
import free_core as f
import merge_core as m
from seed_coverage import load_seeds
from merge_delivery import deliver

FIELDS=('edge_id','alternatives','alternative_cost','s','segment','u','reason_code','eligible_models')

class MergeLimits(Limits):
 def guard(self,phase='delivery'):
  if phase=='control':
   if self.elapsed()>=min(240,self.seconds-600):raise TimeoutError('PHASE_DEADLINE control')
   return super().guard('science')
  return super().guard(phase)

def restore(c,d,guard):
 guard('readiness');pc=Path(c['predecessor_config']);old=json.loads(pc.read_text());assert sha(pc)==c['predecessor_config_sha256'];assert sha(old['decision_path'])==old['decision_sha256']
 path=Path(c['predecessor_stage']);models,a,line=cold_stage(path,c['predecessor_config_sha256'])
 with np.load(path/'MODELS.npz',allow_pickle=False) as z:
  ids=z['model_id'];off=z['offsets'];q=z['q_normalized'];assert ids.shape==(c['predecessor_model_count'],);assert np.issubdtype(ids.dtype,np.integer) and np.all(np.diff(ids)>0);assert off.shape==(len(ids)+1,) and np.issubdtype(off.dtype,np.integer);assert off[0]==0 and off[-1]==len(q) and np.all(np.diff(off)>=2);assert q.ndim==2 and q.shape[1]==3 and np.isfinite(q).all();assert float(z['p'])==d['p']
 assert np.array_equal(a['line_kernel_id'],np.arange(c['kernel_count']));assert np.array_equal(a['primitive_id'],d['asset']['primitive_id'])
 for k in FIELDS:assert len(a[k])==c['kernel_count'],k
 assert a['alternatives'].shape==(c['kernel_count'],2) and a['alternative_cost'].shape==(c['kernel_count'],2)
 assert set(np.unique(a['edge_id'][a['edge_id']>=0])).issubset(models);assert np.all(d['valid'][a['edge_id']>=0])
 for mid,q in models.items():guard('readiness');assert m.version(q)==line['model_versions'][str(mid)];assert f.geometry_ok(q)[0]
 assert line['next_id']==c['predecessor_next_id'] and line['next_id']>max(models,default=-1)
 return models,{k:a[k].copy() for k in FIELDS},line['next_id']

def save_models(path,models):
 ids=sorted(models);offset=[0];qq=[]
 for mid in ids:qq.append(models[mid]);offset.append(offset[-1]+len(models[mid]))
 nz(path,model_id=np.array(ids,np.int64),offsets=np.array(offset,np.int64),q_normalized=np.concatenate(qq) if qq else np.empty((0,3)))

def persist_trial(out,r,base,input_stage):
 out.mkdir(parents=True,exist_ok=True);names=[p.name for p in out.iterdir() if p.is_file()]
 for name,z in [('TEMPLATE',r['template']),('FITTED_Q',r['q'])]:
  if z is not None:nz(out/(name+'.npz'),q_normalized=z);names.append(name+'.npz')
 nz(out/'FIT_ROWS.npz',rows=r['fit_rows']);names.append('FIT_ROWS.npz')
 for name,a in [('RAW_DELTA',r['raw']),('VALIDATED_DELTA',r['assignment'])]:
  if a is not None:nz(out/(name+'.npz'),**m.delta(base,a));names.append(name+'.npz')
 if r['models'] is not None:save_models(out/'TRIAL_MODELS.npz',r['models']);names.append('TRIAL_MODELS.npz')
 meta={k:v for k,v in r.items() if k not in ['models','assignment','raw','template','q','fit_rows']};meta.update(input_stage=str(input_stage),input_checkpoint_sha256=sha(input_stage/'CHECKPOINT.json'),raw_competition_ran=r['raw'] is not None,delta_schema='Copy input MEMBERSHIP fields, replace changed_rows with delta arrays; includes raw alternatives/UNKNOWN; input immutable. Trial model IDs scoped to this trial unless committed.')
 js(out/'TRIAL.json',meta);names.append('TRIAL.json');js(out/'CHECKPOINT.json',dict(complete=True,files={n:sha(out/n) for n in names}))

def run(c,binding):
 U=Path(c['unit_root']);limits=MergeLimits(c);stages=[];d=None;accepted=[];attempted=set();attempts=0;search_complete=False;result=dict(scientific_verdict='PENDING_SAVED_IMAGE_ANALYSIS',experiments_run=False,completed_stages=stages,errors=[],full_views_complete=False)
 try:
  assert sha(c['decision_path'])==c['decision_sha256'];d=load(c,limits.guard);models,old_a,next_id=restore(c,d,limits.guard);d['seed_carriers']=load_seeds(c,limits.guard);result['experiments_run']=True
  js(U/'READINESS.json',dict(rows=len(d['x']),models=len(models),next_id=next_id,predecessor=str(c['predecessor_stage']),input_files=c['input_files'],helper_files=c['helper_files'],all_original_fields=d['fingerprint'],legacy_groups_locked=False))
  a=f.assign(d['x'],d['t'],d['valid'],models,lambda:limits.guard('control'));save_stage(U/'scenes'/c['scene']/'raw'/'NO_MERGE',d,models,a,[],next_id,binding,dict(promoted=False,all_rows_evaluated=True))
  models,a,ev,next_id=f.validate_support(d['x'],d['half'],models,a,next_id,lambda:limits.guard('control'));assert len(models)<=704
  scope=dict(all_rows_evaluated=True,assignment_competitors='ALL current finite segments within1p',model_discovery_complete=False,physical_identity_verified=False,predecessor_stage=c['predecessor_stage'],control='one fresh assignment/support pass, not historical replay')
  base=U/'scenes'/c['scene']/'stages';save_stage(base/'NO_MERGE',d,models,a,ev,next_id,binding,scope);stages.append('NO_MERGE');current='NO_MERGE'
  js(U/'CONTROL_ENERGY.json',m.energy(d,models,a,lambda:limits.guard('science')))
  from coverage_delivery import compare
  js(U/'CONTROL_VS_PREDECESSOR.json',compare(old_a['edge_id'],a['edge_id']))
  generation=0;need_enumerate=True;candidates=[]
  while True:
   limits.guard('science')
   if need_enumerate:
    candidates,records=m.enumerate_candidates(models,lambda:limits.guard('science'));out=U/'candidates'/('GEN_%03d'%generation);out.mkdir(parents=True);nz(out/'ALL_ENDPOINT_PAIRS.npz',**records)
    js(out/'ELIGIBLE.json',dict(complete=True,source_stage=current,source_checkpoint_sha256=sha(base/current/'CHECKPOINT.json'),candidates=candidates,reason_codes={'0':'eligible','1':'gap','2':'tangent','3':'connector'},evaluated_port_pairs=len(records['a']),no_topk=True))
    watch=np.flatnonzero((records['a']==55)&(records['b']==441));js(out/'WATCH_55_441.json',dict(models_present=[i for i in [55,441] if i in models],records=[{k:records[k][j].item() for k in records} for j in watch],forced_eligibility=False))
    generation+=1;need_enumerate=False
   untried=[p for p in candidates if m.key(p) not in attempted]
   if not untried:search_complete=True;break
   if attempts>=64:break
   p=untried[0];attempted.add(m.key(p));index=attempts;attempts+=1;trialpath=U/'trials'/('TRIAL_%03d'%index);trialpath.mkdir(parents=True)
   js(trialpath/'START.json',dict(proposal=p,input_stage=str(base/current),input_checkpoint_sha256=sha(base/current/'CHECKPOINT.json'),tentative_model_id=next_id,attempt_index=index))
   def progress(phase,r):
    if phase=='fitted':
     nz(trialpath/'PROGRESS_TEMPLATE.npz',q_normalized=r['template']);nz(trialpath/'PROGRESS_FITTED_Q.npz',q_normalized=r['q'])
    elif phase=='raw':nz(trialpath/'PROGRESS_RAW_DELTA.npz',**m.delta(a,r['raw']))
    elif phase=='validated':
     nz(trialpath/'PROGRESS_VALIDATED_DELTA.npz',**m.delta(a,r['assignment']));save_models(trialpath/'PROGRESS_VALIDATED_MODELS.npz',r['models'])
   r=m.trial(d,models,a,next_id,p,lambda:limits.guard('science'),progress);persist_trial(trialpath,r,a,base/current)
   if r['accepted']:
    stage='MERGE_%03d'%(len(accepted)+1);event=dict(operation='model_merge',inputs=[p['a'],p['b']],input_versions=[p['version_a'],p['version_b']],proposal_ports=[p['pa'],p['pb']],new_model=r['model_id'],surviving_children=r['surviving_children'],trial=str(trialpath.relative_to(U)),input_stage=current,energy_before=r['before'],energy_after=r['after'])
    save_stage(base/stage,d,r['models'],r['assignment'],[event]+r['events'],r['next_id'],binding,dict(scope,predecessor_stage=current,accepted_trial=index))
    stages.append(stage);accepted.append(event);models=r['models'];a=r['assignment'];next_id=r['next_id'];current=stage;need_enumerate=True
  js(U/'SEARCH_RESULT.json',dict(attempts=attempts,accepted=len(accepted),search_complete_for_current_version_pairs=search_complete,proposal_search_capped=not search_complete,attempted_keys=[list(k) for k in sorted(attempted)],unattempted=[p for p in candidates if m.key(p) not in attempted],history=accepted))
  save_stage(base/'MERGE_FINAL',d,models,a,[],next_id,binding,dict(scope,predecessor_stage=current,search_complete=search_complete,attempts=attempts,accepted=len(accepted)));stages.append('MERGE_FINAL')
 except TimeoutError as exc:result['errors'].append(dict(type=type(exc).__name__,message=str(exc),incomplete_trial_promoted=False))
 except Exception as exc:result['fatal']=True;result['errors'].append(dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
 if not (U/'MERGE_HISTORY.json').exists():js(U/'MERGE_HISTORY.json',dict(attempts_started=attempts,accepted=accepted,search_complete=search_complete,last_saved_stage=stages[-1] if stages else None))
 if d is not None and stages:
  try:result.update(deliver(c,d,stages,binding,lambda:limits.guard('delivery')));result['full_views_complete']=True
  except Exception as exc:
   result['errors'].append(dict(phase='delivery',type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
   if not isinstance(exc,TimeoutError):result['fatal']=True
 result.update(completed_stages=stages,attempts_started=attempts,accepted_merges=len(accepted),elapsed_seconds=limits.elapsed(),execution_state='completed' if 'MERGE_FINAL' in stages and result['full_views_complete'] and not result['errors'] else 'partial',kernel_geometry_frozen=True,legacy_groups_locked=False,uses_gpu=False,uses_training=False)
 js(U/'RUN_RESULT.json',result);signal.setitimer(signal.ITIMER_REAL,0);return 1 if result.get('fatal') else 0

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();c=json.loads(Path(args.config).read_text());return run(c,sha(args.config))
if __name__=='__main__':raise SystemExit(main())
