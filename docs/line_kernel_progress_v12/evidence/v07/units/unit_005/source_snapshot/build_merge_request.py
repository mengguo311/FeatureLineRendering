"""Unit003 build manifest only. Hashes files; never runs scene numerics."""
from pathlib import Path
import json,hashlib
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101');U=O/'units/unit_003';P=O/'units/unit_002'
PY='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for block in iter(lambda:f.read(2**20),b''):h.update(block)
 return h.hexdigest()
def write(p,obj):
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def main():
 pc=P/'CONFIG.json';expected='9df62cacc28d37f6cd1ac99c7f75af9908ea7f7e39fb71234b451fecb0b21180';assert sha(pc)==expected;c=json.loads(pc.read_text());frozen=json.loads((P/'PARENT_RUN_FROZEN.json').read_text());files=dict(c['input_files'])
 for src,h in frozen['source_files'].items():
  snapshot=frozen['immutable_source_snapshot'][src];assert sha(snapshot)==h;files[snapshot]=h
  assert sha(src)==h,'PREVIOUS_SOURCE_CHANGED '+src
 for p in [pc,P/'PARENT_RUN_FROZEN.json',U/'DECISION.json']:files[str(p)]=sha(p)
 stage=P/'scenes/ficus/stages/FREE_ADAPTIVE_3';cp=json.loads((stage/'CHECKPOINT.json').read_text());assert cp['complete'] and cp['config_sha256']==expected
 assert cp['files']['MODELS.npz']=='e990caaa4a47272a8285da8453400b231ffe575df53493557040fb9bf95e4ef3';assert cp['files']['MEMBERSHIP.npz']=='a55f34bb2e74bcff84d6d3c2c408bae0902970e6025953fb2ed83e87b12ebb3e'
 for name,h in cp['files'].items():assert sha(stage/name)==h;files[str(stage/name)]=h
 files[str(stage/'CHECKPOINT.json')]=sha(stage/'CHECKPOINT.json')
 for label,st in [('unit002_STATIC','FREE_STATIC'),('unit002_ADAPTIVE','FREE_ADAPTIVE_3')]:
  p=P/'scenes/ficus/stages'/st/'MEMBERSHIP.npz';cp1=p.parent/'CHECKPOINT.json';d=json.loads(cp1.read_text());assert d['complete'] and d['config_sha256']==expected and sha(p)==d['files']['MEMBERSHIP.npz'];c['reference_memberships'][label]=str(p);files[str(p)]=sha(p);files[str(cp1)]=sha(cp1)
 for name in ['CURVED_7','CURVED_11','CURVED_15','DAMAGED_13054','DAMAGED_37737','DAMAGED_9969']:
  p=P/'figures'/name/'ROWS.npz';c['prior_case_rows']['UNIT002_'+name]=str(p);files[str(p)]=sha(p)
 c.update(unit='unit_003',unit_root=str(U),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=json.loads((U/'DECISION.json').read_text()),input_files=files,predecessor_stage=str(stage),predecessor_config=str(pc),predecessor_config_sha256=expected,predecessor_model_count=520,predecessor_next_id=712,max_seconds=1800,stage_budgets=dict(readiness=120,control_by=240,science_by=1200,delivery_reserved=600))
 shared=['total_models','max_knots','assignment_radius_p','assignment_angle_deg','assignment_angle_weight','UNKNOWN_cost','margin','minimum_primary','minimum_bins','support_halfwidth_cap_p','gap_p','vertex_deg','turn_window_p','window_turn_deg','contact_p','huber_steps','huber_delta_p','smoothing','knot_move_cap_p','EPS']
 c['settings']={k:c['settings'][k] for k in shared};c['settings'].update(initialization='cold saved unit002 FREE_ADAPTIVE_3',ordinary_update_cycles=0,births=0,supported_extension_steps=0,merge_attempt_cap=64,endpoint_gap_p=1.5,endpoint_tangent_deg=30,connector_deg=35,template_length_cap_p=128,fit_member_cap=8192,model_penalty=1.0,energy_improvement_strictly_greater=1e-8)
 c['implementation_details']=dict(assignment='unchanged free_core.assign: all finite segments within1p, no topk; support validation after every full competition',old_groups='no preservation, no legacy membership/validity mask',proposal_enumeration='all4 ports for every distinct current model pair; all numeric screen records saved; sort gap,a,b,pa,pb',attempt_key='(a,sha(q_a),port_a,b,sha(q_b),port_b); max64 including failures; refresh after acceptance, no retry of unchanged geometry versions',fit='canonical orientation a-end to b-start; remove consecutive<=EPS duplicates, resample, one original3-step IRLS on sorted union of current primary rows; no pre-fit concatenation-turn veto',energy='recompute minimum eligible segment cost within FINAL assigned model; UNKNOWN1 plus1 per support-valid model; no stale alternative costs',support='unchanged validate_support; proposed replacement must retain exactly one valid descendant; other labels/models may split/die',rejection='transactional; no input mutation or next_id consumption; tentative IDs scoped to trial until accepted',progress='save trial START/fitted q/raw lossless delta/validated delta before subsequent work; complete accepted checkpoints before diagnostics',delta='copy referenced input checkpoint membership fields and replace every changed_rows entry; all auxiliary fields included',context='full2p original neighborhood, full touched reference identities, complete primary supports of every current model finite-compatible with target rows; not physical-completeness claim',outward='current group support proxy outside projection range of largest contributing immediate input finite q; also report source M4/parent contributions; no physical observed-gap claim',no_resume='new immutable output; reads only hash-verified complete predecessor/accepted stages; interrupted trials not promoted',source_legacy_producer_execution=False,renderer_extraction='pinned AST colors/project_cov/render only',all_array_fields_fingerprinted_including_colors=True)
 for p,h in files.items():assert sha(p)==h,p
 for p,h in c['helper_files'].items():assert sha(p)==h
 logs=[('TEST_RED_API.log',1,'New merge behavior test-first: missing new module; not science failure'),('TEST_CORE_1.log',1,'Test record-container schema assertion corrected (8 columns versus row count); not algorithm RED claim'),('TEST_ALL_1.log',0,'46 bounded regression tests'),('TEST_RED_PROGRESS.log',1,'Missing progress callback meant later support failure could not expose trial raw state'),('TEST_ALL_2.log',0,'47 tests after progress persistence interface'),('TEST_ALL_3.log',0,'48 tests including actual63-row merge and energy rejection'),('TEST_FINAL_GREEN.log',0,'Final48-test suite; actual loader/recovery/accepted checkpoint and later failure preservation'),('CLI_HELP.log',0,'Actual plain --config CLI')]
 for name,rc,note in logs:assert (U/name).is_file()
 assert 'Ran 48 tests' in (U/'TEST_FINAL_GREEN.log').read_text() and (U/'TEST_FINAL_GREEN.log').read_text().rstrip().endswith('OK')
 write(U/'CONFIG.json',c)
 write(U/'TESTS_RECEIPT.json',dict(returncode=0,test_count=48,tdd_status='REAL_NEW_API_RED_GREEN_AND_PROGRESS_CONTRACT_RED_GREEN',command=PY+' -B '+str(S/'run_merge_tests.py'),full_asset_science_run=False,render_run=False,fixture_max_rows=96,logs=[dict(path=str(U/n),sha256=sha(U/n),returncode=rc,note=note) for n,rc,note in logs],scope='Explicit small suites only, all temporary files unit003. Real original-kernel loader and checkpoint restore; actual63-row free-merge runner. Only rendering/diagnostic delivery mocked in runner fixtures; injected later failure kept rc1 in fixture.'))
 sources={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 write(U/'RUN_REQUEST.json',dict(script=str(S/'merge_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=sources,helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json')))
 print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(U/'RUN_REQUEST.json'),config_sha256=sha(U/'CONFIG.json'),source_files=len(sources))))
if __name__=='__main__':main()
