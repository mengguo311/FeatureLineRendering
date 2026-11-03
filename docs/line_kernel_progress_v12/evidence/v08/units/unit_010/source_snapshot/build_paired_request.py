"""Unit010 metadata-only freeze. No numerical asset loading or science launch."""
from pathlib import Path
import copy,hashlib,json,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102')
P=O/'units/unit_009';U=O/'units/unit_010'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,obj):
 with Path(p).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
prior='20ac45ad5de9f863a868d1e74a00a58a73b973081619f3a7032133dc0c89281b'
initial_binding='2dad2b4994628a645dde9cd0d0532298160903cd204020953e90810483a06987'
assert sha(P/'CONFIG.json')==prior
c=copy.deepcopy(read(P/'CONFIG.json'));frozen=read(P/'PARENT_RUN_FROZEN.json');assert frozen['config_sha256']==prior
window=read(O/'orchestration/WINDOW.json');inputs=dict(c['input_files']);snapshots={}
for original,path in frozen['immutable_source_snapshot'].items():
 h=frozen['source_files'][original];assert sha(path)==h
 assert sha(S/Path(path).name)==h,'Inherited source changed'
 inputs[path]=h;snapshots[Path(path).name]=dict(path=path,sha256=h)
for name in ['CONFIG.json','DECISION.json','PARENT_RUN_FROZEN.json','FAILURE_ANALYSIS.json','NEXT.json','scenes/ficus/INITIAL_LIBRARY_FREEZE.json']:
 path=P/name;inputs[str(path)]=sha(path)
