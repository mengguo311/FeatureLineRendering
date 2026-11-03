"""Unit007 metadata/hash freeze only; does not load original numerical assets."""
from pathlib import Path
import copy,hashlib,json,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102');P=O/'units/unit_006';U=O/'units/unit_007'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,obj):
 with Path(p).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
prior='f65f359bddae63265b32f7ed24354aba47527676b43a4d1fbda4b86ab6cdc8cf'
assert sha(P/'CONFIG.json')==prior
c=copy.deepcopy(read(P/'CONFIG.json'));frozen=read(P/'PARENT_RUN_FROZEN.json');assert frozen['config_sha256']==prior
window=read(O/'orchestration/WINDOW.json');inputs=dict(c['input_files']);snapshots={}
for original,path in frozen['immutable_source_snapshot'].items():
 h=frozen['source_files'][original];assert sha(path)==h
 if Path(path).name not in ('overlap_core.py','switch_core.py'):assert sha(S/Path(path).name)==h,'Unexpected inherited source modification'
 inputs[path]=h;snapshots[Path(path).name]=dict(path=path,sha256=h)
for name in ['CONFIG.json','DECISION.json','PARENT_RUN_FROZEN.json','FAILURE_ANALYSIS.json','NEXT.json','scenes/ficus/COHORT_SELECTION.json']:
 path=P/name;inputs[str(path)]=sha(path)
initial=P/'scenes/ficus/stages/BASE_FINAL';cp=read(initial/'CHECKPOINT.json')
assert cp['files']['MEMBERSHIP.npz']=='365dfc05f91447be2213c5a6bf2a1e36fd8961679f50dfb261e48c781d66bab3'
assert cp['files']['GROWTH_STATE.json']=='8aefda9c2e3bffc425d8e4566495a8c04dae4032a3a50243323ab36d5b45189f'
for root in [initial,P/'scenes/ficus/stages/BASE_000',P/'scenes/ficus/observation_bank']:
 cc=read(root/'CHECKPOINT.json');assert cc['complete'] and cc['config_sha256']==prior;inputs[str(root/'CHECKPOINT.json')]=sha(root/'CHECKPOINT.json')
 for name,h in cc['files'].items():assert sha(root/name)==h;inputs[str(root/name)]=h
replay_cases=[dict(stage=str(P/'scenes/ficus/stages/BASE_000'),assigned=121987,next_version=20582,visit=str(P/'scenes/ficus/visits/BASE/0042.json')),dict(stage=str(initial),assigned=122004,next_version=20583,visit=str(P/'scenes/ficus/visits/BASE/0048.json'))]
for case in replay_cases:inputs[case['visit']]=sha(case['visit'])
for arm in ['BASE','HISTORY']:
 path=P/'scenes/ficus/stages'/(arm+'_FINAL')/'MEMBERSHIP.npz';inputs[str(path)]=sha(path);c['external_memberships']['unit006_'+arm]=str(path)
