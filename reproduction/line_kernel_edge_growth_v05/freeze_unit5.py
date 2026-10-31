"""Freeze ficus M3 request; parent exclusively owns snapshots and full compute."""
from common import *
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');RUNTIME=ROOT/'line_kernel_edge_growth_v05_20261031'
UNIT=RUNTIME/'units/unit_005';U2=UNIT.parent/'unit_002';U4=UNIT.parent/'unit_004';SOURCE=Path(__file__).resolve().parent
if __name__=='__main__':
    guard();assert not (UNIT/'source_snapshot').exists(),'Parent owns snapshot target'
    receipt=json.loads((UNIT/'TESTS_RECEIPT.json').read_text());assert receipt['returncode']==0
    verify(receipt['source_files']);assert sha(receipt['log'])==receipt['log_sha256'];assert sha(receipt['red_receipt'])==receipt['red_receipt_sha256']
    decision=json.loads((UNIT/'DECISION.json').read_text());step=decision['recommended_next_step'];window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text())
    c2=json.loads((U2/'CONFIG.json').read_text());c4=json.loads((U4/'CONFIG.json').read_text())
    assert sha(U2/'CONFIG.json')==step['input']['predecessor_config_sha256'];assert sha(U4/'CONFIG.json')==step['reference']['config_sha256'];assert c2['numeric']==c4['numeric']
    frozen=json.loads((U4/'PARENT_RUN_FROZEN.json').read_text());snapshots={snap:frozen['source_files'][original] for original,snap in frozen['immutable_source_snapshot'].items()}
    verify(snapshots);verify(frozen['source_files']);external=dict(frozen['helper_files']);assert len(external)==4;verify(external)
    sources={str(p):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};assert sources==receipt['source_files']
    seal=json.loads((U2/'SEAL.json').read_text())['files'];seal4=json.loads((U4/'SEAL.json').read_text())['files']
    baseline_groups=str(Path(c2['baseline_membership']).with_name('GROUPS.json'))
    original_paths=[c2[k] for k in ('gaussians','controls','representatives','baseline_membership','chains','cameras')]+[str(Path(c2['gaussians']).with_suffix('.ply')),baseline_groups]
    inputs={p:c2['input_files'][p] for p in original_paths}
    state=U2/step['input']['state'];cp=U2/step['input']['checkpoint'];native=U2/step['input']['native'];l1=U2/'scenes/ficus/stages/L1'
    assert Path(step['input']['unit_root'])==U2;assert json.loads(cp.read_text())['stage']==step['input']['checkpoint_stage']=='M2_STATE'
    for directory in (state.parent,native):
        sealed_cp=json.loads((directory/'CHECKPOINT.json').read_text())
        for name in ['CHECKPOINT.json']+list(sealed_cp['files']):inputs[str(directory/name)]=seal[str((directory/name).relative_to(U2))]
    for directory,names in ((native,('GROUPS.json','METRICS.json','LINEAGE.json')),(l1,('MEMBERSHIP.npz','GROUPS.json','LINEAGE.json'))):
        for name in names:inputs[str(directory/name)]=seal[str((directory/name).relative_to(U2))]
    assert inputs[str(state)]==step['input']['state_sha256'];assert inputs[str(cp)]==step['input']['checkpoint_sha256']
    external_metric=U4/'scenes/scan24/stages/M3_MERGE_ONLY/METRICS.json';inputs[str(external_metric)]=seal4[str(external_metric.relative_to(U4))]
    for p in (UNIT/'DECISION.json',U2/'CONFIG.json',U2/'DECISION.json',U2/'SEAL.json',U4/'CONFIG.json',U4/'PARENT_RUN_FROZEN.json',U4/'SEAL.json',RUNTIME/'orchestration/WINDOW.json'):inputs[str(p)]=sha(p)
    verify(inputs)
    keys=('scene','kernel_count','p','gaussians','controls','representatives','baseline_membership','cameras','renderer','libroot')
    config={key:c2[key] for key in keys};assert config['scene']=='ficus' and config['kernel_count']==285956
    config.update(unit=str(UNIT),runtime=str(RUNTIME),views=['test_r_1','test_r_79'],baseline_groups=baseline_groups,decision_path=str(UNIT/'DECISION.json'),decision_sha256=sha(UNIT/'DECISION.json'),previous_state=str(state),previous_checkpoint=str(cp),previous_checkpoint_stage='M2_STATE',previous_membership=str(native/'MEMBERSHIP.npz'),previous_carriers=str(native/'CARRIERS.npz'),previous_groups=str(native/'GROUPS.json'),previous_lineage=str(native/'LINEAGE.json'),predecessor_config=str(U2/'CONFIG.json'),predecessor_config_sha256=sha(U2/'CONFIG.json'),L1_membership=str(l1/'MEMBERSHIP.npz'),L1_groups=str(l1/'GROUPS.json'),tracked_M2_groups=[34448,36790],max_seconds=1800,science_deadline=window['science_wrap_jst'],unit_deadline=window['science_wrap_jst'],no_new_after_jst=window['no_new_after_jst'],stage_elapsed_limits=dict(input=120,M3=1380,final=1800),final_export_reserve_seconds=420,numeric=c4['numeric'],settings=step['settings'],fixed_decision=decision,visual_selection=step['visuals']['selection'],three_fragment_selection='One growth_gate group with>=3 substantial L1 fragments, maximal supported_length_p then minimal edge_id; no substitute if absent',input_files=inputs,source_files=sources,helper_files={**external,**snapshots},reference_results=[baseline_groups,str(l1/'GROUPS.json'),str(native/'GROUPS.json'),str(native/'METRICS.json'),str(external_metric)],reference_snapshot_manifest=str(U4/'PARENT_RUN_FROZEN.json'),reference_config_sha256=sha(U4/'CONFIG.json'),snapshot_creation_owner='PARENT_ONLY',cpu=2,blas=2,strict_serial=True,unit_output_cap_bytes=2*2**30,runtime_output_cap_bytes=8*2**30,min_root_free_bytes=2**30,min_hdd_free_bytes=10*2**30,fit_budget='One additional level3 topology pass, reset30000; no initialization/pooling',all_unknown_eligible=True,no_RGB_source_GS=True)
    js(UNIT/'CONFIG.json',config)
    request=dict(script=str(SOURCE/'continuation_scene.py'),config_path=str(UNIT/'CONFIG.json'),config_sha256=sha(UNIT/'CONFIG.json'),source_files=sources,helper_files=external,max_seconds=1800,tests_receipt=str(UNIT/'TESTS_RECEIPT.json'))
    js(UNIT/'RUN_REQUEST.json',request)
    js(UNIT/'BUILD_RECEIPT.json',dict(status='READY_FOR_PARENT_COMPUTE',utc=now(),decision_sha256=config['decision_sha256'],config_sha256=request['config_sha256'],run_request_sha256=sha(UNIT/'RUN_REQUEST.json'),source_files_count=len(sources),tests_returncode=0,science_launched=False,parent_owns_source_snapshot=True,old_sources_unchanged=True))
    for name in ('CONFIG.json','RUN_REQUEST.json','TESTS_RECEIPT.json','BUILD_RECEIPT.json'):(UNIT/name).chmod(0o444)
    print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(UNIT/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],source_files=len(sources),external_helpers=len(external),science_launched=False)))
