"""Metadata-only frozen scan24 request; never executes source-asset science."""
from pathlib import Path
import json,hashlib,copy,datetime
S=Path(__file__).resolve().parent
R=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
OLD=R/'line_kernel_best_fragment_growth_v09_20261102/units/unit_001'
O=R/'line_kernel_best_fragment_growth_v09_20261102/continuation_001';U=O/'units/unit_001'
M5=R/'line_kernel_edge_growth_v05_20261031/units/unit_018';T=M5/'scenes/scan24/stages/M5_MERGE_ONLY'
M4=R/'line_kernel_edge_growth_v05_20261031/units/unit_015/scenes/scan24/stages/M4_MERGE_ONLY'
V6=R/'line_kernel_global_association_v06_20261101/units/unit_003'
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,obj):
 with Path(path).open('x') as f:json.dump(obj,f,indent=2,ensure_ascii=False,allow_nan=False)
original_hash='bb5feab4f25a24c1314469975ffc6e3b30f98725ddcbb919d1e209ac5d44b42c'
assert sha(OLD/'CONFIG.json')==original_hash
assert sha(M5/'CONFIG.json')=='6bf43845007491d21538a0b4032797e7d98e9f548b8ce7b66bba626b9dc509f2'
c=copy.deepcopy(read(OLD/'CONFIG.json'));frozen=read(OLD/'PARENT_RUN_FROZEN.json');assert frozen['config_sha256']==original_hash
inputs={};snapshot={}
def bind(path,expected=None):
 path=Path(path).resolve();h=sha(path)
 if expected is not None:assert h==expected,('BINDING',str(path))
 inputs[str(path)]=h;return str(path)
for original,path in frozen['immutable_source_snapshot'].items():
 h=frozen['source_files'][original];bind(path,h);snapshot[str(path)]=h
 # All existing modules are unchanged; only the scan24 adapter/delivery entry is new.
 assert sha(S/Path(original).name)==h,('UNCHANGED_CORE',original)
for name in ['CONFIG.json','PARENT_RUN_FROZEN.json','DECISION.json']:bind(OLD/name)
v5=read(M5/'CONFIG.json');v6=read(V6/'CONFIG.json');window=read(O/'orchestration/WINDOW.json')
for name in ['CONFIG.json','DECISION.json']:bind(M5/name)
bind(V6/'CONFIG.json','739636ada8e953befbb72aa4dc82c95a9536a0e849216fa3b31eafd2d2ec5e2f')
for key in ['gaussians','controls','representatives','cameras','renderer','libroot']:c[key]=v5[key]
for key in ['gaussians','controls','representatives','cameras']:bind(c[key])
assert inputs[c['gaussians']]=='af26ea9aa0cd5015d99e5104113b286a1d88c71c35672564ca0d523bfe190e71'
assert inputs[c['controls']]=='0012cd6de8cd87af708f7b43e47daee653a331b538c622095cf7b71293596eb3'
assert inputs[c['cameras']]=='9020d0599f28aaa500b3c24bb28a8c6cc0c6896eda6753b407a9924e970670c4'
for key,name in [('membership','MEMBERSHIP.npz'),('carriers','CARRIERS.npz'),('groups','GROUPS.json'),('lineage','LINEAGE.json')]:c[key]=bind(T/name)
c['state']=bind(M5/'scenes/scan24/states/M5/STATE.pkl','ae1b60384ad17c1730d07a13b9e69f71a089f8fa4386c8146a1e57c2326754cd')
c['predecessor_checkpoint']=bind(M5/'scenes/scan24/states/M5/CHECKPOINT.json')
c['predecessor_config']=str(M5/'CONFIG.json')
def checkpoint_inputs(path):
 p=Path(path);cp=read(p);assert cp['complete']
 bind(p)
 for name,h in cp['files'].items():
  child=p.parent/name;bind(child,h)
  if child.name=='CHECKPOINT.json':checkpoint_inputs(child)
