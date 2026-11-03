"""Parent-owned finite overlap continuation. Importing never runs science."""
from runtime_io import *
from frontier_loader import load,local_validator
from frontier_core import initial,choices
from frontier_delivery import statistics as reference_statistics
from relay_delivery import save_stage as raw_save_stage
from observation_core import observations,ObservationOracle
from observation_bank import export_bank
from overlap_replay import replay
from overlap_delivery import save_stage,statistics_overlap,diagnostics
from scene_render import geometry_fingerprint,render_arm
from port_paths import PathOracle
import overlap_core as core
import argparse,traceback

def run(c,config_path):
 root=Path(c['unit_root']);binding=sha(config_path);lim=Limits(c);facts=dict(status='blocked',config_sha256=binding,started_utc=now(),completed=[],scientific_verdict='UNASSESSED',fit_calls=0);error=None
 try:
  if (root/'RUN_RESULT.json').exists():raise RuntimeError('CLOSED_RUN_NO_OVERWRITE')
  raw=load(c,lim.guard);before=geometry_fingerprint(raw['asset']);assert int(np.sum(raw['membership']['edge_id']>=0))==c['expected_background_assigned']
  for v in raw['asset'].values():v.flags.writeable=False
  lineage=json.loads(Path(c['lineage']).read_text())['events'];seedids=sorted(s for s,v in c['seeds']);seed_status=[]
  for sid,version in c['seeds']:
   assert sid in raw['leaves'] and raw['leaves'][sid].version==version
   assert any(e['operation']=='endpoint' and e['output']==[sid,version] for e in lineage)
   seed_status.append(dict(seed=sid,version=version,valid=raw['leaves'][sid].valid))
  scene=root/'scenes'/c['scene'];raworacle=PathOracle(raw['leaves'],raw['representatives']['x']/raw['p'],raw['representatives']['t'],local_validator(raw,raw['p']),lambda:lim.guard('readiness'))
  reference=scene/'stages/M5_REFERENCE';ref=raw_save_stage(reference,c,raw,initial(seedids,raw['next_version']),raworacle,binding);facts['completed'].append('M5_REFERENCE_MAPPING');saved={'M5_REFERENCE':ref};states={};outputs={};facts['outputs']=outputs
  d=observations(raw,lambda:lim.guard('readiness'));export_bank(c['observation_bank'],c,d,binding)
  replayreceipt,contexts=replay(c,raw,d,c['observation_bank'],lambda:lim.guard('readiness'));js(scene/'PRIOR_OBSERVATION_REPLAY.json',replayreceipt);facts['completed'].append('PRIOR_OBSERVATION_REPLAY')
  js(scene/'READINESS.json',dict(seeds=seed_status,rows=c['kernel_count'],carriers=len(d['leaves']),background_assigned=c['expected_background_assigned'],complete_local_finite_segment_queries=True,global_search=False,tracer_protects_leaf_members=True,attachment_scope='one exact nearest finite point per donor orientation; not exhaustive attachment search'))
  obsoracle=ObservationOracle(d['leaves'],d['ports'],d['representatives']['x']/d['p'],d['representatives']['t'],local_validator(d,d['p']),lambda:lim.guard('selection'));index=core.SegmentIndex(d['leaves'])
  for arm in ['BASE','HISTORY']:
   state=core.initial_overlap(d,seedids,obsoracle);last=save_stage(scene/'stages'/(arm+'_000'),c,d,state,binding);facts['completed'].append(arm+'_INITIAL_MAPPING');visits=[];reason='frontiers_exhausted';visitno=0
   try:
    while state['attempts']<c['max_attempts']:
     progressed=False
     for sid in seedids:
      for side in (0,1):
       if state['accepted'][sid]>=c['max_accepts_per_seed'] or (sid,side) in state['stopped']:continue
       lim.guard('selection');lib=core.candidates(d,state,sid,side,index,lambda:lim.guard('selection'),c['overlap']['max_proposals']);records=lib['records'];choice=choices(records)
       for query in lib['queries']:contexts[sid].update(x[0] for x in query['neighbors'])
       if lib['status']!='COMPLETE':choice=dict(BASE=None,HISTORY=None,reason=lib['status']);reason='partial_frontier_library'
       visit=dict(visit=visitno,seed=sid,side=side,version=state['versions'][sid],shadow=choice,**lib);js(scene/'visits'/arm/f'{visitno:04d}.json',visit)
       visits.append(dict(visit=visitno,seed=sid,side=side,version=state['versions'][sid],shadow=choice,records=len(records),library_status=lib['status'],proposals_seen=lib['proposals_seen'],common_candidates=sum(z['common'] for z in records)));visitno+=1
       selected=choice[arm]
       if selected is None:state['stopped'].add((sid,side));continue
       if state['attempts']>=c['max_attempts']:reason='attempt_cap';break
       state['attempts']+=1;z=records[selected];stage=scene/'stages'/f'{arm}_{len(state["events"])+1:03d}';box={}
       def save(trial):box['output']=save_stage(stage,c,d,trial,binding)
       state=core.commit(state,sid,z,save);last=box['output'];progressed=True;state['stopped'].discard((sid,0));state['stopped'].discard((sid,1));facts['completed'].append(stage.name+'_MAPPING');print('ACCEPTED_OVERLAP_CHECKPOINT',arm,sid,z['donor'],flush=True)
     if not progressed:break
    if any(v>=c['max_accepts_per_seed'] for v in state['accepted'].values()):reason='accept_cap'
   except TimeoutError as exc:reason=str(exc)
   lim.guard('delivery');final=scene/'stages'/(arm+'_FINAL');last=save_stage(final,c,d,state,binding);saved[arm]=last;states[arm]=state
   js(final/'VISIT_SUMMARY.json',dict(visits=visits,stop_reason=reason,attempts=state['attempts'],accepted=len(state['events']),accepts_by_seed=state['accepted'],stopped=sorted(state['stopped']),max_attempts=c['max_attempts'],max_accepts_per_seed=c['max_accepts_per_seed']))
   outputs[arm]=dict(stage=str(final),accepted=len(state['events']),attempts=state['attempts'],stop_reason=reason,rows=len(last[0]['edge_id']));facts['completed'].append(arm+'_FINAL_MAPPING')
  after=geometry_fingerprint(d['asset']);assert before==after;assert sha(c['gaussians'])==c['input_files'][c['gaussians']]
  js(root/'GEOMETRY_AUDIT.json',dict(fields_before=before,fields_after=after,unchanged=True,original_rows=c['kernel_count'],original_row_order=True,source_sha256=c['input_files'][c['gaussians']],no_carrier_ink=True))
  cams0=json.loads(Path(c['cameras']).read_text())[c['scene']];cams=[next(v for v in cams0 if v['view']==name) for name in c['views']];render=renderer(c)
  for arm,(m,gs) in saved.items():
   out=reference if arm=='M5_REFERENCE' else Path(outputs[arm]['stage']);imgs=render_arm(out,c,d,m,gs,[],render,cams,lambda:lim.guard('delivery'),full_only=True)
   js(out/'FULL_NATIVE_CHECKPOINT.json',dict(complete=True,files={k:sha(out/k) for k in imgs+['DISPLAY_SOURCE.json','DISPLAY_COLORS.npz']}));facts['completed'].append(arm+'_FULL_NATIVE')
   if arm in outputs:outputs[arm]['full_images']=imgs
  facts['delivery_gate']=True
  reference_statistics(reference,c,raw,*ref,lambda:lim.guard('delivery'))
  for arm in ['BASE','HISTORY']:statistics_overlap(Path(outputs[arm]['stage']),c,d,*saved[arm],states[arm],lambda:lim.guard('delivery'))
  facts['diagnostic_images']=diagnostics(root,c,d,saved,contexts,render,cams,lambda:lim.guard('delivery'))
  js(scene/'COMPARISON.json',dict(different_labels=int(np.sum(saved['BASE'][0]['edge_id']!=saved['HISTORY'][0]['edge_id'])),shared_initial_overlap_library=True,rollout_candidates_may_diverge=True,physical_correctness=False,relation_guard_changed_from_endpoint=True))
  verify(c['source_files']);verify(c['helper_files']);facts['status']='completed' if all(x['stop_reason']=='frontiers_exhausted' for x in outputs.values()) else 'partial'
 except BaseException as exc:error=exc;facts.update(status='partial' if facts['completed'] else 'blocked',error=repr(exc),traceback=traceback.format_exc())
 finally:
  facts.update(ended_utc=now(),elapsed_seconds=time.monotonic()-lim.start,actual_pngs=[str(p.relative_to(root)) for p in sorted(root.glob('scenes/**/*.png'))],parent_exit_authoritative=True)
  if not (root/'RUN_RESULT.json').exists():js(root/'RUN_RESULT.json',facts)
  lim.close()
 if error:raise error
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();run(json.loads(Path(args.config).read_text()),args.config)
