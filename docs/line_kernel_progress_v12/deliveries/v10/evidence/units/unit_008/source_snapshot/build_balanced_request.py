"""Unit006 metadata freeze: hash verification only; no full asset science."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103')
U=O/'units/unit_006';P=O/'units/unit_005'
F=P/'scenes/scan65/stages/START'
A=P/'scenes/scan65/stages/NO_U_REWARD_FINAL'
ORIGINAL='NO_U_REWARD';NEW='GROUP_BALANCED_SCORE'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with Path(p).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)

prior_hash='84ccab7ce3565158674856dcf5b301eeb44266ecd67a7b102a4df5ac6d896115'
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
assert len(reused)==59
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
old_lin=read(A/'LINEAGE.json');assert len(old_lin['events'])==33
stop=read(A/'STOP.json');assert stop['status']=='PARTIAL' and stop['reason']=='PHASE_DEADLINE NO_U_REWARD'
bind(A/'STOP.json');bind(A/'FULL_NATIVE_RECEIPT.json');bind(A/'METRICS.json')
for name,h in read(A/'FULL_NATIVE_RECEIPT.json')['files'].items():bind(A/name,h)
exit_path=O/'orchestration/unit_005/COMPUTE_EXIT.json';old_exit=read(exit_path)
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
score='.5*D_G+.5*D_F+.25*mean(T_H over nonempty valid-direction sets)+.05mean((turn/90)^2)+.1(maxgap/p)^2+.02K/(L/p+1)'
c['settings'].update(background_reference=str(F),score=score,score_by_policy={ORIGINAL:prior['settings']['score'],NEW:score},unique_support_reward_coefficient={ORIGINAL:0.,NEW:0.},support_unit='U_p is unique_donor_support_p, already normalized by p',diagnostic_unique_support_retained=True)
c['settings']['group_balanced_score']=dict(position='D_H=mean((distance/p)^2) over all distinct original H rows; weights G=.5,F=.5',direction='T_H=mean((unsigned original derivative angle/90)^2) over valid rows; equal weight over nonempty G/F sets',missing_one_direction='log UNKNOWN for missing side; other side weight1; no new veto',missing_both_directions='unchanged common UNKNOWN_direction',projection='same final evaluated Q, finite closest segment, lowest-segment ties',fit_weights_unchanged=True,per_row_evidence='SCORE_EVIDENCE.npz',members_never_removed=True)
for rule in [2,4,6]:c['settings']['connectability'][f'rule{rule}_hard_enabled_by_arm']={p:False for p in policies}
c['settings']['fit']['policy']='WHOLE both scoring policies, every knot movable; identical fitted proposals'
c['settings']['relation_diagnostics'].update(two_scores_per_state=True,earliest_ranking_divergence=True,score_terms_use_policy_coefficient=True)
c['budgets']=dict(readiness_seconds=120,initial_catalog_seconds=180,growth_seconds_per_arm=450,delivery_seconds=600,total_seconds=1350,original_control_reexecuted=False,new_arm_growth_budget_matches_archived_control=True,actual_phase_elapsed_required=True,absolute_science_deadline=window['science_wrap_jst'])
c['external_memberships']['unit005_START']=bind(F/'MEMBERSHIP.npz')
c['external_memberships']['unit005_NO_U_FINAL']=bind(A/'MEMBERSHIP.npz')
c['visual_policy'].update(arms=[NEW],archived_control_full_views=[str(A/(v+'_FULL.png')) for v in c['views']],earliest_ranking_divergence='SCORE_COMPARISON.json every visit and first divergent accepted event native full/isolated/added/full-object context',worst_events='top3 maximum member error and size plus first ranking divergence/pure_pooling/gap_exceeded/self_contact')
c['historical_control']='unit005 NO_U_REWARD has 33 archived accepted events and PARTIAL PHASE_DEADLINE NO_U_REWARD. Only initial catalogs replay here; archived growth is not newly executed or naturally exhausted. Both policies start from unit005 START, not its final state.'
c['initial_catalog_policy']='Exact replay of five NO_U_REWARD initial candidate/scientific/geometry/choice catalogs before promotion. Freeze NO_U_REWARD and GROUP_BALANCED_SCORE catalogs, then run only GROUP_BALANCED_SCORE; save both scores and shadow choices at each new state.'
c['source_provenance']=dict(latest_frozen_source=str(P/'source_snapshot'),latest_snapshot_binding=sha(P/'PARENT_RUN_FROZEN.json'),v10_copied_source_manifest=str(U/'SOURCE_REUSE_PROVENANCE.json'),all_59_prior_files_byte_identical=True,changed_new_copies=[],new_modules=['balanced_core.py','balanced_delivery.py','balanced_runner.py','test_balanced.py','build_balanced_request.py'],old_outputs_edited=False,v08_unit012_used=False,old_producers_executed=False,old_deadlines_imported=False,raw_scan65_loader='branch_loader -> scan65_loader -> paired_loader -> restricted M4_STATE',inherited_u11_and_v09_provenance=prior['source_provenance'])
for name in ['input_files','helper_files']:
 for p,h in c[name].items():assert sha(p)==h,(name,p)
t=U/'tests';red=read(t/'RED_EXIT.json');green=read(t/'GREEN_EXIT.json');cli=read(t/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==cli['returncode']==0 and green['test_count']==31
assert 'actual catalog has no GROUP_BALANCED_SCORE policy' in (t/'RED.log').read_text()
assert (t/'GREEN.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,test_count=31,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN for actual GROUP_BALANCED_SCORE library and unequal-size score formula. Seven new tests added after first GREEN. 23 inherited strict/relaxation/core/union/rollback regressions reused, not new TDD.',red=dict(red,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),test_source=str(t/'RED_test_balanced.py'),test_source_sha256=sha(t/'RED_test_balanced.py'),baseline_source=str(t/'RED_no_u_core.py'),baseline_source_sha256=sha(t/'RED_no_u_core.py')),green=dict(green,log=str(t/'GREEN.log'),sha256=sha(t/'GREEN.log')),cli=dict(cli,log=str(t/'CLI.log'),sha256=sha(t/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,native_render=False,scope='36-row real restricted M4/control/composite loader and runner: both initial score libraries, exact NO_U replay, only new arm, complete cold maps before deliberate native-render boundary. Unequal-size group weights and winner reversal, missing-side direction normalization, finite relaxed pooling/gap/selfcontact scores, NPZ per-row evidence, >8 commits, strict parity, monotone union and rollback.',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'SOURCE_REUSE_PROVENANCE.json',dict(parent_manifest=str(P/'PARENT_RUN_FROZEN.json'),parent_manifest_sha256=sha(P/'PARENT_RUN_FROZEN.json'),snapshot_files_verified=59,byte_identical_existing_files=reused,modified_new_copy={},old_files_edited=False))
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c)
script=str(S/'balanced_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],tests_receipt=str(U/'TESTS_RECEIPT.json'),max_seconds=1350,python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')])
write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),request=str(U/'RUN_REQUEST.json'),command=request['command'])))
