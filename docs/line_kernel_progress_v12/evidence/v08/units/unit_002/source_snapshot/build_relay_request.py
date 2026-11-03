"""Build-only unit002 manifest writer. Hashes files; never loads numerical assets."""
from pathlib import Path
import copy,hashlib,json,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102')
U=O/'units/unit_002';P=O/'units/unit_001'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 with Path(p).open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
assert sha(P/'CONFIG.json')=='010cd6389206a5093067c20c790a41757483844cb70bcfe765f3e1a343f9fe2e'
c=copy.deepcopy(read(P/'CONFIG.json'));frozen=read(P/'PARENT_RUN_FROZEN.json');window=read(O/'orchestration/WINDOW.json')
inputs=dict(c['input_files']);snapshots={}
for original,path in frozen['immutable_source_snapshot'].items():
 expected=frozen['source_files'][original];assert sha(path)==expected
 inputs[path]=expected;snapshots[Path(path).name]=dict(path=path,sha256=expected)
for name in ['frontier_core.py','frontier_loader.py','frontier_delivery.py','port_paths.py','geometry_base.py','runtime_io.py','scene_render.py']:
 assert sha(S/name)==snapshots[name]['sha256'],'Frozen shared policy changed: '+name
for path in [P/'CONFIG.json',P/'DECISION.json',P/'PARENT_RUN_FROZEN.json']:
 inputs[str(path)]=sha(path)
visits=P/'scenes/ficus/visits/BASE';paths=sorted(visits.glob('*.json'));assert len(paths)==8
for path in paths:inputs[str(path)]=sha(path)
for arm in ['BASE','HISTORY']:
 path=P/'scenes/ficus/stages'/(arm+'_FINAL')/'MEMBERSHIP.npz'
 c['external_memberships']['unit001_'+arm]=str(path);inputs[str(path)]=sha(path)
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),prior_visits_root=str(visits),absolute_deadline_jst='2026-11-02T07:38:00+09:00',max_seconds=1800)
assert window['science_wrap_jst']==c['absolute_deadline_jst']
c['seeds']=sorted(c['seeds']);c['relay']=dict(max_donors=3,max_prefixes=256,overflow='whole frontier NOT_RUN; no truncated promotion',enumeration='canonical carrier/port DFS; locally valid nonempty prefixes',minimality='first support AND whole-path-valid prefix; failed shorter prefixes remain expandable',qualification_scope='all new relay leaves; start-frontier positive halfspace',sort=['first_gap','total_gap','donor_count','canonical_oriented_sequence'],ambiguity='first two common relays within 0.15p first-gap; before history including shared-first-donor branches',history_input='current outward seed chain and complete oriented relay; unchanged unit001 history',atomic_donors=True,full_radius_queries=True)
c['settings']['outward_qualification_scope']='aggregate newly proposed relay; no intermediate single-leaf six-kernel/two-p veto'
c['settings']['scientific_stop']='max64 transactions per arm/max8 accepted relays per seed/dead frontier/cap/deadline'
c['source_provenance']['unit001_snapshot']=snapshots
c['input_files']=inputs
assert c['helper_files'] and all('/source_snapshot/' not in k and not k.endswith('.json') for k in c['helper_files'])
for field,value in dict(legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False).items():assert c[field]==value
py=window['python'];testroot=U/'tests'
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: the two-three-kernel-leaf relay test failed with zero common candidates under the initial delegation to unit001 single-donor logic; after relay implementation the same test and 17 regressions pass. No real-asset numerical claim.',red=dict(returncode=1,log=str(testroot/'RED.log'),sha256=sha(testroot/'RED.log'),command=[py,'-B','-m','unittest','-v','test_relay.RelayTests.test_two_small_leaves_jointly_qualify'],cwd=str(S),failure='AssertionError: 0 != 1'),green=dict(returncode=0,tests=18,log=str(testroot/'GREEN_FINAL.log'),sha256=sha(testroot/'GREEN_FINAL.log'),command=[py,'-B','-m','unittest','-v','test_frontier','test_loader_fixture','test_relay'],cwd=str(S)),intermediate_logs=[dict(path=str(testroot/'GREEN_initial.log'),sha256=sha(testroot/'GREEN_initial.log'),returncode=0)],loader_test='Actual six-row restricted pickle/NPZ/control loader; guard(phase) call and exception propagation retained. Atomic full fixture-row relay checkpoint cold-loaded.',full_asset_science_run=False,render_run=False,cli_help_returncode=0,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
assert 'AssertionError: 0 != 1' in (testroot/'RED.log').read_text()
assert 'Ran 18 tests' in (testroot/'GREEN_FINAL.log').read_text() and (testroot/'GREEN_FINAL.log').read_text().rstrip().endswith('OK')
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c)
request=dict(script=str(S/'relay_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'),python=py,command=[py,'-B',str(S/'relay_runner.py'),'--config',str(U/'CONFIG.json')])
write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),helper_files=len(c['helper_files']),input_files=len(inputs))))
