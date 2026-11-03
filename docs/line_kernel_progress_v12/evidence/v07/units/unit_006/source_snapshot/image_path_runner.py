"""Parent-owned unit006 graph birth, no subprocesses or producer execution."""
from free_io import *
import argparse,traceback
import free_core as f
import merge_core as m
import graph_birth_core as g
from overlap_runner import restore,FIELDS,persist_trial,save_models
from seed_coverage import load_seeds
from image_path_delivery import deliver
import image_path_core as e

class GraphLimits(Limits):
 def guard(self,phase='delivery'):
  if phase=='initialization':
   if self.elapsed()>=min(420,self.seconds-600):raise TimeoutError('PHASE_DEADLINE initialization')
   return super().guard('science')
  return super().guard(phase)

def run(c,binding):
 U=Path(c['unit_root']);limits=GraphLimits(c);stages=[];d=None;accepted=[];attempts=0;bank_complete=False;search_complete=False;paths=[];result=dict(scientific_verdict='PENDING_SAVED_IMAGE_ANALYSIS',experiments_run=False,completed_stages=stages,errors=[],full_views_complete=False)
 try:
  if c.get('latest_parent_launch_jst') and time.time()>datetime.datetime.fromisoformat(c['latest_parent_launch_jst']).timestamp():raise RuntimeError('MISSED_LATEST_PARENT_LAUNCH_NOT_RUN')
  assert sha(c['decision_path'])==c['decision_sha256'];d=load(c,limits.guard);models,a,next_id=restore(c,d,limits.guard);d['seed_carriers']=load_seeds(c,limits.guard);result['experiments_run']=True
  js(U/'READINESS.json',dict(rows=len(d['x']),models=len(models),next_id=next_id,predecessor=c['predecessor_stage'],input_files=c['input_files'],helper_files=c['helper_files'],all_original_fields=d['fingerprint'],legacy_groups_locked=False))
  scope=dict(all_rows_evaluated=True,assignment_competitors='ALL current finite segments within1p',model_discovery_complete=False,physical_identity_verified=False,predecessor_stage=c['predecessor_stage'],control='exact saved predecessor; no extra competition/support pass')
  base=U/'scenes'/c['scene']/'stages';save_stage(base/'NO_BIRTH',d,models,a,[],next_id,binding,scope);stages.append('NO_BIRTH');current='NO_BIRTH';js(U/'CONTROL_ENERGY.json',m.energy(d,models,a,lambda:limits.guard('science')))
  cg=lambda:limits.guard('initialization');out=U/'graph';out.mkdir();oldgraph=Path(c['saved_graph'])
  with np.load(oldgraph/'MODES.npz',allow_pickle=False) as zf:z={k:zf[k] for k in zf.files}
  with np.load(oldgraph/'GRAPH.npz',allow_pickle=False) as af:graph={k:af[k] for k in af.files}
  assert len(z['position'])==c['expected_modes'] and len(graph['source'])==c['expected_edges']
  meta=json.loads((oldgraph/'SEED_SELECTION.json').read_text());seeds=[r['mode'] for r in meta['selected']];assert len(seeds)==c['expected_seeds']
  oldpaths,oldreceipts=g.propose(z,graph,seeds,cg);saved=json.loads((oldgraph/'PATHS.json').read_text());assert oldreceipts==saved['seed_receipts'],'CONTROL_SEARCH_RECEIPT_MISMATCH'
  assert [{k:v for k,v in x.items() if k!='q'} for x in oldpaths]==[{k:v for k,v in x.items() if k!='candidate_id'} for x in saved['paths']],'CONTROL_PATH_MISMATCH'
  js(out/'CONTROL_REPLAY.json',dict(exact=True,source=str(oldgraph),source_checkpoint_sha256=sha(oldgraph/'CHECKPOINT.json'),control_fitting_rerun=False))
  status,supported=e.evidence(c,z,graph,cg);nz(out/'IMAGE_EVIDENCE.npz',source=graph['source'],target=graph['target'],view_status=status,supported=supported,old_weight=graph['weight'],new_weight=graph['weight']*np.where(supported,.5,1.))
  js(out/'EVIDENCE.json',dict(complete=True,supported_edges=int(supported.sum()),status_codes={'0':'no_positive_support','1':'positive_projected_support','2':'UNKNOWN_projection'},visibility_verified=False,images=c['evidence_images'],held_out=False))
  def save_R(source,rows):nz(out/'reachable'/('%d.npz'%source),state_ids=rows)
  newgraph=dict(graph,base_weight=graph['weight'],weight=graph['weight']*np.where(supported,.5,1.),save_R=save_R)
  paths,receipts=e.propose(z,newgraph,seeds,cg)
  ids=[];offset=[0];qq=[];path_records=[]
  for index,p in enumerate(paths):
   ids.append(index);qq.append(p['q']);offset.append(offset[-1]+len(p['q']));path_records.append(dict(candidate_id=index,**{k:v for k,v in p.items() if k!='q'}))
  nz(out/'PATH_MODELS.npz',candidate_id=np.array(ids,np.int64),offsets=np.array(offset,np.int64),q_normalized=np.concatenate(qq) if qq else np.empty((0,3)))
  js(out/'PATHS.json',dict(complete=True,paths=path_records,seed_receipts=receipts,enumerated_seed_count=len(seeds),bounded_candidate_scope=True,exact_longest_path_claim=False,ordering='seed coverage selection order; no second endpoint rescue'))
  cg();names=[str(p.relative_to(out)) for p in sorted(out.rglob('*')) if p.is_file()];js(out/'CHECKPOINT.json',dict(complete=True,config_sha256=binding,files={n:sha(out/n) for n in names},source_stage='NO_BIRTH',source_checkpoint_sha256=sha(base/'NO_BIRTH/CHECKPOINT.json')));cg();bank_complete=True
  for index,p in enumerate(paths):
   limits.guard('science');attempts+=1;trialpath=U/'trials'/('TRIAL_%03d'%index);trialpath.mkdir(parents=True)
   js(trialpath/'START.json',dict(candidate=path_records[index],input_stage=str(base/current),input_checkpoint_sha256=sha(base/current/'CHECKPOINT.json'),candidate_checkpoint_sha256=sha(out/'CHECKPOINT.json'),tentative_model_id=next_id))
   def progress(phase,r):
    if phase=='template':nz(trialpath/'PROGRESS_TEMPLATE.npz',q_normalized=r['template'])
    elif phase=='fitted':nz(trialpath/'PROGRESS_FITTED_Q.npz',q_normalized=r['q']);nz(trialpath/'PROGRESS_FIT_ROWS.npz',rows=r['fit_rows'])
    elif phase=='raw':nz(trialpath/'PROGRESS_RAW_DELTA.npz',**m.delta(a,r['raw']))
    elif phase=='validated':nz(trialpath/'PROGRESS_VALIDATED_DELTA.npz',**m.delta(a,r['assignment']));save_models(trialpath/'PROGRESS_VALIDATED_MODELS.npz',r['models'])
   r=g.trial(d,models,a,next_id,p['q'],lambda:limits.guard('science'),progress);persist_trial(trialpath,r,a,base/current)
   if r['accepted']:
    stage='BIRTH_%03d'%(len(accepted)+1);event=dict(operation='observation_graph_path_birth',new_model=r['model_id'],surviving_children=r['surviving_children'],candidate_id=index,seed_mode=p['seed_mode'],states=p['states'],trial=str(trialpath.relative_to(U)),input_stage=current,energy_before=r['before'],energy_after=r['after'],support_events=r['events'])
    save_stage(base/stage,d,r['models'],r['assignment'],[event]+r['events'],r['next_id'],binding,dict(scope,predecessor_stage=current,accepted_trial=index));stages.append(stage);accepted.append(event);models=r['models'];a=r['assignment'];next_id=r['next_id'];current=stage
  search_complete=True;save_stage(base/'BIRTH_FINAL',d,models,a,[],next_id,binding,dict(scope,predecessor_stage=current,bank_complete=True,attempts=attempts,accepted_births=len(accepted),selected_path_search_complete=True));stages.append('BIRTH_FINAL')
 except TimeoutError as exc:result['errors'].append(dict(type=type(exc).__name__,message=str(exc),incomplete_trial_promoted=False))
 except Exception as exc:result['fatal']=True;result['errors'].append(dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
 js(U/'BIRTH_HISTORY.json',dict(attempts_started=attempts,accepted=accepted,complete_candidate_bank=bank_complete,selected_path_search_complete=search_complete,unattempted_candidate_indices=list(range(attempts,len(paths))),last_saved_stage=stages[-1] if stages else None))
 if d is not None and stages:
  try:result.update(deliver(c,d,stages,binding,lambda:limits.guard('delivery')));result['full_views_complete']=True
  except Exception as exc:
   result['errors'].append(dict(phase='delivery',type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
   if not isinstance(exc,TimeoutError):result['fatal']=True
 result.update(completed_stages=stages,attempts_started=attempts,accepted_births=len(accepted),candidate_bank_complete=bank_complete,elapsed_seconds=limits.elapsed(),execution_state='completed' if 'BIRTH_FINAL' in stages and result['full_views_complete'] and not result['errors'] else 'partial',kernel_geometry_frozen=True,legacy_groups_locked=False,uses_gpu=False,uses_training=False)
 js(U/'RUN_RESULT.json',result);signal.setitimer(signal.ITIMER_REAL,0);return 1 if result.get('fatal') else 0

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();c=json.loads(Path(args.config).read_text());return run(c,sha(args.config))
if __name__=='__main__':raise SystemExit(main())