def bind_checkpoint(root,binding):
 cp=read(root/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==binding
 inputs[str(root/'CHECKPOINT.json')]=sha(root/'CHECKPOINT.json')
 for name,h in cp['files'].items():assert sha(root/name)==h;inputs[str(root/name)]=h
 return cp
initial=P/'scenes/ficus/stages/NO_FURTHER_GROWTH';cp=bind_checkpoint(initial,initial_binding)
assert cp['files']['MEMBERSHIP.npz']=='365dfc05f91447be2213c5a6bf2a1e36fd8961679f50dfb261e48c781d66bab3'
assert cp['files']['GROWTH_STATE.json']=='71d5a5ca6868258b1d767b02145764d98ebcf6f5e47ee29c9671b25df5ada369'
bind_checkpoint(P/'scenes/ficus/observation_bank',prior)
st=read(initial/'GROWTH_STATE.json');assert len(st['chains'])==24 and len(st['events'])==3 and st['next_version']==20583
assert sorted(map(int,st['chains']))==sorted(x[0] for x in c['seeds'])
replays=[]
for sid in sorted(map(int,st['chains'])):
 for side in (0,1):
  path=P/'scenes/ficus/initial_libraries'/f'ARC_{sid}_{side}.json';z=read(path)
  assert z['seed']==sid and z['side']==side and z['status']=='COMPLETE'
  inputs[str(path)]=sha(path);replays.append(str(path))
controls={}
for arm,oldarm in [('BASE','BASE'),('OBS_HISTORY','OBS_HISTORY')]:
 root=P/'scenes/ficus/stages'/(oldarm+'_FINAL');bind_checkpoint(root,prior)
 controls[arm]=dict(stage=str(root),config_sha256=prior)
for oldarm in c['arms']:
 path=P/'scenes/ficus/stages'/(oldarm+'_FINAL')/'MEMBERSHIP.npz';inputs[str(path)]=sha(path);c['external_memberships']['unit009_'+oldarm]=str(path)
focus=sorted(set(c['focus_carriers'])|{79841,177351,79855,50407,83549,79865})
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),initial_stage=str(initial),initial_assigned=122004,initial_next_version=20583,prior_config_sha256=initial_binding,prior_observation_config_sha256=prior,source_predecessor_config_sha256=prior,prior_observation_bank=str(P/'scenes/ficus/observation_bank'),observation_bank=str(U/'scenes/ficus/observation_bank'),absolute_deadline_jst=window['science_wrap_jst'],max_seconds=1800,replay_libraries=replays,control_reproductions=controls,arms=['BASE','OBS_HISTORY','PAIRED_HISTORY'],focus_carriers=focus)
c['cohort_policy']['selection']='exact24 saved unit009 NO_FURTHER_GROWTH chains; no reselection'
c['switch']['initial_state']='exact unit009 NO_FURTHER_GROWTH, bound to unit007 config; no initial relabel/version allocation'
c['settings']['initialization_membership_invariant']='all fields exact against unit009 NO_FURTHER_GROWTH'
c['settings']['whole_path_geometry']='unchanged ARC/Hermite all-member, finite-domain, turn, contact, parallel, branch and support tests'
c['seam']['representations']=['HERMITE'];c['seam']['representation_shadows']='fixed ARC/Hermite; three history-policy shadow choices at every state'
c['seam']['initial_catalog']='all48 common ARC frontier libraries with both history evidence diagnostics before promotion'
c['contact']['policies']=['ARC'];c['contact']['contact_guard_definition_changed']=False
c['contact']['scope']='unchanged unit008 ARC final proposed-Q contact; unchanged observation-bank validity'
c['contact']['minimal_relay_prefixes_may_differ']=False
c['history_evidence']['policies']=['BASE','OBS_HISTORY','PAIRED_HISTORY']
c['history_evidence']['mixed_estimator_unchanged']=True
c['paired_history']=dict(pair_key='primitive_id',all_shared_source_ids_required=True,source_ids_are_physical_identity=False,full_bin_axes_unchanged=True,source_bins=['near','far'],donor_bins=['first','second'],min_distinct_paired_rows_per_bin=3,per_source_min_rows_per_bin=1,parameter='original arc_t',parameter_order='disjoint ranges within EPS in either orientation; both directions or neither valid -> UNKNOWN',axis='mean normalized derivative outer-products per source/bin; unchanged eigenvalue and directed-q sign tests',any_weak_source='whole history UNKNOWN; no selective source removal',weight='min(n_g0,n_g1), fixed across two bins',source_increment='weighted mean(axis_near-axis_far)',donor_increment='weighted mean(axis_second-axis_first)',current_orientation='unchanged full-bin t0,u0 including unpaired rows',prediction='normalize(t0+gap*kS)',prediction_angle_deg=15.,curvature_difference_max='2*sin(7.5 degrees)',EPS=1e-8,overlap_gap_p=0.,endpoint_gap='first gap',fallback=False,recompute_after_each_acceptance=True,save=['all paired/unpaired source IDs','row IDs','arc_t ranges','counts','weights','tensors','eigenspectra','signs','axes','increments','UNKNOWN reasons'])
whole=Path('/home/u00134/3dgs_line/gaer_rade_depth_lift_v01/reproduction/radegs_depth_guided_native_dtu_v01/whole.py')
assert sha(whole)=='39e843fc4bd35c62e21282acc81eb9b6c8c837cead00499f03b84c014f058934'
inputs[str(whole)]=sha(whole)
assert inputs[c['controls']]=='0010535c3f30ce54021b10b6f284508fd04fb57baa099cdc7da91b540553b20a'
c['control_identity']=dict(expected=dict(controls=73330,pieces=61829,parents=11503),rows=285956,matching_fields=['primitive_id','internal_piece_id','arc_t'],piece_rule='control_index==piece_control_indices[internal_piece_id]',parent_rule='both control indices inside half-open parent_control_offsets[primitive_id]',basis_and_parameters_finite=True,center_rtol=0,center_atol=1e-10,whole_sampling_provenance=dict(path=str(whole),sha256=sha(whole),producer_executed=False),failure='block comparison')
c['control_replay_policy']=dict(initial_libraries=48,strip_only_new_fields=['paired_history'],original_shadow_policies=['BASE','SECANT_HISTORY','OBS_HISTORY'],reexecute_controls=['BASE','OBS_HISTORY'],control_state_fields=['all membership fields','curves','chains','versions','next_version','events','used','metrics','ports'],mismatch='block comparison and retain saved partial checkpoints')
c['visual_policy'].update(focus_carriers=focus,all_four_arms=False,all_three_arms=True,preserve_later_deadends=[50407,83549,79865],inherited_seeds_and_negatives=True)
c['budgets'].update(total_seconds=1800,growth_stop_seconds=1200,delivery_reserved_seconds=600,readiness_seconds=120,max_new_attempts_per_arm=64,max_new_accepts_per_seed=8)
c['source_provenance']['unit009_snapshot']=snapshots;c['input_files']=inputs
assert c['absolute_deadline_jst']=='2026-11-02T07:38:00+09:00'
for k,v in dict(legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False).items():assert c[k]==v
for path,h in c['helper_files'].items():assert sha(path)==h
for path,h in inputs.items():assert sha(path)==h,('INPUT_BINDING',path)
t=U/'tests';red=read(t/'RED_EXIT.json');green=read(t/'FINAL_TEST_EXIT.json');cli=read(t/'CLI_HELP_EXIT.json')
assert red['returncode']==1 and green['returncode']==0 and cli['returncode']==0
assert 'AssertionError: False is not true' in (t/'RED.log').read_text()
assert 'Ran 61 tests' in (t/'GREEN_FINAL.log').read_text() and (t/'GREEN_FINAL.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: mixed increments reject a composition-shift fixture with zero within-source turn; paired increments pass while preserving full-bin orientation. 61 bounded tests passed; true within-source turn, parameter reversal/overlap, all-source weakness, missing paired rows, actual loader/schema, three-arm checkpoint/control replay, two accepted paired-growth transactions and complete rollback are covered.',red=dict(**red,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),baseline_source=str(t/'RED_paired_history_core.py'),baseline_source_sha256=sha(t/'RED_paired_history_core.py')),green=dict(green,log=str(t/'GREEN_FINAL.log'),sha256=sha(t/'GREEN_FINAL.log')),test_exit_receipt=dict(path=str(t/'FINAL_TEST_EXIT.json'),sha256=sha(t/'FINAL_TEST_EXIT.json')),earlier_attempts=[dict(log=str(t/name),sha256=sha(t/name),returncode=rc) for name,rc in [('GREEN_CORE_1.log',0),('GREEN_1.log',1),('GREEN_2.log',0),('GREEN_VERIFIED.log',0)]],cli_help=dict(**cli,log=str(t/'CLI_HELP.log'),sha256=sha(t/'CLI_HELP.log')),real_loader_callback_test=True,real_runner_fixture_kernels=48,full_asset_science_run=False,render_run=False,test_scope='explicit classes; all test outputs unit010; no historical discovery',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};write(U/'CONFIG.json',c)
py=window['python'];script=str(S/'paired_history_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'),python=py,command=[py,'-B',script,'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),helper_files=len(c['helper_files']))))
