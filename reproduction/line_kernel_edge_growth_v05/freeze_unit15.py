"""Freeze unit015 only; parent owns snapshots and complete numerical process."""
from common import *
import copy
SOURCE=Path(__file__).resolve().parent
RUNTIME=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031')
UNIT=RUNTIME/'units/unit_015';REF=UNIT.parent/'unit_014';JOINT=UNIT.parent/'unit_012';PREFIX=UNIT.parent/'unit_011'

def make_config():
    guard();decision=json.loads((UNIT/'DECISION.json').read_text());step=decision['recommended_next_step'];window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text())
    assert sha(JOINT/'CONFIG.json')=='6a80dc26da122c66fa4a4a9c43b882f6c1b98d76570fa5046b12f8e26fa4d862'
    assert sha(PREFIX/'CONFIG.json')=='2dca3f6c8d3f5572a69f7a6653124b7a4c1fd091d7f50cec7958b3a8939aa884'
    c=copy.deepcopy(json.loads((JOINT/'CONFIG.json').read_text()));f=json.loads((REF/'PARENT_RUN_FROZEN.json').read_text())
    snapshots={snap:f['source_files'][original] for original,snap in f['immutable_source_snapshot'].items()};verify(snapshots);verify(f['source_files']);external=f['helper_files'];verify(external);assert len(external)==4
    assert sha(c['previous_state'])==step['input']['state_sha256'];assert sha(c['previous_checkpoint'])==step['input']['checkpoint_sha256'];assert sha(c['predecessor_config'])==step['input']['predecessor_config_sha256']
    inputs=dict(c['input_files']);seal=json.loads((JOINT/'SEAL.json').read_text())['files'];state=JOINT/'scenes/scan24/states/M4';native=JOINT/'scenes/scan24/stages/M4_MERGE_ONLY'
    for directory in (state,native):
        cp=json.loads((directory/'CHECKPOINT.json').read_text());assert cp['complete']
        for name in ['CHECKPOINT.json']+list(cp['files']):
            p=directory/name;inputs[str(p)]=seal[str(p.relative_to(JOINT))]
    for name in ('GROUPS.json','METRICS.json','CANDIDATE_STATUS.npz'):
        p=native/name;inputs[str(p)]=seal[str(p.relative_to(JOINT))]
    for p in (JOINT/'CONFIG.json',JOINT/'DECISION.json',JOINT/'SEAL.json',JOINT/'RUN_RESULT.json',REF/'CONFIG.json',REF/'PARENT_RUN_FROZEN.json',UNIT/'DECISION.json',RUNTIME/'orchestration/WINDOW.json'):inputs[str(p)]=sha(p)
    verify(inputs);sources={str(p):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    c.update(unit=str(UNIT),variant='prefix_protected_endpoint',decision_path=str(UNIT/'DECISION.json'),decision_sha256=sha(UNIT/'DECISION.json'),fixed_decision=decision,settings=step['fixed_settings'],visual_selection=step['visuals'],source_files=sources,input_files=inputs,helper_files={**external,**snapshots},reference_snapshot_manifest=str(REF/'PARENT_RUN_FROZEN.json'),reference_config_sha256=sha(REF/'CONFIG.json'),joint_state=str(state/'STATE.pkl'),joint_candidates=str(state/'ORDERED_CANDIDATES.npz'),joint_membership=str(native/'MEMBERSHIP.npz'),joint_groups=str(native/'GROUPS.json'),joint_config=str(JOINT/'CONFIG.json'),joint_config_sha256=sha(JOINT/'CONFIG.json'),material_case_ids=[235032,218770,387535,98755,88292,37087],damaged_case_ids=[255246,36865,121930],science_deadline=window['science_wrap_jst'],unit_deadline=window['science_wrap_jst'],no_new_after_jst=window['no_new_after_jst'],reference_results=c['reference_results']+[str(native/'METRICS.json')],fit_budget='One shared original-prefix+endpoint fit pass40000; exact prefix and joint replays without refitting; protected commit priority only')
    assert c['scene']=='scan24' and c['kernel_count']==458490 and c['views']==['0012','0036']
    assert c['numeric']['fit_cap_per_level']==40000 and c['max_seconds']==1800 and c['stage_elapsed_limits']==dict(input=120,M4=1380,final=1800)
    return c,external

if __name__=='__main__':
    assert not (UNIT/'source_snapshot').exists() and not (UNIT/'scenes').exists()
    receipt=json.loads((UNIT/'TESTS_RECEIPT.json').read_text());assert receipt['returncode']==0;verify(receipt['source_files']);assert sha(receipt['log'])==receipt['log_sha256']
    red=json.loads((UNIT/'tests/RED_RECEIPT.json').read_text());assert red['returncode']==1 and red['failures']==1 and red['errors']==0 and not red['implementation_existed'];assert sha(red['log'])==red['log_sha256']
    c,external=make_config();assert c['source_files']==receipt['source_files'];assert time.time()<datetime.datetime.fromisoformat(c['no_new_after_jst']).timestamp()
    js(UNIT/'CONFIG.json',c);request=dict(script=str(SOURCE/'protected_runner.py'),config_path=str(UNIT/'CONFIG.json'),config_sha256=sha(UNIT/'CONFIG.json'),source_files=c['source_files'],helper_files=external,max_seconds=1800,tests_receipt=str(UNIT/'TESTS_RECEIPT.json'));js(UNIT/'RUN_REQUEST.json',request)
    js(UNIT/'BUILD_RECEIPT.json',dict(status='READY_FOR_PARENT_COMPUTE',utc=now(),decision_sha256=c['decision_sha256'],config_sha256=request['config_sha256'],run_request_sha256=sha(UNIT/'RUN_REQUEST.json'),source_files_count=len(c['source_files']),tests_returncode=0,science_launched=False,parent_owns_source_snapshot=True,tdd_status=receipt['tdd_status']))
    for name in ('CONFIG.json','RUN_REQUEST.json','TESTS_RECEIPT.json','BUILD_RECEIPT.json'):(UNIT/name).chmod(0o444)
    print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(UNIT/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],source_files=len(c['source_files']),external_helpers=len(external),science_launched=False)))
