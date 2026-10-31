"""Freeze only; the parent alone snapshots and launches complete science."""
from common import *
import copy
SOURCE=Path(__file__).resolve().parent
RUNTIME=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031')
UNIT=RUNTIME/'units/unit_012';REF=UNIT.parent/'unit_011'

def make_config():
    guard();decision=json.loads((UNIT/'DECISION.json').read_text());step=decision['recommended_next_step']
    window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text());old=json.loads((REF/'CONFIG.json').read_text())
    assert sha(REF/'CONFIG.json')==step['control']['config_sha256']
    frozen=json.loads((REF/'PARENT_RUN_FROZEN.json').read_text());snapshots={snap:frozen['source_files'][orig] for orig,snap in frozen['immutable_source_snapshot'].items()}
    verify(snapshots);verify(frozen['source_files']);external=frozen['helper_files'];verify(external);assert len(external)==4
    pre=Path(step['input']['unit_root']);assert Path(old['previous_state'])==pre/step['input']['state'];assert Path(old['previous_checkpoint'])==pre/step['input']['checkpoint']
    assert sha(old['previous_state'])==step['input']['state_sha256'];assert sha(old['previous_checkpoint'])==step['input']['checkpoint_sha256']
    pc=json.loads(Path(old['previous_checkpoint']).read_text());assert pc['complete'] and pc['stage']=='M3_STATE'
    assert pc['config_binding']==sha(old['predecessor_config'])
    c=copy.deepcopy(old);inputs=dict(old['input_files']);seal=json.loads((REF/'SEAL.json').read_text())['files']
    state=REF/'scenes/scan24/states/M4';native=REF/'scenes/scan24/stages/M4_MERGE_ONLY'
    for directory in (state,native):
        cp=json.loads((directory/'CHECKPOINT.json').read_text());assert cp['complete'] and cp['config_binding']==sha(REF/'CONFIG.json') and cp['decision_sha256']==sha(REF/'DECISION.json')
        for name in ['CHECKPOINT.json']+list(cp['files']):
            p=directory/name;inputs[str(p)]=seal[str(p.relative_to(REF))]
    for name in ('GROUPS.json','METRICS.json','LINEAGE.json','CANDIDATE_STATUS.npz'):
        p=native/name;inputs[str(p)]=seal[str(p.relative_to(REF))]
    for p in (REF/'CONFIG.json',REF/'DECISION.json',REF/'SEAL.json',REF/'PARENT_RUN_FROZEN.json',UNIT/'DECISION.json',RUNTIME/'orchestration/WINDOW.json'):inputs[str(p)]=sha(p)
    verify(inputs)
    sources={str(p):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    c.update(unit=str(UNIT),variant='endpoint_supplement',control_fit_limit=40000,control_state=str(state/'STATE.pkl'),control_candidates=str(state/'ORDERED_CANDIDATES.npz'),control_membership=str(native/'MEMBERSHIP.npz'),control_groups=str(native/'GROUPS.json'),decision_path=str(UNIT/'DECISION.json'),decision_sha256=sha(UNIT/'DECISION.json'),fixed_decision=decision,settings=step['fixed_settings'],visual_selection=step['visuals'],input_files=inputs,source_files=sources,helper_files={**external,**snapshots},reference_snapshot_manifest=str(REF/'PARENT_RUN_FROZEN.json'),reference_config_sha256=sha(REF/'CONFIG.json'),reference_results=old['reference_results']+[str(native/'METRICS.json')],science_deadline=window['science_wrap_jst'],unit_deadline=window['science_wrap_jst'],no_new_after_jst=window['no_new_after_jst'],endpoint_supplement=dict(query_k=32,radius_p=1.5,eps=1e-8,screen_cap=30000,append_cap=10000,per_endpoint_cap=1),fit_budget='One M4 topology round;40000 shared prefix+supplement fits; exact unit011 prefix shadow; no pooling')
    assert c['max_seconds']==1800 and c['numeric']['fit_cap_per_level']==40000
    return c,external

if __name__=='__main__':
    assert not (UNIT/'source_snapshot').exists() and not (UNIT/'scenes').exists()
    receipt=json.loads((UNIT/'TESTS_RECEIPT.json').read_text());assert receipt['returncode']==0;verify(receipt['source_files'])
    assert sha(receipt['log'])==receipt['log_sha256'];assert sha(receipt['red_receipt'])==receipt['red_receipt_sha256']
    c,external=make_config();assert c['source_files']==receipt['source_files']
    assert time.time()<datetime.datetime.fromisoformat(c['no_new_after_jst']).timestamp()
    js(UNIT/'CONFIG.json',c);request=dict(script=str(SOURCE/'endpoint_runner.py'),config_path=str(UNIT/'CONFIG.json'),config_sha256=sha(UNIT/'CONFIG.json'),source_files=c['source_files'],helper_files=external,max_seconds=1800,tests_receipt=str(UNIT/'TESTS_RECEIPT.json'))
    js(UNIT/'RUN_REQUEST.json',request)
    js(UNIT/'BUILD_RECEIPT.json',dict(status='READY_FOR_PARENT_COMPUTE',utc=now(),decision_sha256=c['decision_sha256'],config_sha256=request['config_sha256'],run_request_sha256=sha(UNIT/'RUN_REQUEST.json'),source_files_count=len(c['source_files']),tests_returncode=0,science_launched=False,parent_owns_source_snapshot=True,prior_source_files_unchanged=True,scientific_change='Bounded endpoint proposals appended to unchanged original prefix; same40000fit ceiling and original competition',tdd_status=receipt['tdd_status']))
    for name in ('CONFIG.json','RUN_REQUEST.json','TESTS_RECEIPT.json','BUILD_RECEIPT.json'):(UNIT/name).chmod(0o444)
    print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(UNIT/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],source_files=len(c['source_files']),external_helpers=len(external),science_launched=False)))
