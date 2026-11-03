"""Unit003 metadata/hash freeze only; never loads numerical assets or renders."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103')
U=O/'units/unit_003';P=O/'units/unit_002';F=P/'scenes/scan24/stages/START';A=P/'scenes/scan24/stages/R2_R4_OFF_TRANSPORT_FINAL'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with Path(p).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)

prior_hash='44b274d4a6144296258f6542444ff65dd11ffdb0fdb07ed8c2ef6752c66a6bb7'
assert sha(P/'CONFIG.json')==prior_hash
c=copy.deepcopy(read(P/'CONFIG.json'));window=read(O/'orchestration/WINDOW.json');freeze=read(P/'PARENT_RUN_FROZEN.json');inputs=c['input_files']
def bind(p,h=None):
 p=Path(p).resolve();actual=sha(p)
 if h is not None:assert actual==h,str(p)
 inputs[str(p)]=actual;return str(p)
reused={};changed={}
for old,snapshot in freeze['immutable_source_snapshot'].items():
 bind(snapshot,freeze['source_files'][old]);name=Path(old).name;new_hash=sha(S/name)
 if new_hash==freeze['source_files'][old]:reused[name]=new_hash
 else:changed[name]=dict(before=freeze['source_files'][old],after=new_hash)
assert set(changed)=={'whole_core.py'}
for p in [P/'CONFIG.json',P/'PARENT_RUN_FROZEN.json',P/'RUN_RESULT.json',P/'GEOMETRY_AUDIT.json']:bind(p)
for stage in [F,A,*sorted((P/'scenes/scan24/stages').glob('R2_R4_OFF_TRANSPORT_000?'))]:
 cp=read(stage/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior_hash;bind(stage/'CHECKPOINT.json')
 for name,h in cp['files'].items():bind(stage/name,h)
bind(A/'STOP.json');assert read(A/'STOP.json')['reason']=='KNOT_CAPACITY'
assert sha(F/'MEMBERSHIP.npz')=='74c85f36ff766f27c1336e0e5ceff38c252e7c61e78217ad1648e43f4bdc7b2c'
groups=read(F/'GROUPS.json')['groups'];versions={str(g['id']):g['version'] for g in groups}
assert versions=={'53254':33925,'132977':33930,'200509':33918,'201906':33891,'202023':33881,'210790':33927}
assert read(F/'LINEAGE.json')['next_version']==33931 and len(read(A/'LINEAGE.json')['events'])==6
libraries={}
for gid in c['seed_ids']:
 p=P/'scenes/scan24/initial_catalogs/R2_R4_OFF_TRANSPORT'/str(gid)/'LIBRARY.json';assert read(p)['complete'];libraries[str(gid)]=str(p)
 for name in ['LIBRARY.json','GEOMETRY.npz','BRANCH_WITNESSES.json.gz','SHADOW_CHOICES.json']:bind(p.parent/name)
policies={'R2_R4_OFF_TRANSPORT':[2,4],'R2_R4_R6_OFF_TRANSPORT':[2,4,6]};executed=['R2_R4_R6_OFF_TRANSPORT']
c.update(unit_root=str(U),runtime_root=str(O/'orchestration'),unit=str(U),runtime=str(O),restore_stage=str(F),restore_binding=prior_hash,initial_stage=str(F),initial_assigned=260029,initial_unknown=198461,initial_next_version=33931,seed_versions=versions,arms=executed,catalog_policies=list(policies),arm_policies=policies,relaxed_rule_groups=[2,4,6],max_seconds=1800,science_deadline=window['science_wrap_jst'],absolute_deadline_jst=window['science_wrap_jst'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(P/'source_snapshot'),control_replay_libraries=libraries,archived_control_stage=str(A),archived_control_binding=prior_hash,archived_control_compute_exit=str(O/'orchestration/unit_002/COMPUTE_EXIT.json'),executed_arms=executed)
c.pop('control_state_expected_unchanged',None)
c['helper_files']=freeze['helper_files']
c['source_provenance'].pop('all_unit001_modules_byte_identical',None)
c['source_provenance'].update(latest_frozen_source=str(P/'source_snapshot'),latest_snapshot_binding=sha(P/'PARENT_RUN_FROZEN.json'),v10_copied_source_manifest=str(U/'SOURCE_REUSE_PROVENANCE.json'),changed_new_copies=['whole_core.py'],new_modules=['r6_core.py','r6_control.py','r6_runner.py','r6_delivery.py','test_r6.py','build_r6_request.py'],old_outputs_edited=False)
c['settings']['background_reference']=str(F)
con=c['settings']['connectability'];con.pop('rule6_hard_enabled',None)
con.update(rule2_hard_enabled_by_arm={p:False for p in policies},rule4_hard_enabled_by_arm={p:False for p in policies},rule6_hard_enabled_by_arm={'R2_R4_OFF_TRANSPORT':True,'R2_R4_R6_OFF_TRANSPORT':False},disabled_rule6_diagnostics='contact/gap/no_unique remain finite diagnostics and original score terms; pure pooling allowed; no replacement veto')
c['settings']['closure'].update(relaxed_union_with_gap_or_contact_is_not_supported_closed=True,closure_failure_does_not_reject_relaxed_union=True)
c['budgets']=dict(readiness_seconds=120,initial_catalog_seconds=180,new_growth_seconds=900,delivery_seconds=600,total_seconds=1800,original_control_growth_rerun=False,actual_phase_elapsed_required=True,absolute_science_deadline=window['science_wrap_jst'])
c['external_memberships']['v10_unit002_START']=bind(F/'MEMBERSHIP.npz');c['external_memberships']['v10_unit002_R2_R4_FINAL']=bind(A/'MEMBERSHIP.npz')
c['visual_policy'].update(arms=executed,archived_control='Use unit002 saved full/isolated/context images and membership; not newly rendered or executed',worst_events='top3 maximum member error and size plus first pure_pooling/gap_exceeded/self_contact',known_missing_view='unit002 worst event202023/0012 isolated image is blank; no inferred observation')
c['historical_control']='unit002 [2,4] complete six initial libraries replayed; subsequent six-acceptance KNOT_CAPACITY trajectory is archived, not re-executed. New run starts from same START, not prior FINAL.'
c['initial_catalog_policy']='Both policies complete six initial catalogs before promotion; exact scientific/q/template/movable replay including nonzero selected indexes; incomplete frontier cannot promote.'
for name in ['input_files','helper_files']:
 for p,h in c[name].items():assert sha(p)==h,(name,p)
t=U/'tests';red=read(t/'RED_EXIT.json');green=read(t/'GREEN_INTEGRATION_EXIT.json');cli=read(t/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==cli['returncode']==0 and green['test_count']==23
assert 'actual library never dispatches [2,4,6]' in (t/'RED.log').read_text() and 'gap relaxation falsely certifies supported closure' in (t/'RED.log').read_text()
assert (t/'GREEN_INTEGRATION.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,test_count=23,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN for [2,4,6] actual-library pooling dispatch and false supported-closure stop with internal gap: both failed before implementation, both passed after. Three additional integration tests added after first GREEN; 18 existing regressions reused, not claimed new TDD.',red=dict(red,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),test_source=str(t/'RED_test_r6.py'),test_source_sha256=sha(t/'RED_test_r6.py'),baseline_sources={str(t/n):sha(t/n) for n in ['RED_r4_core.py','RED_whole_core.py']}),green=dict(green,log=str(t/'GREEN_INTEGRATION.log'),sha256=sha(t/'GREEN_INTEGRATION.log')),cli=dict(cli,log=str(t/'CLI.log'),sha256=sha(t/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,native_render=False,scope='36-row actual restricted M5/control/composite loader, runner through cold full maps/archive reference/control replay; renderer deliberately stopped at entry. Real bounded geometric fixtures including >8 commits, exact union and rollback.',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'SOURCE_REUSE_PROVENANCE.json',dict(parent_manifest=str(P/'PARENT_RUN_FROZEN.json'),parent_manifest_sha256=sha(P/'PARENT_RUN_FROZEN.json'),snapshot_files_verified=43,byte_identical_existing_files=reused,modified_new_copy=changed,old_files_edited=False))
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};write(U/'CONFIG.json',c)
script=str(S/'r6_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],tests_receipt=str(U/'TESTS_RECEIPT.json'),max_seconds=1800,python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),request=str(U/'RUN_REQUEST.json'),command=request['command'])))
