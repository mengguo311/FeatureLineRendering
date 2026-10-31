"""Freeze unit019 only; parent owns snapshots and complete numerical process."""
from common import *
import copy
SOURCE=Path(__file__).resolve().parent
RUNTIME=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031')
UNIT=RUNTIME/'units/unit_019';REF=UNIT.parent/'unit_018'

def verify_reference(f):
    verify(f['source_files'])

def make_config():
    guard();decision=json.loads((UNIT/'DECISION.json').read_text());step=decision['recommended_next_step'];window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text())
    previous=UNIT.parent/'unit_016';assert sha(previous/'CONFIG.json')==step['input']['predecessor_config_sha256']
    c=copy.deepcopy(json.loads((previous/'CONFIG.json').read_text()));f=json.loads((REF/'PARENT_RUN_FROZEN.json').read_text())
    snapshots={snap:f['source_files'][original] for original,snap in f['immutable_source_snapshot'].items()};verify(snapshots);verify_reference(f);external=f['helper_files'];verify(external);assert len(external)==4
    assert sha(REF/'CONFIG.json')=='6bf43845007491d21538a0b4032797e7d98e9f548b8ce7b66bba626b9dc509f2'
    inputs=dict(c['input_files']);seal=json.loads((previous/'SEAL.json').read_text())['files'];state=previous/'scenes/ficus/states/M4';native=previous/'scenes/ficus/stages/M4_MERGE_ONLY'
    assert sha(state/'STATE.pkl')==step['input']['state_sha256'];assert sha(state/'CHECKPOINT.json')==step['input']['checkpoint_sha256']
    for directory in (state,native):
        cp=json.loads((directory/'CHECKPOINT.json').read_text());assert cp['complete']
        for name in ['CHECKPOINT.json']+list(cp['files']):
            p=directory/name;inputs[str(p)]=seal[str(p.relative_to(previous))]
    for name in ('GROUPS.json','METRICS.json','CANDIDATE_STATUS.npz'):
        p=native/name;inputs[str(p)]=seal[str(p.relative_to(previous))]
    for p in (previous/'CONFIG.json',previous/'DECISION.json',previous/'SEAL.json',previous/'RUN_RESULT.json',REF/'CONFIG.json',REF/'PARENT_RUN_FROZEN.json',UNIT/'DECISION.json',RUNTIME/'orchestration/WINDOW.json'):inputs[str(p)]=sha(p)
    history=dict(c.get('history_memberships',{}));history['M3']=c['previous_membership']
    for key in list(c):
        if key.startswith(('control_','joint_')) or key in ('material_case_ids','damaged_case_ids','fixed_case_rule'):c.pop(key)
    c.update(unit=str(UNIT),level=5,predecessor_label='M4',variant='prefix_protected_endpoint_continuation',internal_controls=True,previous_state=str(state/'STATE.pkl'),previous_checkpoint=str(state/'CHECKPOINT.json'),previous_checkpoint_stage='M4_STATE',predecessor_config=str(previous/'CONFIG.json'),predecessor_config_sha256=sha(previous/'CONFIG.json'),previous_membership=str(native/'MEMBERSHIP.npz'),previous_carriers=str(native/'CARRIERS.npz'),previous_groups=str(native/'GROUPS.json'),previous_lineage=str(native/'LINEAGE.json'),previous_protection=str(state/'PROTECTION.json'),history_memberships=history,tracked_predecessor_groups=[79171,204470,57769,21870,28829,28837,78077,62169,33824,29734],changed_tracked_groups=[],control_fit_limit=40000,fit_caps_by_round=[30000,30000,40000,40000],stage_elapsed_limits=dict(input=120,M5=1380,final=1800),decision_path=str(UNIT/'DECISION.json'),decision_sha256=sha(UNIT/'DECISION.json'),fixed_decision=decision,settings=step['fixed_settings'],visual_selection=step['visuals'],input_files=inputs,helper_files={**external,**snapshots},reference_snapshot_manifest=str(REF/'PARENT_RUN_FROZEN.json'),reference_config_sha256=sha(REF/'CONFIG.json'),science_deadline=window['science_wrap_jst'],unit_deadline=window['science_wrap_jst'],no_new_after_jst=window['no_new_after_jst'],reference_results=c['reference_results']+[str(native/'METRICS.json')],fit_budget='One level5 shared40000-fit pass. Prefix/joint controls generated internally, no historical M5 replay.')
    c['parent_launch_latest_jst']=step['schedule']['parent_launch_latest'];assert c['parent_launch_latest_jst']=='2026-10-31T12:05:00+09:00'
    verify(inputs);c['source_files']={str(p):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    assert c['scene']=='ficus' and c['kernel_count']==285956 and c['views']==['test_r_1','test_r_79']
    assert c['numeric']['fit_cap_per_level']==40000 and c['max_seconds']==1800
    assert all(k not in c for k in ('control_state','joint_state','control_candidates','joint_candidates'))
    return c,external

if __name__=='__main__':
    assert not (UNIT/'source_snapshot').exists() and not (UNIT/'scenes').exists()
    receipt=json.loads((UNIT/'TESTS_RECEIPT.json').read_text());assert receipt['returncode']==0;verify(receipt['source_files']);assert sha(receipt['log'])==receipt['log_sha256']
    pre=json.loads((UNIT/'tests/PREIMPLEMENTATION.json').read_text());verify(pre['source_files']);assert receipt['tdd_status'].startswith('REGRESSION_ONLY')
    c,external=make_config();assert c['source_files']==receipt['source_files'];assert time.time()<datetime.datetime.fromisoformat(c['no_new_after_jst']).timestamp()
    js(UNIT/'CONFIG.json',c);request=dict(script=str(SOURCE/'progressive_runner.py'),config_path=str(UNIT/'CONFIG.json'),config_sha256=sha(UNIT/'CONFIG.json'),source_files=c['source_files'],helper_files=external,max_seconds=1800,tests_receipt=str(UNIT/'TESTS_RECEIPT.json'));js(UNIT/'RUN_REQUEST.json',request)
    js(UNIT/'BUILD_RECEIPT.json',dict(status='READY_FOR_PARENT_COMPUTE',utc=now(),decision_sha256=c['decision_sha256'],config_sha256=request['config_sha256'],run_request_sha256=sha(UNIT/'RUN_REQUEST.json'),source_files_count=len(c['source_files']),tests_returncode=0,science_launched=False,parent_owns_source_snapshot=True,tdd_status=receipt['tdd_status']))
    for name in ('CONFIG.json','RUN_REQUEST.json','TESTS_RECEIPT.json','BUILD_RECEIPT.json'):(UNIT/name).chmod(0o444)
    print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(UNIT/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],source_files=len(c['source_files']),external_helpers=len(external),science_launched=False)))
