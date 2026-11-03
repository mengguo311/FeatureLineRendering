"""Freeze metadata only; never load raw kernels or run science."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103');U=O/'units/unit_001'
P=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_best_fragment_growth_v09_20261102/continuation_001/units/unit_001')
B=P.parent/'unit_003';F=P/'scenes/scan24/stages/WHOLE_FINAL'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with Path(p).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)

prior_hash='f165be882ffcadc4bf94a7b89e98e4a5b40cef94fe8e5afff10256117999df99';assert sha(P/'CONFIG.json')==prior_hash
c=copy.deepcopy(read(P/'CONFIG.json'));inputs=c['input_files'];window=read(O/'orchestration/WINDOW.json');freeze=read(B/'PARENT_RUN_FROZEN.json')
def bind(p,h=None):
 p=Path(p).resolve();actual=sha(p)
 if h:assert h==actual,str(p)
 inputs[str(p)]=actual;return str(p)
for original,snap in freeze['immutable_source_snapshot'].items():bind(snap,freeze['source_files'][original])
for p in [P/'CONFIG.json',P/'PARENT_RUN_FROZEN.json',B/'CONFIG.json',B/'PARENT_RUN_FROZEN.json',F/'CHECKPOINT.json']:bind(p)
cp=read(F/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior_hash
for name,h in cp['files'].items():bind(F/name,h)
assert sha(F/'MEMBERSHIP.npz')=='f03236e3599f0426f24225fef6ab00d7280ab594fb707f744785b96d4fa16bb4'
c.update(unit_root=str(U),runtime_root=str(O/'orchestration'),unit=str(U),runtime=str(O),raw_config=str(P/'CONFIG.json'),restore_stage=str(F),restore_binding=prior_hash,initial_stage=str(F),initial_assigned=259985,initial_unknown=198505,initial_next_version=33926,seed_versions={'53254':33925,'132977':33917,'200509':33918,'201906':33891,'202023':33881,'210790':33900},arms=['STRICT_TRANSPORT','R2_OFF_TRANSPORT'],arm_policies={'STRICT_TRANSPORT':[],'R2_OFF_TRANSPORT':[2]},relaxed_rule_groups=[2],max_seconds=1800,science_deadline=window['science_wrap_jst'],absolute_deadline_jst=window['science_wrap_jst'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(B/'source_snapshot'),kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False,legacy_groups_locked=True,membership_policy='monotone_group_union',whole_curve_auxiliary_update=True,stop_policy='until_no_connection_or_supported_closed')
c['helper_files']=freeze['helper_files'];c['source_provenance'].update(latest_frozen_source=str(B/'source_snapshot'),latest_snapshot_binding=sha(B/'PARENT_RUN_FROZEN.json'),v10_copied_source_manifest=str(U/'COPY_PROVENANCE.json'),all_original_modules_byte_identical=False,changed_new_copies=['whole_core.py','branch_core.py'],old_outputs_edited=False)
c['settings']['background_reference']=str(F);c['settings']['fit']['policy']='WHOLE both arms, every knot movable'
c['settings']['connectability']['branch']='TRANSPORT_BRANCH: original signed representative directions minimally transported along proposed finite Q; unchanged4p/20deg/3clusters/3reps/2p spans; unresolved whole frontier PARTIAL'
c['settings']['connectability']['rule2_hard_enabled_by_arm']={'STRICT_TRANSPORT':True,'R2_OFF_TRANSPORT':False}
c['settings']['connectability']['rule4_hard_enabled']=True;c['settings']['connectability']['rule6_hard_enabled']=True
c['settings']['score']='mean(d/p)^2+.25mean(theta/90)^2+.05mean(turn/90)^2+.1(maxgap/p)^2+.02K/(L/p+1)-.25(U/p)/(1+U/p)'
c['budgets']=dict(total_seconds=1800,readiness_seconds=120,initial_catalog_seconds=180,each_arm_growth_seconds=450,delivery_seconds=600,unit_bytes=2*2**30,output_root_bytes=20*2**30,complete_library_required=True,acceptance_count_cap=None)
c['external_memberships']['v09_WHOLE_FINAL']=bind(F/'MEMBERSHIP.npz');c['visual_policy'].update(arms=c['arms'],worst_events='top3 by maximum member error and top3 by group size per arm, deterministic event order ties',same_original_views=True)
c['initial_catalog_policy']='common complete fit catalog, both policy decisions before promotion; any incomplete initial catalog blocks promotion'
c['historical_control']='v09 scan24 used RADIAL branch; no zero-growth requirement for newly executed STRICT_TRANSPORT'
for name in ['input_files','helper_files']:
 for p,h in c[name].items():assert sha(p)==h,(name,p)
tests=U/'tests';red=read(tests/'RED_EXIT.json');green=read(tests/'GREEN_EXIT.json');cli=read(tests/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==cli['returncode']==0
assert 'AssertionError: False is not true : member_distance' in (tests/'RED.log').read_text()
assert (tests/'GREEN_VERIFIED.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: existing hard gates ignore relaxed switches and fail real geometry fixtures; conditional gates pass finite-score R2, parallel, pooling/gap/selfcontact fixtures. Integration tests added after initial RED are explicitly subsequent regressions.',red=dict(red,log=str(tests/'RED.log'),sha256=sha(tests/'RED.log'),baseline=str(tests/'RED_whole_core.py'),baseline_sha256=sha(tests/'RED_whole_core.py'),test_source=str(tests/'RED_test_relaxed.py'),test_source_sha256=sha(tests/'RED_test_relaxed.py')),green=dict(green,log=str(tests/'GREEN_VERIFIED.log'),sha256=sha(tests/'GREEN_VERIFIED.log')),cli=dict(cli,log=str(tests/'CLI.log'),sha256=sha(tests/'CLI.log')),test_count=green['test_count'],real_loader_guard_test=True,full_asset_run=False,native_render=False,scope='36-row restricted-M5 composite restoration plus bounded synthetic full-loop geometry; renderer stopped at call boundary',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt);c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};write(U/'CONFIG.json',c)
script=str(S/'relaxed_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],tests_receipt=str(U/'TESTS_RECEIPT.json'),max_seconds=1800,python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),request=str(U/'RUN_REQUEST.json'),command=request['command'])))
