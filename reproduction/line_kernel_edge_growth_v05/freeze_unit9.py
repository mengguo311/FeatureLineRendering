"""Freeze scan65 M4 configuration; no science, no parent snapshot creation."""
from common import *

ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
RUNTIME=ROOT/'line_kernel_edge_growth_v05_20261031'
UNIT=RUNTIME/'units/unit_009'
PRE=UNIT.parent/'unit_006'
REF=UNIT.parent/'unit_008'
SOURCE=Path(__file__).resolve().parent

def make_config():
    guard()
    decision=json.loads((UNIT/'DECISION.json').read_text())
    step=decision['recommended_next_step']
    window=json.loads((RUNTIME/'orchestration/WINDOW.json').read_text())
    predecessor=json.loads((PRE/'CONFIG.json').read_text())
    reference=json.loads((REF/'CONFIG.json').read_text())
    assert sha(PRE/'CONFIG.json')==step['input']['predecessor_config_sha256']
    assert sha(REF/'CONFIG.json')==step['reference']['config_sha256']
    assert predecessor['numeric']==reference['numeric']
    frozen=json.loads((REF/'PARENT_RUN_FROZEN.json').read_text())
    snapshots={snap:frozen['source_files'][orig] for orig,snap in frozen['immutable_source_snapshot'].items()}
    verify(snapshots)
    verify(frozen['source_files'])
    external=dict(frozen['helper_files'])
    assert len(external)==4
    verify(external)
    sources={str(p):sha(p) for p in sorted(SOURCE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    seal=json.loads((PRE/'SEAL.json').read_text())['files']
    baseline_groups=str(Path(predecessor['baseline_membership']).with_name('GROUPS.json'))
    original_paths=[predecessor[k] for k in ('gaussians','controls','representatives','baseline_membership','cameras')]
    original_paths += [str(Path(predecessor['gaussians']).with_suffix('.ply')),baseline_groups,str(Path(predecessor['baseline_membership']).with_name('CHAINS.npz'))]
    inputs={p:predecessor['input_files'][p] for p in original_paths}
    state=PRE/step['input']['state']
    cp=PRE/step['input']['checkpoint']
    native=PRE/'scenes/scan65/stages/M3_MERGE_ONLY'
    l1=Path(predecessor['L1_membership']).parent
    m2=Path(predecessor['previous_membership']).parent
    assert Path(step['input']['unit_root'])==PRE
    oldcp=json.loads(cp.read_text())
    assert oldcp['stage']==step['input']['checkpoint_stage']=='M3_STATE'
    assert oldcp['config_binding']==sha(PRE/'CONFIG.json')
    assert oldcp['decision_sha256']==sha(PRE/'DECISION.json')
    for directory in (state.parent,native):
        closed=json.loads((directory/'CHECKPOINT.json').read_text())
        assert closed['complete']
        for name in ['CHECKPOINT.json']+list(closed['files']):
            p=directory/name
            inputs[str(p)]=seal[str(p.relative_to(PRE))]
    for directory,names in ((native,('GROUPS.json','METRICS.json','LINEAGE.json')),):
        for name in names:
            p=directory/name
            inputs[str(p)]=seal[str(p.relative_to(PRE))]
    for directory,names in ((l1,('MEMBERSHIP.npz','GROUPS.json','LINEAGE.json')),(m2,('MEMBERSHIP.npz','GROUPS.json','LINEAGE.json','METRICS.json'))):
        for name in names:
            p=str(directory/name);inputs[p]=predecessor['input_files'][p]
    assert inputs[str(state)]==step['input']['state_sha256']
    assert inputs[str(cp)]==step['input']['checkpoint_sha256']
    external_metrics=[]
    for oldunit,scene in ((REF,'ficus'),(UNIT.parent/'unit_007','scan24')):
        oldseal=json.loads((oldunit/'SEAL.json').read_text())['files']
        metric=oldunit/f'scenes/{scene}/stages/M4_MERGE_ONLY/METRICS.json'
        inputs[str(metric)]=oldseal[str(metric.relative_to(oldunit))]
        external_metrics.append(str(metric))
        inputs[str(oldunit/'SEAL.json')]=sha(oldunit/'SEAL.json')
    for p in (UNIT/'DECISION.json',PRE/'CONFIG.json',PRE/'DECISION.json',PRE/'SEAL.json',REF/'CONFIG.json',REF/'PARENT_RUN_FROZEN.json',RUNTIME/'orchestration/WINDOW.json'):
        inputs[str(p)]=sha(p)
    verify(inputs)
    keys=('scene','kernel_count','p','gaussians','controls','representatives','baseline_membership','cameras','renderer','libroot')
    config={k:predecessor[k] for k in keys}
    assert config['scene']=='scan65' and config['kernel_count']==279616
    config.update(
        unit=str(UNIT),runtime=str(RUNTIME),views=['0012','0036'],baseline_groups=baseline_groups,
        decision_path=str(UNIT/'DECISION.json'),decision_sha256=sha(UNIT/'DECISION.json'),
        previous_state=str(state),previous_checkpoint=str(cp),previous_checkpoint_stage='M3_STATE',
        previous_membership=str(native/'MEMBERSHIP.npz'),previous_carriers=str(native/'CARRIERS.npz'),
        previous_groups=str(native/'GROUPS.json'),previous_lineage=str(native/'LINEAGE.json'),
        predecessor_config=str(PRE/'CONFIG.json'),predecessor_config_sha256=sha(PRE/'CONFIG.json'),
        L1_membership=str(l1/'MEMBERSHIP.npz'),L1_groups=str(l1/'GROUPS.json'),tracked_predecessor_groups=[56133,64877,167509],level=4,predecessor_label='M3',history_memberships={'M2':str(m2/'MEMBERSHIP.npz')},
        max_seconds=1800,science_deadline=window['science_wrap_jst'],unit_deadline=window['science_wrap_jst'],
        no_new_after_jst=window['no_new_after_jst'],stage_elapsed_limits=dict(input=120,M4=1380,final=1800),
        final_export_reserve_seconds=420,numeric=reference['numeric'],settings=step['settings'],fixed_decision=decision,
        visual_selection=step['visuals'],
        three_fragment_selection='One growth_gate group with>=3 substantial L1 fragments, maximal supported_length_p then minimal edge_id; no substitute if absent',
        input_files=inputs,source_files=sources,helper_files={**external,**snapshots},
        reference_results=[baseline_groups,str(l1/'GROUPS.json'),str(native/'GROUPS.json'),str(native/'METRICS.json'),str(m2/'GROUPS.json'),str(m2/'METRICS.json')]+external_metrics,
        reference_snapshot_manifest=str(REF/'PARENT_RUN_FROZEN.json'),reference_config_sha256=sha(REF/'CONFIG.json'),
        snapshot_creation_owner='PARENT_ONLY',cpu=2,blas=2,strict_serial=True,
        unit_output_cap_bytes=2*2**30,runtime_output_cap_bytes=8*2**30,
        min_root_free_bytes=2**30,min_hdd_free_bytes=10*2**30,
        fit_budget='One additional level4 topology pass, reset30000; no initialization/pooling',
        all_unknown_eligible=True,no_RGB_source_GS=True)
    return config,external

if __name__=='__main__':
    assert not (UNIT/'source_snapshot').exists(),'Parent owns snapshot target'
    receipt=json.loads((UNIT/'TESTS_RECEIPT.json').read_text())
    assert receipt['returncode']==0
    verify(receipt['source_files'])
    assert sha(receipt['log'])==receipt['log_sha256']
    assert sha(receipt['preimplementation_receipt'])==receipt['preimplementation_receipt_sha256']
    config,external=make_config()
    assert config['source_files']==receipt['source_files']
    assert datetime.datetime.now(datetime.timezone.utc).timestamp()<datetime.datetime.fromisoformat(config['no_new_after_jst']).timestamp()
    assert not (UNIT/'scenes').exists(),'BUILD must not launch full science'
    js(UNIT/'CONFIG.json',config)
    request=dict(script=str(SOURCE/'continuation_level.py'),config_path=str(UNIT/'CONFIG.json'),
                 config_sha256=sha(UNIT/'CONFIG.json'),source_files=config['source_files'],helper_files=external,
                 max_seconds=1800,tests_receipt=str(UNIT/'TESTS_RECEIPT.json'))
    js(UNIT/'RUN_REQUEST.json',request)
    js(UNIT/'BUILD_RECEIPT.json',dict(status='READY_FOR_PARENT_COMPUTE',utc=now(),decision_sha256=config['decision_sha256'],
       config_sha256=request['config_sha256'],run_request_sha256=sha(UNIT/'RUN_REQUEST.json'),
       source_files_count=len(config['source_files']),tests_returncode=0,science_launched=False,
       parent_owns_source_snapshot=True,prior_source_files_unchanged=True,numerical_core_unchanged=True,
       tdd_status=receipt['tdd_status']))
    for name in ('CONFIG.json','RUN_REQUEST.json','TESTS_RECEIPT.json','BUILD_RECEIPT.json'):
        (UNIT/name).chmod(0o444)
    print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(UNIT/'RUN_REQUEST.json'),
        config_sha256=request['config_sha256'],source_files=len(config['source_files']),external_helpers=len(external),science_launched=False)))
