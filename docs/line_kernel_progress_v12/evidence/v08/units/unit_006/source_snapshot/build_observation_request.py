"""Unit003 build-only freeze writer: metadata/hash reads, no numerical asset loading."""
from pathlib import Path
import copy,hashlib,json,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102');P=O/'units/unit_002';U=O/'units/unit_003'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 with Path(p).open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
assert sha(P/'CONFIG.json')=='782cd1b45bd12cc459d28f618c928d04af18a0b706f59832ebc0445f3fbaad51'
c=copy.deepcopy(read(P/'CONFIG.json'));frozen=read(P/'PARENT_RUN_FROZEN.json');window=read(O/'orchestration/WINDOW.json');inputs=dict(c['input_files']);snapshots={}
for original,path in frozen['immutable_source_snapshot'].items():
 h=frozen['source_files'][original];assert sha(path)==h;inputs[path]=h;snapshots[Path(path).name]=dict(path=path,sha256=h)
for name in ['frontier_core.py','frontier_loader.py','frontier_delivery.py','port_paths.py','geometry_base.py','runtime_io.py','scene_render.py','relay_core.py','relay_delivery.py']:
 assert sha(S/name)==snapshots[name]['sha256'],'Prior frozen policy changed: '+name
for path in [P/'CONFIG.json',P/'DECISION.json',P/'PARENT_RUN_FROZEN.json',P/'FAILURE_ANALYSIS.json',P/'NEXT.json']:
 inputs[str(path)]=sha(path)
root=P/'scenes/ficus/visits/BASE';paths=sorted(root.glob('*.json'));assert len(paths)==8
for path in paths:inputs[str(path)]=sha(path)
for arm in ['BASE','HISTORY']:
 path=P/'scenes/ficus/stages'/(arm+'_FINAL')/'MEMBERSHIP.npz';c['external_memberships']['unit002_'+arm]=str(path);inputs[str(path)]=sha(path)
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),prior_relay_visits_root=str(root),observation_bank=str(U/'scenes/ficus/observation_bank'),absolute_deadline_jst='2026-11-02T07:38:00+09:00',max_seconds=1800)
assert c['absolute_deadline_jst']==window['science_wrap_jst']
c['observation_policy']=dict(support_bounds='union of saved intervals in original finite q; EPS-only clamping',geometry='interpolate support bounds; retain every interior original knot; no fit/extrapolation/member removal',member_revalidation='all original rows against q_obs using unchanged residual/tangent gates',port_window_p=2,port_arc_bin_p=1,min_valid_derivative_kernels=3,tensor_weights='equal total weight per occupied bin',eigenvalue_ratio_min=2,eigenvalue_min=1e-8,sign='align principal axis with q_obs outward segment; abs dot<=EPS UNKNOWN',projection_ties='lowest segment ID',query_and_oracle_port_policy='same observed source outward and donor inward axes',unknown_port='cannot gain a link; background memberships unchanged',old_original_neighbor_shadow=True,original_q_preserved_separately=True)
c['settings']['endpoint_tangent_source']='observed kernel-derivative port axis; same local-query and complete-oracle dispatch'
c['settings']['whole_path_geometry']='support-clipped q_obs; original turn/contact/parallel/branch/gap limits'
c['settings']['history_geometry']='oriented q_obs composite; unchanged history function'
c['source_provenance']['unit002_snapshot']=snapshots;c['input_files']=inputs
for field,value in dict(legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False).items():assert c[field]==value
assert all('/source_snapshot/' not in p and not p.endswith('.json') for p in c['helper_files'])
py=window['python'];t=U/'tests';red=t/'RED.log';green=t/'GREEN_FINAL.log'
assert 'FAILED' in red.read_text() and 'AssertionError' in red.read_text()
assert 'Ran 25 tests' in green.read_text() and green.read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: support-clipping assertion first failed against previous untrimmed representation; the same fixture now passes. Additional whole-oracle and checkpoint fixtures are regressions; no full-data numerical claim.',red=dict(returncode=1,log=str(red),sha256=sha(red),command=[py,'-B','-m','unittest','-v','test_observation.ObservationTests.test_support_clipping_retains_all_members'],cwd=str(S)),green=dict(returncode=0,tests=25,log=str(green),sha256=sha(green),command=[py,'-B','-m','unittest','-v','test_frontier','test_loader_fixture','test_relay','test_observation'],cwd=str(S)),intermediate_logs=[dict(path=str(t/name),sha256=sha(t/name),returncode=0) for name in ['GREEN_observation.log','GREEN_PIPELINE.log']],real_loader_callback_test=True,full_asset_science_run=False,render_run=False,cli_help_returncode=0,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c)
r=dict(script=str(S/'observation_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'),python=py,command=[py,'-B',str(S/'observation_runner.py'),'--config',str(U/'CONFIG.json')])
write(U/'RUN_REQUEST.json',r)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=r['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),helper_files=len(c['helper_files']),input_files=len(inputs))))
