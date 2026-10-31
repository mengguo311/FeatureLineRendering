"""Freeze unit016 only; parent owns snapshots and complete numerical process."""
from common import *
import copy
SOURCE=Path(__file__).resolve().parent
RUNTIME=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031')
UNIT=RUNTIME/'units/unit_016';REF=UNIT.parent/'unit_015';JOINT=UNIT.parent/'unit_013';PREFIX=UNIT.parent/'unit_008'

def verify_reference(f):
    for original,h in f['source_files'].items():
        if Path(original).name!='protected_runner.py':verify({original:h})
        else:
            before=ast.parse(Path(f['immutable_source_snapshot'][original]).read_text());after=ast.parse(Path(original).read_text())
            allowed={'fixed_case_figures','fixed_case_comparison'}
            strip=lambda tree:ast.dump(ast.Module(body=[node for node in tree.body if not isinstance(node,ast.FunctionDef) or node.name not in allowed],type_ignores=[]))
            assert strip(before)==strip(after),'ONLY_DESCRIPTIVE_CASE_LABELS_MAY_CHANGE'

def make_config():
    guard();decision=json.loads((UNIT/'DECISION.json').read_text());step=decision['recommended_next_step'];window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text())
    assert sha(JOINT/'CONFIG.json')=='40b69d014e2eb2dd1cbffe5aaaa8d52e86c5730b2006d052633dc6939e56452e'
    assert sha(PREFIX/'CONFIG.json')=='6d4cd08c821e15d3eb2bb42d7017375611662a2a942c48e8c5a61e27e2426052'
    c=copy.deepcopy(json.loads((JOINT/'CONFIG.json').read_text()));f=json.loads((REF/'PARENT_RUN_FROZEN.json').read_text())
    snapshots={snap:f['source_files'][original] for original,snap in f['immutable_source_snapshot'].items()};verify(snapshots);verify_reference(f);external=f['helper_files'];verify(external);assert len(external)==4
    assert sha(c['previous_state'])==step['input']['state_sha256'];assert sha(c['previous_checkpoint'])==step['input']['checkpoint_sha256'];assert sha(c['predecessor_config'])==step['input']['predecessor_config_sha256']
    inputs=dict(c['input_files']);seal=json.loads((JOINT/'SEAL.json').read_text())['files'];state=JOINT/'scenes/ficus/states/M4';native=JOINT/'scenes/ficus/stages/M4_MERGE_ONLY'
    for directory in (state,native):
        cp=json.loads((directory/'CHECKPOINT.json').read_text());assert cp['complete']
        for name in ['CHECKPOINT.json']+list(cp['files']):
            p=directory/name;inputs[str(p)]=seal[str(p.relative_to(JOINT))]
    for name in ('GROUPS.json','METRICS.json','CANDIDATE_STATUS.npz'):
        p=native/name;inputs[str(p)]=seal[str(p.relative_to(JOINT))]
    for p in (JOINT/'CONFIG.json',JOINT/'DECISION.json',JOINT/'SEAL.json',JOINT/'RUN_RESULT.json',REF/'CONFIG.json',REF/'PARENT_RUN_FROZEN.json',UNIT/'DECISION.json',RUNTIME/'orchestration/WINDOW.json'):inputs[str(p)]=sha(p)
    verify(inputs);sources={str(p):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    c.update(unit=str(UNIT),variant='prefix_protected_endpoint',decision_path=str(UNIT/'DECISION.json'),decision_sha256=sha(UNIT/'DECISION.json'),fixed_decision=decision,settings=step['fixed_settings'],visual_selection=step['visuals'],source_files=sources,input_files=inputs,helper_files={**external,**snapshots},reference_snapshot_manifest=str(REF/'PARENT_RUN_FROZEN.json'),reference_config_sha256=sha(REF/'CONFIG.json'),joint_state=str(state/'STATE.pkl'),joint_candidates=str(state/'ORDERED_CANDIDATES.npz'),joint_membership=str(native/'MEMBERSHIP.npz'),joint_groups=str(native/'GROUPS.json'),joint_config=str(JOINT/'CONFIG.json'),joint_config_sha256=sha(JOINT/'CONFIG.json'),material_case_ids=[33824,29734],damaged_case_ids=[21870,28829,28837,78077,62169],joint_case_label='joint_reference_not_material',fixed_case_rule='Frozen ficus damaged controls21870/28829/28837/78077/62169, below-threshold33824 and inherited29734; exact identical rows, no new-material assertion.',science_deadline=window['science_wrap_jst'],unit_deadline=window['science_wrap_jst'],no_new_after_jst=window['no_new_after_jst'],reference_results=c['reference_results']+[str(native/'METRICS.json')],fit_budget='One shared original-prefix+endpoint fit pass40000; exact prefix and joint replays without refitting; protected commit priority only')
    assert c['scene']=='ficus' and c['kernel_count']==285956 and c['views']==['test_r_1','test_r_79']
    assert c['control_fit_limit']==30000 and c['control_actual_fit_count']==19949
    assert sha(REF/'CONFIG.json')=='8dd3a00ac789e9b67b6aa964d70e346de5fe955c244992f9f8ed58f623b20b70'
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
