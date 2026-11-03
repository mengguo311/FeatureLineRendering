"""Freeze scan65 metadata only. Does not load original kernel arrays or execute science."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
R=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
O=R/'line_kernel_best_fragment_growth_v09_20261102/continuation_001';P=O/'units/unit_001';U=O/'units/unit_002'
V=R/'line_kernel_edge_growth_v05_20261031/units/unit_017';T=V/'scenes/scan65/stages/M4_MERGE_ONLY'
PREFIX=R/'line_kernel_edge_growth_v05_20261031/units/unit_009/scenes/scan65/stages/M4_MERGE_ONLY'
M3=R/'line_kernel_edge_growth_v05_20261031/units/unit_006/scenes/scan65/stages/M3_MERGE_ONLY'
JOINT=R/'line_kernel_edge_growth_v05_20261031/units/unit_014/scenes/scan65/stages/M4_MERGE_ONLY'
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,obj):
 with Path(path).open('x') as f:json.dump(obj,f,indent=2,ensure_ascii=False,allow_nan=False)
prior_hash='f165be882ffcadc4bf94a7b89e98e4a5b40cef94fe8e5afff10256117999df99'
assert sha(P/'CONFIG.json')==prior_hash
assert sha(V/'CONFIG.json')=='6188a2f45240e56aed9df52e265dbea3bd77cf0ce3cfe82d97201608e493a5a4'
prior=read(P/'CONFIG.json');c=copy.deepcopy(prior);frozen=read(P/'PARENT_RUN_FROZEN.json');assert frozen['config_sha256']==prior_hash
inputs={};snapshot={};deltas={}
def bind(path,expected=None):
 path=Path(path).resolve();h=sha(path)
 if expected is not None:assert h==expected,('BINDING',str(path))
 inputs[str(path)]=h;return str(path)
for original,path in frozen['immutable_source_snapshot'].items():
 h=frozen['source_files'][original];bind(path,h);snapshot[str(path)]=h;target=S/Path(original).name
 if target.name=='frontier_loader.py':
  old=Path(path).read_text();new=target.read_text();assert old.count("pc['stage']=='M5_STATE'")==1
  assert new==old.replace("pc['stage']=='M5_STATE'","pc['stage']==c.get('predecessor_checkpoint_stage','M5_STATE')")
  deltas[str(target)]='Only replace M5_STATE literal with explicit predecessor_checkpoint_stage; default M5_STATE retained.'
 else:assert sha(target)==h,('UNCHANGED_PRIOR_SOURCE',original)
assert len(snapshot)==20
for name in ['CONFIG.json','PARENT_RUN_FROZEN.json','DECISION.json']:bind(P/name)
v=read(V/'CONFIG.json');window=read(O/'orchestration/WINDOW.json')
for name in ['CONFIG.json','DECISION.json']:bind(V/name)
for key in ['gaussians','controls','representatives','cameras','renderer','libroot']:c[key]=v[key]
for key in ['gaussians','controls','representatives','cameras']:bind(c[key])
assert inputs[c['controls']]=='afb766822a92b6b268807e451e7b06b47a11f3efc7ca2bc7cca13842b59bdcf1'
assert inputs[c['cameras']]=='9020d0599f28aaa500b3c24bb28a8c6cc0c6896eda6753b407a9924e970670c4'
for key,name in [('membership','MEMBERSHIP.npz'),('carriers','CARRIERS.npz'),('groups','GROUPS.json'),('lineage','LINEAGE.json')]:c[key]=bind(T/name)
c['state']=bind(V/'scenes/scan65/states/M4/STATE.pkl','062f4d1eb7612c295ae8cd0772d4cb59845ff58a0ffdc241e14ad3db2fec3441')
c['predecessor_checkpoint']=bind(V/'scenes/scan65/states/M4/CHECKPOINT.json','d2c5e4bcea3ac9b1f5226758f6e8c89b8a8f42c56cec09bd58b2bdb1f170c99e')
c['predecessor_config']=str(V/'CONFIG.json');c['predecessor_checkpoint_stage']='M4_STATE'
def checkpoint_inputs(path):
 p=Path(path);cp=read(p);assert cp['complete'];bind(p)
 for name,h in cp['files'].items():
  child=p.parent/name;bind(child,h)
  if child.name=='CHECKPOINT.json':checkpoint_inputs(child)
checkpoint_inputs(c['predecessor_checkpoint'])
c['m4_membership']=c['membership'];c['external_memberships']={'M3':bind(M3/'MEMBERSHIP.npz'),'M4_PREFIX_unit009':bind(PREFIX/'MEMBERSHIP.npz'),'M4_JOINT_unit014':bind(JOINT/'MEMBERSHIP.npz')}
for ref in [M3,PREFIX,JOINT]:
 for name in ['GROUPS.json','LINEAGE.json']:bind(ref/name)
c['unavailable_references']={'scan65_M5':'NOT_EXECUTED: strongest sealed input is unit017 M4','scan65_v06':'No executed scan65 v06 comparison bound; scan24/ficus results are not this scene control'}
c['baseline_label']='M4';c['negative_pairs']=[];c.pop('negative_carriers',None)
c['negative_context_selection']=bind(T/'diagnostics/CONTEXT_SELECTION.json');c['negative_contexts']=[]
for rec in read(c['negative_context_selection']):
 c['negative_contexts'].append(dict(category=rec['category'],rows_path=bind(T/'diagnostics'/rec['rows_file']),input_versions=rec['input_versions'],saved_record=rec['record']))
assert len(c['negative_contexts'])==6
c['damage_carriers']=bind(PREFIX/'CARRIERS.npz');c['damage_reference_ids']=[167509,7786,120042]
control_provenance=c['control_identity']['whole_sampling_provenance'];bind(control_provenance['path'],control_provenance['sha256'])
versions={5558:21426,156151:20659,64111:21553,22130:21057,238627:21540};seeds=sorted(versions)
c.update(scene='scan65',kernel_count=279616,carrier_count=26713,knot_count=62561,next_version=21620,p=.001725801957946726,initial_assigned=126135,initial_unknown=153481,initial_next_version=21620,initial_stage=str(T),prior_config_sha256=sha(V/'CONFIG.json'),seed_ids=seeds,seed_versions={str(k):v for k,v in versions.items()},challenge_seed_ids=[238627],views=['0012','0036'],camera_shape=[777,581],camera_convention='COLMAP_W2C_NO_GL',unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),max_seconds=1800,absolute_deadline_jst='2026-11-02T15:38:00+09:00',decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(P/'source_snapshot'),input_files=inputs)
c.pop('seed_selection_per_model',None)
assert c['absolute_deadline_jst']==window['science_wrap_jst']
c['control_identity'].update(expected=dict(controls=71227,pieces=62356,parents=8874),rows=279616)
c['source_provenance']=dict(prior_config_sha256=prior_hash,exact_source_snapshot=snapshot,prior_regular_files=20,unchanged_prior_files=19,explicit_loader_interface_delta=deltas,numerical_core_byte_identical=True,unit011_loader_reused_with_explicit_M4_stage=True,v08_unit012_used=False,old_producers_executed=False,old_deadlines_imported=False)
c['settings'].update(seed_scope=seeds,whole_object_mapping_rows=279616,coordinate_scale_p=c['p'],background_reference=str(T),unknown_partition='original M4 carrier')
c['seed_policy']=dict(source='fixed saved M4 groups and versions',qualification='first four have two M3 contributions each >=12 kernels and mapped support >=2p; 238627 is single-substantial-source inherited-arc challenge only',failed_readiness='NOT_RUN without substitution',ledger='all saved groups with frozen-cohort exclusion and current version checks',protected_seed_members=True)
c['visual_policy'].update(views=c['views'],seed_ids=seeds,negative_pairs=[],negative_context_categories=[z['category'] for z in c['negative_contexts']],damage_reference_ids=c['damage_reference_ids'],full_projected_context=True,context='crop FULL original-kernel rasters retaining all depths and nonqueried competitors',query_context_separate=True,crop_padding_pixels=16,fixed_target_union_box_across_arms_and_stages=True,separate_start_and_new_members=True,no_GL_conversion=True,display_upsampling=False)
for key in ['discovery','fit','connectability','score','closure','score_ties','max_merges_per_seed','max_merges_total']:
 assert c['settings'][key]==prior['settings'][key],('NUMERICAL_POLICY_CHANGED',key)
for path,h in c['helper_files'].items():assert sha(path)==h,('HELPER_HASH',path)
for path,h in inputs.items():assert sha(path)==h,('INPUT_HASH',path)
tests=U/'tests';red=read(tests/'RED_EXIT.json');green=read(tests/'GREEN_EXIT.json');cli=read(tests/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==0 and cli['returncode']==0
assert "pc['stage']=='M5_STATE'" in (tests/'RED.log').read_text() and 'AssertionError' in (tests/'RED.log').read_text()
assert (tests/'GREEN.log').read_text().rstrip().endswith('OK') and 'Ran 20 tests' in (tests/'GREEN.log').read_text()
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: actual restricted loader rejected M4_STATE at the prior M5-only checkpoint assertion. Explicit configured M4 stage passes the same loader and guard(phase); original M5 and numerical fixtures remain passing.',red=dict(red,log=str(tests/'RED.log'),sha256=sha(tests/'RED.log'),baseline_loader=str(tests/'RED_frontier_loader.py'),baseline_sha256=sha(tests/'RED_frontier_loader.py')),green=dict(green,log=str(tests/'GREEN.log'),sha256=sha(tests/'GREEN.log')),cli=dict(cli,log=str(tests/'CLI.log'),sha256=sha(tests/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,render_run=False,fixture_scope='36-row actual-schema synthetic M4/M5 inputs, bounded geometric growth/rollback fixtures and Pillow context fixtures; native rendering stopped at boundary',test_count=20,numerical_core_byte_identical=True,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c)
py=window['python'];script=str(S/'scan65_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],python=py,command=[py,'-B',script,'--config',str(U/'CONFIG.json')],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'))
write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),inputs=len(inputs))))
