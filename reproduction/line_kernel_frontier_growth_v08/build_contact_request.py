"""Unit008 metadata-only freeze. Never loads numerical arrays or starts science."""
from pathlib import Path
import copy,hashlib,json,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102')
P=O/'units/unit_007';U=O/'units/unit_008'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,obj):
 with Path(p).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
prior='2dad2b4994628a645dde9cd0d0532298160903cd204020953e90810483a06987'
assert sha(P/'CONFIG.json')==prior
c=copy.deepcopy(read(P/'CONFIG.json'));frozen=read(P/'PARENT_RUN_FROZEN.json');assert frozen['config_sha256']==prior
window=read(O/'orchestration/WINDOW.json');inputs=dict(c['input_files']);snapshots={}
for original,path in frozen['immutable_source_snapshot'].items():
 h=frozen['source_files'][original];assert sha(path)==h
 assert sha(S/Path(path).name)==h,'Inherited source changed'
 inputs[path]=h;snapshots[Path(path).name]=dict(path=path,sha256=h)
for name in ['CONFIG.json','DECISION.json','PARENT_RUN_FROZEN.json','FAILURE_ANALYSIS.json','NEXT.json','scenes/ficus/INITIAL_LIBRARY_FREEZE.json']:
 path=P/name;inputs[str(path)]=sha(path)
initial=P/'scenes/ficus/stages/HERMITE_BASE_FINAL';cp=read(initial/'CHECKPOINT.json')
assert cp['files']['MEMBERSHIP.npz']=='365dfc05f91447be2213c5a6bf2a1e36fd8961679f50dfb261e48c781d66bab3'
assert cp['files']['GROWTH_STATE.json']=='71d5a5ca6868258b1d767b02145764d98ebcf6f5e47ee29c9671b25df5ada369'
for root in [initial,P/'scenes/ficus/observation_bank']:
 cc=read(root/'CHECKPOINT.json');assert cc['complete'] and cc['config_sha256']==prior
 inputs[str(root/'CHECKPOINT.json')]=sha(root/'CHECKPOINT.json')
 for name,h in cc['files'].items():assert sha(root/name)==h;inputs[str(root/name)]=h
st=read(initial/'GROWTH_STATE.json');assert len(st['chains'])==24 and len(st['events'])==3 and st['next_version']==20583
assert sorted(map(int,st['chains']))==sorted(x[0] for x in c['seeds'])
replays=[]
for sid in sorted(map(int,st['chains'])):
 for side in (0,1):
  path=P/'scenes/ficus/initial_libraries'/f'HERMITE_{sid}_{side}.json';z=read(path)
  assert z['seed']==sid and z['side']==side and z['status']=='COMPLETE'
  assert z['shadow']['BASE'] is None and z['shadow']['HISTORY'] is None
  inputs[str(path)]=sha(path);replays.append(str(path))
for arm in c['arms']:
 path=P/'scenes/ficus/stages'/(arm+'_FINAL')/'MEMBERSHIP.npz';inputs[str(path)]=sha(path);c['external_memberships']['unit007_'+arm]=str(path)
