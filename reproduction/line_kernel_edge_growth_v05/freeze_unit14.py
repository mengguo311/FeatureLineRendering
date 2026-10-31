"""Scan65 configuration transfer only; parent owns snapshot and complete compute."""
from common import *
import copy
SOURCE=Path(__file__).resolve().parent
RUNTIME=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031')
UNIT=RUNTIME/'units/unit_014';REF=UNIT.parent/'unit_013';CONTROL=UNIT.parent/'unit_009'

def make_config():
    guard();decision=json.loads((UNIT/'DECISION.json').read_text());step=decision['recommended_next_step']
    window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text())
    reference=json.loads((REF/'CONFIG.json').read_text());old=json.loads((CONTROL/'CONFIG.json').read_text())
    assert sha(REF/'CONFIG.json')==step['reference']['config_sha256']
    assert sha(CONTROL/'CONFIG.json')=='3bbee014bf25d241a6576a43d0162da31700fd1a1dc098f9267e2c0f4f2e2979'
    frozen=json.loads((REF/'PARENT_RUN_FROZEN.json').read_text())
    snapshots={snap:frozen['source_files'][orig] for orig,snap in frozen['immutable_source_snapshot'].items()}
    verify(snapshots);verify(frozen['source_files']);external=frozen['helper_files'];verify(external);assert len(external)==4
    pre=Path(step['input']['unit_root'])
    assert Path(old['previous_state'])==pre/step['input']['state']
    assert Path(old['previous_checkpoint'])==pre/step['input']['checkpoint']
    assert sha(old['previous_state'])==step['input']['state_sha256']
    assert sha(old['predecessor_config'])==step['input']['predecessor_config_sha256']
    pc=json.loads(Path(old['previous_checkpoint']).read_text())
    assert pc['complete'] and pc['stage']==step['input']['checkpoint_stage']=='M3_STATE'
    assert pc['config_binding']==sha(pre/'CONFIG.json') and pc['decision_sha256']==sha(pre/'DECISION.json')
    numeric=copy.deepcopy(old['numeric']);assert numeric['fit_cap_per_level']==30000
    numeric['fit_cap_per_level']=40000;assert numeric==reference['numeric']
    c=copy.deepcopy(old);inputs=dict(old['input_files']);seal=json.loads((CONTROL/'SEAL.json').read_text())['files']
    state=CONTROL/'scenes/scan65/states/M4';native=CONTROL/'scenes/scan65/stages/M4_MERGE_ONLY'
    for directory in (state,native):
        cp=json.loads((directory/'CHECKPOINT.json').read_text())
        assert cp['complete'] and cp['config_binding']==sha(CONTROL/'CONFIG.json') and cp['decision_sha256']==sha(CONTROL/'DECISION.json')
        for name in ['CHECKPOINT.json']+list(cp['files']):
            p=directory/name;inputs[str(p)]=seal[str(p.relative_to(CONTROL))]
    for name in ('GROUPS.json','METRICS.json','LINEAGE.json','CANDIDATE_STATUS.npz'):
        p=native/name;inputs[str(p)]=seal[str(p.relative_to(CONTROL))]
    result=json.loads((CONTROL/'RUN_RESULT.json').read_text())
    assert result['comparisons']['M4']['fit_attempts']==18069<30000
    for p in (CONTROL/'CONFIG.json',CONTROL/'DECISION.json',CONTROL/'SEAL.json',CONTROL/'PARENT_RUN_FROZEN.json',CONTROL/'RUN_RESULT.json',REF/'CONFIG.json',REF/'DECISION.json',REF/'PARENT_RUN_FROZEN.json',UNIT/'DECISION.json',RUNTIME/'orchestration/WINDOW.json'):
        inputs[str(p)]=sha(p)
    verify(inputs)
    sources={str(p):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    c.update(unit=str(UNIT),variant='endpoint_supplement',numeric=numeric,
        control_fit_limit=30000,historical_control_fit_limit=30000,control_actual_fit_count=18069,
        shadow_replay_fit_ceiling=40000,
        shadow_receipt_field_semantics='Inherited SHADOW_CONTROL.control_fit_limit records replay ceiling40000; historical control limit is30000 in CONFIG and COMPARISONS. Exact prefix fit count must be18069.',
        control_state=str(state/'STATE.pkl'),control_candidates=str(state/'ORDERED_CANDIDATES.npz'),
        control_membership=str(native/'MEMBERSHIP.npz'),control_groups=str(native/'GROUPS.json'),changed_tracked_groups=[],
        decision_path=str(UNIT/'DECISION.json'),decision_sha256=sha(UNIT/'DECISION.json'),fixed_decision=decision,
        settings=step['fixed_settings'],visual_selection=step['visuals'],input_files=inputs,source_files=sources,
        helper_files={**external,**snapshots},reference_snapshot_manifest=str(REF/'PARENT_RUN_FROZEN.json'),
        reference_config_sha256=sha(REF/'CONFIG.json'),reference_results=old['reference_results']+[str(native/'METRICS.json')],
        control_config=str(CONTROL/'CONFIG.json'),control_config_sha256=sha(CONTROL/'CONFIG.json'),
        science_deadline=window['science_wrap_jst'],unit_deadline=window['science_wrap_jst'],no_new_after_jst=window['no_new_after_jst'],
        endpoint_supplement=copy.deepcopy(reference['endpoint_supplement']),
        fit_budget='One scan65 M4 pass;40000 shared prefix+supplement fits; exact unit009 prefix replay (historical limit30000, actual18069); no pooling')
    assert c['scene']=='scan65' and c['kernel_count']==279616 and c['views']==['0012','0036']
    assert c['tracked_predecessor_groups']==[56133,64877,167509]
    assert c['max_seconds']==1800 and c['stage_elapsed_limits']==dict(input=120,M4=1380,final=1800)
    return c,external

if __name__=='__main__':
    assert not (UNIT/'source_snapshot').exists() and not (UNIT/'scenes').exists()
    receipt=json.loads((UNIT/'TESTS_RECEIPT.json').read_text());assert receipt['returncode']==0
    verify(receipt['source_files']);assert sha(receipt['log'])==receipt['log_sha256']
    assert sha(receipt['preimplementation_receipt'])==receipt['preimplementation_receipt_sha256']
    c,external=make_config();assert c['source_files']==receipt['source_files']
    assert time.time()<datetime.datetime.fromisoformat(c['no_new_after_jst']).timestamp()
    js(UNIT/'CONFIG.json',c)
    request=dict(script=str(SOURCE/'endpoint_runner.py'),config_path=str(UNIT/'CONFIG.json'),config_sha256=sha(UNIT/'CONFIG.json'),source_files=c['source_files'],helper_files=external,max_seconds=1800,tests_receipt=str(UNIT/'TESTS_RECEIPT.json'))
    js(UNIT/'RUN_REQUEST.json',request)
    js(UNIT/'BUILD_RECEIPT.json',dict(status='READY_FOR_PARENT_COMPUTE',utc=now(),decision_sha256=c['decision_sha256'],config_sha256=request['config_sha256'],run_request_sha256=sha(UNIT/'RUN_REQUEST.json'),source_files_count=len(c['source_files']),tests_returncode=0,science_launched=False,parent_owns_source_snapshot=True,prior_source_files_unchanged=True,numerical_core_unchanged=True,tdd_status=receipt['tdd_status']))
    for name in ('CONFIG.json','RUN_REQUEST.json','TESTS_RECEIPT.json','BUILD_RECEIPT.json'):(UNIT/name).chmod(0o444)
    print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(UNIT/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],source_files=len(c['source_files']),external_helpers=len(external),science_launched=False)))
