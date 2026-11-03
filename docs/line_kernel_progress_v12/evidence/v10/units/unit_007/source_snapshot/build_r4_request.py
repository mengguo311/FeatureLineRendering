"""Unit002 metadata freezer only. No model loading, fitting or rendering."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103')
U=O/'units/unit_002';P=O/'units/unit_001';F=P/'scenes/scan24/stages/R2_OFF_TRANSPORT_FINAL'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with Path(p).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)

prior_hash='678bb027ef6f64598b539962bf9d58f4708570d217623d2293f71c534e5f4d6d'
assert sha(P/'CONFIG.json')==prior_hash
c=copy.deepcopy(read(P/'CONFIG.json'));window=read(O/'orchestration/WINDOW.json');freeze=read(P/'PARENT_RUN_FROZEN.json');inputs=c['input_files']
def bind(p,h=None):
 p=Path(p).resolve();actual=sha(p)
 if h is not None:assert actual==h,str(p)
 inputs[str(p)]=actual;return str(p)
for original,snapshot in freeze['immutable_source_snapshot'].items():bind(snapshot,freeze['source_files'][original])
for p in [P/'CONFIG.json',P/'PARENT_RUN_FROZEN.json',F/'CHECKPOINT.json']:bind(p)
cp=read(F/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior_hash
for name,h in cp['files'].items():bind(F/name,h)
assert sha(F/'MEMBERSHIP.npz')=='74c85f36ff766f27c1336e0e5ceff38c252e7c61e78217ad1648e43f4bdc7b2c'
groups=read(F/'GROUPS.json')['groups'];versions={str(g['id']):g['version'] for g in groups}
assert versions=={'53254':33925,'132977':33930,'200509':33918,'201906':33891,'202023':33881,'210790':33927}
lin=read(F/'LINEAGE.json');assert lin['next_version']==33931 and len(lin['historical'])==1819 and len(lin['events'])==5
last={}
for path in sorted((P/'scenes/scan24/libraries/R2_OFF_TRANSPORT').glob('*/LIBRARY.json')):last[path.parent.name.split('_',1)[1]]=path
assert set(last)==set(versions)
for path in last.values():
 d=read(path);assert d['complete'] and d['selected'] is None
 for name in ['LIBRARY.json','GEOMETRY.npz','BRANCH_WITNESSES.json.gz','SHADOW_CHOICES.json']:bind(path.parent/name)
policies={'R2_OFF_TRANSPORT':[2],'R2_R4_OFF_TRANSPORT':[2,4]}
c.update(unit_root=str(U),runtime_root=str(O/'orchestration'),unit=str(U),runtime=str(O),restore_stage=str(F),restore_binding=prior_hash,initial_stage=str(F),initial_assigned=260029,initial_unknown=198461,initial_next_version=33931,seed_versions=versions,arms=list(policies),arm_policies=policies,relaxed_rule_groups=[2,4],max_seconds=1800,science_deadline=window['science_wrap_jst'],absolute_deadline_jst=window['science_wrap_jst'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(P/'source_snapshot'),control_replay_libraries={gid:str(p) for gid,p in last.items()},control_state_expected_unchanged=True)
# raw_config remains the original strong-M5 adapter configuration, not a composite stage.
assert c['raw_config']!=str(P/'CONFIG.json')
c['helper_files']=freeze['helper_files'];c['source_provenance'].update(latest_frozen_source=str(P/'source_snapshot'),latest_snapshot_binding=sha(P/'PARENT_RUN_FROZEN.json'),v10_copied_source_manifest=str(U/'SOURCE_REUSE_PROVENANCE.json'),all_unit001_modules_byte_identical=True,new_modules=['r4_core.py','r4_control.py','r4_runner.py','test_r4.py','build_r4_request.py'],old_outputs_edited=False)
c['settings']['background_reference']=str(F)
con=c['settings']['connectability'];con['rule2_hard_enabled_by_arm']={p:False for p in policies};con.pop('rule4_hard_enabled',None);con['rule4_hard_enabled_by_arm']={'R2_OFF_TRANSPORT':True,'R2_R4_OFF_TRANSPORT':False};con['rule6_hard_enabled']=True
c['settings']['parallel_diagnostic']='Original complete pair predicate; R2_R4 records every reached conflicting leaf pair without hard rejection or extra score penalty. Earlier remaining-guard failures stay NOT_REACHED.'
c['external_memberships']['v10_unit001_START']=bind(P/'scenes/scan24/stages/START/MEMBERSHIP.npz')
c['external_memberships']['v10_unit001_R2_FINAL']=bind(F/'MEMBERSHIP.npz')
c['visual_policy'].update(arms=list(policies),focus_competitor_pairs=[[201906,-201934],[201906,-201915],[201906,-201901],[132977,8423],[132977,8534],[202023,274276]])
c['historical_control']='unit001 terminal R2 complete libraries replayed at matched restored state; R2 control must preserve every membership field, complete current curves and versions; no old growth rerun'
c['initial_catalog_policy']='Both complete policy catalogs frozen before any promotion; exact scientific/control geometry replay required; incomplete frontier cannot promote'
for name in ['input_files','helper_files']:
 for p,h in c[name].items():assert sha(p)==h,(name,p)
for original,snapshot in freeze['immutable_source_snapshot'].items():assert sha(S/Path(original).name)==freeze['source_files'][original],original
t=U/'tests';red=read(t/'RED_EXIT.json');green=read(t/'GREEN_EXIT.json');cli=read(t/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==cli['returncode']==0
assert 'actual library never dispatches [2,4]' in (t/'RED.log').read_text()
assert (t/'GREEN_INTEGRATION.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,test_count=green['test_count'],tdd_status='GENUINE_FUNCTIONAL_RED_GREEN for new [2,4] library dispatch: actual unit001 library lacks this arm, assertion fails; new arm selects finite-score parallel candidate. Existing 18 geometry/loader regressions reused; three replay/new-runner integration tests were added after initial GREEN, not claimed test-first.',red=dict(red,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),test_source=str(t/'RED_test_r4.py'),test_source_sha256=sha(t/'RED_test_r4.py'),baseline=str(t/'RED_relaxed_core.py'),baseline_sha256=sha(t/'RED_relaxed_core.py')),green=dict(green,log=str(t/'GREEN_INTEGRATION.log'),sha256=sha(t/'GREEN_INTEGRATION.log')),cli=dict(cli,log=str(t/'CLI.log'),sha256=sha(t/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,native_render=False,scope='36-row actual restricted loader + restored composite/new runner through cold mapping and replay, renderer stopped at entry; bounded actual geometry including >8 commits',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};write(U/'CONFIG.json',c)
script=str(S/'r4_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],tests_receipt=str(U/'TESTS_RECEIPT.json'),max_seconds=1800,python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),request=str(U/'RUN_REQUEST.json'),command=request['command'])))
