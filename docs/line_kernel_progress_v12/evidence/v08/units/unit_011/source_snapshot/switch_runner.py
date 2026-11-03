"""Parent-owned relation switching; importing performs no numerical run."""
from runtime_io import *
from frontier_loader import load,local_validator
from frontier_core import initial,choices,endpoint_index
from frontier_delivery import statistics as reference_statistics
from relay_delivery import save_stage as raw_save_stage
from observation_core import observations
from observation_bank import export_bank
from scene_render import geometry_fingerprint,render_arm
from port_paths import PathOracle
from switch_io import restore,copy_control,replay_deadends,save_stage,statistics,diagnostics
import switch_core as core
import overlap_core as oc
import argparse,traceback,copy

def run(c,config_path):
 root=Path(c['unit_root']);binding=sha(config_path);lim=Limits(c);facts=dict(status='blocked',config_sha256=binding,started_utc=now(),completed=[],scientific_verdict='UNASSESSED',fit_calls=0);error=None
 try:
  if (root/'RUN_RESULT.json').exists():raise RuntimeError('CLOSED_RUN_NO_OVERWRITE')
  raw=load(c,lim.guard);before=geometry_fingerprint(raw['asset']);assert int(np.sum(raw['membership']['edge_id']>=0))==c['expected_background_assigned']
  for a in raw['asset'].values():a.flags.writeable=False
  scene=root/'scenes'/c['scene'];seedids=sorted(s for s,v in c['seeds']);d=observations(raw,lambda:lim.guard('readiness'))
  export_bank(c['observation_bank'],c,d,binding)
  # Exact observation-bank replay preserves support trimming and axial evidence.
  verify_checkpoint(c['prior_observation_bank'],c['prior_config_sha256'])
  for name in ['OBSERVED_CARRIERS.npz','PORT_EVIDENCE.npz']:
   aa=np.load(Path(c['prior_observation_bank'])/name,allow_pickle=False);bb=np.load(Path(c['observation_bank'])/name,allow_pickle=False);assert aa.files==bb.files
   for key in aa.files:np.testing.assert_array_equal(aa[key],bb[key])
  initial_state,oldmap,oldgroups,oldcp=restore(c,d,lim.guard);index=oc.SegmentIndex(d['leaves']);endpoints=endpoint_index(d['leaves'])
  control=scene/'stages/NO_FURTHER_GROWTH';saved={'NO_FURTHER_GROWTH':copy_control(control,c,initial_state,oldmap,oldgroups,oldcp,binding)};facts['completed'].append('NO_FURTHER_GROWTH_COLD_COPY')
  receipt,contexts=replay_deadends(c,d,initial_state,index,lambda:lim.guard('readiness'));js(scene/'DEADEND_REPLAY.json',receipt);facts['completed'].append('DEADEND_REPLAY')
  for path in c['prior_context_visits']:
   v=json.loads(Path(path).read_text())
   for query in v['queries']:contexts[v['seed']].update(x[0] for x in query['neighbors'])
  raworacle=PathOracle(raw['leaves'],raw['representatives']['x']/raw['p'],raw['representatives']['t'],local_validator(raw,raw['p']),lambda:lim.guard('readiness'))
  ref=scene/'stages/M5_REFERENCE';saved['M5_REFERENCE']=raw_save_stage(ref,c,raw,initial(seedids,raw['next_version']),raworacle,binding);facts['completed'].append('M5_REFERENCE_MAPPING')
  outputs={};states={};facts['outputs']=outputs
  js(scene/'READINESS.json',dict(rows=c['kernel_count'],initial_assigned=c['initial_assigned'],initial_next_version=initial_state['next_version'],seeds=seedids,starting_state_exact=True,global_search=False,tracer_protects_original_leaf_members=True,relation_scope='single overlap OR endpoint-only relay per transaction'))
  for arm in ['BASE','HISTORY']:
   state=core.reopen(initial_state);last=save_stage(scene/'stages'/(arm+'_000'),c,d,state,binding)
   for key in oldmap:np.testing.assert_array_equal(last[0][key],oldmap[key],err_msg='INITIAL_FULL_MAP_REPLAY '+key)
   facts['completed'].append(arm+'_INITIAL_MAPPING');visits=[];reason='frontiers_exhausted';visitno=0;new_events=0
   try:
    while state['attempts']<c['max_attempts']:
     progressed=False
     for sid in seedids:
      for side in (0,1):
       if state['accepted'][sid]>=c['max_accepts_per_seed'] or (sid,side) in state['stopped']:continue
       lim.guard('selection');lib=core.candidates(d,state,sid,side,index,endpoints,lambda:lim.guard('selection'),c['switch']['max_combined_prefixes'],c['switch']['max_endpoint_donors']);records=lib['records'];choice=choices(records)
       for query in lib['queries']:contexts[sid].update(x[0] for x in query['neighbors'])
       if lib['status']!='COMPLETE':choice=dict(BASE=None,HISTORY=None,reason=lib['status']);reason='partial_frontier_library'
       js(scene/'visits'/arm/f'{visitno:04d}.json',dict(visit=visitno,seed=sid,side=side,version=state['versions'][sid],shadow=choice,**lib));visits.append(dict(visit=visitno,seed=sid,side=side,version=state['versions'][sid],shadow=choice,records=len(records),library_status=lib['status'],combined_prefixes_seen=lib['combined_prefixes_seen'],common_candidates=sum(z['common'] for z in records)));visitno+=1
       selected=choice[arm]
       if selected is None:state['stopped'].add((sid,side));continue
       if state['attempts']>=c['max_attempts']:reason='attempt_cap';break
       trial_input=copy.deepcopy(state);trial_input['attempts']+=1;z=records[selected];stage=scene/'stages'/f'{arm}_{new_events+1:03d}';box={}
       def save(trial):box['output']=save_stage(stage,c,d,trial,binding)
       state=core.commit(trial_input,sid,z,save);last=box['output'];new_events+=1;progressed=True;state['stopped'].discard((sid,0));state['stopped'].discard((sid,1));facts['completed'].append(stage.name+'_MAPPING');print('ACCEPTED_SWITCH_CHECKPOINT',arm,sid,z['relation'],z['donors'],flush=True)
     if not progressed:break
    if any(v>=c['max_accepts_per_seed'] for v in state['accepted'].values()):reason='accept_cap'
   except TimeoutError as exc:reason=str(exc)
   lim.guard('delivery');final=scene/'stages'/(arm+'_FINAL');last=save_stage(final,c,d,state,binding);saved[arm]=last;states[arm]=state
   js(final/'VISIT_SUMMARY.json',dict(visits=visits,stop_reason=reason,attempts=state['attempts'],accepted=new_events,historical_accepted=len(initial_state['events']),accepts_by_seed=state['accepted'],stopped=sorted(state['stopped']),max_attempts=c['max_attempts'],max_accepts_per_seed=c['max_accepts_per_seed']))
   outputs[arm]=dict(stage=str(final),accepted=new_events,attempts=state['attempts'],stop_reason=reason,rows=len(last[0]['edge_id']));facts['completed'].append(arm+'_FINAL_MAPPING')
  after=geometry_fingerprint(d['asset']);assert before==after and sha(c['gaussians'])==c['input_files'][c['gaussians']]
  js(root/'GEOMETRY_AUDIT.json',dict(fields_before=before,fields_after=after,unchanged=True,original_rows=c['kernel_count'],original_row_order=True,source_sha256=c['input_files'][c['gaussians']],no_carrier_ink=True))
  cams0=json.loads(Path(c['cameras']).read_text())[c['scene']];cams=[next(v for v in cams0 if v['view']==name) for name in c['views']];render=renderer(c)
  for arm,(m,gs) in saved.items():
   out=ref if arm=='M5_REFERENCE' else control if arm=='NO_FURTHER_GROWTH' else Path(outputs[arm]['stage']);imgs=render_arm(out,c,d,m,gs,[],render,cams,lambda:lim.guard('delivery'),full_only=True)
   js(out/'FULL_NATIVE_CHECKPOINT.json',dict(complete=True,files={k:sha(out/k) for k in imgs+['DISPLAY_SOURCE.json','DISPLAY_COLORS.npz']}));facts['completed'].append(arm+'_FULL_NATIVE')
   if arm in outputs:outputs[arm]['full_images']=imgs
  facts['delivery_gate']=True
  reference_statistics(ref,c,raw,*saved['M5_REFERENCE'],lambda:lim.guard('delivery'))
  for arm in ['NO_FURTHER_GROWTH','BASE','HISTORY']:
   out=control if arm=='NO_FURTHER_GROWTH' else Path(outputs[arm]['stage']);st=core.reopen(initial_state) if arm=='NO_FURTHER_GROWTH' else states[arm];statistics(out,c,d,*saved[arm],st,initial_state,lambda:lim.guard('delivery'))
  facts['diagnostic_images']=diagnostics(root,c,d,saved,contexts,render,cams,lambda:lim.guard('delivery'))
  js(scene/'COMPARISON.json',dict(different_labels=int(np.sum(saved['BASE'][0]['edge_id']!=saved['HISTORY'][0]['edge_id'])),shared_initial_library=True,rollout_candidates_may_diverge=True,physical_correctness=False,prior_accepted_is_ground_truth=False))
  verify(c['source_files']);verify(c['helper_files']);facts['status']='completed' if all(x['stop_reason']=='frontiers_exhausted' for x in outputs.values()) else 'partial'
 except BaseException as exc:error=exc;facts.update(status='partial' if facts['completed'] else 'blocked',error=repr(exc),traceback=traceback.format_exc())
 finally:
  facts.update(ended_utc=now(),elapsed_seconds=time.monotonic()-lim.start,actual_pngs=[str(p.relative_to(root)) for p in sorted(root.glob('scenes/**/*.png'))],parent_exit_authoritative=True)
  if not (root/'RUN_RESULT.json').exists():js(root/'RUN_RESULT.json',facts)
  lim.close()
 if error:raise error
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();run(json.loads(Path(args.config).read_text()),args.config)
