"""Freeze unit_003 request/config; parent exclusively creates source_snapshot."""
from common import *
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
RUNTIME=ROOT/'line_kernel_edge_growth_v05_20261031';UNIT=RUNTIME/'units/unit_003';U2=UNIT.parent/'unit_002'
SOURCE=Path(__file__).resolve().parent
if __name__=='__main__':
    guard();assert not (UNIT/'source_snapshot').exists(),'Parent owns snapshot target'
    receipt=json.loads((UNIT/'TESTS_RECEIPT.json').read_text());assert receipt['returncode']==0
    verify(receipt['source_files']);assert sha(receipt['log'])==receipt['log_sha256'];assert sha(receipt['red_receipt'])==receipt['red_receipt_sha256']
    decision=json.loads((UNIT/'DECISION.json').read_text());step=decision['recommended_next_step'];window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text())
    cfg2=json.loads((U2/'CONFIG.json').read_text());assert sha(U2/'CONFIG.json')=='2b9042ad166cf5e8ba203b9306ac7d1c717be537fa25ff0681728b33c86eac54'
    frozen=json.loads((U2/'PARENT_RUN_FROZEN.json').read_text());snapshots={snap:frozen['source_files'][original] for original,snap in frozen['immutable_source_snapshot'].items()}
    verify(snapshots);verify(frozen['source_files'])
    source_files={str(p):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};assert source_files==receipt['source_files']
    # Only the four allowed external sources enter RUN_REQUEST.helper_files.
    external=dict(frozen['helper_files']);assert len(external)==4;verify(external)
    config_helpers={**external,**snapshots}
    sealed=json.loads((RUNTIME/'orchestration/V03_SEALED_REFERENCE.json').read_text());v03=Path(sealed['root'])
    lock=json.loads((RUNTIME/'orchestration/INPUT_LOCK.json').read_text())['files'];scene='scan65';original=ROOT/'c2l50_multiview05_v01/arms/C/scenes'/scene/'full'
    inputs={str(original/n):lock[str(original/n)] for n in ('gaussians.npz','gaussians.ply','SHARED_CONTROL_AND_SAMPLING.npz')}
    for n in ('scan65/REPRESENTATIVES.npz','scan65/baseline/MEMBERSHIP.npz','scan65/baseline/CHAINS.npz','scan65/baseline/GROUPS.json','CAMERAS.json'):inputs[str(v03/n)]=sealed['files'][n]
    references=[]
    for unit,names in [(UNIT.parent/'unit_001',('STATUS.json','scenes/scan24/stages/M2_MERGE_ONLY/METRICS.json')),(U2,('STATUS.json','scenes/ficus/COMPARISONS.json'))]:
        seal=json.loads((unit/'SEAL.json').read_text())['files']
        for n in names:inputs[str(unit/n)]=seal[n];references.append(str(unit/n))
    for p in (UNIT/'DECISION.json',U2/'CONFIG.json',U2/'PARENT_RUN_FROZEN.json',U2/'SEAL.json',RUNTIME/'orchestration/WINDOW.json'):inputs[str(p)]=sha(p)
    verify(inputs)
    config=dict(unit=str(UNIT),runtime=str(RUNTIME),scene=scene,kernel_count=279616,views=['0012','0036'],p=json.loads((v03/'scan65/baseline/GROUPS.json').read_text())['p'],gaussians=str(original/'gaussians.npz'),controls=str(original/'SHARED_CONTROL_AND_SAMPLING.npz'),representatives=str(v03/'scan65/REPRESENTATIVES.npz'),baseline_membership=str(v03/'scan65/baseline/MEMBERSHIP.npz'),chains=str(v03/'scan65/baseline/CHAINS.npz'),cameras=str(v03/'CAMERAS.json'),renderer=cfg2['renderer'],libroot=cfg2['libroot'],decision_path=str(UNIT/'DECISION.json'),decision_sha256=sha(UNIT/'DECISION.json'),max_seconds=1800,science_deadline=window['science_wrap_jst'],unit_deadline=window['science_wrap_jst'],no_new_after_jst=window['no_new_after_jst'],stage_elapsed_limits=dict(L0=360,L1=1020,M2=1380,final=1800),final_export_reserve_seconds=420,numeric=cfg2['numeric'],settings=step['settings'],fixed_decision=decision,visual_selection=step['visuals']['selection'],input_files=inputs,source_files=source_files,helper_files=config_helpers,reference_results=references,reference_snapshot_manifest=str(U2/'PARENT_RUN_FROZEN.json'),reference_config_sha256=sha(U2/'CONFIG.json'),old_scene_replay=False,snapshot_creation_owner='PARENT_ONLY',cpu=2,blas=2,strict_serial=True,unit_output_cap_bytes=2*2**30,runtime_output_cap_bytes=8*2**30,min_root_free_bytes=2**30,min_hdd_free_bytes=10*2**30,fit_budget='L0 unchanged non-counting initialization; two L1 passes share30000; M2 resets30000',all_unknown_eligible=True,no_RGB_source_GS=True)
    assert config['numeric']==cfg2['numeric'];js(UNIT/'CONFIG.json',config)
    request=dict(script=str(SOURCE/'scene_runner.py'),config_path=str(UNIT/'CONFIG.json'),config_sha256=sha(UNIT/'CONFIG.json'),source_files=source_files,helper_files=external,max_seconds=1800,tests_receipt=str(UNIT/'TESTS_RECEIPT.json'))
    js(UNIT/'RUN_REQUEST.json',request)
    js(UNIT/'BUILD_RECEIPT.json',dict(status='READY_FOR_PARENT_COMPUTE',utc=now(),decision_sha256=config['decision_sha256'],config_sha256=request['config_sha256'],run_request_sha256=sha(UNIT/'RUN_REQUEST.json'),source_files_count=len(source_files),tests_returncode=0,science_launched=False,parent_owns_source_snapshot=True,unit_002_snapshot_and_old_sources_unchanged=True))
    for name in ('CONFIG.json','RUN_REQUEST.json','TESTS_RECEIPT.json','BUILD_RECEIPT.json'):(UNIT/name).chmod(0o444)
    print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(UNIT/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],source_files=len(source_files),external_helpers=len(external),science_launched=False)))
