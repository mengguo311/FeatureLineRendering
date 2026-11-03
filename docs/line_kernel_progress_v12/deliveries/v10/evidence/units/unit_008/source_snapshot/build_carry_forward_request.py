"""Unit008 metadata/hash freeze only; never runs full-data loader, fit or renderer."""
from pathlib import Path
import json,hashlib,copy,datetime,re
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103')
U=O/'units/unit_008';P=O/'units/unit_007';F=P/'scenes/scan65/stages/GROUP_BALANCED_FIT_FINAL';R=P/'scenes/scan65/stages/START'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with Path(p).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)
prior_hash='5f1d77acb511f72f78208d9cef310b9c819978c70b6d2307368f2bd1834837b1'
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
assert len(reused)==69
for p in [P/'CONFIG.json',P/'PARENT_RUN_FROZEN.json',P/'RUN_RESULT.json',P/'GEOMETRY_AUDIT.json',P/'FAILURE_ANALYSIS.json',P/'NEXT.json']:bind(p)
for stage in [F,R]:
 cp=read(stage/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior_hash
 bind(stage/'CHECKPOINT.json')
 for name,h in cp['files'].items():bind(stage/name,h)
assert sha(F/'MEMBERSHIP.npz')=='030f7025d5ce151dfde5ffd4e5d3aa6bbda055d5fc1586865480aa52dc63ccf1'
versions={str(g['id']):g['version'] for g in read(F/'GROUPS.json')['groups']}
assert versions=={'5558':21692,'22130':21686,'64111':21683,'156151':21665,'238627':21706}
lin=read(F/'LINEAGE.json');assert lin['next_version']==21707 and len(lin['historical'])==1760 and len(lin['events'])==38
stop=read(F/'STOP.json');assert stop['status']=='PARTIAL' and stop['reason']=='PHASE_DEADLINE GROUP_BALANCED_FIT'
bind(F/'STOP.json');bind(F/'METRICS.json');bind(F/'FULL_NATIVE_RECEIPT.json')
for name,h in read(F/'FULL_NATIVE_RECEIPT.json')['files'].items():bind(F/name,h)
exit_path=O/'orchestration/unit_007/COMPUTE_EXIT.json';actual_exit=read(exit_path)
assert actual_exit['returncode']==0 and actual_exit['reason'] is None and actual_exit['actual_child_exit'];bind(exit_path)
catalogs={}
for folder_name in ['0105_5558','0106_22130','0107_64111','0108_156151','0109_238627']:
 folder=P/'scenes/scan65/libraries/GROUP_BALANCED_FIT'/folder_name;gid=folder_name.split('_')[1]
 for p in sorted(folder.rglob('*')):
  if p.is_file():bind(p)
 lib=read(folder/'LIBRARY.json');catalogs[gid]=str(folder/'LIBRARY.json')
 if gid!='238627':assert lib['complete'] and lib['selected'] is None
 else:
  assert not lib['complete'] and len(lib['neighbors'])==37 and len(lib['records'])==199 and lib['records'][-1]['reason']=='template'
  assert lib['current_donor']==62128 and lib['unattempted_donors']==[62128,62168,201865,201942]
counter_event=lin['events'][14];assert counter_event['group']==64111 and counter_event['donor']==-274465 and counter_event['metrics']['rule6']['self_contact']
counter_lib=P/'scenes/scan65/libraries/GROUP_BALANCED_FIT'/f"{counter_event['library_visit']:04d}_{counter_event['group']}"
for p in counter_lib.iterdir():
 if p.is_file():bind(p)
counter_stage=P/'scenes/scan65/stages/GROUP_BALANCED_FIT_0015'
cp=read(counter_stage/'CHECKPOINT.json');bind(counter_stage/'CHECKPOINT.json')
for name,h in cp['files'].items():bind(counter_stage/name,h)
policies={'GROUP_BALANCED_SCORE':[2,4,6],'GROUP_BALANCED_FIT':[2,4,6]}
c.update(unit_root=str(U),runtime_root=str(O/'orchestration'),unit=str(U),runtime=str(O),restore_stage=str(F),restore_binding=prior_hash,initial_stage=str(F),initial_assigned=126611,initial_unknown=153005,initial_next_version=21707,seed_versions=versions,arms=['GROUP_BALANCED_FIT'],executed_arms=['GROUP_BALANCED_FIT'],catalog_policies=list(policies),arm_policies=policies,relaxed_rule_groups=[2,4,6],max_seconds=1350,science_deadline=window['science_wrap_jst'],absolute_deadline_jst=window['science_wrap_jst'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(P/'source_snapshot'),helper_files=freeze['helper_files'],control_replay_libraries=catalogs)
assert c['scientific_contract']['action']=='continue'
assert window['science_wrap_jst']=='2026-11-03T05:35:00+09:00'
assert c['scene']=='scan65' and c['kernel_count']==279616 and c['p']==.001725801957946726
assert c['control_identity']['expected']==dict(controls=71227,pieces=62356,parents=8874)
assert c['predecessor_checkpoint_stage']=='M4_STATE'
c['settings']['background_reference']=str(F)
c['fixed_reference_stages']={name:dict(stage=str(stage),binding=prior_hash) for name,stage in [('UNIT007_START',R),('UNIT008_START',F)]}
c['fixed_support_diagnostic']=dict(references=c['fixed_reference_stages'],project='finite nearest segment; lowest-segment ties; existing geometry_base.extended_s only endpoint directional proxy',halfwidth='min(.5,sqrt(original_derivative_axis^T covariance original_derivative_axis)/p)',invalid_derivatives='retain rows, mark unsupported',sets='reference inherited/current/new; separately tag UNIT008 start members',accounting='clipped intervals, union, longest run, gaps, new-minus-inherited on same immutable reference; never physical external-curve evidence',stages='START and each accepted checkpoint and FINAL, after all maps before expensive rendering',used_for_decision=False)
c['archived_counterexample']=dict(unit='unit007',sequence=15,event=counter_event,library=str(counter_lib),stage=str(counter_stage),saved_only=True,refitting=False,member_identity_verified=False)
c['budgets']=dict(readiness_seconds=120,initial_catalog_seconds=180,growth_seconds_per_arm=450,delivery_seconds=600,total_seconds=1350,original_control_reexecuted=False,growth_budget_unchanged=True,actual_phase_elapsed_required=True,absolute_science_deadline=window['science_wrap_jst'])
c['external_memberships']['unit007_START']=bind(R/'MEMBERSHIP.npz')
c['external_memberships']['unit007_GROUP_BALANCED_FIT_FINAL']=bind(F/'MEMBERSHIP.npz')
c['historical_control']='unit006 ROW_FIT 17-step trajectory is archived historical evidence, not matched to the new start or reexecuted. Matched NO_FURTHER_GROWTH is exact unit007 FINAL; 38 accepted unit007 events are inherited, not new.'
c['initial_catalog_policy']='Replay four complete final GROUP_BALANCED_FIT catalogs exactly and completed prefix of the partial 37-donor fifth catalog; exclude interrupted proposal. Requery every donor, separately fit ROW_FIT shadows, freeze both complete catalogs before promotion.'
c['visual_policy'].update(arms=['GROUP_BALANCED_FIT'],fixed_support='two frozen coordinate references; diagnostics do not change native original-kernel ink',inherited_events=38,matched_control=str(F),archived_counterexample=str(counter_lib))
c['source_provenance']=dict(latest_frozen_source=str(P/'source_snapshot'),latest_snapshot_binding=sha(P/'PARENT_RUN_FROZEN.json'),v10_copied_source_manifest=str(U/'SOURCE_REUSE_PROVENANCE.json'),all_69_prior_files_byte_identical=True,changed_new_copies=[],new_modules=['carry_forward_support.py','carry_forward_runner.py','test_carry_forward.py','build_carry_forward_request.py'],old_outputs_edited=False,v08_unit012_used=False,old_producers_executed=False,old_deadlines_imported=False,raw_scan65_loader='branch_loader -> scan65_loader -> paired_loader -> restricted M4_STATE',inherited_u11_and_v09_provenance=prior['source_provenance'])
for section in ['input_files','helper_files']:
 for p,h in c[section].items():assert sha(p)==h,(section,p)
tests=U/'tests';red=read(tests/'RED_EXIT.json');green=read(tests/'GREEN_EXIT.json');cli=read(tests/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==cli['returncode']==0
assert 'dynamic support lacks fixed-reference row/extrapolation accounting' in (tests/'RED.log').read_text()
assert 'Ran 33 tests' in (tests/'GREEN.log').read_text() and (tests/'GREEN.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,test_count=33,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN for fixed-reference evidence versus existing dynamic support. Three further unit008 tests added after first small GREEN. 29 prior strict/relaxed/fit/core/loader regressions reused; not new TDD.',red=dict(red,log=str(tests/'RED.log'),sha256=sha(tests/'RED.log'),test_source=str(tests/'RED_test_carry_forward.py'),test_source_sha256=sha(tests/'RED_test_carry_forward.py'),baseline_source=str(P/'source_snapshot/whole_core.py'),baseline_source_sha256=sha(P/'source_snapshot/whole_core.py')),green=dict(green,log=str(tests/'GREEN.log'),sha256=sha(tests/'GREEN.log')),cli=dict(cli,log=str(tests/'CLI.log'),sha256=sha(tests/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,native_render=False,scope='actual 36-row M4/control/accepted-composite loader with guard(phase), exact current GROUP_BALANCED_FIT library replay, cold maps and two fixed-reference accounts before deliberate renderer boundary; partial-prefix mismatch and no truncated promotion; inherited >8/best/rollback/disabled-guard regressions',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'SOURCE_REUSE_PROVENANCE.json',dict(parent_manifest=str(P/'PARENT_RUN_FROZEN.json'),parent_manifest_sha256=sha(P/'PARENT_RUN_FROZEN.json'),snapshot_files_verified=69,byte_identical_existing_files=reused,modified_new_copy={},old_files_edited=False))
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c)
script=str(S/'carry_forward_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],tests_receipt=str(U/'TESTS_RECEIPT.json'),max_seconds=1350,python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')])
write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),request=str(U/'RUN_REQUEST.json'),command=request['command'])))
