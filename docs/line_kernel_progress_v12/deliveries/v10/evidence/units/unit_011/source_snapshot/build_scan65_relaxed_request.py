"""Unit004 metadata freeze only: no asset loading, fitting or rendering."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103')
U=O/'units/unit_004';P=O/'units/unit_003'
V=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_best_fragment_growth_v09_20261102/continuation_001/units/unit_003')
F=V/'scenes/scan65/stages/TRANSPORT_BRANCH_FINAL'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with Path(p).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)

prior_hash='925b56d91889220832e54cda5273f57055c68b976cf8a096f8bd64b79f8b3453'
scene_hash='f344d0f0f3ee6cd6ef968ab4924440660fd1d0c121ffb8083959d2b2e6c198f1'
assert sha(P/'CONFIG.json')==prior_hash and sha(V/'CONFIG.json')==scene_hash
prior=read(P/'CONFIG.json');c=copy.deepcopy(read(V/'CONFIG.json'));window=read(O/'orchestration/WINDOW.json');freeze=read(P/'PARENT_RUN_FROZEN.json');inputs=c['input_files']
def bind(p,h=None):
 p=Path(p).resolve();actual=sha(p)
 if h is not None:assert actual==h,str(p)
 inputs[str(p)]=actual;return str(p)
reused={}
for old,snapshot in freeze['immutable_source_snapshot'].items():
 h=freeze['source_files'][old];bind(snapshot,h);name=Path(old).name;assert sha(S/name)==h,name;reused[name]=h
assert len(reused)==49
for p in [P/'CONFIG.json',P/'PARENT_RUN_FROZEN.json',V/'CONFIG.json',V/'PARENT_RUN_FROZEN.json',V/'RUN_RESULT.json',V/'GEOMETRY_AUDIT.json']:bind(p)
cp=read(F/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==scene_hash;bind(F/'CHECKPOINT.json')
for name,h in cp['files'].items():bind(F/name,h)
assert sha(F/'MEMBERSHIP.npz')=='252d9a2875a23fda6792d116ba08587c7e31368972924307e0609e05b10dc249'
groups=read(F/'GROUPS.json')['groups'];versions={str(g['id']):g['version'] for g in groups}
assert versions=={'5558':21661,'22130':21667,'64111':21668,'156151':21665,'238627':21651}
lin=read(F/'LINEAGE.json');assert lin['next_version']==21669 and len(lin['historical'])==1759 and len(lin['events'])==1
assert c['kernel_count']==279616 and c['p']==.001725801957946726
assert c['control_identity']['expected']==dict(controls=71227,pieces=62356,parents=8874)
assert c['predecessor_checkpoint_stage']=='M4_STATE'
policies={'R2_R4_OFF_TRANSPORT':[2,4],'R2_R4_R6_OFF_TRANSPORT':[2,4,6]};arms=list(policies)
for key in ['replay_libraries','control_replay_libraries','archived_control_stage','archived_control_binding','archived_control_compute_exit','control_state_expected_unchanged']:c.pop(key,None)
c.update(unit_root=str(U),runtime_root=str(O/'orchestration'),unit=str(U),runtime=str(O),restore_stage=str(F),restore_binding=scene_hash,initial_stage=str(F),initial_assigned=126428,initial_unknown=153188,initial_next_version=21669,seed_versions=versions,arms=arms,executed_arms=arms,catalog_policies=arms,arm_policies=policies,relaxed_rule_groups=[2,4,6],max_seconds=1800,science_deadline=window['science_wrap_jst'],absolute_deadline_jst=window['science_wrap_jst'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(P/'source_snapshot'),helper_files=freeze['helper_files'],legacy_groups_locked=True,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False,membership_policy='monotone_group_union',whole_curve_auxiliary_update=True,stop_policy='until_no_connection_or_supported_closed')
assert window['science_wrap_jst']=='2026-11-03T05:35:00+09:00'
c['settings']=copy.deepcopy(prior['settings'])
c['settings'].update(seed_scope=c['seed_ids'],whole_object_mapping_rows=c['kernel_count'],background_reference=str(F),unknown_partition='original M4 carrier',coordinate_scale_p=c['p'])
c['settings']['relation_diagnostics']=dict(per_donor_all_interpretations=True,original_rows_file='RELATION_ROWS.npz',both_policy_same_state=True,score_components=True,U_zero_vs_endpoint_competition=True,early_guard_failures='NOT_REACHED',decision_effect=False)
c['budgets']=dict(readiness_seconds=120,initial_catalog_seconds=180,growth_seconds_per_arm=450,delivery_seconds=600,total_seconds=1800,both_arms_newly_executed=True,actual_phase_elapsed_required=True,absolute_science_deadline=window['science_wrap_jst'])
c['external_memberships']['v09_TRANSPORT_FINAL']=bind(F/'MEMBERSHIP.npz')
c['visual_policy'].update(arms=arms,worst_events='top3 maximum member error and size plus first pure_pooling/gap_exceeded/self_contact',inherited_long_arc_challenge=238627,unavailable_reference_controls='No executed scan65 M5/v06; use START/M4/M3/unit009 prefix/unit014 joint contingencies')
c['historical_control']='Old strict TRANSPORT terminal is provenance only. Both [2,4] and [2,4,6] newly execute from same restored terminal; neither is required to choose zero.'
c['initial_catalog_policy']='Both policies complete five common template/fit catalogs before any promotion. Same-state choices and all relation diagnostics saved at every visit. Later rollout divergence explicit.'
c['source_provenance']=dict(latest_frozen_source=str(P/'source_snapshot'),latest_snapshot_binding=sha(P/'PARENT_RUN_FROZEN.json'),v10_copied_source_manifest=str(U/'SOURCE_REUSE_PROVENANCE.json'),all_49_prior_files_byte_identical=True,changed_new_copies=[],new_modules=['scan65_relaxed_core.py','scan65_relaxed_runner.py','scan65_relaxed_delivery.py','test_scan65_relaxed.py','build_scan65_relaxed_request.py'],old_outputs_edited=False,v08_unit012_used=False,old_producers_executed=False,old_deadlines_imported=False,raw_scan65_loader='branch_loader -> scan65_loader -> paired_loader -> restricted M4_STATE',inherited_u11_and_v09_provenance=prior['source_provenance'])
for name in ['input_files','helper_files']:
 for p,h in c[name].items():assert sha(p)==h,(name,p)
t=U/'tests';red=read(t/'RED_EXIT.json');green=read(t/'GREEN_EXIT.json');cli=read(t/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==cli['returncode']==0 and green['test_count']==26
assert 'same-donor relation evidence missing' in (t/'RED.log').read_text()
assert (t/'GREEN.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,test_count=26,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN for same-donor relation/row/score accounting and unchanged choices. Two new integration tests added after first GREEN. 23 inherited core/strict-parity/relaxation/union/rollback regressions reused, not new TDD.',red=dict(red,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),test_source=str(t/'RED_test_scan65_relaxed.py'),test_source_sha256=sha(t/'RED_test_scan65_relaxed.py'),baseline_source=str(t/'RED_r6_core.py'),baseline_source_sha256=sha(t/'RED_r6_core.py')),green=dict(green,log=str(t/'GREEN.log'),sha256=sha(t/'GREEN.log')),cli=dict(cli,log=str(t/'CLI.log'),sha256=sha(t/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,native_render=False,scope='36-row real restricted M4/control/composite loader; both new arms through complete cold maps before deliberately stopping at renderer. Geometric fixtures include >8 merges, unchanged kernels, union and rollback.',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'SOURCE_REUSE_PROVENANCE.json',dict(parent_manifest=str(P/'PARENT_RUN_FROZEN.json'),parent_manifest_sha256=sha(P/'PARENT_RUN_FROZEN.json'),snapshot_files_verified=49,byte_identical_existing_files=reused,modified_new_copy={},old_files_edited=False))
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};write(U/'CONFIG.json',c)
script=str(S/'scan65_relaxed_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],tests_receipt=str(U/'TESTS_RECEIPT.json'),max_seconds=1800,python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),request=str(U/'RUN_REQUEST.json'),command=request['command'])))
