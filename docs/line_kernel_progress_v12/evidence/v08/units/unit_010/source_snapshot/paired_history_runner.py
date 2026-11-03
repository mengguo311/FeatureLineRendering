"""Parent-owned three-arm history-evidence experiment; import performs no science."""
from runtime_io import *
from frontier_loader import local_validator
from paired_loader import load
from frontier_core import initial,choices,endpoint_index
from frontier_delivery import statistics as reference_statistics,serial
from relay_delivery import save_stage as raw_save_stage
from observation_core import observations
from observation_bank import export_bank
from scene_render import geometry_fingerprint,render_arm
from port_paths import PathOracle
from switch_io import restore,copy_control
from cohort_delivery import save_stage,statistics,diagnostics
from cohort_core import frontier_signature
from seam_delivery import choose_visuals
import switch_core as core
import overlap_core as oc
import seam_core
import contact_core
import derivative_history_core as old_history
import paired_history_core as dh
import argparse,traceback,copy
ARMS=dh.ARMS

def library(d,state,sid,side,index,endpoints,rep,guard,c):
 if state['metrics'][sid]['seed_status']!='valid':
  return dict(status='NOT_RUN_INVALID_SEED',records=[],queries=[],complete_competition=False,unexplored_frontiers=[])
 lib=contact_core.library(d,state,sid,side,index,endpoints,'ARC',guard,c['switch']['max_combined_prefixes'],c['switch']['max_endpoint_donors'])
 return dh.annotate(d,state,sid,side,lib,guard)

def replay(c,d,index,endpoints,guard):
 state,_,_,_=restore(c,d,guard);state=core.reopen(state);receipts=[]
 assert len(c['replay_libraries'])==2*c['seed_count']
 seen=set()
 for path in c['replay_libraries']:
  old=json.loads(Path(path).read_text());sid=old['seed'];side=old['side']
  assert (sid,side) not in seen;seen.add((sid,side))
  assert old['signature']==frontier_signature(state,sid)
  lib=library(d,state,sid,side,index,endpoints,'ARC',lambda:guard('readiness'),c)
  bare=dh.remove_diagnostics(lib)
  for key,value in bare.items():assert json.loads(json.dumps(value,allow_nan=False))==old[key],('CONTROL_REPLAY',path,key)
  choice=old_history.choices(lib['records']);assert choice==old['shadow']
  receipts.append(dict(path=path,sha256=sha(path),matched=True))
 assert seen=={(sid,side) for sid in state['chains'] for side in (0,1)}
 return receipts

