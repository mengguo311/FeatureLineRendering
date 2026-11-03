"""Metadata-only configuration builder. Never loads numerical scene arrays."""
from pathlib import Path
import json,hashlib,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101')
U=O/'units/unit_010';P=O/'units/unit_009'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def prepare():
 assert not (U/'RUN_REQUEST.json').exists()
 assert sha(P/'CONFIG.json')=='a1fc0bee29f9440196368c3ded858b655cb86bf0dd794ae74c3665bd4093a6dd'
 c=json.loads((P/'CONFIG.json').read_text());f=json.loads((P/'PARENT_RUN_FROZEN.json').read_text());decision=json.loads((U/'DECISION.json').read_text())
 for src,snap in f['immutable_source_snapshot'].items():assert sha(snap)==f['source_files'][src] and sha(S/Path(src).name)==f['source_files'][src],'OLD_SOURCE_CHANGED'
 c.update(unit=str(U),output=str(U),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_decision=decision['recommended_next_step'],changed_variable=decision['changed_variable'],falsification=decision['falsification'],max_seconds=1200,absolute_deadline_jst='2026-11-01T09:38:00+09:00',no_new_after_jst='2026-11-01T09:15:00+09:00',parent_launch_latest_jst='2026-11-01T09:18:00+09:00',fit_source=str(S/'pinned_v05_fit_core.py'),path_cap=128)
 c['stage_budgets']=dict(readiness=300,models_by=400,solver_total=200,mappings_by=600,delivery_reserved=600)
 c['solver']=dict(per_context_seconds=120,total_seconds=200,mip_rel_gap=0)
 c['reference_leaf_sets']=[[64355,65064],[112780,116525],[21870,22319]]
 c['external_memberships']={a:str(P/'scenes/ficus/stages'/b/'MEMBERSHIP.npz') for a,b in [('unit009_greedy_reference','greedy'),('unit009_joint_reference','joint')]}
 c['scientific_settings']=dict(arms=['concat_greedy','concat_joint','common_greedy','common_joint'],path_library='all port-compatible simple paths, canonical reversal, cap128 entire component; total benefit positive',benefit='sum(2-saved_residual_max-saved_tangent_max/30)',fit='once per path: pinned TLS/ordered polyline; canonical ID rows/reps; oriented q template',fit_parameters=dict(huber_iterations=3,delta_p=.5,occupied_bin_p=1,max_kernels=8192,max_knots=128,knot_spacing_p=4),thresholds=dict(EPS=1e-8,residual_max_p=1,residual_q95_p=.5,tangent_degrees=30,endpoint_gap_p=1.5,connector_degrees=35,vertex_degrees=30,window_p=8,window_turn_degrees=60,contact_p=.5,unsupported_gap_p=1.5),common_domain='all original centers extended_s finite; oriented old-q samples monotone; leaf midpoint order',branch='original and fitted knots union',activation=dict(seedlets=3,kernels=6,support_p=4),new_candidates=False,mask_unchanged=True,cost_perturbation=False,overlap_pooling=False)
 c['implementation_details']=dict(selection='whole-path hypothesis greedy/MILP in both representations; not unit009 link-greedy equivalence',fallback='all four arms retain M4 per incomplete component',resume='only complete hash-bound stage/component checkpoints',source_original_leaves_unchanged=True,original_gaussians_rendered=True,auxiliary_curve_never_rendered=True)
 inputs=dict(c['input_files'])
 def add(p,expected=None):
  p=Path(p);h=sha(p)
  if expected is not None:assert h==expected,str(p)
  inputs[str(p)]=h
 add(P/'CONFIG.json');add(P/'PARENT_RUN_FROZEN.json')
 for src,snap in f['immutable_source_snapshot'].items():add(snap,f['source_files'][src])
 for path in c['external_memberships'].values():
  cp=Path(path).parent/'CHECKPOINT.json';z=json.loads(cp.read_text());assert z['complete'];add(cp)
  for n,h in z['files'].items():add(cp.parent/n,h)
 assert sha(c['fit_source'])=='c1565d2c33ee1f75e1a58469f14d8e153a138eb5f3c0dc73fbbcc5a9ab20e512'
 for p,h in c['helper_files'].items():assert sha(p)==h
 c['input_files']=inputs;c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 (U/'CONFIG.draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 (U/'INPUT_HASH_RECEIPT.json').write_text(json.dumps(dict(prior_source_files_verified_unchanged=len(f['source_files']),input_bindings=len(inputs),helpers=c['helper_files'],original_assets_not_loaded=True,created=datetime.datetime.now().astimezone().isoformat()),indent=2)+'\n')
 print('CONFIG_DRAFT_READY',len(c['source_files']),len(inputs))
if __name__=='__main__':prepare()
