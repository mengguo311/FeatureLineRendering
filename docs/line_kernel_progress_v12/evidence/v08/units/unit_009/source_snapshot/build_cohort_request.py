"""Unit006 metadata-only freeze; no Gaussian loading, selection, science or render."""
from pathlib import Path
import copy,hashlib,json,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102');P=O/'units/unit_005';U=O/'units/unit_006'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,obj):
 with Path(p).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
prior='b32439c9b9ffa9e9a8de9beb9d449176ee82ca8165e6cee8cc92422f39e851ab'
assert sha(P/'CONFIG.json')==prior
c=copy.deepcopy(read(P/'CONFIG.json'));frozen=read(P/'PARENT_RUN_FROZEN.json');assert frozen['config_sha256']==prior
window=read(O/'orchestration/WINDOW.json');inputs=dict(c['input_files']);snapshots={}
for original,path in frozen['immutable_source_snapshot'].items():
 h=frozen['source_files'][original];assert sha(path)==h;assert sha(S/Path(path).name)==h,'Inherited source modified';inputs[path]=h;snapshots[Path(path).name]=dict(path=path,sha256=h)
for name in ['CONFIG.json','DECISION.json','PARENT_RUN_FROZEN.json','FAILURE_ANALYSIS.json','NEXT.json']:
 path=P/name;inputs[str(path)]=sha(path)
