"""Build-only manifest writer; does not load original numerical assets."""
from pathlib import Path
import hashlib,json,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102');U=O/'units/unit_001'
R=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
V5=R/'line_kernel_edge_growth_v05_20261031/units/unit_019';V6=R/'line_kernel_global_association_v06_20261101/units/unit_009'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 with Path(p).open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
old=read(V6/'CONFIG.json');lock=read(O/'orchestration/INPUT_LOCK.json');decision=read(U/'DECISION.json');window=read(O/'orchestration/WINDOW.json')
assert sha(V5/'CONFIG.json')=='9bff7e59af8c3cee6a40790a5ec1c6aea4039bfd9463815e34440b33ad01ff81'
frozen=read(V6/'PARENT_RUN_FROZEN.json');helpers=dict(old['helper_files']);origin={}
for name in ['runtime_io.py','geometry_base.py','port_paths.py','scene_adapter.py','scene_render.py']:
 pair=next((k,v) for k,v in frozen['immutable_source_snapshot'].items() if Path(v).name==name)
 assert sha(pair[1])==frozen['source_files'][pair[0]]
 helpers[pair[1]]=frozen['source_files'][pair[0]];origin[name]=dict(path=pair[1],sha256=helpers[pair[1]])
helpers[str(V6/'PARENT_RUN_FROZEN.json')]=sha(V6/'PARENT_RUN_FROZEN.json')
c={k:old[k] for k in ['gaussians','controls','representatives','cameras','renderer','libroot','negative_pairs']}
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),scene='ficus',kernel_count=285956,p=.003530473547030632,carrier_count=28635,knot_count=65335,next_version=20576,seeds=[[64355,20526],[112780,20225],[48496,20415],[137016,20281]],views=['test_r_1','test_r_79'],state=str(V5/'scenes/ficus/states/M5/STATE.pkl'),predecessor_checkpoint=str(V5/'scenes/ficus/states/M5/CHECKPOINT.json'),predecessor_config=str(V5/'CONFIG.json'),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),max_seconds=1800,absolute_deadline_jst=window['science_wrap_jst'],legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False,protected_leaf_tracer=True,max_attempts=64,max_accepts_per_seed=8,helper_files=helpers,source_provenance=origin,scientific_contract=decision,expected_background_assigned=121965)
for key,name in [('membership','MEMBERSHIP.npz'),('carriers','CARRIERS.npz'),('groups','GROUPS.json'),('lineage','LINEAGE.json')]:c[key]=str(V5/'scenes/ficus/stages/M5_MERGE_ONLY'/name)
m4=V5.parent/'unit_016/scenes/ficus/stages/M4_MERGE_ONLY';c['m4_membership']=str(m4/'MEMBERSHIP.npz');c['negative_carriers']=str(m4/'CARRIERS.npz')
c['external_memberships']={name:str(V6.parent/unit/'scenes/ficus/stages'/stage/'MEMBERSHIP.npz') for name,unit,stage in [('v06_overlap','unit_008','joint'),('v06_common','unit_011','common_joint')]};c['external_memberships']['M4']=c['m4_membership']
c['settings']=dict(endpoint_radius_p=1.5,endpoint_tangent_degrees=30,connector_degrees=35,outward_support_p=2,outward_kernels=6,ambiguity_gap_p=.15,history_secant_p=1,history_required_p=2,history_prediction_angle_degrees=15,history_curvature_delta='2*sin(7.5 degrees)',residual_max_p=1,residual_q95_p=.5,member_tangent_degrees=30,member_cap=8192,vertex_turn_degrees=30,turn_window_p=8,window_turn_degrees=60,nonadjacent_contact_p=.5,unsupported_gap_p=1.5,parallel=dict(overlap_p=2,angle_degrees=15,offset_p=.5),branch=dict(angle_degrees=20,seedlets=3,radial_extent_p=2,radius_p=4),activation=dict(seedlets=3,kernels=6,support_p=4),EPS=1e-8,complete_radius_queries=True,model_fitting=False,zero_support_connectors=True,seed_order='ascending ID; port0 then port1; round-robin',scientific_stop='max64 attempts per arm/max8 accepts per seed/no valid frontier/deadline')
c['budgets']=dict(readiness_seconds=120,selection_finish_elapsed_seconds=1200,delivery_reserved_seconds=600,unit_bytes=2*2**30,runtime_bytes=20*2**30,root_min_free=2**30,hdd_min_free=10*2**30,cpu=2,blas=2)
inputs={}
for k in ['gaussians','controls','representatives','cameras']:
 p=c[k];expected=old['input_files'][p]
 if p in lock['files']:assert lock['files'][p]==expected
 inputs[p]=expected
for k in ['state','predecessor_checkpoint','predecessor_config','membership','carriers','groups','lineage','m4_membership','negative_carriers']:
 inputs[c[k]]=sha(c[k])
assert inputs[c['state']]=='5128247be907311d68963405696c9a445b09c5c8aa6b20fa95dea6c686c9dbfb'
for p in c['external_memberships'].values():inputs[p]=sha(p)
for p in [O/'orchestration/INPUT_LOCK.json',O/'orchestration/WINDOW.json',V5/'DECISION.json',V5/'PARENT_RUN_FROZEN.json']:
 if p.exists():inputs[str(p)]=sha(p)
pc=read(c['predecessor_checkpoint'])
for name,h in pc['files'].items():inputs[str(Path(c['predecessor_checkpoint']).parent/name)]=h
c['input_files']=inputs
sources={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};c['source_files']=sources
receipt=U/'TESTS_RECEIPT.json';assert read(receipt)['returncode']==0
write(U/'CONFIG.json',c)
request=dict(script=str(S/'frontier_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=sources,helper_files=helpers,max_seconds=1800,tests_receipt=str(receipt),python=window['python'],command=[window['python'],'-B',str(S/'frontier_runner.py'),'--config',str(U/'CONFIG.json')])
write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='FROZEN_REQUEST',config_sha256=request['config_sha256'],source_files=len(sources),helper_files=len(helpers),request=str(U/'RUN_REQUEST.json'))))
