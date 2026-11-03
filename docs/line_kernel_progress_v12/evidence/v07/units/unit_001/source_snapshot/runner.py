"""Parent-owned plain numerical runner; no subprocesses, no rendering auxiliary ink."""
from free_io import *
import argparse,traceback
import free_core as f
from free_delivery import deliver

def run(c,binding):
 U=Path(c['unit_root']);limits=Limits(c);stages=[];d=None;result=dict(scientific_verdict='PENDING_SAVED_IMAGE_ANALYSIS',experiments_run=False,completed_stages=stages,errors=[],full_views_complete=False)
 try:
  assert sha(c['decision_path'])==c['decision_sha256'];d=load(c,limits.guard);result['experiments_run']=True
  js(U/'READINESS.json',dict(rows=len(d['x']),valid_tangents=int(d['valid'].sum()),invalid_tangents_UNKNOWN=int((~d['valid']).sum()),input_files=c['input_files'],helper_files=c['helper_files'],all_original_fields=d['fingerprint'],legacy_groups_locked=False))
  # All original row IDs are retained; seed proposal limits do not cap assignment competition.
  field=f.Field(d['x'],d['t'],np.flatnonzero(d['valid']),lambda:limits.guard('initialization'))
  models,next_id,discovery=f.discover(field,{},0,512,lambda:limits.guard('initialization'));js(U/'INITIALIZATION.json',discovery)
  a=f.assign(d['x'],d['t'],d['valid'],models,lambda:limits.guard('science'))
  raw=U/'scenes'/c['scene']/'raw'/'STATIC';save_stage(raw,d,models,a,discovery['events'],next_id,binding,dict(promoted=False,all_rows_evaluated=True))
  models,a,events,next_id=f.validate_support(d['x'],d['half'],models,a,next_id,lambda:limits.guard('science'))
  if len(models)>704:raise RuntimeError('TOTAL_MODEL_CAP_AFTER_SPLIT')
  scope=dict(all_rows_evaluated=True,original_count=len(d['x']),model_discovery_complete=not discovery['truncated'],initialization=discovery,assignment_competitors='all finite segments within1p, no top-k truncation',physical_identity_verified=False,complete_cycle=0)
  stage='FREE_STATIC';save_stage(U/'scenes'/c['scene']/'stages'/stage,d,models,a,discovery['events']+events,next_id,binding,scope);stages.append(stage)
  for cycle in range(1,4):
   limits.guard('science');field.guard=lambda:limits.guard('science');updated,events=f.update_models(d['x'],d['half'],models,a,field,lambda:limits.guard('science'))
   unknown=np.flatnonzero(d['valid']&(a['edge_id']<0));uf=f.Field(d['x'],d['t'],unknown,lambda:limits.guard('science'));cap=min(64,704-len(updated));born={};birthlog=dict(cap=cap,events=[],truncated=False)
   if cap>0:born,next_id,birthlog=f.discover(uf,updated,next_id,cap,lambda:limits.guard('science'))
   updated.update(born);events+=birthlog['events'];aa=f.assign(d['x'],d['t'],d['valid'],updated,lambda:limits.guard('science'))
   raw=U/'scenes'/c['scene']/'raw'/('CYCLE_%d'%cycle);save_stage(raw,d,updated,aa,events,next_id,binding,dict(promoted=False,all_rows_evaluated=True,cycle=cycle))
   mm,aa,ee,next_id=f.validate_support(d['x'],d['half'],updated,aa,next_id,lambda:limits.guard('science'));events+=ee
   if len(mm)>704:raise RuntimeError('TOTAL_MODEL_CAP_AFTER_SPLIT')
   stage='FREE_ADAPTIVE_%d'%cycle;scope=dict(predecessor_stage=stages[-1],all_rows_evaluated=True,model_discovery_complete=False,model_cap=704,birth=birthlog,complete_cycle=cycle,assignment_competitors='ALL finite segments within1p',physical_identity_verified=False)
   save_stage(U/'scenes'/c['scene']/'stages'/stage,d,mm,aa,events,next_id,binding,scope);stages.append(stage);models,a=mm,aa
 except TimeoutError as exc:result['errors'].append(dict(type=type(exc).__name__,message=str(exc),incomplete_iteration_promoted=False))
 except Exception as exc:
  result['errors'].append(dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()));result['fatal']=True
 # Delivery always starts from cold-loadable accepted stages, never unsaved memory.
 if d is not None and stages:
  try:result.update(deliver(c,d,stages,binding,lambda:limits.guard('delivery')));result['full_views_complete']=True
  except Exception as exc:
   result['errors'].append(dict(phase='delivery',type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
   if not isinstance(exc,TimeoutError):result['fatal']=True
 result.update(completed_stages=list(stages),elapsed_seconds=limits.elapsed(),execution_state='completed' if len(stages)==4 and result['full_views_complete'] and not result['errors'] else 'partial',kernel_geometry_frozen=True,legacy_groups_locked=False,uses_training=False,uses_gpu=False)
 js(U/'RUN_RESULT.json',result);signal.setitimer(signal.ITIMER_REAL,0)
 return 1 if result.get('fatal') else 0

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();c=json.loads(Path(args.config).read_text());return run(c,sha(args.config))
if __name__=='__main__':raise SystemExit(main())
