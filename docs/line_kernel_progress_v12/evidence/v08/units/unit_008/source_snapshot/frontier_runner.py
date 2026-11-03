"""Parent-owned serial original-kernel frontier experiment; no subprocesses."""
from runtime_io import *
from frontier_loader import load,local_validator
from frontier_core import *
from frontier_delivery import *
from port_paths import PathOracle
import argparse,traceback

def run(c,config_path):
 unitroot=Path(c['unit_root']);binding=sha(config_path);lim=Limits(c);facts=dict(status='blocked',config_sha256=binding,started_utc=now(),completed=[],scientific_verdict='UNASSESSED',fit_calls=0);error=None
 try:
  if (unitroot/'RUN_RESULT.json').exists():raise RuntimeError('CLOSED_RUN_NO_OVERWRITE')
  d=load(c,lim.guard);before=geometry_fingerprint(d['asset'])
  assert int(np.sum(d['membership']['edge_id']>=0))==c['expected_background_assigned'],'STRONG_BACKGROUND_COUNT'
  for v in d['asset'].values():v.flags.writeable=False
  lineage=json.loads(Path(c['lineage']).read_text())['events'];seed_status=[]
  for sid,version in c['seeds']:
   assert sid in d['leaves'] and d['leaves'][sid].version==version
   assert any(e['operation']=='endpoint' and e['output']==[sid,version] for e in lineage)
   seed_status.append(dict(seed=sid,version=version,valid=d['leaves'][sid].valid))
  index=endpoint_index(d['leaves']);seedids=sorted(s for s,v in c['seeds']);base=initial(seedids,d['next_version']);contexts={s:{s} for s in seedids}
  scene=unitroot/'scenes'/c['scene'];js(scene/'READINESS.json',dict(seeds=seed_status,rows=c['kernel_count'],carriers=len(d['leaves']),background_assigned=int(np.sum(d['membership']['edge_id']>=0)),complete_local_queries=True,global_search=False,legacy_groups_locked=False,tracer_protects_leaf_members=True))
  oracle=PathOracle(d['leaves'],d['representatives']['x']/d['p'],d['representatives']['t'],local_validator(d,d['p']),lambda:lim.guard('selection'))
  reference=scene/'stages'/'M5_REFERENCE';ref=save_stage(reference,c,d,base,oracle,binding);facts['completed'].append('M5_REFERENCE_MAPPING');saved={'M5_REFERENCE':ref};outputs={};facts['outputs']=outputs
  for arm in ['BASE','HISTORY']:
   state=initial(seedids,d['next_version']);stage=scene/'stages'/(arm+'_000');last=save_stage(stage,c,d,state,oracle,binding);visits=[];reason='frontiers_exhausted';visitno=0
   try:
    while state['attempts']<c['max_attempts']:
     progressed=False
     for sid in seedids:
      for side in (0,1):
       if state['accepted'][sid]>=c['max_accepts_per_seed'] or (sid,side) in state['stopped']:continue
       lim.guard('selection');records=candidates(d,state,sid,side,index,oracle,lambda:lim.guard('selection'));choice=choices(records);contexts[sid].update(x['donor'] for x in records)
       visit=dict(visit=visitno,seed=sid,side=side,version=state['versions'][sid],shadow=choice,records=records)
       js(scene/'visits'/arm/f'{visitno:04d}.json',visit);visits.append(dict(visit=visitno,seed=sid,side=side,version=state['versions'][sid],shadow=choice,records=len(records)));visitno+=1
       selected=choice[arm]
       if selected is None:state['stopped'].add((sid,side));continue
       if state['attempts']>=c['max_attempts']:break
       state['attempts']+=1;record=records[selected];newpath=scene/'stages'/f'{arm}_{len(state["events"])+1:03d}'
       box={}
       def save(trial):box['output']=save_stage(newpath,c,d,trial,oracle,binding)
       # State and versions change only after a cold-verified topology checkpoint.
       state=commit(state,sid,record,save);last=box['output'];stage=newpath;progressed=True;state['stopped'].discard((sid,0));state['stopped'].discard((sid,1))
       facts['completed'].append(stage.name+'_MAPPING');print('ACCEPTED_CHECKPOINT',arm,sid,record['donor'],flush=True)
     if not progressed:break
   except TimeoutError as exc:reason=str(exc)
   oracle.guard=lambda:lim.guard('delivery')
   # Final complete state copy gives a stable cold-load target even for zero growth.
   final=scene/'stages'/(arm+'_FINAL');last=save_stage(final,c,d,state,oracle,binding);saved[arm]=last
   js(final/'VISIT_SUMMARY.json',dict(visits=visits,stop_reason=reason,attempts=state['attempts'],accepted=len(state['events']),accepts_by_seed=state['accepted'],stopped=list(sorted(state['stopped'])),max_attempts=c['max_attempts'],max_accepts_per_seed=c['max_accepts_per_seed']))
   outputs[arm]=dict(stage=str(final),accepted=len(state['events']),attempts=state['attempts'],stop_reason=reason,rows=len(last[0]['edge_id']));facts['completed'].append(arm+'_FINAL_MAPPING')
   oracle.guard=lambda:lim.guard('selection')
  after=geometry_fingerprint(d['asset']);assert before==after;assert sha(c['gaussians'])==c['input_files'][c['gaussians']]
  js(unitroot/'GEOMETRY_AUDIT.json',dict(fields_before=before,fields_after=after,unchanged=True,original_rows=c['kernel_count'],original_row_order=True,source_sha256=c['input_files'][c['gaussians']],no_carrier_ink=True))
  cams0=json.loads(Path(c['cameras']).read_text())[c['scene']];cams=[next(v for v in cams0 if v['view']==name) for name in c['views']];render=renderer(c)
  for arm,(m,gs) in saved.items():
   out=reference if arm=='M5_REFERENCE' else Path(outputs[arm]['stage']);imgs=render_arm(out,c,d,m,gs,[],render,cams,lambda:lim.guard('delivery'),full_only=True)
   js(out/'FULL_NATIVE_CHECKPOINT.json',dict(complete=True,files={k:sha(out/k) for k in imgs+['DISPLAY_SOURCE.json','DISPLAY_COLORS.npz']}));facts['completed'].append(arm+'_FULL_NATIVE')
   if arm in outputs:outputs[arm]['full_images']=imgs
  facts['delivery_gate']=True
  for arm,(m,gs) in saved.items():
   out=reference if arm=='M5_REFERENCE' else Path(outputs[arm]['stage']);statistics(out,c,d,m,gs,lambda:lim.guard('delivery'))
  facts['diagnostic_images']=diagnostics(unitroot,c,d,saved,contexts,render,cams,lambda:lim.guard('delivery'))
  js(scene/'COMPARISON.json',dict(different_labels=int(np.sum(saved['BASE'][0]['edge_id']!=saved['HISTORY'][0]['edge_id'])),shared_initial_frontiers=True,rollout_candidates_may_diverge=True,physical_correctness=False))
  verify(c['source_files']);verify(c['helper_files']);facts['status']='completed' if all(x['stop_reason']=='frontiers_exhausted' for x in outputs.values()) else 'partial'
 except BaseException as exc:
  error=exc;facts.update(status='partial' if facts['completed'] else 'blocked',error=repr(exc),traceback=traceback.format_exc())
 finally:
  facts.update(ended_utc=now(),elapsed_seconds=time.monotonic()-lim.start,actual_pngs=[str(p.relative_to(unitroot)) for p in sorted(unitroot.glob('scenes/**/*.png'))],parent_exit_authoritative=True)
  if not (unitroot/'RUN_RESULT.json').exists():js(unitroot/'RUN_RESULT.json',facts)
  lim.close()
 if error:raise error

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();run(json.loads(Path(a.config).read_text()),a.config)
