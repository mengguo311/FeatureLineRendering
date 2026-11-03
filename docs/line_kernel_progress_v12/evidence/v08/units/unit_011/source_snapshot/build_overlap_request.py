"""Unit004 metadata-only request freeze. Does not load numerical assets or render."""
from pathlib import Path
import copy,hashlib,json,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102');P=O/'units/unit_003';U=O/'units/unit_004'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,obj):
 with Path(p).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
prior_hash='345d25ba0e31a6a0558fd4df305eb92b342b07e302a96786d850fca49e0088cd'
assert sha(P/'CONFIG.json')==prior_hash
c=copy.deepcopy(read(P/'CONFIG.json'));frozen=read(P/'PARENT_RUN_FROZEN.json');window=read(O/'orchestration/WINDOW.json');inputs=dict(c['input_files']);snapshots={}
for original,path in frozen['immutable_source_snapshot'].items():
 h=frozen['source_files'][original];assert sha(path)==h;inputs[path]=h;snapshots[Path(path).name]=dict(path=path,sha256=h)
for name in ['frontier_core.py','frontier_loader.py','frontier_delivery.py','geometry_base.py','port_paths.py','runtime_io.py','scene_render.py','observation_core.py','observation_oracle.py','observation_relay.py','observation_bank.py','relay_delivery.py']:
 assert sha(S/name)==snapshots[name]['sha256'],'Changed inherited helper '+name
for path in [P/'CONFIG.json',P/'DECISION.json',P/'PARENT_RUN_FROZEN.json',P/'FAILURE_ANALYSIS.json',P/'NEXT.json']:
 inputs[str(path)]=sha(path)
priorbank=P/'scenes/ficus/observation_bank';pc=read(priorbank/'CHECKPOINT.json');assert pc['complete'] and pc['config_sha256']==prior_hash
inputs[str(priorbank/'CHECKPOINT.json')]=sha(priorbank/'CHECKPOINT.json')
for name,h in pc['files'].items():assert sha(priorbank/name)==h;inputs[str(priorbank/name)]=h
root=P/'scenes/ficus/visits/BASE';paths=sorted(root.glob('*.json'));assert len(paths)==8
for p in paths:inputs[str(p)]=sha(p)
for arm in ['BASE','HISTORY']:
 path=P/'scenes/ficus/stages'/(arm+'_FINAL')/'MEMBERSHIP.npz';c['external_memberships']['unit003_'+arm]=str(path);inputs[str(path)]=sha(path)
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),prior_observed_visits_root=str(root),prior_observation_bank=str(priorbank),prior_config_sha256=prior_hash,observation_bank=str(U/'scenes/ficus/observation_bank'),absolute_deadline_jst='2026-11-02T07:38:00+09:00',max_seconds=1800)
assert c['absolute_deadline_jst']==window['science_wrap_jst']
c['historical_relay_policy']=c.pop('relay')
c['overlap']=dict(max_proposals=256,query_radius_p=1.5,complete_all_valid_finite_segments=True,nearest_k=None,one_exact_projection_per_donor_orientation=True,projection_ties='original lowest finite-segment ID before reversing',orientations=[False,True],overlap_window_max_p=2,registration_grid_spacing_p=1,registration_distance_max_p=1,registration_tangent_max_degrees=30,registration_samples='both boundaries + every mapped A/B knot + uniform spacing <=1p',blend='linear weight u/w, A(LA-w+u) to B(s-w+u); retain A prefix and B suffix',smoothing_or_fit=False,connector_angle_on_lateral_registration=False,whole_member_finite_domain=True,original_leaf_monotonic_samples_spacing_p=1,branch_knots='union of all original leaf knots and new auxiliary knots',support_mapping='all original interval endpoints to Q; record extended_s/clamp; union once',outward_support='donor tail s..LB AND positive pre-update source axial halfspace, clipped beyond new seam',history_gap_p=0,history_tail='oriented B from attachment s to LB',post_commit_ports='unit003 axial estimator on all retained members and current auxiliary Q',single_donor_transactions=True,overflow='entire frontier NOT_RUN; complete query/proposal list retained')
c['settings'].update(endpoint_radius_p=1.5,endpoint_tangent_degrees=None,connector_degrees=None,relation='finite overlap registration; no disjoint endpoint proposals',endpoint_angle_guards='historical unit003 only; not applied to transverse registration residual',scientific_stop='max64 attempts/arm; max8 accepted single donors/seed; frontier/library cap/deadline',outward_qualification_scope='single donor tail after attachment AND original-frontier positive halfspace',endpoint_tangent_source='unit003 source axial port for outward evidence; registration uses local directed finite-curve tangents',whole_path_geometry='replaceable current finite auxiliary overlap curve; all-member finite residual/tangent plus original turn/contact/parallel/branch/gap thresholds',history_geometry='pre-update outward A and oriented donor suffix; original history function with overlap gap0')
c['observation_policy']['purpose']='initialization/control replay and recomputed post-acceptance axial ports'
c['observation_policy']['query_and_oracle_port_policy']='source outward axis gates halfspace support; overlap relation uses registration and whole-current-curve checks, not endpoint connectors'
c['source_provenance']['unit003_snapshot']=snapshots;c['input_files']=inputs
for k,v in dict(legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False).items():assert c[k]==v
for p,h in c['helper_files'].items():assert sha(p)==h
py=window['python'];t=U/'tests';red=t/'RED.log';green=t/'GREEN_VERIFIED.log';exitinfo=read(t/'TEST_EXIT.json')
assert exitinfo['returncode']==0 and exitinfo['tests']==20
assert 'FAILED' in red.read_text() and '12.0' in red.read_text() and '8.0' in red.read_text()
assert 'Ran 20 tests' in green.read_text() and green.read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: old-style direct overlap concatenation produced length12 instead of8 in the first functional fixture; unchanged test now passes. Other new and inherited fixtures are regression coverage, not full-asset evidence.',red=dict(returncode=1,log=str(red),sha256=sha(red),command=[py,'-B','-m','unittest','-v','test_overlap'],cwd=str(S)),green=dict(returncode=exitinfo['returncode'],tests=20,log=str(green),sha256=sha(green),command=exitinfo['command'],cwd=str(S)),test_exit_receipt=dict(path=str(t/'TEST_EXIT.json'),sha256=sha(t/'TEST_EXIT.json')),intermediate_logs=[dict(path=str(p),sha256=sha(p)) for p in sorted(t.glob('GREEN_*.log')) if p!=green],real_loader_callback_test=True,full_asset_science_run=False,render_run=False,cli_help_returncode=0,cli_help_log=str(t/'CLI_HELP.log'),test_scope='synthetic <=48 kernels; actual restricted loader fixture, no whole real asset loading',fixture_notes='Preserved inherited parallel predicate: sparse two-knot collinear overlaps can fail it. Positive repeated-growth fixture uses dense original knots and tail support strictly above2p; no production guard change.',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c)
r=dict(script=str(S/'overlap_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'),python=py,command=[py,'-B',str(S/'overlap_runner.py'),'--config',str(U/'CONFIG.json')])
write(U/'RUN_REQUEST.json',r)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=r['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),helper_files=len(c['helper_files']),input_files=len(inputs))))
