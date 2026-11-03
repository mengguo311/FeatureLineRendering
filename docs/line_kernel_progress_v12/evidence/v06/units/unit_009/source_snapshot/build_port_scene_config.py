"""Unit009 metadata preparation only: no scene loading, fitting or rendering."""
from pathlib import Path
import hashlib,json,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101')
U=O/'units/unit_009';P=O/'units/unit_008'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def prepare():
 assert not (U/'RUN_REQUEST.json').exists()
 assert sha(P/'CONFIG.json')=='1a1702f58d22b2146bf7958c39ed2fc156a2953e7d6c19b43e238c94cc5dc852'
 base=json.loads((P/'CONFIG.json').read_text());f=json.loads((P/'PARENT_RUN_FROZEN.json').read_text());decision=json.loads((U/'DECISION.json').read_text())
 for src,snapshot in f['immutable_source_snapshot'].items():
  assert sha(snapshot)==f['source_files'][src];assert sha(S/Path(src).name)==f['source_files'][src],'OLD_SOURCE_CHANGED'
 c={k:base[k] for k in ['runtime','resource_limits','helper_files','renderer','libroot','scene','kernel_count','p','gaussians','controls','representatives','cameras','views','state','predecessor_checkpoint','predecessor_config','predecessor_config_sha256','membership','carriers','ordered_candidates','candidate_status','ambiguity','candidate_metrics']}
 c.update(unit=str(U),output=str(U),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_decision=decision['recommended_next_step'],changed_variable=decision['changed_variable'],falsification=decision['falsification'],max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00',no_new_after_jst='2026-11-01T09:15:00+09:00',parent_launch_latest_jst='2026-11-01T09:08:00+09:00')
 c.update(stage_budgets=dict(readiness=300,solver_total=600,mappings_by=1200,delivery_reserved=600),solver=dict(per_context_seconds=120,total_seconds=600,max_cut_rounds=32,mip_rel_gap=0),decision_carrier_cap=128,expected_candidate_records=89486,expected_successful_endpoints=756,expected_eligible_endpoints=163,expected_endpoint_components=148,expected_masked_endpoints=593,expected_max_component=4,priority_carrier_ids=[64355,65064,112780,116525],seed_groups=[64355,65064,112780,116525],fixed_carrier_ids=[65959,188634],reference_leaf_sets=[[64355,65064],[112780,116525]],negative_pairs=[[11,80709],[16931,18768],[112,205435],[33117,201172]],reference_membership=c['membership'])
 c['external_memberships']={a:str(P/'scenes/ficus/stages'/arm/'MEMBERSHIP.npz') for a,arm in [('unit008_greedy_reference','greedy'),('unit008_joint_reference','joint')]};c['external_memberships']['v05_M5_reference']=base['reference_membership']
 c['scientific_settings']=dict(representation='ordered immutable finite leaves',objective='maximize sum((2-residual_max-tangent_max/30)*x)',port_capacity=1,cycles=False,ambiguity='exclude all saved full joint ambiguity pairs equally; preserve alternatives',fit_calls=0,new_candidates=False,overlap_pooling=False,thresholds=dict(EPS=1e-8,residual_max_p=1,residual_q95_p=.5,tangent_degrees=30,endpoint_gap_p=1.5,connector_degrees=35,vertex_degrees=30,window_p=8,window_turn_degrees=60,contact_p=.5,unsupported_gap_p=1.5),activation=dict(seedlets=3,kernels=6,support_p=4),oracle='byte-identical unit002 port_paths.py',cost_perturbation=False)
 c['implementation_details']=dict(scene_adapter='unit008 validated parameterized loader',scope='complete eligible endpoint components; full nonrecursive incident-record evidence',references='M4 and both unit008 overlap arms and v05M5 are diagnostic only; no historical same-method replay',fallback='unprocessed components retain M4; only checked feasible paths exported',core_unchanged=True)
 inputs=dict(base['input_files'])
 def add(p,expected=None):
  p=Path(p);h=sha(p)
  if expected is not None:assert h==expected,str(p)
  inputs[str(p)]=h
 add(P/'CONFIG.json');add(P/'PARENT_RUN_FROZEN.json')
 for src,snap in f['immutable_source_snapshot'].items():add(snap,f['source_files'][src])
 old=O/'units/unit_002';add(old/'CONFIG.json');add(old/'PARENT_RUN_FROZEN.json')
 for name in ['port_paths.py','geometry_base.py','delivery.py','paired_delivery.py']:
  add(old/'source_snapshot'/name);assert sha(old/'source_snapshot'/name)==sha(P/'source_snapshot'/name)
 add(P/'tests/FICUS_REAL_COMPONENT.npz')
 for path in c['external_memberships'].values():
  add(path)
  cp=Path(path).parent/'CHECKPOINT.json';d=json.loads(cp.read_text());assert d['complete'];add(cp)
  for n,h in d['files'].items():add(cp.parent/n,h)
 for p,h in c['helper_files'].items():assert sha(p)==h
 c['input_files']=inputs;c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 (U/'CONFIG.draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 (U/'INPUT_HASH_RECEIPT.json').write_text(json.dumps(dict(inherited_input_bindings=len(base['input_files']),total_input_bindings=len(inputs),prior_source_files_verified_unchanged=len(f['source_files']),helper_files=c['helper_files'],original_assets_not_loaded=True,full_numerical_run=False),indent=2)+'\n')
 print(json.dumps(dict(config=str(U/'CONFIG.draft.json'),sources=len(c['source_files']),inputs=len(inputs),created=datetime.datetime.now().astimezone().isoformat())))
if __name__=='__main__':prepare()