st=read(initial/'GROWTH_STATE.json');groups=read(initial/'GROUPS.json')['groups'];assert len(st['chains'])==24 and len(st['events'])==3 and st['next_version']==20583
seeds=sorted([[g['edge_id'],next(v['version'] for v in g['leaves'] if v['carrier_id']==g['edge_id'])] for g in groups]);assert len(seeds)==24
rawgroups=read(c['groups'])['groups'];kinds={str(g['edge_id']):g['model'] for g in rawgroups if str(g['edge_id']) in st['chains']};assert len(kinds)==24
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),initial_stage=str(initial),initial_assigned=122004,initial_next_version=20583,prior_config_sha256=prior,prior_observation_bank=str(P/'scenes/ficus/observation_bank'),observation_bank=str(U/'scenes/ficus/observation_bank'),absolute_deadline_jst=window['science_wrap_jst'],max_seconds=1800,seeds=seeds,seed_count=24,seed_kinds=kinds,replay_cases=replay_cases,arms=['LINEAR_BASE','LINEAR_HISTORY','HERMITE_BASE','HERMITE_HISTORY'],focus_seed=230214,focus_carriers=[230214,54189,54197,96009])
assert c['absolute_deadline_jst']=='2026-11-02T07:38:00+09:00'
c['historical_unit006_cohort']=c.pop('cohort');c['cohort_policy']=dict(selection='exact24 saved unit006 BASE_FINAL chains; no reselection',ports=48,all_seeds_protected=True,initial_events=3,initial_membership='all fields identical to saved state',condition_on_prior_BASE_acceptance=True,accepted_merge_is_ground_truth=False)
c['switch']['initial_state']='exact unit006 BASE_FINAL; no initial relabel/version allocation';c['switch'].pop('reopen_all_eight_ports',None);c['switch']['reopen_policy']='all48 ports; reset only attempts/accepts/stopped; preserve curves,ports,used,versions,aux and three events'
c['settings']['initialization_membership_invariant']='all fields exact against unit006 BASE_FINAL';c['settings']['scientific_stop']='64 new attempts per each of four arms;8 new accepts per seed; complete library/phase limits'
c['seam']=dict(representations=['LINEAR','HERMITE'],registration='unchanged unit004 register tests and exact closest donor projection',local_window_before_A_endpoint_p=2.,local_window_after_B_attachment_p=2.,a='LA-min(2,LA)',b='s+min(2,LB-s)',boundary_tangents='directed tangent_at on original oriented A/B at a,b; lowest segment ties',bezier_controls='P0=A(a),P3=B(b),D=norm(P3-P0),P1=P0+D*t0/3,P2=P3-D*t1/3',degenerate_chord_reject_p=1e-8,sample_segments='max(1,ceil(12*max_j norm(P[j+1]-P[j])))',max_segments=128,max_sample_spacing_p=.25,uniform_parameter_sampling=True,outside_region='A before a and B after b retained exactly',duplicate_removal='consecutive EPS only',seam_coordinate='lowest-tie finite projection of B(s) onto new Q',history='pre-update A and unmodified B tail after s, gap0',model_fitting=False,retries=0,fallback_to_linear=False,whole_member_guards='unchanged overlap_core.validate',representation_shadows='both complete libraries on each visited state; rollout divergence explicit',initial_catalog='all96 representation/frontier libraries before any four-arm promotion')
c['visual_policy'].update(focus_carriers=c['focus_carriers'],new_cases='top3 actual changed line and polyline seed memberships by max outward support then ID; top3 lost starting rows; no floating-noise inherited growth promotion',all_four_arms=True)
c['budgets'].update(total_seconds=1800,growth_stop_seconds=1200,delivery_reserved_seconds=600,readiness_seconds=120,max_new_attempts_per_arm=64,max_new_accepts_per_seed=8)
c['source_provenance']['unit006_snapshot']=snapshots;c['input_files']=inputs
for k,v in dict(legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False).items():assert c[k]==v
for path,h in c['helper_files'].items():assert sha(path)==h
# Read-only full dependency hashing; no array numerical load.
for path,h in inputs.items():assert sha(path)==h,('INPUT_BINDING',path)
t=U/'tests';green=read(t/'TEST_EXIT.json');red=read(t/'RED_EXIT.json');cli=read(t/'CLI_HELP_EXIT.json');assert green['returncode']==0 and red['returncode']!=0 and cli['returncode']==0
assert 'FAILED' in (t/'RED.log').read_text() and 'Ran 28 tests' in (t/'GREEN_VERIFIED.log').read_text() and (t/'GREEN_VERIFIED.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: original linear registration fails the short-overlap constrained-seam fixture; frozen Hermite seam passes the unchanged test. 28 bounded tests pass, including real loader and four-arm runner through cold final maps before deliberate renderer stop. No full-asset science.',red=dict(**red,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),baseline_source=str(t/'RED_seam_core.py'),baseline_source_sha256=sha(t/'RED_seam_core.py'),test_source=str(t/'RED_test_seam.py'),test_source_sha256=sha(t/'RED_test_seam.py')),green=dict(**green,log=str(t/'GREEN_VERIFIED.log'),sha256=sha(t/'GREEN_VERIFIED.log')),test_exit_receipt=dict(path=str(t/'TEST_EXIT.json'),sha256=sha(t/'TEST_EXIT.json')),intermediate_failure=dict(log=str(t/'GREEN_1.log'),sha256=sha(t/'GREEN_1.log'),exit=read(t/'GREEN_1_EXIT.json')),cli_help=dict(**cli,log=str(t/'CLI_HELP.log'),sha256=sha(t/'CLI_HELP.log')),real_loader_callback_test=True,real_runner_fixture_kernels=48,full_asset_science_run=False,render_run=False,test_scope='only synthetic <=48 kernels; all fixture ROOTs explicitly unit007; no old test discovery',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};write(U/'CONFIG.json',c)
py=window['python'];script=str(S/'seam_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'),python=py,command=[py,'-B',script,'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),helper_files=len(c['helper_files']))))
