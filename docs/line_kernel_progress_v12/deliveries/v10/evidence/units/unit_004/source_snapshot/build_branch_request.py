"""Freeze transport experiment from immutable scan65 outputs, metadata/hash work only."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_best_fragment_growth_v09_20261102/continuation_001');P=O/'units/unit_002';U=O/'units/unit_003';F=P/'scenes/scan65/stages/WHOLE_FINAL'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 with Path(p).open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
prior_hash='a3b7f89896339fe4594b1dc9a46f703e6eea67abca8f9c824de79d466ffcec0a';assert sha(P/'CONFIG.json')==prior_hash
prior=read(P/'CONFIG.json');c=copy.deepcopy(prior);inputs=c['input_files'];fr=read(P/'PARENT_RUN_FROZEN.json');snapshot={}
def bind(p,expected=None):
 p=Path(p).resolve();h=sha(p)
 if expected:assert h==expected,str(p)
 inputs[str(p)]=h;return str(p)
assert fr['config_sha256']==prior_hash
for old,path in fr['immutable_source_snapshot'].items():
 h=fr['source_files'][old];bind(path,h);snapshot[path]=h;assert sha(S/Path(old).name)==h,('PRIOR_SOURCE_CHANGED',old)
assert len(snapshot)==25
for name in ['CONFIG.json','DECISION.json','PARENT_RUN_FROZEN.json']:bind(P/name)
cp=read(F/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior_hash;bind(F/'CHECKPOINT.json')
for name,h in cp['files'].items():bind(F/name,h)
assert sha(F/'MEMBERSHIP.npz')=='e9fbf75f1dec40b79b40db8012478f2494b3a1d756a0494980f343f1573bfeb6'
c.update(raw_config=str(P/'CONFIG.json'),restore_stage=str(F),restore_binding=prior_hash,initial_stage=str(F),initial_assigned=126423,initial_unknown=153193,initial_next_version=21668,seed_versions={'5558':21661,'22130':21667,'64111':21553,'156151':21665,'238627':21651},unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),max_seconds=1200,arms=['RADIAL_BRANCH','TRANSPORT_BRANCH'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(P/'source_snapshot'))
c['replay_libraries']={}
for sid in c['seed_ids']:
 paths=sorted((P/'scenes/scan65/libraries/WHOLE').glob('*_'+str(sid)));path=paths[-1]/'LIBRARY.json';assert read(path)['selected'] is None and read(path)['complete'];c['replay_libraries'][str(sid)]=bind(path);bind(path.parent/'GEOMETRY.npz')
c['external_memberships']['unit002_START']=bind(P/'scenes/scan65/stages/START/MEMBERSHIP.npz');c['external_memberships']['unit002_WHOLE_FINAL']=bind(F/'MEMBERSHIP.npz')
c['source_provenance']=dict(prior_config_sha256=prior_hash,exact_source_snapshot=snapshot,all_25_prior_files_byte_identical=True,new_branch_only=True,old_producers_executed=False,v08_unit012_used=False)
c['budgets'].update(total_seconds=1200,growth_stop_seconds=600,delivery_reserved_seconds=600,readiness_seconds=120)
c['settings']['background_reference']=str(F);c['settings']['fit']['policy']='WHOLE in both arms; all knots movable'
c['branch_policy']=dict(control='unchanged spatial radially signed axes',variant='minimal Q tangent rotation of those same axes',radius_p=4,cluster_angle_deg=20,qualifying_clusters=3,representatives_per_cluster=3,radial_span_p=2,eps=1e-8,antiparallel='unresolved whole TRANSPORT frontier PARTIAL',center_order='Q knots then original leaf knots in sorted leaf order',representative_order='sorted unique IDs',normal_inferred=False,changed_thresholds=False,initial_catalogs_before_promotion=True,original_replay='all five final WHOLE libraries, exact geometry arrays and scientific records',witness='G/F/union same centers plus premerge G, both policies; first rejecting center and all local source rows; compact gzip JSON')
c['seed_policy']['source']='exact unit002 WHOLE_FINAL current composites, seed identities unchanged';c['visual_policy']['arms']=c['arms']
window=read(O/'orchestration/WINDOW.json');assert c['absolute_deadline_jst']==window['science_wrap_jst']
for kind in ['input_files','helper_files']:
 for p,h in c[kind].items():assert sha(p)==h,(kind,p)
tests=U/'tests';red=read(tests/'RED_EXIT.json');green=read(tests/'GREEN_EXIT.json');cli=read(tests/'CLI_EXIT.json');assert red['returncode']==1 and green['returncode']==cli['returncode']==0
assert 'AssertionError' in (tests/'RED.log').read_text();assert (tests/'GREEN_VERIFIED.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: untransported baseline fails actual axis-rotation expectation; minimal rotation passes. Real restricted M4 plus composite restoration and guard callback exercised; actual three-arm conflict and curved two-arm fixtures, exact RADIAL replay and full cold maps tested.',red=dict(red,log=str(tests/'RED.log'),sha256=sha(tests/'RED.log'),baseline=str(tests/'RED_branch_core.py'),baseline_sha256=sha(tests/'RED_branch_core.py'),test_source=str(tests/'RED_test_branch.py'),test_source_sha256=sha(tests/'RED_test_branch.py')),green=dict(green,log=str(tests/'GREEN_VERIFIED.log'),sha256=sha(tests/'GREEN_VERIFIED.log')),cli=dict(cli,log=str(tests/'CLI.log'),sha256=sha(tests/'CLI.log')),test_count=19,real_loader_guard_test=True,full_asset_run=False,native_render=False,fixture_scope='bounded 36-row original-schema cold-load fixture and synthetic geometry only',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt);c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};write(U/'CONFIG.json',c)
script=str(S/'branch_runner.py');req=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')],max_seconds=1200,tests_receipt=str(U/'TESTS_RECEIPT.json'));write(U/'RUN_REQUEST.json',req)
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=req['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),inputs=len(inputs),command=req['command'])))