pairs=[[112780,168654],[23216,23209],[26025,167360],[79841,177351],[79841,79855]]
focus=sorted({230214,54189,54197,96009}|{i for pair in pairs for i in pair})
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),initial_stage=str(initial),initial_assigned=122004,initial_next_version=20583,prior_config_sha256=prior,prior_observation_bank=str(P/'scenes/ficus/observation_bank'),observation_bank=str(U/'scenes/ficus/observation_bank'),absolute_deadline_jst=window['science_wrap_jst'],max_seconds=1800,replay_libraries=replays,arms=['INDEX_BASE','INDEX_HISTORY','ARC_BASE','ARC_HISTORY'],contact_focus_pairs=pairs,focus_carriers=focus)
c['historical_unit007_replay_cases']=c.pop('replay_cases')
c['cohort_policy']['selection']='exact24 saved unit007 HERMITE_BASE_FINAL chains; no reselection'
c['switch']['initial_state']='exact unit007 HERMITE_BASE_FINAL; no initial relabel/version allocation'
c['settings']['initialization_membership_invariant']='all fields exact against unit007 HERMITE_BASE_FINAL'
c['settings']['whole_path_geometry']='unchanged whole-member/turn/parallel/branch/support tests; contact policy INDEX or intrinsic ARC only on final proposed Q'
c['settings']['contact_arc_exclusion_p']=1.
c['historical_unit007_seam']=copy.deepcopy(c['seam'])
c['seam']['representations']=['HERMITE'];c['seam']['representation_shadows']='fixed Hermite; both contact policies on every visited state'
c['seam']['initial_catalog']='all96 contact-policy/frontier libraries before four-arm promotion'
c['contact']=dict(policies=['INDEX','ARC'],distance_p=.5,intrinsic_separation_p=1.,EPS=1e-8,scope='only final proposed-Q contact; inherited observation bank validity unchanged',common_check_only_collinear_handling='unchanged original geometry_guard',INDEX='original contact_bounded on simplified Q; segment index separation>=2',ARC='global minimum over all affine segment point pairs with S_j+v*l_j-S_i-u*l_i>=1; all i<=j, including same and adjacent segments',pair_solver='clipped unit rectangle; feasible unconstrained least-squares stationary point plus exact quadratic edge minima; singular and empty domains explicit',ties='distance then intrinsic arclength pair then segment IDs',witnesses=['distance_p','segment_ids','parameters','arclengths_p','arc_separation_p','points_p'],bounded_memory=True,approximate_sampling=False,model_fitting=False,contact_guard_definition_changed=True,minimal_relay_prefixes_may_differ=True,earlier_guard_failures_authoritative=True)
c['visual_policy'].update(focus_carriers=focus,contact_focus_pairs=pairs,all_four_arms=True)
c['budgets'].update(total_seconds=1800,growth_stop_seconds=1200,delivery_reserved_seconds=600,readiness_seconds=120,max_new_attempts_per_arm=64,max_new_accepts_per_seed=8)
c['source_provenance']['unit007_snapshot']=snapshots;c['input_files']=inputs
assert c['absolute_deadline_jst']=='2026-11-02T07:38:00+09:00'
for k,v in dict(legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False).items():assert c[k]==v
for path,h in c['helper_files'].items():assert sha(path)==h
# Full byte/hash verification only, no Gaussian/control array load.
for path,h in inputs.items():assert sha(path)==h,('INPUT_BINDING',path)
t=U/'tests';red=read(t/'RED_EXIT.json');green=read(t/'TEST_EXIT.json');cli=read(t/'CLI_HELP_EXIT.json')
assert red['returncode']!=0 and green['returncode']==0 and cli['returncode']==0
assert 'AssertionError: True is not false' in (t/'RED.log').read_text()
assert 'Ran 37 tests' in (t/'GREEN_VERIFIED.log').read_text() and (t/'GREEN_VERIFIED.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: inherited index contact rejects dense gentle-arc fixture; intrinsic implementation passes unchanged assertion. 37 bounded tests pass, including exact subdivision invariance, nonlocal crossing, real final-Q validation and real loader through four-arm cold maps before deliberate render-boundary stop.',red=dict(**red,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),baseline_source=str(t/'RED_contact_core.py'),baseline_source_sha256=sha(t/'RED_contact_core.py'),test_source=str(t/'RED_test_contact.py'),test_source_sha256=sha(t/'RED_test_contact.py')),green=dict(**green,log=str(t/'GREEN_VERIFIED.log'),sha256=sha(t/'GREEN_VERIFIED.log')),test_exit_receipt=dict(path=str(t/'TEST_EXIT.json'),sha256=sha(t/'TEST_EXIT.json')),earlier_green=dict(log=str(t/'GREEN_1.log'),sha256=sha(t/'GREEN_1.log'),exit=read(t/'GREEN_1_EXIT.json')),cli_help=dict(**cli,log=str(t/'CLI_HELP.log'),sha256=sha(t/'CLI_HELP.log')),real_loader_callback_test=True,real_runner_fixture_kernels=48,full_asset_science_run=False,render_run=False,test_scope='explicit classes only; all mutable test roots unit008; no historical suite discovery',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};write(U/'CONFIG.json',c)
py=window['python'];script=str(S/'contact_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'),python=py,command=[py,'-B',script,'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),helper_files=len(c['helper_files']))))