def run(c,config_path):
 root=Path(c['unit_root']);binding=sha(config_path);lim=Limits(c);facts=dict(status='blocked',config_sha256=binding,started_utc=now(),completed=[],scientific_verdict='UNASSESSED',fit_calls=0);error=None
 try:
  if (root/'RUN_RESULT.json').exists():raise RuntimeError('CLOSED_RUN_NO_OVERWRITE')
  raw=load(c,lim.guard);js(root/'CONTROL_IDENTITY_READINESS.json',raw['control_identity_receipt']);before=geometry_fingerprint(raw['asset']);assert int(np.sum(raw['membership']['edge_id']>=0))==c['expected_background_assigned']
  for a in raw['asset'].values():a.flags.writeable=False
  scene=root/'scenes'/c['scene'];d=observations(raw,lambda:lim.guard('readiness'));export_bank(c['observation_bank'],c,d,binding)
  verify_checkpoint(c['prior_observation_bank'],c['prior_observation_config_sha256'])
  for name in ['OBSERVED_CARRIERS.npz','PORT_EVIDENCE.npz']:
   with np.load(Path(c['prior_observation_bank'])/name,allow_pickle=False) as aa,np.load(Path(c['observation_bank'])/name,allow_pickle=False) as bb:
    assert aa.files==bb.files
    for key in aa.files:np.testing.assert_array_equal(aa[key],bb[key])
  oldstate,oldmap,oldgroups,oldcp=restore(c,d,lim.guard);seedids=sorted(oldstate['chains']);assert len(seedids)==c['seed_count']
  index=oc.SegmentIndex(d['leaves']);endpoints=endpoint_index(d['leaves']);contexts={sid:{i for i,_ in ch} for sid,ch in oldstate['chains'].items()}
  control=scene/'stages/NO_FURTHER_GROWTH';saved={'NO_FURTHER_GROWTH':copy_control(control,c,oldstate,oldmap,oldgroups,oldcp,binding)};facts['completed'].append('NO_FURTHER_GROWTH_COLD_COPY')
  js(scene/'PRIOR_VISIT_REPLAY.json',dict(status='MATCHED',cases=replay(c,d,index,endpoints,lim.guard)));facts['completed'].append('PRIOR_VISIT_REPLAY')
  starting=core.reopen(oldstate);states={};outputs={};facts['outputs']=outputs
  for arm in ARMS:
   mm,_=save_stage(scene/'stages'/(arm+'_000'),c,d,starting,binding)
   assert mm.keys()==oldmap.keys()
   for key in oldmap:np.testing.assert_array_equal(mm[key],oldmap[key],err_msg='EXACT_INITIAL_MAP '+key)
   facts['completed'].append(arm+'_INITIAL_MAPPING')
  initial_libs={};catalog=[];catalog_complete=False;catalog_reason='frontiers_exhausted'
  try:
   for sid in seedids:
    for side in (0,1):
     for rep in ('ARC',):
      lib=library(d,starting,sid,side,index,endpoints,rep,lambda:lim.guard('selection'),c)
      path=scene/'initial_libraries'/f'{rep}_{sid}_{side}.json';choice=dh.choices(lib['records'])
      if lib['status']!='COMPLETE':choice=dict(BASE=None,OBS_HISTORY=None,PAIRED_HISTORY=None,reason=lib['status'])
      js(path,dict(seed=sid,side=side,signature=frontier_signature(starting,sid),shadow=choice,**lib));initial_libs[(rep,sid,side)]=path
      for query in lib['queries']:contexts[sid].update(x[0] for x in query['neighbors'])
      catalog.append(dict(representation=rep,seed=sid,side=side,path=str(path.relative_to(root)),sha256=sha(path),status=lib['status'],common_candidates=sum(z['common'] for z in lib['records']),shadow=choice))
   catalog_complete=True
  except TimeoutError as exc:catalog_reason=str(exc)
  js(scene/'INITIAL_LIBRARY_FREEZE.json',dict(complete=catalog_complete,completed_frontiers=catalog,expected_frontiers=2*len(seedids),reason=catalog_reason,no_promotion_before_complete_catalog=True))
  for arm in ARMS:
   rep='ARC';policy=arm;state=copy.deepcopy(starting);visits=[];reason=catalog_reason;visitno=0;new_events=0
   try:
    while catalog_complete and state['attempts']<c['max_attempts']:
     progressed=False
     for sid in seedids:
      for side in (0,1):
       if state['accepted'][sid]>=c['max_accepts_per_seed'] or (sid,side) in state['stopped']:continue
       lim.guard('selection');libs={};shadows={}
       for representation in ('ARC',):
        frozen=json.loads(initial_libs[(representation,sid,side)].read_text());reused=frozen['signature']==frontier_signature(state,sid) and state['used']==starting['used']
        lib={k:v for k,v in frozen.items() if k not in ['seed','side','signature','shadow']} if reused else library(d,state,sid,side,index,endpoints,representation,lambda:lim.guard('selection'),c)
        choice=dh.choices(lib['records'])
        if lib['status']!='COMPLETE':choice=dict(BASE=None,OBS_HISTORY=None,PAIRED_HISTORY=None,reason=lib['status'])
        for query in lib['queries']:contexts[sid].update(x[0] for x in query['neighbors'])
        libs[representation]=lib;shadows[representation]=choice
       lib=libs[rep];choice=shadows[rep]
       if lib['status']!='COMPLETE':reason='partial_frontier_library'
       js(scene/'visits'/arm/f'{visitno:04d}.json',dict(visit=visitno,seed=sid,side=side,version=state['versions'][sid],representation=rep,shadow=choice,representation_shadows=shadows,**lib))
       visits.append(dict(visit=visitno,seed=sid,side=side,shadow=choice,representation_shadows=shadows,library_status=lib['status'],common_candidates=sum(z['common'] for z in lib['records'])));visitno+=1
       selected=choice[policy]
       if selected is None:state['stopped'].add((sid,side));continue
       if state['attempts']>=c['max_attempts']:reason='attempt_cap';break
       trial=copy.deepcopy(state);trial['attempts']+=1;z=lib['records'][selected];stage=scene/'stages'/f'{arm}_{new_events+1:03d}'
       def persist(st):
        if arm=='OBS_HISTORY':st['events'][-1].update(history_policy=arm,observed_history=z['observed_history'])
        if arm=='PAIRED_HISTORY':st['events'][-1].update(history_policy=arm,observed_history=z['observed_history'],paired_history=z['paired_history'])
        save_stage(stage,c,d,st,binding)
       state=core.commit(trial,sid,z,persist);new_events+=1;progressed=True
       state['stopped'].discard((sid,0));state['stopped'].discard((sid,1));facts['completed'].append(stage.name+'_MAPPING');print('ACCEPTED_SEAM_CHECKPOINT',arm,sid,z['relation'],z['donors'],flush=True)
     if not progressed:break
    if state['attempts']>=c['max_attempts']:reason='attempt_cap'
    if any(v>=c['max_accepts_per_seed'] for v in state['accepted'].values()):reason='accept_cap'
   except TimeoutError as exc:reason=str(exc)
   lim.guard('delivery');final=scene/'stages'/(arm+'_FINAL');saved[arm]=save_stage(final,c,d,state,binding);states[arm]=state
   js(final/'VISIT_SUMMARY.json',dict(visits=visits,stop_reason=reason,attempts=state['attempts'],accepted=new_events,historical_accepted=len(oldstate['events']),accepts_by_seed=state['accepted'],stopped=sorted(state['stopped'])))
   outputs[arm]=dict(stage=str(final),accepted=new_events,attempts=state['attempts'],stop_reason=reason,rows=len(saved[arm][0]['edge_id']));facts['completed'].append(arm+'_FINAL_MAPPING')
  controls=[]
  for arm,ref in c['control_reproductions'].items():
   guard=lambda:lim.guard('delivery');guard();verify_checkpoint(ref['stage'],ref['config_sha256'])
   expected=dict(np.load(Path(ref['stage'])/'MEMBERSHIP.npz',allow_pickle=False));actual=saved[arm][0]
   assert actual.keys()==expected.keys(),('CONTROL_FIELDS',arm)
   for key in expected:np.testing.assert_array_equal(actual[key],expected[key],err_msg='CONTROL_MEMBERSHIP '+arm+' '+key)
   old=core.hydrate(json.loads((Path(ref['stage'])/'GROWTH_STATE.json').read_text()));new=states[arm]
   for key in ['chains','curves','versions','next_version','events','used','metrics','ports']:
    assert json.loads(json.dumps(serial({key:new[key]}),allow_nan=False))==json.loads(json.dumps(serial({key:old[key]}),allow_nan=False)),('CONTROL_STATE',arm,key)
   controls.append(dict(arm=arm,reference=ref['stage'],matched=True,membership_all_fields=True,curves_versions_lineage_exact=True))
  js(scene/'CONTROL_REPRODUCTION.json',dict(status='MATCHED',controls=controls));facts['completed'].append('CONTROL_REPRODUCTION')
  raworacle=PathOracle(raw['leaves'],raw['representatives']['x']/raw['p'],raw['representatives']['t'],local_validator(raw,raw['p']),lambda:lim.guard('delivery'))
  reference=scene/'stages/M5_REFERENCE';saved['M5_REFERENCE']=raw_save_stage(reference,c,raw,initial(seedids,raw['next_version']),raworacle,binding);facts['completed'].append('M5_REFERENCE_MAPPING')
  after=geometry_fingerprint(d['asset']);assert before==after and sha(c['gaussians'])==c['input_files'][c['gaussians']]
  js(root/'GEOMETRY_AUDIT.json',dict(fields_before=before,fields_after=after,unchanged=True,original_rows=c['kernel_count'],original_row_order=True,source_sha256=c['input_files'][c['gaussians']],no_carrier_ink=True))
  cams0=json.loads(Path(c['cameras']).read_text())[c['scene']];cams=[next(v for v in cams0 if v['view']==name) for name in c['views']];render=renderer(c)
  for arm,(m,gs) in saved.items():
   out=control if arm=='NO_FURTHER_GROWTH' else reference if arm=='M5_REFERENCE' else Path(outputs[arm]['stage']);imgs=render_arm(out,c,d,m,gs,[],render,cams,lambda:lim.guard('delivery'),full_only=True)
   js(out/'FULL_NATIVE_CHECKPOINT.json',dict(complete=True,files={k:sha(out/k) for k in imgs+['DISPLAY_SOURCE.json','DISPLAY_COLORS.npz']}));facts['completed'].append(arm+'_FULL_NATIVE')
   if arm in outputs:outputs[arm]['full_images']=imgs
  facts['delivery_gate']=True;incremental={}
  reference_statistics(reference,c,raw,*saved['M5_REFERENCE'],lambda:lim.guard('delivery'))
  for arm in ['NO_FURTHER_GROWTH',*ARMS]:
   out=control if arm=='NO_FURTHER_GROWTH' else Path(outputs[arm]['stage']);st=starting if arm=='NO_FURTHER_GROWTH' else states[arm]
   incremental[arm]=statistics(out,c,d,*saved[arm],st,starting,lambda:lim.guard('delivery'))
  visual_ids,receipt=choose_visuals(c,d,incremental,saved);js(scene/'VISUAL_SELECTION.json',receipt)
  # Donor-only fixed contexts use their whole original rows and the complete root query halo.
  focus=set(contexts.get(c['focus_seed'],set()))
  for sid in c['focus_carriers']:contexts.setdefault(sid,set()).update(focus|{sid})
  for seed,donor in c['contact_focus_pairs']:contexts.setdefault(donor,set()).update(contexts.get(seed,set())|{seed,donor})
  vc=copy.deepcopy(c);vc['seeds']=[[i,d['original_leaves'][i].version] for i in visual_ids]
  facts['diagnostic_images']=diagnostics(root,vc,d,saved,contexts,render,cams,lambda:lim.guard('delivery'))
  js(scene/'COMPARISON.json',dict(different_labels={a+'__'+b:int(np.sum(saved[a][0]['edge_id']!=saved[b][0]['edge_id'])) for a,b in [('BASE','OBS_HISTORY'),('BASE','PAIRED_HISTORY'),('OBS_HISTORY','PAIRED_HISTORY')]},shared_initial_state=True,same_state_history_shadows=True,representation_fixed_ARC_HERMITE=True,only_history_evidence_changed=True,rollout_candidates_may_diverge=True,physical_correctness=False,prior_accepted_is_ground_truth=False))
  js(scene/'READINESS.json',dict(rows=c['kernel_count'],initial_assigned=c['initial_assigned'],initial_next_version=starting['next_version'],seed_ids=seedids,starting_membership_exact=True,global_search=False,tracer_protects_original_leaf_members=True,initial_catalog_complete=catalog_complete))
  verify(c['source_files']);verify(c['helper_files']);facts['status']='completed' if catalog_complete and all(x['stop_reason']=='frontiers_exhausted' for x in outputs.values()) else 'partial'
 except BaseException as exc:error=exc;facts.update(status='partial' if facts['completed'] else 'blocked',error=repr(exc),traceback=traceback.format_exc())
 finally:
  facts.update(ended_utc=now(),elapsed_seconds=time.monotonic()-lim.start,actual_pngs=[str(p.relative_to(root)) for p in sorted(root.glob('scenes/**/*.png'))],parent_exit_authoritative=True)
  if not (root/'RUN_RESULT.json').exists():js(root/'RUN_RESULT.json',facts)
  lim.close()
 if error:raise error
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();run(json.loads(Path(args.config).read_text()),args.config)
