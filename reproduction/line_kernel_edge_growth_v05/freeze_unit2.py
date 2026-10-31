"""Freeze config/request; parent exclusively owns source_snapshot creation."""
from common import *
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');RUNTIME=ROOT/'line_kernel_edge_growth_v05_20261031';UNIT=RUNTIME/'units/unit_002';U1=RUNTIME/'units/unit_001';SOURCE=Path(__file__).resolve().parent
if __name__=='__main__':
    guard();receipt=json.loads((UNIT/'TESTS_RECEIPT.json').read_text());assert receipt['returncode']==0;verify(receipt['source_files']);assert sha(receipt['log'])==receipt['log_sha256'];assert sha(receipt['red_receipt'])==receipt['red_receipt_sha256']
    d=json.loads((UNIT/'DECISION.json').read_text());window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text());oldcfg=json.loads((U1/'CONFIG.json').read_text());assert sha(U1/'CONFIG.json')=='eca69514ff92ffe40d208427f9a551906122b272df3815e0015b9f8bb1daf361'
    snap=json.loads((U1/'SOURCE_SNAPSHOT.json').read_text());verify(snap['snapshot_files']);verify(snap['source_files'])
    v03seal=json.loads((RUNTIME/'orchestration/V03_SEALED_REFERENCE.json').read_text());v03=Path(v03seal['root']);lock=json.loads((RUNTIME/'orchestration/INPUT_LOCK.json').read_text())['files'];source=ROOT/'c2l50_multiview05_v01/arms/C/scenes/ficus/full'
    inputs={str(source/n):lock[str(source/n)] for n in ('gaussians.npz','gaussians.ply','SHARED_CONTROL_AND_SAMPLING.npz')}
    for n in ('ficus/REPRESENTATIVES.npz','ficus/baseline/MEMBERSHIP.npz','ficus/baseline/CHAINS.npz','ficus/baseline/GROUPS.json','CAMERAS.json'):
        inputs[str(v03/n)]=v03seal['files'][n]
    control=dict(gaussians=oldcfg['gaussians'],L0_membership=oldcfg['baseline_membership'],L1_membership=oldcfg['previous_membership'],M2_membership=str(U1/'scenes/scan24/stages/M2_MERGE_ONLY/MEMBERSHIP.npz'),M2_carriers=str(U1/'scenes/scan24/stages/M2_MERGE_ONLY/CARRIERS.npz'),group_ids=[103748,202626])
    seal=json.loads((U1/'SEAL.json').read_text())['files']
    for k,v in control.items():
        if k=='group_ids':continue
        path=Path(v);inputs[v]=seal[str(path.relative_to(U1))] if path.is_relative_to(U1) else oldcfg['input_files'][v]
    for path in (UNIT/'DECISION.json',U1/'CONFIG.json',U1/'SEAL.json',U1/'SOURCE_SNAPSHOT.json',RUNTIME/'orchestration/WINDOW.json'):inputs[str(path)]=sha(path)
    verify(inputs)
    helper_files=dict(oldcfg['helper_files']);helper_files.update(snap['snapshot_files']);verify(helper_files)
    source_files={str(p):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};assert source_files==receipt['source_files']
    numeric=oldcfg['numeric'];deadline=min(datetime.datetime.fromisoformat(window['science_wrap_jst']),datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=65)).isoformat()
    config=dict(unit=str(UNIT),runtime=str(RUNTIME),scene='ficus',kernel_count=285956,views=['test_r_1','test_r_79'],p=json.loads((v03/'ficus/baseline/GROUPS.json').read_text())['p'],gaussians=str(source/'gaussians.npz'),controls=str(source/'SHARED_CONTROL_AND_SAMPLING.npz'),representatives=str(v03/'ficus/REPRESENTATIVES.npz'),baseline_membership=str(v03/'ficus/baseline/MEMBERSHIP.npz'),chains=str(v03/'ficus/baseline/CHAINS.npz'),cameras=str(v03/'CAMERAS.json'),renderer=oldcfg['renderer'],libroot=oldcfg['libroot'],control=control,decision_path=str(UNIT/'DECISION.json'),decision_sha256=sha(UNIT/'DECISION.json'),max_seconds=1800,science_deadline=window['science_wrap_jst'],unit_deadline=deadline,stage_elapsed_limits=dict(control=120,L0=360,L1=1020,M2=1380,final=1800),final_export_reserve_seconds=420,stage_budget_note='Cumulative elapsed caps; M2 fitting/commits end by1380 leaving420s. No additional pool after M2.',numeric=numeric,settings=d['recommended_next_step']['settings'],fixed_decision=d,visual_selection=d['recommended_next_step']['visuals']['selection'],input_files=inputs,source_files=source_files,helper_files=helper_files,cpu=2,blas=2,strict_serial=True,unit_output_cap_bytes=2*2**30,runtime_output_cap_bytes=8*2**30,min_root_free_bytes=2**30,min_hdd_free_bytes=10*2**30,reference_snapshot_manifest=str(U1/'SOURCE_SNAPSHOT.json'),reference_config_sha256=sha(U1/'CONFIG.json'),snapshot_creation_owner='PARENT_ONLY',fit_budget='L0 uncapped non-counting initialization; L1 two passes share30000; M2 resets30000',all_unknown_eligible=True,no_RGB_source_GS=True)
    js(UNIT/'CONFIG.json',config)
    req=dict(script=str(SOURCE/'transfer.py'),config_path=str(UNIT/'CONFIG.json'),config_sha256=sha(UNIT/'CONFIG.json'),source_files=source_files,helper_files=helper_files,max_seconds=1800,tests_receipt=str(UNIT/'TESTS_RECEIPT.json'))
    # Intentionally do not create, chmod, rewrite or reserve unit_002/source_snapshot.
    assert not (UNIT/'source_snapshot').exists(),'Parent snapshot target must remain unoccupied during BUILD'
    js(UNIT/'RUN_REQUEST.json',req);js(UNIT/'BUILD_RECEIPT.json',dict(status='READY_FOR_PARENT_COMPUTE',utc=now(),decision_sha256=config['decision_sha256'],config_sha256=req['config_sha256'],run_request_sha256=sha(UNIT/'RUN_REQUEST.json'),science_launched=False,tests_returncode=0,source_files_count=len(source_files),parent_owns_source_snapshot=True,unit_001_snapshot_unchanged=True))
    for name in ('CONFIG.json','RUN_REQUEST.json','TESTS_RECEIPT.json','BUILD_RECEIPT.json'):(UNIT/name).chmod(0o444)
    print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(UNIT/'RUN_REQUEST.json'),config_sha256=req['config_sha256'],source_files=len(source_files),parent_snapshot_target_created=False,science_launched=False)))