initial=P/'scenes/ficus/stages/BASE_FINAL';cp=read(initial/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior
assert cp['files']['MEMBERSHIP.npz']=='f063a792c48aec5c70e65833ad38c6d458e7049f019afc965e6d7c1480e40709'
assert cp['files']['GROWTH_STATE.json']=='78917390ee23521289433db4f23ece4585a2b6acd58f304dc8f35fc161d9fb61'
for root in [initial,P/'scenes/ficus/observation_bank']:
 cc=read(root/'CHECKPOINT.json');assert cc['complete'] and cc['config_sha256']==prior;inputs[str(root/'CHECKPOINT.json')]=sha(root/'CHECKPOINT.json')
 for name,h in cc['files'].items():assert sha(root/name)==h;inputs[str(root/name)]=h
visits=sorted((P/'scenes/ficus/visits/BASE').glob('*.json'));assert len(visits)==8
for path in visits:inputs[str(path)]=sha(path)
for arm in ['BASE','HISTORY']:
 path=P/'scenes/ficus/stages'/(arm+'_FINAL')/'MEMBERSHIP.npz';inputs[str(path)]=sha(path);c['external_memberships']['unit005_'+arm]=str(path)
for name in ['groups','lineage','carriers']:
 path=Path(c[name]);assert sha(path)==c['input_files'][str(path)]
assert sha(c['lineage'])=='e9539992b647d284e8ef7ded8967a55a753536611d7ac2356a8f17d99d8c2e38'
assert sha(c['groups'])=='8928748f4a7beab55b40f7ca5da1bedf8d0e8fc02a638491b0bdc9e3876adc7a'
assert sha(c['carriers'])=='2aab72ee0e05e690112674d7c9ff0cdb591c484742fa623c86c2f92b710ca0ad'
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),initial_stage=str(initial),initial_assigned=121987,initial_next_version=20582,prior_config_sha256=prior,prior_observation_bank=str(P/'scenes/ficus/observation_bank'),observation_bank=str(U/'scenes/ficus/observation_bank'),prior_base_visits=[str(p) for p in visits],absolute_deadline_jst=window['science_wrap_jst'],max_seconds=1800)
assert c['absolute_deadline_jst']=='2026-11-02T07:38:00+09:00'
c['fixed_seeds']=copy.deepcopy(c['seeds'])
c['cohort']=dict(per_kind_cap=16,total_with_fixed_cap=36,selection_stage='parent compute before any new frontier search',candidate_condition='active exact M5 endpoint event output ID/version; GROUPS.valid;>=2 M4 contributions each>=12 kernels and mapped_supported_length_p>=2; not starting used leaf',strata=['line','polyline'],ranking=['saved supported_length_p descending','carrier ID ascending'],no_replacement_after_validation_failure=True,queue_frozen_before_continuation_results=True,original_four_seeds_retained=True,new_seed_version='original M5 version until first accepted transaction',initial_membership='all fields equal saved unit005 BASE_FINAL',auxiliary_geometry='new seeds use unchanged unit003 q_obs/ports; prior composite seams retained',complete_initial_frontier_library_required_before_promotion=True,cache_reuse='exact seed version and full used-leaf set match',seed_protection_changes_available_donors=True,selection_scope='all saved metadata considered; at most32 new decision seeds; unselected range explicit')
c['switch']['initial_state']='exact unit005 BASE_FINAL plus pre-frozen new M5 seed metadata; no initial relabel or version allocation'
c['switch']['reopen_all_eight_ports']=True
c['switch']['reopen_policy']='all fixed and new valid seed ports; original four replayed before extra protection; invalid new seeds NOT_RUN'
c['settings']['scientific_stop']='64 NEW attempts/arm;8 NEW accepts/seed; capacity or deadline; no seed replacement'
c['settings']['seed_evidence']='M5 saved endpoint-merge provenance and two substantial M4 support contributions; not physical truth'
c['settings']['initialization_membership_invariant']='all fields exact against saved unit005 BASE_FINAL; no growth is inferred from extra seed metadata'
c['visual_policy']=dict(views=c['views'],fixed_seeds=c['fixed_seeds'],negative_pairs=c['negative_pairs'],new_cases='top3 line and top3 polyline by max across arms outward support beyond starting auxiliary q, then ID; top3 new seed assignment damage by lost/reassociated starting rows then ID; zero damage explicit',same_rows_and_complete_query_context=True,union_bbox_pad_pixels=16,nearest_scale=4,white_floor=.0144,only_original_gaussian_ink=True,empty_views='explicit missing evidence',source_surface_occlusion=False)
c['budgets']=dict(readiness_seconds=120,growth_stop_seconds=1200,delivery_reserved_seconds=600,total_seconds=1800,max_new_attempts_per_arm=64,max_new_accepts_per_seed=8,cpu_blas_threads=2,unit_output_bytes=2*2**30,runtime_output_bytes=20*2**30)
c['source_provenance']['unit005_snapshot']=snapshots;c['input_files']=inputs
for k,v in dict(legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False).items():assert c[k]==v
for path,h in c['helper_files'].items():assert sha(path)==h
t=U/'tests';exitinfo=read(t/'TEST_EXIT.json');redinfo=read(t/'RED_EXIT.json');assert exitinfo['returncode']==0 and redinfo['returncode']!=0;assert read(t/'CLI_HELP_EXIT.json')['returncode']==0
assert 'Items in the second set but not the first' in (t/'RED.log').read_text() and 'FAILED' in (t/'RED.log').read_text()
assert 'Ran 29 tests' in (t/'GREEN_VERIFIED.log').read_text() and (t/'GREEN_VERIFIED.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: initial adapter retained prior seed set and failed the new-seed registration assertion; implemented metadata augmentation passes that same test. 28 further bounded regression/adapter checks pass; no claimed scientific result.',red=dict(**redinfo,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),baseline_source=str(t/'RED_cohort_core.py'),baseline_source_sha256=sha(t/'RED_cohort_core.py'),test_source=str(t/'RED_test_cohort.py'),test_source_sha256=sha(t/'RED_test_cohort.py')),green=dict(**exitinfo,log=str(t/'GREEN_VERIFIED.log'),sha256=sha(t/'GREEN_VERIFIED.log')),test_exit_receipt=dict(path=str(t/'TEST_EXIT.json'),sha256=sha(t/'TEST_EXIT.json')),real_loader_callback_test=True,real_loader_runner_fixture_kernels=48,full_asset_science_run=False,render_run=False,renderer_boundary='48-kernel real-loader runner fixture deliberately raises before obtaining renderer; mappings and initial-library freeze asserted first',cli_help_returncode=0,cli_help_log=str(t/'CLI_HELP.log'),test_scope='synthetic <=48 kernels; real restricted loader/checkpoint/restoration, queue ranking and versions, no-fill failure, seed protection, rollback; all test writes under unit006',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c);py=window['python'];r=dict(script=str(S/'cohort_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'),python=py,command=[py,'-B',str(S/'cohort_runner.py'),'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',r)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=r['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),helper_files=len(c['helper_files']),input_files=len(inputs))))
