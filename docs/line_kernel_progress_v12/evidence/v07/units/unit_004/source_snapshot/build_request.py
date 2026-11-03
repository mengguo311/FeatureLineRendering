"""Build-time metadata only; never loads full numerical assets."""
from pathlib import Path
import json,hashlib
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101');U=O/'units/unit_001';BASE=O.parent
V6=BASE/'line_kernel_global_association_v06_20261101';V5=BASE/'line_kernel_edge_growth_v05_20261031'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def write(p,d):
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def main():
 decision=U/'DECISION.json';step=json.loads(decision.read_text());oldpath=V6/'units/unit_011/CONFIG.json';old=json.loads(oldpath.read_text());lockpath=O/'orchestration/INPUT_LOCK.json';lock=json.loads(lockpath.read_text());files={};refs={
 'v05_M4':V5/'units/unit_016/scenes/ficus/stages/M4_MERGE_ONLY/MEMBERSHIP.npz',
 'v05_M5':V5/'units/unit_019/scenes/ficus/stages/M5_MERGE_ONLY/MEMBERSHIP.npz',
 'v06_overlap_joint':V6/'units/unit_008/scenes/ficus/stages/joint/MEMBERSHIP.npz',
 'v06_common_joint':V6/'units/unit_011/scenes/ficus/stages/common_joint/MEMBERSHIP.npz'}
 for k in ['gaussians','controls','cameras']:
  path=old[k];expected=old['input_files'][path];assert sha(path)==expected
  if path in lock['files']:assert lock['files'][path]==expected
  files[path]=expected
 for name,p in refs.items():
  cp=json.loads((p.parent/'CHECKPOINT.json').read_text());recorded=cp.get('files',{}).get('MEMBERSHIP.npz')
  if isinstance(recorded,dict):recorded=recorded.get('sha256')
  if recorded is not None:assert sha(p)==recorded
  files[str(p)]=sha(p);files[str(p.parent/'CHECKPOINT.json')]=sha(p.parent/'CHECKPOINT.json')
 for p in [oldpath,lockpath,decision,O/'orchestration/WINDOW.json',V6/'units/unit_011/PARENT_RUN_FROZEN.json']:files[str(p)]=sha(p)
 c=dict(unit='unit_001',unit_root=str(U),runtime_root=str(O),scene='ficus',kernel_count=285956,p=.003530473547030632,decision_path=str(decision),decision_sha256=sha(decision),legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,gaussians=old['gaussians'],controls=old['controls'],cameras=old['cameras'],reference_memberships={k:str(v) for k,v in refs.items()},input_files=files,helper_files=old['helper_files'],renderer=old['renderer'],libroot=old['libroot'],views=['test_r_1','test_r_79'],max_seconds=1800,absolute_deadline_jst='2026-11-01T19:38:00+09:00',no_new_after_jst='2026-11-01T19:15:00+09:00',stage_budgets=dict(readiness=120,initialization_by=360,science_by=1200,delivery_reserved=600),fixed_contexts=[[112780,116525],[64355,65064],[11,80709],[16931,18768],[112,205435],[33117,201172]],scientific_contract=step,settings=dict(voxel_p=1,seed_radius_p=2,trace_neighbors=32,trace_radius_p=2,trace_axial_p=.5,trace_sigma_p=1,trace_step_p=1,trace_steps_per_side=64,max_knots=129,initial_models=512,birth_per_cycle=64,total_models=704,cycles=3,assignment_radius_p=1,assignment_angle_deg=30,assignment_angle_weight=.25,UNKNOWN_cost=1,margin=.05,minimum_primary=12,minimum_bins=6,support_halfwidth_cap_p=.5,gap_p=1.5,vertex_deg=30,turn_window_p=8,window_turn_deg=60,contact_p=.5,huber_steps=3,huber_delta_p=.5,smoothing=.1,knot_move_cap_p=.5,end_extension_steps=2,EPS=1e-8),implementation_details=dict(unknown_participates_in_margin=True,seed_tie='minimum original row, canonical eigenvector sign',radius_query='segment midpoint query radius half segment length plus1p, exact finite segment filtering; all candidate models retained',fit_interpolation='fixed closest segment barycentric coordinates during each three-IRLS update',support_validation='simultaneous winner-support pruning, no reassignment to runners-up until next scheduled cycle; split children get new IDs',model_cap='active models including support splits; overflow preserves raw checkpoint and stops promotion',curve_selection_proxy='total turn greater than30deg, a ranking label not visual success',trace_length_cap='trim trace at128p only to respect129knots spacing<=1p; never extrapolate',no_resume='completed immutable stages never overwritten; run in fresh parent-owned unit',source_legacy_producer_execution=False,renderer_extraction='AST selects colors/project_cov/render only; no common or SH imports',all_array_fields_fingerprinted_including_colors=True))
 for p,h in c['helper_files'].items():assert sha(p)==h
 write(U/'CONFIG.json',c)
 # These exit statuses were actually observed by the executing build session.
 receipts=[('TEST_RED.log',1,'new API absent before implementation'),('TEST_GREEN_1.log',0,'12 small tests'),('TEST_GREEN_2.log',0,'15 tests'),('TEST_RED_SPLIT.log',1,'real child-coordinate regression failure'),('TEST_GREEN_3.log',0,'16 tests after coordinate fix'),('TEST_RED_DIAGNOSTICS.log',1,'real diagnostic EPS import failure'),('TEST_FINAL.log',0,'18 tests including actual four-stage30-row runner, rendering mocked explicitly'),('TEST_FINAL_VERIFIED.log',0,'18 tests after final delivery-error exit handling'),('CLI_HELP.log',0,'plain --config CLI')]
 for name,rc,note in receipts:assert (U/name).is_file()
 assert 'Ran 18 tests' in (U/'TEST_FINAL.log').read_text() and (U/'TEST_FINAL.log').read_text().rstrip().endswith('OK')
 write(U/'TESTS_RECEIPT.json',dict(returncode=0,tdd_status='TEST_FIRST_NEW_API_THEN_REAL_RED_GREEN_SPLIT_COORDINATES',full_asset_science_run=False,render_run=False,logs=[dict(path=str(U/name),sha256=sha(U/name),returncode=rc,note=note) for name,rc,note in receipts],command='approved python -B '+str(S/'test_free.py'),scope='isolated <=96 synthetic rows, actual loader reads temporary NPZ and guard(phase); source and old outputs untouched'))
 source={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 write(U/'RUN_REQUEST.json',dict(script=str(S/'runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=source,helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json')))
 print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',config_sha256=sha(U/'CONFIG.json'),request=str(U/'RUN_REQUEST.json'),source_count=len(source))))
if __name__=='__main__':main()
