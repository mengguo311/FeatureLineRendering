"""Unit010 metadata/hash freeze only; no full asset loading, fitting or rendering."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103')
U=O/'units/unit_010';P=O/'units/unit_009';F=P/'scenes/scan65/stages/GROUP_BALANCED_FIT_0071'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with Path(p).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)
prior_hash='b7bd482602aff3be2cebf1b25cf6370614193e176c7908abaf36028957e3e258'
assert sha(P/'CONFIG.json')==prior_hash
prior=read(P/'CONFIG.json');c=copy.deepcopy(prior);inputs=c['input_files'];window=read(O/'orchestration/WINDOW.json');freeze=read(P/'PARENT_RUN_FROZEN.json')
def bind(p,h=None):
 p=Path(p).resolve();actual=sha(p)
 if h is not None:assert actual==h,str(p)
 inputs[str(p)]=actual;return str(p)
reused={}
for old,snapshot in freeze['immutable_source_snapshot'].items():
 h=freeze['source_files'][old];bind(snapshot,h);name=Path(old).name
 assert sha(S/name)==h,name
 reused[name]=h
assert len(reused)==78
for name in ['CONFIG.json','PARENT_RUN_FROZEN.json','RUN_RESULT.json','GEOMETRY_AUDIT.json','FAILURE_ANALYSIS.json','NEXT.json','SAVED_OUTPUT_AUDIT.json']:bind(P/name)
cp=read(F/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior_hash;bind(F/'CHECKPOINT.json')
for name,h in cp['files'].items():bind(F/name,h)
assert sha(F/'MEMBERSHIP.npz')=='34f0bc3d1e440ca8d52dae22c442f740c980a95409be80283b7d6b11dcb7db3f'
groups=read(F/'GROUPS.json')['groups'];versions={str(g['id']):g['version'] for g in groups};counts={str(g['id']):len(g['rows']) for g in groups}
assert versions=={'13285':21775,'30579':21776,'84607':21777,'136538':21749,'162227':21724,'233067':21778,'5558':21692,'22130':21686,'64111':21683,'156151':21665,'238627':21707}
assert counts['30579']==586
lin=read(F/'LINEAGE.json');assert lin['next_version']==21779 and len(lin['historical'])==1799 and len(lin['events'])==71
exit_path=O/'orchestration/unit_009/COMPUTE_EXIT.json';actual_exit=read(exit_path)
assert actual_exit['returncode']==0 and actual_exit['reason'] is None and actual_exit['actual_child_exit'];bind(exit_path)
folder=P/'scenes/scan65/libraries/GROUP_BALANCED_FIT/0091_30579'
for p in sorted(folder.rglob('*')):
 if p.is_file():bind(p)
lib=read(folder/'LIBRARY.json')
assert lib['complete'] and lib['selected']==327 and len(lib['neighbors'])==85 and len(lib['records'])==510 and sum(r['connectable'] for r in lib['records'])==40
final=P/'scenes/scan65/stages/GROUP_BALANCED_FIT_FINAL';fc=read(final/'CHECKPOINT.json');assert fc['config_sha256']==prior_hash;bind(final/'CHECKPOINT.json')
for name,h in fc['files'].items():bind(final/name,h)
for name in ['STOP.json','METRICS.json']:bind(final/name)
fl=read(final/'LINEAGE.json');assert len(fl['events'])==74
event=fl['events'][71];assert event['sequence']==72 and event['group']==30579 and event['donor']==-30821
lastlib=P/'scenes/scan65/libraries/GROUP_BALANCED_FIT/0097_30579'
if lastlib.exists():
 for p in sorted(lastlib.rglob('*')):
  if p.is_file():bind(p)
active=[30579];raw_ids=[5558,22130,64111,156151,238627];tracked=sorted(map(int,versions));policies={'BASE_J':[2,4,6],'CONTACT_SOFT_J':[2,4,6]}
c.update(unit_root=str(U),runtime_root=str(O/'orchestration'),unit=str(U),runtime=str(O),restore_stage=str(F),restore_binding=prior_hash,initial_stage=str(F),initial_assigned=127000,initial_unknown=152616,initial_next_version=21779,raw_seed_ids=raw_ids,restore_seed_versions=versions,seed_ids=active,seed_versions={'30579':21776},seed_expected_rows={'30579':586},tracked_origin_ids=tracked,arms=list(policies),executed_arms=list(policies),catalog_policies=list(policies),arm_policies=policies,relaxed_rule_groups=[2,4,6],max_seconds=1320,science_deadline=window['science_wrap_jst'],absolute_deadline_jst=window['science_wrap_jst'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(P/'source_snapshot'),helper_files=freeze['helper_files'],control_replay_libraries={'30579':str(folder/'LIBRARY.json')})
for name in ['restore_seed_ids','expected_selection_counts']:c.pop(name,None)
assert c['scientific_contract']['action']=='continue' and window['science_wrap_jst']=='2026-11-03T05:35:00+09:00'
assert c['scene']=='scan65' and c['kernel_count']==279616 and c['p']==.001725801957946726
assert c['control_identity']['expected']==dict(controls=71227,pieces=62356,parents=8874) and c['predecessor_checkpoint_stage']=='M4_STATE'
c['seed_policy']=dict(kind='restore all eleven checkpoint composites without reselection, retagging, or initial version allocation',active=active,raw_loader_cohort=raw_ids,tracked_origins=tracked,expected_versions=versions,expected_rows=counts,other_composites_remain_whole_eligible_donors=True,no_replacement=True)
settings=c['settings'];settings['background_reference']=str(F);settings['seed_scope']=active
settings['fit'].update(policy='WHOLE every knot movable; both score policies use the identical GROUP_BALANCED_FIT Q; separate ROW_FIT shadow only',position_by_policy={p:'.5 mean_G Huber rho + .5 mean_F Huber rho' for p in policies},matrix_row_factor_by_policy={p:'sqrt(h_i/(4*n_H))' for p in policies},row_fit_shadow=dict(position='mean_union Huber rho',matrix_row_factor='sqrt(h_i/(2*N))',executed_rollout=False))
settings['score_by_policy']={'BASE_J':settings['score'],'CONTACT_SOFT_J':settings['score']+' + .01*I(existing final-Q rule6.self_contact)'}
settings['unique_support_reward_coefficient']={p:0. for p in policies}
settings['contact_soft_coefficient']={'BASE_J':0.,'CONTACT_SOFT_J':.01}
settings['contact_soft_policy']=dict(existing_diagnostic_only=True,recompute_contact=False,missing_diagnostic='PARTIAL entire frontier',finite_penalty=True,contact_candidate_can_win_and_must_commit=True,earlier_failures='NOT_REACHED; no fabricated score',no_other_new_penalties=True)
settings['group_balanced_score']['fit_weights_unchanged']=True
for r in [2,4,6]:settings['connectability'][f'rule{r}_hard_enabled_by_arm']={p:False for p in policies}
c['fixed_reference_stages']={'UNIT010_START':dict(stage=str(U/'scenes/scan65/stages/START'),binding='THIS_CONFIG_SHA256_RESOLVED_AT_RUNTIME')}
c['fixed_support_diagnostic'].update(references=c['fixed_reference_stages'],sets='all eleven immutable UNIT010 START origins; inherited/current/new separately; original derivative covariance widths',used_for_decision=False)
c['archived_counterexample']=dict(unit='unit009',library=str(folder),accepted_event=event,not_refitted_as_archived_evidence=True,previous_final=str(final),inherited_damage_row=214901,damage_not_claimed_improved_in_this_unit=True)
c['archived_transitions']=dict(unit='unit009',audit=str(P/'SAVED_OUTPUT_AUDIT.json'),audit_sha256=sha(P/'SAVED_OUTPUT_AUDIT.json'),partial_last_library=str(lastlib),reason='archived partial library with acute-fold rejects; not proof self-contact caused deadend',refitting_archived_acceptance=False,rule5_unchanged=True)
c['budgets']=dict(readiness_seconds=120,initial_catalog_seconds=120,growth_seconds_per_arm=300,delivery_seconds=480,total_seconds=1320,matched_base_rollout_executed=True,archived_row_fit_control_reexecuted=False,actual_phase_elapsed_required=True,absolute_science_deadline=window['science_wrap_jst'])
c['external_memberships']['unit009_PRE72']=bind(F/'MEMBERSHIP.npz');c['external_memberships']['unit009_FINAL_ARCHIVED_DIFFERENT_SCOPE']=bind(final/'MEMBERSHIP.npz')
c['historical_control']='Matched BASE_J and CONTACT_SOFT_J are both newly executed from the exact unit009 stage0071. NO_FURTHER_GROWTH copies that stage. unit006 ROW_FIT 17-step and unit009 six-seed 74-step trajectories are archived historical evidence, not matched new rollouts. All 1799 historical plus71 events are inherited.'
c['initial_catalog_policy']=dict(replay=str(folder/'LIBRARY.json'),expected_donors=85,expected_records=510,expected_connectable=40,expected_original_selection=327,exact_fields=['records','scores','rejections','q','template','local_movable','selection'],additional_diagnostics_ignored=True,freeze_both_before_promotion=True,share_main_fitted_geometry=True,separate_row_fit_shadow=True,mismatch_blocks=True)
c['visual_policy'].update(seed_ids=active,arms=list(policies),fixed_support='one immutable UNIT010 START reference for each of eleven tracked origins; never used for ranking',inherited_events=1870,matched_control=str(F),archived_counterexample=str(folder),comparison_competitors=[-30821,67269],inherited_damage_only=[214901])
new_modules=['contact_soft_core.py','contact_soft_loader.py','contact_soft_delivery.py','contact_soft_runner.py','test_contact_soft.py','build_contact_soft_request.py']
c['source_provenance']=dict(latest_frozen_source=str(P/'source_snapshot'),latest_snapshot_binding=sha(P/'PARENT_RUN_FROZEN.json'),v10_copied_source_manifest=str(U/'SOURCE_REUSE_PROVENANCE.json'),all_78_prior_files_byte_identical=True,changed_new_copies=[],new_modules=new_modules,old_outputs_edited=False,v08_unit012_used=False,old_producers_executed=False,old_deadlines_imported=False,raw_scan65_loader='contact_soft_loader -> branch_loader with original five raw IDs and all eleven restoration versions -> scan65_loader -> paired_loader -> restricted M4_STATE',inherited_u11_and_v09_provenance=prior['source_provenance'])
for section in ['input_files','helper_files']:
 for p,h in c[section].items():assert sha(p)==h,(section,p)
tests=U/'tests';red=read(tests/'RED_EXIT.json');green=read(tests/'GREEN_EXIT.json');cli=read(tests/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==cli['returncode']==0
assert 'existing actual library has no finite CONTACT_SOFT_J policy' in (tests/'RED.log').read_text()
assert 'Ran 44 tests' in (tests/'GREEN.log').read_text() and (tests/'GREEN.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,test_count=44,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: unchanged actual fitted library lacked CONTACT_SOFT_J; finite paired-score interface passes. Five additional unit010 tests added after first GREEN; 38 previous regression tests reused, not new TDD.',red=dict(red,log=str(tests/'RED.log'),sha256=sha(tests/'RED.log'),test_source=str(tests/'RED_test_contact_soft.py'),test_source_sha256=sha(tests/'RED_test_contact_soft.py'),baseline_source=str(P/'source_snapshot/group_fit_core.py'),baseline_source_sha256=sha(P/'source_snapshot/group_fit_core.py')),green=dict(green,log=str(tests/'GREEN.log'),sha256=sha(tests/'GREEN.log')),cli=dict(cli,log=str(tests/'CLI.log'),sha256=sha(tests/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,native_render=False,scope='actual 36-row M4/control checkpoint loader with distinct raw/tracked/active origins and guard(phase); exact scientific-library replay; .01 finite contact increment and contact winner commit; missing diagnostic PARTIAL; two full maps before intentional renderer boundary; >8 commits and no truncated winner/rollback; inherited eleven-origin cold checkpoint and strict/relaxed regressions',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'SOURCE_REUSE_PROVENANCE.json',dict(parent_manifest=str(P/'PARENT_RUN_FROZEN.json'),parent_manifest_sha256=sha(P/'PARENT_RUN_FROZEN.json'),snapshot_files_verified=78,byte_identical_existing_files=reused,modified_new_copy={},old_files_edited=False))
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
assert len(c['source_files'])==84
write(U/'CONFIG.json',c)
script=str(S/'contact_soft_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],tests_receipt=str(U/'TESTS_RECEIPT.json'),max_seconds=1320,python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')])
write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),request=str(U/'RUN_REQUEST.json'),command=request['command'])))
