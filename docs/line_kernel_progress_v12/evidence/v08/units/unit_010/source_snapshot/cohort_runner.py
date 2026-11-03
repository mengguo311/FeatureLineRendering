"""Parent-owned pre-frozen cohort experiment; import performs no science."""
from runtime_io import *
from frontier_loader import load,local_validator
from frontier_core import initial,choices,endpoint_index
from frontier_delivery import statistics as reference_statistics
from relay_delivery import save_stage as raw_save_stage
from observation_core import observations,ObservationOracle
from observation_bank import export_bank
from scene_render import geometry_fingerprint,render_arm
from port_paths import PathOracle
from switch_io import restore,copy_control
from cohort_delivery import save_stage,statistics,diagnostics,choose_visuals
import cohort_core as cohort
import switch_core as core
import overlap_core as oc
import argparse,traceback,copy

def frozen_library(d,state,sid,side,index,endpoints,guard,c):
 if state['metrics'][sid]['seed_status']!='valid':
  return dict(status='NOT_RUN_INVALID_SEED',records=[],queries=[],complete_competition=False,combined_prefixes_seen=0,unexplored_frontiers=[])
 return core.candidates(d,state,sid,side,index,endpoints,guard,c['switch']['max_combined_prefixes'],c['switch']['max_endpoint_donors'])

