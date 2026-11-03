"""Unit004 immutable build metadata; hashing only, never scene computation."""
from pathlib import Path
import json,hashlib
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101');U=O/'units/unit_004';P=O/'units/unit_003'
PY='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for block in iter(lambda:f.read(2**20),b''):h.update(block)
 return h.hexdigest()
def write(p,obj):
 with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def main():
 pc=P/'CONFIG.json';expected='8231ab7ff396c30c7e359fd139c53b2cf65f92d6092d97dd81d1ce6eee59e256';assert sha(pc)==expected;c=json.loads(pc.read_text());frozen=json.loads((P/'PARENT_RUN_FROZEN.json').read_text());files=dict(c['input_files'])
 for src,h in frozen['source_files'].items():
  snapshot=frozen['immutable_source_snapshot'][src];assert sha(snapshot)==h;files[snapshot]=h
  assert sha(src)==h,'OLD_SOURCE_CHANGED '+src
 for p in [pc,P/'PARENT_RUN_FROZEN.json',U/'DECISION.json']:files[str(p)]=sha(p)
 stage=P/'scenes/ficus/stages/NO_MERGE';cp=json.loads((stage/'CHECKPOINT.json').read_text());assert cp['complete'] and cp['config_sha256']==expected
 assert cp['files']['MODELS.npz']=='e990caaa4a47272a8285da8453400b231ffe575df53493557040fb9bf95e4ef3';assert cp['files']['MEMBERSHIP.npz']=='1d544bc84345ae8e8f268c2009d277c7d9ecf5019409bb775d39fd9b1842ea20'
 for name,h in cp['files'].items():assert sha(stage/name)==h;files[str(stage/name)]=h
 files[str(stage/'CHECKPOINT.json')]=sha(stage/'CHECKPOINT.json')
 c['reference_memberships']['unit003_NO_MERGE']=str(stage/'MEMBERSHIP.npz')
 c.update(unit='unit_004',unit_root=str(U),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=json.loads((U/'DECISION.json').read_text()),input_files=files,predecessor_stage=str(stage),predecessor_config=str(pc),predecessor_config_sha256=expected,predecessor_model_count=520,predecessor_next_id=712,max_seconds=1800,absolute_deadline_jst='2026-11-01T19:38:00+09:00',no_new_after_jst='2026-11-01T19:15:00+09:00',stage_budgets=dict(readiness=120,complete_initial_relation_by=360,science_by=1200,delivery_reserved=600),legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False)
 for k in ['endpoint_gap_p','endpoint_tangent_deg','connector_deg']:c['settings'].pop(k,None)
 c['settings'].update(initialization='exact cold unit003 NO_MERGE; no assignment/support pass',relation_cost_strict_upper=1.0,shared_kernel_min=12,shared_support_union_min_p=2.0,common_domain_overlap_min_p=2.0,overlap_sample_spacing_p=1.0,overlap_distance_max_p=1.0,overlap_directed_tangent_max_deg=30.0,merge_attempt_cap=64,ordinary_update_cycles=0,births=0,supported_extension_steps=0)
 c['implementation_details']=dict(compatibility='complete model-major CSR from all valid original rows and finite segments; exact assign minimum-cost segment with lowest segment ID ties, cost<1; no top-k truncation',proposal='all distinct current model pairs; common rows>=12 and covariance interval unions>=2p in both finite domains; score min(unions), then canonical IDs; all pair counts/reasons saved',cache='read-only relation cache keyed by model ID and q SHA; after each accepted state complete current relation/candidate table persisted before next trial',orientation='sum corresponding shared-kernel segment tangent dot products; reverse B iff negative; zero keeps direction',coordinate='delta=median(sA-sB_oriented); A domain[0,LA],B[delta,delta+LB]; lowest segment at boundaries; no finite extrapolation',template='>=2p overlap; uniform <=1p checks distance1p and directed30deg; left/right owners by extreme domain, canonical smaller ID ties; containment keeps owner geometry; partial overlap linear blend on union knot coordinates; resample;128p/129knot cap',fit='one existing three-step IRLS on sorted union of current primary rows<=8192, no pre-fit turn veto; q auxiliary only',selection='dynamic transactional replacement with all-row/all-model assign and support validation; exactly one valid replacement descendant, E=sum actual final model cost+M decreases>EPS; no MILP or legacy atoms',control='exact saved predecessor numeric state, no extra assignment or support pass',guard_implementation='unchanged free_core assignment/geometry/support and merge_core energy; complete relation construction must finish before proposals can promote',rejection='original state/next_id unchanged; persist fitted q, parameterization, raw/validated lossless deltas and checkpoint dependencies; incomplete trial never promoted',outward='largest immediate input selected by its full PRE-TRIAL support proxy, not retained subset; report retained and input support, finite domain projection, union/longest/gaps separately',delivery='native full original-kernel views first; same-row comparisons, all geometric model competitors and complete primary contexts; fixed55/441 and historical negatives; no rendered auxiliary curve',no_resume='only cold hash-verified complete input/accepted stages; no interrupted-stage promotion',source_legacy_producer_execution=False,renderer_extraction='pinned AST colors/project_cov/render only')
 for p,h in files.items():assert sha(p)==h,p
 for p,h in c['helper_files'].items():assert sha(p)==h,p
 logs=[('TEST_RED_API.log',1,'New overlap interface test first: module absent, no science run'),('TEST_ALL_1.log',0,'58 bounded tests: complete relation/templates/free trial and exact-control runner'),('TEST_ALL_2.log',0,'61 bounded tests including real63-row positive runner, accepted checkpoint and energy rollback'),('TEST_FINAL_GREEN.log',0,'Final61-test regression after exact2p bounds and largest-input diagnostic clarification'),('CLI_HELP.log',0,'Plain --config CLI parse')]
 for n,rc,note in logs:assert (U/n).is_file(),n
 assert 'Ran 61 tests' in (U/'TEST_FINAL_GREEN.log').read_text() and (U/'TEST_FINAL_GREEN.log').read_text().rstrip().endswith('OK')
 assert 'ModuleNotFoundError' in (U/'TEST_RED_API.log').read_text()
 write(U/'CONFIG.json',c)
 write(U/'TESTS_RECEIPT.json',dict(returncode=0,test_count=61,tdd_status='REAL_NEW_OVERLAP_API_RED_GREEN; EXISTING_CHECKS_ARE_REGRESSIONS',command=PY+' -B '+str(S/'run_overlap_tests.py'),full_asset_science_run=False,render_run=False,fixture_max_rows=96,logs=[dict(path=str(U/n),sha256=sha(U/n),returncode=rc,note=note) for n,rc,note in logs],scope='Explicit suites only; all temporary outputs unit004. Real loader guard(phase), checkpoint restore and positive63-row overlap runner/energy/accepted state. Rendering/diagnostic delivery mocked only in fixtures; actual full-scene readiness deferred to parent.'))
 sources={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 write(U/'RUN_REQUEST.json',dict(script=str(S/'overlap_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=sources,helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json')))
 print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(U/'RUN_REQUEST.json'),config_sha256=sha(U/'CONFIG.json'),source_files=len(sources))))
if __name__=='__main__':main()
