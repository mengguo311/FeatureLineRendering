"""Unit005 metadata-only freeze. Never loads Gaussian arrays or runs science."""
from pathlib import Path
import copy,hashlib,json,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102');P=O/'units/unit_004';U=O/'units/unit_005'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,obj):
 with Path(p).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
prior='e73736f7a81ea46805e01f2b0529ae2258b3a2c7b2cd978dfb0fb01621bc7ac5'
assert sha(P/'CONFIG.json')==prior
c=copy.deepcopy(read(P/'CONFIG.json'));frozen=read(P/'PARENT_RUN_FROZEN.json');assert frozen['config_sha256']==prior
window=read(O/'orchestration/WINDOW.json');inputs=dict(c['input_files']);snapshots={}
for original,path in frozen['immutable_source_snapshot'].items():
 h=frozen['source_files'][original];assert sha(path)==h;assert sha(S/Path(path).name)==h,'Inherited source modified';inputs[path]=h;snapshots[Path(path).name]=dict(path=path,sha256=h)
for name in ['CONFIG.json','DECISION.json','PARENT_RUN_FROZEN.json','FAILURE_ANALYSIS.json','NEXT.json']:
 path=P/name;inputs[str(path)]=sha(path)
initial=P/'scenes/ficus/stages/BASE_FINAL';cp=read(initial/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior
assert cp['files']['MEMBERSHIP.npz']=='f063a792c48aec5c70e65833ad38c6d458e7049f019afc965e6d7c1480e40709'
assert cp['files']['GROWTH_STATE.json']=='7982aa18d959ce7655297586f71e46470e6866b7b3dcfe02a6571190d85c2ba0'
for root in [initial,P/'scenes/ficus/observation_bank']:
 cc=read(root/'CHECKPOINT.json');assert cc['complete'] and cc['config_sha256']==prior;inputs[str(root/'CHECKPOINT.json')]=sha(root/'CHECKPOINT.json')
 for name,h in cc['files'].items():assert sha(root/name)==h;inputs[str(root/name)]=h
visits=sorted((P/'scenes/ficus/visits').glob('*/*.json'));assert len(visits)==22
for path in visits:inputs[str(path)]=sha(path)
for arm in ['BASE','HISTORY']:
 path=P/'scenes/ficus/stages'/(arm+'_FINAL')/'MEMBERSHIP.npz';inputs[str(path)]=sha(path);c['external_memberships']['unit004_'+arm]=str(path)
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),initial_stage=str(initial),initial_assigned=121987,initial_next_version=20582,prior_config_sha256=prior,prior_observation_bank=str(P/'scenes/ficus/observation_bank'),observation_bank=str(U/'scenes/ficus/observation_bank'),prior_context_visits=[str(p) for p in visits],deadend_visits=[str(P/'scenes/ficus/visits/BASE'/n) for n in ['0009.json','0010.json']],absolute_deadline_jst=window['science_wrap_jst'],max_seconds=1800)
assert c['absolute_deadline_jst']=='2026-11-02T07:38:00+09:00'
c['switch']=dict(max_combined_prefixes=256,max_endpoint_donors=3,complete_endpoint_radius_p=1.5,endpoint_tangent_degrees=30,endpoint_connector_degrees=35,zero_gap='tangent only',source_axis='current composite observation port; subsequent donor observation ports',seed_curve='current saved auxiliary q, never reconstructed from original leaves',relation_scope='single overlap OR endpoint-only minimal relay per transaction; switching between transactions',combined_count='all overlap orientations plus locally hop-qualified endpoint prefixes;257 aborts whole frontier',short_prefix_failures='expand through at most3 donors; first support+whole-geometry valid prefix terminates branch',outward_support='>=6 unique original kernels and>=2p interval union in original starting outward halfspace; mapped onto proposed Q',connectors='zero observed support and never ink; retain/rebase connector intervals',ranking=['first_attachment_distance','total_attachment_distance','donor_count','canonical_oriented_sequence','relation_type'],deduplication='identical relation and sequence only',shared_ambiguity_p=.15,history='unchanged function; endpoint full relay/first gap; overlap tail/gap0',initial_state='exact saved unit004 BASE_FINAL',reopen_all_eight_ports=True,reset='new-unit counters only; retain used leaves, curves, ports, versions, lineage',history_not_ground_truth=True)
c['historical_unit004_settings']=copy.deepcopy(c['settings'])
c['settings'].update(relation='shared single-overlap and endpoint-relay library',endpoint_tangent_degrees=30,connector_degrees=35,endpoint_angle_guards='apply only to endpoint relay hops; overlap registration unchanged',outward_qualification_scope='overlap donor tail OR aggregate endpoint relay, starting positive halfspace',whole_path_geometry='unit004 validate on final Q for both relation types',scientific_stop='64 NEW attempts/arm;8 NEW accepts/seed; capacity or deadline',history_geometry='pre-update current outward Q versus relay Q/first gap or overlap tail/gap0')
c['observation_policy']['purpose']='exact replay of saved observation bank and composite axial ports; derivative invalidity remains UNKNOWN'
c['observation_policy']['query_and_oracle_port_policy']='endpoint hops use current/source and donor observed axes; overlap uses unchanged registration guards'
c['budgets']=dict(readiness_seconds=120,growth_stop_seconds=1200,delivery_reserved_seconds=600,total_seconds=1800,max_new_attempts_per_arm=64,max_new_accepts_per_seed=8,cpu_blas_threads=2,unit_output_bytes=2*2**30,runtime_output_bytes=20*2**30)
c['source_provenance']['unit004_snapshot']=snapshots;c['input_files']=inputs
for k,v in dict(legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False).items():assert c[k]==v
for path,h in c['helper_files'].items():assert sha(path)==h
t=U/'tests';exitinfo=read(t/'TEST_EXIT.json');redinfo=read(t/'RED_EXIT.json');assert exitinfo['returncode']==0 and redinfo['returncode']!=0;assert read(t/'CLI_HELP_EXIT.json')['returncode']==0
assert '0 != 1' in (t/'RED.log').read_text() and 'FAILED' in (t/'RED.log').read_text()
assert 'Ran 20 tests' in (t/'GREEN_VERIFIED.log').read_text() and (t/'GREEN_VERIFIED.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: overlap-only baseline produced0 eligible relays where two bounded endpoint donors jointly supply2.4p; same assertion passed after implementation. Other tests are bounded regression checks.',red=dict(**redinfo,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),baseline_source=str(t/'RED_switch_core.py'),baseline_source_sha256=sha(t/'RED_switch_core.py'),test_source=str(t/'RED_test_switch.py'),test_source_sha256=sha(t/'RED_test_switch.py')),green=dict(**exitinfo,log=str(t/'GREEN_VERIFIED.log'),sha256=sha(t/'GREEN_VERIFIED.log')),test_exit_receipt=dict(path=str(t/'TEST_EXIT.json'),sha256=sha(t/'TEST_EXIT.json')),real_loader_callback_test=True,full_asset_science_run=False,render_run=False,cli_help_returncode=0,cli_help_log=str(t/'CLI_HELP.log'),test_scope='synthetic <=48 kernels; actual restricted loader and cold-state/checkpoint contracts, no whole-asset numerical execution',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c);py=window['python'];r=dict(script=str(S/'switch_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'),python=py,command=[py,'-B',str(S/'switch_runner.py'),'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',r)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=r['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),helper_files=len(c['helper_files']),input_files=len(inputs))))