def run(c,config_path):
 root=Path(c['unit_root']);binding=sha(config_path);lim=Limits(c);facts=dict(status='blocked',config_sha256=binding,started_utc=now(),completed=[],scientific_verdict='UNASSESSED',fit_calls=0);error=None
 try:
  if (root/'RUN_RESULT.json').exists():raise RuntimeError('CLOSED_RUN_NO_OVERWRITE')
  raw=load(c,lim.guard);before=geometry_fingerprint(raw['asset']);assert int(np.sum(raw['membership']['edge_id']>=0))==c['expected_background_assigned']
  for a in raw['asset'].values():a.flags.writeable=False
  scene=root/'scenes'/c['scene'];d=observations(raw,lambda:lim.guard('readiness'));export_bank(c['observation_bank'],c,d,binding)
  verify_checkpoint(c['prior_observation_bank'],c['prior_config_sha256'])
  for name in ['OBSERVED_CARRIERS.npz','PORT_EVIDENCE.npz']:
   with np.load(Path(c['prior_observation_bank'])/name,allow_pickle=False) as aa,np.load(Path(c['observation_bank'])/name,allow_pickle=False) as bb:
    assert aa.files==bb.files
    for key in aa.files:np.testing.assert_array_equal(aa[key],bb[key])
  oldstate,oldmap,oldgroups,oldcp=restore(c,d,lim.guard);index=oc.SegmentIndex(d['leaves']);endpoints=endpoint_index(d['leaves'])
  control=scene/'stages/NO_FURTHER_GROWTH';saved={'NO_FURTHER_GROWTH':copy_control(control,c,oldstate,oldmap,oldgroups,oldcp,binding)};facts['completed'].append('NO_FURTHER_GROWTH_COLD_COPY')
  replay,contexts=cohort.replay_visits(c['prior_base_visits'],d,oldstate,index,endpoints,lambda:lim.guard('readiness'));assert len(replay['visits'])==8
  js(scene/'PRIOR_VISIT_REPLAY.json',replay);facts['completed'].append('PRIOR_EIGHT_VISIT_REPLAY')
  events=json.loads(Path(c['lineage']).read_text())['events'];groups=json.loads(Path(c['groups']).read_text())['groups']
  selected,queue=cohort.select_cohort(events,groups,{i:leaf.version for i,leaf in raw['leaves'].items()},oldstate['used'],c['cohort']['per_kind_cap'])
  js(scene/'COHORT_SELECTION.json',dict(selected=selected,fixed_seeds=c['fixed_seeds'],**queue))
  oracle=ObservationOracle(d['leaves'],d['ports'],d['representatives']['x']/d['p'],d['representatives']['t'],local_validator(d,d['p']),lambda:lim.guard('readiness'))
  starting,init_receipt=cohort.augment(oldstate,d,selected,oracle);seedids=sorted(starting['chains']);assert len(seedids)<=36
  cc=copy.deepcopy(c);cc['seeds']=[[sid,d['original_leaves'][sid].version] for sid in seedids]
  for sid in seedids:contexts.setdefault(sid,{i for i,_ in starting['chains'][sid]})
  js(scene/'COHORT_INITIALIZATION.json',dict(new_seeds=init_receipt,next_version=starting['next_version'],initial_events=len(starting['events']),seed_ids=seedids,new_seed_protection_changes_donor_availability=True,no_replacement_after_validation=True))
  states={};outputs={};facts['outputs']=outputs;initial_outputs={}
  for arm in ['BASE','HISTORY']:
   st=copy.deepcopy(starting);initial_outputs[arm]=save_stage(scene/'stages'/(arm+'_000'),cc,d,st,binding)
   mm=initial_outputs[arm][0];assert mm.keys()==oldmap.keys()
   for key in oldmap:np.testing.assert_array_equal(mm[key],oldmap[key],err_msg='COHORT_INITIAL_FULL_MAP_REPLAY '+key)
   facts['completed'].append(arm+'_INITIAL_MAPPING')
  # Extra group metadata for the unchanged control; never modify its copied checkpoint bytes.
  saved['NO_FURTHER_GROWTH']=(saved['NO_FURTHER_GROWTH'][0],initial_outputs['BASE'][1])
  js(control/'COHORT_BASELINE_GROUPS.json',dict(groups=initial_outputs['BASE'][1],membership_unchanged=True))
  initial_libs={};catalog_complete=False;catalog_reason='frontiers_exhausted';catalog=[]
  try:
   for sid in seedids:
    for side in (0,1):
     lim.guard('selection');lib=frozen_library(d,starting,sid,side,index,endpoints,lambda:lim.guard('selection'),cc)
     path=scene/'initial_libraries'/f'{sid}_{side}.json';sig=cohort.frontier_signature(starting,sid);choice=choices(lib['records'])
     if lib['status']!='COMPLETE':choice=dict(BASE=None,HISTORY=None,reason=lib['status'])
     js(path,dict(seed=sid,side=side,signature=sig,shadow=choice,**lib));initial_libs[(sid,side)]=path
     for query in lib['queries']:contexts[sid].update(x[0] for x in query['neighbors'])
     catalog.append(dict(seed=sid,side=side,path=str(path.relative_to(root)),sha256=sha(path),status=lib['status'],common_candidates=sum(z['common'] for z in lib['records']),shadow=choice))
   catalog_complete=True
  except TimeoutError as exc:catalog_reason=str(exc)
  js(scene/'INITIAL_LIBRARY_FREEZE.json',dict(complete=catalog_complete,completed_frontiers=catalog,expected_frontiers=2*len(seedids),reason=catalog_reason,no_promotion_before_complete_catalog=True))
  for arm in ['BASE','HISTORY']:
   state=copy.deepcopy(starting);visits=[];reason=catalog_reason;visitno=0;new_events=0
   try:
    while catalog_complete and state['attempts']<c['max_attempts']:
     progressed=False
     for sid in seedids:
      for side in (0,1):
       if state['accepted'][sid]>=c['max_accepts_per_seed'] or (sid,side) in state['stopped']:continue
       lim.guard('selection');frozen=json.loads(initial_libs[(sid,side)].read_text());reused=frozen['signature']==cohort.frontier_signature(state,sid)
       if reused:lib={k:v for k,v in frozen.items() if k not in ['seed','side','signature','shadow']}
       else:lib=frozen_library(d,state,sid,side,index,endpoints,lambda:lim.guard('selection'),cc)
       records=lib['records'];choice=choices(records)
       for query in lib['queries']:contexts[sid].update(x[0] for x in query['neighbors'])
       if lib['status']!='COMPLETE':choice=dict(BASE=None,HISTORY=None,reason=lib['status']);reason='partial_frontier_library'
       js(scene/'visits'/arm/f'{visitno:04d}.json',dict(visit=visitno,seed=sid,side=side,version=state['versions'][sid],shadow=choice,reused_frozen_initial_library=reused,**lib))
       visits.append(dict(visit=visitno,seed=sid,side=side,shadow=choice,library_status=lib['status'],records=len(records),common_candidates=sum(z['common'] for z in records)));visitno+=1
       selected_index=choice[arm]
       if selected_index is None:state['stopped'].add((sid,side));continue
       if state['attempts']>=c['max_attempts']:reason='attempt_cap';break
       trial_input=copy.deepcopy(state);trial_input['attempts']+=1;z=records[selected_index];stage=scene/'stages'/f'{arm}_{new_events+1:03d}';box={}
       def save(trial):box['output']=save_stage(stage,cc,d,trial,binding)
       state=core.commit(trial_input,sid,z,save);new_events+=1;progressed=True;state['stopped'].discard((sid,0));state['stopped'].discard((sid,1));facts['completed'].append(stage.name+'_MAPPING');print('ACCEPTED_COHORT_CHECKPOINT',arm,sid,z['relation'],z['donors'],flush=True)
     if not progressed:break
    if state['attempts']>=c['max_attempts']:reason='attempt_cap'
    if any(v>=c['max_accepts_per_seed'] for v in state['accepted'].values()):reason='accept_cap'
    if any(r['status']=='NOT_RUN' for r in init_receipt) and reason=='frontiers_exhausted':reason='partial_invalid_seed'
   except TimeoutError as exc:reason=str(exc)
   lim.guard('delivery');final=scene/'stages'/(arm+'_FINAL');saved[arm]=save_stage(final,cc,d,state,binding);states[arm]=state
   js(final/'VISIT_SUMMARY.json',dict(visits=visits,stop_reason=reason,attempts=state['attempts'],accepted=new_events,historical_accepted=len(oldstate['events']),accepts_by_seed=state['accepted'],stopped=sorted(state['stopped']),max_attempts=c['max_attempts'],max_accepts_per_seed=c['max_accepts_per_seed']))
   outputs[arm]=dict(stage=str(final),accepted=new_events,attempts=state['attempts'],stop_reason=reason,rows=len(saved[arm][0]['edge_id']));facts['completed'].append(arm+'_FINAL_MAPPING')
  raworacle=PathOracle(raw['leaves'],raw['representatives']['x']/raw['p'],raw['representatives']['t'],local_validator(raw,raw['p']),lambda:lim.guard('delivery'))
  reference=scene/'stages/M5_REFERENCE';saved['M5_REFERENCE']=raw_save_stage(reference,cc,raw,initial(seedids,raw['next_version']),raworacle,binding);facts['completed'].append('M5_REFERENCE_MAPPING')
  after=geometry_fingerprint(d['asset']);assert before==after and sha(c['gaussians'])==c['input_files'][c['gaussians']]
  js(root/'GEOMETRY_AUDIT.json',dict(fields_before=before,fields_after=after,unchanged=True,original_rows=c['kernel_count'],original_row_order=True,source_sha256=c['input_files'][c['gaussians']],no_carrier_ink=True))
  cams0=json.loads(Path(c['cameras']).read_text())[c['scene']];cams=[next(v for v in cams0 if v['view']==name) for name in c['views']];render=renderer(c)
  for arm,(m,gs) in saved.items():
   out=control if arm=='NO_FURTHER_GROWTH' else reference if arm=='M5_REFERENCE' else Path(outputs[arm]['stage']);imgs=render_arm(out,cc,d,m,gs,[],render,cams,lambda:lim.guard('delivery'),full_only=True)
   js(out/'FULL_NATIVE_CHECKPOINT.json',dict(complete=True,files={k:sha(out/k) for k in imgs+['DISPLAY_SOURCE.json','DISPLAY_COLORS.npz']}));facts['completed'].append(arm+'_FULL_NATIVE')
   if arm in outputs:outputs[arm]['full_images']=imgs
  facts['delivery_gate']=True;incremental={}
  reference_statistics(reference,cc,raw,*saved['M5_REFERENCE'],lambda:lim.guard('delivery'))
  for arm in ['NO_FURTHER_GROWTH','BASE','HISTORY']:
   out=control if arm=='NO_FURTHER_GROWTH' else Path(outputs[arm]['stage']);st=starting if arm=='NO_FURTHER_GROWTH' else states[arm]
   incremental[arm]=statistics(out,cc,d,*saved[arm],st,starting,lambda:lim.guard('delivery'))
  visual_ids,visual_receipt=choose_visuals(c,selected,incremental,saved);js(scene/'VISUAL_SELECTION.json',visual_receipt)
  vc=copy.deepcopy(cc);vc['seeds']=[[i,d['original_leaves'][i].version] for i in visual_ids]
  facts['diagnostic_images']=diagnostics(root,vc,d,saved,contexts,render,cams,lambda:lim.guard('delivery'))
  js(scene/'COMPARISON.json',dict(different_labels=int(np.sum(saved['BASE'][0]['edge_id']!=saved['HISTORY'][0]['edge_id'])),shared_initial_library=True,rollout_candidates_may_diverge=True,seed_protection_changes_available_donors=True,physical_correctness=False,prior_accepted_is_ground_truth=False))
  js(scene/'READINESS.json',dict(rows=c['kernel_count'],initial_assigned=c['initial_assigned'],initial_next_version=starting['next_version'],seed_ids=seedids,additional_seeds=selected,starting_membership_exact=True,global_search=False,tracer_protects_original_leaf_members=True,initial_catalog_complete=catalog_complete))
  verify(c['source_files']);verify(c['helper_files']);facts['status']='completed' if catalog_complete and all(x['stop_reason']=='frontiers_exhausted' for x in outputs.values()) else 'partial'
 except BaseException as exc:error=exc;facts.update(status='partial' if facts['completed'] else 'blocked',error=repr(exc),traceback=traceback.format_exc())
 finally:
  facts.update(ended_utc=now(),elapsed_seconds=time.monotonic()-lim.start,actual_pngs=[str(p.relative_to(root)) for p in sorted(root.glob('scenes/**/*.png'))],parent_exit_authoritative=True)
  if not (root/'RUN_RESULT.json').exists():js(root/'RUN_RESULT.json',facts)
  lim.close()
 if error:raise error
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();run(json.loads(Path(args.config).read_text()),args.config)
