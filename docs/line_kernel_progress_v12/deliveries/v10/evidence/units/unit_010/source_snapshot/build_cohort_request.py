"""Unit009 metadata/hash freeze only: never loads full Gaussian data or fits/renders."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103')
U=O/'units/unit_009';P=O/'units/unit_008';F=P/'scenes/scan65/stages/GROUP_BALANCED_FIT_FINAL'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with Path(p).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)
prior_hash='e36a099d0d7fb6bd3e284c7e0c0941a82cffe72e67397484f061d1eea9926a16'
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
assert len(reused)==73
for p in [P/'CONFIG.json',P/'PARENT_RUN_FROZEN.json',P/'RUN_RESULT.json',P/'GEOMETRY_AUDIT.json',P/'FAILURE_ANALYSIS.json',P/'NEXT.json',P/'SAVED_OUTPUT_AUDIT.json']:bind(p)
cp=read(F/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior_hash;bind(F/'CHECKPOINT.json')
for name,h in cp['files'].items():bind(F/name,h)
assert sha(F/'MEMBERSHIP.npz')=='e3c6a05baf6d4c94c7d4ce2d8d81f4919cc6491b026fcfa7d48adffa5ab8f2a5'
restore_versions={str(g['id']):g['version'] for g in read(F/'GROUPS.json')['groups']}
assert restore_versions=={'5558':21692,'22130':21686,'64111':21683,'156151':21665,'238627':21707}
lin=read(F/'LINEAGE.json');assert lin['next_version']==21708 and len(lin['historical'])+len(lin['events'])==1799
stop=read(F/'STOP.json');assert stop['status']=='completed' and stop['reason']=='NATURAL_SCOPE_EXHAUSTION'
for n in ['STOP.json','METRICS.json','FULL_NATIVE_RECEIPT.json']:bind(F/n)
for n,h in read(F/'FULL_NATIVE_RECEIPT.json')['files'].items():bind(F/n,h)
exit_path=O/'orchestration/unit_008/COMPUTE_EXIT.json';actual_exit=read(exit_path)
assert actual_exit['returncode']==0 and actual_exit['reason'] is None and actual_exit['actual_child_exit'];bind(exit_path)
catalogs={}
for folder_name in ['0005_5558','0006_22130','0007_64111','0008_156151','0009_238627']:
 folder=P/'scenes/scan65/libraries/GROUP_BALANCED_FIT'/folder_name;gid=folder_name.split('_')[1]
 for p in sorted(folder.rglob('*')):
  if p.is_file():bind(p)
 lib=read(folder/'LIBRARY.json');assert lib['complete'] and lib['selected'] is None;catalogs[gid]=str(folder/'LIBRARY.json')
# Preserve the reached G/F/union witnesses for the one acceptance and subsequent transitions.
event=lin['events'][0];counter=P/'scenes/scan65/libraries/GROUP_BALANCED_FIT'/f"{event['library_visit']:04d}_{event['group']}"
for p in sorted(counter.rglob('*')):
 if p.is_file():bind(p)
audit=read(P/'SAVED_OUTPUT_AUDIT.json')
seeds={136538:(20920,75),84607:(21350,55),233067:(20662,45),30579:(21407,99),162227:(21222,83),13285:(20509,72)}
active=sorted(seeds);old=sorted(map(int,restore_versions));tracked=sorted(old+active)
policies={'GROUP_BALANCED_SCORE':[2,4,6],'GROUP_BALANCED_FIT':[2,4,6]}
c.update(unit_root=str(U),runtime_root=str(O/'orchestration'),unit=str(U),runtime=str(O),restore_stage=str(F),restore_binding=prior_hash,initial_stage=str(F),initial_assigned=126616,initial_unknown=153000,initial_next_version=21708,restore_seed_ids=old,restore_seed_versions=restore_versions,seed_ids=active,seed_versions={str(i):v for i,(v,n) in seeds.items()},seed_expected_rows={str(i):n for i,(v,n) in seeds.items()},tracked_origin_ids=tracked,expected_selection_counts=dict(records=3670,eligible=dict(line=4,polyline=10),unselected=8),arms=['GROUP_BALANCED_FIT'],executed_arms=['GROUP_BALANCED_FIT'],catalog_policies=list(policies),arm_policies=policies,relaxed_rule_groups=[2,4,6],max_seconds=1350,science_deadline=window['science_wrap_jst'],absolute_deadline_jst=window['science_wrap_jst'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(P/'source_snapshot'),helper_files=freeze['helper_files'],control_replay_libraries=catalogs)
assert c['scientific_contract']['action']=='continue'
assert window['science_wrap_jst']=='2026-11-03T05:35:00+09:00'
assert c['scene']=='scan65' and c['kernel_count']==279616 and c['p']==.001725801957946726
assert c['control_identity']['expected']==dict(controls=71227,pieces=62356,parents=8874)
assert c['predecessor_checkpoint_stage']=='M4_STATE'
c['settings']['background_reference']=str(F);c['settings']['seed_scope']=active
c['seed_policy']=dict(source='original unit017 M4 GROUPS and endpoint LINEAGE, checked against restored full objects',valid_original_output=True,complete_unchanged_members_and_version=True,excluded_prior_origins=old,min_M3_contributions=2,min_contribution_kernels=12,min_contribution_support_p=2,supported_length_p=[10,80],models=['line','polyline'],sort=['descending supported_length_p','ascending ID'],take_per_model=3,no_replacement=True,cohort_selection_not_donor_validity_gate=True)
c['fixed_reference_stages']={'UNIT009_START':dict(stage=str(U/'scenes/scan65/stages/START'),binding='THIS_CONFIG_SHA256_RESOLVED_AT_RUNTIME')}
c['fixed_support_diagnostic'].update(references=c['fixed_reference_stages'],sets='eleven immutable UNIT009 START origins: inherited/current/new; each reference frozen before growth',stages='START and each accepted checkpoint and FINAL after cold maps, before native rendering',used_for_decision=False)
c['archived_transitions']=dict(unit='unit008',audit=str(P/'SAVED_OUTPUT_AUDIT.json'),audit_sha256=sha(P/'SAVED_OUTPUT_AUDIT.json'),transitions=audit['post_acceptance_transitions'],acceptance_library=str(counter),final_libraries=catalogs,refitting_archived_acceptance=False,rule5_unchanged=True)
c['budgets']=dict(readiness_seconds=120,initial_catalog_seconds=180,growth_seconds_per_arm=450,delivery_seconds=600,total_seconds=1350,original_control_reexecuted=False,actual_phase_elapsed_required=True,absolute_science_deadline=window['science_wrap_jst'])
c['external_memberships']['unit008_GROUP_BALANCED_FIT_FINAL']=bind(F/'MEMBERSHIP.npz')
c['historical_control']='unit006 ROW_FIT 17-step trajectory is archived historical evidence, not matched or reexecuted. Matched NO_FURTHER_GROWTH exactly copies unit008 FINAL; all 1799 existing events are inherited, not new.'
c['initial_catalog_policy']='Restore original five composites; replay their five complete zero-choice final libraries, without old growth. Tag six intact M4 objects without changing row/Q/version. Freeze dual-fit initial catalogs for six READY new origins before promotion. Failed frozen seeds remain NOT_RUN, no replacement.'
c['visual_policy'].update(seed_ids=active,arms=['GROUP_BALANCED_FIT'],fixed_support='one immutable UNIT009 START coordinate reference for each of all eleven tracked origins; never used for ranking',inherited_events=1799,matched_control=str(F))
c['source_provenance']=dict(latest_frozen_source=str(P/'source_snapshot'),latest_snapshot_binding=sha(P/'PARENT_RUN_FROZEN.json'),v10_copied_source_manifest=str(U/'SOURCE_REUSE_PROVENANCE.json'),all_73_prior_files_byte_identical=True,changed_new_copies=[],new_modules=['cohort_loader.py','cohort_support.py','cohort_runner.py','test_cohort.py','build_cohort_request.py'],old_outputs_edited=False,v08_unit012_used=False,old_producers_executed=False,old_deadlines_imported=False,raw_scan65_loader='cohort_loader -> branch_loader using restore cohort -> scan65_loader -> paired_loader -> restricted M4_STATE',inherited_u11_and_v09_provenance=prior['source_provenance'])
for section in ['input_files','helper_files']:
 for p,h in c[section].items():assert sha(p)==h,(section,p)
tests=U/'tests';red=read(tests/'RED_EXIT.json');green=read(tests/'GREEN_EXIT.json');cli=read(tests/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==cli['returncode']==0
assert "KeyError: '2'" in (tests/'RED.log').read_text()
assert 'Ran 38 tests' in (tests/'GREEN.log').read_text() and (tests/'GREEN.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,test_count=38,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: actual old branch_loader cannot restore old cohort while activating new ID (KeyError 2); separate restore/active adapter passes. Four additional cohort tests were added after first GREEN; 33 earlier regressions reused, not new TDD.',red=dict(red,log=str(tests/'RED.log'),sha256=sha(tests/'RED.log'),test_source=str(tests/'RED_test_cohort.py'),test_source_sha256=sha(tests/'RED_test_cohort.py'),baseline_source=str(P/'source_snapshot/branch_loader.py'),baseline_source_sha256=sha(P/'source_snapshot/branch_loader.py')),green=dict(green,log=str(tests/'GREEN.log'),sha256=sha(tests/'GREEN.log')),cli=dict(cli,log=str(tests/'CLI.log'),sha256=sha(tests/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,native_render=False,scope='actual 36-row M4/control/composite loader plus new-cohort version failure, eleven-origin cold checkpoint/fixed references, unchanged membership/Q/version, old-library replay, dual new catalogs and complete maps before intentional renderer boundary, >8 new-runner growth and no truncated winner; inherited strict/relaxed/rollback tests',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'SOURCE_REUSE_PROVENANCE.json',dict(parent_manifest=str(P/'PARENT_RUN_FROZEN.json'),parent_manifest_sha256=sha(P/'PARENT_RUN_FROZEN.json'),snapshot_files_verified=73,byte_identical_existing_files=reused,modified_new_copy={},old_files_edited=False))
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c)
script=str(S/'cohort_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],tests_receipt=str(U/'TESTS_RECEIPT.json'),max_seconds=1350,python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')])
write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),request=str(U/'RUN_REQUEST.json'),command=request['command'])))
