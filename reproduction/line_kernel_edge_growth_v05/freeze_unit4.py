"""Immutable unit004 request; parent alone snapshots and launches full science."""
from common import *
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');RUNTIME=ROOT/'line_kernel_edge_growth_v05_20261031'
UNIT=RUNTIME/'units/unit_004';U1=UNIT.parent/'unit_001';U3=UNIT.parent/'unit_003';SOURCE=Path(__file__).resolve().parent
if __name__=='__main__':
    guard();assert not (UNIT/'source_snapshot').exists(),'Parent owns snapshot target'
    receipt=json.loads((UNIT/'TESTS_RECEIPT.json').read_text());assert receipt['returncode']==0
    verify(receipt['source_files']);assert sha(receipt['log'])==receipt['log_sha256'];assert sha(receipt['red_receipt'])==receipt['red_receipt_sha256']
    decision=json.loads((UNIT/'DECISION.json').read_text());step=decision['recommended_next_step'];window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text())
    cfg1=json.loads((U1/'CONFIG.json').read_text());cfg3=json.loads((U3/'CONFIG.json').read_text())
    assert sha(U1/'CONFIG.json')=='eca69514ff92ffe40d208427f9a551906122b272df3815e0015b9f8bb1daf361'
    assert sha(U3/'CONFIG.json')==step['settings']['reference_config_sha256'];assert cfg1['numeric']==cfg3['numeric']
    frozen=json.loads((U3/'PARENT_RUN_FROZEN.json').read_text());snapshots={snap:frozen['source_files'][original] for original,snap in frozen['immutable_source_snapshot'].items()}
    verify(snapshots);verify(frozen['source_files']);external=dict(frozen['helper_files']);assert len(external)==4;verify(external)
    sources={str(p):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};assert sources==receipt['source_files']
    seal=json.loads((U1/'SEAL.json').read_text())['files'];inputs=dict(cfg1['input_files'])
    oldstate=UNIT.parent/'unit_001/scenes/scan24/stages/S2_MERGE';oldnative=UNIT.parent/'unit_001/scenes/scan24/stages/M2_MERGE_ONLY'
    for directory in (oldstate,oldnative):
        cp=json.loads((directory/'CHECKPOINT.json').read_text())
        for name in ['CHECKPOINT.json']+list(cp['files']):inputs[str(directory/name)]=seal[str((directory/name).relative_to(U1))]
    for name in ('GROUPS.json','METRICS.json','LINEAGE.json'):inputs[str(oldnative/name)]=seal[str((oldnative/name).relative_to(U1))]
    assert inputs[str(oldstate/'STATE.pkl')]==step['input']['state_sha256'];assert inputs[str(oldstate/'CHECKPOINT.json')]==step['input']['checkpoint_sha256']
    for p in (UNIT/'DECISION.json',U1/'CONFIG.json',U1/'SEAL.json',U3/'CONFIG.json',U3/'PARENT_RUN_FROZEN.json',RUNTIME/'orchestration/WINDOW.json'):inputs[str(p)]=sha(p)
    verify(inputs)
    keys=('scene','kernel_count','p','gaussians','controls','representatives','baseline_membership','baseline_groups','cameras','renderer','libroot')
    config={key:cfg1[key] for key in keys}
    config.update(unit=str(UNIT),runtime=str(RUNTIME),views=['0012','0036'],decision_path=str(UNIT/'DECISION.json'),decision_sha256=sha(UNIT/'DECISION.json'),previous_state=str(oldstate/'STATE.pkl'),previous_checkpoint=str(oldstate/'CHECKPOINT.json'),previous_membership=str(oldnative/'MEMBERSHIP.npz'),previous_carriers=str(oldnative/'CARRIERS.npz'),previous_groups=str(oldnative/'GROUPS.json'),previous_lineage=str(oldnative/'LINEAGE.json'),predecessor_config=str(U1/'CONFIG.json'),predecessor_config_sha256=sha(U1/'CONFIG.json'),L1_membership=cfg1['previous_membership'],L1_groups=cfg1['previous_groups'],tracked_M2_groups=[103748,202626],max_seconds=1800,science_deadline=window['science_wrap_jst'],unit_deadline=window['science_wrap_jst'],no_new_after_jst=window['no_new_after_jst'],stage_elapsed_limits=dict(input=120,M3=1380,final=1800),final_export_reserve_seconds=420,numeric=cfg3['numeric'],settings=step['settings'],fixed_decision=decision,visual_selection=step['visuals']['selection'],input_files=inputs,source_files=sources,helper_files={**external,**snapshots},reference_results=[cfg1['baseline_groups'],cfg1['previous_groups'],str(oldnative/'GROUPS.json'),str(oldnative/'METRICS.json')],reference_snapshot_manifest=str(U3/'PARENT_RUN_FROZEN.json'),reference_config_sha256=sha(U3/'CONFIG.json'),snapshot_creation_owner='PARENT_ONLY',cpu=2,blas=2,strict_serial=True,unit_output_cap_bytes=2*2**30,runtime_output_cap_bytes=8*2**30,min_root_free_bytes=2**30,min_hdd_free_bytes=10*2**30,fit_budget='one additional level3 topology pass, reset30000; no initialization or pooling',all_unknown_eligible=True,no_RGB_source_GS=True)
    js(UNIT/'CONFIG.json',config)
    request=dict(script=str(SOURCE/'continuation_runner.py'),config_path=str(UNIT/'CONFIG.json'),config_sha256=sha(UNIT/'CONFIG.json'),source_files=sources,helper_files=external,max_seconds=1800,tests_receipt=str(UNIT/'TESTS_RECEIPT.json'))
    js(UNIT/'RUN_REQUEST.json',request)
    js(UNIT/'BUILD_RECEIPT.json',dict(status='READY_FOR_PARENT_COMPUTE',utc=now(),decision_sha256=config['decision_sha256'],config_sha256=request['config_sha256'],run_request_sha256=sha(UNIT/'RUN_REQUEST.json'),source_files_count=len(sources),tests_returncode=0,science_launched=False,parent_owns_source_snapshot=True,old_sources_unchanged=True))
    for name in ('CONFIG.json','RUN_REQUEST.json','TESTS_RECEIPT.json','BUILD_RECEIPT.json'):(UNIT/name).chmod(0o444)
    print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(UNIT/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],source_files=len(sources),external_helpers=len(external),science_launched=False)))