checkpoint_inputs(c['predecessor_checkpoint'])
c['m4_membership']=bind(M4/'MEMBERSHIP.npz');c['negative_carriers']=bind(M4/'CARRIERS.npz');c['negative_pairs']=v6['negative_pairs']
for name in ['GROUPS.json','LINEAGE.json']:bind(M4/name)
c['external_memberships']={'M4':c['m4_membership'],'v06_greedy':bind(V6/'scenes/scan24/stages/greedy/MEMBERSHIP.npz'),'v06_joint':bind(V6/'scenes/scan24/stages/joint/MEMBERSHIP.npz')}
control_provenance=c['control_identity']['whole_sampling_provenance'];bind(control_provenance['path'],control_provenance['sha256'])
versions={53254:33868,132977:32496,200509:32356,201906:33649,210790:33039,202023:32446};seeds=sorted(versions)
c.update(scene='scan24',kernel_count=458490,carrier_count=34633,knot_count=86916,next_version=33877,p=.0014320037356621643,initial_assigned=259758,initial_unknown=198732,initial_next_version=33877,initial_stage=str(T),prior_config_sha256=sha(M5/'CONFIG.json'),seed_ids=seeds,seed_versions={str(k):v for k,v in versions.items()},seed_selection_per_model=3,views=['0012','0036'],camera_shape=[777,581],camera_convention='COLMAP_W2C_NO_GL',unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),max_seconds=1800,absolute_deadline_jst='2026-11-02T15:38:00+09:00',decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),source_snapshot_root=str(OLD/'source_snapshot'),input_files=inputs)
assert c['absolute_deadline_jst']==window['science_wrap_jst']
c['control_identity'].update(expected=dict(controls=122765,pieces=111471,parents=11309),rows=458490)
c['source_provenance']=dict(original_v09_config_sha256=original_hash,exact_source_snapshot=snapshot,all_original_modules_byte_identical=True,unit011_loader_reused_via_original_snapshot=True,v08_unit012_used=False,old_producers_executed=False,old_deadlines_imported=False)
c['settings'].update(seed_scope=seeds,whole_object_mapping_rows=458490,coordinate_scale_p=c['p'],background_reference=str(T))
c['seed_policy']=dict(source='saved M5 GROUPS/LINEAGE endpoint surviving ID+version',model_counts={'line':3,'polyline':3},rank=['supported_length_p descending','ID ascending'],qualification='valid and two M4 contributions each >=12 kernels and mapped support >=2p',failed_readiness='NOT_RUN without substitution',ledger='all groups, eligibility/exclusion, rank and unselected scope')
c['visual_policy'].update(views=c['views'],seed_ids=seeds,negative_pairs=c['negative_pairs'],full_projected_context=True,context='crop FULL original-kernel rasters retaining all depths and nonqueried competitors',query_context_separate=True,crop_padding_pixels=16,fixed_target_union_box_across_arms_and_stages=True,separate_start_and_new_members=True,no_GL_conversion=True,display_upsampling=False)
c['external_evidence_only']=dict(ficus_79841=str(OLD),rerun=False,inherited_differences_not_new_gains=True)
for key in ['discovery','fit','connectability','score','closure','score_ties','max_merges_per_seed','max_merges_total']:
 assert c['settings'][key]==read(OLD/'CONFIG.json')['settings'][key],('NUMERICAL_POLICY_CHANGED',key)
for path,h in c['helper_files'].items():assert sha(path)==h,('HELPER_HASH',path)
for path,h in inputs.items():assert sha(path)==h,('INPUT_HASH',path)
tests=U/'tests';red=read(tests/'RED_EXIT.json');green=read(tests/'GREEN_EXIT.json');cli=read(tests/'CLI_EXIT.json')
assert red['returncode']==1 and green['returncode']==0 and cli['returncode']==0
assert "KeyError: 'config_sha256'" in (tests/'RED.log').read_text()
assert (tests/'GREEN.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: actual restricted M5 load succeeded but old composite-state adapter rejected the M5 checkpoint schema; new direct-M5 adapter passes without replacing the loader. All original numerical regression tests also pass.',red=dict(red,log=str(tests/'RED.log'),sha256=sha(tests/'RED.log'),baseline_adapter=str(tests/'RED_scan24_loader.py'),baseline_sha256=sha(tests/'RED_scan24_loader.py')),green=dict(green,log=str(tests/'GREEN.log'),sha256=sha(tests/'GREEN.log')),cli=dict(cli,log=str(tests/'CLI.log'),sha256=sha(tests/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,render_run=False,fixture_scope='36 original-schema synthetic rows and bounded geometric fixtures; Pillow context fixture only, no native renderer invoked',test_count=16,original_core_byte_identical=True,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
write(U/'CONFIG.json',c)
py=window['python'];script=str(S/'scan24_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],python=py,command=[py,'-B',script,'--config',str(U/'CONFIG.json')],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'))
write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),inputs=len(inputs))))
