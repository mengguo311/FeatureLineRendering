"""Unit005 metadata freeze only; never runs full-asset computation."""
from pathlib import Path
import json,hashlib
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101');U=O/'units/unit_005';P=O/'units/unit_004'
PYTHON='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for block in iter(lambda:f.read(2**20),b''):h.update(block)
 return h.hexdigest()
def write(p,obj):
 with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def main():
 pc=P/'CONFIG.json';expected='32e458dc5e5640d0f3a9c91cfd1135fb1f653929a8d446cf608797981ef9dd18';assert sha(pc)==expected;c=json.loads(pc.read_text());frozen=json.loads((P/'PARENT_RUN_FROZEN.json').read_text());files=dict(c['input_files'])
 for src,h in frozen['source_files'].items():
  snapshot=frozen['immutable_source_snapshot'][src];assert sha(snapshot)==h;files[snapshot]=h
  # Only NEW files are introduced; inherited numerical implementation stays exact.
  assert sha(src)==h,'INHERITED_SOURCE_CHANGED '+src
 for p in [pc,P/'PARENT_RUN_FROZEN.json',U/'DECISION.json']:files[str(p)]=sha(p)
 stage=P/'scenes/ficus/stages/OVERLAP_FINAL';cp=json.loads((stage/'CHECKPOINT.json').read_text());assert cp['complete'] and cp['config_sha256']==expected
 assert cp['files']['MODELS.npz']=='099f9a5955c8be96a0d8ad0afe51f49d33dcae16688cede57b26e883316dc2ca';assert cp['files']['MEMBERSHIP.npz']=='638516c98f696a31e4fda76568cadf8d2a88c3fc30b2996526a31e5867d06b11'
 for name,h in cp['files'].items():assert sha(stage/name)==h;files[str(stage/name)]=h
 files[str(stage/'CHECKPOINT.json')]=sha(stage/'CHECKPOINT.json');c['reference_memberships']['unit004_OVERLAP_FINAL']=str(stage/'MEMBERSHIP.npz')
 case=P/'figures/CURVED_712/ROWS.npz';assert case.is_file();files[str(case)]=sha(case);c['prior_case_rows']['UNIT004_CURVED_712']=str(case)
 c.update(unit='unit_005',unit_root=str(U),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=json.loads((U/'DECISION.json').read_text()),input_files=files,predecessor_stage=str(stage),predecessor_config=str(pc),predecessor_config_sha256=expected,predecessor_model_count=519,predecessor_next_id=713,max_seconds=1800,absolute_deadline_jst='2026-11-01T19:38:00+09:00',latest_parent_launch_jst='2026-11-01T19:08:00+09:00',no_new_after_jst='2026-11-01T19:15:00+09:00',stage_budgets=dict(readiness=120,complete_graph_and_paths_by=420,science_by=1200,delivery_reserved=600),legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False)
 shared=('total_models','max_knots','assignment_radius_p','assignment_angle_deg','assignment_angle_weight','UNKNOWN_cost','margin','minimum_primary','minimum_bins','support_halfwidth_cap_p','gap_p','vertex_deg','turn_window_p','window_turn_deg','contact_p','huber_steps','huber_delta_p','smoothing','knot_move_cap_p','EPS','template_length_cap_p','fit_member_cap','model_penalty','energy_improvement_strictly_greater')
 c['settings']={k:c['settings'][k] for k in shared};c['settings'].update(initialization='exact unit004 OVERLAP_FINAL',voxel_p=1.,mode_unsigned_angle_deg=15.,graph_radius_p=1.5,graph_tangent_deg=30.,graph_connector_deg=35.,graph_directed_edge_cap=4000000,edge_cost='length*(1+(tangent_angle/30)^2+0.25*(connector_i^2+connector_j^2)/35^2)',seed_coverage_radius_p=8.,max_seeds=64,dijkstra_cost_cap_each_direction=64.,minimum_path_voxels=6,birth_attempt_cap=64,ordinary_update_cycles=0,supported_extension_steps=0,merge_attempts=0)
 c['implementation_details']=dict(modes='per1p voxel original-row order; fixed first-member unsigned tangent representative, nearest-angle<=15deg, canonical representative tie; centroid position, all directional modes retained; even state positive canonical sign',graph='complete radius1.5p between distinct spatial voxels; two oriented reverse arcs when tangent/connector guards pass; no nearest-k; complete graph or no birth promotion',seed_bank='eligible mode contains valid UNKNOWN and has in/out oriented continuation; all UNKNOWN-containing mode centroids within8p, deduplicated spatial voxel; exact lazy maximum marginal coverage, representative-row ties',paths='two positive-weight Dijkstra trees/seed with cost64; exact distance ties choose canonical predecessor, no cost perturbation; endpoints ranked distinct UNKNOWN voxels then geometric length then cost then state ID; canonical reverse sequence; repeated spatial voxels/less6/long128/duplicate reject without endpoint rescue; seed order preserved',assignment='original complete finite segment search with original cost/UNKNOWN; no old labels locked, no top-k competitors',fit='one unchanged IRLS on ALL template-compatible valid original rows cost<1 sorted by row; >8192 whole rejection; original geometry checked after fitting',transaction='add new q without pre-removing old models; full original rows reassign; support validation/death/split; exactly one supported birth descendant; E=sum true assigned cost+M strictly decreases; rollback and incomplete stages never promoted',control='exact saved NO_BIRTH state, no fresh assignment',outward='relative to most contributing existing pre-trial model, by retained kernel count then projected support then canonical ID; no existing contributor means missing outward reference, never fabricated success',renderer='read-only pinned AST colors/project_cov/render; full native original-kernel images first; complete candidate contexts, same rows, no auxiliary ink',resume='only cold hash-verified complete stages; interrupted graph/trial never promoted',source_legacy_producer_execution=False)
 for p,h in files.items():assert sha(p)==h,p
 for p,h in c['helper_files'].items():assert sha(p)==h,p
 receipts=json.loads((U/'TEST_EXECUTIONS.json').read_text());assert receipts['runs'][-1]['returncode']==0;green=Path(receipts['runs'][-1]['log']);assert green.read_text().rstrip().endswith('OK')
 assert 'ModuleNotFoundError' in (U/'TEST_RED_API.log').read_text();assert receipts['runs'][0]['returncode']==1
 cli=U/'CLI_HELP.log';assert cli.is_file() and '--config' in cli.read_text()
 write(U/'CONFIG.json',c)
 write(U/'TESTS_RECEIPT.json',dict(returncode=0,tdd_status='REAL_NEW_GRAPH_API_RED_GREEN; LEGACY_CHECKS_REGRESSIONS',command=[PYTHON,'-B',str(S/'run_graph_tests.py')],full_asset_science_run=False,render_run=False,fixture_max_rows=96,test_count=78,logs=[dict(path=r['log'],returncode=r['returncode'],note=r['note'],sha256=sha(r['log'])) for r in receipts['runs']],cli_help=dict(path=str(cli),sha256=sha(cli),returncode=0),scope='Explicit bounded suites; unit005 temporary outputs; real loader phase callback, real graph construction/Dijkstra/birth/full-row checkpoint tested. Rendering mocked only in runner fixtures. Full-asset numerical readiness remains parent compute.'))
 sources={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 write(U/'RUN_REQUEST.json',dict(script=str(S/'graph_birth_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=sources,helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json')))
 print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(U/'RUN_REQUEST.json'),config_sha256=sha(U/'CONFIG.json'),source_files=len(sources))))
if __name__=='__main__':main()
