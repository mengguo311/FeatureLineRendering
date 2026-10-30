"""Freeze only after successful bounded BUILD tests. Does not launch compute."""
from common import *
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
RUNTIME=ROOT/'line_kernel_edge_growth_v05_20261031'
UNIT=RUNTIME/'units/unit_001'
SOURCE=Path(__file__).resolve().parent
if __name__=='__main__':
    guard();decision=UNIT/'DECISION.json';d=json.loads(decision.read_text());window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text());receipt=json.loads((UNIT/'TESTS_RECEIPT.json').read_text());assert receipt['returncode']==0
    verify(receipt['source_files']);assert sha(receipt['log'])==receipt['log_sha256'];assert sha(receipt['red_receipt'])==receipt['red_receipt_sha256']
    old=ROOT/'line_kernel_edge_growth_v04/units/unit_001';l1=old/'scan24/L1';l0=old/'scan24/L0';v03=ROOT/'line_kernel_edge_grouping_v03/units/unit_001/scan24';native=ROOT/'c2l50_multiview05_v01/arms/C/scenes/scan24/full'
    inputs=json.loads((l1/'INPUT_HASHES_BEFORE.json').read_text());verify(inputs)
    for level,names in [(l1,['STATE.pkl','MEMBERSHIP.npz','CARRIERS.npz','GROUPS.json','LINEAGE.json']),(l0,['GROUPS.json'])]:
        sealed=json.loads((level/'CHECKPOINT.json').read_text());assert sealed['complete']
        for n in names:inputs[str(level/n)]=sealed['files'][n]
        inputs[str(level/'CHECKPOINT.json')]=sha(level/'CHECKPOINT.json')
    assert inputs[str(l1/'STATE.pkl')]=='8f3d3cf00cb84aacba494bb824ff58b5afe7ceec845ebf7e23c8699ef77e8c94'
    inputs[str(old/'CAMERAS.json')]=json.loads((old/'CONFIG.json').read_text())['camera_sha256']
    inputs[str(RUNTIME/'orchestration/WINDOW.json')]=sha(RUNTIME/'orchestration/WINDOW.json');inputs[str(decision)]=sha(decision);verify(inputs)
    helpers0=json.loads((old/'CONFIG.json').read_text())['helper_hashes'];ref=Path('/home/u00134/3dgs_line/line_kernel_edge_growth_v04/reproduction/line_kernel_edge_growth_v04/core.py');helpers0[str(ref)]=sha(UNIT/'tests/red_source/core.py');verify(helpers0)
    # Files are frozen before any complete-asset output or parent numerical launch.
    source_files={str(f):sha(f) for f in sorted(SOURCE.rglob('*')) if f.is_file() and '__pycache__' not in f.parts};assert source_files==receipt['source_files']
    deadline=min(datetime.datetime.fromisoformat(window['science_wrap_jst']),datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=65)).isoformat()
    config=dict(unit=str(UNIT),runtime=str(RUNTIME),decision_path=str(decision),decision_sha256=sha(decision),unit_deadline=deadline,science_deadline=window['science_wrap_jst'],max_seconds=1800,stage_elapsed_limits={'input':120,'topology':1500,'export':1740,'diagnostics':1800},export_reserve_seconds=300,stage_budget_note='Elapsed caps from process start; topology includes S1 global competition and S2 commits. No acceptance from incomplete competition.',scene='scan24',kernel_count=458490,p=json.loads((l1/'GROUPS.json').read_text())['p'],gaussians=str(native/'gaussians.npz'),controls=str(native/'SHARED_CONTROL_AND_SAMPLING.npz'),representatives=str(v03/'REPRESENTATIVES.npz'),baseline_membership=str(v03/'baseline/MEMBERSHIP.npz'),baseline_groups=str(l0/'GROUPS.json'),previous_state=str(l1/'STATE.pkl'),previous_membership=str(l1/'MEMBERSHIP.npz'),previous_carriers=str(l1/'CARRIERS.npz'),previous_groups=str(l1/'GROUPS.json'),previous_lineage=str(l1/'LINEAGE.json'),cameras=str(old/'CAMERAS.json'),renderer='/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01/renderer.py',libroot=str(ROOT/'c2l50_8build_joint_gs_v01'),input_files=inputs,helper_files=helpers0,source_files=source_files,settings=d['recommended_next_step']['settings'],numeric=json.loads((old/'CONFIG.json').read_text())['numeric'],fixed_decision=d,threads=2,unit_output_cap_bytes=2*2**30,runtime_output_cap_bytes=8*2**30,min_root_free_bytes=2**30,min_hdd_free_bytes=10*2**30,scientific_stages=['scan24 L1 -> M2_MERGE_ONLY'],not_run=['post_merge_pooling','further_rounds','ficus','scan65'],reference_equivalence='Final v04 batch implementation; small real/fixture equivalence verified. Historical scalar full ranking NOT_VERIFIED.')
    js(UNIT/'CONFIG.json',config);snap=UNIT/'source_snapshot';snap.mkdir()
    for name,h in source_files.items():
        f=Path(name);dest=snap/f.relative_to(SOURCE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest);assert sha(dest)==h;dest.chmod(0o444)
    js(UNIT/'SOURCE_SNAPSHOT.json',dict(source_files=source_files,snapshot_files={str(snap/Path(f).relative_to(SOURCE)):h for f,h in source_files.items()}))
    request=dict(script=str(SOURCE/'runner.py'),config_path=str(UNIT/'CONFIG.json'),config_sha256=sha(UNIT/'CONFIG.json'),source_files=source_files,helper_files=helpers0,max_seconds=1800,tests_receipt=str(UNIT/'TESTS_RECEIPT.json'))
    js(UNIT/'RUN_REQUEST.json',request);js(UNIT/'BUILD_RECEIPT.json',dict(status='READY_FOR_PARENT_COMPUTE',utc=now(),decision_sha256=sha(decision),config_sha256=request['config_sha256'],run_request_sha256=sha(UNIT/'RUN_REQUEST.json'),science_launched=False,tests_returncode=0,source_files_count=len(source_files),implementation='post-merge journals and complete checkpoint precede export; no pooling'))
    for f in SOURCE.rglob('*'):
        if f.is_file() and '__pycache__' not in f.parts:f.chmod(0o444)
    for name in ('CONFIG.json','RUN_REQUEST.json','SOURCE_SNAPSHOT.json','TESTS_RECEIPT.json','BUILD_RECEIPT.json'):(UNIT/name).chmod(0o444)
    print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(UNIT/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],science_launched=False)))
