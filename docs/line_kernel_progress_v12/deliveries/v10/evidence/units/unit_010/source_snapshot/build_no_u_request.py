"""Unit005 metadata freeze: hash verification only; no full asset science."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103')
U=O/'units/unit_005';P=O/'units/unit_004'
F=P/'scenes/scan65/stages/START'
A=P/'scenes/scan65/stages/R2_R4_R6_OFF_TRANSPORT_FINAL'
ORIGINAL='R2_R4_R6_OFF_TRANSPORT';NEW='NO_U_REWARD'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with Path(p).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)

prior_hash='4bc1a97468d1c4e6b70c58671d49ac79d102dbc53d0ec73287287b6801275d8b'
assert sha(P/'CONFIG.json')==prior_hash
prior=read(P/'CONFIG.json');c=copy.deepcopy(prior)
window=read(O/'orchestration/WINDOW.json');freeze=read(P/'PARENT_RUN_FROZEN.json');inputs=c['input_files']
def bind(p,h=None):
 p=Path(p).resolve();actual=sha(p)
 if h is not None:assert actual==h,str(p)
 inputs[str(p)]=actual;return str(p)
reused={}
for old,snapshot in freeze['immutable_source_snapshot'].items():
 h=freeze['source_files'][old];bind(snapshot,h);name=Path(old).name
 assert sha(S/name)==h,name
 reused[name]=h
assert len(reused)==54
for p in [P/'CONFIG.json',P/'PARENT_RUN_FROZEN.json',P/'RUN_RESULT.json',P/'GEOMETRY_AUDIT.json']:bind(p)
def checkpoint(stage):
 cp=read(stage/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior_hash
 bind(stage/'CHECKPOINT.json')
 for name,h in cp['files'].items():bind(stage/name,h)
 return cp
checkpoint(F);checkpoint(A)
assert sha(F/'MEMBERSHIP.npz')=='252d9a2875a23fda6792d116ba08587c7e31368972924307e0609e05b10dc249'
versions={str(g['id']):g['version'] for g in read(F/'GROUPS.json')['groups']}
assert versions=={'5558':21661,'22130':21667,'64111':21668,'156151':21665,'238627':21651}
lin=read(F/'LINEAGE.json');assert lin['next_version']==21669 and len(lin['historical'])==1760 and not lin['events']
old_lin=read(A/'LINEAGE.json');assert len(old_lin['events'])==24
stop=read(A/'STOP.json');assert stop['status']=='completed' and stop['reason']=='NATURAL_SCOPE_EXHAUSTION'
bind(A/'STOP.json');bind(A/'FULL_NATIVE_RECEIPT.json');bind(A/'METRICS.json')
for name,h in read(A/'FULL_NATIVE_RECEIPT.json')['files'].items():bind(A/name,h)
exit_path=O/'orchestration/unit_004/COMPUTE_EXIT.json';old_exit=read(exit_path)
assert old_exit['returncode']==0 and old_exit['reason'] is None and old_exit['actual_child_exit']
bind(exit_path)
catalogs={}
for gid in c['seed_ids']:
 folder=P/'scenes/scan65/initial_catalogs'/ORIGINAL/str(gid)
 for p in sorted(folder.iterdir()):
  if p.is_file():bind(p)
 catalogs[str(gid)]=str(folder/'LIBRARY.json')
 assert read(folder/'LIBRARY.json')['complete']
assert c['scene']=='scan65' and c['kernel_count']==279616 and c['p']==.001725801957946726
assert c['control_identity']['expected']==dict(controls=71227,pieces=62356,parents=8874)
assert c['predecessor_checkpoint_stage']=='M4_STATE'
assert c['raw_config']==prior['raw_config']
policies={ORIGINAL:[2,4,6],NEW:[2,4,6]}
c.update(unit_root=str(U),runtime_root=str(O/'orchestration'),unit=str(U),runtime=str(O),restore_stage=str(F),restore_binding=prior_hash,initial_stage=str(F),initial_assigned=126428,initial_unknown=153188,initial_next_version=21669,seed_versions=versions,arms=[NEW],executed_arms=[NEW],catalog_policies=list(policies),arm_policies=policies,relaxed_rule_groups=[2,4,6],max_seconds=1350,science_deadline=window['science_wrap_jst'],absolute_deadline_jst=window['science_wrap_jst'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(P/'source_snapshot'),helper_files=freeze['helper_files'],legacy_groups_locked=True,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False,membership_policy='monotone_group_union',whole_curve_auxiliary_update=True,stop_policy='until_no_connection_or_supported_closed',control_replay_libraries=catalogs,archived_control_stage=str(A),archived_control_binding=prior_hash,archived_control_compute_exit=str(exit_path))
assert window['science_wrap_jst']=='2026-11-03T05:35:00+09:00'
c['settings'].update(background_reference=str(F),score='mean(d/p)^2+.25mean(theta/90)^2+.05mean(turn/90)^2+.1(maxgap/p)^2+.02K/(L/p+1)',score_by_policy={ORIGINAL:prior['settings']['score'],NEW:'J_original + .25*U_p/(1+U_p)'},unique_support_reward_coefficient={ORIGINAL:.25,NEW:0.},support_unit='U_p is unique_donor_support_p, already normalized by p',diagnostic_unique_support_retained=True)
for rule in [2,4,6]:c['settings']['connectability'][f'rule{rule}_hard_enabled_by_arm']={p:False for p in policies}
c['settings']['fit']['policy']='WHOLE both scoring policies, every knot movable; identical fitted proposals'
c['settings']['relation_diagnostics'].update(two_scores_per_state=True,earliest_ranking_divergence=True,score_terms_use_policy_coefficient=True)
c['budgets']=dict(readiness_seconds=120,initial_catalog_seconds=180,growth_seconds_per_arm=450,delivery_seconds=600,total_seconds=1350,original_control_reexecuted=False,new_arm_growth_budget_matches_archived_control=True,actual_phase_elapsed_required=True,absolute_science_deadline=window['science_wrap_jst'])
c['external_memberships']['unit004_START']=bind(F/'MEMBERSHIP.npz')
c['external_memberships']['unit004_R2_R4_R6_FINAL']=bind(A/'MEMBERSHIP.npz')
c['visual_policy'].update(arms=[NEW],archived_control_full_views=[str(A/(v+'_FULL.png')) for v in c['views']],earliest_ranking_divergence='SCORE_COMPARISON.json at every library visit; same fixed seed start/mid/final and added-row full-object context views',worst_events='top3 maximum member error and size plus first pure_pooling/gap_exceeded/self_contact')
c['historical_control']='Original-J unit004 R2_R4_R6 has 24 archived accepted events and complete natural scope exhaustion. Only initial catalogs replay here; archived growth is not newly executed. Both policies start from unit004 START, not its final state.'
c['initial_catalog_policy']='Exact replay of five original-J initial candidate/scientific/geometry/choice catalogs before promotion. Freeze original and NO_U_REWARD catalogs, then run only NO_U_REWARD; save both scores and shadow choices at each new state.'
c['source_provenance']=dict(latest_frozen_source=str(P/'source_snapshot'),latest_snapshot_binding=sha(P/'PARENT_RUN_FROZEN.json'),v10_copied_source_manifest=str(U/'SOURCE_REUSE_PROVENANCE.json'),all_54_prior_files_byte_identical=True,changed_new_copies=[],new_modules=['no_u_core.py','no_u_delivery.py','no_u_runner.py','test_no_u.py','build_no_u_request.py'],old_outputs_edited=False,v08_unit012_used=False,old_producers_executed=False,old_deadlines_imported=False,raw_scan65_loader='branch_loader -> scan65_loader -> paired_loader -> restricted M4_STATE',inherited_u11_and_v09_provenance=prior['source_provenance'])
for name in ['input_files','helper_files']:
 for p,h in c[name].items():assert sha(p)==h,(name,p)
t=U/'tests';red=read(t/'RED_EXIT.json');green=read(t/'GREEN_EXIT.json');cli=read(t/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==cli['returncode']==0 and green['test_count']==28
assert 'actual catalog has no NO_U_REWARD policy' in (t/'RED.log').read_text()
assert (t/'GREEN.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,test_count=28,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN for actual library NO_U_REWARD policy and exact score removal. Four new tests added after first GREEN. 23 inherited strict/relaxation/core/union/rollback regressions reused, not new TDD.',red=dict(red,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),test_source=str(t/'RED_test_no_u.py'),test_source_sha256=sha(t/'RED_test_no_u.py'),baseline_source=str(t/'RED_scan65_relaxed_core.py'),baseline_source_sha256=sha(t/'RED_scan65_relaxed_core.py')),green=dict(green,log=str(t/'GREEN.log'),sha256=sha(t/'GREEN.log')),cli=dict(cli,log=str(t/'CLI.log'),sha256=sha(t/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,native_render=False,scope='36-row real restricted M4/control/composite loader and runner: both initial scoring libraries, exact archived-control replay, only new arm, complete cold maps before deliberate native-render boundary. Exact original J/geometry replay, U=0 unchanged, U>0 reward removal, ranking reversal, >8 commits, remaining guards, monotone union and rollback.',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'SOURCE_REUSE_PROVENANCE.json',dict(parent_manifest=str(P/'PARENT_RUN_FROZEN.json'),parent_manifest_sha256=sha(P/'PARENT_RUN_FROZEN.json'),snapshot_files_verified=54,byte_identical_existing_files=reused,modified_new_copy={},old_files_edited=False))
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c)
script=str(S/'no_u_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],tests_receipt=str(U/'TESTS_RECEIPT.json'),max_seconds=1350,python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')])
write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),request=str(U/'RUN_REQUEST.json'),command=request['command'])))
